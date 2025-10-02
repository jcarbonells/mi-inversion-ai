# streamlit_dashboard/pages/4_GenAI.py
import streamlit as st
import os

BASE = "/content/drive/MyDrive/investment_ai"
REPORTS_DIR = f"{BASE}/reports"

st.title("🧠 Análisis con GenAI")

# Último análisis
ai_path = f"{REPORTS_DIR}/ai_dashboard_summary_*.md"
import glob
files = glob.glob(ai_path)
if files:
    latest = max(files, key=os.path.getctime)
    with open(latest) as f:
        content = f.read()
    st.markdown(content)
else:
    st.info("No hay análisis con GenAI.")