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


def test_portal_job_exec_and_email(monkeypatch):
    """Simula ejecución del job CRAI 2026-05, verifica éxito, log y envío de email simulado."""

    def fake_run_command(args):
        # Simulamos un batch exitoso que además escribe una marca de envío de correo
        return 0, "Proceso completado\nEMAIL_SENT: destinatario=test@example.com", ""

    monkeypatch.setattr("backend.scheduler.run_command", fake_run_command)

    client = TestClient(app)

    payload = {"mes": 5, "anio": 2026, "area": "CRAI", "usuario": "testuser"}
    resp = client.post("/api/jobs/run", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("Estado") == "Exitoso"
    assert data.get("Mensaje") is not None
    assert "EMAIL_SENT" in data.get("Mensaje")

    # Verificamos que la ejecución quedó registrada en el historial de ejecuciones
    jobs_resp = client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert any(j["EjecucionId"] == data["EjecucionId"] for j in jobs)
