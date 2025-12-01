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



