import os
import sys
from pathlib import Path
import json

# Añadir el root al path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Agregar la carpeta ARCHIVOS_NO_DESPLIEGUE donde está azure_blob_logger
NO_DESPLIEGUE_DIR = ROOT_DIR / "ARCHIVOS_NO_DESPLIEGUE"
if str(NO_DESPLIEGUE_DIR) not in sys.path:
    sys.path.insert(0, str(NO_DESPLIEGUE_DIR))

from dotenv import load_dotenv

env_path = ROOT_DIR / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

from backend.app import app, read_job_log
from fastapi.testclient import TestClient

client = TestClient(app)

def test_orquestador_y_logs():
    print("=== INICIANDO PRUEBA DEL ORQUESTADOR Y CONSULTA DE LOG EN STORAGE ===")
    
    # 1. Lanzamos el orquestador
    print("1. Ejecutando POST /api/orquestador/run...")
    payload = {"area": "TODAS", "anio": 2026, "mes": 5, "auto_date": False}
    response = client.post("/api/orquestador/run", json=payload)
    
    if response.status_code != 200:
        print(f"ERROR al lanzar orquestador: {response.text}")
        return False
        
    data = response.json()
    log_path = data.get("log_path")
    print(f"Orquestador lanzado con éxito. Log esperado: {log_path}")
    
    # 2. Forzamos lectura del log (que intentará usar local, o Azure si no existe local)
    print("2. Ejecutando GET /api/jobs/runtime-log...")
    log_response = client.get("/api/jobs/runtime-log")
    
    if log_response.status_code == 200:
        log_data = log_response.json()
        log_text = log_data.get("log", "")
        
        print("\nResultado de extracción de log:")
        if log_text:
            print("--------------------------------------------------")
            print(log_text[:500] + "\n...[truncado]..." if len(log_text) > 500 else log_text)
            print("--------------------------------------------------")
            print("¡ÉXITO! Log obtenido correctamente (desde local o Azure).")
        else:
            print("El log está vacío o no se pudo encontrar en local ni en Azure Storage.")
            print("Esto es normal si el archivo aún no se ha creado o subido.")
    else:
        print(f"ERROR al leer log: {log_response.text}")
        return False
        
    # 3. Probando lectura directa desde azure_blob_logger (opcional)
    print("\n3. Probando lectura directa de un archivo ficticio desde Azure Storage (para validar AzureBlobManager)...")
    try:
        from azure_blob_logger import AzureBlobManager
        print("Módulo AzureBlobManager cargado. Intentando leer 'prueba_ficticia.log'...")
        # Esto probará si las credenciales funcionan para lectura
        AzureBlobManager.read_log("portal_jobs", "prueba_ficticia.log")
        print("La consulta a Azure Storage se ejecutó sin excepciones (el archivo puede no existir, pero la conexión es válida).")
    except ImportError:
        print("No se encontró azure_blob_logger en el PYTHONPATH.")
    except Exception as e:
        print(f"Resultado de Azure Storage (Conexión válida si es BlobNotFound): {e}")

    return True

if __name__ == "__main__":
    test_orquestador_y_logs()
