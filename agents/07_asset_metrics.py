#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# ============================================
# 07_asset_metrics.ipynb - Métricas por activo (MEJORADO + CONTRATO)
# ============================================

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
import numpy as np
import yfinance as yf
import re
import json
from google.colab import auth, drive

# Instalación segura
try:
    import gspread
    from gspread_dataframe import get_as_dataframe
except ImportError:
    get_ipython().system('pip -q install yfinance pandas gspread gspread-dataframe')
    import gspread
    from gspread_dataframe import get_as_dataframe

drive.mount('/content/drive', force_remount=False)
auth.authenticate_user()

from google.auth import default
creds, _ = default()
gc = gspread.authorize(creds)

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "reports": f"{BASE}/reports"
}

# --- 1. Leer historial de compras ---
try:
    sh = gc.open("positions_history")
    ws = sh.sheet1
    positions = get_as_dataframe(ws, evaluate_formulas=True, header=0).dropna(how="all")
    print(f"✅ Historial cargado: {positions.shape[0]} posiciones")
except Exception as e:
    raise Exception(f"❌ Error al abrir 'positions_history': {e}")

# --- Validar columnas obligatorias ---
required_cols = ["Fecha_Compra", "Unidades", "ticker_yf", "importe_inicial", "nombre"]
missing_cols = [col for col in required_cols if col not in positions.columns]
if missing_cols:
    raise ValueError(f"❌ Faltan columnas en 'positions_history': {missing_cols}")

# --- Limpiar datos ---
def clean_euro(x):
    if pd.isna(x) or x == "": return 0.0
    s = str(x).replace("€", "").replace(" ", "")
    if re.search(r"\d+\.\d{3},\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

positions["Fecha_Compra"] = pd.to_datetime(positions["Fecha_Compra"], dayfirst=True, errors="coerce")
positions["Unidades"] = positions["Unidades"].apply(clean_euro)
positions["importe_inicial"] = positions["importe_inicial"].apply(clean_euro)
positions["ticker_yf"] = positions["ticker_yf"].fillna("CASH").replace("-", "CASH")
positions.loc[positions["nombre"].str.contains("ACN", na=False), "ticker_yf"] = "ACN"

# Asegurar columna tipo_aporte
if "tipo_aporte" not in positions.columns:
    positions["tipo_aporte"] = "propio"
else:
    positions["tipo_aporte"] = positions["tipo_aporte"].fillna("propio")

# --- 2. Descargar precios históricos (excluyendo CASH) ---
tickers = [t for t in positions["ticker_yf"].unique() if t != "CASH"]
start_date = positions["Fecha_Compra"].min()
if pd.isna(start_date):
    raise ValueError("❌ Fecha de compra inválida en el historial.")
start_date = start_date.strftime("%Y-%m-%d")
print(f"📥 Descargando precios desde {start_date} para: {tickers}")

prices = yf.download(tickers, start=start_date, end=None, interval="1d", auto_adjust=True, progress=False)
if isinstance(prices.columns, pd.MultiIndex):
    prices = prices["Close"]
else:
    if len(tickers) == 1 and "Close" in prices.columns:
        prices = prices.rename(columns={"Close": tickers[0]})
    else:
        prices = pd.DataFrame(index=prices.index if not prices.empty else pd.date_range(start=start_date, periods=1))

prices = prices.ffill().bfill()
print(f"✅ Precios descargados: {prices.shape}")

# --- 3. Calcular métricas por activo ---
metrics_list = []

for ticker in positions["ticker_yf"].unique():
    ticker_positions = positions[positions["ticker_yf"] == ticker]

    # --- Caso especial: CASH ---
    if ticker == "CASH":
        capital_inicial = ticker_positions["importe_inicial"].sum()
        metrics_list.append({
            "Activo": "CASH",
            "Nombre": "Cash",
            "Capital inicial (€)": capital_inicial,
            "Valor actual (€)": capital_inicial,
            "Valor regalo (€)": 0.0,
            "Valor actual mejorado (€)": capital_inicial,
            "Drawdown máx.": 0.0,
            "Retorno anualizado": 0.0,
            "Volatilidad anualizada": 0.0,
            "Retorno total": 0.0,
            "Retorno total (€)": 0.0,
            "Retorno total mejorado": 0.0,
            "Retorno mejorado (€)": 0.0
        })
        continue

    # --- Activos cotizados ---
    if ticker not in prices.columns:
        print(f"⚠️ Ticker no encontrado: {ticker}")
        capital_inicial_propio = ticker_positions[ticker_positions["tipo_aporte"] == "propio"]["importe_inicial"].sum()
        metrics_list.append({
            "Activo": ticker,
            "Nombre": ticker_positions["nombre"].iloc[0],
            "Capital inicial (€)": capital_inicial_propio,
            "Valor actual (€)": capital_inicial_propio,
            "Valor regalo (€)": 0.0,
            "Valor actual mejorado (€)": capital_inicial_propio,
            "Drawdown máx.": np.nan,
            "Retorno anualizado": np.nan,
            "Volatilidad anualizada": np.nan,
            "Retorno total": 0.0,
            "Retorno total (€)": 0.0,
            "Retorno total mejorado": 0.0,
            "Retorno mejorado (€)": 0.0
        })
        continue

    # Separar propio y regalo
    propio = ticker_positions[ticker_positions["tipo_aporte"] == "propio"]
    regalo = ticker_positions[ticker_positions["tipo_aporte"] == "regalo"]

    units_propio = propio["Unidades"].sum()
    capital_inicial_propio = propio["importe_inicial"].sum()

    current_price = prices[ticker].iloc[-1]
    valor_actual_propio = units_propio * current_price

    # Valor del regalo
    valor_actual_regalo = 0.0
    for _, r in regalo.iterrows():
        if r["Unidades"] > 0:
            valor_actual_regalo += r["Unidades"] * current_price
        else:
            valor_actual_regalo += r["importe_inicial"]

    valor_actual = valor_actual_propio
    valor_actual_mejorado = valor_actual_propio + valor_actual_regalo

    # Retornos
    if capital_inicial_propio > 0:
        retorno_total_pct = (valor_actual / capital_inicial_propio) - 1
        retorno_mejorado_pct = (valor_actual_mejorado / capital_inicial_propio) - 1
        retorno_total_eur = valor_actual - capital_inicial_propio
        retorno_mejorado_eur = valor_actual_mejorado - capital_inicial_propio
    else:
        retorno_total_pct = np.nan
        retorno_mejorado_pct = np.nan
        retorno_total_eur = np.nan
        retorno_mejorado_eur = np.nan

    # Métricas de riesgo (solo sobre parte propia)
    max_dd = np.nan
    annual_return = np.nan
    volatility = np.nan

    if units_propio > 0:
        first_date = ticker_positions["Fecha_Compra"].min()
        if pd.isna(first_date):
            first_date = prices.index[0]
        price_series = prices[ticker].loc[prices.index >= first_date]
        value_series = price_series * units_propio

        if len(value_series) >= 10:
            peak = value_series.cummax()
            drawdown = (value_series - peak) / peak
            max_dd = drawdown.min()

            total_ret = (value_series.iloc[-1] / value_series.iloc[0]) - 1
            days = (value_series.index[-1] - value_series.index[0]).days
            annual_return = (1 + total_ret) ** (252 / days) - 1 if days > 0 else 0
            volatility = value_series.pct_change().std() * np.sqrt(252)

    metrics_list.append({
        "Activo": ticker,
        "Nombre": ticker_positions["nombre"].iloc[0],
        "Capital inicial (€)": capital_inicial_propio,
        "Valor actual (€)": valor_actual,
        "Valor regalo (€)": valor_actual_regalo,
        "Valor actual mejorado (€)": valor_actual_mejorado,
        "Drawdown máx.": max_dd,
        "Retorno anualizado": annual_return,
        "Volatilidad anualizada": volatility,
        "Retorno total": retorno_total_pct,
        "Retorno total (€)": retorno_total_eur,
        "Retorno total mejorado": retorno_mejorado_pct,
        "Retorno mejorado (€)": retorno_mejorado_eur
    })

# --- 4. Mostrar resultados ---
if not metrics_list:
    raise ValueError("❌ No se generaron métricas.")

metrics_df = pd.DataFrame(metrics_list)

# --- Fila de totales ---
total_capital = metrics_df["Capital inicial (€)"].sum()
total_valor_actual = metrics_df["Valor actual (€)"].sum()
total_valor_regalo = metrics_df["Valor regalo (€)"].sum()
total_valor_mejorado = metrics_df["Valor actual mejorado (€)"].sum()

total_retorno_total_eur = total_valor_actual - total_capital
total_retorno_total_pct = total_retorno_total_eur / total_capital if total_capital > 0 else 0

total_retorno_mejorado_eur = total_valor_mejorado - total_capital
total_retorno_mejorado_pct = total_retorno_mejorado_eur / total_capital if total_capital > 0 else 0

total_row = pd.DataFrame([{
    "Activo": "TOTAL",
    "Nombre": "Cartera Total",
    "Capital inicial (€)": total_capital,
    "Valor actual (€)": total_valor_actual,
    "Valor regalo (€)": total_valor_regalo,
    "Valor actual mejorado (€)": total_valor_mejorado,
    "Drawdown máx.": np.nan,
    "Retorno anualizado": np.nan,
    "Volatilidad anualizada": np.nan,
    "Retorno total": total_retorno_total_pct,
    "Retorno total (€)": total_retorno_total_eur,
    "Retorno total mejorado": total_retorno_mejorado_pct,
    "Retorno mejorado (€)": total_retorno_mejorado_eur
}])

metrics_df = pd.concat([metrics_df, total_row], ignore_index=True)
metrics_df = metrics_df.sort_values(by=["Activo"], key=lambda x: x == "TOTAL", ascending=True).reset_index(drop=True)

# --- Formatear para visualización (solo para impresión) ---
display_df = metrics_df.copy()
for col in ["Capital inicial (€)", "Valor actual (€)", "Valor regalo (€)", "Valor actual mejorado (€)", "Retorno total (€)", "Retorno mejorado (€)"]:
    display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")

for col in ["Drawdown máx.", "Retorno anualizado", "Volatilidad anualizada", "Retorno total", "Retorno total mejorado"]:
    display_df[col] = display_df[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")

print("=== 📊 MÉTRICAS POR ACTIVO (con totales y cash) ===")
display_columns = [
    "Activo", "Nombre", "Capital inicial (€)",
    "Valor actual (€)", "Valor regalo (€)", "Valor actual mejorado (€)",
    "Retorno total", "Retorno total (€)",
    "Retorno total mejorado", "Retorno mejorado (€)",
    "Drawdown máx.", "Retorno anualizado", "Volatilidad anualizada"
]
print(display_df[display_columns].to_string(index=False))

# --- 5. Guardar ---
CSV_PATH = f"{DIRS['reports']}/asset_metrics.csv"
metrics_df.to_csv(CSV_PATH, index=False)
print(f"\n✅ Métricas guardadas en: {CSV_PATH}")

PARQUET_PATH = f"{DIRS['reports']}/asset_metrics.parquet"
metrics_df.to_parquet(PARQUET_PATH, index=False)
print(f"✅ Versión Parquet guardada: {PARQUET_PATH}")

# --- 6. Guardar resumen para orquestador ---
activos_dict = {}
for _, row in metrics_df[metrics_df["Activo"] != "TOTAL"].iterrows():
    activos_dict[row["Activo"]] = {
        "nombre": row["Nombre"],
        "capital_inicial": float(row["Capital inicial (€)"]),
        "valor_actual": float(row["Valor actual (€)"]),
        "retorno_total": float(row["Retorno total"]) if pd.notna(row["Retorno total"]) else None,
        "drawdown_max": float(row["Drawdown máx."]) if pd.notna(row["Drawdown máx."]) else None,
        "volatilidad": float(row["Volatilidad anualizada"]) if pd.notna(row["Volatilidad anualizada"]) else None
    }

asset_summary = {
    "fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
    "activos": activos_dict,
    "total": {
        "capital_inicial": float(total_capital),
        "valor_actual": float(total_valor_actual),
        "retorno_total": float(total_retorno_total_pct),
        "valor_mejorado": float(total_valor_mejorado)
    }
}

JSON_PATH = f"{DIRS['reports']}/asset_metrics_latest.json"
with open(JSON_PATH, "w") as f:
    json.dump(asset_summary, f, indent=2)
print(f"✅ Resumen para orquestador: {JSON_PATH}")


# In[1]:


# ============================================
# 07_asset_metrics.ipynb - Métricas por activo (MEJORADO + CONTRATO + LOG)
# ============================================

import os
import pandas as pd
import numpy as np
import yfinance as yf
import re
import json
from datetime import datetime
from google.colab import auth, drive

# Instalación segura
try:
    import gspread
    from gspread_dataframe import get_as_dataframe
except ImportError:
    get_ipython().system('pip -q install yfinance pandas gspread gspread-dataframe')
    import gspread
    from gspread_dataframe import get_as_dataframe

drive.mount('/content/drive', force_remount=False)
auth.authenticate_user()

from google.auth import default
creds, _ = default()
gc = gspread.authorize(creds)

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "reports": f"{BASE}/reports"
}

# --- FUNCIÓN PARA REGISTRAR SEÑALES (PARA PERFORMANCE AGENT) ---
def log_signal(
    agente: str,
    tipo_senal: str,
    recomendacion: str,
    contexto: dict = None,
    horizonte_eval: str = "5d",
    metadata: dict = None
):
    """
    Registra una señal emitida por un agente en signals_emitted.csv.
    """
    SIGNALS_LOG_PATH = f"{BASE}/data/signals_emitted.csv"
    os.makedirs(os.path.dirname(SIGNALS_LOG_PATH), exist_ok=True)

    new_row = {
        "fecha_emision": datetime.today().strftime("%Y-%m-%d"),
        "agente": agente,
        "tipo_senal": tipo_senal,
        "recomendacion": recomendacion,
        "contexto_liquidez": contexto.get("liquidez_regime", "N/A") if contexto else "N/A",
        "contexto_mercado": contexto.get("market_regime", "N/A") if contexto else "N/A",
        "horizonte_eval": horizonte_eval,
        "señal_id": f"{agente}_{datetime.today().strftime('%Y%m%d')}_{hash(recomendacion) % 1000:03d}"
    }

    import json as json_lib
    if metadata:
        new_row["metadata"] = json_lib.dumps(metadata, ensure_ascii=False)
    else:
        new_row["metadata"] = "{}"

    # Cargar o crear CSV
    if os.path.exists(SIGNALS_LOG_PATH):
        df = pd.read_csv(SIGNALS_LOG_PATH)
    else:
        df = pd.DataFrame(columns=[
            "fecha_emision", "agente", "tipo_senal", "recomendacion",
            "contexto_liquidez", "contexto_mercado", "horizonte_eval", "señal_id", "metadata"
        ])

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(SIGNALS_LOG_PATH, index=False, encoding="utf-8")
    print(f"✅ Señal registrada para evaluación: {recomendacion[:60]}...")

# --- 1. Leer historial de compras ---
try:
    sh = gc.open("positions_history")
    ws = sh.sheet1
    positions = get_as_dataframe(ws, evaluate_formulas=True, header=0).dropna(how="all")
    print(f"✅ Historial cargado: {positions.shape[0]} posiciones")
except Exception as e:
    raise Exception(f"❌ Error al abrir 'positions_history': {e}")

# --- Validar columnas obligatorias ---
required_cols = ["Fecha_Compra", "Unidades", "ticker_yf", "importe_inicial", "nombre"]
missing_cols = [col for col in required_cols if col not in positions.columns]
if missing_cols:
    raise ValueError(f"❌ Faltan columnas en 'positions_history': {missing_cols}")

# --- Limpiar datos ---
def clean_euro(x):
    if pd.isna(x) or x == "": return 0.0
    s = str(x).replace("€", "").replace(" ", "")
    if re.search(r"\d+\.\d{3},\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

positions["Fecha_Compra"] = pd.to_datetime(positions["Fecha_Compra"], dayfirst=True, errors="coerce")
positions["Unidades"] = positions["Unidades"].apply(clean_euro)
positions["importe_inicial"] = positions["importe_inicial"].apply(clean_euro)
positions["ticker_yf"] = positions["ticker_yf"].fillna("CASH").replace("-", "CASH")
positions.loc[positions["nombre"].str.contains("ACN", na=False), "ticker_yf"] = "ACN"

# Asegurar columna tipo_aporte
if "tipo_aporte" not in positions.columns:
    positions["tipo_aporte"] = "propio"
else:
    positions["tipo_aporte"] = positions["tipo_aporte"].fillna("propio")

# --- 2. Descargar precios históricos (excluyendo CASH) ---
tickers = [t for t in positions["ticker_yf"].unique() if t != "CASH"]
start_date = positions["Fecha_Compra"].min()
if pd.isna(start_date):
    raise ValueError("❌ Fecha de compra inválida en el historial.")
start_date = start_date.strftime("%Y-%m-%d")
print(f"📥 Descargando precios desde {start_date} para: {tickers}")

prices = yf.download(tickers, start=start_date, end=None, interval="1d", auto_adjust=True, progress=False)
if isinstance(prices.columns, pd.MultiIndex):
    prices = prices["Close"]
else:
    if len(tickers) == 1 and "Close" in prices.columns:
        prices = prices.rename(columns={"Close": tickers[0]})
    else:
        prices = pd.DataFrame(index=prices.index if not prices.empty else pd.date_range(start=start_date, periods=1))

prices = prices.ffill().bfill()
print(f"✅ Precios descargados: {prices.shape}")

# --- 3. Calcular métricas por activo ---
metrics_list = []

for ticker in positions["ticker_yf"].unique():
    ticker_positions = positions[positions["ticker_yf"] == ticker]

    # --- Caso especial: CASH ---
    if ticker == "CASH":
        capital_inicial = ticker_positions["importe_inicial"].sum()
        metrics_list.append({
            "Activo": "CASH",
            "Nombre": "Cash",
            "Capital inicial (€)": capital_inicial,
            "Valor actual (€)": capital_inicial,
            "Valor regalo (€)": 0.0,
            "Valor actual mejorado (€)": capital_inicial,
            "Drawdown máx.": 0.0,
            "Retorno anualizado": 0.0,
            "Volatilidad anualizada": 0.0,
            "Retorno total": 0.0,
            "Retorno total (€)": 0.0,
            "Retorno total mejorado": 0.0,
            "Retorno mejorado (€)": 0.0
        })
        continue

    # --- Activos cotizados ---
    if ticker not in prices.columns:
        print(f"⚠️ Ticker no encontrado: {ticker}")
        capital_inicial_propio = ticker_positions[ticker_positions["tipo_aporte"] == "propio"]["importe_inicial"].sum()
        metrics_list.append({
            "Activo": ticker,
            "Nombre": ticker_positions["nombre"].iloc[0],
            "Capital inicial (€)": capital_inicial_propio,
            "Valor actual (€)": capital_inicial_propio,
            "Valor regalo (€)": 0.0,
            "Valor actual mejorado (€)": capital_inicial_propio,
            "Drawdown máx.": np.nan,
            "Retorno anualizado": np.nan,
            "Volatilidad anualizada": np.nan,
            "Retorno total": 0.0,
            "Retorno total (€)": 0.0,
            "Retorno total mejorado": 0.0,
            "Retorno mejorado (€)": 0.0
        })
        continue

    # Separar propio y regalo
    propio = ticker_positions[ticker_positions["tipo_aporte"] == "propio"]
    regalo = ticker_positions[ticker_positions["tipo_aporte"] == "regalo"]

    units_propio = propio["Unidades"].sum()
    capital_inicial_propio = propio["importe_inicial"].sum()

    current_price = prices[ticker].iloc[-1]
    valor_actual_propio = units_propio * current_price

    # Valor del regalo
    valor_actual_regalo = 0.0
    for _, r in regalo.iterrows():
        if r["Unidades"] > 0:
            valor_actual_regalo += r["Unidades"] * current_price
        else:
            valor_actual_regalo += r["importe_inicial"]

    valor_actual = valor_actual_propio
    valor_actual_mejorado = valor_actual_propio + valor_actual_regalo

    # Retornos
    if capital_inicial_propio > 0:
        retorno_total_pct = (valor_actual / capital_inicial_propio) - 1
        retorno_mejorado_pct = (valor_actual_mejorado / capital_inicial_propio) - 1
        retorno_total_eur = valor_actual - capital_inicial_propio
        retorno_mejorado_eur = valor_actual_mejorado - capital_inicial_propio
    else:
        retorno_total_pct = np.nan
        retorno_mejorado_pct = np.nan
        retorno_total_eur = np.nan
        retorno_mejorado_eur = np.nan

    # Métricas de riesgo (solo sobre parte propia)
    max_dd = np.nan
    annual_return = np.nan
    volatility = np.nan

    if units_propio > 0:
        first_date = ticker_positions["Fecha_Compra"].min()
        if pd.isna(first_date):
            first_date = prices.index[0]
        price_series = prices[ticker].loc[prices.index >= first_date]
        value_series = price_series * units_propio

        if len(value_series) >= 10:
            peak = value_series.cummax()
            drawdown = (value_series - peak) / peak
            max_dd = drawdown.min()

            total_ret = (value_series.iloc[-1] / value_series.iloc[0]) - 1
            days = (value_series.index[-1] - value_series.index[0]).days
            annual_return = (1 + total_ret) ** (252 / days) - 1 if days > 0 else 0
            volatility = value_series.pct_change().std() * np.sqrt(252)

    metrics_list.append({
        "Activo": ticker,
        "Nombre": ticker_positions["nombre"].iloc[0],
        "Capital inicial (€)": capital_inicial_propio,
        "Valor actual (€)": valor_actual,
        "Valor regalo (€)": valor_actual_regalo,
        "Valor actual mejorado (€)": valor_actual_mejorado,
        "Drawdown máx.": max_dd,
        "Retorno anualizado": annual_return,
        "Volatilidad anualizada": volatility,
        "Retorno total": retorno_total_pct,
        "Retorno total (€)": retorno_total_eur,
        "Retorno total mejorado": retorno_mejorado_pct,
        "Retorno mejorado (€)": retorno_mejorado_eur
    })

# --- 4. Mostrar resultados ---
if not metrics_list:
    raise ValueError("❌ No se generaron métricas.")

metrics_df = pd.DataFrame(metrics_list)

# --- Fila de totales ---
total_capital = metrics_df["Capital inicial (€)"].sum()
total_valor_actual = metrics_df["Valor actual (€)"].sum()
total_valor_regalo = metrics_df["Valor regalo (€)"].sum()
total_valor_mejorado = metrics_df["Valor actual mejorado (€)"].sum()

total_retorno_total_eur = total_valor_actual - total_capital
total_retorno_total_pct = total_retorno_total_eur / total_capital if total_capital > 0 else 0

total_retorno_mejorado_eur = total_valor_mejorado - total_capital
total_retorno_mejorado_pct = total_retorno_mejorado_eur / total_capital if total_capital > 0 else 0

total_row = pd.DataFrame([{
    "Activo": "TOTAL",
    "Nombre": "Cartera Total",
    "Capital inicial (€)": total_capital,
    "Valor actual (€)": total_valor_actual,
    "Valor regalo (€)": total_valor_regalo,
    "Valor actual mejorado (€)": total_valor_mejorado,
    "Drawdown máx.": np.nan,
    "Retorno anualizado": np.nan,
    "Volatilidad anualizada": np.nan,
    "Retorno total": total_retorno_total_pct,
    "Retorno total (€)": total_retorno_total_eur,
    "Retorno total mejorado": total_retorno_mejorado_pct,
    "Retorno mejorado (€)": total_retorno_mejorado_eur
}])

metrics_df = pd.concat([metrics_df, total_row], ignore_index=True)
metrics_df = metrics_df.sort_values(by=["Activo"], key=lambda x: x == "TOTAL", ascending=True).reset_index(drop=True)

# --- Formatear para visualización (solo para impresión) ---
display_df = metrics_df.copy()
for col in ["Capital inicial (€)", "Valor actual (€)", "Valor regalo (€)", "Valor actual mejorado (€)", "Retorno total (€)", "Retorno mejorado (€)"]:
    display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")

for col in ["Drawdown máx.", "Retorno anualizado", "Volatilidad anualizada", "Retorno total", "Retorno total mejorado"]:
    display_df[col] = display_df[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")

print("=== 📊 MÉTRICAS POR ACTIVO (con totales y cash) ===")
display_columns = [
    "Activo", "Nombre", "Capital inicial (€)",
    "Valor actual (€)", "Valor regalo (€)", "Valor actual mejorado (€)",
    "Retorno total", "Retorno total (€)",
    "Retorno total mejorado", "Retorno mejorado (€)",
    "Drawdown máx.", "Retorno anualizado", "Volatilidad anualizada"
]
print(display_df[display_columns].to_string(index=False))

# --- 5. Guardar ---
CSV_PATH = f"{DIRS['reports']}/asset_metrics.csv"
metrics_df.to_csv(CSV_PATH, index=False)
print(f"\n✅ Métricas guardadas en: {CSV_PATH}")

PARQUET_PATH = f"{DIRS['reports']}/asset_metrics.parquet"
metrics_df.to_parquet(PARQUET_PATH, index=False)
print(f"✅ Versión Parquet guardada: {PARQUET_PATH}")

# --- 6. Guardar resumen para orquestador ---
activos_dict = {}
for _, row in metrics_df[metrics_df["Activo"] != "TOTAL"].iterrows():
    activos_dict[row["Activo"]] = {
        "nombre": row["Nombre"],
        "capital_inicial": float(row["Capital inicial (€)"]),
        "valor_actual": float(row["Valor actual (€)"]),
        "retorno_total": float(row["Retorno total"]) if pd.notna(row["Retorno total"]) else None,
        "drawdown_max": float(row["Drawdown máx."]) if pd.notna(row["Drawdown máx."]) else None,
        "volatilidad": float(row["Volatilidad anualizada"]) if pd.notna(row["Volatilidad anualizada"]) else None
    }

asset_summary = {
    "fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
    "activos": activos_dict,
    "total": {
        "capital_inicial": float(total_capital),
        "valor_actual": float(total_valor_actual),
        "retorno_total": float(total_retorno_total_pct),
        "valor_mejorado": float(total_valor_mejorado)
    }
}

JSON_PATH = f"{DIRS['reports']}/asset_metrics_latest.json"
with open(JSON_PATH, "w") as f:
    json.dump(asset_summary, f, indent=2)
print(f"✅ Resumen para orquestador: {JSON_PATH}")

# --- 7. Leer régimen de liquidez (para contexto en log_signal) ---
liquidity_regime = "Neutral"
liquidity_path = f"{DIRS['reports']}/liquidity_regime_latest.json"
if os.path.exists(liquidity_path):
    try:
        with open(liquidity_path, "r") as f:
            liquidity_data = json.load(f)
            liquidity_regime = liquidity_data.get("regimen", "Neutral")
    except Exception:
        pass
print(f"💧 Régimen de liquidez: {liquidity_regime}")

# --- 8. REGISTRAR SEÑALES PARA EVALUACIÓN ---
# Calcular métricas de interés para registro
activos_con_rendimiento = metrics_df[metrics_df["Activo"] != "TOTAL"]
activos_positivos = activos_con_rendimiento[activos_con_rendimiento["Retorno total"] > 0]
activos_negativos = activos_con_rendimiento[activos_con_rendimiento["Retorno total"] < 0]

if not activos_positivos.empty:
    top_activos = activos_positivos.nlargest(3, "Retorno total")
    top_activos_str = ", ".join([f"{row['Activo']} ({row['Retorno total']:.1%})" for _, row in top_activos.iterrows()])
    recomendacion_pos = f"Activos con mejor rendimiento: {top_activos_str}"
    log_signal(
        agente="asset_metrics",
        tipo_senal="rendimiento_positivo",
        recomendacion=recomendacion_pos,
        contexto={
            "liquidez_regime": liquidity_regime,
            "market_regime": "Normal"
        },
        horizonte_eval="5d",
        metadata={
            "top_activos": top_activos_str,
            "total_positivos": int(len(activos_positivos)),
            "retorno_medio": float(activos_positivos["Retorno total"].mean())
        }
    )

if not activos_negativos.empty:
    worst_activos = activos_negativos.nsmallest(3, "Retorno total")
    worst_activos_str = ", ".join([f"{row['Activo']} ({row['Retorno total']:.1%})" for _, row in worst_activos.iterrows()])
    recomendacion_neg = f"Activos con peor rendimiento: {worst_activos_str}"
    log_signal(
        agente="asset_metrics",
        tipo_senal="rendimiento_negativo",
        recomendacion=recomendacion_neg,
        contexto={
            "liquidez_regime": liquidity_regime,
            "market_regime": "Risk-off" if len(activos_negativos) > len(activos_positivos) else "Normal"
        },
        horizonte_eval="5d",
        metadata={
            "worst_activos": worst_activos_str,
            "total_negativos": int(len(activos_negativos)),
            "retorno_medio": float(activos_negativos["Retorno total"].mean())
        }
    )

# Señal general de rendimiento de la cartera
recomendacion_general = f"Rendimiento total: {total_retorno_total_pct:.1%}, Mejorado: {total_retorno_mejorado_pct:.1%}"
log_signal(
    agente="asset_metrics",
    tipo_senal="rendimiento_general",
    recomendacion=recomendacion_general,
    contexto={
        "liquidez_regime": liquidity_regime,
        "market_regime": "Risk-off" if total_retorno_total_pct < 0 else "Normal"
    },
    horizonte_eval="5d",
    metadata={
        "retorno_total": float(total_retorno_total_pct),
        "retorno_mejorado": float(total_retorno_mejorado_pct),
        "activo_mejor": top_activos.iloc[0]["Activo"] if not top_activos.empty else None,
        "activo_peor": worst_activos.iloc[0]["Activo"] if not worst_activos.empty else None,
        "total_activos": int(len(activos_con_rendimiento)),
        "total_positivos": int(len(activos_positivos)),
        "total_negativos": int(len(activos_negativos))
    }
)

print("\n✅ Asset Metrics completado exitosamente.")

