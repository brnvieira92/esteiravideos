# Validação — 24/10/2026

A primeira entrega foi validada em Linux, Python 3.12.14, Node.js 24.19.0 e Chromium local. A segunda entrega também passou por build e testes automatizados em Windows Server 2022 no GitHub Actions, conforme registro abaixo. Não foi usado um dispositivo móvel físico.

| Verificação | Resultado |
|---|---|
| Instalação Python em `.venv` | Aprovada |
| `npm ci` com lockfile | Aprovada |
| `npm run build` (TypeScript + Vite) | Aprovada |
| `npm run lint` | Aprovada |
| `python -m pytest -q tests` | **7 testes aprovados** |
| Navegador desktop, 1440 × 1000 | Importou vídeo real sintético, salvou corte e enviou exportação |
| Reprodução do resultado em Chromium | 1080 × 1920, relógio de reprodução avançou |
| Revisão pela interface | Estado Revisado persistido pela API |
| Layout móvel, 390 × 844 | Sem overflow horizontal, navegação inferior e resultado legíveis |
| Erros JavaScript no fluxo de navegador | Nenhum |
| Encerramento do supervisor por SIGTERM | Saiu com código 0 e encerrou o trabalhador iniciado |
| `git diff --check` | Aprovada |

Os testes cobrem: intervalos e limites de coordenadas; recorte de SRT da gravação para o Short; português nas legendas incorporadas via libass; renderização combinada real com/sem áudio; dimensão, 30 fps e duração por FFprobe; HTTP Range; idempotência da exportação; ZIP sem original; rejeição de CSRF e origem externa; pareamento exigido na LAN; cookie HttpOnly; recuperação de tarefa interrompida; exclusão mútua entre trabalhadores; cópia H.264 com duração/resolução preservadas; cancelamento durante encoding e remoção de MP4 parcial; rejeição e limpeza de upload inválido.

Há um aviso de depreciação no TestClient do Starlette sobre um alias do AnyIO. Não impediu os testes. As capturas de tela usaram barras sintéticas geradas localmente pelo FFmpeg; o aplicativo não inclui gravações fixas nem imagens do mockup.

Não validados em uma máquina do usuário: Firewall, fechamento manual da janela no Windows, rede Wi-Fi física, Safari/iOS, codecs de câmera específicos, vídeos de várias horas, taxa de quadros variável em arquivo real, falha de energia, concorrência de múltiplos celulares e grandes volumes de upload/ZIP. Essas condições exigem validação adicional no computador de destino.

Limitações implementacionais estão no README: transcrição/NVENC não integrados, seleção de regiões por números, timeline sem miniaturas/forma de onda, fonte/cor/alinhamento de legenda fixos e prévia instantânea com diferenças de quebra de texto. O resultado renderizado é a referência final.

## Empacotamento Windows (segunda entrega)

- Testes de regressão e resolução de recursos do bundle: **10 aprovados em Linux**.
- Teste adicional do supervisor em modo local e LAN: upload real, legenda, H.264/AAC 1080×1920, pareamento e liberação do lock após encerramento, aprovado em Linux.
- `scripts/build-windows.ps1` e `.github/workflows/windows-installer.yml` executam o build nativo Windows, teste do binário PyInstaller, instalação Inno Setup, teste da cópia instalada e desinstalação. O resultado de cada build deve ser consultado no GitHub Actions; uma configuração de CI, por si só, não comprova aprovação no Windows.
- Build por usuário, FFmpeg fixado por SHA256, recursos resolvidos por `_MEIPASS`, trabalhador reexecutado com `--worker`, grupos de processos e Job Object no Windows.
- Sem assinatura Authenticode, sem alteração de Path, Firewall ou remoção da pasta de dados na desinstalação. Não há release pública automática; artefatos de validação ficam no Actions por 30 dias.

### Resultado confirmado no Windows

Execução [40125974544](https://github.com/brnvieira92/esteiravideos/actions/runs/40125974544), commit `6139485`, concluída com **Success** em 24/10/2026. Duração total: 4m10s.

- PyInstaller compilou o executável nativo Windows x64 com Python, frontend e FFmpeg/FFprobe incluídos.
- O binário congelado passou pelo smoke test nos modos local e LAN: upload real, legenda, renderização 1080×1920 com áudio, pareamento e encerramento do trabalhador.
- Inno Setup produziu o instalador; o pipeline instalou em caminho com espaços/acentos, repetiu o smoke test na instalação e executou o desinstalador.
- A etapa de regressão Windows passou antes do upload do artefato (o workflow interrompe ao primeiro erro).
- Artefato `EsteiraVideos-Windows-x64`, aproximadamente 102 MB, inclui `EsteiraVideos-Setup.exe`, `SHA256SUMS.txt` e `LEIA-ME.txt`; retenção de 30 dias.
- O log da execução tem um aviso de migração do runtime das actions Node.js 20 para Node.js 24. O build e os testes concluíram com sucesso.

Permanece necessária a validação do uso interativo em Windows 10/11 físico, SmartScreen/antivírus, regras do Firewall e acesso por um celular real. O smoke test não abre o navegador nem exercita o assistente gráfico do instalador; ele testa instalação/desinstalação silenciosas e a API do programa instalado.

## Correção 0.2.1 — enquadramento automático

Prévia, API e geometria de exportação agora preservam largura/altura e limitam X/Y ao espaço disponível. Os campos mostram o ajuste imediatamente. O caso relatado (X=0,06, Y=0,35, largura=0,62, altura=0,87) passa a Y=0,13 e pode ser salvo, reaberto e exportado.

- 11 testes Python aprovados, incluindo persistência e exportação real do enquadramento relatado.
- 3 testes de geometria do frontend aprovados, incluindo idempotência, bordas e rejeição de valores inválidos.
- TypeScript/build e lint aprovados.
- Smoke test local e LAN com as coordenadas relatadas, renderização real e legendas aprovado em Linux.
- O smoke test do executável Windows e da cópia instalada também exercitou essas coordenadas. A [execução 40128973874](https://github.com/brnvieira92/esteiravideos/actions/runs/40128973874), commit `841d3a5`, terminou com **Success** em 3m11s e disponibilizou o instalador 0.2.1 (artefato de aproximadamente 102 MB).

Conferência adicional em Chromium: as coordenadas do caso relatado foram digitadas na interface; o campo Y mudou para 0,13, o salvamento foi confirmado pela API e o mesmo enquadramento reapareceu ao recarregar o projeto. Nenhum erro JavaScript nesse fluxo.

## Versão 0.3.0 — seleção visual e sliders

- Seleção desenhada em qualquer direção sobre o conteúdo real do vídeo; mover e redimensionar pelos quatro cantos.
- Sliders de horizontal, vertical, largura e altura, campos numéricos e movimento por setas (Shift para 10 pixels).
- Edição pausa a gravação e preserva sua proporção, evitando mapear barras vazias como parte da imagem. Concluir seleção devolve os controles nativos do player.
- 6 testes de geometria do frontend aprovados, incluindo desenho, limites, movimento e redimensionamento; build/TypeScript e lint aprovados.
- 11 testes de backend aprovados.
- Chromium 1440 px: desenhar webcam, mover sem alterar tamanho, redimensionar, ajustar pelo slider e salvar; coordenadas persistidas conferidas pela API, nenhum erro JavaScript.
- Chromium com toque emulado 390 × 844: desenhar webcam por eventos de toque, conferir coordenadas e ausência de overflow horizontal. Não substitui teste em celular físico/Safari.

A [execução Windows 40131442044](https://github.com/brnvieira92/esteiravideos/actions/runs/40131442044), commit `8a8325d`, terminou com **Success** em 3m55s: build/TypeScript, lint, 6 testes de geometria, smoke tests do executável e da cópia instalada (local/LAN, exportação real), desinstalação e 11 testes de regressão Python. O artefato contém o instalador **0.3.0**. A interação de arraste/toque foi exercitada em Chromium Linux; o teste Windows do pacote exercita API/renderização, não automação da interface gráfica.

## Versão 0.3.1 — excluir resultados e preservar enquadramento

- Resultados têm Excluir vídeo com confirmação; o player é fechado antes da solicitação para liberar o arquivo no Windows.
- A API remove somente arquivos gerados de um resultado concluído, bloqueia tarefas ainda ativas e cópias de visualização, protege originais e caminhos externos e responde 410 para arquivos já excluídos.
- Identificadores das tarefas excluídas são retidos sem o arquivo de vídeo, impedindo que retransmissões da mesma requisição recriem a exportação. Os registros não aparecem na fila nem em Resultados.
- Novos cortes copiam layout, webcam/gameplay, split e estilo do corte atual; os objetos são independentes e os blocos de legenda, nome e ID não são copiados. A seleção de resultados também foi separada da seleção de cortes.
- 15 testes Python aprovados, incluindo exportação real seguida de exclusão, preservação byte a byte do original, proteção contra exclusão de original, idempotência, arquivos em uso simulados e reabertura de cortes antigos sem blocos opcionais.
- 8 testes frontend aprovados, build/TypeScript e lint aprovados.
- Chromium: editar enquadramento, salvar, criar e exportar outro corte com o mesmo enquadramento, cancelar uma exclusão e depois confirmá-la durante reprodução. O resultado desapareceu após recarga; original e dois cortes continuaram disponíveis. Conferidos seleção independente, toque mínimo de 44 px e ausência de overflow em 390 px. Nenhum erro JavaScript nesse fluxo.
- Smoke test local/LAN passou a excluir o resultado após a renderização e confirmar que o projeto, original e corte permanecem disponíveis. O mesmo teste será executado no pacote Windows.
