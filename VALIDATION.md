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
