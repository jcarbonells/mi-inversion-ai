import subprocess
import os
import json
import time
from datetime import datetime
import pandas as pd

class InvestmentOrchestrator:
    """Orquestador principal del sistema multiagente de inversión"""
    
    def __init__(self):
        self.BASE_DIR = os.path.dirname(__file__)
        self.AGENTS_DIR = os.path.join(self.BASE_DIR, "..", "agents")
        self.DATA_DIR = os.path.join(self.BASE_DIR, "..", "data")
        self.REPORTS_DIR = os.path.join(self.BASE_DIR, "..", "reports")
        
        # Definir el orden de ejecución de los agentes
        self.execution_order = [
            "00_liquidity_agent.py",      # Análisis de liquidez
            "01_data_prep.py",            # Preparación de datos
            "02_portfolio_exposure.py",   # Exposición de cartera
            "03_fx_agent.py",             # Señales FX
            "04_quant_signals.py",        # Señales cuantitativas
            "05_risk_manager.py",         # Gestión de riesgo
            "06_portfolio_reconstructor.py",  # Reconstrucción de cartera
            "07_asset_metrics.py",        # Métricas por activo
            "07_reporter_advanced.py",    # Generación de informe
            "11_market_analyst.py",       # Análisis macroeconómico
            "12_sectorial_strength.py",   # Fuerza sectorial
            "13_performance_agent.py"     # Evaluación de rendimiento
        ]
        
    def execute_agent(self, agent_name):
        """Ejecutar un agente específico"""
        agent_path = os.path.join(self.AGENTS_DIR, agent_name)
        
        if not os.path.exists(agent_path):
            return {
                "status": "error",
                "message": f"Agente no encontrado: {agent_path}"
            }
        
        try:
            print(f"🚀 Ejecutando {agent_name}...")
            result = subprocess.run(
                ['python', agent_path],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos por agente
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
                "message": f"Tiempo excedido para {agent_name}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def run_full_analysis(self):
        """Ejecutar el análisis completo de todos los agentes"""
        results = {}
        
        print("🚀 Iniciando análisis completo del sistema multiagente...")
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        for i, agent in enumerate(self.execution_order, 1):
            print(f"\n{i:2d}/{len(self.execution_order)} - Ejecutando: {agent}")
            
            result = self.execute_agent(agent)
            results[agent] = result
            
            if result["status"] == "error":
                print(f"❌ Error en {agent}: {result.get('message', result.get('error', 'Error desconocido'))}")
                # Puedes decidir si continuar o detenerse
                # Por ahora, continuamos para ver todos los resultados
            else:
                print(f"✅ {agent} completado exitosamente")
        
        print("\n" + "="*60)
        print("✅ Análisis completo completado")
        
        # Guardar resultados
        self.save_execution_results(results)
        
        return results
    
    def save_execution_results(self, results):
        """Guardar resultados de ejecución"""
        results_file = os.path.join(self.REPORTS_DIR, "orchestrator_results.json")
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(results),
            "successful": len([r for r in results.values() if r["status"] == "success"]),
            "failed": len([r for r in results.values() if r["status"] == "error"]),
            "results": results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Resultados guardados en: {results_file}")
    
    def get_execution_summary(self):
        """Obtener resumen de la última ejecución"""
        results_file = os.path.join(self.REPORTS_DIR, "orchestrator_results.json")
        
        if os.path.exists(results_file):
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        return None

# Función principal para ejecutar desde línea de comandos
def main():
    orchestrator = InvestmentOrchestrator()
    results = orchestrator.run_full_analysis()
    
    # Mostrar resumen
    summary = orchestrator.get_execution_summary()
    if summary:
        print(f"\n📈 Resumen de ejecución:")
        print(f"   Total agentes: {summary['total_agents']}")
        print(f"   Exitosos: {summary['successful']}")
        print(f"   Fallidos: {summary['failed']}")
        print(f"   Fecha: {summary['timestamp']}")

if __name__ == "__main__":
    main()
