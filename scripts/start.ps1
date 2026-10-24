param([switch]$Lan, [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$arguments = @('-m', 'backend.run', '--port', "$Port")
if ($Lan) { $arguments += '--lan' }
& .\.venv\Scripts\python.exe @arguments
