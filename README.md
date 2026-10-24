# EsteiraVídeos

Editor local de gameplays e lives para Shorts. Interface em português, desktop e celular; FastAPI, React/TypeScript, SQLite e FFmpeg. Nenhuma chave de API, telemetria ou envio externo de vídeos. O projeto entrega edição manual real, não usa vídeos demonstrativos na interface.

## Executar no Windows

Pré-requisitos instalados pelo usuário: **Python 3.12**, **Node.js 22 ou 24**, **FFmpeg e FFprobe** no PATH. Use uma distribuição do FFmpeg indicada em https://ffmpeg.org/download.html com `libx264`, AAC e `ass/subtitles` (libass). Nenhum script instala ferramentas globalmente, altera firewall ou baixa modelos.

No PowerShell, na raiz do checkout:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Abra o endereço impresso no terminal (porta 8000 por padrão). Caso a política local impeça scripts, execute os comandos do `setup.ps1` manualmente; não é necessário alterar permanentemente a política da máquina. O frontend compilado é servido pela API na mesma origem.

1. **Projetos → Novo projeto**; selecione ou arraste um MP4, MKV ou MOV.
2. Aguarde o envio e a validação FFprobe. Cada projeto recebe uma gravação original.
3. No editor, marque início/fim pelo player, pelos campos `HH:MM:SS.mmm`, pelas alças ou pelos sliders. Salve o corte. Use **Novo corte** para criar outros.
4. Em **Layout**, escolha gameplay ou webcam + gameplay. Defina as regiões normalizadas de cada parte: X/Y são o canto superior esquerdo, largura/altura são frações do original. Exemplo: webcam no canto superior esquerdo ocupando 25% × 30%: X=0, Y=0, largura=0,25, altura=0,30. X+largura e Y+altura não podem ultrapassar 1. O enquadramento faz crop central para preencher, sem distorcer.
5. Em **Legendas**, adicione blocos ou importe SRT. Tempos manuais são relativos ao início do Short. A importação de SRT da gravação recorta e converte os tempos automaticamente. Ajuste tamanho, contorno e margem inferior. Salve.
6. Gere uma **prévia renderizada de até 5 segundos** para conferir. A composição de vídeo usa a mesma geometria normalizada; a prévia instantânea é reduzida e o texto do canvas pode diferir na quebra de linhas da renderização libass. Confira a renderizada antes da exportação final.
7. Marque os cortes e **Exporte**. A fila processa um vídeo por vez, em CPU. Os ajustes são copiados no momento do envio; editar depois não altera tarefas existentes.
8. Em **Resultados**, reproduza, edite título/descrição e aprove. Aprovação significa apenas revisão local. Baixe MP4, SRT ou ZIP selecionado; o original nunca entra no ZIP.

Se o player não conseguir reproduzir um codec, use **Gerar cópia compatível**, aguarde sua tarefa na fila e clique em **Usar cópia**. Ela é H.264/AAC, começa no tempo zero e mantém a duração; os cortes continuam referenciando o original. Essa conversão pode consumir tempo e espaço equivalentes a um novo vídeo.

## Celular na mesma rede Wi-Fi

```powershell
.\scripts\start.ps1 -Lan
# Porta alternativa:
.\scripts\start.ps1 -Lan -Port 8001
```

O servidor imprime o endereço IPv4 e um código de pareamento válido por 10 minutos. Abra o endereço no celular e digite o código na tela (não em uma URL). Se a descoberta mostrar um adaptador incorreto, consulte `ipconfig` e use o IPv4 do Wi-Fi. Se necessário, autorize manualmente Python no Firewall do Windows **somente para redes privadas**. Não abra portas no roteador nem use túnel público.

O modo LAN exige pareamento também no navegador do PC. O cookie é HttpOnly/SameSite Strict, dura até 24 horas e as sessões são invalidadas no reinício. Há limite de 5 tentativas por minuto por IP, validação de origem e cabeçalho obrigatório contra CSRF nas alterações. O HTTP local não cifra os vídeos: use apenas uma rede privada confiável. A aplicação não configura HTTPS. Reinicie para gerar outro código após expiração. O terminal exibe o código; logs de acesso HTTP ficam desativados.

O computador deve permanecer ligado. Ao perder conexão, a interface informa o problema e consulta novamente a fila quando reconecta. Exportações usam um identificador por requisição para impedir duplicação no backend; a interface não reenvia exportações automaticamente.

## Encerrar e retomar

Use **Ctrl+C no terminal de inicialização**. O supervisor encerra o servidor e sinaliza o trabalhador, que encerra o grupo do FFmpeg (no Windows, `taskkill /T`). Aguarda a saída e usa término forçado se necessário. Não feche o terminal à força durante uma renderização. Uma queda abrupta não é tratada como sucesso: ao reiniciar o trabalhador, tarefas em processamento ficam como falhas e podem ser tentadas novamente. Um bloqueio de arquivo do sistema impede dois trabalhadores simultâneos para a mesma pasta de dados. Uma nova tentativa cria uma tarefa e um nome de saída novos.

É possível executar separadamente `python -m backend.worker` e `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000`, mas nesse modo encerre os dois terminais. Para LAN, prefira o supervisor, que configura pareamento e imprime os endereços.

## Armazenamento e configuração

Dados ficam **fora do código**, por padrão em `%LOCALAPPDATA%\esteira-videos` no Windows e `~/.local/share/esteira-videos` no Linux. Banco `esteira.db` (WAL, versão de esquema 2) e uma pasta de identificador aleatório por projeto. Nela ficam original, resultados, SRT/ASS, logs e miniaturas reais. Cópias compatíveis e prévias são tarefas reais que também ocupam disco. Arquivos não são publicados como uma pasta inteira; a API resolve identificadores internos.

Variáveis opcionais (veja `config.example.ps1`):

| Variável | Padrão | Função |
|---|---|---|
| `ESTEIRA_DATA` | pasta do usuário acima | Banco e arquivos; deve ser gravável |
| `ESTEIRA_MAX_UPLOAD_GB` | `20` | Limite por gravação, aplicado durante streaming |
| `ESTEIRA_FFMPEG` | `ffmpeg` | Executável local |
| `ESTEIRA_FFPROBE` | `ffprobe` | Executável local |

O envio é um corpo binário recebido em blocos, com um único upload ativo. A gravação é validada antes de entrar no banco; arquivos inválidos/parciais são removidos. Originais válidos nunca são alterados. A renderização escreve `.partial.mp4`, verifica resolução/duração por FFprobe e só então promove o resultado. Cancelamentos/falhas removem o MP4 parcial; SRT/ASS e logs permanecem para diagnóstico. Não há limpeza automática de originais nem expiração de resultados. **Excluir projeto** exige confirmação e remove todos os seus arquivos; tarefas pendentes/ativas devem ser canceladas e o trabalhador deve terminar antes. Faça backup da pasta de dados com os processos parados.

## Desenvolvimento (Linux ou Windows)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cd frontend
npm ci
npm run build
npm run lint
cd ..
.venv/bin/python -m pytest -q tests
.venv/bin/python -m backend.run
```

No Windows substitua `.venv/bin/python` por `.venv\Scripts\python.exe`. Para hot reload, execute a API em 8000 e `npm run dev` em `frontend`; Vite encaminha `/api` para a mesma origem no desenvolvimento. Abra `http://127.0.0.1:5173`. O proxy de desenvolvimento encaminha apenas essa origem local para a API; no modo normal não há proxy Vite nem exceção adicional de origem.

Estrutura: `backend/core.py` (banco, validação, geometria, SRT/ASS), `backend/app.py` (API, sessões e arquivos), `backend/worker.py` (fila e renderização), `backend/run.py` (supervisor), `frontend/src/` (interface), `tests/` (validação e integração). Não é necessário Docker.

## Diagnóstico e validação

No menu lateral, **Diagnóstico do sistema** mostra versões de FFmpeg/FFprobe, presença de libass e limites. Falta de libass impede legendas incorporadas; exportação sem legendas continua disponível. Todos os encoders usam CPU/libx264, 30 fps constantes, yuv420p, AAC quando há áudio e `faststart`. Não é necessário CUDA.

Testes automatizados geram vídeos sintéticos temporários, exercitam a API, conferem intervalo/regiões, SRT português, HTTP Range, exportação 1080×1920 com/sem áudio, duração, ZIP sem original, CSRF, pareamento, cancelamento e recuperação da fila. O navegador foi exercitado em Chromium Linux em 1440 px e 390 px, com importação, corte, exportação, reprodução real e revisão. Veja `VALIDATION.md` para resultados e limites.

## Limitações desta primeira versão

- Não há transcrição integrada, NVENC selecionável, rastreamento ou sugestões por IA. `requirements-transcription.txt` é **opcional e separado**, não é instalado no setup, e não baixa modelos na inicialização. Nenhum botão simula transcrição.
- O enquadramento é feito por campos numéricos e proporção vertical; não há seleção da região por retângulo arrastável sobre o player.
- A linha do tempo tem navegação, zoom, alças e cursor, mas não gera tira de miniaturas nem forma de onda. O fundo é identificado como faixa da gravação e não representa fotogramas/áudio fictícios.
- As legendas têm fonte Arial/sans equivalente, cor branca, contorno preto e posição inferior ajustável pela margem. Não há seletor de fonte, cor ou alinhamento nesta versão; não há destaque por palavra.
- A prévia curta renderizada aparece como resultado separado. Metadados de resultados são manuais. Não há publicação no YouTube.
- Importação não é retomável e o ZIP é preparado em arquivo temporário no disco do sistema antes do download. Reserve espaço para originais, cópias e exportações.
- Windows, Firewall e um celular físico não foram executados neste ambiente Linux. A compatibilidade foi implementada, mas precisa ser confirmada na máquina de destino.
