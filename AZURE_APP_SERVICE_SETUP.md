# Azure App Service Deployment Setup

## Visión general
Este repositorio contiene dos carpetas de aplicación:
- `backend` → API Python/FastAPI
- `frontend` → aplicación React/Vite
- `ARCHIVOS_NO_DESPLIEGUE` → archivos auxiliares y documentación no desplegable

Cada carpeta debe pesar menos de 100 MB en el repositorio final. Para lograrlo, no se debe versionar `frontend/node_modules`, `frontend/dist` ni `frontend/ARCHIVOS_NO_DESPLIEGUE`.

## App Service Plan
- Plan: `ASP-IAUR`
- SKU: `B1`
- Dos App Services separados:
  - `AS-AppBackendEncuestasUR`
  - `AS-AppFrontEndEncuestasUR`

## Configuración recomendada para `AS-AppBackendEncuestasUR`
- Runtime stack: `Python 3.11`
- Platform: Linux
- Project folder / app location: `backend`
- Startup command:
  ```bash
  gunicorn --bind=0.0.0.0 --workers 4 --worker-class uvicorn.workers.UvicornWorker app:app
  ```
- App settings:
  - `SCM_DO_BUILD_DURING_DEPLOYMENT = true`
  - `PYTHONPATH = /home/site/wwwroot/backend`
  - `PORT = 8000`
- Deployment source: GitHub repo, folder `backend`

## Configuración recomendada para `AS-AppFrontEndEncuestasUR`
- Runtime stack: `Node 20 LTS`
- Platform: Linux
- Project folder / app location: `frontend`
- Startup command:
  ```bash
  npm start
  ```
- App settings:
  - `SCM_DO_BUILD_DURING_DEPLOYMENT = true`
  - `WEBSITE_NODE_DEFAULT_VERSION = 20.0.0`
- Deployment source: GitHub repo, folder `frontend`

## Recomendaciones de contenido para cada carpeta

### `backend`
- Mantener solo código Python, `requirements.txt`, `app.py`, `sql/`, `tests/`, y scripts que se ejecuten en producción.
- No subir entornos virtuales ni `__pycache__`.
- `requirements.txt` incluye `gunicorn`, `uvicorn`, `fastapi`, y todas las dependencias necesarias.
- El comando local para probar:
  ```powershell
  conda activate EncuestasBackendAzure
  cd backend
  pytest tests
  ```

### `frontend`
- Mantener solo código React, `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json`, `public/`, `src/`, y el resultado de `npm build` solo localmente.
- No subir `node_modules` ni archivos de prueba provisionales.
- `package.json` ahora define:
  - `build`: `vite build`
  - `start`: `npx serve -s dist`
  - `test`: `vitest`
- El comando local para probar:
  ```powershell
  conda activate EncuestasFrontendAzure
  cd frontend
  npm ci
  npm test
  npm run build
  ```

## Validación local
- `validar_funcionamiento.ps1` sirve `frontend/dist` y comprueba HTTP 200.
- Ejecutar:
  ```powershell
  .\validar_funcionamiento.ps1
  ```

## Notas de despliegue
- Si usas GitHub Actions o Deployment Center, configura el path del proyecto a `backend` o `frontend` según el App Service.
- Si prefieres desplegar con ZIP deploy, crea ZIP separado de cada carpeta y súbelo al App Service correspondiente.
