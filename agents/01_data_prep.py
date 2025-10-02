#!/usr/bin/env python
# coding: utf-8

# In[2]:


# ============================================
#  DATA AGENT
# 01_data_prep_personalized.ipynb - Precios de TU cartera
# ============================================
get_ipython().system('pip -q install yfinance pandas pyarrow')
import os
import pandas as pd
import numpy as np

# Directorios base para rutas relativas
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
REPORTS_DIR = os.path.join(BASE_DIR, "..", "reports")
CONFIG_DIR = os.path.join(BASE_DIR, "..", "config")
AGENTS_DIR = os.path.join(BASE_DIR, "..", "agents")


import os
import pandas as pd
import numpy as np

# Directorios base para rutas relativas
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
REPORTS_DIR = os.path.join(BASE_DIR, "..", "reports")
CONFIG_DIR = os.path.join(BASE_DIR, "..", "config")


import os
import pandas as pd
import yfinance as yf
import json
from google.colab import auth, drive

# Montar Drive y autenticar
drive.mount('/content/drive', force_remount=False)
auth.authenticate_user()

import gspread
from google.auth import default
from gspread_dataframe import get_as_dataframe

creds, _ = default()
gc = gspread.authorize(creds)

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "data": f"{BASE}/data",
    "raw": f"{BASE}/data/raw",
    "clean": f"{BASE}/data/clean",
    "reports": f"{BASE}/reports"
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# --- Leer historial de compras desde Google Sheet ---
try:
    sh = gc.open("positions_history")
    ws = sh.sheet1
    positions = get_as_dataframe(ws, evaluate_formulas=True, header=0).dropna(how="all")
    print(f"✅ Historial cargado: {positions.shape[0]} posiciones")
except Exception as e:
    raise Exception(f"Error al abrir 'positions_history': {e}")

# --- Extraer tickers únicos ---
tickers_to_download = set()
for _, row in positions.iterrows():
    ticker = str(row.get("ticker_yf", "")).strip()
    if ticker not in ["", "-", "CASH", "ACN_RSU"]:
        tickers_to_download.add(ticker)

tickers_to_download = sorted(list(tickers_to_download))

if not tickers_to_download:
    raise ValueError("❌ No hay tickers válidos para descargar. Revisa tu Google Sheet 'positions_history'.")

print(f"🔍 Tickers a descargar: {tickers_to_download}")

# --- Descargar precios ---
print("📥 Descargando precios históricos...")
prices = yf.download(
    tickers_to_download,
    start="2020-01-01",
    end=None,
    interval="1d",
    auto_adjust=True,
    progress=False
)

# --- Normalizar a DataFrame de cierres ---
if len(tickers_to_download) == 1:
    ticker = tickers_to_download[0]
    if isinstance(prices.columns, pd.MultiIndex):
        prices = prices['Close']
    else:
        if 'Close' in prices.columns:
            prices = prices[['Close']].rename(columns={'Close': ticker})
        else:
            prices = prices.to_frame(name=ticker)
else:
    if isinstance(prices.columns, pd.MultiIndex):
        prices = prices['Close']
    else:
        # Caso inesperado: forzar DataFrame vacío
        prices = pd.DataFrame(index=prices.index)

prices.index.name = "date"
prices = prices.dropna(how="all", axis=1)

# --- Guardar ---
RAW_PATH = f"{DIRS['raw']}/my_portfolio_prices.parquet"
prices.to_parquet(RAW_PATH)
print(f"✅ Precios guardados en: {RAW_PATH}")

# --- Limpieza básica ---
def clean_prices(df, min_days=100):
    df = df.ffill().bfill()
    valid_cols = [c for c in df.columns if df[c].dropna().shape[0] >= min_days]
    return df[valid_cols]

prices_clean = clean_prices(prices)
CLEAN_PATH = f"{DIRS['clean']}/my_portfolio_prices_clean.parquet"
prices_clean.to_parquet(CLEAN_PATH)
print(f"✅ Precios limpios guardados en: {CLEAN_PATH}")

# --- Metadatos (opcional pero útil) ---
meta = {
    "last_update": pd.Timestamp.now().isoformat(),
    "tickers": tickers_to_download,
    "raw_path": RAW_PATH,
    "clean_path": CLEAN_PATH
}
with open(f"{DIRS['raw']}/portfolio_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

# --- Mostrar muestra ---
print("\n📅 Últimos precios:")
print(prices_clean.tail().to_string())

# --- VERIFICAR SALIDAS ---
required_files = [RAW_PATH, CLEAN_PATH]
for f in required_files:
    if not os.path.exists(f):
        raise RuntimeError(f"❌ Archivo no generado: {f}")
    else:
        print(f"✅ {os.path.basename(f)} verificado.")

