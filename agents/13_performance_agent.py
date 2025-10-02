#!/usr/bin/env python
# coding: utf-8

# In[9]:


# ============================================
# 13_performance_agent.ipynb - Evaluación de Rendimiento de Agentes
# ============================================

# --- 1. Montar Google Drive (¡ES IMPRESCINDIBLE!) ---
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

# --- 2. Imports ---
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
import yfinance as yf

# --- 3. Configuración de rutas (¡IDÉNTICA al FX Agent!) ---
BASE = "/content/drive/MyDrive/investment_ai"
SIGNALS_LOG_PATH = f"{BASE}/data/signals_emitted.csv"
REPORTS_DIR = f"{BASE}/reports"

# --- 4. Verificación de rutas (para depuración) ---
print("🔍 Verificando rutas...")
print(f"BASE: {BASE}")
print(f"¿Existe BASE? {os.path.exists(BASE)}")
print(f"¿Existe carpeta data? {os.path.exists(f'{BASE}/data')}")
print(f"¿Existe signals_emitted.csv? {os.path.exists(SIGNALS_LOG_PATH)}")
print("-" * 50)

# --- 5. Crear carpeta de reports si no existe ---
os.makedirs(REPORTS_DIR, exist_ok=True)

# %%
# 1. Cargar señales emitidas
if not os.path.exists(SIGNALS_LOG_PATH):
    print("⚠️ No hay señales registradas. Ejecuta primero los agentes emisores (ej. 03_fx_agent).")
    exit()

signals_df = pd.read_csv(SIGNALS_LOG_PATH, encoding="utf-8")

# Parsear metadata (de str a dict)
import json as json_lib
signals_df["metadata"] = signals_df["metadata"].apply(
    lambda x: json_lib.loads(x) if pd.notna(x) and x != "{}" else {}
)

print(f"📊 Cargadas {len(signals_df)} señales emitidas.")

# %%
# 2. Función para evaluar señales FX
def evaluar_senal_fx(row):
    """
    Evalúa si una señal de cobertura FX fue acertada.
    """
    fecha_emision = datetime.strptime(row["fecha_emision"], "%Y-%m-%d")
    horizonte = row["horizonte_eval"]

    try:
        dias = int(horizonte.replace("d", ""))
    except:
        dias = 5

    fecha_eval = fecha_emision + timedelta(days=dias)

    # Si aún no ha pasado el horizonte, no evaluar
    if datetime.today().date() < fecha_eval.date():
        return None

    recomendacion = row["recomendacion"].lower()
    metadata = row["metadata"]

    # --- Señal POSITIVA: se recomienda cobertura ---
    if "cobertura fx recomendada para:" in recomendacion:
        # Obtener divisas a cubrir desde metadata
        divisas = metadata.get("divisas_a_cubrir", [])
        if "USD" in divisas:
            dxy = yf.download("DX=F", start=fecha_emision, end=fecha_eval + timedelta(days=1), progress=False)
            if len(dxy) < 2:
                return None
            retorno_dxy = (dxy["Close"].iloc[-1] / dxy["Close"].iloc[0]) - 1
            return retorno_dxy > 0.015  # USD se fortaleció >1.5%
        return None  # otra divisa (no evaluamos por ahora)

    # --- Señal NEGATIVA: no se recomienda cobertura ---
    elif "no se recomienda cobertura" in recomendacion:
        # Solo evaluamos si había exposición significativa a USD
        divisas_analizadas = metadata.get("divisas_analizadas", [])
        if "USD" in divisas_analizadas:
            dxy = yf.download("DX=F", start=fecha_emision, end=fecha_eval + timedelta(days=1), progress=False)
            if len(dxy) < 2:
                return None
            retorno_dxy = (dxy["Close"].iloc[-1] / dxy["Close"].iloc[0]) - 1
            return retorno_dxy < 0.010  # USD no se fortaleció significativamente
        return True  # no había USD → correcto no cubrir

    return None

# %%
# 3. Aplicar evaluación SOLO a señales FX
signals_df["resultado"] = signals_df.apply(
    lambda row: evaluar_senal_fx(row) if row["agente"] == "fx_agent" else None,
    axis=1
)
signals_df["evaluable"] = signals_df["resultado"].notna()

# Guardar para auditoría
signals_df.to_csv(f"{BASE}/data/signals_emitted_with_results.csv", index=False)

# %%
# %%
# 4. Calcular métricas por agente
performance = {}

for agente in signals_df["agente"].unique():
    df_agente = signals_df[(signals_df["agente"] == agente) & (signals_df["evaluable"])]
    if len(df_agente) == 0:
        continue

    # --- Asegurar que 'aciertos' sea un entero escalar ---
    aciertos_raw = df_agente["resultado"].sum()
    if isinstance(aciertos_raw, pd.Series):
        aciertos = int(aciertos_raw.iloc[0]) if len(aciertos_raw) > 0 else 0
    else:
        aciertos = int(aciertos_raw)

    total = len(df_agente)
    precision = aciertos / total if total > 0 else 0.0

    # --- Precisión últimos 30 días ---
    df_reciente = df_agente[
        pd.to_datetime(df_agente["fecha_emision"]) >= (datetime.today() - timedelta(days=30))
    ]
    if len(df_reciente) > 0:
        reciente_sum = df_reciente["resultado"].sum()
        if isinstance(reciente_sum, pd.Series):
            reciente_sum = reciente_sum.iloc[0] if len(reciente_sum) > 0 else 0
        precision_30d = float(reciente_sum) / len(df_reciente)
    else:
        precision_30d = None

    performance[agente] = {
        "precision_total": round(precision, 4),
        "aciertos": aciertos,  # ya es int
        "total_señales": total,
        "precision_30d": round(precision_30d, 4) if precision_30d is not None else None,
        "ultima_evaluacion": datetime.today().strftime("%Y-%m-%d")
    }

# %%
# 5. Guardar resultados
if performance:
    # JSON
    with open(f"{REPORTS_DIR}/performance_summary.json", "w", encoding="utf-8") as f:
        json.dump(performance, f, indent=2, ensure_ascii=False)

    # Markdown
    md = "# 📊 Desempeño de los Agentes\n\n"
    for agente, stats in performance.items():
        md += f"## {agente}\n"
        md += f"- **Precisión total**: {stats['precision_total']*100:.1f}% ({stats['aciertos']}/{stats['total_señales']})\n"
        if stats["precision_30d"] is not None:
            md += f"- **Precisión últimos 30 días**: {stats['precision_30d']*100:.1f}%\n"
        md += "\n"

    with open(f"{REPORTS_DIR}/performance_summary.md", "w", encoding="utf-8") as f:
        f.write(md)

    print("✅ Informe de desempeño generado:")
    print(f"   - JSON: {REPORTS_DIR}/performance_summary.json")
    print(f"   - Markdown: {REPORTS_DIR}/performance_summary.md")

    # Mostrar tabla
    display(pd.DataFrame(performance).T)

    # Alertas
    for agente, stats in performance.items():
        if stats["precision_total"] < 0.60 and stats["total_señales"] >= 3:
            print(f"🚨 ALERTA: {agente} tiene precisión baja ({stats['precision_total']*100:.1f}%)")
else:
    print("ℹ️ No hay señales evaluable aún. Espera al menos 5 días tras emitir señales.")

