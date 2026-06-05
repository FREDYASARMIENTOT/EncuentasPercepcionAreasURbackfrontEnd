from sqlalchemy import Column, Integer, NVARCHAR, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from .database import Base

class Area(Base):
    __tablename__ = "Areas"
    __table_args__ = {"schema": "Catalogo"}

    AreaId = Column(Integer, primary_key=True, autoincrement=True)
    CodigoArea = Column(NVARCHAR(100), nullable=False)
    NombreArea = Column(NVARCHAR(200), nullable=False)
    Activo = Column(Boolean, nullable=False, default=True)

    ejecuciones = relationship("JobEjecucion", back_populates="area")
    cargas = relationship("CargaArea", back_populates="area")

class SedesAreasServiciosEncuestasRespuestas(Base):
    __tablename__ = "SedesAreasServiciosEncuestasRespuestas"
    __table_args__ = (
        UniqueConstraint("SedeId", "AreaId", "ServicioId", name="UX_SedesAreasServiciosEncuestasRespuestas"),
        {"schema": "Catalogo"},
    )

    RegistroId = Column(Integer, primary_key=True, autoincrement=True)
    SedeId = Column(Integer, nullable=False)
    SedeNombre = Column(NVARCHAR(200), nullable=False)
    SedeEstadoDescripcion = Column(NVARCHAR(200), nullable=True)
    AreaId = Column(NVARCHAR(200), nullable=True)
    AreaNombre = Column(NVARCHAR(200), nullable=False)
    AreaEstadoDescripcion = Column(NVARCHAR(200), nullable=True)
    ServicioId = Column(NVARCHAR(200), nullable=True)
    ServicioNombre = Column(NVARCHAR(200), nullable=False)
    ServicioEstadoDescripcion = Column(NVARCHAR(200), nullable=True)
    EncuestasPorRelacion = Column(NVARCHAR(500), nullable=True)
    CantidadEncuestas = Column(Integer, nullable=True)
    TotalRespuestasHistoricas = Column(Integer, nullable=True)
    FechaInsercion = Column(DateTime(timezone=True), nullable=False, server_default=func.sysdatetime())
    FechaModificacion = Column(DateTime(timezone=True), nullable=False, server_default=func.sysdatetime())
    EstadoRegistro = Column(NVARCHAR(50), nullable=False, default="Activo")

class JobParametro(Base):
    __tablename__ = "JobParametros"
    __table_args__ = {"schema": "Orquestacion"}

    ParametroId = Column(Integer, primary_key=True, autoincrement=True)
    Mes = Column(Integer, nullable=False)
    Anio = Column(Integer, nullable=False)
    AreaId = Column(Integer, ForeignKey("Catalogo.Areas.AreaId"), nullable=True)
    FechaProgramacion = Column(DateTime(timezone=True), nullable=False, server_default=func.sysdatetime())
    UsuarioProgramo = Column(NVARCHAR(256), nullable=True)

    ejecuciones = relationship("JobEjecucion", back_populates="parametro")

class Schedule(Base):
    __tablename__ = "Schedules"
    __table_args__ = {"schema": "Orquestacion"}

    ScheduleId = Column(Integer, primary_key=True, autoincrement=True)
    ParametroId = Column(Integer, ForeignKey("Orquestacion.JobParametros.ParametroId"), nullable=True)
    Nombre = Column(NVARCHAR(256), nullable=False)
    Activo = Column(Boolean, nullable=False, default=True)
    Periodico = Column(Boolean, nullable=False, default=True)
    ServicioActivo = Column(Boolean, nullable=False, default=True)
    MesAnterior = Column(Boolean, nullable=False, default=True)
    DiaDelMes = Column(Integer, nullable=True)
    FechaEspecifica = Column(DateTime(timezone=True), nullable=True)
    Hora = Column(NVARCHAR(10), nullable=False, default="00:05")
    AreaId = Column(Integer, ForeignKey("Catalogo.Areas.AreaId"), nullable=True)
    TipoCarga = Column(NVARCHAR(50), nullable=False, default="mensual")
    Launcher = Column(NVARCHAR(512), nullable=False)
    UsuarioProgramo = Column(NVARCHAR(256), nullable=True)
    FechaCreacion = Column(DateTime(timezone=True), nullable=False, server_default=func.sysdatetime())

    parametro = relationship("JobParametro")

class JobEjecucion(Base):
    __tablename__ = "JobEjecuciones"
    __table_args__ = {"schema": "Orquestacion"}

    EjecucionId = Column(Integer, primary_key=True, autoincrement=True)
    ParametroId = Column(Integer, ForeignKey("Orquestacion.JobParametros.ParametroId"), nullable=False)
    TipoCarga = Column(NVARCHAR(50), nullable=False)
    FechaEjecucion = Column(DateTime(timezone=True), nullable=False, server_default=func.sysdatetime())
    Estado = Column(NVARCHAR(50), nullable=False)
    Mensaje = Column(NVARCHAR(None), nullable=True)
    ArchivoLanzado = Column(NVARCHAR(500), nullable=True)
    AreaId = Column(Integer, ForeignKey("Catalogo.Areas.AreaId"), nullable=True)

    parametro = relationship("JobParametro", back_populates="ejecuciones")
    area = relationship("Area", back_populates="ejecuciones")

class CargaArea(Base):
    __tablename__ = "CargasArea"
    __table_args__ = {"schema": "Historial"}

    CargaId = Column(Integer, primary_key=True, autoincrement=True)
    FechaCarga = Column(DateTime(timezone=True), nullable=False, server_default=func.sysdatetime())
    Mes = Column(Integer, nullable=False)
    Anio = Column(Integer, nullable=False)
    AreaId = Column(Integer, ForeignKey("Catalogo.Areas.AreaId"), nullable=True)
    TipoCarga = Column(NVARCHAR(50), nullable=False)
    RegistrosProcesados = Column(Integer, nullable=True)
    Estado = Column(NVARCHAR(50), nullable=False)
    Observaciones = Column(NVARCHAR(None), nullable=True)

    area = relationship("Area", back_populates="cargas")
