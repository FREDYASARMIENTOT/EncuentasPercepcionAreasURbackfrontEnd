"""Script para probar la conexión a la base de datos dbpercepcion."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pyodbc

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

print("="*60)
print("PRUEBA DE CONEXION A BASE DE DATOS")
print("="*60)

# Leer variables
server = os.getenv("DB_DATA_SERVER")
database = os.getenv("DB_DATA_NAME")
user = os.getenv("DB_DATA_USER")
password = os.getenv("DB_DATA_PASS")

print(f"  Servidor : {server}")
print(f"  Base dato: {database}")
print(f"  Usuario  : {user}")
print(f"  Password : {password[:3]}***" if password else "  Password : [VACIO]")

print("\n--- Drivers SQL disponibles ---")
for d in pyodbc.drivers():
    if "SQL" in d.upper() or "ODBC" in d.upper():
        print(f"  -> {d}")

driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
print(f"\n--- Usando driver: {driver} ---")

conn_str = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password};"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=10;"
    "Login Timeout=10;"
)

print("\n--- Intentando conexión ---")
try:
    conn = pyodbc.connect(conn_str)
    print("CONEXION EXITOSA!")
    cursor = conn.cursor()
    cursor.execute("SELECT DB_NAME() AS DB, @@VERSION AS VER")
    row = cursor.fetchone()
    print(f"  Base de datos activa : {row[0]}")
    print(f"  Version SQL Server   : {row[1][:80]}...")
    conn.close()
except Exception as e:
    print(f"ERROR DE CONEXION: {e}")

print("="*60)