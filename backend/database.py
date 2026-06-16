import os
import io
import logging
import urllib.parse
from datetime import datetime
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

# Intentar importar dependencias de Azure
try:
    from azure.storage.blob import BlobServiceClient
    from azure.identity import DefaultAzureCredential
except ImportError:
    pass

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parents[0] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

Base = declarative_base()

def get_connection_string() -> str:
    server = os.getenv("SQL_SERVER", "SRVBISQL01\\SQLPRBI")
    database = os.getenv("SQL_DATABASE", "DWHEncuestasPercepcion")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "yes").lower() in ("yes", "true", "1")
    user = os.getenv("SQL_USER")
    password = os.getenv("SQL_PASSWORD")

    if trusted:
        params = (
            f"Driver={driver};"
            f"Server={server};"
            f"Database={database};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
            "Connection Timeout=5;"
            "LoginTimeout=5;"
        )
    elif user and password:
        params = (
            f"Driver={driver};"
            f"Server={server};"
            f"Database={database};"
            f"UID={user};"
            f"PWD={password};"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
            "Connection Timeout=5;"
            "LoginTimeout=5;"
        )
    else:
        raise ValueError("SQL connection is not configured. Set SQL_TRUSTED_CONNECTION=yes or provide SQL_USER and SQL_PASSWORD.")

    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(params)

engine = create_engine(get_connection_string(), echo=False, future=True, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))


def init_db():
    Base.metadata.create_all(bind=engine)

def get_total_registros_anio_actual() -> int:
    """
    Obtiene el conteo de registros del año actual.
    Intento 1: Parquet en Azure Blob Storage.
    Intento 2 (Fallback): Consulta SQL Server.
    """
    try:
        azure_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        container_name = os.getenv("AZURE_CONTAINER_NAME")
        
        if not azure_url or not container_name:
            raise ValueError("Las variables de entorno para Azure Blob Storage no están configuradas")
            
        file_path = "EncuestasPercepcion/VistaEncuestaPercepcion2026.parquet"
        
        sas_token = os.getenv("AZURE_SAS_TOKEN")
        if sas_token:
            blob_service_client = BlobServiceClient(account_url=azure_url, credential=sas_token)
        else:
            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(account_url=azure_url, credential=credential)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_path)
        
        download_stream = blob_client.download_blob()
        parquet_data = io.BytesIO(download_stream.readall())
        
        df = pd.read_parquet(parquet_data)
        
        current_year = datetime.now().year
        if 'Anio' not in df.columns:
            raise KeyError("La columna 'Anio' no se encuentra en el archivo Parquet")
            
        count = df[df['Anio'] == current_year].shape[0]
        return count
        
    except Exception as e:
        logger.warning(f"Intento 1 (Azure Blob Storage) falló: {e}. Usando contingencia (Base de Datos Local).")
        
        try:
            with SessionLocal() as session:
                query = text("SELECT COUNT(*) FROM dbo.view_respuestas_encuesta_percepcion_historica_optimizada WHERE Año = YEAR(GETDATE())")
                result = session.execute(query).scalar()
                return result or 0
        except Exception as sql_e:
            logger.error(f"Error en el Intento 2 (Fallback SQL): {sql_e}")
            raise Exception("Ambos métodos de obtención de datos fallaron") from sql_e
