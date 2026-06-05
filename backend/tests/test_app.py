import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / "backend" / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import or_
from backend.app import app
from backend.database import SessionLocal
from backend.models import Area, CargaArea, JobParametro, JobEjecucion

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data


@pytest.mark.parametrize("path", ["/api/areas", "/api/jobs", "/api/history", "/api/status"])
def test_api_endpoints_return_json_or_200(path):
    response = client.get(path)
    assert response.status_code in (200, 500)
    assert response.headers["content-type"].startswith("application/json")


def test_execute_job_creates_historial_and_job_records(monkeypatch):
    db = SessionLocal()
    created_area = False
    try:
        area = db.query(Area).filter(
            or_(Area.NombreArea.ilike("CRAI"), Area.CodigoArea.ilike("CRAI"))
        ).first()
        if not area:
            area = Area(CodigoArea="CRAI", NombreArea="CRAI", Activo=True)
            db.add(area)
            db.commit()
            db.refresh(area)
            created_area = True

        before_count = db.query(CargaArea).count()

        def fake_run_now(mes, anio, tipo_carga, area=None, auto_date=False):
            return {
                "returncode": 0,
                "stdout": "Simulated batch success",
                "stderr": "",
                "batch_path": "Lanzador_encuestapercepcion.bat",
                "timestamp": datetime.now().isoformat(),
            }

        monkeypatch.setattr("backend.app.run_now", fake_run_now)

        payload = {
            "mes": 5,
            "anio": 2026,
            "area": "CRAI",
            "tipo_carga": "mensual",
            "usuario": "test"
        }
        response = client.post("/api/jobs/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["TipoCarga"] == "mensual"
        assert data["Estado"] == "Exitoso"

        after_count = db.query(CargaArea).count()
        assert after_count == before_count + 1

        carga = db.query(CargaArea).order_by(CargaArea.CargaId.desc()).first()
        assert carga is not None
        assert carga.Mes == 5
        assert carga.Anio == 2026
        assert carga.AreaId == area.AreaId
        assert carga.TipoCarga == "mensual"
        assert carga.Estado == "Exitoso"
        assert "Simulated batch success" in carga.Observaciones

        ejecucion = db.query(JobEjecucion).filter(JobEjecucion.ParametroId == data["ParametroId"]).first()
        assert ejecucion is not None
        assert ejecucion.AreaId == area.AreaId

        parametro = db.query(JobParametro).filter(JobParametro.ParametroId == data["ParametroId"]).first()
        assert parametro is not None

        db.delete(ejecucion)
        db.delete(carga)
        db.delete(parametro)
        db.commit()
    finally:
        if created_area:
            db.delete(area)
            db.commit()
        db.close()


def test_job_param_creation_and_deletion():
    db = SessionLocal()
    created_area = False
    try:
        area = db.query(Area).filter(
            or_(Area.NombreArea.ilike("CRAI"), Area.CodigoArea.ilike("CRAI"))
        ).first()
        if not area:
            area = Area(CodigoArea="CRAI", NombreArea="CRAI", Activo=True)
            db.add(area)
            db.commit()
            db.refresh(area)
            created_area = True

        payload = {
            "mes": 5,
            "anio": 2026,
            "area": "CRAI",
            "tipo_carga": "mensual",
            "usuario": "test"
        }
        response = client.post("/api/job-params", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["Mes"] == 5
        assert data["Anio"] == 2026
        assert data["AreaId"] == area.AreaId

        param_id = data["ParametroId"]
        response = client.get(f"/api/job-params")
        assert response.status_code == 200
        params = response.json()
        assert any(item["ParametroId"] == param_id for item in params)

        response = client.delete(f"/api/job-params/{param_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] == param_id

        deleted_param = db.query(JobParametro).filter(JobParametro.ParametroId == param_id).first()
        assert deleted_param is None
    finally:
        if created_area:
            db.delete(area)
            db.commit()
        db.close()


def test_run_job_param_creates_execution_and_history(monkeypatch):
    db = SessionLocal()
    created_area = False
    try:
        area = db.query(Area).filter(
            or_(Area.NombreArea.ilike("CRAI"), Area.CodigoArea.ilike("CRAI"))
        ).first()
        if not area:
            area = Area(CodigoArea="CRAI", NombreArea="CRAI", Activo=True)
            db.add(area)
            db.commit()
            db.refresh(area)
            created_area = True

        before_ejecuciones = db.query(JobEjecucion).count()
        before_cargas = db.query(CargaArea).count()

        def fake_run_now(mes, anio, tipo_carga, area=None, auto_date=False):
            return {
                "returncode": 0,
                "stdout": "Simulated job param success",
                "stderr": "",
                "batch_path": "Lanzador_encuestapercepcion.bat",
                "timestamp": datetime.now().isoformat(),
            }

        monkeypatch.setattr("backend.app.run_now", fake_run_now)

        payload = {
            "mes": 0,
            "anio": 0,
            "area": "CRAI",
            "tipo_carga": "mensual",
            "usuario": "test-param"
        }

        response = client.post("/api/job-params", json=payload)
        assert response.status_code == 200
        parametro = response.json()
        param_id = parametro["ParametroId"]
        assert parametro["AreaId"] == area.AreaId

        response = client.post(f"/api/job-params/{param_id}/run")
        assert response.status_code == 200
        ejecucion = response.json()
        assert ejecucion["ParametroId"] == param_id
        assert ejecucion["TipoCarga"] == "mensual"
        assert ejecucion["Estado"] == "Exitoso"

        assert db.query(JobEjecucion).count() == before_ejecuciones + 1
        assert db.query(CargaArea).count() == before_cargas + 1

        carga = db.query(CargaArea).order_by(CargaArea.CargaId.desc()).first()
        assert carga is not None
        assert carga.AreaId == area.AreaId
        assert carga.TipoCarga == "mensual"
        assert carga.Estado == "Exitoso"

        ejec = db.query(JobEjecucion).filter(JobEjecucion.ParametroId == param_id).first()
        assert ejec is not None
        assert ejec.TipoCarga == "mensual"

        db.delete(ejec)
        db.delete(carga)
        db.delete(db.query(JobParametro).filter(JobParametro.ParametroId == param_id).first())
        db.commit()
    finally:
        if created_area:
            db.delete(area)
            db.commit()
        db.close()
