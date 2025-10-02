# streamlit_dashboard/pages/5_Rendimiento.py
import streamlit as st
import json
import os

BASE = "/content/drive/MyDrive/investment_ai"
REPORTS_DIR = f"{BASE}/reports"

st.title("📊 Rendimiento de Agentes")

perf_path = f"{REPORTS_DIR}/performance_summary.json"
if os.path.exists(perf_path):
    with open(perf_path) as f:
        perf = json.load(f)
    st.json(perf)
else:
    st.info("No hay datos de rendimiento.")