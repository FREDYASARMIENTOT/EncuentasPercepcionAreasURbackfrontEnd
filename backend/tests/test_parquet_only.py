import os
import sys
from pathlib import Path
import io
import pandas as pd

# Añadir el root al path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

env_path = ROOT_DIR / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

def test_parquet_connection():
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.identity import DefaultAzureCredential
        
        azure_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        container_name = os.getenv("AZURE_CONTAINER_NAME")
        
        if not azure_url or not container_name:
            print("ERROR: Faltan variables AZURE_STORAGE_ACCOUNT_URL o AZURE_CONTAINER_NAME en .env")
            return False
            
        print(f"Intentando conectar a: {azure_url}, Contenedor: {container_name}")
        
        # Opcional: Si el usuario provee un SAS token en AZURE_SAS_TOKEN
        sas_token = os.getenv("AZURE_SAS_TOKEN")
        if sas_token:
            print("Usando SAS Token para autenticación...")
            blob_service_client = BlobServiceClient(account_url=azure_url, credential=sas_token)
        else:
            print("Usando DefaultAzureCredential (requiere az login o Managed Identity)...")
            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(account_url=azure_url, credential=credential)
            
        file_path = "EncuestasPercepcion/VistaEncuestaPercepcion2026.parquet"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_path)
        
        print(f"Descargando blob: {file_path}")
        download_stream = blob_client.download_blob()
        parquet_data = io.BytesIO(download_stream.readall())
        
        print("Leyendo Parquet con pandas...")
        df = pd.read_parquet(parquet_data)
        
        print("Columnas encontradas:", df.columns.tolist())
        if 'Anio' in df.columns:
            print("¡Éxito! Columna 'Anio' encontrada.")
            print("Primeros 5 registros:")
            print(df.head())
            return True
        else:
            print("ADVERTENCIA: La columna 'Anio' no se encontró en el Parquet.")
            return False
            
    except Exception as e:
        print(f"FALLO al conectar o leer el Parquet: {e}")
        return False

if __name__ == "__main__":
    test_parquet_connection()
