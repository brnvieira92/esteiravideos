"""Per-installation local CA and a read-only certificate onboarding server."""
import html
import ipaddress
import json
import os
import ssl
import socket
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def private_write(path, data):
    # Files live in the current user's application-data directory, never in the bundle.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data)


def prepare_tls(data: Path, addresses):
    folder = data / 'https'
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ca_path, key_path = folder / 'ca.crt', folder / 'ca.key'
    if ca_path.exists() != key_path.exists():
        raise ValueError('Certificado HTTPS incompleto. Restaure a pasta https do backup.')
    if not ca_path.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'EsteiraVideos CA ' + os.urandom(4).hex())])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
              .not_valid_after(now + timedelta(days=3650))
              .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
              .sign(key, hashes.SHA256()))
        private_write(key_path, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    ca = x509.load_pem_x509_certificate(ca_path.read_bytes())
    if ca.public_key().public_numbers() != key.public_key().public_numbers():
        raise ValueError('Chave e certificado HTTPS não correspondem.')
    if ca.not_valid_after_utc < now + timedelta(days=30):
        raise ValueError('Certificado local expirando. Remova a confiança nos dispositivos e renomeie a pasta https para configurar novamente.')
    ips = sorted({str(ipaddress.ip_address(a)) for a in addresses} | {'127.0.0.1'})
    cert_path, server_key = folder / 'server.crt', folder / 'server.key'
    manifest = folder / 'addresses.json'
    renew = True
    if cert_path.exists() and server_key.exists() and manifest.exists():
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        renew = json.loads(manifest.read_text()) != ips or cert.not_valid_after_utc < now + timedelta(days=7)
    if renew:
        leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cert = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'EsteiraVideos local')]))
                .issuer_name(ca.subject).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=90))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')] + [x509.IPAddress(ipaddress.ip_address(a)) for a in ips]), critical=False)
                .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .sign(key, hashes.SHA256()))
        private_write(server_key, leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        manifest.write_text(json.dumps(ips))
    # Fail at startup rather than leaving a worker running after a broken TLS setup.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, server_key)
    return cert_path, server_key, ca, ca_path


def start_setup(host, port, https_port, ca, addresses):
    public_cert = ca.public_bytes(serialization.Encoding.DER)
    fingerprint = ca.fingerprint(hashes.SHA256()).hex(':').upper()
    links = ''.join(f'<li><a href="https://{html.escape(ip)}:{https_port}">https://{html.escape(ip)}:{https_port}</a></li>' for ip in addresses)
    page = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EsteiraVídeos — conectar celular</title><style>body{{font:17px system-ui;background:#11131a;color:#eee;max-width:780px;margin:30px auto;padding:20px;line-height:1.6}}a{{color:#b99aff}}code{{overflow-wrap:anywhere}}</style>
<h1>Grave seu react pelo celular</h1><p>Computador e celular devem estar no mesmo Wi-Fi. Esta página HTTP serve apenas para instalar o certificado público; vídeos e pareamento usam HTTPS.</p>
<ol><li>Baixe o certificado. Antes de confiar, confira nos detalhes do certificado baixado se a impressão SHA-256 é igual à exibida no terminal do computador. Conferir apenas o texto desta página não verifica o arquivo baixado. Se o celular não mostrar a impressão, transfira o certificado público diretamente do PC por cabo ou outro meio confiável.</li><li><a href="/esteira-ca.cer">Baixar certificado deste computador</a></li><li>Instale e confie no certificado seguindo as instruções abaixo.</li><li>Abra o endereço HTTPS do computador, digite o código de pareamento mostrado no terminal e entre em <b>Editor → Modo react → Gravar agora</b>. Autorize câmera e microfone.</li></ol>
<h2>Android — Chrome</h2><p>Nas Configurações, procure “Instalar certificado” → Certificado CA (normalmente em Segurança → Criptografia e credenciais). Selecione esteira-ca.cer em Downloads. Os nomes variam por fabricante. Feche e reabra o Chrome.</p>
<h2>iPhone — Safari</h2><p>Após baixar, abra Ajustes → Perfil Baixado (ou Geral → VPN e Gerenciamento de Dispositivo) → Instalar. Depois, em Geral → Sobre → Ajustes de Confiança de Certificado, ative a confiança total para a CA EsteiraVideos deste computador. Reabra o Safari.</p>
<h2>Computador — Windows</h2><p>Abra o certificado baixado → Instalar Certificado → Usuário Atual → Colocar todos os certificados no repositório a seguir → Autoridades de Certificação Raiz Confiáveis. Reabra o navegador. A instalação é manual e não exige alterar o Path.</p>
<h2>Abrir o sistema com HTTPS</h2><ul>{links}</ul><p>Se houver aviso de certificado, conclua a instalação acima; ignorar o aviso não libera a câmera. Se o IP mudar, reinicie o aplicativo e use o novo endereço. O certificado raiz continua o mesmo.</p>
<p>SHA-256 deste computador:<br><code>{fingerprint}</code></p><p>Confie apenas no certificado do seu computador. Ele permite confiar em conexões assinadas por esta instalação. Para remover, exclua a CA EsteiraVideos nas configurações de certificados/perfis do dispositivo. Nunca compartilhe os arquivos .key. Não abra portas no roteador.</p>
<p>Mantenha esta aba aberta durante a gravação, sem bloquear a tela. Não há garantia de captura em segundo plano. A compatibilidade depende do navegador e dispositivo.</p></html>'''.encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/esteira-ca.cer':
                body, content_type = public_cert, 'application/x-x509-ca-cert'
            elif self.path == '/':
                body, content_type = page, 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
            if self.path.endswith('.cer'):
                self.send_header('Content-Disposition', 'attachment; filename="esteira-ca.cer"')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    class SetupServer(ThreadingHTTPServer):
        # POSIX SO_REUSEADDR permits restart after closed connections, but doesn't
        # share an active listener. Windows needs exclusive binding instead.
        allow_reuse_address = os.name != 'nt'

        def server_bind(self):
            if os.name == 'nt':
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

    server = SetupServer((host, port), Handler)
    server.daemon_threads = True
    Thread(target=server.serve_forever, daemon=True).start()
    return server, fingerprint
