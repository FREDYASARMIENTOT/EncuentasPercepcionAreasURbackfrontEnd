USE [DWHEncuestasPercepcion]
GO

IF OBJECT_ID('Catalogo.SedesAreasServiciosEncuestasRespuestas', 'U') IS NULL
BEGIN
    CREATE TABLE Catalogo.SedesAreasServiciosEncuestasRespuestas (
        RegistroId INT IDENTITY(1,1) PRIMARY KEY,
        SedeId INT NOT NULL,
        SedeNombre NVARCHAR(200) NOT NULL,
        SedeEstadoDescripcion NVARCHAR(200) NULL,
        AreaId NVARCHAR(200) NULL,
        AreaNombre NVARCHAR(200) NOT NULL,
        AreaEstadoDescripcion NVARCHAR(200) NULL,
        ServicioId NVARCHAR(200) NULL,
        ServicioNombre NVARCHAR(200) NOT NULL,
        ServicioEstadoDescripcion NVARCHAR(200) NULL,
        EncuestasPorRelacion NVARCHAR(500) NULL,
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
