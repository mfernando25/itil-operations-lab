$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[1/3] Creando entorno virtual..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3 -m venv .venv
}

Write-Host "[2/3] Instalando dependencias..."
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "[3/3] Instalación terminada. Ejecuta .\scripts\start_lab.ps1"
