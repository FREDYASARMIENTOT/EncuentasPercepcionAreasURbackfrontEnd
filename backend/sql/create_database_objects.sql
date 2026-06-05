USE [DWHEncuestasPercepcion]
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Catalogo')
    EXEC('CREATE SCHEMA Catalogo');
GO
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Orquestacion')
    EXEC('CREATE SCHEMA Orquestacion');
GO
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Historial')
    EXEC('CREATE SCHEMA Historial');
GO

IF OBJECT_ID('Catalogo.Areas', 'U') IS NULL
BEGIN
    CREATE TABLE Catalogo.Areas (
        AreaId INT IDENTITY(1,1) PRIMARY KEY,
        CodigoArea NVARCHAR(100) NOT NULL,
        NombreArea NVARCHAR(200) NOT NULL,
        Activo BIT NOT NULL DEFAULT 1
    );
END
GO

IF OBJECT_ID('Catalogo.SedesAreasServiciosEncuestasRespuestas', 'U') IS NULL
BEGIN
    CREATE TABLE Catalogo.SedesAreasServiciosEncuestasRespuestas (
        RegistroId INT IDENTITY(1,1) PRIMARY KEY,
        SedeId INT NOT NULL,
        SedeNombre NVARCHAR(200) NOT NULL,
        SedeEstadoDescripcion NVARCHAR(200) NULL,
        AreaId INT NULL,
        AreaNombre NVARCHAR(200) NOT NULL,
        AreaEstadoDescripcion NVARCHAR(200) NULL,
        ServicioId INT NULL,
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
GO

IF OBJECT_ID('Catalogo.View_SedesAreasServiciosEncuestasRespuestas', 'V') IS NULL
BEGIN
    CREATE VIEW Catalogo.View_SedesAreasServiciosEncuestasRespuestas
    AS
    SELECT * FROM Catalogo.SedesAreasServiciosEncuestasRespuestas;
END
GO

IF OBJECT_ID('Orquestacion.JobParametros', 'U') IS NULL
BEGIN
    CREATE TABLE Orquestacion.JobParametros (
        ParametroId INT IDENTITY(1,1) PRIMARY KEY,
        Mes INT NOT NULL,
        Anio INT NOT NULL,
        AreaId INT NULL,
        FechaProgramacion DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        UsuarioProgramo NVARCHAR(256) NULL,
        CONSTRAINT FK_JobParametros_Area FOREIGN KEY (AreaId) REFERENCES Catalogo.Areas(AreaId)
    );
END
GO

IF OBJECT_ID('Orquestacion.JobEjecuciones', 'U') IS NULL
BEGIN
    CREATE TABLE Orquestacion.JobEjecuciones (
        EjecucionId INT IDENTITY(1,1) PRIMARY KEY,
        ParametroId INT NOT NULL,
        TipoCarga NVARCHAR(50) NOT NULL,
        FechaEjecucion DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        Estado NVARCHAR(50) NOT NULL,
        Mensaje NVARCHAR(MAX) NULL,
        ArchivoLanzado NVARCHAR(500) NULL,
        AreaId INT NULL,
        CONSTRAINT FK_JobEjecuciones_Parametros FOREIGN KEY (ParametroId) REFERENCES Orquestacion.JobParametros(ParametroId),
        CONSTRAINT FK_JobEjecuciones_Area FOREIGN KEY (AreaId) REFERENCES Catalogo.Areas(AreaId)
    );
END
GO

IF OBJECT_ID('Orquestacion.Schedules', 'U') IS NULL
BEGIN
    CREATE TABLE Orquestacion.Schedules (
        ScheduleId INT IDENTITY(1,1) PRIMARY KEY,
        ParametroId INT NULL,
        Nombre NVARCHAR(256) NOT NULL,
        Activo BIT NOT NULL DEFAULT 1,
        Periodico BIT NOT NULL DEFAULT 1,
        ServicioActivo BIT NOT NULL DEFAULT 1,
        MesAnterior BIT NOT NULL DEFAULT 1,
        DiaDelMes INT NULL,
        FechaEspecifica DATETIME2 NULL,
        Hora NVARCHAR(10) NOT NULL DEFAULT '00:05',
        AreaId INT NULL,
        TipoCarga NVARCHAR(50) NOT NULL DEFAULT 'mensual',
        Launcher NVARCHAR(512) NOT NULL,
        UsuarioProgramo NVARCHAR(256) NULL,
        FechaCreacion DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_Schedules_JobParametros FOREIGN KEY (ParametroId) REFERENCES Orquestacion.JobParametros(ParametroId),
        CONSTRAINT FK_Schedules_Area FOREIGN KEY (AreaId) REFERENCES Catalogo.Areas(AreaId)
    );
END
GO

IF OBJECT_ID('Orquestacion.Schedules', 'U') IS NOT NULL
   AND COL_LENGTH('Orquestacion.Schedules', 'ParametroId') IS NULL
BEGIN
    ALTER TABLE Orquestacion.Schedules ADD ParametroId INT NULL;
END
GO

IF OBJECT_ID('Historial.CargasArea', 'U') IS NULL
BEGIN
    CREATE TABLE Historial.CargasArea (
        CargaId INT IDENTITY(1,1) PRIMARY KEY,
        FechaCarga DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        Mes INT NOT NULL,
        Anio INT NOT NULL,
        AreaId INT NULL,
        TipoCarga NVARCHAR(50) NOT NULL,
        RegistrosProcesados INT NULL,
        Estado NVARCHAR(50) NOT NULL,
        Observaciones NVARCHAR(MAX) NULL,
        CONSTRAINT FK_CargasArea_Area FOREIGN KEY (AreaId) REFERENCES Catalogo.Areas(AreaId)
    );
END
GO
