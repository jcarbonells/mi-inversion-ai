import subprocess
import json
import os
from datetime import datetime

def execute_agent(agent_name):
    """Ejecutar un agente específico de forma segura"""
    
    # Lista de agentes permitidos
    allowed_agents = {
        "liquidity": "agents/00_liquidity_agent.py",
        "data_prep": "agents/01_data_prep.py",
        "portfolio_exposure": "agents/02_portfolio_exposure.py",
        "fx": "agents/03_fx_agent.py",
        "quant": "agents/04_quant_signals.py",
        "risk": "agents/05_risk_manager.py",
        "portfolio_reconstructor": "agents/06_portfolio_reconstructor.py",
        "asset_metrics": "agents/07_asset_metrics.py",
        "reporter": "agents/07_reporter_advanced.py",
        "market_analyst": "agents/11_market_analyst.py",
        "sectorial_strength": "agents/12_sectorial_strength.py",
        "performance": "agents/13_performance_agent.py",
        "orchestrator": "src/orchestrator.py"
    }
    
    if agent_name in allowed_agents:
        agent_path = allowed_agents[agent_name]
        
        # Verificar que el archivo existe
        if not os.path.exists(agent_path):
            return {
                "status": "error", 
                "message": f"Archivo no encontrado: {agent_path}"
            }
        
        # Ejecutar el agente
        try:
            result = subprocess.run(
                ['python', agent_path], 
                capture_output=True, 
                text=True,
                timeout=600  # 10 minutos de timeout
            )
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
                "timestamp": datetime.now().isoformat()
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "Tiempo de ejecución excedido (10 minutos)"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    else:
        return {
            "status": "error", 
            "message": f"Agente no permitido: {agent_name}"
        }

def execute_orchestrator():
    """Ejecutar el orquestador completo"""
    try:
        result = subprocess.run(
            ['python', 'src/orchestrator.py'], 
            capture_output=True, 
            text=True,
            timeout=3600  # 1 hora de timeout para el orquestador completo
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
            "timestamp": datetime.now().isoformat()
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Tiempo de ejecución excedido (1 hora)"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def list_available_agents():
    """Listar agentes disponibles"""
    return {
        "liquidity": "Análisis de liquidez global",
        "data_prep": "Preparación de datos",
        "portfolio_exposure": "Exposición de cartera",
        "fx": "Señales de cobertura FX",
        "quant": "Señales cuantitativas",
        "risk": "Gestión de riesgo",
        "portfolio_reconstructor": "Reconstrucción de cartera",
        "asset_metrics": "Métricas por activo",
        "reporter": "Generación de informes",
        "market_analyst": "Análisis macroeconómico",
        "sectorial_strength": "Fuerza relativa sectorial",
        "performance": "Evaluación de rendimiento",
        "orchestrator": "Orquestador completo"
    }
