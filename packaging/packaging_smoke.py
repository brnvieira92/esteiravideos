"""Real packaged-binary smoke test, also callable on Linux for supervisor validation."""
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request


def main():
    from backend.resources import executable, resource_root
    ffmpeg = executable('ffmpeg')
    ffprobe = executable('ffprobe')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix='esteira-videos-package-') as tmp:
        root = Path(tmp)
        source = root / 'source.mp4'
        subprocess.run([ffmpeg, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=24:duration=2',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-c:v', 'libx264', '-threads', '1',
                        '-c:a', 'aac', str(source)], check=True)
        for lan in (False, True):
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            url = f'http://127.0.0.1:{port}'
            env = {**os.environ, 'ESTEIRA_DATA': str(root / ('lan' if lan else 'local')), 'PYTHONUTF8': '1'}
            # Explicit bundled paths, and no system FFmpeg on PATH, prove the dependency is included.
            env['ESTEIRA_FFMPEG'] = ffmpeg
            env['ESTEIRA_FFPROBE'] = ffprobe
            if getattr(sys, 'frozen', False):
                env['PATH'] = os.environ.get('SystemRoot', 'C:\\Windows') + '\\System32'
                command = [sys.executable, '--no-browser']
            else:
                command = [sys.executable, '-m', 'backend.run', '--no-browser']
            command += ['--port', str(port)] + (['--lan'] if lan else [])
            proc = subprocess.Popen(command, cwd=resource_root(), env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                                    **({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {}))
            lines = []
            def read():
                for line in proc.stdout:
                    lines.append(line)
            thread = threading.Thread(target=read, daemon=True)
            thread.start()
            def request(path, data=None, method=None, raw=False, headers=None):
                h = {'X-Esteira': '1', **(headers or {})}
                if data is not None and not raw:
                    data = json.dumps(data).encode()
                    h['Content-Type'] = 'application/json'
                req = urllib.request.Request(url + path, data=data, method=method, headers=h)
                with opener.open(req, timeout=10) as response:
                    body = response.read()
                    return body if raw else json.loads(body)
            try:
                deadline = time.time() + 60
                while time.time() < deadline:
                    if proc.poll() is not None:
                        raise AssertionError('Servidor encerrou: ' + ''.join(lines))
                    try:
                        request('/api/session')
                        break
                    except (OSError, ValueError):
                        time.sleep(.2)
                else:
                    raise AssertionError('Servidor não ficou pronto.')
                assert b'EsteiraV' in request('/', raw=True)
                if lan:
                    try:
                        request('/api/projects')
                        raise AssertionError('LAN aceitou acesso não autenticado.')
                    except urllib.error.HTTPError as e:
                        assert e.code == 401
                    code = re.search(r'Pareamento .*?: ([A-F0-9]{6})', ''.join(lines))
                    assert code, 'Código de pareamento não foi exibido.'
                    import http.cookiejar
                    cookies = http.cookiejar.CookieJar()
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(cookies))
                    request('/api/pair', {'code': code[1]})
                p = request('/api/projects', {'name': 'Teste do instalador'})
                request('/api/projects/' + p['id'] + '/media', source.read_bytes(), raw=True,
                        headers={'X-Video-Extension': '.mp4'})
                cut = request('/api/projects/' + p['id'] + '/cuts', {
                    'name': 'Corte português', 'start': .2, 'end': 1.4,
                    'layout':'combined', 'split':.48,
                    'game':{'x':.06,'y':.35,'w':.62,'h':.87},
                    'cam':{'x':.69,'y':.51,'w':.31,'h':.27},
                    'subtitles': [{'start': 0, 'end': 1, 'text': 'Ação e reação!'}]})
                assert abs(cut['game']['y']-.13)<1e-12 and cut['game']['h']==.87
                jid = request('/api/projects/' + p['id'] + '/export', {
                    'ids': [cut['id']], 'requestId': 'package-smoke-test-12345'})['ids'][0]
                deadline = time.time() + 120
                while time.time() < deadline:
                    job = next(j for j in request('/api/jobs') if j['id'] == jid)
                    if job['state'] == 'falhou':
                        raise AssertionError(job['error'])
                    if job['state'] == 'concluído':
                        break
                    time.sleep(.3)
                else:
                    raise AssertionError('Exportação não terminou.')
                output = root / ('lan.mp4' if lan else 'local.mp4')
                output.write_bytes(request('/api/jobs/' + jid + '/file/mp4', raw=True))
                result = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)],
                                        capture_output=True, text=True, check=True)
                meta = json.loads(result.stdout)
                video = next(s for s in meta['streams'] if s['codec_type'] == 'video')
                assert (video['width'], video['height']) == (1080, 1920)
                assert any(s['codec_type'] == 'audio' for s in meta['streams'])
                assert abs(float(meta['format']['duration']) - 1.2) < .2
                assert request('/api/diagnostics')['libass']
            finally:
                if proc.poll() is None:
                    proc.send_signal(signal.CTRL_BREAK_EVENT if os.name == 'nt' else signal.SIGTERM)
                    try:
                        proc.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                        raise AssertionError('Supervisor não encerrou corretamente.')
                assert proc.returncode == 0, ''.join(lines)
            # The kernel lock must be available after shutdown: no orphan worker remains.
            os.environ['ESTEIRA_DATA'] = env['ESTEIRA_DATA']
            check = subprocess.run([sys.executable, '--check-worker-lock'] if getattr(sys, 'frozen', False)
                                   else [sys.executable, '-c', 'from backend.worker import lock_worker; lock=lock_worker()'],
                                   cwd=resource_root(), env=env, capture_output=True, text=True, timeout=15)
            assert check.returncode == 0, check.stdout + check.stderr
            print('Pacote validado: ' + ('LAN pareada' if lan else 'local') + ', upload, legenda, 1080x1920 com áudio e encerramento.', flush=True)


if __name__ == '__main__':
    main()
