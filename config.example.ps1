# Exemplo opcional: copie para um arquivo local fora do repositório e execute antes de iniciar.
# Não contém segredos. Nenhuma API externa é necessária.
$env:ESTEIRA_DATA = Join-Path $env:LOCALAPPDATA 'esteira-videos'
$env:ESTEIRA_MAX_UPLOAD_GB = '20'
# Se FFmpeg não estiver no PATH, use caminhos absolutos locais:
# $env:ESTEIRA_FFMPEG = 'C:\Ferramentas\ffmpeg\bin\ffmpeg.exe'
# $env:ESTEIRA_FFPROBE = 'C:\Ferramentas\ffmpeg\bin\ffprobe.exe'
