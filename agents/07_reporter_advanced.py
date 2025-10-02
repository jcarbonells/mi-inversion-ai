#!/usr/bin/env python
# coding: utf-8

# In[4]:


# ============================================
# 07_reporter_advanced.ipynb - Informe tipo consultoría (MEJORADO + LIQUIDEZ + ROBUSTO + LOG)
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
import json
import re  # ✅ Añadido
from datetime import datetime

# Instalar y configurar dependencias al inicio
try:
    import google.generativeai as genai
    import gspread
    from gspread_dataframe import get_as_dataframe
    from google.auth import default
    from google.colab import auth, drive
    import markdown
    from weasyprint import HTML
except ImportError:
    get_ipython().system('pip -q install pandas google-generativeai openpyxl gspread gspread-dataframe markdown weasyprint')
    import google.generativeai as genai
    import gspread
    from gspread_dataframe import get_as_dataframe
    from google.auth import default
    from google.colab import auth, drive
    import markdown
    from weasyprint import HTML

# --- Configuración y Montaje de Drive ---
drive.mount('/content/drive', force_remount=False)

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

# --- API KEY DE GEMINI ---
GEMINI_API_KEY = "AIzaSyCjID5QZSe0xDvGaq7mTHcHOctWBaxaAn8"  # ← TU CLAVE
genai.configure(api_key=GEMINI_API_KEY)

BASE = "/content/drive/MyDrive/investment_ai"
DIRS = {
    "portfolio": f"{BASE}/data/portfolio",
    "reports": f"{BASE}/reports"
}

# --- Leer cartera desde Google Sheet ---
try:
    auth.authenticate_user()
    creds, _ = default()
    gc = gspread.authorize(creds)
    sh = gc.open("portfolio_holdings")
    ws = sh.sheet1
    pf = get_as_dataframe(ws, evaluate_formulas=True, header=0).dropna(how="all")
    print("✅ Cartera cargada desde Google Sheet.")
except Exception as e:
    raise FileNotFoundError(f"Error al cargar 'portfolio_holdings' de Google Sheet: {e}")

# Normalizar columnas
pf.columns = [c.strip().lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "") for c in pf.columns]
pf = pf.rename(columns={
    "producto__cuenta": "nombre",
    "importe_actual_(€)": "importe_actual_eur"
})

# Limpiar importe
def clean_currency(x):
    """Limpia formatos de moneda, manejando separadores de miles y decimales."""
    if pd.isna(x) or x is None: return 0.0
    s = str(x).strip().replace("€", "").replace(" ", "")

    # Patrón más robusto para formato europeo (1.234,56)
    if re.search(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0

pf["importe_actual_eur"] = pf["importe_actual_eur"].apply(clean_currency)

# --- Asegurar columnas clave ---
if "modulo" not in pf.columns:
    pf["modulo"] = "Otros"
if "bloque" not in pf.columns:
    pf["bloque"] = "Otros"

# --- Preparar datos para el Contexto ---
pf_display = pf[['modulo', 'bloque', 'nombre', 'ticker_yf', 'importe_actual_eur']].copy()
# Formatear el importe y añadir el porcentaje para ayudar a la IA a construir la tabla 0
total_value = pf_display['importe_actual_eur'].sum()
pf_display['Importe (€)'] = pf_display['importe_actual_eur'].apply(lambda x: f"{x:,.0f} €")
pf_display['% Cartera'] = (pf_display['importe_actual_eur'] / total_value * 100).apply(lambda x: f"{x:.1f} %")
pf_display = pf_display.rename(columns={'nombre': 'Producto'})

# --- LEER OTROS DATOS ---
risk_path = f"{DIRS['reports']}/risk_dashboard.csv"
risk = pd.read_csv(risk_path) if os.path.exists(risk_path) else pd.DataFrame()

quant_path = f"{DIRS['reports']}/quant_signals.csv"
quant = pd.read_csv(quant_path) if os.path.exists(quant_path) else pd.DataFrame()

fx_path = f"{DIRS['reports']}/fx_hedge_signal.csv"
fx = pd.read_csv(fx_path) if os.path.exists(fx_path) else pd.DataFrame()

# --- Función robusta para extraer KPIs del risk dashboard ---
def extract_kpi_from_risk(risk_df, kpi_name):
    """Extrae un KPI del risk dashboard de forma robusta."""
    if risk_df.empty:
        return "N/A"

    # Encontrar la columna de métrica (maneja diferentes nombres)
    metric_col = None
    value_col = None

    for col in risk_df.columns:
        col_lower = col.lower().strip()
        if 'métrica' in col_lower or 'metrica' in col_lower or 'metric' in col_lower:
            metric_col = col
        elif 'valor' in col_lower or 'value' in col_lower:
            value_col = col

    if not metric_col or not value_col:
        return "N/A"

    # Buscar la fila que contiene el KPI
    mask = risk_df[metric_col].astype(str).str.contains(kpi_name, case=False, na=False)
    if mask.any():
        return risk_df.loc[mask, value_col].iloc[0]
    return "N/A"

# --- CONSTRUIR LA VARIABLE 'CONTEXT' CORRECTAMENTE ---
# 1. Indicadores clave (usando función robusta)
drawdown = extract_kpi_from_risk(risk, 'Drawdown')
alpha = extract_kpi_from_risk(risk, 'Alpha')

kpis_context = f"""
- Valor total cartera: {total_value:,.0f} €
- Drawdown actual: {drawdown}
- Alpha vs S&P 500: {alpha}
"""

# 2. Composición Detallada (Usando el dataframe pre-formateado)
portfolio_context = pf_display[['modulo', 'bloque', 'Producto', 'ticker_yf', 'Importe (€)', '% Cartera']].to_string(index=False)

# 3. Señales Cuantitativas
quant_context = quant[['Activo', 'Señal']].to_string(index=False) if not quant.empty else 'Sin señales cuantitativas relevantes este mes.'

# 4. Señales FX
fx_context = fx[['divisa', 'cobertura_recomendada', '%_cobertura']].to_string(index=False) if not fx.empty else 'Sin necesidad de nuevas coberturas de divisa.'

# --- ANÁLISIS DE LIQUIDEZ COMPLETO (ÚNICO BLOQUE) ---
liquidity_context = "No disponible"
factores_emergentes = "No disponible"
liquidity_regime = "Neutral"  # Para contexto en log_signal

# Leer régimen de liquidez y riesgos
liquidity_path_md = f"{DIRS['reports']}/liquidity_dashboard_latest.md"
liquidity_path_json = f"{DIRS['reports']}/liquidity_regime_latest.json"

if os.path.exists(liquidity_path_json):
    try:
        # Leer datos estructurados del JSON
        with open(liquidity_path_json, 'r', encoding='utf-8') as f:
            liquidity_data = json.load(f)

        # Extraer régimen y score
        regimen = liquidity_data.get("regimen", "No disponible")
        score = liquidity_data.get("score", "No disponible")
        liquidity_regime = regimen  # Guardar para log_signal

        # Construir contexto principal
        liquidity_context = f"Régimen de Liquidez: {regimen} (Score: {score}/7)"

        # Extraer riesgos con alerta
        riesgos = liquidity_data.get("riesgos", [])
        riesgos_alerta = [r["nombre"] for r in riesgos if r.get("alerta", False)]
        if riesgos_alerta:
            liquidity_context += f"\nRiesgos Críticos: {', '.join(riesgos_alerta)}"

        # Extraer factores emergentes
        factores = liquidity_data.get("factores_emergentes", {})
        factores_list = []
        if factores.get("deficit_bn") is not None:
            factores_list.append(f"Déficit fiscal: {factores['deficit_bn']:.0f}B USD")
        if factores.get("usdc_bn") is not None:
            factores_list.append(f"Liquidez crypto: {factores['usdc_bn']:.1f}B USD")
        if factores_list:
            factores_emergentes = "; ".join(factores_list)

    except Exception as e:
        liquidity_context = f"Error al leer análisis de liquidez: {e}"
        factores_emergentes = "Error al cargar factores emergentes"

# --- Construir el contexto final ---
context_with_liquidity = f"""
## DATOS CLAVE
{kpis_context}

## ANÁLISIS DE LIQUIDEZ GLOBAL
{liquidity_context}

## FACTORES EMERGENTES
{factores_emergentes}

## DATOS DETALLE CARTERA (para usar en la Tabla 0 del output)
{portfolio_context}

## DATOS ANÁLISIS CUANTITATIVO
- Señales cuantitativas del mercado:
{quant_context}

- Señales de cobertura de divisas (FX):
{fx_context}
"""

# --- RESTO DEL PROMPT IGUAL ---
full_prompt = f"""
# Prompt Optimizado para Agente 'reporter_advanced'

## ROL Y OBJETIVO
Actúas como un **Consultor de Inversiones Senior** (estilo McKinsey). Tu especialidad es transformar datos brutos de cartera en un informe ejecutivo que sea **claro, conciso, estructurado y visualmente atractivo**. Priorizas el análisis *data-driven* y las **recomendaciones accionables**, presentadas en un formato profesional.

## TAREA PRINCIPAL
Utilizando **exclusivamente** los datos de entrada proporcionados en la sección 'DATOS DE ENTRADA', debes generar un informe de cartera mensual en **formato Markdown**. Tu tarea principal es:
1.  **Rellenar la tabla de la Sección 0** con los datos de detalle de la cartera proporcionados en el contexto (sección DATOS DETALLE CARTERA).
2.  **Analizar los KPIs y las Señales** para rellenar de forma coherente y lógica las secciones "Diagnóstico", "Escenarios de riesgo" y "Recomendaciones".
3.  **Integrar el análisis de liquidez global** en las recomendaciones y escenarios de riesgo.
4.  Debes seguir de forma **ESTRICTA E INFLEXIBLE** el formato, tono y estructura del ejemplo de referencia.

## FORMATO DE SALIDA Y EJEMPLO DE REFERENCIA (ESTRICTO)
El resultado final debe ser un **único bloque de texto en Markdown**, replicando **EXACTAMENTE** la estructura, emojis, tablas, encabezados de sección y estilo del siguiente ejemplo. **NO INVENTES SECCIONES O SUBSECCIONES.**

--- INICIO EJEMPLO DE FORMATO ---
# 📑 Informe de Cartera — [MES ACTUAL] [AÑO ACTUAL]

## 0. Detalle actual de la cartera
*(Rellenar esta tabla usando los datos en 'DATOS DETALLE CARTERA', pero agrupando por Módulo. Añade una fila de sumatorio por Módulo, como en el ejemplo. Debes calcular los subtotales de módulo y el % de cartera de cada línea y módulo.)*

| Módulo | Bloque | Producto | ticker_yf | Importe (€) | % Cartera |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **[Módulo X – Nombre (Suma €)]** | | | | **[Suma €]** | **[Suma %]** |
| | Bloque A | Producto 1 | Ticker 1 | Importe 1 | % 1 |
| | Bloque B | Producto 2 | Ticker 2 | Importe 2 | % 2 |
| **[Módulo Y – Nombre (Suma €)]** | | | | **[Suma €]** | **[Suma %]** |
| | Bloque C | Producto 3 | Ticker 3 | Importe 3 | % 3 |
| *... y así sucesivamente para todos los módulos/bloques ...*

---
## 1. Distribución global
- **Liquidez:** [Valor %] 🟢/🟡/🔴 *(Comentario breve)*
- **Renta Fija:** [Valor %] 🟢/🟡/🔴 *(Comentario breve)*
- **RV Core:** [Valor %] 🟢/🟡/🔴 *(Comentario breve)*
- *... (Añadir puntos clave de distribución) ...*

## 2. Panel de señales
- [Resumen de señales cuantitativas, ej. 5 verdes, 1 rojo].
- 👉 **Régimen [Defensivo/Ofensivo]** (score ≈ [Estimación 0.00-1.00]).
- 💧 **Liquidez Global:** [Expansivo/Neutral/Contractivo] (Score: X.X/7).
- ⚠️ **Riesgos Críticos:** [Lista de riesgos con alerta, si existen].

## 3. Diagnóstico
*(Análisis conciso de los KPIs (Valor Total, Drawdown, Alpha) y las distribuciones. Máximo 5 líneas.)*

## 4. Escenarios de riesgo
*(Describe brevemente 2-3 riesgos clave identificados a partir del Drawdown, las Señales Cuantitativas/FX, y el análisis de liquidez global. Incluye riesgos cuantificados como: tensión geopolítica, sostenibilidad de deuda, shocks de cadena de suministro, etc. No te inventes métricas.)*

## 5. Recomendaciones
*(Formula 3-5 recomendaciones accionables y específicas, incluyendo las señales de cobertura FX si aplican, cómo mitigar el Drawdown o mejorar el Alpha, y considerando el entorno de liquidez y riesgos identificados.)*

## 6. Próximos hitos
*(Inventa 3-4 hitos de inversión a futuro basados en un plan de inversión genérico (ej. aportaciones mensuales a RV) para mantener la estructura.)*

---
### 📌 Conclusión Ejecutiva
*(Resumen de la tesis de inversión y las recomendaciones más urgentes. Máximo 3 líneas.)*
--- FIN EJEMPLO DE FORMATO ---

## REGLAS Y RESTRICCIONES
1.  **Adherencia Absoluta:** La estructura (incluyendo la línea horizontal `---`) y los emojis (📑, 🟢, 🟡, 🔴, 👉, 💧, ⚠️, 📌) **no son negociables**.
2.  **Formato Técnico:** DEBES usar formato Markdown (`## Títulos`, `**Negritas**`, `Tablas Markdown`).
3.  **Concisión:** El informe completo **no debe superar las 500 palabras**.
4.  **No-alucinación:** Usa solo los datos proporcionados en 'DATOS DE ENTRADA'. **No inventes tickers, productos o métricas.**
5.  **Integración de liquidez:** Debes mencionar explícitamente el régimen de liquidez y cualquier riesgo crítico identificado en las secciones 2, 4 y 5.

## DATOS DE ENTRADA PARA EL INFORME ACTUAL
{context_with_liquidity}
"""

# --- Llamar a Gemini ---
model = genai.GenerativeModel('models/gemini-2.5-flash')
response = model.generate_content(full_prompt)

print(response.text)

# --- Guardar el informe en un archivo ---
today = datetime.now().strftime('%Y%m%d')
report_path = f"{DIRS['reports']}/report_final_{today}.md"

# Guardar el informe en formato Markdown
with open(report_path, "w", encoding='utf-8') as f:
    f.write(response.text)

print(f"\n✅ Informe guardado en: {report_path}")

# --- También guardar una versión en PDF (opcional pero recomendado) ---
try:
    from markdown import markdown
    from weasyprint import HTML

    # Convertir Markdown a HTML
    html_text = markdown(response.text)

    # Añadir estilos básicos
    styled_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            h1, h2 {{ color: #2c3e50; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #bdc3c7; padding: 12px; text-align: left; }}
            th {{ background-color: #ecf0f1; }}
            .conclusion {{ background-color: #f8f9fa; padding: 20px; border-left: 4px solid #3498db; }}
        </style>
    </head>
    <body>
        {html_text}
    </body>
    </html>
    """

    # Guardar como PDF
    pdf_path = f"{DIRS['reports']}/report_final_{today}.pdf"
    HTML(string=styled_html).write_pdf(pdf_path)
    print(f"✅ Versión PDF guardada en: {pdf_path}")

except Exception as e:
    print(f"⚠️ No se pudo generar PDF: {e}")
    print("✅ Informe en Markdown guardado correctamente.")

# --- REGISTRAR SEÑAL PARA EVALUACIÓN ---
# Extraer información clave del informe generado
import re

# Buscar alpha y drawdown en el texto del informe
alpha_match = re.search(r"Alpha vs S&P 500: ([^\\n]+)", response.text)
drawdown_match = re.search(r"Drawdown actual: ([^\\n]+)", response.text)

alpha_str = alpha_match.group(1) if alpha_match else "N/A"
drawdown_str = drawdown_match.group(1) if drawdown_match else "N/A"

recomendacion_general = f"Informe generado - Alpha: {alpha_str}, Drawdown: {drawdown_str}"

log_signal(
    agente="reporter_advanced",
    tipo_senal="informe_generado",
    recomendacion=recomendacion_general,
    contexto={
        "liquidez_regime": liquidity_regime,
        "market_regime": "Risk-off" if "drawdown" in drawdown_str.lower() and "-" in drawdown_str else "Normal"
    },
    horizonte_eval="5d",
    metadata={
        "fecha_informe": today,
        "alpha": alpha_str,
        "drawdown": drawdown_str,
        "liquidez_regime": liquidity_regime,
        "total_activos": len(pf),
        "valor_total": float(total_value)
    }
)

print("\n✅ Reporter Advanced completado exitosamente.")

