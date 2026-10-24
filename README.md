# EsteiraVídeos

Editor local de gameplays e lives para Shorts. Interface em português, desktop e celular; FastAPI, React/TypeScript, SQLite e FFmpeg. Nenhuma chave de API, telemetria ou envio externo de vídeos. O projeto entrega edição manual real, não usa vídeos demonstrativos na interface.

## Instalação simples no Windows (sem configurar ferramentas)

O instalador **0.3.1**, com exclusão de resultados e herança de enquadramento entre cortes, foi gerado e validado na [execução 40134282812](https://github.com/brnvieira92/esteiravideos/actions/runs/40134282812). Baixe o pacote **EsteiraVideos-Windows-x64** na seção **Artifacts** dessa execução.

O fluxo [Instalador Windows](https://github.com/brnvieira92/esteiravideos/actions/workflows/windows-installer.yml) compila o programa em Windows e testa o executável e o instalador antes de disponibilizar o arquivo.

1. Abra o link acima e selecione a execução mais recente **concluída com sucesso**.
2. No final da página, em **Artifacts**, baixe **EsteiraVideos-Windows-x64**. É necessário estar conectado ao GitHub para baixar artefatos.
3. Extraia o ZIP e abra **EsteiraVideos-Setup.exe**.
4. Siga o instalador. Depois, abra **EsteiraVídeos** no menu Iniciar (ou marque a criação de atalho na Área de Trabalho).
5. O navegador abre automaticamente. Mantenha a janela do aplicativo aberta; use **Ctrl+C** nela para encerrar.

O pacote inclui Python, FFmpeg/FFprobe e a interface pronta. **Não precisa instalar Python, Git, Node.js ou FFmpeg, nem editar o Path.** O instalador é por usuário e não exige administrador. Windows 10 22H2/11 x64; ARM nativo e Windows 32 bits não são alvos deste pacote.

Para celular, abra o atalho **EsteiraVídeos — acesso pelo Wi-Fi**. O endereço e o código temporário aparecem na janela do aplicativo. O instalador não altera o Firewall; caso necessário, autorize manualmente o aplicativo apenas na rede privada. Não exponha a porta na internet.

Atualizações usam o mesmo diretório. Feche o aplicativo antes de atualizar. Projetos ficam em `%LOCALAPPDATA%\esteira-videos`, fora da instalação; atualizar ou desinstalar **não apaga seus vídeos**. Faça backup com o aplicativo parado.

O pacote não tem assinatura digital. Confira o repositório de origem e o arquivo `SHA256SUMS.txt`; não desative o antivírus. O artefato fica disponível por 30 dias e pode ser gerado novamente pelo botão **Run workflow**, por quem possui permissão no repositório. Se a execução falhar, não haverá instalador aprovado para aquele commit.

### Gerar o instalador (somente desenvolvedores)

No Windows com Python 3.12, Node.js 24 e Inno Setup 6:

```powershell
.\scripts\build-windows.ps1
```

Saída: `dist\installer\EsteiraVideos-Setup.exe`. O script cria um ambiente Python local, compila a interface, baixa um FFmpeg de versão fixada (~200 MB) e confere SHA256 antes de usá-lo. Nenhuma dependência é instalada globalmente. Inclui avisos e licenças de terceiros. Consulte `packaging/THIRD-PARTY.txt` para as condições de redistribuição dos componentes; a geração de artefatos de teste não publica uma release pública automaticamente.

O pipeline testa upload, corte com legenda, renderização H.264/AAC 1080×1920, LAN com pareamento e encerramento do trabalhador **com o executável empacotado e sem FFmpeg/Python no PATH**. Em seguida, instala silenciosamente em um caminho com espaços e acentos, repete o teste e desinstala. O modo padrão abre o navegador; os testes usam `--no-browser` para não abrir janelas no runner.

## Instalação pelo código-fonte no Windows (alternativa para desenvolvimento)

Pré-requisitos instalados pelo usuário: **Python 3.12**, **Node.js 22 ou 24**, **FFmpeg e FFprobe** no PATH. Use uma distribuição do FFmpeg indicada em https://ffmpeg.org/download.html com `libx264`, AAC e `ass/subtitles` (libass). Nenhum script instala ferramentas globalmente, altera firewall ou baixa modelos.

No PowerShell, na raiz do checkout:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Abra o endereço impresso no terminal (porta 8000 por padrão). Caso a política local impeça scripts, execute os comandos do `setup.ps1` manualmente; não é necessário alterar permanentemente a política da máquina. O frontend compilado é servido pela API na mesma origem.

1. **Projetos → Novo projeto**; selecione ou arraste um MP4, MKV ou MOV.
2. Aguarde o envio e a validação FFprobe. Cada projeto recebe uma gravação original.
3. No editor, marque início/fim pelo player, pelos campos `HH:MM:SS.mmm`, pelas alças ou pelos sliders. Salve o corte. Use **Novo corte** para criar outros: o layout, as regiões de webcam/gameplay, a proporção e o estilo das legendas do corte atual são mantidos. Cada corte recebe intervalo, nome e blocos de legenda próprios; não é necessário reenquadrar a mesma gravação.
4. Em **Layout**, escolha gameplay ou webcam + gameplay. Clique em **Selecionar webcam no vídeo** (ou gameplay), desenhe a região sobre a gravação e arraste para mover; os quatro cantos redimensionam. Use **Nova seleção** para desenhar novamente e **Concluir seleção** para voltar aos controles do player. Os sliders de horizontal, vertical, largura e altura permitem ajustes rápidos, e os campos numéricos continuam disponíveis para precisão. Clique em **Salvar corte** para persistir. As regiões usam coordenadas normalizadas: X/Y são o canto superior esquerdo, largura/altura são frações do original. Exemplo: webcam no canto superior esquerdo ocupando 25% × 30%: X=0, Y=0, largura=0,25, altura=0,30. Se X+largura ou Y+altura ultrapassarem 1, a posição é ajustada automaticamente para caber, preservando largura e altura. Os campos mostram o ajuste e prévia, salvamento e exportação usam a mesma região. O enquadramento faz crop central para preencher, sem distorcer.
5. Em **Legendas**, adicione blocos ou importe SRT. Tempos manuais são relativos ao início do Short. A importação de SRT da gravação recorta e converte os tempos automaticamente. Ajuste tamanho, contorno e margem inferior. Salve.
6. Gere uma **prévia renderizada de até 5 segundos** para conferir. A composição de vídeo usa a mesma geometria normalizada; a prévia instantânea é reduzida e o texto do canvas pode diferir na quebra de linhas da renderização libass. Confira a renderizada antes da exportação final.
7. Marque os cortes e **Exporte**. A fila processa um vídeo por vez, em CPU. Os ajustes são copiados no momento do envio; editar depois não altera tarefas existentes.
8. Em **Resultados**, reproduza, edite título/descrição e aprove. Aprovação significa apenas revisão local. Baixe MP4, SRT ou ZIP selecionado; o original nunca entra no ZIP. Após baixar, use **Excluir vídeo** no cartão e confirme: essa ação remove a exportação e seus arquivos de legenda/miniatura, preservando o projeto, a gravação original e os cortes salvos. Você pode exportar o corte novamente. Se o Windows indicar arquivo em uso, feche a reprodução/download em outros aparelhos e tente excluir novamente.

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

Dados ficam **fora do código**, por padrão em `%LOCALAPPDATA%\esteira-videos` no Windows e `~/.local/share/esteira-videos` no Linux. Banco `esteira.db` (WAL, versão de esquema 3) e uma pasta de identificador aleatório por projeto. Nela ficam original, resultados, SRT/ASS, logs e miniaturas reais. Cópias compatíveis e prévias são tarefas reais que também ocupam disco. Arquivos não são publicados como uma pasta inteira; a API resolve identificadores internos.

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
- A seleção de região é manual (arraste, cantos, sliders ou campos numéricos). Não há rastreamento automático de rosto; o retângulo permanece na região escolhida do vídeo original.
- A linha do tempo tem navegação, zoom, alças e cursor, mas não gera tira de miniaturas nem forma de onda. O fundo é identificado como faixa da gravação e não representa fotogramas/áudio fictícios.
- As legendas têm fonte Arial/sans equivalente, cor branca, contorno preto e posição inferior ajustável pela margem. Não há seletor de fonte, cor ou alinhamento nesta versão; não há destaque por palavra.
- A prévia curta renderizada aparece como resultado separado. Metadados de resultados são manuais. Não há publicação no YouTube.
- Importação não é retomável e o ZIP é preparado em arquivo temporário no disco do sistema antes do download. Reserve espaço para originais, cópias e exportações.
- O instalador e o programa empacotado passaram por testes automatizados no Windows Server 2022 pelo GitHub Actions. Uso interativo em Windows 10/11 físico, SmartScreen, Firewall e um celular real ainda precisam ser confirmados na máquina de destino.

## Modo react: vídeo base + sua reação (0.4.0)

O projeto continua tendo um vídeo base, mas pode guardar vários vídeos de reação separados. Cada corte escolhe uma reação; arquivos originais são preservados. A saída continua vertical (webcam acima, base abaixo). Não há download de vídeos de terceiros, publicação ou envio a serviços externos.

### Usar uma reação que já está gravada

1. Importe o vídeo base normalmente e abra o editor.
2. Abra **Modo react → Adicionar reação → Enviar reação** e envie seu MP4, MKV, MOV ou WebM.
3. A aplicação prepara um novo corte no intervalo em comum. Os cortes já salvos permanecem independentes.
4. Ajuste **Reação começa no vídeo base em (segundos)**. Fórmula: tempo da reação = tempo do base − esse valor. Se a reação começa quando o base está em 10 s, use 10. Um valor negativo significa que a câmera começou antes do base.
5. **Reproduzir sincronizado** permite conferir imagem/voz. **Criar corte no intervalo em comum** refaz o intervalo mantendo o enquadramento da mesma reação. O corte precisa estar coberto pela gravação da reação; não é preenchido silenciosamente com imagem congelada.
6. Em Layout, selecione a webcam no **vídeo da reação** e a gameplay no **vídeo base**. Ajuste proporção e **Áudio do react**: volumes independentes de base e reação/voz, de 0 a 100%.
7. Salve e exporte. Novos cortes herdam também a reação, sincronização e volumes do corte atual. As tarefas guardam uma cópia das duas fontes/configurações no momento do envio.

Se o codec da reação não tocar no navegador, use **Gerar cópia compatível da reação**, aguarde sua tarefa na Fila e clique em **Usar cópia da reação**. A exportação usa o original.

### Gravar câmera e voz enquanto assiste

Faça isso no **Chrome ou Edge do computador**, usando o endereço **localhost ou 127.0.0.1** aberto pelo aplicativo. Câmera/microfone exigem contexto seguro; o endereço HTTP do computador no Wi-Fi não permite captura em navegadores comuns. No celular pela rede, envie uma reação já gravada e revise os resultados. Não é necessário criar outra rede nem desativar a internet.

1. Se for usar **Iriun Webcam**, abra e conecte o aplicativo/telefone e instale o driver oficial no Windows antes. O EsteiraVídeos não instala nem controla o Iriun: ele usa a câmera virtual que o driver disponibiliza ao navegador. Também pode usar webcam USB ou integrada.
2. Em **Modo react → Gravar agora**, clique em **Ativar câmera e microfone** e autorize o navegador. Após a autorização, a lista mostra os nomes dos dispositivos.
3. Escolha a câmera (por exemplo, Iriun Webcam) e o microfone desejado e ative novamente caso tenha mudado o dispositivo. **Atualizar dispositivos** consulta a lista do navegador. Se estiver ocupado, feche outros programas usando a câmera, mantendo o fornecedor da câmera virtual conectado.
4. Use **fones de ouvido** para evitar que o áudio do vídeo entre de novo no microfone. A prévia da câmera é muda para não causar realimentação; o microfone é gravado no arquivo.
5. Posicione o vídeo base no player do editor e clique em **Gravar enquanto assisto**. O monitor do vídeo base começa nessa posição. Durante a gravação não há edição, saltos ou pausas: o tempo entre as duas fontes deve continuar constante.
6. Clique em **Parar e salvar reação**. A gravação também termina ao acabar/pausar o base, ao perder o dispositivo ou detectar interrupção de reprodução. O arquivo é enviado ao computador e validado; não feche a aba antes da confirmação.
7. Confira a sincronização e ajuste o valor em segundos se necessário (latência de dispositivo/driver não é calibrada automaticamente). Configure o enquadramento, salve o corte e exporte.

A captura usa MediaRecorder e grava chunks em arquivo temporário no disco do navegador (OPFS), quando disponível, com limite de 60 minutos. Sem esse recurso, o fallback em memória é limitado a 128 MB e interrompe ao atingir o limite. Espaço/quota e permissão podem interromper a gravação; falhas são informadas. Se o envio falhar, use **Tentar salvar reação** ou **Baixar cópia da gravação**; após parar e fechar o arquivo, a recuperação da gravação pendente é oferecida ao reabrir o mesmo projeto/origem quando o navegador permite persistência. Fechar/derrubar o navegador **durante** a gravação pode perder o trecho ainda não finalizado.

WebM de navegador é remuxado localmente, sem recodificar os originais, para obter duração e navegação confiáveis. São mantidos tanto o arquivo recebido (`.original.webm` ou `.original.mp4`) quanto a cópia com índice. Reserve espaço para essas cópias, o temporário do navegador e as exportações. Excluir um resultado não apaga a reação original; Excluir projeto remove seus arquivos após confirmação.

O banco migra automaticamente da versão 2 para a **versão 3**, mantendo os projetos antigos como fonte base. Faça backup da pasta de dados com o programa fechado antes de atualizar; versões anteriores não abrem o banco versão 3. Webcam física e Iriun dependem das permissões/driver do seu Windows. A captura foi testada com dispositivos de câmera/microfone fornecidos pelo Chromium para testes; isso não substitui teste do seu hardware.
