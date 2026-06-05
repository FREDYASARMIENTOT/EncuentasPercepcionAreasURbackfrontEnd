from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class AreaModel(BaseModel):
    AreaId: int
    CodigoArea: str
    NombreArea: str
    Activo: bool

    model_config = ConfigDict(from_attributes=True)

class JobParamCreate(BaseModel):
    mes: int = Field(..., ge=0, le=12, description="0=mes anterior, 1-12 mes específico")
    anio: Optional[int] = None
    area_id: Optional[int] = None
    area: Optional[str] = None
    tipo_carga: str = Field("mensual", description="flujo mensual integral: mensual, acumulado y correo")
    usuario: Optional[str] = None

class JobParamUpdate(BaseModel):
    mes: Optional[int] = Field(None, ge=0, le=12, description="0=mes anterior, 1-12 mes especifico")
    anio: Optional[int] = None
    area_id: Optional[int] = None
    area: Optional[str] = None
    usuario: Optional[str] = None

class JobExecutionModel(BaseModel):
    EjecucionId: int
    ParametroId: int
    TipoCarga: str
    FechaEjecucion: datetime
    Estado: str
    Mensaje: Optional[str]
    ArchivoLanzado: Optional[str]
    AreaId: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class JobParametroModel(BaseModel):
    ParametroId: int
    Mes: int
    Anio: int
    AreaId: Optional[int]
    FechaProgramacion: datetime
    UsuarioProgramo: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class ScheduleCreate(BaseModel):
    parametro_id: Optional[int] = None
    nombre: str
    activo: bool = True
    periodico: bool = True
    servicio_activo: bool = True
    mes_anterior: bool = True
    dia_del_mes: Optional[int] = None
    fecha_especifica: Optional[datetime] = None
    hora: str = "00:05"
    area_id: Optional[int] = None
    area: Optional[str] = None
    tipo_carga: str = "mensual"
    launcher: str
    usuario: Optional[str] = None

class ScheduleUpdate(BaseModel):
    parametro_id: Optional[int] = None
    nombre: Optional[str] = None
    activo: Optional[bool] = None
    periodico: Optional[bool] = None
    servicio_activo: Optional[bool] = None
    mes_anterior: Optional[bool] = None
    dia_del_mes: Optional[int] = None
    fecha_especifica: Optional[datetime] = None
    hora: Optional[str] = None
    area_id: Optional[int] = None
    area: Optional[str] = None
    tipo_carga: Optional[str] = None
    launcher: Optional[str] = None
    usuario: Optional[str] = None

class ScheduleModel(BaseModel):
    ScheduleId: int
    ParametroId: Optional[int]
    Nombre: str
    Activo: bool
    Periodico: bool
    ServicioActivo: bool
    MesAnterior: bool
    DiaDelMes: Optional[int]
    FechaEspecifica: Optional[datetime]
    Hora: str
    AreaId: Optional[int]
    TipoCarga: str
    Launcher: str
    UsuarioProgramo: Optional[str]
    FechaCreacion: datetime

    model_config = ConfigDict(from_attributes=True)

class HistoryModel(BaseModel):
    CargaId: int
    FechaCarga: datetime
    Mes: int
    Anio: int
    AreaId: Optional[int]
    TipoCarga: str
    RegistrosProcesados: Optional[int]
    Estado: str
    Observaciones: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class JobStatusModel(BaseModel):
    task_name: str
    exists: bool
    next_run: Optional[str]
    last_run_time: Optional[str]
    status: Optional[str]
    path: Optional[str]
