USE [DWHEncuestasPercepcion]
GO

-- Insertar datos en la tabla Catalogo.Areas
INSERT INTO [Catalogo].[Areas] (CodigoArea, NombreArea, Activo)
VALUES
('A001', 'Área de Recursos Humanos', 1),
('A002', 'Área de Finanzas', 1),
('A003', 'Área de Tecnología', 1),
('A004', 'Área de Marketing', 1);

-- Insertar datos en la tabla Orquestacion.JobParametros
INSERT INTO [Orquestacion].[JobParametros] (Mes, Anio, AreaId, FechaProgramacion, UsuarioProgramo)
VALUES
(4, 2026, 1, SYSDATETIME(), 'admin'),
(4, 2026, 2, SYSDATETIME(), 'admin'),
(4, 2026, 3, SYSDATETIME(), 'admin'),
(4, 2026, 4, SYSDATETIME(), 'admin');

-- Insertar datos en la tabla Historial.CargasArea
INSERT INTO [Historial].[CargasArea] (FechaCarga, Mes, Anio, AreaId, TipoCarga, RegistrosProcesados, Estado, Observaciones)
VALUES
(SYSDATETIME(), 4, 2026, 1, 'Automático', 100, 'Exitoso', 'Carga completada sin errores'),
(SYSDATETIME(), 4, 2026, 2, 'Manual', 50, 'Exitoso', 'Carga completada con observaciones'),
(SYSDATETIME(), 4, 2026, 3, 'Automático', 200, 'Error', 'Error en la validación de datos'),
(SYSDATETIME(), 4, 2026, 4, 'Manual', 150, 'Exitoso', 'Carga completada sin errores');

-- Insertar datos en la tabla Orquestacion.JobEjecuciones
INSERT INTO [Orquestacion].[JobEjecuciones] (ParametroId, TipoCarga, FechaEjecucion, Estado, Mensaje, ArchivoLanzado, AreaId)
VALUES
(1, 'Automático', SYSDATETIME(), 'Exitoso', 'Ejecución completada', 'orquestador_batch_1.bat', 1),
(2, 'Manual', SYSDATETIME(), 'Exitoso', 'Ejecución completada', 'orquestador_batch_2.bat', 2),
(3, 'Automático', SYSDATETIME(), 'Error', 'Error en la ejecución del batch', 'orquestador_batch_3.bat', 3),
(4, 'Manual', SYSDATETIME(), 'Exitoso', 'Ejecución completada', 'orquestador_batch_4.bat', 4);