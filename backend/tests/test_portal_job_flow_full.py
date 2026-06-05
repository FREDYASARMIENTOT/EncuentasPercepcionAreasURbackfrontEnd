import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / "backend" / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

from backend.app import app


def test_portal_job_exec_full_flow(monkeypatch):
    """Prueba de integración simulada: batch genera Excel, lo sube a SharePoint/Azure y luego se envía el correo final.

    - Mockea la ejecución del batch para devolver stdout con marcadores de subida y envío de correo.
    - Mockea AzureBlobManager.read_log para simular lectura de logs remotos.
    - Verifica que la API registre la ejecución como exitosa y que el mensaje/observaciones contienen los marcadores esperados.
    """

    # Simulamos que el batch devuelve stdout con indicadores de éxito, subida y envío de correo
    simulated_stdout = (
        "Proceso completado\n"
        "EXPORT_EXCEL: CRAI_2026_05.xlsx\n"
        "SHAREPOINT_UPLOADED: /sites/encuestas/CRAI_2026_05.xlsx\n"
        "EMAIL_SENT: to=fredy.sarmiento@urosario.edu.co; subject=Reporte CRAI 2026-05\n"
    )

    def fake_run_command(args):
        return 0, simulated_stdout, ""

    # Mockeamos la función que ejecuta comandos (scheduler.run_command)
    monkeypatch.setattr("backend.scheduler.run_command", fake_run_command)

    # Mockeamos lectura remota de logs desde Azure Blob (si la app intenta leerlos)
    def fake_read_log(subfolder, file_name, max_chars=120000):
        return "[SIMULATED REMOTE LOG]\nDetalle: export ok\nEMAIL_SENT registro presente"

    monkeypatch.setattr("azure_blob_logger.AzureBlobManager.read_log", fake_read_log, raising=False)

    client = TestClient(app)

    payload = {"mes": 5, "anio": 2026, "area": "CRAI", "usuario": "testuser"}
    resp = client.post("/api/jobs/run", json=payload)

    assert resp.status_code == 200
    data = resp.json()

    # Validaciones principales
    assert data.get("Estado") == "Exitoso"
    mensaje = data.get("Mensaje") or ""
    assert "SHAREPOINT_UPLOADED" in mensaje
    assert "EMAIL_SENT" in mensaje

    # La ejecución debe aparecer en la lista de jobs
    jobs_resp = client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert any(j["EjecucionId"] == data["EjecucionId"] for j in jobs)

    # Opcional: consultar log runtime y asegurarnos que la API devuelve algo (mock read_log cubre esto)
    runtime_log = client.get("/api/jobs/runtime-log")
    assert runtime_log.status_code == 200
    log_json = runtime_log.json()
    assert isinstance(log_json.get("log"), str)
    assert "EMAIL_SENT" in (log_json.get("log") or "")
