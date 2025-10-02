# streamlit_dashboard/app.py
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

BASE = "/content/drive/MyDrive/investment_ai"
REPORTS_DIR = f"{BASE}/reports"

st.set_page_config(page_title="🧠 Agente Inversor AI", layout="wide")
st.title("🧠 Dashboard de Inversión Autónoma")

# --- Sidebar ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Nodejs_logo.svg/1200px-Nodejs_logo.svg.png", width=100)
st.sidebar.header("🧠 Agente Inversor AI")
st.sidebar.markdown("---")
st.sidebar.write("Sistema multiagente autónomo para gestión de cartera.")

# --- Resumen ejecutivo ---
st.header("📊 Resumen Ejecutivo")

# Cargar datos clave
pf_path = f"{REPORTS_DIR}/portfolio_enriched_final.csv"
pf = pd.read_csv(pf_path) if os.path.exists(pf_path) else pd.DataFrame()

risk_path = f"{REPORTS_DIR}/risk_dashboard_latest.json"
risk = {}
if os.path.exists(risk_path):
    with open(risk_path) as f:
        risk = json.load(f)

market_path = f"{REPORTS_DIR}/market_regime_latest.json"
market = {}
if os.path.exists(market_path):
    with open(market_path) as f:
        market = json.load(f)

liquidity_path = f"{REPORTS_DIR}/liquidity_regime_latest.json"
liquidity = {}
if os.path.exists(liquidity_path):
    with open(liquidity_path) as f:
        liquidity = json.load(f)

# Métricas clave
col1, col2, col3, col4 = st.columns(4)
with col1:
    total = pf["importe_actual_eur"].sum() if not pf.empty else 0
    st.metric("Valor Total", f"€{total:,.0f}")
with col2:
    drawdown = risk.get("drawdown", "N/A")
    st.metric("Drawdown", f"{drawdown}")
with col3:
    alpha = risk.get("alpha", "N/A")
    st.metric("Alpha vs S&P 500", f"{alpha}")
with col4:
    regimen = market.get("regimen", "N/A")
    st.metric("Régimen de Mercado", regimen)

# Cartera por región
if not pf.empty:
    exp_region = pf.groupby("region")["importe_actual_eur"].sum().to_frame()
    exp_region["peso_%"] = exp_region["importe_actual_eur"] / total * 100
    st.subheader("🌍 Exposición por Región")
    st.bar_chart(exp_region["peso_%"])

# Últimas señales
st.subheader("🔔 Últimas Señales")
signals_path = f"{BASE}/data/signals_emitted.csv"
if os.path.exists(signals_path):
    signals = pd.read_csv(signals_path).tail(5)
    st.dataframe(signals[["fecha_emision", "agente", "recomendacion"]])
else:
    st.info("No hay señales registradas aún.")

# Footer
st.markdown("---")
st.caption(f"📅 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}")