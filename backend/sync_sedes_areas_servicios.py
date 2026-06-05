import os
from pathlib import Path
from typing import List, Tuple

import pyodbc
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[0] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

SOURCE_VIEW = os.getenv("DB_DATA_VIEW", "dbo.View_SedesAreasServiciosEncuestasRespuestas")
TARGET_TABLE = "Catalogo.SedesAreasServiciosEncuestasRespuestas"
TARGET_VIEW = "Catalogo.View_SedesAreasServiciosEncuestasRespuestas"
SOURCE_COLUMNS = [
    "SedeId",
    "SedeNombre",
    "SedeEstadoDescripcion",
    "AreaId",
    "AreaNombre",
    "AreaEstadoDescripcion",
    "ServicioId",
    "ServicioNombre",
    "ServicioEstadoDescripcion",
    "EncuestasPorRelacion",
    "CantidadEncuestas",
    "TotalRespuestasHistoricas",
]

DEFAULT_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")


def get_source_connection_string() -> str:
    server = os.getenv("DB_DATA_SERVER")
    database = os.getenv("DB_DATA_NAME")
    user = os.getenv("DB_DATA_USER")
    password = os.getenv("DB_DATA_PASS")

    if not server or not database or not user or not password:
        raise ValueError("Source database connection is not configured in environment variables.")

    return (
        f"DRIVER={{{DEFAULT_DRIVER}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )


def get_target_connection_string() -> str:
    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    user = os.getenv("SQL_USER")
    password = os.getenv("SQL_PASSWORD")
    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "yes").lower() in ("yes", "true", "1")

    if not server or not database:
        raise ValueError("Target database connection is not configured in environment variables.")

    if trusted:
        return (
            f"DRIVER={{{DEFAULT_DRIVER}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )

    if not user or not password:
        raise ValueError("Target database credentials are missing; set SQL_USER and SQL_PASSWORD or enable trusted connection.")

    return (
        f"DRIVER={{{DEFAULT_DRIVER}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=no;"
    )


def build_target_table_ddl() -> str:
    return """
IF OBJECT_ID('Catalogo.SedesAreasServiciosEncuestasRespuestas', 'U') IS NULL
BEGIN
    CREATE TABLE Catalogo.SedesAreasServiciosEncuestasRespuestas (
        RegistroId INT IDENTITY(1,1) PRIMARY KEY,
        SedeId INT NOT NULL,
        SedeNombre NVARCHAR(200) NOT NULL,
        SedeEstadoDescripcion NVARCHAR(200) NULL,
        AreaId NVARCHAR(200) NULL,
        AreaNombre NVARCHAR(200) NOT NULL,
        AreaEstadoDescripcion NVARCHAR(200) NULL,
        ServicioId NVARCHAR(200) NULL,
        ServicioNombre NVARCHAR(200) NOT NULL,
        ServicioEstadoDescripcion NVARCHAR(200) NULL,
        EncuestasPorRelacion INT NULL,
        CantidadEncuestas INT NULL,
        TotalRespuestasHistoricas INT NULL,
        FechaInsercion DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        FechaModificacion DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        EstadoRegistro NVARCHAR(50) NOT NULL DEFAULT 'Activo'
    );

    CREATE UNIQUE INDEX UX_SedesAreasServiciosEncuestasRespuestas
        ON Catalogo.SedesAreasServiciosEncuestasRespuestas (SedeId, AreaId, ServicioId);
END
""".strip()


def build_target_view_ddl() -> str:
    return """
IF OBJECT_ID('Catalogo.View_SedesAreasServiciosEncuestasRespuestas', 'V') IS NULL
    EXEC('CREATE VIEW Catalogo.View_SedesAreasServiciosEncuestasRespuestas AS SELECT * FROM Catalogo.SedesAreasServiciosEncuestasRespuestas');
""".strip()


def build_merge_sql(temp_table_name: str = "#SedesAreasServiciosSource") -> str:
    key_columns = ["SedeId", "AreaId", "ServicioId"]
    update_columns = [
        "SedeNombre",
        "SedeEstadoDescripcion",
        "AreaNombre",
        "AreaEstadoDescripcion",
        "ServicioNombre",
        "ServicioEstadoDescripcion",
        "EncuestasPorRelacion",
        "CantidadEncuestas",
        "TotalRespuestasHistoricas",
    ]

    change_conditions: List[str] = [
        "target.EstadoRegistro <> 'Activo'"
    ]

    for column in update_columns:
        if column in ("EncuestasPorRelacion", "CantidadEncuestas", "TotalRespuestasHistoricas"):
            change_conditions.append(
                f"(target.{column} <> source.{column} OR (target.{column} IS NULL AND source.{column} IS NOT NULL) OR (target.{column} IS NOT NULL AND source.{column} IS NULL))"
            )
        else:
            change_conditions.append(
                f"ISNULL(target.{column}, '') <> ISNULL(source.{column}, '')"
            )

    set_clauses = [
        f"target.{column} = source.{column}" for column in update_columns
    ] + [
        "target.EstadoRegistro = 'Activo'",
        "target.FechaModificacion = SYSUTCDATETIME()",
    ]

    change_condition_text = " OR\n    ".join(change_conditions)
    set_clause_text = ",\n    ".join(set_clauses)

    return f"""
MERGE {TARGET_TABLE} AS target
USING {temp_table_name} AS source
    ON target.SedeId = source.SedeId
    AND ((target.AreaId = source.AreaId) OR (target.AreaId IS NULL AND source.AreaId IS NULL))
    AND ((target.ServicioId = source.ServicioId) OR (target.ServicioId IS NULL AND source.ServicioId IS NULL))
WHEN MATCHED AND (
    {change_condition_text}
) THEN
    UPDATE SET
    {set_clause_text}
WHEN NOT MATCHED BY TARGET THEN
    INSERT (SedeId, SedeNombre, SedeEstadoDescripcion, AreaId, AreaNombre, AreaEstadoDescripcion, ServicioId, ServicioNombre, ServicioEstadoDescripcion, EncuestasPorRelacion, CantidadEncuestas, TotalRespuestasHistoricas, FechaInsercion, FechaModificacion, EstadoRegistro)
    VALUES (source.SedeId, source.SedeNombre, source.SedeEstadoDescripcion, source.AreaId, source.AreaNombre, source.AreaEstadoDescripcion, source.ServicioId, source.ServicioNombre, source.ServicioEstadoDescripcion, source.EncuestasPorRelacion, source.CantidadEncuestas, source.TotalRespuestasHistoricas, SYSUTCDATETIME(), SYSUTCDATETIME(), 'Activo')
WHEN NOT MATCHED BY SOURCE AND target.EstadoRegistro = 'Activo' THEN
    UPDATE SET EstadoRegistro = 'Inactivo', FechaModificacion = SYSUTCDATETIME();
""".strip()


def build_temp_table_ddl(temp_table_name: str = "#SedesAreasServiciosSource") -> str:
    return f"""
CREATE TABLE {temp_table_name} (
    SedeId INT NOT NULL,
    SedeNombre NVARCHAR(200) NOT NULL,
    SedeEstadoDescripcion NVARCHAR(200) NULL,
    AreaId NVARCHAR(200) NULL,
    AreaNombre NVARCHAR(200) NOT NULL,
    AreaEstadoDescripcion NVARCHAR(200) NULL,
    ServicioId NVARCHAR(200) NULL,
    ServicioNombre NVARCHAR(200) NOT NULL,
    ServicioEstadoDescripcion NVARCHAR(200) NULL,
    EncuestasPorRelacion NVARCHAR(500) NULL,
    CantidadEncuestas INT NULL,
    TotalRespuestasHistoricas INT NULL
);
""".strip()


def get_source_connection() -> pyodbc.Connection:
    connection_string = get_source_connection_string()
    return pyodbc.connect(connection_string, timeout=10, autocommit=True)


def get_target_connection() -> pyodbc.Connection:
    connection_string = get_target_connection_string()
    return pyodbc.connect(connection_string, timeout=10, autocommit=True)


def fetch_source_rows() -> List[Tuple]:
    query = f"SELECT {', '.join(SOURCE_COLUMNS)} FROM {SOURCE_VIEW}"
    with get_source_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        return [tuple(row) for row in rows]


def ensure_target_table_exists(cursor: pyodbc.Cursor) -> None:
    cursor.execute(build_target_table_ddl())
    cursor.execute(build_target_view_ddl())


def sync_sedes_areas_servicios() -> dict:
    rows = fetch_source_rows()
    with get_target_connection() as target_connection:
        cursor = target_connection.cursor()
        ensure_target_table_exists(cursor)
        cursor.execute(build_temp_table_ddl())
        cursor.fast_executemany = True
        insert_sql = f"INSERT INTO #SedesAreasServiciosSource ({', '.join(SOURCE_COLUMNS)}) VALUES ({', '.join('?' for _ in SOURCE_COLUMNS)})"
        cursor.executemany(insert_sql, rows)
        cursor.execute(build_merge_sql())
        return {
            "rows_synced": len(rows),
            "message": f"Synchronized {len(rows)} rows from {SOURCE_VIEW} into {TARGET_TABLE}."
        }


def main() -> None:
    result = sync_sedes_areas_servicios()
    print(result["message"])


if __name__ == "__main__":
    main()
