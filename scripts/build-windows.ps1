param([string]$Version = '0.4.7')
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if ($env:OS -ne 'Windows_NT') { throw 'O instalador Windows deve ser compilado no Windows (ou GitHub Actions).' }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Versão deve ter formato 0.4.7.' }
function Assert-Exit { if ($LASTEXITCODE -ne 0) { throw 'O comando anterior falhou; build interrompido.' } }
$compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (!(Test-Path $compiler)) { throw 'Inno Setup 6 não encontrado. Instale-o apenas na máquina de build.' }
py -3.12 -m venv .build-venv
Assert-Exit
$python = (Resolve-Path '.build-venv\Scripts\python.exe').Path
& $python -m pip install -r requirements-packaging.txt
Assert-Exit
Push-Location frontend
try {
    npm.cmd ci
    Assert-Exit
    npm.cmd run build
    Assert-Exit
    npm.cmd run lint
    Assert-Exit
    npm.cmd test
    Assert-Exit
} finally { Pop-Location }
& $python packaging\prepare_vendor.py
Assert-Exit
& $python -m PyInstaller --noconfirm --clean packaging\EsteiraVideos.spec
Assert-Exit
# Validate the real frozen application before creating any installer.
& .\dist\EsteiraVideos\EsteiraVideos.exe --smoke-test
Assert-Exit
& $compiler "/DAppVersion=$Version" packaging\installer.iss
Assert-Exit
$installer = (Resolve-Path 'dist\installer\EsteiraVideos-Setup.exe').Path
# Verify install and uninstall in a path containing spaces and Portuguese characters.
$testInstall = Join-Path $env:TEMP ('esteira-videos instalação ' + [guid]::NewGuid().ToString('N'))
$process = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$testInstall`"") -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Instalador falhou: $($process.ExitCode)" }
try {
    & (Join-Path $testInstall 'EsteiraVideos.exe') --smoke-test
    Assert-Exit
} finally {
    $uninstaller = Join-Path $testInstall 'unins000.exe'
    if (Test-Path $uninstaller) {
        $process = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "Desinstalador falhou: $($process.ExitCode)" }
    }
}
Copy-Item packaging\INSTALL-NOTES.txt dist\installer\LEIA-ME.txt
$hash = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText((Join-Path (Split-Path $installer) 'SHA256SUMS.txt'), "$hash  EsteiraVideos-Setup.exe`n")
Write-Host 'Instalador compilado, instalado, exercitado e desinstalado com sucesso.'
Write-Host $installer
