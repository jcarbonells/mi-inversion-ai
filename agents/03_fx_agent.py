#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# ¡Obligatorio en cada notebook!
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


from google.colab import drive
drive.mount('/content/drive', force_remount=False)

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "reports": f"{BASE}/reports",
    "clean": f"{BASE}/data/clean"
}


# --- Calibración Dinámica (desde orquestador) ---
import os
FX_AGENT_WEIGHT = float(os.getenv("FX_AGENT_WEIGHT", 1.0))
print(f"⚖️ Peso del FX Agent: {FX_AGENT_WEIGHT:.2f}")

# Ajustar sensibilidad según el peso
FX_THRESHOLD = 0.10 / FX_AGENT_WEIGHT  # Ej: peso=1.2 → umbral=8.3%
print(f"📉 Umbral de exposición ajustado: {FX_THRESHOLD:.1%}")



from google.colab import drive
drive.mount('/content/drive')

# Verificar que el archivo existe
import os

BASE = "/content/drive/MyDrive/investment_ai"
ENRICHED_PATH = f"{BASE}/reports/portfolio_enriched_final.csv"

if os.path.exists(ENRICHED_PATH):
    print("✅ Archivo encontrado en:", ENRICHED_PATH)
else:
    print("❌ Archivo NO encontrado en:", ENRICHED_PATH)

# ============================================
# BACKFILL HISTÓRICO DE SEÑALES FX
# ============================================
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta

# Configuración
BASE = "/content/drive/MyDrive/investment_ai"
HISTORIC_DATES = pd.date_range(
    start=datetime.today() - timedelta(weeks=12),  # Últimas 12 semanas
    end=datetime.today(),
    freq='W-MON'  # Lunes de cada semana
).strftime("%Y-%m-%d").tolist()

print(f"🔄 Generando señales históricas para {len(HISTORIC_DATES)} fechas...")

# Cargar datos históricos que SÍ tienes
daily_path = f"{BASE}/reports/portfolio_daily_value.csv"
daily = pd.read_csv(daily_path, index_col=0, parse_dates=True) if os.path.exists(daily_path) else None

# Cartera actual como proxy (asumimos estable)
ENRICHED_PATH = f"{BASE}/reports/portfolio_enriched_final.csv"
pf = pd.read_csv(ENRICHED_PATH)
total_portfolio = pf["importe_actual_eur"].sum()
exp_div = pf.groupby("divisa_base")["importe_actual_eur"].sum().to_frame()
exp_div.columns = ["importe_eur"]

# Mapeo FX
FX_MAP = {"USD": "EURUSD=X", "GBP": "EURGBP=X", "CHF": "EURCHF=X", "JPY": "EURJPY=X"}
FX_THRESHOLD = 0.10

# Cargar FX históricos
fx_prices = pd.read_parquet(f"{BASE}/data/clean/fx_rates_clean.parquet")

for fecha_str in HISTORIC_DATES:
    fecha = pd.to_datetime(fecha_str)

    # 1. Obtener drawdown en esa fecha
    risk_off = False
    if daily is not None and fecha in daily.index:
        dd = daily.loc[fecha, "drawdown"] if "drawdown" in daily.columns else 0
        risk_off = dd < -0.05

    # 2. Simular régimen de liquidez (aquí usarías un historial si lo tuvieras)
    # Por ahora, asumimos "Neutral" o usamos una regla simple
    liquidity_regime = "Contractivo" if fecha.month in [1, 2, 9, 10] else "Expansivo"  # ejemplo
    geo_alert = False
    usd_adjustment = fecha.year == 2025 and fecha.month >= 4  # ejemplo: déficit desde abr 2025

    # 3. Generar señal (misma lógica que en el FX Agent)
    fx_signals = []
    for divisa, row in exp_div.iterrows():
        if divisa == "EUR": continue
        exposure_pct = row["importe_eur"] / total_portfolio
        if exposure_pct < FX_THRESHOLD: continue

        if divisa not in FX_MAP: continue
        fx_ticker = FX_MAP[divisa]
        if fx_ticker not in fx_prices.columns: continue

        # Obtener precio en esa fecha
        if fecha not in fx_prices.index: continue
        price = fx_prices.loc[fecha, fx_ticker]

        # Aquí pondrías la lógica real (tendencia, vol, etc.)
        # Para simplificar, asumimos cobertura si liquidez contractiva
        hedge = liquidity_regime == "Contractivo"
        hedge_pct = 75 if hedge else 0

        if hedge and divisa == "USD" and usd_adjustment:
            hedge_pct = 80

        fx_signals.append({
            "divisa": divisa,
            "exposicion_%": exposure_pct,
            "cobertura_recomendada": "Sí" if hedge else "No",
            "%_cobertura": hedge_pct,
            "risk_off": risk_off,
            "regimen_liquidez": liquidity_regime
        })

    # 4. Registrar señal (con fecha histórica)
    if fx_signals:
        divisas_a_cubrir = [s["divisa"] for s in fx_signals if s["cobertura_recomendada"] == "Sí"]
        recomendacion = f"Cobertura FX recomendada para: {', '.join(divisas_a_cubrir)} (simulado {fecha_str})"
        metadata = {"divisas_a_cubrir": divisas_a_cubrir, "simulado": True}
    else:
        recomendacion = "No se recomienda cobertura FX (simulado)"
        metadata = {"divisas_analizadas": exp_div.index.tolist(), "simulado": True}

    # Guardar en signals_emitted.csv con fecha histórica
    SIGNALS_LOG_PATH = f"{BASE}/data/signals_emitted.csv"
    new_row = {
        "fecha_emision": fecha_str,
        "agente": "fx_agent",
        "tipo_senal": "cobertura_fx",
        "recomendacion": recomendacion,
        "contexto_liquidez": liquidity_regime,
        "contexto_mercado": "Risk-off" if risk_off else "Normal",
        "horizonte_eval": "5d",
        "señal_id": f"fx_sim_{fecha_str.replace('-', '')}",
        "metadata": json.dumps(metadata)
    }

    # Añadir al CSV
    if os.path.exists(SIGNALS_LOG_PATH):
        df = pd.read_csv(SIGNALS_LOG_PATH)
    else:
        df = pd.DataFrame(columns=new_row.keys())
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(SIGNALS_LOG_PATH, index=False)

print("✅ Señales históricas generadas y registradas.")


# In[1]:


# ============================================
# 03_fx_agent.ipynb - Señal de cobertura FX (MEJORADO + LIQUIDEZ + CALIBRACIÓN)
# ============================================

# --- 1. Montar Google Drive ---
from google.colab import drive
drive.mount('/content/drive', force_remount=False)

# --- 2. Imports y configuración ---
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "reports": f"{BASE}/reports",
    "clean": f"{BASE}/data/clean"
}

# --- 3. FUNCIÓN PARA REGISTRAR SEÑALES (PARA PERFORMANCE AGENT) ---
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

# --- 4. Parámetros dinámicos (desde orquestador) ---
FX_AGENT_WEIGHT = float(os.getenv("FX_AGENT_WEIGHT", 1.0))
FX_THRESHOLD = 0.10 / FX_AGENT_WEIGHT  # Ajustado por rendimiento

print(f"⚖️ Peso del FX Agent: {FX_AGENT_WEIGHT:.2f}")
print(f"📉 Umbral de exposición ajustado: {FX_THRESHOLD:.1%}")

# --- 5. Leer cartera enriquecida ---
ENRICHED_PATH = f"{DIRS['reports']}/portfolio_enriched_final.csv"
if not os.path.exists(ENRICHED_PATH):
    raise FileNotFoundError("❌ Ejecuta primero 02_portfolio_exposure.ipynb")

pf = pd.read_csv(ENRICHED_PATH)
total_portfolio = pf["importe_actual_eur"].sum()

if total_portfolio == 0:
    raise ValueError("❌ El valor total de la cartera es 0.")

# Calcular exposición por divisa_base
exp_div = pf.groupby("divisa_base")["importe_actual_eur"].sum().to_frame()
exp_div.columns = ["importe_eur"]
exp_div.index.name = "divisa"

print("=== 🌍 EXPOSICIÓN POR DIVISA (desde cartera enriquecida) ===")
print(exp_div.to_string())

# --- 6. Leer tipos de cambio ---
fx_path = f"{DIRS['clean']}/my_portfolio_prices_clean.parquet"  # o fx_rates_clean.parquet
if not os.path.exists(fx_path):
    raise FileNotFoundError("❌ Ejecuta primero 01_data_prep.ipynb")

fx_prices = pd.read_parquet(fx_path)
if fx_prices.empty:
    raise ValueError("❌ El archivo de tipos de cambio está vacío.")

# --- 7. Leer régimen de mercado (drawdown) ---
daily_path = f"{DIRS['reports']}/portfolio_daily_value.csv"
current_dd = 0.0
risk_off = False
if os.path.exists(daily_path):
    try:
        daily = pd.read_csv(daily_path, index_col=0, parse_dates=True)
        if "drawdown" in daily.columns and not daily["drawdown"].empty:
            current_dd = daily["drawdown"].min()
            risk_off = current_dd < -0.05  # Drawdown > 5%
        print(f"📉 Drawdown actual: {current_dd:.2%} → Risk-off: {risk_off}")
    except Exception as e:
        print(f"⚠️ Error al leer drawdown: {e}. Asumiendo risk-off = False.")
else:
    print("⚠️ portfolio_daily_value.csv no encontrado. Asumiendo risk-off = False.")

# --- 8. Leer régimen de liquidez ---
liquidity_regime = "Neutral"
liquidity_score = 0
liquidity_data = {}
geo_alert = False
usd_adjustment = False

liquidity_path = f"{DIRS['reports']}/liquidity_regime_latest.json"

if os.path.exists(liquidity_path):
    try:
        with open(liquidity_path, "r") as f:
            liquidity_data = json.load(f)
            liquidity_regime = liquidity_data.get("regimen", "Neutral")
            liquidity_score = liquidity_data.get("score", 0)
        print(f"💧 Régimen de liquidez: {liquidity_regime} (Score: {liquidity_score})")

        # Análisis de riesgos
        riesgos = liquidity_data.get("riesgos", [])
        geo_alert = any(
            r.get("alerta") and "geopol" in r.get("nombre", "").lower()
            for r in riesgos
        )

        # Factores emergentes
        fiscal_deficit = liquidity_data.get("factores_emergentes", {}).get("deficit_bn", 0)
        if fiscal_deficit and fiscal_deficit > 1000:  # > 1T USD
            print("  💰 Déficit fiscal elevado → presión sobre USD")
            usd_adjustment = True
        else:
            usd_adjustment = False

    except Exception as e:
        print(f"⚠️ Error al leer régimen de liquidez: {e}. Asumiendo 'Neutral'.")
else:
    print("⚠️ liquidity_regime_latest.json no encontrado. Asumiendo régimen 'Neutral'.")

# --- 9. Configuración ---
VOL_WINDOW = 30
TREND_WINDOW = 90

# Mapeo extensible de divisas → pares FX
FX_MAP = {
    "USD": "EURUSD=X",
    "GBP": "EURGBP=X",
    "CHF": "EURCHF=X",
    "JPY": "EURJPY=X"
}

# --- 10. Generar señales ---
fx_signals = []

for divisa, row in exp_div.iterrows():
    if divisa == "EUR":
        continue

    exposure_eur = row["importe_eur"]
    exposure_pct = exposure_eur / total_portfolio

    if exposure_pct < FX_THRESHOLD:
        print(f"\n🔍 Ignorando {divisa}: exposición baja ({exposure_pct:.1%})")
        continue

    print(f"\n🔍 Analizando divisa: {divisa} ({exposure_pct:.1%})")

    if divisa not in FX_MAP:
        print(f"  ⚠️ Divisa no soportada: {divisa}. Soportadas: {list(FX_MAP.keys())}")
        continue

    fx_ticker = FX_MAP[divisa]
    if fx_ticker not in fx_prices.columns:
        print(f"  ⚠️ Par FX no encontrado: {fx_ticker}")
        continue

    fx_series = fx_prices[fx_ticker].dropna()
    if len(fx_series) < max(200, TREND_WINDOW):
        print(f"  ⚠️ Datos insuficientes para {fx_ticker} (necesario: 200, actual: {len(fx_series)})")
        continue

    # Calcular tendencia y volatilidad
    sma_short = fx_series.rolling(50).mean().iloc[-1]
    sma_long = fx_series.rolling(200).mean().iloc[-1]
    trend_bearish = sma_short < sma_long  # EUR se debilita → cobertura

    returns = fx_series.pct_change().dropna()
    vol_30d = returns.tail(VOL_WINDOW).std() * np.sqrt(252)
    high_vol = vol_30d > 0.10  # 10% anualizada

    # Decisión base
    hedge = False
    hedge_pct = 0

    if trend_bearish:
        hedge = True
        hedge_pct = 75
    if high_vol:
        hedge = True
        hedge_pct = max(hedge_pct, 50)
    if risk_off:
        hedge = True
        hedge_pct = 100
    if liquidity_regime == "Contractivo":
        hedge = True
        hedge_pct = max(hedge_pct, 75)
    elif liquidity_regime == "Expansivo":
        if not (trend_bearish or high_vol or risk_off):
            hedge = False
            hedge_pct = 0

    # ✅ AJUSTES POR RIESGOS (solo si ya hay cobertura)
    if hedge:
        if geo_alert and divisa in ["USD", "EUR"]:
            hedge_pct = min(hedge_pct + 25, 100)
            print("  🌍 Ajuste por riesgo geopolítico: cobertura aumentada")
        if divisa == "USD" and usd_adjustment:
            hedge_pct = max(hedge_pct, 80)
            print("  💰 Ajuste por déficit fiscal: cobertura USD aumentada")

    print(f"  ✅ Tendencia bajista: {trend_bearish}, Alta vol: {high_vol}, Risk-off: {risk_off}")
    print(f"  💧 Régimen de liquidez: {liquidity_regime}")
    print(f"  📌 Cobertura: {'Sí' if hedge else 'No'} ({hedge_pct}%)")

    fx_signals.append({
        "divisa": divisa,
        "exposicion_eur": exposure_eur,
        "exposicion_%": exposure_pct,
        "cobertura_recomendada": "Sí" if hedge else "No",
        "%_cobertura": hedge_pct,
        "tendencia_bajista": trend_bearish,
        "alta_volatilidad": high_vol,
        "risk_off": risk_off,
        "regimen_liquidez": liquidity_regime,
        "volatilidad_anualizada_%": vol_30d,
        "sma_50": sma_short,
        "sma_200": sma_long
    })

# --- 11. Mostrar resultado, guardar y REGISTRAR SEÑAL ---
if fx_signals:
    signals_df = pd.DataFrame(fx_signals)
    print("\n=== 🌐 SEÑAL DE COBERTURA FX (DETALLADA) ===")
    print(signals_df.round(4).to_string())

    # Guardar CSV
    csv_path = f"{DIRS['reports']}/fx_hedge_signal.csv"
    signals_df.to_csv(csv_path, index=False)
    print(f"\n✅ Señal guardada en: {csv_path}")

    # Construir recomendaciones detalladas
    divisas_a_cubrir = []
    recomendaciones = {}

    for s in fx_signals:
        if s["cobertura_recomendada"] == "Sí":
            divisa = s["divisa"]
            divisas_a_cubrir.append(divisa)
            razones = []
            if s["tendencia_bajista"]:
                razones.append("Tendencia")
            if s["alta_volatilidad"]:
                razones.append("Volatilidad")
            if s["risk_off"]:
                razones.append("Risk-off")
            if s["regimen_liquidez"] == "Contractivo":
                razones.append("Liquidez Contractiva")

            recomendaciones[divisa] = {
                "exposicion_%": float(s["exposicion_%"]),  # asegurar tipo serializable
                "%_cobertura": int(s["%_cobertura"]),
                "razones": razones  # ✅ lista, no set
            }

    fx_summary = {
        "fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "divisas_a_cubrir": divisas_a_cubrir,
        "recomendaciones": recomendaciones,
        "total_divisas_analizadas": len(fx_signals),
        "regimen_liquidez": liquidity_regime
    }

    # Guardar JSON
    json_path = f"{DIRS['reports']}/fx_hedge_latest.json"
    with open(json_path, "w") as f:
        import json as json_lib
        json_lib.dump(fx_summary, f, indent=2)
    print(f"✅ Resumen para orquestador: {json_path}")

    # ✨ REGISTRAR SEÑAL PARA EVALUACIÓN ✨
    recomendacion_texto = f"Cobertura FX recomendada para: {', '.join(divisas_a_cubrir)} con ajustes por liquidez ({liquidity_regime}) y riesgos."
    log_signal(
        agente="fx_agent",
        tipo_senal="cobertura_fx",
        recomendacion=recomendacion_texto,
        contexto={
            "liquidez_regime": liquidity_regime,
            "market_regime": "Risk-off" if risk_off else "Normal"
        },
        horizonte_eval="5d",
        metadata={
            "divisas_a_cubrir": divisas_a_cubrir,
            "recomendaciones_detalle": recomendaciones,
            "score_liquidez": float(liquidity_score),
            "geo_alert": bool(geo_alert),
            "usd_adjustment": bool(usd_adjustment)
        }
    )

else:
    print("\n✅ No se requiere cobertura FX en este momento.")

    fx_summary = {
        "fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "divisas_a_cubrir": [],
        "recomendaciones": {},
        "total_divisas_analizadas": 0,
        "regimen_liquidez": liquidity_regime
    }

    json_path = f"{DIRS['reports']}/fx_hedge_latest.json"
    with open(json_path, "w") as f:
        import json as json_lib
        json_lib.dump(fx_summary, f, indent=2)
    print(f"✅ Resumen vacío guardado: {json_path}")

    # ✨ REGISTRAR SEÑAL NEGATIVA ✨
    log_signal(
        agente="fx_agent",
        tipo_senal="cobertura_fx",
        recomendacion="No se recomienda cobertura FX en este momento.",
        contexto={
            "liquidez_regime": liquidity_regime,
            "market_regime": "Risk-off" if risk_off else "Normal"
        },
        horizonte_eval="5d",
        metadata={
            "divisas_analizadas": exp_div.index.tolist(),
            "score_liquidez": float(liquidity_score),
            "geo_alert": bool(geo_alert)
        }
    )

print("\n✅ FX Agent completado exitosamente.")

