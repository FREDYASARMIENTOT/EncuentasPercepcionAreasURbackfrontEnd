import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from portal.backend.app import ensure_schema_columns, ensure_schemas
from portal.backend.database import SessionLocal, init_db
from portal.backend.models import Area, CargaArea, JobEjecucion, JobParametro, Schedule


AREAS = [
    ("CRAI", "CRAI"),
    ("CASAUR", "CASA UR"),
    ("CANCILLERIA", "Cancilleria UR"),
    ("TI", "Tecnologia"),
]


def get_or_create_area(db, code: str, name: str) -> Area:
    area = db.query(Area).filter(Area.CodigoArea == code).first()
    if area:
        area.NombreArea = name
        area.Activo = True
        return area

    area = Area(CodigoArea=code, NombreArea=name, Activo=True)
    db.add(area)
    db.flush()
    return area


def main() -> None:
    ensure_schemas()
    init_db()
    ensure_schema_columns()

    with SessionLocal() as db:
        areas = [get_or_create_area(db, code, name) for code, name in AREAS]
        db.flush()

        seed_params_count = db.query(JobParametro).filter(JobParametro.UsuarioProgramo == "seed").count()
        if seed_params_count < 4:
            for index, area in enumerate(areas, start=1):
                db.add(
                    JobParametro(
                        Mes=5,
                        Anio=2026,
                        AreaId=area.AreaId,
                        UsuarioProgramo="seed",
                    )
                )
            db.flush()

        params = db.query(JobParametro).filter(JobParametro.UsuarioProgramo == "seed").order_by(JobParametro.ParametroId.desc()).limit(4).all()
        seed_history_count = db.query(CargaArea).filter(CargaArea.Observaciones.like("Dato de prueba portal%")).count()
        if seed_history_count < 12:
            states = ["Exitoso", "Exitoso", "Error", "Iniciado", "Finalizado"]
            for index in range(12):
                area = areas[index % len(areas)]
                db.add(
                    CargaArea(
                        FechaCarga=datetime.now() - timedelta(minutes=index * 15),
                        Mes=((index % 12) + 1),
                        Anio=2026,
                        AreaId=area.AreaId,
                        TipoCarga="mensual" if index % 2 == 0 else "manual",
                        RegistrosProcesados=100 + index,
                        Estado=states[index % len(states)],
                        Observaciones=f"Dato de prueba portal #{index + 1}",
                    )
                )

        seed_execution_count = db.query(JobEjecucion).filter(JobEjecucion.Mensaje.like("Ejecucion de prueba%")).count()
        if seed_execution_count < 4:
            for index, param in enumerate(params, start=1):
                db.add(
                    JobEjecucion(
                        ParametroId=param.ParametroId,
                        TipoCarga="mensual",
                        FechaEjecucion=datetime.now() - timedelta(minutes=index * 10),
                        Estado="Exitoso" if index % 3 else "Error",
                        Mensaje=f"Ejecucion de prueba #{index}",
                        ArchivoLanzado="Lanzador_encuestapercepcion.bat",
                        AreaId=param.AreaId,
                    )
                )

        if db.query(Schedule).count() == 0 and params:
            db.add(
                Schedule(
                    ParametroId=params[0].ParametroId,
                    Nombre="Schedule mensual de prueba",
                    Activo=True,
                    Periodico=True,
                    ServicioActivo=True,
                    MesAnterior=True,
                    DiaDelMes=1,
                    Hora="00:05",
                    AreaId=params[0].AreaId,
                    TipoCarga="mensual",
                    Launcher="EncuestatExcelxAreasMesAnioV34.py",
                    UsuarioProgramo="seed",
                )
            )

        db.commit()
        print("Datos de prueba insertados o actualizados correctamente.")


if __name__ == "__main__":
    main()
