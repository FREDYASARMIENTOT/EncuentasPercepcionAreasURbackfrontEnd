# ============================================================
# ejecutar_pruebas_parquet.ps1
# Prueba completa del lanzador parquet + validacion de Excels
# ============================================================

Write-Host ""
Write-Host ("=" * 70)
Write-Host "  PRUEBAS COMPLETAS - LANZADOR PARQUET"
Write-Host ("=" * 70)
Write-Host ""

$ROOT = "F:\ETL_DITIC\EncuestasPercepcionAzure"
$LAUNCHER = "$ROOT\ARCHIVOS_NO_DESPLIEGUE\VersionesEncuestas\lanzador_parquet_v1.py"
$VALIDATOR = "$ROOT\verificar_excels_parquet.py"
$OUTPUT_DIR = "F:\ETL_DITIC\temp_exportacion_multiarea"

# --------------------------------------------------
# PASO 1: Listar areas disponibles
# --------------------------------------------------
Write-Host "[PASO 1] Listar areas y meses disponibles..." -ForegroundColor Cyan
Write-Host ""
python $LAUNCHER --listar --anio 2026

Write-Host ""
Write-Host "Presiona ENTER para continuar..." -ForegroundColor Yellow
Read-Host

# --------------------------------------------------
# PASO 2: Procesar un area REAL (CRAI - mes 5)
# --------------------------------------------------
Write-Host ""
Write-Host "[PASO 2] Procesar area CRAI, mes=5, anio=2026..." -ForegroundColor Cyan
Write-Host "    (CRAI es un area que SI existe en areaNombre)" -ForegroundColor DarkYellow
Write-Host ""
python $LAUNCHER --anio 2026 --mes 5 --area "CRAI"
Write-Host ""
Write-Host "    Exit code: $LASTEXITCODE"

Write-Host ""
Write-Host "Presiona ENTER para continuar..." -ForegroundColor Yellow
Read-Host

# --------------------------------------------------
# PASO 3: Ejecutar validacion de Excels generados
# --------------------------------------------------
Write-Host ""
Write-Host "[PASO 3] Validar Excels generados..." -ForegroundColor Cyan
Write-Host ""
python $VALIDATOR --ruta $OUTPUT_DIR --parquet "$ROOT\VistaEncuestaPercepcion2026.parquet" --anio 2026 --mes 5

Write-Host ""
Write-Host "Presiona ENTER para continuar..." -ForegroundColor Yellow
Read-Host

# --------------------------------------------------
# PASO 4: Validar especificamente el CRAI
# --------------------------------------------------
Write-Host ""
Write-Host "[PASO 4] Validar Excel del area CRAI..." -ForegroundColor Cyan
Write-Host ""
python $VALIDATOR --ruta $OUTPUT_DIR --parquet "$ROOT\VistaEncuestaPercepcion2026.parquet" --area "CRAI" --anio 2026 --mes 5

Write-Host ""
Write-Host ("=" * 70)
Write-Host "  PRUEBAS COMPLETADAS"
Write-Host ("=" * 70)
Write-Host ""
Write-Host "Archivos generados en: $OUTPUT_DIR\CRAI\" -ForegroundColor Green
Write-Host ""