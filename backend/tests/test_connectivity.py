import os
import sys
import urllib.parse
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / "backend" / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import get_connection_string, engine
from backend.scheduler import get_batch_path


def test_connection_string_is_valid():
    connection_string = get_connection_string()
    assert connection_string.startswith("mssql+pyodbc:///?odbc_connect=")
    unquoted = urllib.parse.unquote(connection_string)
    assert "Driver=" in unquoted
    assert "Server=" in unquoted
    assert "Database=" in unquoted


def test_batch_path_exists():
    batch_file = Path(get_batch_path())
    assert batch_file.exists(), f"Batch file not found: {batch_file}"
    assert batch_file.is_file()


def test_sharepoint_configuration_format_is_valid():
    site_id = os.getenv("SP_SITE_ID")
    base_path = os.getenv("SP_BASE_PATH")
    assert site_id, "SP_SITE_ID tiene que estar configurado"
    assert base_path, "SP_BASE_PATH tiene que estar configurado"

    parts = [part.strip() for part in site_id.split(",") if part.strip()]
    assert len(parts) >= 3, f"SP_SITE_ID no tiene el formato esperado: {site_id}"
    assert "sharepoint.com" in parts[0].lower(), f"SP_SITE_ID debe contener sharepoint.com: {site_id}"
    assert "/" in base_path, f"SP_BASE_PATH debe usar formato SharePoint con /: {base_path}"
    assert not any(ch in base_path for ch in '<>:"|?*'), f"SP_BASE_PATH contiene caracteres inválidos: {base_path}"


def test_excel_export_directory_permissions():
    export_dir = Path(os.getenv("DIRECTORIO_PRUEBAS_EXPORTACION", r"F:\\ETL_DITIC\\temp_exportacion_multiarea\\PruebasExcel"))
    export_dir.mkdir(parents=True, exist_ok=True)
    temp_file = export_dir / "pytest_export_permission_test.txt"
    temp_file.write_text("ok", encoding="utf-8")
    assert temp_file.exists()
    temp_file.unlink()


@pytest.mark.skipif(
    not os.getenv("SQL_SERVER") and not os.getenv("SQL_USER"),
    reason="SQL credentials are not configured for connectivity tests",
)
def test_database_connectivity():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1
