param(
    [int]$Port = 4173,
    [int]$TimeoutSec = 10
)

Write-Host "Iniciando validación de funcionamiento del portal (serving frontend/dist)" -ForegroundColor Cyan

$dist = Join-Path (Get-Location).Path 'frontend\dist'
if (-not (Test-Path $dist)) { Write-Host "ERROR: carpeta dist no encontrada: $dist" -ForegroundColor Red; exit 1 }

# Start a temporary Python HTTP server
$python = "python"
$proc = Start-Process -FilePath $python -ArgumentList "-m http.server $Port --directory `"$dist`"" -NoNewWindow -PassThru
Start-Sleep -Seconds 1

try {
    $url = "http://localhost:$Port/"
    Write-Host "Comprobando $url ..."
    $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
    if ($resp.StatusCode -eq 200 -and $resp.Content -match '<title') {
        Write-Host "OK: Portal cargado (status 200)." -ForegroundColor Green
        Write-Host "Resumen: `n  Size: $($resp.RawContentLength) bytes" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "WARN: respuesta inesperada (codigo $($resp.StatusCode))." -ForegroundColor Yellow
        exit 2
    }
} catch {
    Write-Host "ERROR: no se pudo acceder al portal: $($_.Exception.Message)" -ForegroundColor Red
    exit 3
} finally {
    if ($proc -and -not $proc.HasExited) { $proc | Stop-Process -Force }
}
