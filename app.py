from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from config import Config
from datetime import timedelta
from auth import authenticate_user
from user import get_all_users
from ph_locations_loader import get_coords
import numpy as np
from sklearn.linear_model import LinearRegression


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


#analytics.init(CSV_PATH)
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
    df = ppi.load_df()

    # Normalize columns
    df.columns = [c.lower().strip() for c in df.columns]

    # Must have area, unit, totalppi
    if not {"area", "unit", "totalppi"}.issubset(df.columns):
        return jsonify([])

    # Clean totalppi
    df["totalppi"] = (
        df["totalppi"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    )
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df = df.dropna(subset=["totalppi"])

    # Group by AREA + UNIT
    grouped = (
        df.groupby(["area", "unit"], dropna=False)["totalppi"]
        .mean()
        .reset_index()
    )

    # Build API output
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
            "lng": lng
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

    return jsonify({"labels": labels, "values": values, "group": group})


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
        "worsened_pct": float(round(worsened / total_clients * 100, 2)) if total_clients else 0.0
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
        "worsened_pct": float(round(worsened / total_clients * 100, 2)) if total_clients else 0.0
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

    # -------------------------
    # RETURN CLEAN JSON
    # -------------------------
    return jsonify({
    "total_clients": int(len(pre)),
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


@app.route('/ppi/descriptive', methods=['POST'])
def descriptive_analysis():
    """
    Input: { "roof": "strong", "children": "many", "tv": "no" }
    Output: Current Score, Segment, and Probability
    """
    data = request.json
    score = ppi.calculate_ppi_score(data)
    probability = ppi.get_poverty_probability(score)
    
    # Segment Logic
    if score < 20:
        segment = "Very Poor"
    elif score < 50:
        segment = "Enterprising Poor"
    else:
        segment = "Non-Poor / Graduate"

    return jsonify({
        "type": "Descriptive",
        "score": score,
        "poverty_probability": probability,
        "segment": segment,
        "message": f"Client score is {score}, placing them in the {segment} category."
    })



# --- 2. PREDICTIVE ANALYSIS ENGINE ---
# Goal: Forecast next year's score based on history
@app.route('/ppi/predictive', methods=['POST'])
def predictive_analysis():
    """
    Input: { "history": [10, 15, 22] }  (Scores from Year 1, 2, 3)
    Output: Predicted Score for Year 4 based on the average rate of change.
    """
    data = request.json
    history = data.get('history', [])
    
    if len(history) < 2:
        return jsonify({"error": "Need at least 2 scores to calculate the average rate of change."}), 400

    # Calculate the difference (improvement/decline) between each consecutive score
    # Example: [10, 15, 22] -> differences = [5, 7]
    differences = [history[i] - history[i-1] for i in range(1, len(history))]

    # Calculate the average annual improvement (rate of change)
    # This is the prediction rule based purely on score progression.
    average_improvement_rate = sum(differences) / len(differences)

    # Predict the next score by adding the average rate of change to the last known score
    predicted_score = history[-1] + average_improvement_rate
    
    # Determine the trend based on the calculated rate
    if average_improvement_rate > 0.1:
        trend = "improving"
    elif average_improvement_rate < -0.1:
        trend = "declining"
    else:
        trend = "stagnant" # Use a small tolerance for flat trends

    return jsonify({
        "type": "Predictive",
        "historical_scores": history,
        "predicted_next_score": round(predicted_score, 1),
        "average_improvement_rate": round(average_improvement_rate, 2),
        "trend": trend
    })

# --- 3. PRESCRIPTIVE ANALYSIS ENGINE ---
# Goal: Recommend actions based on Descriptive (current) and Predictive (future)
@app.route('/ppi/prescriptive', methods=['POST'])
def prescriptive_analysis():
    """
    Input: { "current_score": 25, "predicted_score": 30 }
    Output: Recommended Products/Interventions
    """
    data = request.json
    current_score = data.get('current_score')
    predicted_score = data.get('predicted_score')

    recommendations = []

    # Rule Engine
    if current_score < 20:
        # Segment: Very Poor
        recommendations.append("Enroll in 'MaHP' (Microfinance and Health Protection)")
        recommendations.append("Grant 'Educational Scholarship' for children")
    elif current_score < 50:
        # Segment: Enterprising Poor
        recommendations.append("Offer 'Sikap 1' Micro-loan")
        recommendations.append("Suggest 'Weekly Savings' buildup")
    else:
        # Segment: Graduate
        recommendations.append("Upsell to SME Bank Loan")
        recommendations.append("Offer Insurance/Investment products")

    # Trend-based prescriptions
    if predicted_score > current_score + 5:
        recommendations.append("High Potential Client: Invite to leadership training")
    elif predicted_score < current_score:
        recommendations.append("Risk Alert: Schedule Account Officer visit for support")

    return jsonify({
        "type": "Prescriptive",
        "analysis": {
            "current": current_score,
            "forecast": predicted_score
        },
        "recommended_actions": recommendations
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

@app.route("/ppi/poverty-changes")
def ppi_poverty_changes():
    df = ppi.load_df()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"cid", "totalppi", "dopen"}
    missing = required - set(df.columns)
    if missing:
        return jsonify({"error": f"Missing columns: {list(missing)}"}), 400

    # clean data
    df["totalppi"] = ppi.pd.to_numeric(df["totalppi"], errors="coerce")
    df["dopen"] = ppi.pd.to_datetime(df["dopen"], errors="coerce")
    df = df.dropna(subset=["totalppi", "dopen"])

    # exclude zeros and invalid PPI
    df = df[df["totalppi"] > 0]

    # only clients with multiple records
    counts = df.groupby("cid")["totalppi"].count()
    valid_clients = counts[counts >= 2].index
    df = df[df["cid"].isin(valid_clients)]

    if df.empty:
        return jsonify({"error": "No clients have multiple PPI entries"}), 400

    # sort
    df_sorted = df.sort_values("dopen")

    # PRE
    pre = df_sorted.groupby("cid").first().reset_index()
    pre = pre.set_index("cid")

    # POST
    post = df_sorted.groupby("cid").last().reset_index()
    post = post.set_index("cid")

    # Compute poverty likelihood
    def pov(score):
        return max(0, min(100, 100 - (float(score) * 1.3)))

    rows = []

    for cid in pre.index:
        pre_ppi = float(pre.loc[cid, "totalppi"])
        post_ppi = float(post.loc[cid, "totalppi"])

        pre_pct = pov(pre_ppi)
        post_pct = pov(post_ppi)
        change = round(post_pct - pre_pct, 2)

        if change < 0:
            movement = "Improved"
        elif change > 0:
            movement = "Worsened"
        else:
            movement = "Same"

        rows.append({
            "cid": cid,
            "pre_ppi": pre_ppi,
            "pre_poverty_pct": round(pre_pct, 2),
            "post_ppi": post_ppi,
            "post_poverty_pct": round(post_pct, 2),
            "change_pct": change,
            "movement": movement
        })

    return jsonify(rows)










@app.route("/ppi/impact-explorer")
def impact_explorer():
    df = ppi.load_df()
    region = request.args.get("region")
    program = request.args.get("program")
    income = request.args.get("income")

    temp = df.copy()

    if region and "region" in temp.columns:
        temp = temp[temp["region"] == region]

    if program and "program_type" in temp.columns:
        temp = temp[temp["program_type"] == program]

    if income and "income_level" in temp.columns:
        temp = temp[temp["income_level"] == income]

    return jsonify(temp.to_dict(orient="records"))


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
