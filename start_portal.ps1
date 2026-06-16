# Start backend and frontend in separate PowerShell windows with Conda envs
Param()

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Build paths
$backendPath = Join-Path $root 'backend'
$frontendPath = Join-Path $root 'frontend'

function Check-CommandAvailable {
	param($cmd)
	return (Get-Command $cmd -ErrorAction SilentlyContinue) -ne $null
}

Write-Output "Checking Conda availability..."
if (-not (Check-CommandAvailable 'conda')) {
	Write-Warning "Conda not found in PATH. Ensure Conda is installed and available in VS Code integrated terminals."
	Write-Output "You can still run tasks in VS Code; they use 'conda run -n <env> -- ...'."
}

Write-Output "Checking backend tool availability (uvicorn via conda run)..."
$uvicornOK = $false
try {
	& conda run -n EncuestasBackendAzure -- uvicorn --version 2>$null
	$uvicornOK = $true
} catch { $uvicornOK = $false }
if (-not $uvicornOK) { Write-Warning "uvicorn not available in environment 'EncuestasBackendAzure' (or conda run failed)." }

Write-Output "Checking frontend tool availability (npm via conda run)..."
$npmOK = $false
try {
	& conda run -n EncuestasFrontendAzure -- npm --version 2>$null
	$npmOK = $true
} catch { $npmOK = $false }
if (-not $npmOK) { Write-Warning "npm not available in environment 'EncuestasFrontendAzure' (or conda run failed)." }

Write-Output "Configuration summary:"
Write-Output " - Backend path: $backendPath"
Write-Output " - Frontend path: $frontendPath"

Write-Output "The project is configured to start the backend and frontend in VS Code integrated terminals automatically via tasks (Start Backend API, Start Frontend Portal) when the workspace opens."
Write-Output "If you prefer to start them now from this terminal, the script can run them here using 'conda run -n'."

if ($uvicornOK -and $npmOK) {
	Write-Output "Starting backend and frontend in this terminal session (note: frontend will block this terminal)."
	Write-Output "Backend will be started in background (Start-Job) and frontend in foreground."
	Start-Job -ScriptBlock { conda run -n EncuestasBackendAzure -- uvicorn app:app --reload --host 127.0.0.1 --port 8000 } | Out-Null
	Write-Output "Backend job started. Now starting frontend (this will run in this terminal)."
	Push-Location $frontendPath
	& conda run -n EncuestasFrontendAzure -- npm run dev
	Pop-Location
} else {
	Write-Output "Skipping automatic start because prerequisites are missing."
	Write-Output "Open the project in VS Code (or reload window) to trigger the integrated tasks, or run these commands manually:" 
	Write-Output "  cd $backendPath && conda run -n EncuestasBackendAzure -- uvicorn app:app --reload --host 127.0.0.1 --port 8000"
	Write-Output "  cd $frontendPath && conda run -n EncuestasFrontendAzure -- npm run dev"
}
