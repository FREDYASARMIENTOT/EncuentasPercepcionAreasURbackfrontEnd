import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

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
