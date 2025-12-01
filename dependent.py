from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import os


CSV_PATH = "data/scholar/Dependent.csv"

def load_df():
    try:
        return pd.read_csv(CSV_PATH, encoding="latin1")
    except:
        return pd.read_csv(CSV_PATH, encoding="utf-8", errors="ignore")
