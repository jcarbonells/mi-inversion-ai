# streamlit_dashboard/pages/2_Senales.py
import streamlit as st
import pandas as pd
import os

BASE = "/content/drive/MyDrive/investment_ai"
REPORTS_DIR = f"{BASE}/reports"

st.title("🔔 Señales")

# FX
fx_path = f"{REPORTS_DIR}/fx_hedge_signal.csv"
if os.path.exists(fx_path):
    fx = pd.read_csv(fx_path)
    st.subheader("💱 Señales FX")
    st.dataframe(fx)
else:
    st.info("No hay señales FX.")

# Cuantitativas
quant_path = f"{REPORTS_DIR}/quant_signals.csv"
if os.path.exists(quant_path):
    quant = pd.read_csv(quant_path)
    st.subheader("📈 Señales Cuantitativas")
    st.dataframe(quant)
else:
    st.info("No hay señales cuantitativas.")