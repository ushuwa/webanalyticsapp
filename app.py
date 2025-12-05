from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from config import Config
from datetime import timedelta
from auth import authenticate_user
from user import get_all_users
from ph_locations_loader import get_coords
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression

import os
from werkzeug.utils import secure_filename
import logging
import ppi
import dependent
#CSV_PATH = "data/PPI.csv"

UPLOAD_FOLDER = "data/uploads"
ALLOWED_EXTENSIONS = {"csv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

logging.basicConfig(
    filename="login.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

app = Flask(__name__)
app.config.from_object(Config)
app.permanent_session_lifetime = timedelta(minutes=1)


# ===========================
#        PAGE ROUTES
# ===========================

@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("analytics_dashboard"))
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

# Main layout for dashboard
@app.route("/analytics/dashboard")
def analytics_dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("main2.html", user=session["user"])

# -----------------------------
# Dynamic pages served to AJAX
# -----------------------------
@app.route("/pages/<page>")
def serve_page(page):
    return render_template(f"pages/{page}")

# Standalone page fallback if needed
@app.route("/dashboard.html")
def dashboard_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html",user=session["user"])
@app.route("/cardprograms.html")
def cardprograms_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("cardprograms.html",user=session["user"])

@app.route("/povertyinsights.html")
def povertyinsights_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("povertyinsights.html",user=session["user"])


@app.route("/usermanagement.html")
def usermanagement_section():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("usermanagement.html")

# ===========================================
# CATCH-ALL ROUTE TO FIX PAGE REFRESH 404
# ===========================================
@app.route("/analytics/<path:subpath>")
def analytics_router(subpath):
    if "user" not in session:
        return redirect(url_for("login"))
    # Always load main layout, JS loads inner content
    return render_template("main2.html", user=session["user"])

# ===========================
#        API ROUTES
# ===========================

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    ip = request.remote_addr
    user = authenticate_user(username, password)

    if user:
        session.permanent = True
        session["user"] = {
            "userid": user["userid"],
            "username": user["username"],
            "firstname": user["firstname"],
            "staffid": user["staffid"],
             "position": user["position"]
        }

        logging.info(f"LOGIN SUCCESS username={username} user_id={user['userid']} ip={ip}")

        return jsonify({
            "status": "success",
            "user": session["user"]
        })
    
    logging.info(f"LOGIN FAILED username={username} ip={ip}")
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@app.route("/api/check-session", methods=["GET"])
def check_session():
    if "user" in session:
        return jsonify({"active": True})
    return jsonify({"active": False}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully"})


# GetAllUsers
@app.route("/api/users", methods=["GET"])
def api_get_users():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    users = get_all_users()
    return jsonify(users)




#PPI END POINTS

@app.route("/ppi/heatmap-data")
def ppi_heatmap_data():
    df = ppi.load_df() #load csv

    df.columns = [c.lower().strip() for c in df.columns]

#Here, nag select ng columns to use
    if not {"area", "unit", "totalppi"}.issubset(df.columns):
        return jsonify([])

    # Clean totalppi
    df["totalppi"] = df["totalppi"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df = df.dropna(subset=["totalppi"])

    # Group by area + unit
    grouped = (
        df.groupby(["area", "unit"], dropna=False)["totalppi"]
        .mean()
        .reset_index()
    )

    # ------------------------------
    # MACHINE LEARNING – KMEANS
    # ------------------------------

    # Must convert to 2D array
    X = grouped["totalppi"].values.reshape(-1, 1)

    # If less than 3 LGUs exist, avoid crash
    if len(grouped) >= 3:
        kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
        grouped["cluster"] = kmeans.fit_predict(X)

        # Order clusters by avg PPI
        order = (
            grouped.groupby("cluster")["totalppi"]
            .mean()
            .sort_values()
            .index
            .tolist()
        )

        cluster_map = {
            order[0]: "High Poverty Risk",
            order[1]: "Medium Poverty Risk",
            order[2]: "Low Poverty Risk",
        }
    else:
        grouped["cluster"] = 1
        cluster_map = {1: "Not enough data"}

    results = []
    for _, row in grouped.iterrows():
        area = str(row["area"])
        unit = str(row["unit"])
        avg_ppi = float(row["totalppi"])

        lat, lng, match_type = get_coords(area, unit)

        results.append({
            "area": area,
            "unit": unit,
            "avg_ppi": round(avg_ppi),
            "lat": lat,
            "lng": lng,
            "cluster": cluster_map[row["cluster"]]
        })

    return jsonify(results)


@app.route("/ppi/trend-data")
def trend_data():
    df = ppi.load_df()

    # Required columns
    required_cols = ["dopen", "totalppi", "status"]
    for c in required_cols:
        if c not in df.columns:
            return jsonify({"labels": [], "values": [], "error": f"Missing column: {c}"})

    # Filter valid status
    df = df[df["status"] != 99]

    # Convert date column
    df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
    df = df.dropna(subset=["dopen"])

    # Clean and convert totalppi
    df["totalppi"] = (
        df["totalppi"]
        .astype(str)
        .str.replace(r"[^0-9.\-]", "", regex=True)
    )
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df = df.dropna(subset=["totalppi"])

    if df.empty:
        return jsonify({"labels": [], "values": [], "error": "No valid data"})

    # ===========================
    # PARAMETERIZED GROUPING
    # ===========================

    group = request.args.get("group", "Y").upper()  # default Yearly

    # Mapping of user input to Pandas period codes
    period_map = {
        "D": "D",  # Daily
        "W": "W",  # Weekly
        "M": "M",  # Monthly
        "Q": "Q",  # Quarterly
        "Y": "Y"   # Yearly
    }

    if group not in period_map:
        group = "Y"

    period = period_map[group]

    # Group by selected time period
    monthly = (
        df.groupby(df["dopen"].dt.to_period(period))["totalppi"]
        .mean()
        .reset_index()
    )

    # Format labels (Period objects → str)
    labels = [str(p) for p in monthly["dopen"]]

    # Poverty likelihood (rounded)
    values = [round(ppi.compute_poverty_likelihood(v)) for v in monthly["totalppi"]]



    # Prepare the regression dataset
    x = np.arange(len(values)).reshape(-1, 1)
    y = np.array(values)

    # Train model
    model = LinearRegression()
    model.fit(x, y)

    # Predict next 3 periods
    future_x = np.arange(len(values), len(values) + 3).reshape(-1, 1)
    forecast = model.predict(future_x).tolist()

    slope = float(model.coef_[0])  # trend slope

    return jsonify({
    "labels": labels,
    "values": values,
    "forecast_next_3": [round(v, 2) for v in forecast],
    "trend_slope": round(slope, 4),
    "group": group
})


@app.route("/ppi/improvement-stats")
def improvement_stats():
    import datetime

    df = ppi.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"cid", "totalppi", "dopen"}
    if not required.issubset(df.columns):
        return jsonify({"error": "Missing columns: cid, totalppi, dopen"}), 400

    # Clean values
    df["totalppi"] = df["totalppi"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")

    df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
    df = df.dropna(subset=["totalppi", "dopen"])

    # Extract year
    df["year"] = df["dopen"].dt.year

    # Auto-detect years
    current_year = datetime.datetime.now().year
    last_year = current_year - 1

    # Validate dataset year availability
    years_available = sorted(df["year"].unique())

    if last_year not in years_available or current_year not in years_available:
        return jsonify({
            "error": "Dataset does not contain the required years.",
            "required_years": [last_year, current_year],
            "years_available": [int(y) for y in years_available]
        }), 400

    # Group per client per year
    grouped = df.groupby(["cid", "year"])["totalppi"].mean().reset_index()

    # Pivot table: each client = row, each year = column
    pivot = grouped.pivot(index="cid", columns="year", values="totalppi")

    # Only compare clients with both years
    pivot = pivot.dropna(subset=[last_year, current_year])


    total_clients = int(len(pivot))
    improved = int((pivot[current_year] > pivot[last_year]).sum())
    same = int((pivot[current_year] == pivot[last_year]).sum())
    worsened = int((pivot[current_year] < pivot[last_year]).sum())



    # Build training data
    pivot["improved_flag"] = (pivot[current_year] > pivot[last_year]).astype(int)

    X = pivot[[last_year]]  # previous year’s PPI
    y = pivot["improved_flag"]

    # Train logistic regression
    log_model = LogisticRegression()
    log_model.fit(X, y)

    # Probability client improves NEXT YEAR
    future_prob = log_model.predict_proba([[pivot[last_year].mean()]])[0][1]

    return jsonify({
        "year1": int(last_year),
        "year2": int(current_year),
        "years_available": [int(y) for y in years_available],
        "total_clients": total_clients,
        "improved": improved,
        "same": same,
        "worsened": worsened,
        "improved_pct": float(round(improved / total_clients * 100, 2)) if total_clients else 0.0,
        "same_pct": float(round(same / total_clients * 100, 2)) if total_clients else 0.0,
        "worsened_pct": float(round(worsened / total_clients * 100, 2)) if total_clients else 0.0,
        "predict_improvement_probability": round(float(future_prob), 4)

    })

@app.route("/ppi/improvement-stats-monthly")
def improvement_stats_monthly():
    df = ppi.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"cid", "totalppi", "dopen"}
    if not required.issubset(df.columns):
        return jsonify({"error": "Missing required columns"}), 400

    # CLEAN AND PREPARE
    df["totalppi"] = df["totalppi"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
    df = df.dropna(subset=["dopen", "totalppi"])

    # EXTRACT YYYY-MM AS PERIOD
    df["year_month"] = df["dopen"].dt.to_period("M")

    # ALL MONTHS AVAILABLE
    months = sorted(df["year_month"].unique())
    months_str = [str(m) for m in months]

    # READ PARAMETERS
    m1 = request.args.get("m1")  # YYYY-MM
    m2 = request.args.get("m2")  # YYYY-MM

    if m1 and m2:
        try:
            m1 = ppi.pd.Period(m1, freq="M")
            m2 = ppi.pd.Period(m2, freq="M")
        except:
            return jsonify({"error": "Invalid month format. Use YYYY-MM."}), 400
    else:
        # AUTO-DETECT LAST AND PREVIOUS MONTH
        if len(months) < 2:
            return jsonify({"error": "Not enough months to compare.",
                            "months_available": months_str}), 400
        m2 = months[-1]
        m1 = months[-2]

    # COMPUTE AVERAGE PPI PER CLIENT PER MONTH
    grouped = df.groupby(["cid", "year_month"])["totalppi"].mean().reset_index()
    pivot = grouped.pivot(index="cid", columns="year_month", values="totalppi")

    # VALIDATE BOTH MONTHS EXIST
    if m1 not in pivot.columns or m2 not in pivot.columns:
        return jsonify({
            "error": "Missing data for requested months.",
            "requested": [str(m1), str(m2)],
            "months_available": months_str
        }), 400

    # FILTER CLIENTS WITH DATA IN BOTH MONTHS
    pivot = pivot.dropna(subset=[m1, m2], how="any")

    total_clients = int(len(pivot))
    improved = int((pivot[m2] > pivot[m1]).sum())
    same = int((pivot[m2] == pivot[m1]).sum())
    worsened = int((pivot[m2] < pivot[m1]).sum())

    log_model_month = LogisticRegression()
    pivot["improved_flag"] = (pivot[m2] > pivot[m1]).astype(int)

    X = pivot[[m1]]
    y = pivot["improved_flag"]

    log_model_month.fit(X, y)

    prob = log_model_month.predict_proba([[pivot[m1].mean()]])[0][1]


    return jsonify({
        "month1": str(m1),
        "month2": str(m2),
        "months_available": months_str,
        "total_clients": total_clients,
        "improved": improved,
        "same": same,
        "worsened": worsened,
        "improved_pct": float(round(improved / total_clients * 100, 2)) if total_clients else 0.0,
        "same_pct": float(round(same / total_clients * 100, 2)) if total_clients else 0.0,
        "worsened_pct": float(round(worsened / total_clients * 100, 2)) if total_clients else 0.0,
        "predict_monthly_improvement_probability": round(float(prob), 4)

    })


@app.route("/ppi/prepost-latest")
def prepost_latest():
    df = ppi.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"cid", "totalppi", "dopen"}
    if not required.issubset(df.columns):
        return jsonify({"error": "Missing required columns"}), 400

    # -------------------------
    # CLEAN DATA
    # -------------------------
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")

    df = df.dropna(subset=["totalppi", "dopen"])

    # exclude invalid PPI
    df = df[(df["totalppi"] > 0) & (df["totalppi"] <= 200)]

    # -------------------------
    # KEEP ONLY CLIENTS WITH 2+ RECORDS
    # -------------------------
    counts = df.groupby("cid")["totalppi"].count()
    valid_clients = counts[counts >= 2].index
    df = df[df["cid"].isin(valid_clients)]

    if df.empty:
        return jsonify({"error": "No valid clients with multiple PPI entries."}), 400

    # sort by date
    df_sorted = df.sort_values("dopen")

    # PRE = first entry
    pre = df_sorted.groupby("cid").first().reset_index()
    pre["band"] = pre["totalppi"].apply(ppi.ppi_band)

    # POST = last entry
    post = df_sorted.groupby("cid").last().reset_index()
    post["band"] = post["totalppi"].apply(ppi.ppi_band)

    # -------------------------
    # DEFINE BAND ORDER (THE BEST VERSION)
    # -------------------------
    bands = ["0-20", "20-40", "40-60", "60-80", "80-90", "90-100", "100+"]

    # band counts
    pre_counts = pre["band"].value_counts().to_dict()
    post_counts = post["band"].value_counts().to_dict()

    # ordered & cleaned
    pre_final = {b: int(pre_counts.get(b, 0)) for b in bands}
    post_final = {b: int(post_counts.get(b, 0)) for b in bands}

    # Use PRE and POST PPI values
    X = pre[["totalppi"]].merge(post[["totalppi"]], left_index=True, right_index=True)
    X.columns = ["pre_ppi", "post_ppi"]

    # Fit KMeans
    kmeans_mov = KMeans(n_clusters=3, random_state=42)
    movement_clusters = kmeans_mov.fit_predict(X)

    # Attach result
    cluster_map = {0: "Strong Improvement", 1: "Stable", 2: "Worsening"}
    cluster_labels = [cluster_map[c] for c in movement_clusters]

    # -------------------------
    # RETURN CLEAN JSON
    # -------------------------
    return jsonify({
    "total_clients": int(len(pre)),
    "movement_clusters": cluster_labels,
    "bands": [
        {"band": b, "pre": int(pre_final[b]), "post": int(post_final[b])}
        for b in bands
    ]
})

@app.route("/ppi/upload", methods=["POST"])
def upload_ppi_csv():
    # check if file included
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    file = request.files["file"]

    # filename validation
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "Only CSV files allowed"}), 400

    # save uploaded file
    filename = secure_filename(file.filename)
    temp_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(temp_path)

    # load existing PPI.csv
    try:
        main_df = ppi.load_df()
        main_df.columns = [c.lower().strip() for c in main_df.columns]
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to load main PPI.csv: {str(e)}"}), 500

    # load uploaded CSV
    try:
        new_df = ppi.pd.read_csv(temp_path)
        new_df.columns = [c.lower().strip() for c in new_df.columns]
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid CSV format: {str(e)}"}), 400

    # merge datasets
    merged_df = ppi.pd.concat([main_df, new_df], ignore_index=True)

    # remove duplicates: same client + same date of PPI
    if {"cid", "dopen", "status"}.issubset(merged_df.columns):
     merged_df.drop_duplicates(
        subset=["cid", "dopen", "status"],
        keep="last",
        inplace=True
    )

    # save updated PPI.csv
    try:
        merged_df.to_csv("data/PPI.csv", index=False)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save merged CSV: {str(e)}"}), 500

    # return response
    return jsonify({
        "status": "success",
        "message": "CSV uploaded and merged successfully.",
        "existing_records": int(len(main_df)),
        "uploaded_records": int(len(new_df)),
        "final_total_records": int(len(merged_df))
    })

@app.route("/ppi/segmentation")
def ppi_segmentation():
    df = dependent.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    # Required fields
    required = {"cid", "city", "householdmonthly income"}
    missing = required - set(df.columns)
    if missing:
        return jsonify({"error": f"Missing columns: {list(missing)}"}), 400

    # Remove NULL income entries
    df = df[df["householdmonthly income"].notna()]
    df = df[df["householdmonthly income"] != "[NULL]"]
    df = df[df["householdmonthly income"] != "NULL"]

    # Deduplicate: keep last entry per cid
    df_sorted = df.sort_values("cid")
    unique_clients = df_sorted.groupby("cid").last().reset_index()

    # -------------------------
    # CITY SEGMENTATION
    # -------------------------
    city_counts = (
        unique_clients["city"]
        .fillna("UNKNOWN")
        .astype(str)
        .str.strip()
        .value_counts()
        .to_dict()
    )

    income_counts = (
        unique_clients["householdmonthly income"]
        .fillna("UNKNOWN")
        .astype(str)
        .str.strip()
        .value_counts()
        .to_dict()
    )

    return jsonify({
        "total_clients": int(len(unique_clients)),
        "city": city_counts,
        "income_level": income_counts
    })

@app.route("/ppi/cohort-analysis")
def ppi_cohort_analysis():
    import datetime

    df = ppi.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"cid", "dorecognized"}
    missing = required - set(df.columns)
    if missing:
        return jsonify({"error": f"Missing columns: {list(missing)}"}), 400

    # Convert dates
    df["dorecognized"] = ppi.pd.to_datetime(df["dorecognized"], errors="coerce")
    df = df.dropna(subset=["dorecognized", "cid"])

    # Keep one record per CID (earliest recognition)
    df_sorted = df.sort_values("dorecognized")
    cohort_df = df_sorted.groupby("cid").first().reset_index()

    # Current date
    today = datetime.datetime.now()

    # Classification thresholds
    one_year_ago = today - datetime.timedelta(days=365)

    cohort_df["cohort"] = cohort_df["dorecognized"].apply(
        lambda d: "New" if d >= one_year_ago else "Long-time"
    )

    # Counts
    new_count = int((cohort_df["cohort"] == "New").sum())
    old_count = int((cohort_df["cohort"] == "Long-time").sum())

    # Year cohort distribution
    cohort_df["year"] = cohort_df["dorecognized"].dt.year
    year_counts = cohort_df["year"].value_counts().sort_index().to_dict()

    # Month cohort distribution
    cohort_df["year_month"] = cohort_df["dorecognized"].dt.to_period("M")
    month_counts = (
        cohort_df["year_month"]
        .value_counts()
        .sort_index()
        .apply(int)
        .to_dict()
    )

    return jsonify({
        "total_clients": int(len(cohort_df)),
        "new_clients": new_count,
        "long_time_clients": old_count,
        "cohort_by_year": {str(k): int(v) for k, v in year_counts.items()},
        "cohort_by_month": {str(k): int(v) for k, v in month_counts.items()}
    })



@app.route("/ppi/poverty-probability-tables")
def ppi_poverty_probability_tables():
    df = ppi.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"cid", "totalppi", "dopen"}
    missing = required - set(df.columns)
    if missing:
        return jsonify({"error": f"Missing columns: {list(missing)}"}), 400

    # Clean
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")

    # Remove zero, negative or missing PPI
    df = df.dropna(subset=["totalppi", "dopen"])
    df = df[df["totalppi"] > 0]

    # Clients with at least 2 valid rows
    counts = df.groupby("cid")["totalppi"].count()
    valid_clients = counts[counts >= 2].index
    df = df[df["cid"].isin(valid_clients)]

    if df.empty:
        return jsonify({"error": "No valid clients with multiple non-zero PPI entries"}), 400

    # Sort by date
    df_sorted = df.sort_values("dopen")

    # PRE = earliest
    pre = df_sorted.groupby("cid").first()

    # POST = latest
    post = df_sorted.groupby("cid").last()

    # Extra safety: remove any leftover 0 values
    pre = pre[pre["totalppi"] > 0]
    post = post[post["totalppi"] > 0]

    # Poverty likelihood function
    def pov(score):
        return max(0, min(100, 100 - (float(score) * 1.3)))

    pre["poverty_pct"] = pre["totalppi"].apply(pov)
    post["poverty_pct"] = post["totalppi"].apply(pov)

    # Probability bands
    def prob_band(p):
        if p < 20: return "0-20%"
        elif p < 40: return "20-40%"
        elif p < 60: return "40-60%"
        elif p < 80: return "60-80%"
        elif p < 90: return "80-90%"
        else: return "90-100%"

    pre["band"] = pre["poverty_pct"].apply(prob_band)
    post["band"] = post["poverty_pct"].apply(prob_band)

    # Count per band
    pre_counts = pre["band"].value_counts().to_dict()
    post_counts = post["band"].value_counts().to_dict()

    # Ensure all bands exist
    bands = ["0-20%", "20-40%", "40-60%", "60-80%", "80-90%", "90-100%"]

    total = len(pre)
    pre_table = []
    post_table = []

    for b in bands:
        pre_count = pre_counts.get(b, 0)
        post_count = post_counts.get(b, 0)

        pre_table.append({
            "band": b,
            "count": pre_count,
            "percentage": round(pre_count / total * 100, 2)
        })

        post_table.append({
            "band": b,
            "count": post_count,
            "percentage": round(post_count / total * 100, 2)
        })

        # Prepare regression (pre→post)
    X = pre[["poverty_pct"]]
    y = post["poverty_pct"]

    reg = LinearRegression()
    reg.fit(X, y)

    trend_slope = float(reg.coef_[0])

    return jsonify({
        "total_clients": total,
        "pre_probability_table": pre_table,
        "post_probability_table": post_table,
        "poverty_trend_slope": round(trend_slope, 4)

    })

@app.route("/ppi/insights")
def ppi_full_insights():
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.cluster import KMeans

    # Load datasets
    ppi_df = ppi.load_df()
    dep_df = dependent.load_df()

    # ================
    # REGION INSIGHTS
    # ================
    region_insights = ppi.compute_insights_ppi(ppi_df)


    # ================================
    # SEGMENT INSIGHTS (DEPENDENT.CSV)
    # ================================
    segment_insights = dependent.compute_segment_insights_city(dep_df)


    # ==========================
    # ML MODEL 1: TREND FORECAST
    # ==========================
    df = ppi_df.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    # clean
    df = df[df["status"] != 99]
    df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
    df = df.dropna(subset=["dopen"])
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df = df.dropna(subset=["totalppi"])

    # group by month
    monthly = df.groupby(df["dopen"].dt.to_period("M"))["totalppi"].mean().reset_index()
    if len(monthly) >= 3:
        values = [ppi.compute_poverty_likelihood(v) for v in monthly["totalppi"]]
        x = np.arange(len(values)).reshape(-1, 1)
        y = np.array(values)
        model = LinearRegression()
        model.fit(x, y)
        trend_slope = float(model.coef_[0])
    else:
        trend_slope = None


    # =================================
    # ML MODEL 2: HEATMAP RISK CLUSTERS
    # =================================
    dfhm = ppi_df.copy()
    dfhm.columns = [c.lower().strip() for c in dfhm.columns]
    dfhm = dfhm.dropna(subset=["area", "unit", "totalppi"])

    dfhm["totalppi"] = ppi.pd.to_numeric(dfhm["totalppi"], errors="coerce")
    dfhm = dfhm.dropna(subset=["totalppi"])

    grouped = dfhm.groupby(["area", "unit"])["totalppi"].mean().reset_index()

    if len(grouped) >= 3:
        X = grouped["totalppi"].values.reshape(-1, 1)
        kmeans = KMeans(n_clusters=3, n_init="auto", random_state=42)
        grouped["cluster"] = kmeans.fit_predict(X)

        # order clusters by severity
        order = grouped.groupby("cluster")["totalppi"].mean().sort_values().index.tolist()
        cluster_map = {
            order[0]: "High Poverty Risk",
            order[1]: "Medium Poverty Risk",
            order[2]: "Low Poverty Risk"
        }

        grouped["cluster_label"] = grouped["cluster"].map(cluster_map)

        # count how many areas per cluster
        region_clusters = {
            "High Poverty Risk": int((grouped["cluster_label"] == "High Poverty Risk").sum()),
            "Medium Poverty Risk": int((grouped["cluster_label"] == "Medium Poverty Risk").sum()),
            "Low Poverty Risk": int((grouped["cluster_label"] == "Low Poverty Risk").sum())
        }

    else:
        region_clusters = {
            "High Poverty Risk": 0,
            "Medium Poverty Risk": 0,
            "Low Poverty Risk": 0
        }


    # ==========================
    # FINAL INSIGHT RESPONSE
    # ==========================
    return jsonify({
        "regions_needing_support": region_insights["regions_needing_support"],
        "top_improving_segments": segment_insights["top_improving_segments"],

        "ml_models": {
            "trend_slope": trend_slope,
            "region_clusters": region_clusters
        },

        "meta": {
            "ppi_clients": region_insights["total_clients"],
            "dependent_clients": segment_insights["total_segments_analyzed"]
        }
    })







#SCHOLARSHIP MODULE API

@app.route("/scholarship/high-need-areas")
def scholarship_high_need_areas():
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LinearRegression

    df = dependent.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {
        "city",
        "province",
        "householdmonthly income",
        "loan balance",
        "total ppi"
    }
    missing = required - set(df.columns)
    if missing:
        return jsonify({"error": f"Missing required columns: {missing}"}), 400

    # CLEAN COLUMNS
    df["householdmonthly income"] = pd.to_numeric(
        df["householdmonthly income"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce"
    )
    df["loan balance"] = pd.to_numeric(
        df["loan balance"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce"
    )
    df["total ppi"] = pd.to_numeric(
        df["total ppi"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce"
    )

    # Remove NULLs
    df = df.dropna(subset=["householdmonthly income", "loan balance", "total ppi", "city", "province"])

    # EXCLUDE totalppi = 0
    df = df[df["total ppi"] > 0]

    if df.empty:
        return jsonify({"error": "No valid data available."}), 400

    # NORMALIZATION
    max_income = df["householdmonthly income"].max() or 1
    max_loan = df["loan balance"].max() or 1
    max_ppi = df["total ppi"].max() or 1

    # Normalize factors
    df["income_score"] = 1 - (df["householdmonthly income"] / max_income)
    df["loan_score"] = df["loan balance"] / max_loan
    df["poverty_score"] = 1 - (df["total ppi"] / max_ppi)

    # COMPOSITE NEED SCORE
    df["need_score"] = (
        df["income_score"] * 0.5 +
        df["loan_score"] * 0.3 +
        df["poverty_score"] * 0.2
    )

    # RANKING PER AREA
    grouped = (
        df.groupby(["province", "city"])["need_score"]
        .mean()
        .reset_index()
        .sort_values("need_score", ascending=False)
    )

    # ===============================
    # FIT MULTIPLE LINEAR REGRESSION
    # ===============================
    X = df[["householdmonthly income", "loan balance", "total ppi"]]
    y = df["need_score"]

    model = LinearRegression()
    model.fit(X, y)

    coeffs = {
        "income_coeff": float(model.coef_[0]),
        "loan_coeff": float(model.coef_[1]),
        "ppi_coeff": float(model.coef_[2]),
        "intercept": float(model.intercept_),
        "r2_score": float(model.score(X, y))
    }

    # PREPARE OUTPUT
    results = []
    for _, row in grouped.iterrows():
        results.append({
            "province": row["province"],
            "city": row["city"],
            "average_need_score": round(float(row["need_score"]), 4),
            "category": (
                "High Need" if row["need_score"] > 0.66 else
                "Medium Need" if row["need_score"] > 0.33 else
                "Low Need"
            )
        })

    return jsonify({
        "ranking": results,
        "model_summary": coeffs
    })


@app.route("/scholarship/demand-forecast")
def scholarship_demand_forecast():
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    import datetime

    # =======================
    # LOAD & CLEAN DATA
    # =======================
    df = dependent.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {
        "province",
        "city",
        "householdmonthly income",
        "loan balance",
        "total ppi",
        "dependent_age"
    }
    missing = required - set(df.columns)
    if missing:
        return jsonify({"error": f"Missing required columns: {missing}"}), 400

    # Convert numeric fields
    def clean(col):
        return pd.to_numeric(
            df[col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
            errors="coerce"
        )

    df["income"] = clean("householdmonthly income")
    df["loan"] = clean("loan balance")
    df["ppi"] = clean("total ppi")
    df["age"] = clean("dependent_age")

    # Remove bad rows
    df = df.dropna(subset=["income", "loan", "ppi", "age", "province", "city"])

    # Exclude invalid poverty values
    df = df[df["ppi"] > 0]

    # =======================
    # ELIGIBLE DEPENDENT FLAG
    # =======================
    df["eligible"] = df["age"].apply(lambda a: 1 if 6 <= a <= 22 else 0)

    # =======================
    # NORMALIZATION
    # =======================
    max_income = df["income"].max() or 1
    max_loan = df["loan"].max() or 1
    max_ppi = df["ppi"].max() or 1

    df["income_score"] = 1 - (df["income"] / max_income)
    df["loan_score"] = df["loan"] / max_loan
    df["poverty_score"] = 1 - (df["ppi"] / max_ppi)

    # =======================
    # DEMAND PROXY (TARGET)
    # =======================
    df["demand_proxy"] = (
        df["eligible"] * 0.50 +
        df["income_score"] * 0.20 +
        df["loan_score"] * 0.20 +
        df["poverty_score"] * 0.10
    )

    # =======================
    # GROUP BY AREA
    # =======================
    area_df = df.groupby(["province", "city"]).agg({
        "eligible": "sum",
        "income_score": "mean",
        "loan_score": "mean",
        "poverty_score": "mean",
        "demand_proxy": "sum"
    }).reset_index()

    # =======================
    # ML MODELS
    # =======================

    X = area_df[["eligible", "income_score", "loan_score", "poverty_score"]]
    y = area_df["demand_proxy"]

    # --- Linear Regression (explainable model)
    lr = LinearRegression()
    lr.fit(X, y)

    # --- Random Forest (predictive model)
    rf = RandomForestRegressor(n_estimators=300, random_state=42)
    rf.fit(X, y)

    # Predict demand for each area
    area_df["predicted"] = rf.predict(X)

    # =======================
    # FORMAT RESPONSE
    # =======================
    results = []
    for _, row in area_df.iterrows():
        demand = float(row["predicted"])

        # Categorization logic
        if demand > area_df["predicted"].quantile(0.66):
            category = "High"
        elif demand > area_df["predicted"].quantile(0.33):
            category = "Medium"
        else:
            category = "Low"

        results.append({
            "province": row["province"],
            "city": row["city"],
            "predicted_scholarship_demand": int(round(demand)),
            "demand_category": category,
            "drivers": {
                "eligible_dependents": int(row["eligible"]),
                "income_score": round(float(row["income_score"]), 4),
                "loan_score": round(float(row["loan_score"]), 4),
                "poverty_score": round(float(row["poverty_score"]), 4)
            }
        })

    # Feature importance from the Random Forest
    feature_importance = {
        name: float(val)
        for name, val in zip(X.columns, rf.feature_importances_)
    }

    # Regression coefficients (for thesis interpretation)
    regression_coeffs = {
        "eligible": float(lr.coef_[0]),
        "income_score": float(lr.coef_[1]),
        "loan_score": float(lr.coef_[2]),
        "poverty_score": float(lr.coef_[3]),
        "intercept": float(lr.intercept_)
    }

    # =======================
    # FINAL JSON OUTPUT
    # =======================
    return jsonify({
        "forecast_horizon": "Next School Year",
        "area_demand": results,
        "model_summary": {
            "model_used": "RandomForestRegressor + LinearRegression",
            "feature_importance": feature_importance,
            "regression_coefficients": regression_coeffs
        },
        "metadata": {
            "total_areas_evaluated": len(area_df),
            "generated_on": datetime.datetime.now().strftime("%Y-%m-%d")
        }
    })





# ===========================
#           RUN
# ===========================
if __name__ == "__main__":
    app.run(debug=True, port=5000)



# from flask import Flask, request, session, jsonify, render_template, redirect, url_for
# from config import Config
# from datetime import timedelta
# from auth import authenticate_user
# import logging

# logging.basicConfig(
#     filename="login.log",
#     level=logging.INFO,
#     format="%(asctime)s - %(message)s"
# )



# app = Flask(__name__)
# app.config.from_object(Config)
# app.permanent_session_lifetime = timedelta(minutes=1)


# # ========== PAGES ==========

# @app.route("/")
# def home():
#     if "user_id" in session:
#         return redirect(url_for("dashboard"))
#     return redirect(url_for("login"))

# @app.route("/login")
# def login():
#     return render_template("login.html")

# @app.route("/analytics/dashboard")
# def main():
#     if "user_id" not in session:
#         return redirect(url_for("login"))
#     return render_template("main2.html", user_id=session["user_id"])


# # add for paging
# @app.route("/pages/<page>")
# def serve_page(page):
#     return render_template(f"pages/{page}")


# @app.route("/dashboard.html")
# def dashboard_section():
#     if "user_id" not in session:
#         return redirect(url_for("login"))
#     return render_template("dashboard.html")

# @app.route("/usermanagement.html")
# def usermanagement_section():
#     if "user_id" not in session:
#         return redirect(url_for("login"))
#     return render_template("usermanagement.html")

# # # end here




# # ========== API ROUTES ==========
# @app.route("/api/login", methods=["POST"])
# def api_login():
#     data = request.json
#     username = data.get("username")
#     password = data.get("password")

#     ip = request.remote_addr
#     user_id = authenticate_user(username, password)

#     if user_id:
#         session.permanent = True
#         session["user_id"] = user_id

#         # FILE LOGGING — SUCCESS
#         logging.info(f"LOGIN SUCCESS username={username} user_id={user_id} ip={ip}")

#         return jsonify({"status": "success"})
    
#     # FILE LOGGING — FAILED
#     logging.info(f"LOGIN FAILED username={username} ip={ip}")

#     return jsonify({"status": "error", "message": "Invalid credentials"}), 401


# @app.route("/api/check-session", methods=["GET"])
# def check_session():
#     if "user_id" in session:
#         return jsonify({"active": True})
#     return jsonify({"active": False}), 401

# @app.route("/api/logout", methods=["POST"])
# def api_logout():
#     session.clear()
#     return jsonify({"status": "success", "message": "Logged out successfully"})


# @app.route("/ppi/prepost-comparison")
# def prepost_comparison():
#     df = ppi.load_df()
#     df.columns = [c.lower().strip() for c in df.columns]

#     required = {"cid", "totalppi", "dopen"}
#     if not required.issubset(df.columns):
#         return jsonify({"error": "Missing required columns"}), 400

#     # CLEAN
#     df["totalppi"] = df["totalppi"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
#     df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
#     df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
#     df = df.dropna(subset=["totalppi", "dopen"])

#     # Convert to period YYYY-MM
#     df["year_month"] = df["dopen"].dt.to_period("M")

#     # -------------------------------
#     # READ PARAMETERS
#     # -------------------------------
#     m1 = request.args.get("m1")     # YYYY-MM
#     m2 = request.args.get("m2")     # YYYY-MM

#     months_available = sorted(df["year_month"].unique())
#     months_str = [str(m) for m in months_available]

#     if not m1 or not m2:
#         return jsonify({
#             "error": "Provide parameters m1 and m2 in YYYY-MM format.",
#             "months_available": months_str
#         }), 400

#     try:
#         m1 = ppi.pd.Period(m1, freq="M")
#         m2 = ppi.pd.Period(m2, freq="M")
#     except:
#         return jsonify({"error": "Invalid month format. Use YYYY-MM."}), 400

#     if m1 > m2:
#         return jsonify({"error": "m1 must be earlier than m2"}), 400

#     # -------------------------------
#     # PRE = very first row per client
#     # -------------------------------
#     pre = df.sort_values("dopen").groupby("cid").first().reset_index()
#     pre["band"] = pre["totalppi"].apply(ppi.ppi_band)  # uses your band function

#     # -------------------------------
#     # POST = rows inside selected range
#     # -------------------------------
#     post = df[(df["year_month"] >= m1) & (df["year_month"] <= m2)]

#     # remove PRE records (first records per client)
#     post = post.merge(pre[["cid", "dopen"]], on="cid", suffixes=("", "_first"))
#     post = post[post["dopen"] != post["dopen_first"]]

#     if post.empty:
#         return jsonify({
#             "error": "No POST records found inside selected range.",
#             "range": [str(m1), str(m2)]
#         }), 400

#     # -------------------------------
#     # POST aggregates by month
#     # -------------------------------
#     result_monthly = {}
#     months_in_range = sorted(post["year_month"].unique())

#     for m in months_in_range:
#         dm = post[post["year_month"] == m]
#         avg_ppi = float(dm["totalppi"].mean())
#         band_counts = dm["totalppi"].apply(ppi.ppi_band).value_counts().to_dict()

#         for b in ["0-20", "20-40", "40-60", "60-80", "80+"]:
#             band_counts.setdefault(b, 0)

#         result_monthly[str(m)] = {
#             "avg_ppi": avg_ppi,
#             "counts": band_counts
#         }

#     # PRE counts
#     pre_counts = pre["band"].value_counts().to_dict()
#     for b in ["0-20", "20-40", "40-60", "60-80", "80+"]:
#         pre_counts.setdefault(b, 0)

#     # -------------------------------
#     # FINAL RESULT
#     # -------------------------------
#     return jsonify({
#         "range": {
#             "start": str(m1),
#             "end": str(m2)
#         },
#         "months_available": months_str,
#         "pre_counts": pre_counts,
#         "months_in_range": [str(m) for m in months_in_range],
#         "post_monthly": result_monthly
#     })






# @app.route("/ppi/improvement-stats")
# def improvement_stats():
#     df = ppi.load_df()
#     df.columns = [c.lower().strip() for c in df.columns]

#     required = {"cid", "totalppi", "dopen"}
#     if not required.issubset(df.columns):
#         return jsonify({"error": "Missing required columns (cid, dopen, totalppi)."}), 400

#     df["totalppi"] = (
#         df["totalppi"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
#     )
#     df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")

#     df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
#     df = df.dropna(subset=["dopen", "totalppi"])

#     df["year"] = df["dopen"].dt.year

#     y1 = request.args.get("year1")
#     y2 = request.args.get("year2")

#     all_years = sorted(df["year"].unique())

#     if not y1 or not y2:
#         if len(all_years) < 2:
#             return jsonify({"error": "Not enough years in dataset."}), 400
#         y1, y2 = all_years[-2], all_years[-1]
#     else:
#         y1, y2 = int(y1), int(y2)

#     grouped = df.groupby(["cid", "year"])["totalppi"].mean().reset_index()
#     pivot = grouped.pivot(index="cid", columns="year", values="totalppi")

#     if y1 not in pivot.columns or y2 not in pivot.columns:
#         return jsonify({"error": "Missing data for one or both years.",
#                         "years_available": [int(y) for y in all_years]}), 400

#     pivot = pivot.dropna(subset=[y1, y2], how="any")

#     total_clients = int(len(pivot))

#     improved = int((pivot[y2] > pivot[y1]).sum())
#     same = int((pivot[y2] == pivot[y1]).sum())
#     worsened = int((pivot[y2] < pivot[y1]).sum())

#     return jsonify({
#         "year1": int(y1),
#         "year2": int(y2),
#         "years_available": [int(y) for y in all_years],
#         "total_clients": total_clients,
#         "improved": improved,
#         "same": same,
#         "worsened": worsened,
#         "improved_pct": float(round(improved / total_clients * 100, 2)) if total_clients else 0.0,
#         "same_pct": float(round(same / total_clients * 100, 2)) if total_clients else 0.0,
#         "worsened_pct": float(round(worsened / total_clients * 100, 2)) if total_clients else 0.0
#     })

# if __name__ == "__main__":
#     app.run(debug=True)


# @app.route('/ppi/descriptive', methods=['POST'])
# def descriptive_analysis():
#     """
#     Input: { "roof": "strong", "children": "many", "tv": "no" }
#     Output: Current Score, Segment, and Probability
#     """
#     data = request.json
#     score = ppi.calculate_ppi_score(data)
#     probability = ppi.get_poverty_probability(score)
    
#     # Segment Logic
#     if score < 20:
#         segment = "Very Poor"
#     elif score < 50:
#         segment = "Enterprising Poor"
#     else:
#         segment = "Non-Poor / Graduate"

#     return jsonify({
#         "type": "Descriptive",
#         "score": score,
#         "poverty_probability": probability,
#         "segment": segment,
#         "message": f"Client score is {score}, placing them in the {segment} category."
#     })



# # --- 2. PREDICTIVE ANALYSIS ENGINE ---
# # Goal: Forecast next year's score based on history
# @app.route('/ppi/predictive', methods=['POST'])
# def predictive_analysis():
#     """
#     Input: { "history": [10, 15, 22] }  (Scores from Year 1, 2, 3)
#     Output: Predicted Score for Year 4 based on the average rate of change.
#     """
#     data = request.json
#     history = data.get('history', [])
    
#     if len(history) < 2:
#         return jsonify({"error": "Need at least 2 scores to calculate the average rate of change."}), 400

#     # Calculate the difference (improvement/decline) between each consecutive score
#     # Example: [10, 15, 22] -> differences = [5, 7]
#     differences = [history[i] - history[i-1] for i in range(1, len(history))]

#     # Calculate the average annual improvement (rate of change)
#     # This is the prediction rule based purely on score progression.
#     average_improvement_rate = sum(differences) / len(differences)

#     # Predict the next score by adding the average rate of change to the last known score
#     predicted_score = history[-1] + average_improvement_rate
    
#     # Determine the trend based on the calculated rate
#     if average_improvement_rate > 0.1:
#         trend = "improving"
#     elif average_improvement_rate < -0.1:
#         trend = "declining"
#     else:
#         trend = "stagnant" # Use a small tolerance for flat trends

#     return jsonify({
#         "type": "Predictive",
#         "historical_scores": history,
#         "predicted_next_score": round(predicted_score, 1),
#         "average_improvement_rate": round(average_improvement_rate, 2),
#         "trend": trend
#     })

# # --- 3. PRESCRIPTIVE ANALYSIS ENGINE ---
# # Goal: Recommend actions based on Descriptive (current) and Predictive (future)
# @app.route('/ppi/prescriptive', methods=['POST'])
# def prescriptive_analysis():
#     """
#     Input: { "current_score": 25, "predicted_score": 30 }
#     Output: Recommended Products/Interventions
#     """
#     data = request.json
#     current_score = data.get('current_score')
#     predicted_score = data.get('predicted_score')

#     recommendations = []

#     # Rule Engine
#     if current_score < 20:
#         # Segment: Very Poor
#         recommendations.append("Enroll in 'MaHP' (Microfinance and Health Protection)")
#         recommendations.append("Grant 'Educational Scholarship' for children")
#     elif current_score < 50:
#         # Segment: Enterprising Poor
#         recommendations.append("Offer 'Sikap 1' Micro-loan")
#         recommendations.append("Suggest 'Weekly Savings' buildup")
#     else:
#         # Segment: Graduate
#         recommendations.append("Upsell to SME Bank Loan")
#         recommendations.append("Offer Insurance/Investment products")

#     # Trend-based prescriptions
#     if predicted_score > current_score + 5:
#         recommendations.append("High Potential Client: Invite to leadership training")
#     elif predicted_score < current_score:
#         recommendations.append("Risk Alert: Schedule Account Officer visit for support")

#     return jsonify({
#         "type": "Prescriptive",
#         "analysis": {
#             "current": current_score,
#             "forecast": predicted_score
#         },
#         "recommended_actions": recommendations
#     })


# @app.route("/ppi/poverty-changes")
# def ppi_poverty_changes():
#     df = ppi.load_df()
#     df.columns = [c.lower().strip() for c in df.columns]

#     required = {"cid", "totalppi", "dopen"}
#     missing = required - set(df.columns)
#     if missing:
#         return jsonify({"error": f"Missing columns: {list(missing)}"}), 400

#     # clean data
#     df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
#     df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
#     df = df.dropna(subset=["totalppi", "dopen"])

#     # exclude zeros and invalid PPI
#     df = df[df["totalppi"] > 0]

#     # only clients with multiple records
#     counts = df.groupby("cid")["totalppi"].count()
#     valid_clients = counts[counts >= 2].index
#     df = df[df["cid"].isin(valid_clients)]

#     if df.empty:
#         return jsonify({"error": "No clients have multiple PPI entries"}), 400

#     # sort
#     df_sorted = df.sort_values("dopen")

#     # PRE
#     pre = df_sorted.groupby("cid").first().reset_index()
#     pre = pre.set_index("cid")

#     # POST
#     post = df_sorted.groupby("cid").last().reset_index()
#     post = post.set_index("cid")

#     # Compute poverty likelihood
#     def pov(score):
#         return max(0, min(100, 100 - (float(score) * 1.3)))

#     rows = []

#     for cid in pre.index:
#         pre_ppi = float(pre.loc[cid, "totalppi"])
#         post_ppi = float(post.loc[cid, "totalppi"])

#         pre_pct = pov(pre_ppi)
#         post_pct = pov(post_ppi)
#         change = round(post_pct - pre_pct, 2)

#         if change < 0:
#             movement = "Improved"
#         elif change > 0:
#             movement = "Worsened"
#         else:
#             movement = "Same"

#         rows.append({
#             "cid": cid,
#             "pre_ppi": pre_ppi,
#             "pre_poverty_pct": round(pre_pct, 2),
#             "post_ppi": post_ppi,
#             "post_poverty_pct": round(post_pct, 2),
#             "change_pct": change,
#             "movement": movement
#         })

#     return jsonify(rows)