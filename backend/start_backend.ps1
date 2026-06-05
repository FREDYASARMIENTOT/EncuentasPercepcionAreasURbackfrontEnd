param([switch]$Debug=false)

Write-Host "Starting backend (development)" -ForegroundColor Cyan
if ($Debug) { Write-Host "Debug mode" -ForegroundColor Yellow }

# Activate conda env if exists
if (Get-Command conda -ErrorAction SilentlyContinue) {
    conda activate EncuestasBackendAzure
}

Set-Location $PSScriptRoot

# Install dependencies if missing (safe)
if (Test-Path requirements.txt) {
    pip install -r requirements.txt
}

# Run uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000
