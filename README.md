# Encuestas Percepción Azure

Repositorio: https://github.com/FREDYASARMIENTOT/EncuentasPercepcionAreasURbackfrontEnd

## Estructura del proyecto

- `backend/`: aplicación Python FastAPI que expone la API y orquesta los jobs.
- `frontend/`: aplicación React + Vite que consume la API y muestra el portal.
- `ARCHIVOS_NO_DESPLIEGUE/`: contenido extra no desplegable que se mantiene fuera de la aplicación.
- `.vscode/`: configuración de tareas y lanzamiento para abrir el portal local.

## Objetivo

Este repositorio está configurado para:
- iniciar el backend en `http://127.0.0.1:8000`
- iniciar el frontend en `http://127.0.0.1:5173`
- ejecutar automáticamente dos terminales con sus entornos `conda`
- abrir el portal en el navegador local
- ejecutar una prueba de carga específica de Backend para CRAI 2026-05

## Backend

### Qué hace

El backend es un servicio FastAPI que:
- expone endpoints REST para orquestar jobs de encuesta,
- gestiona datos de áreas, jobs, schedules e historial,
- inicia procesos batch con `orquestador` para cargar datos de 2026,
- permite consultar estado de ejecución y log de jobs.

### Arranque local

1. Activar Conda: `conda activate EncuestasBackendAzure`
2. Ir a `backend/`
3. Ejecutar: `uvicorn app:app --reload --host 127.0.0.1 --port 8000`

### Prueba de carga

Se incluye un test de backend para la carga `CRAI 2026-05` en `backend/tests/test_orquestador.py`.

### Verificación de conexiones

Antes de lanzar procesos de orquestación se recomienda verificar lo siguiente:
- `pytest backend/tests/test_connectivity.py -q`
- El backend ahora usa preferentemente `DB_DATA_SERVER`, `DB_DATA_NAME`, `DB_DATA_USER` y `DB_DATA_PASS` si están definidos, y luego cae a `SQL_SERVER` / `SQL_DATABASE`.
- El lanzador batch usa el intérprete de Python del entorno `EncuestasBackendAzure` para garantizar que las dependencias del proyecto estén disponibles.
- El acceso al blob de Azure se valida con las variables `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_CONTAINER_NAME` y `AZURE_SAS_TOKEN`.

## Frontend

### Qué hace

El frontend es un portal React que:
- muestra el estado de los jobs,
- permite lanzar procesos manuales y automáticos,
- consume el backend en `/api`,
- expone la interfaz de usuario en `http://127.0.0.1:5173`.

### Arranque local

1. Activar Conda: `conda activate EncuestasFrontendAzure`
2. Ir a `frontend/`
3. Ejecutar: `npm install` (si no está hecho)
4. Ejecutar: `npm run dev`

## VS Code

Al abrir la carpeta `F:\ETL_DITIC\EncuestasPercepciónAzure` en VS Code:
- se ejecutarán automáticamente dos tareas en terminales separadas:
  - `Start Backend API` -> arranca el backend en el entorno `EncuestasBackendAzure`
  - `Start Frontend Portal` -> arranca el frontend en el entorno `EncuestasFrontendAzure`
- también hay una configuración de lanzamiento para abrir el portal en Chrome en `http://127.0.0.1:5173`.

## Flujo de despliegue en producción

1. El frontend se construye con Vite (`npm run build`) y sirve los archivos estáticos.
2. El backend se despliega como servicio Python en Azure App Service usando FastAPI/Uvicorn.
3. En producción el frontend y el backend pueden desplegarse juntos o separadamente, pero la estructura del repositorio mantiene ambos proyectos en la raíz.
4. Si se usa Azure App Service, el backend debe incluir:
   - `requirements.txt`
   - el archivo `backend/app.py` como entrada
   - la configuración de inicio del App Service para ejecutar `uvicorn app:app --host 0.0.0.0 --port 8000`
5. El frontend se puede servir desde un App Service estático o como recursos estáticos integrados en el backend.

## Notas finales

- El código ya está enlazado al repositorio GitHub correcto.
- El antiguo remoto `EncuentasPercepcionAreasUR2026` ya no se usa como `origin`.
- Los artefactos generados (`frontend/dist`, `frontend/node_modules`, etc.) no deben subirse al repositorio.
