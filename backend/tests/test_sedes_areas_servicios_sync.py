import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / "backend" / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.sync_sedes_areas_servicios import (
    SOURCE_COLUMNS,
    TARGET_TABLE,
    build_merge_sql,
    build_target_table_ddl,
    build_target_view_ddl,
)


def test_build_target_table_ddl_includes_expected_columns():
    sql = build_target_table_ddl()
    assert "Catalogo.SedesAreasServiciosEncuestasRespuestas" in sql
    assert "SedeId INT NOT NULL" in sql
    assert "AreaNombre NVARCHAR(200) NOT NULL" in sql
    assert "CantidadEncuestas INT NULL" in sql
    assert "FechaInsercion DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()" in sql
    assert "EstadoRegistro NVARCHAR(50) NOT NULL DEFAULT 'Activo'" in sql
    assert "CREATE UNIQUE INDEX UX_SedesAreasServiciosEncuestasRespuestas" in sql


def test_build_view_ddl_creates_local_view():
    sql = build_target_view_ddl()
    assert "CREATE VIEW Catalogo.View_SedesAreasServiciosEncuestasRespuestas" in sql
    assert "SELECT * FROM Catalogo.SedesAreasServiciosEncuestasRespuestas" in sql


def test_build_merge_sql_uses_primary_key_columns():
    sql = build_merge_sql()
    assert "ON target.SedeId = source.SedeId" in sql
    assert "target.AreaId = source.AreaId" in sql
    assert "target.ServicioId = source.ServicioId" in sql
    assert "WHEN NOT MATCHED BY TARGET THEN" in sql
    assert "WHEN NOT MATCHED BY SOURCE AND target.EstadoRegistro = 'Activo' THEN" in sql
    assert "INSERT (SedeId, SedeNombre, SedeEstadoDescripcion" in sql


def test_expected_source_columns_are_configured():
    assert "SedeId" in SOURCE_COLUMNS
    assert "ServicioNombre" in SOURCE_COLUMNS
    assert len(SOURCE_COLUMNS) == 12
