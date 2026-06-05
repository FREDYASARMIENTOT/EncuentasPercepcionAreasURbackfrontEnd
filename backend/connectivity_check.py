from pathlib import Path
import os
import sys
import tempfile
import traceback

from dotenv import load_dotenv
import requests
from sqlalchemy import text

from backend.database import get_connection_string, engine
from backend.scheduler import get_batch_path

BASE_DIR = Path(__file__).resolve().parents[0]
load_dotenv(BASE_DIR / '.env')


def report(message: str):
    print(f'[*] {message}')


def verify_env_vars():
    required = [
        'DB_DATA_SERVER', 'DB_DATA_NAME', 'DB_DATA_USER', 'DB_DATA_PASS',
        'DB_LOG_SERVER', 'DB_LOG_NAME', 'DB_LOG_USER', 'DB_LOG_PASS',
        'SMTP_USER', 'SMTP_PASS',
        'SP_CLIENT_ID', 'SP_CLIENT_SECRET', 'SP_TENANT_ID', 'SP_SITE_ID', 'SP_BASE_PATH',
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        report(f'⚠️ Faltan variables de entorno: {missing}')
        return False
    report('✅ Variables de entorno de servicio presentes.')
    return True


def verify_db_connection():
    report('Verificando la conexión SQL...')
    try:
        connection_string = get_connection_string()
        report(f'  Cadena generada: {connection_string[:80]}...')
        with engine.connect() as conn:
            result = conn.execute(text('SELECT 1'))
            value = result.scalar()
        if value == 1:
            report('✅ Conexión a SQL Server exitosa.')
            return True
    except Exception as exc:
        report(f'❌ Falló la conexión SQL: {exc}')
        traceback.print_exc()
    return False


def verify_batch_file():
    path = Path(get_batch_path())
    report(f'Verificando batch: {path}')
    if path.exists() and path.is_file():
        report('✅ Batch file encontrado.')
        return True
    report('❌ No se encontró el batch file.')
    return False


def verify_sharepoint_configuration():
    report('Verificando configuración de SharePoint...')
    site_id = os.getenv('SP_SITE_ID')
    base_path = os.getenv('SP_BASE_PATH')
    if not site_id or not base_path:
        report('❌ SP_SITE_ID o SP_BASE_PATH no están configurados.')
        return False

    parts = [p.strip() for p in site_id.split(',') if p.strip()]
    if len(parts) < 3 or 'sharepoint.com' not in parts[0].lower():
        report(f'❌ SP_SITE_ID inválido: {site_id}')
        return False

    if '\\' in base_path or ':' in base_path:
        report(f'❌ SP_BASE_PATH debe usar formato SharePoint y no rutas de Windows: {base_path}')
        return False

    if not base_path.strip():
        report('❌ SP_BASE_PATH no puede estar vacío.')
        return False

    report(f'✅ Configuración de SharePoint válida: {site_id} / {base_path}')
    return True


def verify_excel_export_permissions():
    report('Verificando permisos de generación Excel en el directorio de exportación...')
    export_dir = Path(os.getenv('DIRECTORIO_PRUEBAS_EXPORTACION', r'F:\ETL_DITIC\temp_exportacion_multiarea\PruebasExcel'))
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=export_dir, delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write('test')
            temp_path = Path(tmp_file.name)
        if temp_path.exists():
            report(f'✅ Permisos de escritura OK en {export_dir}')
            temp_path.unlink()
            return True
    except Exception as exc:
        report(f'❌ No se pudo escribir en el directorio de exportación Excel: {exc}')
    return False


def verify_backend_health():
    url = 'http://127.0.0.1:8000/api/health'
    report(f'Consultando endpoint de salud: {url}')
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            report('✅ Backend saludable.')
            report(f'  Respuesta: {response.json()}')
            return True
        report(f'❌ Backend respondió con estado {response.status_code}.')
    except Exception as exc:
        report(f'❌ No se pudo conectar al backend: {exc}')
    return False


def main():
    report('Iniciando pruebas de conectividad del portal Encuestas Percepción')
    env_ok = verify_env_vars()
    batch_ok = verify_batch_file()
    sharepoint_ok = verify_sharepoint_configuration()
    excel_ok = verify_excel_export_permissions()
    db_ok = verify_db_connection()
    backend_ok = verify_backend_health()

    report('Resumen final:')
    report(f"  Variables de entorno: {'OK' if env_ok else 'NO'}")
    report(f"  Batch file: {'OK' if batch_ok else 'NO'}")
    report(f"  Configuración SharePoint: {'OK' if sharepoint_ok else 'NO'}")
    report(f"  Permisos Excel local: {'OK' if excel_ok else 'NO'}")
    report(f"  Conexión SQL: {'OK' if db_ok else 'NO'}")
    report(f"  Health endpoint: {'OK' if backend_ok else 'NO'}")

    if all((env_ok, batch_ok, sharepoint_ok, excel_ok, db_ok, backend_ok)):
        report('✅ Todas las pruebas de conectividad pasaron.')
        return 0
    report('❌ Algunas pruebas fallaron. Revisa los mensajes anteriores.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
