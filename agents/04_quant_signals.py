#!/usr/bin/env python
# coding: utf-8

# In[1]:


# ============================================
# 04_quant_signals.ipynb - Señales cuantitativas (MEJORADO + CONTRATO + LOG)
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
import json
from datetime import datetime
from google.colab import drive

# Instalación segura
try:
    import pandas as pd
except ImportError:
    get_ipython().system('pip -q install pandas pyarrow')
    import pandas as pd

drive.mount('/content/drive', force_remount=False)

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "reports": f"{BASE}/reports",
    "clean": f"{BASE}/data/clean"
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

# --- Parámetros dinámicos (desde orquestador) ---
QUANT_AGENT_WEIGHT = float(os.getenv("QUANT_AGENT_WEIGHT", 1.0))
print(f"⚖️ Peso del Quant Agent: {QUANT_AGENT_WEIGHT:.2f}")

# --- 1. Leer cartera enriquecida (para obtener tickers activos) ---
ENRICHED_PATH = f"{DIRS['reports']}/portfolio_enriched_final.csv"
if not os.path.exists(ENRICHED_PATH):
    raise FileNotFoundError("❌ Ejecuta primero 02_portfolio_exposure.ipynb")

pf = pd.read_csv(ENRICHED_PATH)
# Obtener tickers únicos (excluir cash y otros sin ticker)
active_tickers = pf[pf["ticker_yf"].notna() & (pf["ticker_yf"] != "-")]["ticker_yf"].unique().tolist()
print(f"🔍 Tickers activos: {active_tickers}")

if not active_tickers:
    raise ValueError("❌ No hay tickers activos en la cartera.")

# --- 2. Leer precios limpios ---
PRICES_PATH = f"{DIRS['clean']}/etfs_prices_clean.parquet"
INDICES_PATH = f"{DIRS['clean']}/indices_prices_clean.parquet"
FX_PATH = f"{DIRS['clean']}/fx_rates_clean.parquet"

# Combinar todos los precios disponibles
all_prices = pd.DataFrame()

files_found = []
if os.path.exists(PRICES_PATH):
    etfs = pd.read_parquet(PRICES_PATH)
    all_prices = pd.concat([all_prices, etfs], axis=1)
    files_found.append("etfs")

if os.path.exists(INDICES_PATH):
    indices = pd.read_parquet(INDICES_PATH)
    all_prices = pd.concat([all_prices, indices], axis=1)
    files_found.append("índices")

if os.path.exists(FX_PATH):
    fx = pd.read_parquet(FX_PATH)
    all_prices = pd.concat([all_prices, fx], axis=1)
    files_found.append("FX")

if all_prices.empty:
    raise FileNotFoundError("❌ No se encontraron archivos de precios válidos.")

print(f"✅ Archivos de precios cargados: {', '.join(files_found)}")
print(f"✅ Precios disponibles para {len(all_prices.columns)} instrumentos")

# Asegurar que los tickers de la cartera estén en los precios
available_tickers = [t for t in active_tickers if t in all_prices.columns]
if not available_tickers:
    raise ValueError("❌ Ningún ticker activo tiene datos de precios.")

print(f"✅ Tickers con precios: {available_tickers}")

# --- 3. Leer régimen de mercado y liquidez ---
DAILY_PATH = f"{DIRS['reports']}/portfolio_daily_value.csv"
regime = "calma"  # por defecto

if os.path.exists(DAILY_PATH):
    try:
        daily = pd.read_csv(DAILY_PATH, index_col=0, parse_dates=True)
        if "drawdown" in daily.columns and "valor_mejorado" in daily.columns:
            current_dd = daily["drawdown"].min()
            current_vol = daily["valor_mejorado"].pct_change().std() * np.sqrt(252)

            if current_dd < -0.08:
                regime = "estrés"
            elif current_vol > 0.15:
                regime = "mixto"
            else:
                regime = "calma"
        print(f"📊 Régimen de mercado: {regime} (DD: {current_dd:.1%}, Vol: {current_vol:.1%})")
    except Exception as e:
        print(f"⚠️ Error al leer régimen: {e}. Asumiendo 'calma'.")
else:
    print("⚠️ portfolio_daily_value.csv no encontrado. Asumiendo régimen 'calma'.")

# Leer régimen de liquidez (para contexto en log_signal)
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

# --- 4. Calcular señales por activo ---
signals_list = []

# Pre-calcular volatilidades para todos los tickers disponibles (eficiencia)
vol_6m_dict = {}
for ticker in available_tickers:
    price_series = all_prices[ticker].dropna()
    if len(price_series) >= 126:
        vol = price_series.pct_change().tail(126).std() * np.sqrt(252)
        if pd.notna(vol):
            vol_6m_dict[ticker] = vol

# Calcular percentil de volatilidad
all_vols = list(vol_6m_dict.values())
vol_percentiles = {}
if all_vols:
    all_vols_arr = np.array(all_vols)
    for ticker, vol in vol_6m_dict.items():
        vol_percentiles[ticker] = (all_vols_arr < vol).mean()
else:
    vol_percentiles = {t: 0.5 for t in available_tickers}

for ticker in available_tickers:
    price_series = all_prices[ticker].dropna()
    if len(price_series) < 252:
        print(f"⚠️ {ticker}: datos insuficientes para momentum (<252 días)")
        continue

    # --- Momentum (12-1) ---
    ret_12m = price_series.pct_change(252).iloc[-1]
    ret_1m = price_series.pct_change(21).iloc[-1]
    momentum = ret_12m - ret_1m
    momentum_signal = "positivo" if momentum > 0 else "negativo"

    # --- Low volatility ---
    vol_6m = vol_6m_dict.get(ticker, np.nan)
    vol_percentile = vol_percentiles.get(ticker, 0.5)
    low_vol = vol_percentile < 0.3  # top 30% menos volátil

    # --- Señal final ---
    if regime == "estrés":
        if momentum_signal == "negativo":
            signal = "Reducir"
        else:
            signal = "Mantener"
    elif regime == "calma":
        if momentum_signal == "positivo" and low_vol:
            signal = "Aumentar"
        else:
            signal = "Mantener"
    else:  # mixto
        signal = "Mantener"

    signals_list.append({
        "Activo": ticker,
        "Régimen": regime,
        "Momentum": momentum_signal,
        "LowVol": low_vol,
        "Volatilidad_6m_%": vol_6m,
        "Señal": signal
    })

# --- 5. Mostrar resultados ---
if signals_list:
    signals_df = pd.DataFrame(signals_list)
    print("=== 📈 SEÑALES CUANTITATIVAS ===")
    print(signals_df.to_string(index=False))

    # Guardar CSV
    CSV_PATH = f"{DIRS['reports']}/quant_signals.csv"
    signals_df.to_csv(CSV_PATH, index=False)
    print(f"\n✅ Señales guardadas en: {CSV_PATH}")

    # Guardar resumen para orquestador
    señales_dict = {row["Activo"]: row["Señal"] for _, row in signals_df.iterrows()}
    resumen = signals_df["Señal"].value_counts().to_dict()

    quant_summary = {
        "fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "regimen": regime,
        "tickers_analizados": available_tickers,
        "señales": señales_dict,
        "resumen": resumen
    }

    JSON_PATH = f"{DIRS['reports']}/quant_signals_latest.json"
    with open(JSON_PATH, "w") as f:
        json.dump(quant_summary, f, indent=2)
    print(f"✅ Resumen para orquestador: {JSON_PATH}")

    # --- 6. REGISTRAR SEÑALES PARA EVALUACIÓN ---
    acciones_positivas = [s["Activo"] for s in signals_list if s["Señal"] == "Aumentar"]
    acciones_negativas = [s["Activo"] for s in signals_list if s["Señal"] == "Reducir"]

    if acciones_positivas:
        recomendacion_pos = f"Comprar/Incrementar: {', '.join(acciones_positivas)} (por momentum y baja vol)"
        log_signal(
            agente="quant_signals",
            tipo_senal="compra",
            recomendacion=recomendacion_pos,
            contexto={
                "liquidez_regime": liquidity_regime,
                "market_regime": regime
            },
            horizonte_eval="5d",
            metadata={
                "tickers": acciones_positivas,
                "razones": ["momentum_positivo", "low_volatility"],
                "regimen": regime
            }
        )

    if acciones_negativas:
        recomendacion_neg = f"Reducir: {', '.join(acciones_negativas)} (por momentum negativo)"
        log_signal(
            agente="quant_signals",
            tipo_senal="venta",
            recomendacion=recomendacion_neg,
            contexto={
                "liquidez_regime": liquidity_regime,
                "market_regime": regime
            },
            horizonte_eval="5d",
            metadata={
                "tickers": acciones_negativas,
                "razones": ["momentum_negativo"],
                "regimen": regime
            }
        )

    if not acciones_positivas and not acciones_negativas:
        log_signal(
            agente="quant_signals",
            tipo_senal="mantener",
            recomendacion="No se recomienda cambios (señales neutrales)",
            contexto={
                "liquidez_regime": liquidity_regime,
                "market_regime": regime
            },
            horizonte_eval="5d",
            metadata={
                "tickers": available_tickers,
                "razones": ["señales_neutrales"],
                "regimen": regime
            }
        )

    # --- 7. Resumen ejecutivo ---
    print("\n=== 📊 RESUMEN DE SEÑALES ===")
    for action, count in sorted(resumen.items()):
        print(f"- {action}: {count} activos")
else:
    print("⚠️ No se generaron señales. Revisa los tickers y precios.")
    # Guardar JSON vacío
    quant_summary = {
        "fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "regimen": regime,
        "tickers_analizados": [],
        "señales": {},
        "resumen": {}
    }
    JSON_PATH = f"{DIRS['reports']}/quant_signals_latest.json"
    with open(JSON_PATH, "w") as f:
        json.dump(quant_summary, f, indent=2)
    print(f"✅ Resumen vacío guardado: {JSON_PATH}")

    # ✅ REGISTRAR SEÑAL VACÍA PARA EVALUACIÓN
    log_signal(
        agente="quant_signals",
        tipo_senal="mantener",
        recomendacion="No se generaron señales cuantitativas (sin datos)",
        contexto={
            "liquidez_regime": liquidity_regime,
            "market_regime": regime
        },
        horizonte_eval="5d",
        metadata={
            "tickers": active_tickers,
            "razones": ["sin_datos"],
            "regimen": regime
        }
    )

print("\n✅ Quant Agent completado exitosamente.")

