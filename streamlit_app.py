import streamlit as st
import google.generativeai as genai
import os
import json
from datetime import datetime
import pandas as pd

# Configurar API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY", "TU_API_KEY_AQUI_TEMPORAL"))
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.0-flash')

# Rutas del sistema
BASE_DIR = os.path.dirname(__file__)
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DATA_DIR = os.path.join(BASE_DIR, "data")

st.set_page_config(page_title="🧠 Asesor Financiero AI", layout="wide")
st.title("🧠 Asesor Financiero con GenAI")
st.markdown("*Sistema de inversión autónomo basado en análisis cuantitativo y macroeconómico*")

# Sidebar con información del sistema
with st.sidebar:
    st.header("📊 Estado del Sistema")
    
    # Cargar datos reales del sistema si existen
    try:
        # Intentar cargar métricas reales de tus agentes
        metrics_file = os.path.join(REPORTS_DIR, "portfolio_metrics.json")
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            st.metric("Valor Cartera", f"{metrics.get('total_value', '884.024 €')}")
            st.metric("Alpha vs S&P", f"{metrics.get('alpha', '-8.4%')}")
            st.metric("Drawdown", f"{metrics.get('drawdown', '-3.8%')}")
        else:
            st.metric("Valor Cartera", "884.024 €")
            st.metric("Alpha vs S&P", "-8.4%")
            st.metric("Drawdown", "-3.8%")
    except:
        st.metric("Valor Cartera", "884.024 €")
        st.metric("Alpha vs S&P", "-8.4%")
        st.metric("Drawdown", "-3.8%")
    
    st.subheader("ℹ️ Información del Sistema")
    st.write(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write("🤖 Agentes activos: 12")
    st.write("📊 Análisis completos: Semanal")
    st.write("📈 Actualización: Automática")

# Cargar señales recientes de tus agentes si existen
try:
    signals_file = os.path.join(DATA_DIR, "signals_emitted.csv")
    if os.path.exists(signals_file):
        df_signals = pd.read_csv(signals_file)
        latest_signals = df_signals.tail(5)
        with st.expander("🔔 Señales Recientes de Agentes"):
            st.dataframe(latest_signals[['timestamp', 'agent', 'signal_type', 'recommendation']])
    else:
        with st.expander("🔔 Señales Recientes"):
            st.write("No hay señales recientes disponibles")
except:
    with st.expander("🔔 Señales Recientes"):
        st.write("No se pudieron cargar las señales")

# Historial de chat
if "historial" not in st.session_state:
    st.session_state.historial = [
        {
            "rol": "assistant", 
            "texto": "👋 ¡Hola! Soy tu asistente financiero AI integrado con el sistema multiagente de inversión.\n\nPuedo ayudarte con:\n- Análisis de tu cartera actual\n- Explicación de señales de inversión\n- Recomendaciones basadas en análisis cuantitativo\n- Evaluación de riesgos y oportunidades\n\n¿En qué puedo ayudarte hoy?"
        }
    ]

# Mostrar historial de chat
for mensaje in st.session_state.historial:
    if mensaje["rol"] == "usuario":
        with st.chat_message("user", avatar="👤"):
            st.write(mensaje["texto"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(mensaje["texto"])

# Entrada de usuario
with st.form("formulario_pregunta", clear_on_submit=True):
    pregunta = st.text_input("Escribe tu pregunta sobre inversiones, cartera o mercado:")
    submit = st.form_submit_button("Enviar pregunta")

if submit and pregunta:
    # Añadir al historial
    st.session_state.historial.append({"rol": "usuario", "texto": pregunta})
    
    # Generar respuesta con GenAI usando datos de tus agentes
    with st.spinner("🧠 Analizando tu pregunta..."):
        try:
            # Cargar contexto real de tus agentes
            contexto = {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "cartera_valor": "884.024 €",
                "retorno": "+2.3%",
                "drawdown": "-3.8%",
                "alpha": "-8.4%",
                "regimen_liquidez": "Contractivo",
                "regimen_mercado": "Neutral",
                "señales_fx": "Cobertura USD 80%",
                "señales_cuanti": "Aumentar: XLK, QQQ, ASML",
                "riesgos": "Déficit fiscal elevado, tensión en mercados emergentes"
            }
            
            # Si tienes archivos reales, cargarlos
            try:
                signals_file = os.path.join(DATA_DIR, "signals_emitted.csv")
                if os.path.exists(signals_file):
                    df_signals = pd.read_csv(signals_file)
                    latest_fx = df_signals[df_signals['agent'] == 'fx_agent'].tail(1)
                    if not latest_fx.empty:
                        contexto['señales_fx'] = latest_fx.iloc[0]['recommendation']
            except:
                pass

            prompt = f"""
Eres un asistente financiero experto integrado en un sistema multiagente de inversión. 
Responde usando los siguientes datos del sistema:

**Datos del sistema ({contexto['fecha']}):**
- Valor cartera: {contexto['cartera_valor']}
- Retorno: {contexto['retorno']}
- Drawdown: {contexto['drawdown']}
- Alpha vs benchmark: {contexto['alpha']}
- Régimen de liquidez: {contexto['regimen_liquidez']}
- Régimen de mercado: {contexto['regimen_mercado']}
- Señales FX: {contexto['señales_fx']}
- Señales cuantitativas: {contexto['señales_cuanti']}
- Riesgos identificados: {contexto['riesgos']}

**Pregunta del usuario:** {pregunta}

**Instrucciones:**
- Responde de forma clara, profesional y con datos específicos
- Explica las recomendaciones del sistema
- Usa formato markdown para mejor lectura

**Respuesta:**
"""

            response = model.generate_content(prompt)
            respuesta = response.text if response.text else "No pude generar una respuesta adecuada."

            # Añadir al historial
            st.session_state.historial.append({"rol": "assistant", "texto": respuesta})
            
        except Exception as e:
            error_msg = f"❌ Error al procesar tu pregunta: {str(e)}"
            st.session_state.historial.append({"rol": "assistant", "texto": error_msg})
            st.error(error_msg)

# Botón para limpiar historial
if st.button("🗑️ Limpiar conversación"):
    st.session_state.historial = [
        {
            "rol": "assistant", 
            "texto": "👋 ¡Hola de nuevo! Historial limpiado. ¿En qué puedo ayudarte?"
        }
    ]

#Añadir controles de ejecución en la interfaz
# En tu streamlit_app.py, añade esta sección
with st.sidebar:
    st.header("⚙️ Control del Sistema")
    
    # Botón para ejecutar el orquestador completo
    if st.button("🔄 Ejecutar Orquestador Completo"):
        with st.spinner("Ejecutando orquestador..."):
            try:
                import subprocess
                result = subprocess.run(['python', 'orchestrator.py'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("✅ Orquestador ejecutado exitosamente")
                    st.code(result.stdout)
                else:
                    st.error(f"❌ Error: {result.stderr}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    st.subheader("🤖 Agentes Individuales")
    
    # Botones para ejecutar agentes individuales
    agent_options = {
        "Liquidity Agent": "00_liquidity_agent.py",
        "FX Agent": "03_fx_agent.py", 
        "Quant Signals": "04_quant_signals.py",
        "Risk Manager": "05_risk_manager.py",
        "Market Analyst": "11_market_analyst.py",
        "Sectorial Strength": "12_sectorial_strength.py",
        "Performance Agent": "13_performance_agent.py"
    }
    
    selected_agent = st.selectbox("Selecciona un agente:", list(agent_options.keys()))
    
    if st.button(f"▶️ Ejecutar {selected_agent}"):
        agent_file = agent_options[selected_agent]
        with st.spinner(f"Ejecutando {selected_agent}..."):
            try:
                import subprocess
                result = subprocess.run(['python', agent_file], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    st.success(f"✅ {selected_agent} ejecutado exitosamente")
                    st.code(result.stdout)
                else:
                    st.error(f"❌ Error: {result.stderr}")
            except Exception as e:
                st.error(f"❌ Error: {e}")


# Añade esta función para validar la ejecución
def validate_agent_execution(agent_name):
    """Validar que el agente a ejecutar es seguro"""
    allowed_agents = [
        "00_liquidity_agent.py", "01_data_prep.py", "02_portfolio_exposure.py",
        "03_fx_agent.py", "04_quant_signals.py", "05_risk_manager.py",
        "06_portfolio_reconstructor.py", "07_asset_metrics.py", 
        "07_reporter_advanced.py", "09_orchestrator.py", "11_market_analyst.py",
        "12_sectorial_strength.py", "13_performance_agent.py"
    ]
    return agent_name in allowed_agents

# Usa esta función antes de ejecutar
if validate_agent_execution(agent_file):
    # Ejecutar el agente
    pass
else:
    st.error("❌ Agente no autorizado")

# Añade esta función para validar la ejecución
def validate_agent_execution(agent_name):
    """Validar que el agente a ejecutar es seguro"""
    allowed_agents = [
        "00_liquidity_agent.py", "01_data_prep.py", "02_portfolio_exposure.py",
        "03_fx_agent.py", "04_quant_signals.py", "05_risk_manager.py",
        "06_portfolio_reconstructor.py", "07_asset_metrics.py", 
        "07_reporter_advanced.py", "09_orchestrator.py", "11_market_analyst.py",
        "12_sectorial_strength.py", "13_performance_agent.py"
    ]
    return agent_name in allowed_agents

# Usa esta función antes de ejecutar
if validate_agent_execution(agent_file):
    # Ejecutar el agente
    pass
else:
    st.error("❌ Agente no autorizado")


# Mejorar la interfaz de usuario
with st.expander("📊 Dashboard de Riesgo"):
    st.write("Aquí podrías mostrar gráficos de drawdown, alpha, etc.")

with st.expander("📈 Fuerza Sectorial"):
    st.write("Aquí podrías mostrar la fuerza relativa por sectores/ETFs")

with st.expander("🌍 Análisis Macroeconómico"):
    st.write("Aquí podrías mostrar el análisis macroeconómico del Market Analyst")


#  Conectar con Google Sheets para datos en tiempo real
import gspread
from google.oauth2.service_account import Credentials

def get_google_sheets_data():
    """Obtener datos de Google Sheets"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    creds = Credentials.from_service_account_file('config/service_account.json', scopes=scope)
    client = gspread.authorize(creds)
    
    sheet = client.open_by_key('TU_GOOGLE_SHEET_ID').sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)
