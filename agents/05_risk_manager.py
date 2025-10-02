#!/usr/bin/env python
# coding: utf-8

# In[3]:


# ============================================
# 05_risk_manager.ipynb - Semáforo de riesgo (MEJORADO + CONTRATO + LOG)
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

drive.mount('/content/drive', force_remount=False)

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "reports": f"{BASE}/reports",
    "data": f"{BASE}/data",
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

# --- Leer cartera enriquecida ---
ENRICHED_PATH = f"{DIRS['reports']}/portfolio_enriched_final.csv"
if not os.path.exists(ENRICHED_PATH):
    raise FileNotFoundError("❌ Ejecuta primero 02_portfolio_exposure.ipynb")

pf = pd.read_csv(ENRICHED_PATH)
total = pf["importe_actual_eur"].sum()

if total == 0:
    raise ValueError("❌ El valor total de la cartera es 0.")

# --- Leer drawdown y retorno de la cartera reconstruida ---
DAILY_PATH = f"{DIRS['reports']}/portfolio_daily_value.csv"
annual_return = 0.0
current_dd = 0.0
alpha = np.nan

if os.path.exists(DAILY_PATH):
    try:
        portfolio_daily = pd.read_csv(DAILY_PATH, index_col=0, parse_dates=True)
        if "drawdown" not in portfolio_daily.columns or "valor_mejorado" not in portfolio_daily.columns:
            raise ValueError("Columnas faltantes en portfolio_daily_value.csv")

        current_dd = portfolio_daily["drawdown"].min()

        # Calcular retorno anualizado de la cartera
        first_val = portfolio_daily["valor_mejorado"].iloc[0]
        last_val = portfolio_daily["valor_mejorado"].iloc[-1]
        days = (portfolio_daily.index[-1] - portfolio_daily.index[0]).days
        if days > 0:
            annual_return = (last_val / first_val) ** (252 / days) - 1
    except Exception as e:
        print(f"⚠️ Error al leer portfolio_daily_value.csv: {e}. Usando valores por defecto.")
        current_dd = 0.0
        annual_return = 0.0
else:
    print("⚠️ Archivo portfolio_daily_value.csv no encontrado. Usando valores por defecto.")
    current_dd = 0.0
    annual_return = 0.0

# --- Comparar con S&P 500 ---
BENCHMARK_PATH = f"{DIRS['clean']}/indices_prices_clean.parquet"
sp500_return = np.nan

if os.path.exists(BENCHMARK_PATH):
    try:
        indices = pd.read_parquet(BENCHMARK_PATH)
        if "^GSPC" not in indices.columns:
            print("⚠️ ^GSPC no encontrado en indices_prices_clean.parquet")
        else:
            sp500 = indices["^GSPC"].dropna()
            if os.path.exists(DAILY_PATH):
                try:
                    portfolio_daily = pd.read_csv(DAILY_PATH, index_col=0, parse_dates=True)
                    common_dates = portfolio_daily.index.intersection(sp500.index)
                    if len(common_dates) > 100:
                        sp500_aligned = sp500[common_dates]
                        portfolio_aligned = portfolio_daily.loc[common_dates]["valor_mejorado"]
                        # Calcular retornos anualizados en el mismo período
                        sp500_ret = (sp500_aligned.iloc[-1] / sp500_aligned.iloc[0]) ** (252 / len(sp500_aligned)) - 1
                        portfolio_ret = (portfolio_aligned.iloc[-1] / portfolio_aligned.iloc[0]) ** (252 / len(portfolio_aligned)) - 1
                        sp500_return = sp500_ret
                        alpha = portfolio_ret - sp500_ret
                    else:
                        print(f"⚠️ Pocas fechas comunes ({len(common_dates)}) para calcular alpha")
                except Exception as e:
                    print(f"⚠️ Error al alinear fechas: {e}")
    except Exception as e:
        print(f"⚠️ Error al leer el benchmark: {e}")

# --- Leer régimen de liquidez (para contexto en log_signal) ---
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

# --- Configuración de límites ---
MAX_REGION = 0.30
MAX_ASSET = 0.05
MAX_DD = 0.10
AMBER_DD = 0.09

# --- Límites por activo ---
pf["breach_asset"] = pf["peso_%"] / 100 > MAX_ASSET
breaches_asset = pf[pf["breach_asset"]]

# --- Límites por región ---
exp_region = pf.groupby("region")["importe_actual_eur"].sum().to_frame()
exp_region["peso_%"] = exp_region["importe_actual_eur"] / total * 100
exp_region["breach_region"] = exp_region["peso_%"] / 100 > MAX_REGION
breaches_region = exp_region[exp_region["breach_region"]]

# --- USD no hedged ---
usd_unhedged = pf[(pf["divisa_base"] == "USD") & (pf["hedged"] != "Sí")]["importe_actual_eur"].sum()
usd_unhedged_pct = usd_unhedged / total

# --- Alertas de drawdown ---
amber_alert = current_dd <= -AMBER_DD
red_alert = current_dd <= -MAX_DD

# --- Estado general de riesgo ---
if red_alert:
    estado_general = "ROJO"
elif amber_alert or len(breaches_asset) > 0 or len(breaches_region) > 0 or usd_unhedged_pct >= 0.10:
    estado_general = "AMBER"
else:
    estado_general = "VERDE"

# --- Dashboard ---
risk_dashboard = pd.DataFrame({
    "metrica": [
        "Drawdown actual",
        "Retorno anualizado cartera",
        "Retorno anualizado S&P 500",
        "Alpha vs S&P 500",
        "Alpha objetivo (+5%)",
        "Drawdown ≥ 9% (ámbar)",
        "Drawdown ≥ 10% (rojo)",
        "Activos > 5%",
        "Regiones > 30%",
        "USD no hedged (%)"
    ],
    "valor": [
        f"{current_dd:.1%}",
        f"{annual_return:.1%}",
        f"{sp500_return:.1%}" if pd.notna(sp500_return) else "N/A",
        f"{alpha:.1%}" if pd.notna(alpha) else "N/A",
        "✅" if pd.notna(alpha) and alpha >= 0.05 else "❌",
        amber_alert,
        red_alert,
        len(breaches_asset),
        len(breaches_region),
        f"{usd_unhedged_pct:.1%}"
    ],
    "estado": [
        "✅" if not amber_alert else "⚠️" if not red_alert else "🔴",
        "✅" if annual_return > 0 else "⚠️",
        "N/A",
        "✅" if pd.notna(alpha) and alpha > 0 else "⚠️",
        "✅" if pd.notna(alpha) and alpha >= 0.05 else "⚠️",
        "✅" if not amber_alert else "⚠️",
        "✅" if not red_alert else "🔴",
        "✅" if len(breaches_asset) == 0 else "⚠️",
        "✅" if len(breaches_region) == 0 else "⚠️",
        "✅" if usd_unhedged_pct < 0.10 else "⚠️"
    ]
})

print("=== 🛡️ DASHBOARD DE RIESGO (con Alpha vs S&P 500) ===")
print(risk_dashboard.to_string(index=False))

# --- Guardar archivos ---
CSV_PATH = f"{DIRS['reports']}/risk_dashboard.csv"
risk_dashboard.to_csv(CSV_PATH, index=False, encoding='utf-8')
print(f"✅ Dashboard guardado: {CSV_PATH}")

BREACHES_ASSET_PATH = f"{DIRS['reports']}/breaches_asset.csv"
breaches_asset.to_csv(BREACHES_ASSET_PATH, index=False)
print(f"✅ Brechas por activo: {BREACHES_ASSET_PATH}")

BREACHES_REGION_PATH = f"{DIRS['reports']}/breaches_region.csv"
breaches_region.to_csv(BREACHES_REGION_PATH, index=False)
print(f"✅ Brechas por región: {BREACHES_REGION_PATH}")

# --- Guardar resumen para orquestador ---
risk_summary = {
    "fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
    "estado_general": estado_general,
    "drawdown": float(current_dd),
    "retorno_cartera": float(annual_return),
    "alpha": float(alpha) if pd.notna(alpha) else None,
    "brechas": {
        "activos": len(breaches_asset),
        "regiones": len(breaches_region)
    },
    "usd_no_hedged_pct": float(usd_unhedged_pct)
}

JSON_PATH = f"{DIRS['reports']}/risk_dashboard_latest.json"
with open(JSON_PATH, "w") as f:
    json.dump(risk_summary, f, indent=2)
print(f"✅ Resumen para orquestador: {JSON_PATH}")

# --- REGISTRAR SEÑAL PARA EVALUACIÓN ---
# Corregido: usar lógica separada para el f-string
if pd.notna(alpha):
    alpha_str = f"{alpha:.1%}"
else:
    alpha_str = "N/A"

recomendacion_estado = f"Estado de riesgo: {estado_general} - Drawdown: {current_dd:.1%}, Alpha vs S&P500: {alpha_str}"
log_signal(
    agente="risk_manager",
    tipo_senal="riesgo_general",
    recomendacion=recomendacion_estado,
    contexto={
        "liquidez_regime": liquidity_regime,
        "market_regime": "Risk-off" if red_alert or amber_alert else "Normal"
    },
    horizonte_eval="5d",
    metadata={
        "estado_general": estado_general,
        "drawdown": float(current_dd),
        "alpha": float(alpha) if pd.notna(alpha) else None,
        "brechas_activos": int(len(breaches_asset)),
        "brechas_regiones": int(len(breaches_region)),
        "usd_no_hedged_pct": float(usd_unhedged_pct),
        "retorno_cartera": float(annual_return)
    }
)

print("\n✅ Risk Manager completado exitosamente.")

