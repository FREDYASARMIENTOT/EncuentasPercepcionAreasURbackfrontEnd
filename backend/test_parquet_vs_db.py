"""
Prueba conexión al Data Lake y compara el parquet con la vista SQL Server.
Si no encuentra la vista exacta, busca vistas similares.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pyodbc
import pandas as pd
from io import BytesIO
from azure.storage.blob import BlobServiceClient

# ── Cargar .env ────────────────────────────────────────────────────────────
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# ── Variables Azure Blob ────────────────────────────────────────────────────
AZURE_URL    = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "https://saurdatamining.blob.core.windows.net")
CONTAINER    = os.getenv("AZURE_CONTAINER_NAME", "fs-encuestaspercepcion")
SAS_TOKEN    = os.getenv("AZURE_SAS_TOKEN", "")
PARQUET_NAME = "EncuestasPercepcion/VistaEncuestaPercepcion2026.parquet"

# ── Variables SQL ──────────────────────────────────────────────────────────
DB_SERVER = os.getenv("DB_DATA_SERVER")
DB_NAME   = os.getenv("DB_DATA_NAME")
DB_USER   = os.getenv("DB_DATA_USER")
DB_PASS   = os.getenv("DB_DATA_PASS")
DB_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

SEP = "=" * 70


def get_blob_service():
    url = AZURE_URL.rstrip("/")
    sas = SAS_TOKEN.lstrip("?")
    return BlobServiceClient(f"{url}?{sas}")


def download_parquet():
    print(f"\n[1] Descargando parquet desde Data Lake ...")
    print(f"    URL: {AZURE_URL}/{CONTAINER}/{PARQUET_NAME}")
    try:
        client = get_blob_service().get_blob_client(container=CONTAINER, blob=PARQUET_NAME)
        raw = client.download_blob().readall()
        print(f"    -> Descargado: {len(raw):,} bytes")
        df = pd.read_parquet(BytesIO(raw))
        print(f"    -> Filas    : {len(df):,}")
        print(f"    -> Columnas : {len(df.columns)}")
        return df
    except Exception as e:
        print(f"    !! ERROR: {e}")
        sys.exit(1)


def get_sql_connection():
    conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASS};"
        "Encrypt=no;TrustServerCertificate=yes;"
        "Connection Timeout=15;"
    )
    print(f"\n[2] Conectando a SQL Server ...")
    print(f"    Servidor : {DB_SERVER}")
    print(f"    Base dato: {DB_NAME}")
    print(f"    Usuario  : {DB_USER}")
    try:
        conn = pyodbc.connect(conn_str)
        print(f"    -> CONEXION EXITOSA")
        return conn
    except Exception as e:
        print(f"    !! ERROR conectando: {e}")
        sys.exit(1)


def buscar_vistas(conn, buscar="percepcion"):
    """Busca vistas/tablas que contengan la palabra clave."""
    sql = f"""
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
          FROM INFORMATION_SCHEMA.TABLES
         WHERE TABLE_NAME LIKE '%{buscar}%'
         ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    return pd.read_sql(sql, conn)


def get_view_columns(conn, schema, view_name):
    """Obtiene columnas de una vista específica."""
    sql = f"""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
               IS_NULLABLE, ORDINAL_POSITION
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{view_name}'
         ORDER BY ORDINAL_POSITION
    """
    return pd.read_sql(sql, conn)


def compare_structures(df_blob, df_sql):
    """Compara la estructura del parquet vs la vista SQL."""
    print(f"\n{SEP}")
    print("  COMPARACION DE ESTRUCTURAS")
    print(SEP)

    cols_blob = set(df_blob.columns)
    cols_db   = set(df_sql["COLUMN_NAME"])

    solo_blob = sorted(cols_blob - cols_db)
    solo_db   = sorted(cols_db - cols_blob)
    comunes   = sorted(cols_blob & cols_db)

    print(f"\n  Columnas en parquet : {len(cols_blob)}")
    print(f"  Columnas en vista   : {len(cols_db)}")
    print(f"  Columnas comunes    : {len(comunes)}")

    # Detalle parquet
    print(f"\n  -- Estructura del parquet {'─' * 50}")
    for i, (c, t) in enumerate(df_blob.dtypes.items(), 1):
        status = ""
        if c in solo_blob:
            status = "  <-- SOLO PARQUET"
        elif c not in cols_db:
            status = "  <-- NO en vista"
        else:
            status = "  ✓"
        print(f"    {i:3d}. {c:<40s} {str(t):<20s}{status}")

    # Detalle vista SQL
    print(f"\n  -- Estructura de la vista SQL {'─' * 47}")
    for _, row in df_sql.iterrows():
        c = row["COLUMN_NAME"]
        t = row["DATA_TYPE"]
        lng = row.get("CHARACTER_MAXIMUM_LENGTH", "")
        lng_s = f"({lng})" if pd.notna(lng) and lng != "" else ""
        status = ""
        if c in solo_db:
            status = "  <-- SOLO VISTA (faltante en parquet)"
        else:
            status = "  ✓"
        print(f"    {row['ORDINAL_POSITION']:3d}. {c:<40s} {t}{lng_s:<15s}{status}")

    # Tipos desalineados
    if comunes:
        tipo_map = {
            "int64":         ["bigint", "int"],
            "int32":         ["int", "smallint", "tinyint", "bigint"],
            "float64":       ["float", "real", "numeric", "decimal", "money"],
            "object":        ["varchar", "nvarchar", "char", "nchar", "text"],
            "bool":          ["bit"],
            "datetime64[ns]":["datetime", "datetime2", "date", "smalldatetime"],
        }
        print(f"\n  -- Verificacion de tipos en columnas comunes {'─' * 30}")
        desalineados = []
        for c in comunes:
            blob_tipo = str(df_blob[c].dtype)
            db_tipo = df_sql.loc[df_sql["COLUMN_NAME"] == c, "DATA_TYPE"].values[0]
            compatibles = tipo_map.get(blob_tipo, [])
            match = "OK" if db_tipo in compatibles else f"MISMATCH (parquet={blob_tipo}, vista={db_tipo})"
            symbol = "  " if db_tipo in compatibles else "!!"
            print(f"    {symbol} {c:<40s} {match}")
            if db_tipo not in compatibles:
                desalineados.append((c, blob_tipo, db_tipo))

    # Resumen
    print(f"\n{SEP}")
    if not solo_blob and not solo_db:
        print("  RESULTADO: LAS ESTRUCTURAS SON IGUALES")
        print(f"  No se requieren ajustes. Las {len(comunes)} columnas coinciden.")
    else:
        print("  RESULTADO: LAS ESTRUCTURAS DIFIEREN")
        if solo_blob:
            print(f"\n  Columnas SOLO en parquet (eliminar o mapear):")
            for c in solo_blob:
                print(f"    - {c}")
        if solo_db:
            print(f"\n  Columnas SOLO en vista (agregar al parquet):")
            for c in solo_db:
                db_tipo = df_sql.loc[df_sql["COLUMN_NAME"] == c, "DATA_TYPE"].values[0]
                print(f"    - {c} ({db_tipo})")

        # Mostrar orden correcto
        print(f"\n  -- Orden de columnas para que el parquet coincida con la vista {'─' * 15}")
        orden_vista = df_sql["COLUMN_NAME"].tolist()
        for i, c in enumerate(orden_vista, 1):
            if c in cols_blob:
                print(f"    {i:3d}. {c}  (existe en parquet)")
            else:
                print(f"    {i:3d}. {c}  ** FALTA en parquet **")
    print(SEP)


def main():
    print(SEP)
    print("  PRUEBA DATA LAKE + COMPARACION PARQUET vs VISTA SQL")
    print(SEP)

    # 1. Descargar parquet
    df_blob = download_parquet()

    # 2. Conectar a SQL
    conn = get_sql_connection()

    # 3. Buscar vistas con "percepcion" en el nombre
    print(f"\n[3] Buscando vistas/tablas con 'Percepcion' en el nombre ...")
    vistas = buscar_vistas(conn, "percepcion")
    
    if len(vistas) == 0:
        print("    !! No se encontraron vistas con 'Percepcion'")
        print("\n    Mostrando TODAS las vistas de la base de datos:")
        todas = buscar_vistas(conn, "")
        if len(todas) > 0:
            for _, row in todas.iterrows():
                print(f"      {row['TABLE_SCHEMA']}.{row['TABLE_NAME']} ({row['TABLE_TYPE']})")
        else:
            print("      No hay tablas/vistas en esta base de datos.")
        
        # También buscar en otras BD si hay permisos
        print("\n    Buscando vistas con 'Encuesta' en el nombre:")
        vistas2 = buscar_vistas(conn, "encuesta")
        if len(vistas2) > 0:
            for _, row in vistas2.iterrows():
                print(f"      {row['TABLE_SCHEMA']}.{row['TABLE_NAME']} ({row['TABLE_TYPE']})")

    elif len(vistas) == 1:
        # Una sola vista encontrada, usarla
        row = vistas.iloc[0]
        schema = row["TABLE_SCHEMA"]
        view_name = row["TABLE_NAME"]
        print(f"    -> Encontrada: {schema}.{view_name}")
        
        print(f"\n[4] Obteniendo columnas de la vista ...")
        cols_sql = get_view_columns(conn, schema, view_name)
        print(f"    -> Columnas: {len(cols_sql)}")
        conn.close()
        
        # 5. Comparar
        compare_structures(df_blob, cols_sql)
    else:
        # Múltiples vistas encontradas
        print(f"    -> Se encontraron {len(vistas)} vistas:")
        for i, row in vistas.iterrows():
            print(f"       {i}. {row['TABLE_SCHEMA']}.{row['TABLE_NAME']} ({row['TABLE_TYPE']})")
        
        # Buscar la que más se parezca al nombre del parquet
        target = "VistaEncuestaPercepcion2026"
        matches = vistas[vistas["TABLE_NAME"].str.contains("2026", case=False, na=False)]
        
        if len(matches) > 0:
            row = matches.iloc[0]
            schema = row["TABLE_SCHEMA"]
            view_name = row["TABLE_NAME"]
            print(f"\n    -> Usando vista coincidente con '2026': {schema}.{view_name}")
        else:
            # Usar la primera
            row = vistas.iloc[0]
            schema = row["TABLE_SCHEMA"]
            view_name = row["TABLE_NAME"]
            print(f"\n    -> Usando primera vista: {schema}.{view_name}")
        
        print(f"\n[4] Obteniendo columnas de {schema}.{view_name} ...")
        cols_sql = get_view_columns(conn, schema, view_name)
        print(f"    -> Columnas: {len(cols_sql)}")
        conn.close()
        
        # 5. Comparar
        compare_structures(df_blob, cols_sql)


if __name__ == "__main__":
    main()