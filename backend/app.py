import os
import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

# Agregamos la raíz del repositorio al PYTHONPATH para que los módulos raíz
# sean importables cuando el backend se ejecute.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configuración del logger
LOG_DIR = ROOT_DIR / "Logs" / "areas"
LOG_DIR.mkdir(parents=True, exist_ok=True)
JOB_LOG_DIR = ROOT_DIR / "Logs" / "portal_jobs"
JOB_LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "backend_errors.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text, or_

from .database import SessionLocal, engine, init_db
from .models import Area, JobParametro, JobEjecucion, CargaArea, Schedule
from .scheduler import create_monthly_task, delete_task, get_task_status, run_now, get_batch_path
from .orquestador import ejecutar_orquestador_batch
from .schema import (
    AreaModel,
    JobParamCreate,
    JobParamUpdate,
    JobExecutionModel,
    JobParametroModel,
    HistoryModel,
    JobStatusModel,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleModel,
)

app = FastAPI(title="Portal Encuestas Percepción", version="0.1.0")

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
RUNNING_JOBS = {}
FINISHED_JOBS = []
RUNNING_JOBS_LOCK = threading.Lock()
DATABASE_STARTUP_ERROR = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    index_html = FRONTEND_DIST / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    return {"status": "ok", "message": "Portal Encuestas Percepción API"}

@app.get("/api/health")
def health():
    return {
        "status": "ok" if DATABASE_STARTUP_ERROR is None else "degraded",
        "database": os.getenv("SQL_DATABASE", "DWHEncuestasPercepcion"),
        "database_error": DATABASE_STARTUP_ERROR,
    }


@app.get("/api/registros/anio-actual")
def get_registros_anio_actual():
    from .database import get_total_registros_anio_actual
    try:
        total = get_total_registros_anio_actual()
        return {"year": datetime.now().year, "total_registros": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schemas():
    with engine.begin() as conn:
        conn.execute(text("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name='Catalogo') EXEC('CREATE SCHEMA Catalogo')"))
        conn.execute(text("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name='Orquestacion') EXEC('CREATE SCHEMA Orquestacion')"))
        conn.execute(text("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name='Historial') EXEC('CREATE SCHEMA Historial')"))


def ensure_schema_columns():
    with engine.begin() as conn:
        conn.execute(text("""
            IF OBJECT_ID('Orquestacion.Schedules', 'U') IS NOT NULL
               AND COL_LENGTH('Orquestacion.Schedules', 'ParametroId') IS NULL
            BEGIN
                ALTER TABLE Orquestacion.Schedules ADD ParametroId INT NULL;
            END
        """))
        conn.execute(text("""
            IF OBJECT_ID('Orquestacion.Schedules', 'U') IS NOT NULL
               AND COL_LENGTH('Orquestacion.Schedules', 'ParametroId') IS NOT NULL
               AND NOT EXISTS (
                    SELECT 1
                    FROM sys.foreign_keys
                    WHERE name = 'FK_Schedules_JobParametros'
                      AND parent_object_id = OBJECT_ID('Orquestacion.Schedules')
               )
            BEGIN
                ALTER TABLE Orquestacion.Schedules
                ADD CONSTRAINT FK_Schedules_JobParametros
                FOREIGN KEY (ParametroId) REFERENCES Orquestacion.JobParametros(ParametroId);
            END
        """))


def refresh_catalogo_areas(db):
    try:
        resultado = db.execute(text(
            "SELECT DISTINCT AreaNombre FROM Catalogo.SedesAreasServiciosEncuestasRespuestas "
            "WHERE AreaNombre IS NOT NULL AND LTRIM(RTRIM(AreaNombre)) <> ''"
        ))
        nombres_fuente = {fila[0].strip() for fila in resultado if fila[0] and fila[0].strip()}

        areas_existentes = {area.NombreArea: area for area in db.query(Area).all()}

        for nombre in sorted(nombres_fuente):
            if nombre not in areas_existentes:
                db.add(Area(CodigoArea=nombre, NombreArea=nombre, Activo=True))

        for nombre, area_obj in areas_existentes.items():
            area_obj.Activo = nombre in nombres_fuente

        db.commit()
        return len([nombre for nombre in nombres_fuente if nombre not in areas_existentes])
    except Exception:
        db.rollback()
        raise


def seed_demo_job_records(db):
    try:
        if db.query(JobParametro).count() == 0 and db.query(JobEjecucion).count() == 0:
            area = db.query(Area).filter(
                or_(Area.NombreArea.ilike('CRAI'), Area.CodigoArea.ilike('CRAI'))
            ).first()
            if not area:
                area = Area(CodigoArea='CRAI', NombreArea='CRAI', Activo=True)
                db.add(area)
                db.flush()

            parametro = JobParametro(
                Mes=5,
                Anio=2026,
                AreaId=area.AreaId,
                UsuarioProgramo='demo'
            )
            db.add(parametro)
            db.flush()

            ejecucion = JobEjecucion(
                ParametroId=parametro.ParametroId,
                TipoCarga='mensual',
                Estado='Exitoso',
                Mensaje='Registro sintético inicial de orquestador',
                ArchivoLanzado=None,
                AreaId=area.AreaId,
            )
            db.add(ejecucion)
            db.commit()
    except Exception:
        db.rollback()


def resolve_area_id(db, area_name: Optional[str]):
    if not area_name:
        return None
    if area_name.upper() == "TODAS":
        return None
    area = db.query(Area).filter(
        or_(
            Area.NombreArea.ilike(area_name),
            Area.CodigoArea.ilike(area_name)
        )
    ).first()
    if not area:
        refresh_catalogo_areas(db)
        area = db.query(Area).filter(
            or_(
                Area.NombreArea.ilike(area_name),
                Area.CodigoArea.ilike(area_name)
            )
        ).first()
    return area.AreaId if area else None


def register_running_job(process, carga_id: int, metadata: dict):
    started_at = datetime.now().isoformat(timespec="seconds")
    job_info = {
        **metadata,
        "pid": process.pid,
        "carga_id": carga_id,
        "started_at": started_at,
        "status": "running",
    }
    with RUNNING_JOBS_LOCK:
        RUNNING_JOBS[process.pid] = job_info

    def monitor_process():
        returncode = process.wait()
        ended_at = datetime.now().isoformat(timespec="seconds")
        estado = "Finalizado" if returncode == 0 else "Error"
        archivo_log = getattr(process, "_portal_log_handle", None)
        log_path_local = None
        if archivo_log is not None:
            try:
                log_path_local = archivo_log.name
                archivo_log.write(f"\n[PORTAL] Proceso PID {process.pid} finalizo con codigo {returncode}.\n")
                archivo_log.flush()
                archivo_log.close()
                # Subir el log a Azure Blob Storage
                try:
                    from azure_blob_logger import AzureBlobManager
                    AzureBlobManager.upload_log(log_path_local, "portal_jobs")
                except Exception as e:
                    logger.error(f"No se pudo subir a Azure Blob: {e}")
            except Exception:
                pass
        with SessionLocal() as db:
            carga = db.query(CargaArea).filter(CargaArea.CargaId == carga_id).first()
            if carga:
                carga.Estado = estado
                detalle = f"Proceso PID {process.pid} finalizo con codigo {returncode}."
                carga.Observaciones = f"{carga.Observaciones or ''}\n{detalle}".strip()
                db.commit()
            ejecucion_id = metadata.get("ejecucion_id")
            if ejecucion_id:
                ejecucion = db.query(JobEjecucion).filter(JobEjecucion.EjecucionId == ejecucion_id).first()
                if ejecucion:
                    ejecucion.Estado = estado
                    ejecucion.Mensaje = f"Proceso PID {process.pid} finalizo con codigo {returncode}."
                    db.commit()
        with RUNNING_JOBS_LOCK:
            finished = RUNNING_JOBS.pop(process.pid, None)
            if finished is not None:
                finished["status"] = estado
                finished["ended_at"] = ended_at
                finished["returncode"] = returncode
                FINISHED_JOBS.insert(0, finished)
                del FINISHED_JOBS[10:]

    thread = threading.Thread(target=monitor_process, daemon=True)
    thread.start()


def get_running_job_list():
    with RUNNING_JOBS_LOCK:
        return list(RUNNING_JOBS.values())


def read_job_log(log_path: Optional[str], max_chars: int = 120000):
    if not log_path:
        return ""
    path = Path(log_path)
    if not path.exists() or not path.is_file():
        # Intentar leer desde Azure Blob Storage si no está en disco local
        try:
            from azure_blob_logger import AzureBlobManager
            blob_content = AzureBlobManager.read_log("portal_jobs", path.name, max_chars)
            if blob_content is not None:
                return blob_content
        except Exception:
            pass
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def get_latest_runtime_log():
    with RUNNING_JOBS_LOCK:
        running = list(RUNNING_JOBS.values())
        finished = list(FINISHED_JOBS)
    selected_jobs = running or finished[:1]
    log_blocks = []
    for job in selected_jobs:
        header = f"===== PID {job.get('pid')} | {job.get('area') or 'TODAS'} | {job.get('mes')}/{job.get('anio')} | {job.get('status')} ====="
        log_blocks.append(f"{header}\n{read_job_log(job.get('log_path'))}")
    latest_finished = finished[0] if finished else None
    return {
        "running": len(running) > 0,
        "count": len(running),
        "state": "En ejecucion" if running else "En pausa",
        "execution_status": "En ejecucion" if running else (latest_finished.get("status") if latest_finished else "En pausa"),
        "refreshed_at": datetime.now().isoformat(timespec="seconds"),
        "jobs": running,
        "latest_finished": latest_finished,
        "log": "\n\n".join(log_blocks).strip(),
    }


@app.on_event("startup")
async def startup():
    global DATABASE_STARTUP_ERROR
    try:
        ensure_schemas()
        init_db()
        ensure_schema_columns()
        with SessionLocal() as db:
            refresh_catalogo_areas(db)
            seed_demo_job_records(db)
        DATABASE_STARTUP_ERROR = None
    except Exception as exc:
        DATABASE_STARTUP_ERROR = str(exc)
        logger.warning("No se pudo inicializar la base de datos en el arranque: %s", exc)


@app.get("/api/areas", response_model=List[AreaModel])
def get_areas(refresh: bool = False, db=Depends(get_db)):
    if refresh:
        refresh_catalogo_areas(db)
    areas = db.query(Area).order_by(Area.NombreArea).all()
    if not areas:
        refresh_catalogo_areas(db)
        areas = db.query(Area).order_by(Area.NombreArea).all()
    return areas


@app.post("/api/areas/refresh")
def refresh_areas(db=Depends(get_db)):
    inserted = refresh_catalogo_areas(db)
    return {"refreshed": inserted}


@app.get("/api/history", response_model=List[HistoryModel])
def get_history(
    limit: int = 100,
    offset: int = 0,
    area_id: Optional[int] = None,
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    tipo_carga: Optional[str] = None,
    db=Depends(get_db),
):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    query = db.query(CargaArea)
    if area_id is not None:
        query = query.filter(CargaArea.AreaId == area_id)
    if anio is not None:
        query = query.filter(CargaArea.Anio == anio)
    if mes is not None:
        query = query.filter(CargaArea.Mes == mes)
    if tipo_carga:
        query = query.filter(CargaArea.TipoCarga == tipo_carga)
    return query.order_by(CargaArea.FechaCarga.desc(), CargaArea.CargaId.desc()).offset(offset).limit(limit).all()


@app.get("/api/jobs", response_model=List[JobExecutionModel])
def get_jobs(limit: int = 100, offset: int = 0, db=Depends(get_db)):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    return db.query(JobEjecucion).order_by(JobEjecucion.FechaEjecucion.desc(), JobEjecucion.EjecucionId.desc()).offset(offset).limit(limit).all()


@app.get("/api/jobs/running")
def get_running_jobs(db=Depends(get_db)):
    running = get_running_job_list()
    latest_history = db.query(CargaArea).order_by(CargaArea.FechaCarga.desc(), CargaArea.CargaId.desc()).limit(10).all()
    latest_executions = db.query(JobEjecucion).order_by(JobEjecucion.FechaEjecucion.desc(), JobEjecucion.EjecucionId.desc()).limit(10).all()
    return {
        "running": len(running) > 0,
        "count": len(running),
        "jobs": running,
        "latest_history": latest_history,
        "latest_executions": latest_executions,
    }


@app.get("/api/jobs/runtime-log")
def get_job_runtime_log():
    return get_latest_runtime_log()


@app.get("/api/job-params", response_model=List[JobParametroModel])
def get_job_params(limit: int = 100, offset: int = 0, db=Depends(get_db)):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    return db.query(JobParametro).order_by(JobParametro.FechaProgramacion.desc(), JobParametro.ParametroId.desc()).offset(offset).limit(limit).all()


@app.post("/api/job-params", response_model=JobParametroModel)
def create_job_param(params: JobParamCreate, db=Depends(get_db)):
    try:
        anio = params.anio or datetime.now().year
        if params.mes == 0:
            today = datetime.now()
            if today.month == 1:
                mes = 12
                anio = today.year - 1
            else:
                mes = today.month - 1
        else:
            mes = params.mes

        area_id = params.area_id
        area_name = params.area
        if not area_id and area_name:
            area_id = resolve_area_id(db, area_name)
            if area_id is None:
                raise HTTPException(status_code=400, detail=f"Área '{area_name}' no encontrada")

        parametro = JobParametro(
            Mes=mes,
            Anio=anio,
            AreaId=area_id,
            UsuarioProgramo=params.usuario,
        )
        db.add(parametro)
        db.commit()
        db.refresh(parametro)
        return parametro
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando el job param: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creando el parámetro del job")


@app.put("/api/job-params/{parametro_id}", response_model=JobParametroModel)
def update_job_param(parametro_id: int, params: JobParamUpdate, db=Depends(get_db)):
    parametro = db.query(JobParametro).filter(JobParametro.ParametroId == parametro_id).first()
    if not parametro:
        raise HTTPException(status_code=404, detail="Parametro de job no encontrado")

    try:
        values = params.dict(exclude_unset=True)
        if "mes" in values:
            mes_value = values["mes"]
            if mes_value == 0:
                today = datetime.now()
                parametro.Mes = 12 if today.month == 1 else today.month - 1
                parametro.Anio = today.year - 1 if today.month == 1 else today.year
            else:
                parametro.Mes = mes_value
        if "anio" in values and values["anio"] is not None:
            parametro.Anio = values["anio"]
        if "area_id" in values:
            parametro.AreaId = values["area_id"]
        if "area" in values:
            parametro.AreaId = resolve_area_id(db, values["area"])
            if values["area"] and values["area"].upper() != "TODAS" and parametro.AreaId is None:
                raise HTTPException(status_code=400, detail=f"Area '{values['area']}' no encontrada")
        if "usuario" in values:
            parametro.UsuarioProgramo = values["usuario"]
        db.commit()
        db.refresh(parametro)
        return parametro
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando el job param: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error actualizando el parametro del job")


@app.post("/api/job-params/{parametro_id}/run")
def execute_job_param(parametro_id: int, db=Depends(get_db)):
    parametro = db.query(JobParametro).filter(JobParametro.ParametroId == parametro_id).first()
    if not parametro:
        raise HTTPException(status_code=404, detail="Parámetro de job no encontrado")

    if parametro.AreaId:
        area_obj = db.query(Area).filter(Area.AreaId == parametro.AreaId).first()
        area_name = area_obj.NombreArea if area_obj else None
    else:
        area_name = "TODAS"

    auto_date = parametro.Mes == 0
    mes = None if auto_date else parametro.Mes
    anio = None if auto_date else parametro.Anio

    result = run_now(mes or 0, anio or datetime.now().year, "mensual", area=area_name, auto_date=auto_date)
    estado = "Exitoso" if result["returncode"] == 0 else "Error"

    ejecucion = JobEjecucion(
        ParametroId=parametro.ParametroId,
        TipoCarga="mensual",
        Estado=estado,
        Mensaje=result.get("stderr") or result.get("stdout"),
        ArchivoLanzado=result.get("batch_path"),
        AreaId=parametro.AreaId,
    )
    db.add(ejecucion)

    carga = CargaArea(
        Mes=parametro.Mes,
        Anio=parametro.Anio,
        AreaId=parametro.AreaId,
        TipoCarga="mensual",
        Estado=estado,
        Observaciones=result.get("stderr") or result.get("stdout"),
    )
    db.add(carga)
    db.commit()
    db.refresh(ejecucion)
    return ejecucion


@app.delete("/api/job-params/{parametro_id}")
def delete_job_param(parametro_id: int, db=Depends(get_db)):
    parametro = db.query(JobParametro).filter(JobParametro.ParametroId == parametro_id).first()
    if not parametro:
        raise HTTPException(status_code=404, detail="Parámetro de job no encontrado")
    referenced = db.query(Schedule).filter(Schedule.ParametroId == parametro_id).count()
    if referenced:
        raise HTTPException(status_code=409, detail="El job esta asociado a uno o mas schedules")
    db.delete(parametro)
    db.commit()
    return {"deleted": parametro_id}


@app.get("/api/jobs/schedule", response_model=JobStatusModel)
def get_job_schedule():
    status = get_task_status()
    return JobStatusModel(**status)


@app.post("/api/jobs/run", response_model=JobExecutionModel)
def execute_job(params: JobParamCreate, db=Depends(get_db)):
    try:
        anio = params.anio or datetime.now().year
        auto_date = params.mes == 0
        if auto_date:
            today = datetime.now()
            if today.month == 1:
                mes = 12
                anio = today.year - 1
            else:
                mes = today.month - 1
        else:
            mes = params.mes

        area_id = params.area_id
        area_name = params.area

        if not area_id and area_name:
            area_id = resolve_area_id(db, area_name)
            if area_id is None:
                raise HTTPException(status_code=400, detail=f"Área '{area_name}' no encontrada")

        if area_id and not area_name:
            area_obj = db.query(Area).filter(Area.AreaId == area_id).first()
            if area_obj:
                area_name = area_obj.NombreArea

        parametro = JobParametro(
            Mes=mes,
            Anio=anio,
            AreaId=area_id,
            UsuarioProgramo=params.usuario,
        )
        db.add(parametro)
        db.flush()

        tipo_carga = "mensual"
        result = run_now(mes, anio, tipo_carga, area=area_name, auto_date=auto_date)
        estado = "Exitoso" if result["returncode"] == 0 else "Error"
        ejecucion = JobEjecucion(
            ParametroId=parametro.ParametroId,
            TipoCarga=tipo_carga,
            Estado=estado,
            Mensaje=result.get("stderr") or result.get("stdout"),
            ArchivoLanzado=result.get("batch_path"),
            AreaId=area_id,
        )
        db.add(ejecucion)
        carga = CargaArea(
            Mes=mes,
            Anio=anio,
            AreaId=area_id,
            TipoCarga=tipo_carga,
            Estado=estado,
            Observaciones=result.get("stderr") or result.get("stdout"),
        )
        db.add(carga)
        db.commit()
        db.refresh(ejecucion)
        return ejecucion

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al ejecutar el job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al ejecutar el job")


@app.post("/api/jobs/schedule")
def schedule_job(start_time: str = "00:05"):
    result = create_monthly_task(start_time=start_time)
    if result["returncode"] != 0:
        raise HTTPException(status_code=500, detail=f"Error creando tarea: {result['stderr']}")
    return result


@app.get("/api/launchers")
def get_launchers():
    launcher_dir = ROOT_DIR / "VersionesEncuestas"
    if not launcher_dir.exists():
        raise HTTPException(status_code=500, detail="No se encontró el directorio de launchers")
    launchers = [p.name for p in launcher_dir.glob("*.py") if p.is_file()]
    return {"launchers": sorted(launchers)}


@app.get("/api/schedules", response_model=List[ScheduleModel])
def get_schedules(db=Depends(get_db)):
    return db.query(Schedule).order_by(Schedule.FechaCreacion.desc()).all()


@app.post("/api/schedules", response_model=ScheduleModel)
def create_schedule(schedule: ScheduleCreate, db=Depends(get_db)):
    try:
        if schedule.parametro_id:
            parametro = db.query(JobParametro).filter(JobParametro.ParametroId == schedule.parametro_id).first()
            if not parametro:
                raise HTTPException(status_code=400, detail="Job asociado no encontrado")

        area_id = schedule.area_id
        if not area_id and schedule.area:
            area_id = resolve_area_id(db, schedule.area)
            if area_id is None:
                raise HTTPException(status_code=400, detail=f"Área '{schedule.area}' no encontrada")

        if schedule.periodico and not schedule.dia_del_mes:
            raise HTTPException(status_code=400, detail="Debe indicar el día del mes para una programación periódica")

        new_schedule = Schedule(
            ParametroId=schedule.parametro_id,
            Nombre=schedule.nombre,
            Activo=schedule.activo,
            Periodico=schedule.periodico,
            ServicioActivo=schedule.servicio_activo,
            MesAnterior=schedule.mes_anterior,
            DiaDelMes=schedule.dia_del_mes,
            FechaEspecifica=schedule.fecha_especifica,
            Hora=schedule.hora,
            AreaId=area_id,
            TipoCarga="mensual",
            Launcher=schedule.launcher,
            UsuarioProgramo=schedule.usuario,
        )
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        return new_schedule
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creando la programación")


@app.put("/api/schedules/{schedule_id}", response_model=ScheduleModel)
def update_schedule(schedule_id: int, payload: ScheduleUpdate, db=Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.ScheduleId == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule no encontrado")

    try:
        values = payload.dict(exclude_unset=True)
        if "parametro_id" in values:
            parametro_id = values["parametro_id"]
            if parametro_id:
                parametro = db.query(JobParametro).filter(JobParametro.ParametroId == parametro_id).first()
                if not parametro:
                    raise HTTPException(status_code=400, detail="Job asociado no encontrado")
            schedule.ParametroId = parametro_id
        if "nombre" in values and values["nombre"] is not None:
            schedule.Nombre = values["nombre"]
        if "activo" in values and values["activo"] is not None:
            schedule.Activo = values["activo"]
        if "periodico" in values and values["periodico"] is not None:
            schedule.Periodico = values["periodico"]
        if "servicio_activo" in values and values["servicio_activo"] is not None:
            schedule.ServicioActivo = values["servicio_activo"]
        if "mes_anterior" in values and values["mes_anterior"] is not None:
            schedule.MesAnterior = values["mes_anterior"]
        if "dia_del_mes" in values:
            schedule.DiaDelMes = values["dia_del_mes"]
        if "fecha_especifica" in values:
            schedule.FechaEspecifica = values["fecha_especifica"]
        if "hora" in values and values["hora"] is not None:
            schedule.Hora = values["hora"]
        if "area_id" in values:
            schedule.AreaId = values["area_id"]
        if "area" in values:
            schedule.AreaId = resolve_area_id(db, values["area"])
            if values["area"] and values["area"].upper() != "TODAS" and schedule.AreaId is None:
                raise HTTPException(status_code=400, detail=f"Area '{values['area']}' no encontrada")
        if "tipo_carga" in values and values["tipo_carga"] is not None:
            schedule.TipoCarga = "mensual"
        if "launcher" in values and values["launcher"] is not None:
            schedule.Launcher = values["launcher"]
        if "usuario" in values:
            schedule.UsuarioProgramo = values["usuario"]
        if schedule.Periodico and not schedule.DiaDelMes:
            raise HTTPException(status_code=400, detail="Debe indicar el dia del mes para una programacion periodica")
        db.commit()
        db.refresh(schedule)
        return schedule
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error actualizando la programacion")


@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db=Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.ScheduleId == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule no encontrado")
    db.delete(schedule)
    db.commit()
    return {"deleted": schedule_id}


def run_python_launcher(script_name: str, mes: int, anio: int, auto_date: bool, area_name: Optional[str]) -> dict:
    script_path = ROOT_DIR / "VersionesEncuestas" / script_name
    if not script_path.exists():
        return {"returncode": 1, "stdout": "", "stderr": f"Lanzador no encontrado: {script_name}", "batch_path": str(script_path)}
    args = [sys.executable, str(script_path)]
    if auto_date:
        args.append("--auto_date")
    else:
        args += ["--anio", str(anio), "--mes", str(mes)]
    if area_name:
        args += ["--area", area_name]
    result = subprocess.run(args, capture_output=True, text=True, shell=False)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "batch_path": str(script_path),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/schedules/{schedule_id}/trigger")
def trigger_schedule(schedule_id: int, db=Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.ScheduleId == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule no encontrado")
    if not schedule.Activo or not schedule.ServicioActivo:
        raise HTTPException(status_code=400, detail="El schedule no está activo")

    now = datetime.now()
    auto_date = schedule.MesAnterior and not schedule.ParametroId
    area_id = schedule.AreaId

    if schedule.ParametroId:
        parametro = db.query(JobParametro).filter(JobParametro.ParametroId == schedule.ParametroId).first()
        if not parametro:
            raise HTTPException(status_code=400, detail="Job asociado no encontrado")
        mes = parametro.Mes
        anio = parametro.Anio
        area_id = parametro.AreaId
    elif auto_date:
        if now.month == 1:
            mes = 12
            anio = now.year - 1
        else:
            mes = now.month - 1
            anio = now.year
        parametro = JobParametro(
            Mes=mes,
            Anio=anio,
            AreaId=area_id,
            UsuarioProgramo=schedule.UsuarioProgramo,
        )
        db.add(parametro)
        db.flush()
    else:
        if schedule.FechaEspecifica:
            mes = schedule.FechaEspecifica.month
            anio = schedule.FechaEspecifica.year
        else:
            mes = now.month
            anio = now.year
        parametro = JobParametro(
            Mes=mes,
            Anio=anio,
            AreaId=area_id,
            UsuarioProgramo=schedule.UsuarioProgramo,
        )
        db.add(parametro)
        db.flush()

    area_name = None
    if area_id:
        area_obj = db.query(Area).filter(Area.AreaId == area_id).first()
        area_name = area_obj.NombreArea if area_obj else None

    result = run_python_launcher(schedule.Launcher, mes, anio, auto_date, area_name)
    estado = "Exitoso" if result["returncode"] == 0 else "Error"

    ejecucion = JobEjecucion(
        ParametroId=parametro.ParametroId,
        TipoCarga="mensual",
        Estado=estado,
        Mensaje=result.get("stderr") or result.get("stdout"),
        ArchivoLanzado=result.get("batch_path"),
        AreaId=area_id,
    )
    db.add(ejecucion)
    carga = CargaArea(
        Mes=mes,
        Anio=anio,
        AreaId=area_id,
        TipoCarga="mensual",
        Estado=estado,
        Observaciones=result.get("stderr") or result.get("stdout"),
    )
    db.add(carga)
    db.commit()
    db.refresh(ejecucion)
    return ejecucion


class OrquestadorRequest(BaseModel):
    area: Optional[str] = "TODAS"
    anio: Optional[int] = None
    mes: Optional[int] = None
    auto_date: bool = False


@app.post("/api/jobs/disable")
def disable_schedule():
    result = delete_task()
    if result["returncode"] != 0:
        raise HTTPException(status_code=500, detail=f"Error eliminando tarea: {result['stderr']}")
    return result


@app.post("/api/orquestador/run")
def run_orquestador(request: OrquestadorRequest, db=Depends(get_db)):
    try:
        area_id = None
        if request.area and request.area.upper() != "TODAS":
            area_id = resolve_area_id(db, request.area)

        anio = request.anio
        mes = request.mes
        if request.auto_date:
            today = datetime.now()
            if mes is None:
                if today.month == 1:
                    mes = 12
                    anio = today.year - 1
                else:
                    mes = today.month - 1
            if anio is None:
                anio = today.year

        tipo_carga = "mensual"
        parametro = JobParametro(
            Mes=mes or 0,
            Anio=anio or datetime.now().year,
            AreaId=area_id,
            UsuarioProgramo="portal",
        )
        db.add(parametro)
        db.flush()

        carga = CargaArea(
            Mes=mes or 0,
            Anio=anio or datetime.now().year,
            AreaId=area_id,
            TipoCarga=tipo_carga,
            Estado="Iniciado",
            Observaciones="Lanzador en preparacion desde el portal."
        )
        db.add(carga)
        db.flush()

        ejecucion = JobEjecucion(
            ParametroId=parametro.ParametroId,
            TipoCarga="mensual",
            Estado="Iniciado",
            Mensaje="Proceso iniciado desde el portal.",
            ArchivoLanzado=get_batch_path(),
            AreaId=area_id,
        )
        db.add(ejecucion)
        db.flush()

        log_path = JOB_LOG_DIR / f"job_{carga.CargaId}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        comando = ejecutar_orquestador_batch(request.area or "TODAS", anio, mes, request.auto_date, log_path=log_path)

        carga.Observaciones = f"Lanzador ejecutado: {comando.args if hasattr(comando, 'args') else str(comando)}\nLog: {log_path}"
        ejecucion.ArchivoLanzado = str(log_path)
        db.commit()
        db.refresh(carga)
        db.refresh(ejecucion)
        register_running_job(
            comando,
            carga.CargaId,
            {
                "ejecucion_id": ejecucion.EjecucionId,
                "area": request.area,
                "anio": anio,
                "mes": mes,
                "auto_date": request.auto_date,
                "tipo_carga": tipo_carga,
                "log_path": str(log_path),
            },
        )

        return {
            "status": "started",
            "area": request.area,
            "anio": request.anio,
            "mes": request.mes,
            "auto_date": request.auto_date,
            "pid": comando.pid,
            "execution_id": ejecucion.EjecucionId,
            "log_path": str(log_path),
            "command": "cmd.exe /c " + str(Path(get_batch_path()).name) +
                (" --area " + (request.area or "TODAS") if not request.auto_date else "") +
                (" --anio " + str(anio) if anio is not None and not request.auto_date else "") +
                (" --mes " + str(mes) if mes is not None and not request.auto_date else "")
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al ejecutar el orquestador: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al ejecutar el orquestador")


@app.get("/api/status", response_model=JobStatusModel)
def task_status():
    status = get_task_status()
    return JobStatusModel(**status)

@app.get("/{full_path:path}")
def spa_catch_all(full_path: str):
    candidate = FRONTEND_DIST / full_path
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)

    index_html = FRONTEND_DIST / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    raise HTTPException(status_code=404, detail="Resource not found")
