$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
function Assert-Exit { if ($LASTEXITCODE -ne 0) { throw 'O comando anterior falhou. Corrija o erro antes de continuar.' } }
Get-Command ffmpeg, ffprobe, node, npm -ErrorAction Stop | Out-Null
py -3.12 -m venv .venv
Assert-Exit
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Assert-Exit
Push-Location frontend
try {
    npm.cmd ci
    Assert-Exit
    npm.cmd run build
    Assert-Exit
} finally { Pop-Location }
Write-Host 'Pronto. Execute .\scripts\start.ps1'
