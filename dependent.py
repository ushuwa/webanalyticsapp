from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import os


CSV_PATH = "data/scholar/Dependent.csv"

def load_df():
    try:
        return pd.read_csv(CSV_PATH, encoding="latin1")
    except:
        return pd.read_csv(CSV_PATH, encoding="utf-8", errors="ignore")



def compute_segment_insights(df_dep):
    import pandas as pd

    df = df_dep.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    # Required fields
    required = {"cid", "householdmonthly income"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Dependent.csv missing columns: {missing}")

    # CLEAN income
    df["householdmonthly income"] = df["householdmonthly income"].astype(str).str.strip()

    null_values = ["", "none", "null", "nan", "[null]", "nil", "0", "unknown"]
    df = df[~df["householdmonthly income"].str.lower().isin(null_values)]
    df = df[df["householdmonthly income"].notna()]

    # Keep one row per cid (latest)
    df_sorted = df.sort_values("cid")
    df_unique = df_sorted.groupby("cid").last().reset_index()

    # Define improvement rule (customize)
    def is_improved(income):
        income = income.upper()
        if income in ["MID", "HIGH", "15000-20000", "20000-30000", "ABOVE 15000"]:
            return True
        return False

    df_unique["improved"] = df_unique["householdmonthly income"].apply(
        lambda x: 1 if is_improved(x) else 0
    )

    # Count totals per segment
    totals = df_unique.groupby("householdmonthly income")["cid"].count().rename("total")

    # Count improved per segment
    improved_counts = df_unique.groupby("householdmonthly income")["improved"].sum().rename("improved")

    # Merge into a table
    merged = pd.concat([totals, improved_counts], axis=1).fillna(0)

    # Compute improvement rate
    merged["improvement_rate"] = (merged["improved"] / merged["total"]) * 100
    merged = merged.reset_index()

    # Build clean list
    result = []
    for _, row in merged.iterrows():
        result.append({
            "segment": row["householdmonthly income"],
            "total": int(row["total"]),
            "improved": int(row["improved"]),
            "improvement_rate": round(float(row["improvement_rate"]), 2)
        })

    # Sort by improvement rate
    result = sorted(result, key=lambda x: x["improvement_rate"], reverse=True)

    # Only top 5
    return {
        "top_improving_segments": result[:5],
        "total_segments_analyzed": len(df_unique)
    }






def compute_segment_insights_city(df_dep):
    import pandas as pd

    df = df_dep.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    # Required fields
    required = {"cid", "city"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Dependent.csv missing columns: {missing}")

    # CLEAN city
    df["city"] = df["city"].astype(str).str.strip()

    null_values = ["", "none", "null", "nan", "[null]", "nil", "0", "unknown"]
    df = df[~df["city"].str.lower().isin(null_values)]
    df = df[df["city"].notna()]

    # Deduplicate per cid (use latest row)
    df_sorted = df.sort_values("cid")
    df_unique = df_sorted.groupby("cid").last().reset_index()

    # --------------------------
    # IMPROVEMENT LOGIC
    # --------------------------
    # You decide the meaning of "Improved" based on business rule.
    # Since Dependent.csv may not contain PPI improvement,
    # we assume SEGMENT improvement based on some attribute.

    # If you want to use PPI improvements, tell me and I will link to PPI.csv.

    # For now, we assign a dummy improvement flag to illustrate:
    # Example rule:
    # Cities with alphabetically earlier names = more improved
    # Replace with actual logic when available.

    def is_improved(city_name):
        # SAMPLE RULE — replace with your real logic later
        first_letter = city_name[0].upper()
        # Cities starting with A–M = "Improved"
        return first_letter <= "M"

    df_unique["improved"] = df_unique["city"].apply(
        lambda x: 1 if is_improved(x) else 0
    )

    # --------------------------
    # GROUP BY CITY
    # --------------------------

    totals = df_unique.groupby("city")["cid"].count().rename("total")
    improved_counts = df_unique.groupby("city")["improved"].sum().rename("improved")

    merged = pd.concat([totals, improved_counts], axis=1).fillna(0)
    merged["improvement_rate"] = (merged["improved"] / merged["total"]) * 100

    merged = merged.reset_index()

    # Build final list
    result = []
    for _, row in merged.iterrows():
        result.append({
            "city": row["city"],
            "total": int(row["total"]),
            "improved": int(row["improved"]),
            "improvement_rate": round(float(row["improvement_rate"]), 2)
        })

    # sort DESC by improvement rate
    result = sorted(result, key=lambda x: x["improvement_rate"], reverse=True)

    # Return top 5 cities
    return {
        "top_improving_segments": result[:5],
        "total_segments_analyzed": len(df_unique)
    }


