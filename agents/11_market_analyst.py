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

#!/usr/bin/env python
# coding: utf-8

# In[1]:


# ============================================
# 11_market_analyst.ipynb - Agente de Análisis de Mercado (MEJORADO + REPORTS + LOG)
# ============================================

import warnings, io, math, datetime as dt, sys, os, json, time
warnings.filterwarnings('ignore')

import numpy as np, pandas as pd, matplotlib.pyplot as plt, yfinance as yf, requests
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime

pd.set_option('display.float_format', lambda x: f"{x:,.2f}")
plt.rcParams.update({'figure.figsize': (26,18), 'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3})

HOY = pd.Timestamp.today().normalize()

# =====================
# FUNCIÓN PARA REGISTRAR SEÑALES (PARA PERFORMANCE AGENT)
# =====================
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

# =====================
# CONFIGURACIÓN DE REPORTS
# =====================
if os.path.exists("/content/drive"):
    BASE = "/content/drive/MyDrive/investment_ai"
    REPORTS_DIR = f"{BASE}/reports"
else:
    BASE = "investment_ai"
    REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)
print(f"📁 Carpeta de reports: {REPORTS_DIR}")

# =====================
# CONFIGURACIÓN
# =====================
CONFIG = {
    'start_date': '2000-01-01',
    'weights': {'M2': .20, 'RRP': .20, 'Curva': .15, 'HY_OAS': .15, 'NFCI': .15, 'Yield_10Y': .15},
    'thresholds': {
        'M2_up': 5.0, 'M2_down': -2.0,
        'RRP_low': 100, 'RRP_high': 2000,
        'Curva_up': .20, 'Curva_down': 0.0,
        'HY_up': 3.5, 'HY_down': 6.0,
        'NFCI_up': -0.30, 'NFCI_down': 0.30,
        'Y10_up': 3.0, 'Y10_down': 5.0
    },
    'yahoo': {
        '^GSPC': '^GSPC', 'QQQ': 'QQQ', 'IWD': 'IWD', 'IWM': 'IWM',
        'SPY': 'SPY', 'HYG': 'HYG', 'LQD': 'LQD', '^VIX': '^VIX', 'DX-Y.NYB': 'DXY'
    },
    'fred': {
        'M2SL': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=M2SL',
        'RRPONTSYD': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=RRPONTSYD',
        'T10Y2Y': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y',
        'DGS10': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10',
        'BAMLH0A0HYM2': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2',
        'NFCI': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=NFCI',
        'USREC': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=USREC',
    }
}

# =====================
# FUNCIONES UTILITARIAS
# =====================
def fred_csv(url, retries=3, timeout=10):
    """Descarga datos de FRED con reintentos."""
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text), sep=None, engine='python')
            df.columns = [c.strip().lower() for c in df.columns]
            col = 'observation_date' if 'observation_date' in df.columns else 'date'
            df[col] = pd.to_datetime(df[col])
            s = pd.to_numeric(df.iloc[:, 1], errors='coerce')
            s.index = df[col]
            return s.dropna().sort_index()
        except Exception as e:
            print(f"⚠️ Error descargando {url.split('=')[-1]} (intento {attempt+1}): {e}")
            time.sleep(2)
    return pd.Series(dtype=float)

resample_weekly = lambda s, anchor='FRI': s.resample(f'W-{anchor}').last().dropna() if len(s) else s
latest = lambda s: s.dropna().iloc[-1] if len(s.dropna()) else np.nan
yoy = lambda s, periods=52: s.pct_change(periods=periods) * 100

# =====================
# DESCARGA DE DATOS
# =====================
print('🔄 Descargando datos de FRED y Yahoo Finance...')
FRED = {k: fred_csv(url) for k, url in CONFIG['fred'].items()}
YAHOO = {}
for name, ticker in CONFIG['yahoo'].items():
    try:
        print(f"⬇️ Yahoo: {name} ({ticker})...")
        df = yf.download(ticker, start=CONFIG['start_date'], end=HOY.strftime('%Y-%m-%d'),
                         progress=False, auto_adjust=True, threads=False, timeout=10)
        YAHOO[name] = df['Close'].dropna()
    except Exception as e:
        print(f"❌ Error descargando {name}: {e}")
        YAHOO[name] = pd.Series(dtype=float)

# Validar series de FRED
for k, s in FRED.items():
    if len(s) < 10:
        print(f"⚠️ Serie {k} tiene pocos datos ({len(s)}). Usando serie vacía.")
        FRED[k] = pd.Series(dtype=float)

# Series clave
M2_w = resample_weekly(FRED['M2SL'])
RRP_w = resample_weekly(FRED['RRPONTSYD'])
T10Y2Y_w = resample_weekly(FRED['T10Y2Y'])
DGS10_w = resample_weekly(FRED['DGS10'])
HY_OAS_w = resample_weekly(FRED['BAMLH0A0HYM2'])
NFCI_w = resample_weekly(FRED['NFCI'])
USREC_w = resample_weekly(FRED['USREC'])
SPX_w = resample_weekly(YAHOO['^GSPC'])
QQQ, IWD, IWM, SPY, HYG, LQD = [YAHOO.get(k, pd.Series()) for k in ['QQQ','IWD','IWM','SPY','HYG','LQD']]

# Fecha efectiva de análisis (última fecha común)
all_dates = []
for s in list(FRED.values()) + list(YAHOO.values()):
    if len(s) > 0:
        all_dates.append(s.index[-1])
HOY_EFECTIVO = min(all_dates) if all_dates else HOY
print(f"📅 Fecha de análisis: {HOY_EFECTIVO.strftime('%Y-%m-%d')}")

# =====================
# SISTEMA DE SEMÁFOROS
# =====================
def bucket_from_value(name, value):
    """Convierte un valor en un semáforo (🟢/🟡/🔴)."""
    if np.isnan(value): return '🟡'
    t = CONFIG['thresholds']
    if name == 'M2': return '🟢' if value > t['M2_up'] else '🔴' if value < t['M2_down'] else '🟡'
    if name == 'RRP': return '🟢' if value < t['RRP_low'] else '🔴' if value > t['RRP_high'] else '🟡'
    if name == 'Curva': return '🟢' if value > t['Curva_up'] else '🔴' if value < t['Curva_down'] else '🟡'
    if name == 'HY_OAS': return '🟢' if value < t['HY_up'] else '🔴' if value > t['HY_down'] else '🟡'
    if name == 'NFCI': return '🟢' if value < t['NFCI_up'] else '🔴' if value > t['NFCI_down'] else '🟡'
    if name == 'Yield_10Y': return '🟢' if value < t['Y10_up'] else '🔴' if value > t['Y10_down'] else '🟡'
    return '🟡'

def get_semaforos(fecha_corte=None):
    """Genera el diccionario de semáforos con valores y mensajes."""
    if fecha_corte is None:
        fecha_corte = HOY_EFECTIVO

    def last_val(series):
        s = series[series.index <= fecha_corte]
        return latest(s)

    sem = {}
    sem['M2'] = {'bucket': bucket_from_value('M2', last_val(yoy(M2_w, 52))),
                 'value': last_val(yoy(M2_w, 52)), 'msg': f"{last_val(yoy(M2_w, 52)):.1f}% a/a"}
    sem['RRP'] = {'bucket': bucket_from_value('RRP', last_val(RRP_w)),
                  'value': last_val(RRP_w), 'msg': f"{last_val(RRP_w):,.0f} B$"}
    sem['Curva'] = {'bucket': bucket_from_value('Curva', last_val(T10Y2Y_w)),
                    'value': last_val(T10Y2Y_w), 'msg': f"{last_val(T10Y2Y_w):.2f}%"}
    sem['HY_OAS'] = {'bucket': bucket_from_value('HY_OAS', last_val(HY_OAS_w)),
                     'value': last_val(HY_OAS_w), 'msg': f"{last_val(HY_OAS_w):.2f}%"}
    sem['NFCI'] = {'bucket': bucket_from_value('NFCI', last_val(NFCI_w)),
                   'value': last_val(NFCI_w), 'msg': f"{last_val(NFCI_w):.2f}"}
    sem['Yield_10Y'] = {'bucket': bucket_from_value('Yield_10Y', last_val(DGS10_w)),
                        'value': last_val(DGS10_w), 'msg': f"{last_val(DGS10_w):.2f}%"}

    # Ratios de rotación
    for ratio, name in [(QQQ/IWD,'Growth_Value'),(IWM/SPY,'Small_Large'),(HYG/LQD,'HY_IG')]:
        r = resample_weekly(ratio[ratio.index >= pd.Timestamp('2000-01-01')])
        r_cut = r[r.index <= fecha_corte]
        if len(r_cut) >= 20:
            slope = np.polyfit(np.arange(len(r_cut.tail(20))), r_cut.tail(20), 1)[0]
            sem[name] = {'bucket': '🟢' if slope > 0 else '🔴',
                         'value': latest(r_cut), 'msg': f"trend {slope:.2f}"}
        else:
            sem[name] = {'bucket': '🟡', 'value': np.nan, 'msg': "Sin datos"}
    return sem

def score_regimen(sem):
    """Calcula el score y régimen a partir de los semáforos."""
    w = CONFIG['weights']
    convert = {'🟢': 1, '🟡': 0, '🔴': -1}
    score = sum(convert[sem[k]['bucket']] * w.get(k, 0) for k in w.keys() if k in sem)
    regime = '🟢 Ofensivo' if score > 0.25 else ('🔴 Defensivo' if score < -0.25 else '🟡 Neutral')
    return score, regime

def calcular_score_historico(freq='W-FRI'):
    """Calcula la evolución del score en el tiempo (optimizado)."""
    # Usar fecha de inicio realista para evitar datos vacíos
    start_real = max(pd.Timestamp('2003-01-01'), M2_w.index.min() if len(M2_w) else pd.Timestamp('2003-01-01'))
    fechas = pd.date_range(start=start_real, end=HOY_EFECTIVO, freq=freq)

    # Precalcular series derivadas una sola vez
    m2_yoy = yoy(M2_w, 52)
    ratios = {
        'Growth_Value': resample_weekly(QQQ / IWD),
        'Small_Large': resample_weekly(IWM / SPY),
        'HY_IG': resample_weekly(HYG / LQD)
    }

    scores = []
    for fecha in fechas:
        # Obtener valores en la fecha (sin recalcular todo)
        def val_at(series, f):
            s = series[series.index <= f]
            return latest(s) if len(s) > 0 else np.nan

        sem = {}
        sem['M2'] = bucket_from_value('M2', val_at(m2_yoy, fecha))
        sem['RRP'] = bucket_from_value('RRP', val_at(RRP_w, fecha))
        sem['Curva'] = bucket_from_value('Curva', val_at(T10Y2Y_w, fecha))
        sem['HY_OAS'] = bucket_from_value('HY_OAS', val_at(HY_OAS_w, fecha))
        sem['NFCI'] = bucket_from_value('NFCI', val_at(NFCI_w, fecha))
        sem['Yield_10Y'] = bucket_from_value('Yield_10Y', val_at(DGS10_w, fecha))

        # No incluimos ratios en el score (según CONFIG['weights'] no los incluye)
        score = sum({'🟢':1,'🟡':0,'🔴':-1}[sem[k]] * CONFIG['weights'][k] for k in CONFIG['weights'])
        scores.append(score)

    return pd.Series(scores, index=fechas).dropna()

def duracion_regimenes(score_series):
    """Calcula la duración promedio de cada régimen histórico."""
    if len(score_series) < 10:
        return pd.Series({'Ofensivo': np.nan, 'Neutral': np.nan, 'Defensivo': np.nan})
    df = pd.DataFrame({'score': score_series})
    df['regimen'] = df['score'].apply(
        lambda x: 'Ofensivo' if x > 0.25 else ('Defensivo' if x < -0.25 else 'Neutral')
    )
    df['cambio'] = df['regimen'] != df['regimen'].shift(1)
    df['grupo'] = df['cambio'].cumsum()
    duraciones = df.groupby(['regimen', 'grupo']).size()
    return duraciones.groupby('regimen').mean().reindex(['Ofensivo', 'Neutral', 'Defensivo'])

# =====================
# GRÁFICOS CON GUARDADO EN REPORTS
# =====================
def graficos_completos():
    """Genera el dashboard visual de 7 paneles y lo guarda en /reports/."""
    start = pd.Timestamp('2000-01-01')
    spx = SPX_w[SPX_w.index>=start]
    curva = T10Y2Y_w[T10Y2Y_w.index>=start]
    hy = HY_OAS_w[HY_OAS_w.index>=start]
    m2 = M2_w[M2_w.index>=start]
    rrp = RRP_w[RRP_w.index>=start]
    y10 = DGS10_w[DGS10_w.index>=start]
    nfci = NFCI_w[NFCI_w.index>=start]
    score_hist = calcular_score_historico()

    def shade_recessions(ax):
        """Sombrea períodos de recesión en los gráficos."""
        if len(USREC_w) > 0:
            rec = USREC_w
            on = False; start_rec = None
            for d, val in rec.items():
                if val >= 0.5 and not on:
                    on = True; start_rec = d
                elif val < 0.5 and on:
                    ax.axvspan(start_rec, d, color='grey', alpha=0.15); on=False
            if on:
                ax.axvspan(start_rec, rec.index[-1], color='grey', alpha=0.15)

    fig, axes = plt.subplots(3, 3, figsize=(26, 18))
    fig.suptitle('📊 Dashboard Completo 2000-2025', fontsize=24, y=0.96)

    # 1. S&P vs Curva
    ax = axes[0,0]
    ax.plot(spx.index, spx, lw=3, label='S&P 500')
    ax2 = ax.twinx(); ax2.plot(curva.index, curva, lw=2, color='r')
    ax.set_title('S&P 500 vs Curva 10Y-2Y'); ax.legend(); ax2.legend(['10Y-2Y %'])
    shade_recessions(ax)

    # 2. S&P vs HY OAS
    ax = axes[0,1]
    ax.plot(spx.index, spx, lw=3, label='S&P 500')
    ax2 = ax.twinx(); ax2.plot(hy.index, hy, lw=2, color='green')
    ax.set_title('S&P 500 vs HY OAS'); ax.legend(); ax2.legend(['HY OAS %'])
    shade_recessions(ax)

    # 3. M2 vs RRP
    ax = axes[0,2]
    ax.plot(m2.index, m2/1e3, lw=3, label='M2 (Trillions)')
    ax2 = ax.twinx(); ax2.plot(rrp.index, rrp/1e3, lw=2, color='r')
    ax.set_title('M2 vs Reverse Repo'); ax.legend(); ax2.legend(['RRP (Trillions)'])
    shade_recessions(ax)

    # 4. S&P vs NFCI
    ax = axes[1,0]
    ax.plot(spx.index, spx, lw=3)
    ax2 = ax.twinx(); ax2.plot(nfci.index, nfci, lw=2)
    ax.set_title('S&P 500 vs NFCI'); ax.legend(['S&P 500']); ax2.legend(['NFCI'])
    shade_recessions(ax)

    # 5. 10Y Yield
    ax = axes[1,1]
    ax.plot(y10.index, y10, lw=3)
    for y in [3,4,5]:
        ax.axhline(y, ls='--', label=f'{y}%')
    ax.set_title('10-Year Treasury Yield'); ax.legend()
    shade_recessions(ax)

    # 6. Rotaciones
    ax = axes[1,2]
    for ratio, label in [(QQQ/IWD,'Growth/Value'),(IWM/SPY,'Small/Large'),(HYG/LQD,'HY/IG')]:
        r = resample_weekly(ratio[ratio.index>=start])
        if len(r):
            ax.plot(r.index, (r/r.iloc[0])*100, lw=2, label=label)
    ax.set_title('Rotation Ratios (base 100)'); ax.legend()

    # 7. Score de Régimen con eventos históricos
    ax = axes[2,0]
    ax.plot(score_hist.index, score_hist, lw=2, color='purple', label='Score')
    ax.axhline(0.25, color='green', ls='--', label='Umbral Ofensivo')
    ax.axhline(-0.25, color='red', ls='--', label='Umbral Defensivo')
    ax.axhline(0, color='gray', ls='-', alpha=0.5)

    # Eventos históricos clave
    eventos = {
        'GFC': '2008-09-01',
        'Euro Crisis': '2011-08-01',
        'Taper Tantrum': '2013-06-01',
        'Pandemia': '2020-02-01',
        'Inflación 2022': '2022-03-01'
    }
    for nombre, fecha_str in eventos.items():
        fecha = pd.Timestamp(fecha_str)
        if start <= fecha <= HOY_EFECTIVO and fecha in score_hist.index:
            ax.axvline(fecha, color='black', alpha=0.5, linestyle=':')
            ax.text(fecha, ax.get_ylim()[1]*0.9, nombre, rotation=90,
                    verticalalignment='top', fontsize=9, alpha=0.7)

    ax.set_title('Evolución del Score de Régimen (con eventos históricos)')
    ax.set_ylabel('Score')
    ax.legend()
    shade_recessions(ax)

    # Ocultar ejes vacíos
    for ax in [axes[2,1], axes[2,2]]:
        ax.axis('off')

    for ax in axes.flat:
        if ax.has_data():
            ax.set_xlim(start, HOY_EFECTIVO)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout(rect=[0,0,1,0.96])

    # Guardar y mostrar
    filepath = os.path.join(REPORTS_DIR, f"market_dashboard_{HOY_EFECTIVO.strftime('%Y%m%d')}.png")
    plt.savefig(filepath, dpi=300)
    print(f"📊 Dashboard guardado: {filepath}")
    plt.show()
    return fig

# =====================
# FORMATO EXACTO SOLICITADO
# =====================
def informe_formato_exacto():
    """Genera el informe en el formato exacto solicitado."""
    sem = get_semaforos()
    score, regime = score_regimen(sem)

    # 1. INTERPRETACIÓN DETALLADA
    print("\n" + "="*80)
    print("🔍 INTERPRETACIÓN DETALLADA DE SEMÁFOROS")
    print("="*80)

    interpretaciones = {
        'M2': { '🟢': "💰 Liquidez abundante: M2 >5% estimula crecimiento y mercados riesgo",
                '🟡': "⚖️ M2 estable: crecimiento monetario adecuado",
                '🔴': "💸 M2 contractivo: restricción monetaria"},
        'RRP': { '🟢': "🏦 Sistema líquido: RRP <100B indica efectivo disponible",
                 '🟡': "⚖️ RRP moderado: liquidez controlada",
                 '🔴': "🚨 RRP elevado: liquidez estancada"},
        'Curva': { '🟢': "📈 Curva normal: expectativas de crecimiento",
                   '🟡': "⚖️ Curva plana: incertidumbre",
                   '🔴': "📉 Curva invertida: señal recesiva"},
        'HY_OAS': { '🟢': "💪 Apetito riesgo: spreads bajos indican confianza",
                    '🟡': "⚖️ Spreads moderados",
                    '🔴': "⚠️ Tensión crediticia"},
        'NFCI': { '🟢': "💸 Condiciones laxas: acceso al crédito facilitado",
                  '🟡': "⚖️ Condiciones neutrales",
                  '🔴': "🏛️ Condiciones restrictivas"},
        'Yield_10Y': { '🟢': "📉 Tasas bajas: favorable para crecimiento",
                       '🟡': "⚖️ Tasas moderadas",
                       '🔴': "📈 Tasas altas: presión sobre valoraciones"}
    }

    for key, data in sem.items():
        if key in interpretaciones:
            print(f"\n{data['bucket'][:2]} {key} ({data['msg']})")
            print(f"   └─ {interpretaciones[key][data['bucket']]}")

    # 2. HISTÓRICO SEMANAL
    print("\n" + "="*80)
    print("📊 HISTÓRICO SEMANAL (Últimos 12 períodos)")
    print("="*80)

    fechas_semanales = pd.date_range(end=HOY_EFECTIVO, periods=12, freq='W-FRI')
    hist_semanal = []

    for fecha in fechas_semanales:
        sem_hist = get_semaforos(fecha_corte=fecha)
        vals = {
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'M2': sem_hist['M2']['bucket'],
            'RRP': sem_hist['RRP']['bucket'],
            'Curva': sem_hist['Curva']['bucket'],
            'HY_OAS': sem_hist['HY_OAS']['bucket'],
            'NFCI': sem_hist['NFCI']['bucket'],
            'Yield_10Y': sem_hist['Yield_10Y']['bucket']
        }
        score_hist = sum({'🟢':1,'🟡':0,'🔴':-1}[vals[k]] * CONFIG['weights'][k] for k in CONFIG['weights'])
        vals['Régimen'] = '🟢 Ofensivo' if score_hist > 0.25 else ('🔴 Defensivo' if score_hist < -0.25 else '🟡 Neutral')
        vals['Score'] = round(score_hist, 3)
        hist_semanal.append(vals)

    df_semanal = pd.DataFrame(hist_semanal)
    print(df_semanal.to_string(index=False))

    # Tendencia semanal dinámica
    scores_sem = [h['Score'] for h in hist_semanal]
    if len(scores_sem) >= 4:
        x = np.arange(len(scores_sem[-4:]))
        slope = np.polyfit(x, scores_sem[-4:], 1)[0]
        tendencia = "Alcista 📈" if slope > 0.01 else ("Bajista 📉" if slope < -0.01 else "Lateral ➖")
    else:
        tendencia, slope = "Insuficiente historial", 0.0

    print(f"\n📈 ANÁLISIS DE TENDENCIA")
    print("-" * 40)
    print(f"✅ Últimos 4 semanas: {tendencia}")
    print(f"   Pendiente del score: {slope:.3f}")
    print(f"   Score promedio: {np.mean(scores_sem):.3f}")

    # 3. HISTÓRICO MENSUAL
    print("\n" + "="*80)
    print("📊 HISTÓRICO MENSUAL (Últimos 12 períodos)")
    print("="*80)

    fechas_mensuales = pd.date_range(end=HOY_EFECTIVO, periods=12, freq='M')
    hist_mensual = []

    for fecha in fechas_mensuales:
        sem_hist = get_semaforos(fecha_corte=fecha)
        vals = {
            'Fecha': fecha.strftime('%Y-%m-%d'),
            'M2': sem_hist['M2']['bucket'],
            'RRP': sem_hist['RRP']['bucket'],
            'Curva': sem_hist['Curva']['bucket'],
            'HY_OAS': sem_hist['HY_OAS']['bucket'],
            'NFCI': sem_hist['NFCI']['bucket'],
            'Yield_10Y': sem_hist['Yield_10Y']['bucket']
        }
        score_hist = sum({'🟢':1,'🟡':0,'🔴':-1}[vals[k]] * CONFIG['weights'][k] for k in CONFIG['weights'])
        vals['Régimen'] = '🟢 Ofensivo' if score_hist > 0.25 else ('🔴 Defensivo' if score_hist < -0.25 else '🟡 Neutral')
        vals['Score'] = round(score_hist, 3)
        hist_mensual.append(vals)

    df_mensual = pd.DataFrame(hist_mensual)
    print(df_mensual.to_string(index=False))

    # Tendencia mensual
    scores_mens = [h['Score'] for h in hist_mensual]
    if len(scores_mens) >= 4:
        x = np.arange(len(scores_mens[-4:]))
        slope_m = np.polyfit(x, scores_mens[-4:], 1)[0]
        tendencia_m = "Alcista 📈" if slope_m > 0.01 else ("Bajista 📉" if slope_m < -0.01 else "Lateral ➖")
    else:
        tendencia_m, slope_m = "Insuficiente historial", 0.0

    print(f"\n📈 ANÁLISIS DE TENDENCIA")
    print("-" * 40)
    print(f"✅ Últimos 4 meses: {tendencia_m}")
    print(f"   Pendiente del score: {slope_m:.3f}")
    print(f"   Score promedio: {np.mean(scores_mens):.3f}")

    # 4. ALERTAS
    print("\n" + "="*80)
    print("⚠️ ALERTAS DE MERCADO ACTIVAS")
    print("="*80)
    alertas = []
    if sem['Curva']['bucket'] == '🟢':
        alertas.append(f"🟢 Curva normalizada ({sem['Curva']['value']:.2f}%) → Se puede aumentar riesgo")
    if sem['RRP']['bucket'] == '🟢':
        alertas.append(f"🟢 RRP muy bajo ({sem['RRP']['value']:.0f} B$) → Liquidez abundante")
    if sem['HY_OAS']['bucket'] == '🟢' and sem['HY_OAS']['value'] < 3.0:
        alertas.append("⚠️ HY OAS extremadamente bajo → Posible sobrevaloración")
    if not alertas:
        alertas.append("✅ Sin alertas críticas. Mercado en equilibrio.")

    for alerta in alertas: print(f"   {alerta}")

    # 5. RECOMENDACIONES
    print("\n" + "="*80)
    print("💡 ACCIONES SUGERIDAS")
    print("="*80)
    score_float = float(score)

    if score_float > 0.5:
        acciones = [
            "1. Aumentar equity global +8-12p.p. priorizando Quality/Momentum",
            "2. Añadir +2-3p.p. duración (EUR/UST) si VIX <20",
            "3. Entradas por tramos 1-2% semanal, stop 8% bajo máximos"
        ]
    elif 0.25 < score_float <= 0.5:
        acciones = [
            "1. Aumentar equity +5-8p.p. con foco en dividendos estables",
            "2. Mantener duración actual, preparar compras en dips",
            "3. Rotación sectorial hacia industriales y tech"
        ]
    elif -0.25 <= score_float <= 0.25:
        acciones = [
            "1. Mantener exposición actual, rebalancing mensual",
            "2. Barbell RF: 50% corto plazo + 50% 5-7 años",
            "3. Estrategias de cobertura parciales"
        ]
    else:
        acciones = [
            "1. Reducir equity -5-10p.p., aumentar cash a 15-20%",
            "2. Acortar duración, preferir IG corto plazo",
            "3. Implementar stops dinámicos 5-7%"
        ]

    print("\n".join(acciones))

    # 6. RESUMEN FINAL INTEGRADO
    print("\n" + "="*80)
    print("🎯 RESUMEN FINAL INTEGRADO")
    print("="*80)

    # Percentil histórico
    score_hist_full = calcular_score_historico(freq='W-FRI')
    if len(score_hist_full) > 50:
        percentil = (score_hist_full < score).mean() * 100
        print(f"Score: {score:.3f} | Régimen: {regime}")
        print(f"📅 Fecha: {HOY_EFECTIVO.strftime('%Y-%m-%d')} | Percentil histórico: {percentil:.0f}%")
    else:
        print(f"Score: {score:.3f} | Régimen: {regime} | Fecha: {HOY_EFECTIVO.strftime('%Y-%m-%d')}")

    # Duración típica
    duracion_media = duracion_regimenes(score_hist_full)
    regimen_actual = "Ofensivo" if score > 0.25 else ("Defensivo" if score < -0.25 else "Neutral")
    dur_actual = duracion_media.get(regimen_actual, np.nan)
    if not pd.isna(dur_actual):
        print(f"⏱️  Duración media del régimen '{regimen_actual}': {dur_actual:.1f} semanas")

    # Sensibilidad
    print("\n🔍 Sensibilidad del régimen:")
    sem_actual = get_semaforos()
    cambios_criticos = []
    for k in CONFIG['weights']:
        if sem_actual[k]['bucket'] == '🔴':
            sim_bucket = '🟢'
        elif sem_actual[k]['bucket'] == '🟢':
            sim_bucket = '🔴'
        else:
            for sim_b in ['🟢', '🔴']:
                score_sim = score + ({'🟢':1,'🟡':0,'🔴':-1}[sim_b] - {'🟢':1,'🟡':0,'🔴':-1}[sem_actual[k]['bucket']]) * CONFIG['weights'][k]
                if (score <= 0.25 and score_sim > 0.25) or (score >= -0.25 and score_sim < -0.25):
                    cambios_criticos.append(f"{k} → {sim_b}")
            continue

        score_sim = score + ({'🟢':1,'🟡':0,'🔴':-1}[sim_bucket] - {'🟢':1,'🟡':0,'🔴':-1}[sem_actual[k]['bucket']]) * CONFIG['weights'][k]
        if (score <= 0.25 and score_sim > 0.25) or (score >= -0.25 and score_sim < -0.25):
            cambios_criticos.append(f"{k} → {sim_bucket}")

    if cambios_criticos:
        print("   ⚠️  Cambios que alterarían el régimen:")
        for cambio in cambios_criticos[:3]:
            print(f"      • {cambio}")
    else:
        print("   ✅ Ningún indicador individual cambiaría el régimen actual.")

    # Exportar a JSON
    exportar_resultados_json(sem, score, regime, hist_semanal, hist_mensual, alertas, acciones, score_hist_full=score_hist_full)

def exportar_resultados_json(sem, score, regime, hist_semanal, hist_mensual, alertas, acciones, score_hist_full=None):
    """Exporta resultados estructurados en JSON a la carpeta /reports/."""
    resultado = {
        "fecha_analisis": HOY_EFECTIVO.strftime('%Y-%m-%d'),
        "score": round(float(score), 3),
        "regimen": regime,
        "semaforos": {k: v['bucket'] for k, v in sem.items() if k in CONFIG['weights']},
        "valores_numericos": {k: float(v['value']) if not pd.isna(v['value']) else None
                             for k, v in sem.items() if k in CONFIG['weights']},
        "historico_semanal": hist_semanal,
        "historico_mensual": hist_mensual,
        "alertas": alertas,
        "recomendaciones": acciones,
        "percentil_historico": (score_hist_full < score).mean() * 100 if score_hist_full is not None and len(score_hist_full) > 50 else None
    }

    filename = f"analisis_mercado_{HOY_EFECTIVO.strftime('%Y%m%d')}.json"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"\n📤 Resultados completos exportados a: {filepath}")

    # Versión ligera para orquestador
    resumen = {
        "fecha": HOY_EFECTIVO.strftime('%Y-%m-%d'),
        "regimen": regime,
        "score": round(float(score), 3),
        "percentil": resultado["percentil_historico"]
    }
    latest_path = os.path.join(REPORTS_DIR, "market_regime_latest.json")
    with open(latest_path, "w") as f:
        json.dump(resumen, f, indent=2)
    print(f"📤 Archivo latest para orquestador: {latest_path}")

    # =====================
    # REGISTRAR SEÑAL PARA EVALUACIÓN
    # =====================
    # Leer régimen de liquidez (para contexto en log_signal)
    liquidity_regime = "Neutral"
    liquidity_path = f"{REPORTS_DIR}/liquidity_regime_latest.json"
    if os.path.exists(liquidity_path):
        try:
            with open(liquidity_path, "r") as f:
                liquidity_data = json.load(f)
                liquidity_regime = liquidity_data.get("regimen", "Neutral")
        except Exception:
            pass
    print(f"💧 Régimen de liquidez (contexto): {liquidity_regime}")

    recomendacion_estado = f"Régimen de mercado: {regime} - Score: {score:.3f} - Percentil: {resultado['percentil_historico']:.1f}%"
    log_signal(
        agente="market_analyst",
        tipo_senal="regimen_mercado",
        recomendacion=recomendacion_estado,
        contexto={
            "liquidez_regime": liquidity_regime,
            "market_regime": regime
        },
        horizonte_eval="5d",
        metadata={
            "regimen": regime,
            "score": float(score),
            "percentil_historico": resultado["percentil_historico"],
            "fecha_analisis": HOY_EFECTIVO.strftime('%Y-%m-%d'),
            "semaforos": {k: v['bucket'] for k, v in sem.items() if k in CONFIG['weights']},
            "valores_numericos": {k: float(v['value']) if not pd.isna(v['value']) else None
                                 for k, v in sem.items() if k in CONFIG['weights']},
            "alertas_activas": len(alertas),
            "acciones_sugeridas": len(acciones)
        }
    )

# =====================
# EJECUCIÓN
# =====================
if __name__ == "__main__":
    print("✅ Iniciando agente de análisis de mercado...")
    informe_formato_exacto()
    print("\n✅ Generando gráficos...")
    fig = graficos_completos()
    print("✅ Análisis de mercado completado.")

