# streamlit_dashboard/pages/3_Macro.py
import streamlit as st
import json
import os

BASE = "/content/drive/MyDrive/investment_ai"
REPORTS_DIR = f"{BASE}/reports"

st.title("🌍 Análisis Macro")

# Liquidez
liquidity_path = f"{REPORTS_DIR}/liquidity_regime_latest.json"
if os.path.exists(liquidity_path):
    with open(liquidity_path) as f:
        liquidity = json.load(f)
    st.subheader("💧 Régimen de Liquidez")
    st.json(liquidity)
else:
    st.info("No hay análisis de liquidez.")

# Mercado
market_path = f"{REPORTS_DIR}/market_regime_latest.json"
if os.path.exists(market_path):
    with open(market_path) as f:
        market = json.load(f)
    st.subheader("💹 Régimen de Mercado")
    st.json(market)
else:
    st.info("No hay análisis de mercado.")