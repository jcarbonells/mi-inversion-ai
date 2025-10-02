#!/usr/bin/env python
# coding: utf-8

# In[1]:


# ============================================
# 00_liquidity_agent.ipynb - Agente de Liquidez Global (Riesgos Cuantificados + JSON Safe)
# ============================================

get_ipython().system('pip -q install pandas fredapi yfinance')

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
import json
import pandas as pd
import numpy as np
from datetime import datetime
from fredapi import Fred
import yfinance as yf

# --- MONTAR GOOGLE DRIVE ---
try:
    from google.colab import drive
    drive.mount('/content/drive')
    print("✅ Google Drive montado.")
except:
    print("ℹ️ No en Colab o ya montado.")

# --- Configuración ---
BASE = "/content/drive/MyDrive/investment_ai"
REPORTS_DIR = f"{BASE}/reports"
FRED_API_KEY = "2c229e32f3ee5ac1a8939904319d1d7a"  # ⚠️ Reemplaza con tu clave
fred = Fred(api_key=FRED_API_KEY)

# --- FUNCIONES: 4 CAPAS PRINCIPALES ---
def get_m2_yoy():
    try:
        m2 = fred.get_series('M2SL', observation_start='2015-01-01').dropna()
        return (m2.pct_change(periods=12) * 100).iloc[-1]
    except:
        return np.nan

def get_fed_balance_change_bn():
    try:
        assets = fred.get_series('WALCL', observation_start='2024-01-01').dropna()
        if len(assets) >= 20:
            return (assets.iloc[-1] - assets.iloc[-20]) / 1000
        return np.nan
    except:
        return np.nan

def get_real_rate():
    try:
        fed_rate = fred.get_series('DFF', observation_start='2024-01-01').iloc[-1]
        cpi = fred.get_series('CPIAUCSL', observation_start='2024-01-01')
        cpi_yoy = cpi.pct_change(periods=12).iloc[-1] * 100
        return fed_rate - cpi_yoy
    except:
        return 0.0

def get_pmi_global():
    try:
        oecd = fred.get_series('CLITOTL10USD', observation_start='2020-01-01').dropna()
        return (oecd.iloc[-1] - 0.98) * 1000
    except:
        return 51.0

def get_vix_level():
    try:
        return yf.Ticker("^VIX").history(period="5d")["Close"].iloc[-1]
    except:
        return 20.0

# --- FUNCIONES: FACTORES EMERGENTES ---
def get_usdc_circulation():
    try:
        usdc = fred.get_series('USDCIRCTOT', observation_start='2020-01-01').dropna()
        return usdc.iloc[-1] / 1e9
    except:
        return None

def get_fiscal_deficit():
    try:
        deficit = fred.get_series('FYFSD', observation_start='2020-01-01').dropna()
        return -deficit.iloc[-1] / 1e3
    except:
        return None

def get_corporate_cash():
    try:
        cash = fred.get_series('TOTCI', observation_start='2015-01-01').dropna()
        return cash.iloc[-1] / 1e3
    except:
        return None

# --- FUNCIONES: RIESGOS CUANTIFICABLES ---
def get_debt_to_gdp():
    try:
        return fred.get_series('GFDEGDQ188S', observation_start='2020-01-01').iloc[-1]
    except:
        return None

def get_geopolitical_risk():
    try:
        return fred.get_series('GEPUGLOBAL', observation_start='2020-01-01').iloc[-1]
    except:
        return None

def get_ppi_mom():
    try:
        ppi = fred.get_series('PPIACO', observation_start='2024-01-01').dropna()
        return ppi.pct_change().iloc[-1] * 100
    except:
        return None

def get_em_liquidity_proxy():
    try:
        dxy = yf.Ticker("DX-Y.NYB").history(period="5d")["Close"].iloc[-1]
        eem = yf.Ticker("EEM").history(period="5d")["Close"].iloc[-1]
        eem_prev = yf.Ticker("EEM").history(period="10d")["Close"].iloc[-5]
        eem_change = ((eem - eem_prev) / eem_prev) * 100
        return {"dxy": dxy, "eem_change": eem_change}
    except:
        return None

# --- FUNCIÓN PARA SERIALIZAR A JSON (CORRECCIÓN CLAVE) ---
def convert_to_serializable(obj):
    if isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj) if not np.isnan(obj) else None
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    elif isinstance(obj, (np.bool_, np.bool)):
        return bool(obj)
    else:
        return obj

# --- EJECUCIÓN ---
print("💧 Ejecutando Agente de Liquidez Global (Riesgos Cuantificados)...")

# Capas principales
m2_yoy = get_m2_yoy()
fed_delta_bn = get_fed_balance_change_bn()
real_rate = get_real_rate()
pmi_global = get_pmi_global()
vix = get_vix_level()

# Factores emergentes
usdc_bn = get_usdc_circulation()
deficit_bn = get_fiscal_deficit()
corp_cash_bn = get_corporate_cash()

# Riesgos cuantificados
debt_gdp = get_debt_to_gdp()
geo_risk = get_geopolitical_risk()
ppi_shock = get_ppi_mom()
em_data = get_em_liquidity_proxy()

# --- SCORING ---
score = 0
m2_ok = pd.notna(m2_yoy)
fed_ok = pd.notna(fed_delta_bn)

if m2_ok:
    if m2_yoy > 8: score += 2
    elif m2_yoy > 4: score += 1
if fed_ok:
    if fed_delta_bn > 50: score += 2
    elif fed_delta_bn > 0: score += 1
if pmi_global > 52: score += 2
elif pmi_global > 50: score += 1
if real_rate < -0.5: score += 1
elif real_rate < 0: score += 0.5
if vix < 15: score += 1
elif vix < 20: score += 0.5

# --- RÉGIMEN FINAL ---
if score >= 5.5:
    regimen = "Expansivo"
    emoji = "🟢"
elif score >= 3:
    regimen = "Neutral"
    emoji = "🟠"
else:
    regimen = "Contractivo"
    emoji = "🔴"

# --- TABLA DE CAPAS ---
def get_semaphore(value, layer):
    if layer == "capa1" and pd.notna(value):
        return "🟢" if value > 8 else "🟠" if value > 4 else "🔴"
    elif layer == "capa2" and pd.notna(value):
        return "🟢" if value > 0 else "🔴"
    elif layer == "capa3_pmi" and pd.notna(value):
        return "🟢" if value > 52 else "🟠" if value > 50 else "🔴"
    elif layer == "capa3_rate" and pd.notna(value):
        return "🟢" if value < -0.5 else "🟠" if value < 0 else "🔴"
    elif layer == "capa4" and pd.notna(value):
        return "🟢" if value < 15 else "🟠" if value < 25 else "🔴"
    return "⚪"

rows = []
m2_val = round(m2_yoy, 2) if m2_ok else None
m2_sem = get_semaphore(m2_yoy, "capa1") if m2_ok else "⚪"
m2_accion = "Sobreponderar riesgo" if m2_sem == "🟢" else "Neutral" if m2_sem == "🟠" else "Reducir exposición"
rows.append(["**1. Liquidez Base**", "M2 YoY", f"{m2_val:+.2f}%" if m2_ok else "N/A", "Crecimiento del dinero", m2_sem, m2_accion])

fed_val = round(fed_delta_bn, 1) if fed_ok else None
fed_sem = get_semaphore(fed_delta_bn, "capa2") if fed_ok else "⚪"
fed_accion = "Apoyo a mercados" if fed_sem == "🟢" else "Riesgo de tensión" if fed_sem == "🔴" else "Neutral"
rows.append(["**2. Liquidez Operativa**", "Balance Fed (4 sem)", f"{fed_val:+.1f}B" if fed_ok else "N/A", "Inyección/drenaje Fed", fed_sem, fed_accion])

pmi_val = round(pmi_global, 1)
rate_val = round(real_rate, 2)
pmi_sem = get_semaphore(pmi_global, "capa3_pmi")
rate_sem = get_semaphore(real_rate, "capa3_rate")
capa3_sem = "🟢" if pmi_sem == "🟢" and rate_sem == "🟢" else "🔴" if pmi_sem == "🔴" or rate_sem == "🔴" else "🟠"
capa3_accion = "Sobreponderar RV global" if capa3_sem == "🟢" else "Defensivos y efectivo" if capa3_sem == "🔴" else "Selectividad"
rows.append(["**3. Liquidez Real**", "PMI + Tasa Real", f"{pmi_val} / {rate_val:+.2f}%", "Actividad + costo dinero", capa3_sem, capa3_accion])

vix_val = round(vix, 1)
vix_sem = get_semaphore(vix, "capa4")
vix_accion = "Aprovechar momentum" if vix_sem == "🟢" else "Mantener cobertura" if vix_sem == "🔴" else "Operar normal"
rows.append(["**4. Liquidez de Mercado**", "VIX", f"{vix_val}", "Apetito por riesgo", vix_sem, vix_accion])

# --- TENDENCIAS Y DIVERGENCIAS ---
tendencias = []
if m2_ok:
    tendencias.append(f"• M2: +{m2_yoy:.1f}% YoY")
if fed_ok and fed_delta_bn < 0:
    tendencias.append(f"• Balance Fed: {fed_delta_bn:+.1f}B (drenaje)")

divergencias = []
if m2_ok and fed_ok and m2_yoy > 4 and fed_delta_bn < 0:
    divergencias.append("⚠️ M2 crece pero Fed drena liquidez")

# --- CONCLUSIÓN Y ASIGNACIÓN ---
if regimen == "Expansivo":
    conclusion = "✅ **Conclusión Estratégica**: Entorno óptimo para sobreponderar renta variable global, emergentes y activos alternativos."
elif regimen == "Neutral":
    conclusion = "⚠️ **Conclusión Estratégica**: Entorno moderado. Mantén diversificación equilibrada y busca calidad."
else:
    conclusion = "❌ **Conclusión Estratégica**: Entorno restrictivo. Aumenta efectivo, defensivos y activos de refugio."

asignacion = """**Asignación Táctica Recomendada:**
| Activo | Sesgo | Justificación |
|--------|------|--------------|
| Renta Variable Global | ⚖️ Neutral | PMI positivo pero tasa real restrictiva |
| Tech (QQQ) | ➕ Ligero sobreponder | Flujo de fondos fuerte, VIX bajo |
| Bonos Gobierno | ➖ Subponderar | Tasa real positiva |
| Oro | ➕ Neutral-alza | Hedge contra volatilidad |
| Efectivo | ➕ 5-10% | Opción de compra en corrección"""

# --- FACTORES EMERGENTES ---
factores_emergentes = []
if usdc_bn is not None:
    factores_emergentes.append(["Liquidez Crypto (USDC)", f"{usdc_bn:.1f}B USD", "Estable; sin presión de redención"])
if deficit_bn is not None:
    factores_emergentes.append(["Déficit Fiscal EE.UU.", f"{deficit_bn:.0f}B USD/año", "Estímulo fiscal significativo"])
if corp_cash_bn is not None:
    factores_emergentes.append(["Cash Corporativo", f"{corp_cash_bn:.0f}B USD", "Alto; potencial para buybacks"])

# --- RIESGOS MONITOREADOS ---
riesgos_monitoreados = []

if usdc_bn is not None:
    riesgos_monitoreados.append({
        "nombre": "Regulación de stablecoins",
        "valor": f"USDC: {usdc_bn:.1f}B USD",
        "nivel": "Bajo" if usdc_bn > 30 else "Moderado" if usdc_bn > 20 else "Alto",
        "alerta": usdc_bn < 20
    })

if debt_gdp is not None:
    riesgos_monitoreados.append({
        "nombre": "Sostenibilidad deuda pública",
        "valor": f"{debt_gdp:.1f}% del PIB",
        "nivel": "Alto" if debt_gdp > 120 else "Moderado" if debt_gdp > 100 else "Bajo",
        "alerta": debt_gdp > 120
    })

if geo_risk is not None:
    riesgos_monitoreados.append({
        "nombre": "Tensiones geopolíticas",
        "valor": f"Índice GPR: {geo_risk:.0f}",
        "nivel": "Alto" if geo_risk > 300 else "Moderado" if geo_risk > 150 else "Bajo",
        "alerta": geo_risk > 300
    })

if ppi_shock is not None:
    riesgos_monitoreados.append({
        "nombre": "Shocks cadena de suministro",
        "valor": f"PPI mensual: {ppi_shock:+.2f}%",
        "nivel": "Alto" if abs(ppi_shock) > 1.0 else "Moderado" if abs(ppi_shock) > 0.5 else "Bajo",
        "alerta": abs(ppi_shock) > 1.0
    })

if em_data is not None:
    dxy = em_data["dxy"]
    eem_change = em_data["eem_change"]
    nivel_em = "Alto" if dxy > 105 and eem_change < -3 else "Moderado" if dxy > 103 else "Bajo"
    riesgos_monitoreados.append({
        "nombre": "Liquidez en mercados emergentes",
        "valor": f"DXY: {dxy:.1f}, EEM: {eem_change:+.1f}%",
        "nivel": nivel_em,
        "alerta": nivel_em == "Alto"
    })

# --- MARKDOWN ---
tabla_resumen_md = "| Capa | Indicador | Resultado | Interpretación | Semáforo | Acción |\n|------|----------|----------|----------------|--------|--------|\n"
tabla_resumen_md += "\n".join([f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows])

factores_md = "\n".join([f"- **{f[0]}**: {f[1]} → {f[2]}" for f in factores_emergentes]) if factores_emergentes else "No disponible."

riesgos_md = "| Riesgo | Valor Actual | Nivel | Alerta |\n|--------|--------------|-------|--------|\n"
for r in riesgos_monitoreados:
    alert_icon = "⚠️" if r["alerta"] else "✅"
    riesgos_md += f"| {r['nombre']} | {r['valor']} | {r['nivel']} | {alert_icon} |\n"

output_md = f"""# 💧 Análisis de Liquidez Global ({datetime.today().strftime('%Y-%m-%d')})

**Régimen Final**: {emoji} **{regimen}** (Score: {score:.1f}/7)

## 📋 Resumen por Capas de Liquidez
{tabla_resumen_md}

## 🔍 Factores Adicionales de Liquidez
{factores_md}

## ⚠️ Riesgos Monitoreados (Antes "No Capturados")
{riesgos_md}

---

### 📈 Tendencias Recientes
{"\n".join(tendencias) if tendencias else "Ninguna."}

### ⚠️ Divergencias Detectadas
{"\n".join(divergencias) if divergencias else "Ninguna."}

---

{conclusion}

{asignacion}

> ℹ️ **Metodología**:
> - **Capas 1-4**: M2, Balance Fed, PMI+tasa real, VIX
> - **Factores emergentes**: USDC, Déficit fiscal, Cash corporativo
> - **Riesgos**: Deuda/PIB (`GFDEGDQ188S`), Riesgo geopolítico (`GEPUGLOBAL`), PPI (`PPIACO`), DXY/EEM
"""

# --- HTML ---
html_riesgos = "<table border='1' cellpadding='8' style='width:100%; margin:15px 0;'><tr><th>Riesgo</th><th>Valor</th><th>Nivel</th><th>Alerta</th></tr>"
for r in riesgos_monitoreados:
    alert_color = "#721c24" if r["alerta"] else "#155724"
    alert_icon = "⚠️" if r["alerta"] else "✅"
    html_riesgos += f"<tr><td>{r['nombre']}</td><td>{r['valor']}</td><td>{r['nivel']}</td><td style='color:{alert_color};'>{alert_icon}</td></tr>"
html_riesgos += "</table>"

html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>Liquidez Global</title>
<style>body{{font-family:Arial,sans-serif;max-width:1000px;margin:0 auto;padding:20px;}}
table{{width:100%;border-collapse:collapse;margin:15px 0;}}th,td{{padding:10px;border:1px solid #ddd;}}</style>
</head>
<body>
<h1>💧 Análisis de Liquidez Global</h1>
<div><strong>Régimen:</strong> {regimen} (Score: {score:.1f}/7)</div>

<h2>📋 Capas de Liquidez</h2>
<table>
<tr><th>Capa</th><th>Indicador</th><th>Resultado</th><th>Interpretación</th><th>Semáforo</th><th>Acción</th></tr>
{''.join([
    f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td></tr>"
    for r in rows
])}
</table>

<h2>⚠️ Riesgos Monitoreados</h2>
{html_riesgos}

<h2>🎯 Conclusión</h2>
<p>{conclusion.replace('**', '').replace('✅', '✅ ').replace('⚠️', '⚠️ ').replace('❌', '❌ ')}</p>
</body>
</html>
"""

# --- GUARDAR ARCHIVOS ---
os.makedirs(REPORTS_DIR, exist_ok=True)

# Preparar datos para JSON (¡CORREGIDO!)
full_data = {
    "regimen": regimen,
    "score": round(score, 1),
    "fecha": datetime.today().strftime('%Y-%m-%d'),
    "capas": {
        "m2_yoy": m2_val,
        "fed_delta_bn": fed_val,
        "pmi": pmi_val,
        "real_rate": rate_val,
        "vix": vix_val
    },
    "factores_emergentes": {
        "usdc_bn": usdc_bn,
        "deficit_bn": deficit_bn,
        "corp_cash_bn": corp_cash_bn
    },
    "riesgos": [
        {
            "nombre": r["nombre"],
            "valor": r["valor"],
            "nivel": r["nivel"],
            "alerta": r["alerta"]
        }
        for r in riesgos_monitoreados
    ]
}



# ¡CONVERSIÓN SEGURA ANTES DE GUARDAR!
full_data_safe = convert_to_serializable(full_data)

with open(f"{REPORTS_DIR}/liquidity_regime_latest.json", "w") as f:
    json.dump(full_data_safe, f, indent=2)

with open(f"{REPORTS_DIR}/liquidity_dashboard_latest.md", "w") as f:
    f.write(output_md)

with open(f"{REPORTS_DIR}/liquidity_dashboard_latest.html", "w", encoding="utf-8") as f:
    f.write(html_content)

# --- MOSTRAR EN PANTALLA ---
print("\n" + "="*60)
print("📄 INFORME COMPLETO")
print("="*60)
print(output_md)
print("="*60)

print(f"\n📂 Archivos generados en: {REPORTS_DIR}")
get_ipython().system('ls -l "{REPORTS_DIR}"')

# --- DESCARGAR EN COLAB ---
try:
    from google.colab import files
    files.download(f"{REPORTS_DIR}/liquidity_dashboard_latest.html")
    print("\n📥 HTML descargado a tu computadora.")
except:
    pass

print(f"\n📊 Régimen actual: {emoji} {regimen} (Score: {score:.1f}/7)")


# --- VERIFICAR SALIDAS ---
required_files = [
    f"{REPORTS_DIR}/liquidity_regime_latest.json",
    f"{REPORTS_DIR}/liquidity_dashboard_latest.md"
]

for f in required_files:
    if not os.path.exists(f):
        raise RuntimeError(f"❌ Archivo no generado: {f}")
    else:
        print(f"✅ {os.path.basename(f)} generado correctamente.")

