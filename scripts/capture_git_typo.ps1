# Captura un error de Git sin modificar archivos ni crear commits.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$evidenceDir = Join-Path $root "evidence"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
$log = Join-Path $evidenceDir "git_typo.txt"
"ITIL Operations Lab - evidencia de error Git" | Set-Content -Path $log -Encoding UTF8
"Fecha: $(Get-Date -Format o)" | Add-Content -Path $log -Encoding UTF8
"Directorio: $root" | Add-Content -Path $log -Encoding UTF8
"Comando ejecutado: git comite" | Add-Content -Path $log -Encoding UTF8
"--- Salida de Git ---" | Add-Content -Path $log -Encoding UTF8
Push-Location $root
try {
    $output = & git comite 2>&1
    $exitCode = $LASTEXITCODE
    $output | Tee-Object -FilePath $log -Append
    "Código de salida: $exitCode" | Add-Content -Path $log -Encoding UTF8
} finally { Pop-Location }
Write-Host "Evidencia guardada en: $log"
Write-Host "Este ejercicio no crea commits ni modifica archivos del proyecto."
