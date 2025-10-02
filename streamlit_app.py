# streamlit_app.py - Código limpio para GitHub
import streamlit as st
import google.generativeai as genai
import os
import json
from datetime import datetime
import pandas as pd
import api_controller

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

# Sidebar con controles del sistema
with st.sidebar:
    st.header("📊 Estado del Sistema")
    
    # Información estática (puedes conectar con tus datos reales después)
    st.subheader("ℹ️ Información del Sistema")
    st.write(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write("🤖 Agentes activos: 12")
    st.write("📊 Análisis completos: Semanal")
    st.write("📈 Actualización: Automática")
    
    # Métricas de ejemplo
    st.metric("Valor Cartera", "884.024 €", "+2.3%")
    st.metric("Drawdown", "-3.8%", "-0.2%")
    st.metric("Alpha vs S&P", "-8.4%", "-0.1%")
    
    # Controles de ejecución
    st.header("⚙️ Control del Sistema")
    
    # Botón para ejecutar el orquestador completo
    if st.button("🔄 Ejecutar Orquestador Completo"):
        with st.spinner("Ejecutando orquestador completo..."):
            try:
                result = api_controller.execute_orchestrator()
                if result["status"] == "success":
                    st.success("✅ Orquestador ejecutado exitosamente")
                    st.code(result["output"])
                else:
                    st.error(f"❌ Error: {result['message']}")
                    if "error" in result:
                        st.code(result["error"])
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    st.subheader("🤖 Agentes Individuales")
    
    # Botones para ejecutar agentes individuales
    agent_list = api_controller.list_available_agents()
    agent_names = list(agent_list.keys())
    agent_descriptions = list(agent_list.values())
    
    # Crear diccionario para mostrar nombres amigables
    agent_display = {f"{name}: {desc}": name for name, desc in zip(agent_names, agent_descriptions)}
    
    selected_display = st.selectbox("Selecciona un agente:", list(agent_display.keys()))
    selected_agent = agent_display[selected_display]
    
    if st.button(f"▶️ Ejecutar {selected_agent}"):
        with st.spinner(f"Ejecutando {selected_agent}..."):
            try:
                result = api_controller.execute_agent(selected_agent)
                if result["status"] == "success":
                    st.success(f"✅ {selected_agent} ejecutado exitosamente")
                    st.code(result["output"])
                else:
                    st.error(f"❌ Error: {result['message']}")
                    if "error" in result:
                        st.code(result["error"])
            except Exception as e:
                st.error(f"❌ Error: {e}")

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
