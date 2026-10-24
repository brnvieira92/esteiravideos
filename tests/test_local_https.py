import ssl
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from backend.local_https import prepare_tls, start_setup


def test_trusted_tls_and_renewal(tmp_path):
    cert, key, ca, ca_path = prepare_tls(tmp_path, ['192.168.1.20'])
    before = ca.fingerprint(hashes.SHA256())
    original = cert.read_bytes()
    prepare_tls(tmp_path, ['192.168.1.20'])
    assert cert.read_bytes() == original
    cert, key, ca, _ = prepare_tls(tmp_path, ['192.168.1.21'])
    assert ca.fingerprint(hashes.SHA256()) == before
    sans = x509.load_pem_x509_certificate(cert.read_bytes()).extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert str(sans.get_values_for_type(x509.IPAddress)[0]) == '127.0.0.1'
    assert '192.168.1.21' in [str(a) for a in sans.get_values_for_type(x509.IPAddress)]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'TLS OK')
        def log_message(self, *_): pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = ssl.create_default_context(cafile=str(ca_path))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=client))
        assert opener.open(f'https://127.0.0.1:{server.server_port}').read() == b'TLS OK'
        with pytest.raises(ssl.SSLCertVerificationError):
            wrong = ssl.create_default_context()
            with __import__('socket').create_connection(server.server_address) as sock:
                wrong.wrap_socket(sock, server_hostname='localhost')
    finally:
        server.shutdown()
        server.server_close()


def test_setup_only_exposes_public_certificate(tmp_path):
    _, _, ca, _ = prepare_tls(tmp_path, [])
    server, fingerprint = start_setup('127.0.0.1', 0, 8000, ca, ['127.0.0.1'])
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        assert fingerprint.encode() in opener.open(base).read()
        public = x509.load_der_x509_certificate(opener.open(base + '/esteira-ca.cer').read())
        assert public.fingerprint(hashes.SHA256()) == ca.fingerprint(hashes.SHA256())
        for path in ['/ca.key', '/server.key', '/api/projects', '/../ca.key']:
            with pytest.raises(urllib.error.HTTPError) as e:
                opener.open(base + path)
            assert e.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
