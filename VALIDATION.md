# Validação — 24/10/2026

Ambiente executado: Linux, Python 3.12.14, Node.js 24.19.0, Chromium local. Não foi executado Windows nem um dispositivo móvel físico.

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

Não validados neste ambiente: PowerShell/Windows, Firewall, taskkill no Windows, rede Wi-Fi física, Safari/iOS, codecs de câmera específicos, vídeos de várias horas, taxa de quadros variável em arquivo real, falha de energia, concorrência de múltiplos celulares e grandes volumes de upload/ZIP. Essas condições exigem validação adicional no computador de destino.

Limitações implementacionais estão no README: transcrição/NVENC não integrados, seleção de regiões por números, timeline sem miniaturas/forma de onda, fonte/cor/alinhamento de legenda fixos e prévia instantânea com diferenças de quebra de texto. O resultado renderizado é a referência final.

## Empacotamento Windows (segunda entrega)

- Testes de regressão e resolução de recursos do bundle: **10 aprovados em Linux**.
- Teste adicional do supervisor em modo local e LAN: upload real, legenda, H.264/AAC 1080×1920, pareamento e liberação do lock após encerramento, aprovado em Linux.
- `scripts/build-windows.ps1` e `.github/workflows/windows-installer.yml` executam o build nativo Windows, teste do binário PyInstaller, instalação Inno Setup, teste da cópia instalada e desinstalação. O resultado de cada build deve ser consultado no GitHub Actions; uma configuração de CI, por si só, não comprova aprovação no Windows.
- Build por usuário, FFmpeg fixado por SHA256, recursos resolvidos por `_MEIPASS`, trabalhador reexecutado com `--worker`, grupos de processos e Job Object no Windows.
- Sem assinatura Authenticode, sem alteração de Path, Firewall ou remoção da pasta de dados na desinstalação. Não há release pública automática; artefatos de validação ficam no Actions por 30 dias.
