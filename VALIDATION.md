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

A [execução Windows 40134282812](https://github.com/brnvieira92/esteiravideos/actions/runs/40134282812), commit `081a31e`, concluiu com **Success** em 3m25s. Foram aprovados build/TypeScript, lint, 8 testes frontend, 15 testes Python e os smoke tests do executável e da instalação em modos local/LAN, agora incluindo exclusão real de resultado e preservação de original/corte. O artefato contém o instalador **0.3.1**.

## Versão 0.4.0 — react com duas fontes e captura

- 25 testes Python aprovados: migração de banco v2→v3 preservando original, isolamento entre projetos, limites de cobertura/offset, snapshot imutável, remux WebM sem duração, renderização de fontes com dimensões distintas e quatro combinações de presença de áudio.
- A exportação real foi decodificada para verificar pixel vermelho da fonte de reação na metade superior. Testes de frequência do áudio verificaram aproximadamente 880 Hz para reação isolada e 440 Hz para base isolada ao zerar a outra fonte.
- 8 testes frontend aprovados, incluindo herança de reação/offset/volumes em novos cortes; build/TypeScript e lint aprovados.
- Chromium Linux: envio de reação, reprodução sincronizada dos dois players, seleção da webcam sobre a fonte correta, gravação MediaRecorder de câmera e microfone de teste, escrita em OPFS, upload real de WebM, persistência e exportação/reprodução em 1080×1920. Nenhum erro JavaScript. Sem overflow em largura de 390 px.
- A captura usa as flags de câmera/microfone de teste **somente no navegador de teste**; o aplicativo não inclui fonte simulada. Iriun físico, dispositivos reais, Safari e gravação de longa duração/quota reduzida ainda precisam ser testados na máquina do usuário.
- O smoke test do executável passou a compor base e reação separados, conferir áudio, excluir o resultado e confirmar que as duas fontes e o corte permanecem. Validado em Linux nos modos local/LAN; o build Windows será confirmado pela execução do Actions.

A validação adicional de áudio com início atrasado detectou e corrigiu uma antecipação indevida da voz: agora o mixer mantém o silêncio inicial do arquivo original. O teste decodifica o PCM da exportação e confere silêncio antes do início da voz e áudio depois.

A [execução Windows 40136713237](https://github.com/brnvieira92/esteiravideos/actions/runs/40136713237), commit `3225754`, terminou com **Success** em 3m53s e disponibilizou o instalador **0.4.0** (~102 MB). Passaram build/TypeScript, lint, 8 testes frontend, 25 testes Python e os smoke tests do binário e da cópia instalada, com composição real de base/reação, áudio, legendas, pareamento e exclusão preservando as duas fontes. A gravação pelo navegador foi exercitada em Chromium Linux com dispositivos de teste; o runner Windows não testou câmera física nem Iriun.

## HTTPS local — versão 0.4.1

- 27 testes Python aprovados; 8 testes de frontend, TypeScript/Vite e lint aprovados.
- Handshake TLS real com validação da cadeia e do IP por CA explícita: aprovado. CA não confiável: rejeitada. Renovação do certificado após alteração do IP preserva a CA.
- Servidor de configuração HTTP: serve apenas página e certificado DER público; URLs de chaves privadas, traversal e API retornam 404.
- Smoke do supervisor em Linux passou em três modos: localhost HTTP, LAN HTTP legada e LAN HTTPS com verificação da CA, cookie Secure, pareamento, importação de duas fontes, exportação com voz/legendas, exclusão e encerramento. O mesmo smoke integra o build do executável e da instalação Windows.
- Chromium em viewport 390×844: contexto seguro, pareamento, upload, reprodução sincronizada, gravação MediaRecorder com câmera/microfone de teste, envio automático, exportação e reprodução 1080×1920; sem erros JavaScript ou overflow. O teste de UI usa a opção de teste Playwright `ignoreHTTPSErrors` por não instalar uma CA no perfil do navegador do ambiente; a cadeia TLS foi validada separadamente sem essa exceção pelo cliente Python e pelo smoke.
- A reprodução do vídeo base começa no gesto do usuário antes das operações assíncronas de armazenamento, para respeitar restrições de autoplay móvel; o offset é capturado ao iniciar o gravador.
- Sem Android/iPhone físico neste ambiente: instalação do certificado, permissões, câmera real, comportamento específico do Safari e gravação prolongada precisam ser conferidos nos dispositivos. Não foi instalada confiança automática no Windows ou celular.

Instalador 0.4.1 aprovado em Windows Server 2022: [execução 40138941938](https://github.com/brnvieira92/esteiravideos/actions/runs/40138941938), commit `edd39c5`. Compilação, smoke do executável, instalação silenciosa em caminho com espaços/acentos, smoke da cópia instalada (HTTP local, LAN legada e HTTPS com verificação de certificado), desinstalação e 27 testes Python concluídos com sucesso. Artefato disponível: `EsteiraVideos-Windows-x64`. Isso não substitui a validação em celular físico.

## Rotação de vídeos de celular — versão 0.4.2

Corrigida a leitura das dimensões após a matriz de rotação usada por Android/iPhone: 90° e 270° trocam largura e altura, como o navegador e o autorotate do FFmpeg. Os metadados antigos são atualizados ao abrir o projeto, criar uma tarefa ou executar tarefas antigas, sem reencodar os originais nem alterar regiões normalizadas.

Testes reais com MP4 e matrizes 0°, 90°, 180° e 270° verificam upload de base/reação, exportação com ambas as fontes, metadados legados, tarefas antigas, resolução 1080×1920 e preservação byte a byte do original. O smoke do instalador também passou a usar reação com matriz de rotação 90°. Linux: 31 testes Python, 8 de frontend, build/lint e smoke HTTP/LAN/HTTPS aprovados.

A versão 0.4.2 foi aprovada no Windows na [execução 40141130226](https://github.com/brnvieira92/esteiravideos/actions/runs/40141130226), commit `8f9f151`: executável, instalação, smoke com reação rotacionada e 31 testes Python. Chromium com viewport 390×844 também reconheceu a fonte com rotação 90° como 180×320 e exportou/reproduziu 1080×1920 sem erros JavaScript.

## Espelhamento da câmera — versão 0.4.3

Checkbox em Gravar agora e Enquadramento controla a prévia ao vivo, o canvas do Short e `hflip` apenas no ramo de webcam do FFmpeg, após o recorte. Preferência booleana validada, salva e herdada nos novos cortes. Gravação original preservada. Testes exportam imagens assimétricas (vermelho de um lado, azul do outro) com e sem espelhamento, usando webcam no original e reação separada, e verificam os pixels decodificados: apenas a metade da webcam troca os lados.

Versão 0.4.3 aprovada no Windows: [execução 40141639888](https://github.com/brnvieira92/esteiravideos/actions/runs/40141639888), commit `c11ee8f`. Executável, instalação em caminho com espaços/acentos, smoke nos modos local/LAN/HTTPS com reação rotacionada e espelhamento, desinstalação e 34 testes Python aprovados. Frontend: 8 testes, build e lint aprovados.

Chromium em 390×844 verificou pixels do canvas antes/depois do checkbox (webcam vermelha à esquerda tornou-se azul, gameplay continuou vermelha), persistência de `camFlip`, checkbox compartilhado em Gravar agora, câmera de teste ao vivo com transformação horizontal, ausência de erros JavaScript e de overflow. Testes de exportação verificaram os pixels do MP4 decodificado em resolução completa, evitando mistura de crominância de uma redução para 2×2. Não houve teste adicional em câmera física de celular.

## Gestos na prévia — versão 0.4.4

12 testes de frontend aprovados: geometria do recorte visível, âncora da pinça, proporções, limites extremos, direção com webcam espelhada e testes anteriores. Build TypeScript/Vite e lint aprovados. Backend: 34 testes aprovados.

Chromium emulado com toque real via CDP (390×844, `isMobile` e `hasTouch`): dois contatos simultâneos aproximaram webcam e gameplay independentemente, levantar um contato e continuar arrastando manteve o zoom, arraste moveu a região, viewport permaneceu em escala 1 e scroll não mudou durante os gestos. Desfazer restaurou os dois enquadramentos de entrada, o botão + ajustou a região ativa, concluir retirou a camada que captura gestos, salvar persistiu as coordenadas e o resultado exportado reproduziu em 1080×1920. Sem erros JavaScript ou overflow horizontal. Não houve teste em celular físico.

A transformação começa na região efetivamente visível após o recorte central de preenchimento, para permitir mover a imagem mesmo quando os campos anteriores abrangem o vídeo inteiro. O zoom preserva a proporção e a âncora entre os dedos, limita as coordenadas à fonte, considera o espelhamento da câmera e não afeta as legendas ou a outra região. O modo explícito de edição usa `touch-action:none`; ao concluir a camada é retirada.

Instalador 0.4.4 aprovado em Windows Server 2022: [execução 40199751067](https://github.com/brnvieira92/esteiravideos/actions/runs/40199751067), commit `c41525c`. Executável, instalação silenciosa, smoke local/LAN/HTTPS, desinstalação, 34 testes Python e 12 testes de frontend concluídos com sucesso. Build e lint também aprovados. Artefato `EsteiraVideos-Windows-x64` disponível.

Teste adicional com contatos de toque via CDP confirmou a direção do arraste com webcam espelhada e que um cancelamento de toque permite começar um novo gesto normalmente. Inspeção visual da tela móvel confirmou os controles junto à prévia e as duas regiões identificadas. O teste cobre Chromium emulado; não foi utilizado Android/iPhone físico.

## Numeração e prevenção de exportação repetida — versão 0.4.5

Tabela adicional `cut_sequences` preserva a sequência por projeto sem alterar a versão de esquema ou renomear cortes existentes. A alocação e a comparação de nomes usam transação SQLite `BEGIN IMMEDIATE`. Projetos antigos iniciam considerando seus cortes e os números encontrados nos títulos. Sugestões desatualizadas de clientes simultâneos são corrigidas ao salvar. Títulos duplicados antigos continuam editáveis; novos conflitos são recusados.

Exportações são comparadas por campos que afetam a renderização, incluindo fonte/dimensões, intervalo, regiões, reação/sincronização, volumes, espelhamento e legendas/estilo. Nome, ID do corte e ID da requisição não criam uma diferença de vídeo. A transação serializa pedidos concorrentes. Histórico de resultados excluídos é preservado; regeneração exige `force:true`, que também reaproveita tarefas ativas. Prévias usam categoria separada. Cancelamentos/falhas não bloqueiam novo pedido; retry reaproveita um resultado disponível ou tarefa ativa.

Testes exercitam contador após exclusão/renomeação, sugestões antigas, duas gravações simultâneas, duas exportações simultâneas, cópia com conteúdo igual, renomeação sem reexportar, alteração de renderização, resultado excluído ou ausente, regeneração explícita, prévia separada, histórico de versões anteriores, retry e títulos duplicados legados. O smoke do executável também verifica nome automático e histórico antes/depois da exclusão.

Chromium em viewport 390×844 criou e salvou partes 1 e 2; exportou a primeira, adicionou só a segunda ao exportar a seleção inteira e reutilizou ambos os resultados ao repetir o pedido. Mantidos apenas dois jobs e sugestão parte 3; sem erros JavaScript ou overflow.

Instalador 0.4.5 aprovado em Windows Server 2022: [execução 40203928973](https://github.com/brnvieira92/esteiravideos/actions/runs/40203928973), commit `b832262`. Compilação, 13 testes de frontend, build/lint, smoke do executável e da instalação em caminho com espaços/acentos (local/LAN/HTTPS), exclusão preservando histórico, desinstalação e 39 testes Python concluídos com sucesso. Artefato `EsteiraVideos-Windows-x64` disponível.

## Dispositivos confiáveis — versão 0.4.6

43 testes Python e 13 de frontend aprovados em Linux; TypeScript/Vite e lint aprovados. Novos testes verificam cookie Secure/HttpOnly/SameSite Strict/Path / com validade de 90 dias, token apenas como hash no SQLite, autenticação após perda das sessões em memória e mudança de código, validade expirada, token adulterado, recusa por HTTP mesmo com replay manual, pareamento temporário, revogação individual/em lote, logout, restrição da gestão a loopback com hostname local e recusa de IP encaminhado falso. Respostas de autenticação/lista não são armazenáveis em cache.

Smoke Linux com verificação TLS da CA real: reinício completo do supervisor, mesma pasta de dados/certificado e cookie, acesso autorizado sem reenviar código, listagem local e revogação bloqueando a próxima requisição. Foram ajustadas as opções de reuso de porta em POSIX para permitir reinício com conexões anteriores fechadas; no Windows a página de configuração usa bind exclusivo. O servidor de configuração continua recusando um segundo listener ativo na mesma porta.

Chromium em viewport 390×844: pareamento pela interface com checkbox e nome; cookie de confiança protegido; reinício real do servidor mantendo acesso; gestão da autorização por outro navegador no PC; celular voltando ao formulário após revogação; novo pareamento e esquecimento do próprio dispositivo removendo o cookie; sem erros JavaScript ou overflow. O teste usou endereços de loopback separados para simular os papéis do celular e PC e `ignoreHTTPSErrors` no perfil de teste. A cadeia TLS foi verificada separadamente no smoke sem ignorar certificados. Não foi utilizado telefone físico.

Instalador 0.4.6 aprovado em Windows Server 2022: [execução 40206576776](https://github.com/brnvieira92/esteiravideos/actions/runs/40206576776), commit `3f1b386`. Compilação, 13 testes de frontend, build/lint, smoke do executável e da cópia instalada em caminho com espaços/acentos, reinício HTTPS com conexão keep-alive anterior, permanência da confiança sem novo código, revogação, encerramento e 43 testes Python aprovados. Artefato `EsteiraVideos-Windows-x64` disponível.

O encerramento do servidor recebeu limite de 5 segundos para drenar requisições, evitando espera indefinida com conexões HTTPS mantidas pelo navegador; em seguida o supervisor encerra o trabalhador e a página de configuração. A reinicialização rápida foi verificada em Linux e no Windows com as mesmas portas e pasta de dados.

## Webcam em tela cheia — versão 0.4.7

49 testes Python e 13 de frontend aprovados em Linux; TypeScript/Vite e lint aprovados. O layout `webcam` recorta `cam` da fonte original ou da reação separada, preenche 1080×1920 e aplica espelhamento, sem empilhar gameplay. Com reação separada, somente sua faixa de áudio é usada; falta de áudio ou volume zero não aciona fallback para o vídeo base. A prévia usa o mesmo recorte e seus gestos atuam somente em `cam`.

Novos testes exportam webcam do original e reação separada, com/sem espelhamento; verificam pixels de ambos os lados no alto e na parte inferior do MP4, resolução, presença de áudio, frequência da voz e ausência da frequência do vídeo base. Testam também reação silenciosa/voz silenciada e a identidade de exportação: mudanças em gameplay/divisão/volume do base não criam outro resultado webcam-only, mas mudar o espelhamento permite nova exportação.

Instalador 0.4.7 aprovado em Windows Server 2022: [execução 40211354811](https://github.com/brnvieira92/esteiravideos/actions/runs/40211354811), commit `586a88a`. Build/lint, 13 testes de frontend, smoke do executável e da instalação (local/LAN/HTTPS, webcam-only com reação rotacionada, áudio, legenda, reinício e revogação), desinstalação e 49 testes Python aprovados. Artefato `EsteiraVideos-Windows-x64` disponível.

Chromium em viewport móvel 390×844 verificou webcam separada vermelha no alto e embaixo do canvas, volume do base igual a zero, volume da reação igual a um, controles exclusivos de webcam, uma única região na prévia, zoom modificando `cam`, persistência do layout `webcam`, exportação e reprodução 1080×1920; sem erros JavaScript ou overflow. O teste usou navegador emulado, sem telefone físico.

## 0.4.8 — intervalo automático da reação

- 14 testes da interface aprovados, incluindo 7 + 15 = 22, mudança de início, milissegundos, limites do original e ausência de sobreposição.
- Lint e build TypeScript/Vite aprovados.
- Chromium: envio de MP4 sintético com o original posicionado em 7 s definiu corte 7–22 s; alteração da sincronização para 10 s definiu 10–25 s; início 20 s em original de 30 s limitou o fim a 30 s. Todos os intervalos foram salvos e conferidos pela API, sem erros JavaScript. Não foi usado celular físico nesta validação.

## 0.4.9 — mesclagem de resultados

- Suíte Python anterior e novo teste de união: 50 aprovados; ampliado o teste de união com e sem SRT: ambos aprovados separadamente.
- Renderização FFmpeg real: sequência vermelho/azul, duração somada, 1080×1920, fonte com áudio e fonte silenciosa, SRT deslocado, preservação dos arquivos, bloqueio de exclusão enquanto pendente, deduplicação e ordem invertida.
- 14 testes frontend, lint e build aprovados.
- Chromium em viewport mobile: selecionou dois resultados, inverteu ordem, informou nome e enviou mesclagem à fila sem erros JavaScript ou rolagem horizontal. Sem aparelho físico nesta validação.
