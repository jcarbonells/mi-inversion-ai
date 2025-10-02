# streamlit_dashboard/pages/1_Cartera.py
import streamlit as st
import pandas as pd
import os

BASE = "/content/drive/MyDrive/investment_ai"
REPORTS_DIR = f"{BASE}/reports"

st.title("💼 Cartera")

pf_path = f"{REPORTS_DIR}/portfolio_enriched_final.csv"
if os.path.exists(pf_path):
    pf = pd.read_csv(pf_path)
    st.dataframe(pf)
else:
    st.error("❌ No se encontró portfolio_enriched_final.csv")

# Gráficos
if not pf.empty:
    st.subheader("📊 Exposición por Categoría")
    exp_cat = pf.groupby("categoria")["importe_actual_eur"].sum()
    st.bar_chart(exp_cat)

    st.subheader("🌍 Exposición por Región")
    exp_region = pf.groupby("region")["importe_actual_eur"].sum()
    st.bar_chart(exp_region)