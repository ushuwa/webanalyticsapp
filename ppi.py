from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import os

# bp = Blueprint(
#     "ppi",
#     __name__,
#     url_prefix="/ppi",
#     template_folder="templates/ppi",
#     static_folder="static/ppi"
# )

CSV_PATH = "data/ppi/PPI.csv"

def load_df():
    try:
        return pd.read_csv(CSV_PATH, encoding="latin1")
    except:
        return pd.read_csv(CSV_PATH, encoding="utf-8", errors="ignore")

def compute_poverty_likelihood(score):
    try:
        s = float(score)
    except:
        s = 0
    return max(0, min(100, 100 - (s * 1.3)))


 # Deterministic coordinate generator
def get_coords(area, unit):
        import hashlib
        key = f"{area.upper()}||{unit.upper()}"
        h = hashlib.md5(key.encode()).hexdigest()

        # PH bounds
        lat_min, lat_max = 5.0, 19.0
        lng_min, lng_max = 116.0, 126.0

        lat_seed = int(h[:8], 16) % 1000000
        lng_seed = int(h[8:16], 16) % 1000000

        lat = lat_min + (lat_max - lat_min) * (lat_seed / 1_000_000)
        lng = lng_min + (lng_max - lng_min) * (lng_seed / 1_000_000)

        return round(lat, 6), round(lng, 6)


def ppi_band(score):
    s = float(score)

    if s < 20:
        return "0-20"
    elif s < 40:
        return "20-40"
    elif s < 60:
        return "40-60"
    elif s < 80:
        return "60-80"
    elif s < 90:
        return "80-90"
    elif s <= 100:
        return "90-100"
    else:
        return "100+"

def calculate_ppi_score(data):
    score = 0
    
    # Roof Logic
    if data.get('roof') == 'strong':
        score += 12
    
    # Children Logic
    if data.get('children') == 'few': # 0-1 children
        score += 15
        
    # TV Logic
    if data.get('tv') == 'yes':
        score += 8
        
    return score

def get_poverty_probability(score):
    # Simplified lookup based on your HTML table
    if score < 10: return 85
    if score < 20: return 60
    if score < 30: return 35
    return 10

def compute_insights_ppi(df):
    import pandas as pd

    df = df.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"cid", "totalppi", "dopen", "area"}
    if not required.issubset(df.columns):
        raise KeyError(f"Missing columns: {required - set(df.columns)}")

    # clean PPI
    df["totalppi"] = pd.to_numeric(df["totalppi"], errors="coerce")
    df["dopen"] = pd.to_datetime(df["dopen"], errors="coerce")
    df = df.dropna(subset=["totalppi", "dopen", "area"])
    df = df[df["totalppi"] > 0]

    # PRE / POST
    df_sorted = df.sort_values("dopen")
    pre = df_sorted.groupby("cid").first()
    post = df_sorted.groupby("cid").last()

    post["area"] = pre["area"]

    # Poverty calculation
    def pov(x):
        return max(0, min(100, 100 - (float(x) * 1.3)))

    pre["poverty"] = pre["totalppi"].apply(pov)
    post["poverty"] = post["totalppi"].apply(pov)

    post["change"] = post["poverty"] - pre["poverty"]
    post["movement"] = post["change"].apply(
        lambda x: "Improved" if x < 0 else ("Worsened" if x > 0 else "Same")
    )

    # region metrics
    pre_area = pre.groupby("area")["poverty"].mean().rename("pre_avg")
    post_area = post.groupby("area")["poverty"].mean().rename("post_avg")

    moved_area = post.groupby("area")["movement"].value_counts().unstack(fill_value=0)

    df_reg = pd.concat([pre_area, post_area], axis=1).fillna(0)
    df_reg["total"] = moved_area.sum(axis=1)
    df_reg["improved_pct"] = (moved_area.get("Improved", 0) / df_reg["total"]) * 100
    df_reg["worsened_pct"] = (moved_area.get("Worsened", 0) / df_reg["total"]) * 100

    # heuristic
    df_reg["support_score"] = (
        df_reg["post_avg"] - df_reg["pre_avg"]
    ) + (df_reg["worsened_pct"] / 10)

    df_reg = df_reg.reset_index()
    df_reg = df_reg.sort_values("support_score", ascending=False).head(5)

    regions_output = [
        {
            "area": r["area"],
            "pre_avg": round(float(r["pre_avg"]), 2),
            "post_avg": round(float(r["post_avg"]), 2),
            "improved_pct": round(float(r["improved_pct"]), 2),
            "worsened_pct": round(float(r["worsened_pct"]), 2),
            "support_score": round(float(r["support_score"]), 3)
        }
        for _, r in df_reg.iterrows()
    ]

    return {
        "regions_needing_support": regions_output,
        "total_clients": int(len(pre))
    }


