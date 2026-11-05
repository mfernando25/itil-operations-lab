$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "No se encontró .venv. Ejecuta primero .\scripts\setup_windows.ps1"
}
& $python app.py
