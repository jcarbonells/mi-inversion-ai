import streamlit as st
import google.generativeai as genai
import os
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys

# Intentar importar sheets_controller
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    from sheets_controller import SheetsController
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    st.warning("⚠️ No se pudo importar sheets_controller - Google Sheets no disponible")

# Configurar API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY", "TU_API_KEY_AQUI_TEMPORAL"))
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.0-flash')

# Rutas del sistema
BASE_DIR = os.path.dirname(__file__)
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Inicializar controlador de Google Sheets si está disponible
SHEET_ID = "1C5qVh7uTBdNLcWv5kQL8aLkxxsIWDN0yh9y6ReVXLzE"  # Tu Sheet ID real
sheets_controller = None

if SHEETS_AVAILABLE:
    try:
        # Intentar diferentes rutas para el archivo de credenciales
        possible_paths = [
            'config/service_account.json',
            '../config/service_account.json',
            'service_account.json',
            '../service_account.json'
        ]
        
        credentials_path = None
        for path in possible_paths:
            if os.path.exists(path):
                credentials_path = path
                break
        
        if credentials_path:
            sheets_controller = SheetsController(SHEET_ID, credentials_path=credentials_path)
            st.success("✅ Conectado a Google Sheets")
        else:
            st.warning("⚠️ No conectado a Google Sheets - Archivo de credenciales no encontrado")
            st.warning("   Asegúrate de que el archivo service_account.json esté en el repositorio GitHub")
    except Exception as e:
        st.warning(f"⚠️ No conectado a Google Sheets: {e}")
        st.warning("   Verifica que el archivo service_account.json esté en el repositorio GitHub")
else:
    st.warning("⚠️ Google Sheets no disponible - sheets_controller no encontrado")

st.set_page_config(page_title="🧠 Centro de Control Financiero", layout="wide")
st.title("🧠 Centro de Control de Agentes Financieros Autónomos")
st.markdown("*Sistema multiagente integrado con asistente financiero cognitivo personalizado*")

# Sidebar - Panel de Control
with st.sidebar:
    st.header("⚙️ Panel de Control")
    
    # Información del sistema
    st.subheader("📊 Estado del Sistema")
    st.write(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write("🤖 Agentes activos: 12")
    st.write("📈 Actualización: Automática")
    
    # Controles de ejecución
    st.header("⚡ Ejecutar Agentes")
    
    # Botón para ejecutar el orquestador completo
    if st.button("🔄 Orquestador Completo", help="Ejecutar todos los agentes en secuencia"):
        with st.spinner("Ejecutando orquestador completo..."):
            try:
                import subprocess
                result = subprocess.run(['python', 'src/orchestrator.py'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("✅ Orquestador ejecutado exitosamente")
                    st.success("📊 Informes generados correctamente")
                else:
                    st.error(f"❌ Error: {result.stderr}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# Pestañas para diferentes vistas
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Dashboard", "📊 Cartera", "🌍 Liquidez", "📈 Fuerza Sectorial", "💬 Asistente"])

# Tab 1: Dashboard Principal
with tab1:
    st.header("📊 Dashboard Principal")
    
    # Leer datos de Google Sheets si está conectado
    if sheets_controller:
        try:
            df_signals = sheets_controller.read_from_sheet('signals')
            df_portfolio = sheets_controller.read_from_sheet('portfolio_history')
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Valor Cartera", "884.024 €", "+2.3%")
            with col2:
                st.metric("Drawdown", "-3.8%", "-0.2%")
            with col3:
                st.metric("Alpha vs S&P", "-8.4%", "-0.1%")
            with col4:
                st.metric("Régimen Liquidez", "Contractivo", "0.2")
            
            # Gráfico de evolución de cartera
            if not df_portfolio.empty:
                fig_portfolio = px.line(df_portfolio, x='date', y='value', title='Evolución de Cartera')
                st.plotly_chart(fig_portfolio, use_container_width=True)
            else:
                st.info("No hay datos de evolución de cartera disponibles")
        except Exception as e:
            st.warning(f"⚠️ Error leyendo datos de Google Sheets: {e}")
    else:
        st.warning("⚠️ No conectado a Google Sheets - Mostrando datos de ejemplo")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Valor Cartera", "884.024 €", "+2.3%")
        with col2:
            st.metric("Drawdown", "-3.8%", "-0.2%")
        with col3:
            st.metric("Alpha vs S&P", "-8.4%", "-0.1%")
        with col4:
            st.metric("Régimen Liquidez", "Contractivo", "0.2")

# Tab 2: Análisis de Cartera
with tab2:
    st.header("📊 Análisis de Cartera")
    
    if sheets_controller:
        try:
            df_geo = sheets_controller.read_from_sheet('geographic_exposure')
            df_asset = sheets_controller.read_from_sheet('asset_class_exposure')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🌍 Exposición por Geografía")
                if not df_geo.empty:
                    fig_geo = px.pie(df_geo, values='percentage', names='region', title='Distribución Geográfica')
                    st.plotly_chart(fig_geo, use_container_width=True)
                else:
                    st.info("No hay datos de exposición geográfica")
            
            with col2:
                st.subheader("💳 Exposición por Clase de Activo")
                if not df_asset.empty:
                    fig_asset = px.bar(df_asset, x='asset_class', y='percentage', title='Distribución por Clase de Activo')
                    st.plotly_chart(fig_asset, use_container_width=True)
                else:
                    st.info("No hay datos de exposición por clase de activo")
        except Exception as e:
            st.warning(f"⚠️ Error leyendo datos de cartera: {e}")

# Tab 3: Análisis de Liquidez
with tab3:
    st.header("🌍 Análisis de Liquidez Global")
    
    if sheets_controller:
        try:
            df_liquidity = sheets_controller.read_from_sheet('liquidity_data')
            df_risks = sheets_controller.read_from_sheet('liquidity_data')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 4 Capas de Liquidez")
                if not df_liquidity.empty:
                    fig_liquidity = px.bar(df_liquidity, x='liquidity_layer', y='score', color='regime', 
                                          title='Liquidez por Capa (Contractivo < 3.5 < Expansionista)')
                    st.plotly_chart(fig_liquidity, use_container_width=True)
                else:
                    st.info("No hay datos de liquidez disponibles")
            
            with col2:
                st.subheader("⚠️ Riesgos Cuantificados")
                if not df_risks.empty:
                    fig_risk = px.bar(df_risks, x='liquidity_layer', y='score', 
                                     title='Riesgos Cuantificados', range_y=[0, 10])
                    st.plotly_chart(fig_risk, use_container_width=True)
                else:
                    st.info("No hay datos de riesgos disponibles")
        except Exception as e:
            st.warning(f"⚠️ Error leyendo datos de liquidez: {e}")

# Tab 4: Fuerza Sectorial
with tab4:
    st.header("📈 Fuerza Relativa Sectorial")
    
    if sheets_controller:
        try:
            df_sector = sheets_controller.read_from_sheet('sector_strength')
            df_momentum = sheets_controller.read_from_sheet('etf_momentum')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Ranking de Fuerza Sectorial")
                if not df_sector.empty:
                    fig_sector = px.bar(df_sector, x='sector', y='strength_score', 
                                       title='Fuerza Relativa por Sector')
                    st.plotly_chart(fig_sector, use_container_width=True)
                else:
                    st.info("No hay datos de fuerza sectorial")
            
            with col2:
                st.subheader("📈 Momentum por ETF")
                if not df_momentum.empty:
                    fig_momentum = px.scatter(df_momentum, x='volatility', y='momentum', 
                                            size='volume', color='etf', 
                                            title='Momentum vs Volatilidad por ETF')
                    st.plotly_chart(fig_momentum, use_container_width=True)
                else:
                    st.info("No hay datos de momentum de ETFs")
        except Exception as e:
            st.warning(f"⚠️ Error leyendo datos de fuerza sectorial: {e}")

# Tab 5: Asistente Financiero Cognitivo
with tab5:
    st.header("💬 Asistente Financiero Cognitivo Personalizado")
    
    # Mostrar señales recientes
    if sheets_controller:
        try:
            df_signals = sheets_controller.read_from_sheet('signals')
            if not df_signals.empty:
                with st.expander("🔔 Señales Recientes de Agentes"):
                    st.dataframe(df_signals.tail(5)[['timestamp', 'agent', 'signal_type', 'recommendation']])
            else:
                st.info("No hay señales recientes disponibles")
        except Exception as e:
            st.warning(f"⚠️ Error leyendo señales: {e}")
    else:
        st.warning("⚠️ No conectado a Google Sheets")
    
    # Historial de chat
    if "historial" not in st.session_state:
        st.session_state.historial = [
            {
                "rol": "assistant", 
                "texto": "👋 ¡Hola! Soy tu asistente financiero cognitivo personalizado.\n\nPuedo ayudarte con:\n- Análisis de tu cartera actual\n- Explicación de señales de inversión\n- Recomendaciones basadas en análisis cuantitativo\n- Evaluación de riesgos y oportunidades\n- Simulación de escenarios\n- Explicación de recomendaciones\n\n¿En qué puedo ayudarte hoy?"
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
        pregunta = st.text_input("Escribe tu pregunta financiera:")
        submit = st.form_submit_button("Enviar pregunta")
    
    if submit and pregunta:
        # Añadir al historial
        st.session_state.historial.append({"rol": "usuario", "texto": pregunta})
        
        # Generar respuesta con GenAI usando datos de tus agentes
        with st.spinner("🧠 Analizando tu pregunta..."):
            try:
                # Cargar contexto real de tus agentes (desde Google Sheets si disponible)
                contexto = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
                
                # Si tienes acceso a Google Sheets, cargar datos reales
                if sheets_controller:
                    try:
                        df_signals = sheets_controller.read_from_sheet('signals')
                        if not df_signals.empty:
                            latest_fx = df_signals[df_signals['agent'] == 'fx_agent'].tail(1)
                            if not latest_fx.empty:
                                contexto['señales_fx'] = latest_fx.iloc[0]['recommendation']
                    except:
                        pass

                prompt = f"""
Eres un asistente financiero cognitivo personalizado integrado en un sistema multiagente de inversión. 
Responde usando los siguientes datos del sistema y mantén contexto dinámico:

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
- Integra el contexto histórico si es relevante
- Propón ajustes estratégicos si aplica
- Simula escenarios si se solicita

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
if st.button("🗑️ Limpiar Conversación"):
    st.session_state.historial = [
        {
            "rol": "assistant", 
            "texto": "👋 ¡Hola de nuevo! Historial limpiado. ¿En qué puedo ayudarte?"
        }
    ]
