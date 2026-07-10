# ============================================================
# test_parquet_launcher.ps1
# Prueba basica del lanzador parquet
# ============================================================

Write-Host ""
Write-Host ("=" * 60)
Write-Host "  TEST LANZADOR PARQUET"
Write-Host ("=" * 60)

$ROOT = "F:\ETL_DITIC\EncuestasPercepcionAzure"
$LAUNCHER = "$ROOT\ARCHIVOS_NO_DESPLIEGUE\VersionesEncuestas\lanzador_parquet_v1.py"

# --------------------------------------------------
# Test 1: Listar areas y meses disponibles
# --------------------------------------------------
Write-Host ""
Write-Host "[1] Listando areas y meses disponibles..." -ForegroundColor Cyan
Write-Host "    Comando: python lanzador_parquet_v1.py --listar --anio 2026" -ForegroundColor DarkGray
python $LAUNCHER --listar --anio 2026
Write-Host "    Exit code: $LASTEXITCODE"

# --------------------------------------------------
# Test 2: Procesar un area especifica
# --------------------------------------------------
Write-Host ""
Write-Host "[2] Procesando area 'Centro' (mes=1, anio=2026)..." -ForegroundColor Cyan
Write-Host "    Comando: python lanzador_parquet_v1.py --anio 2026 --mes 1 --area Centro" -ForegroundColor DarkGray
python $LAUNCHER --anio 2026 --mes 1 --area "Centro"
Write-Host "    Exit code: $LASTEXITCODE"

Write-Host ""
Write-Host ("=" * 60)
Write-Host "  TESTS FINALIZADOS"
Write-Host ("=" * 60)