import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from contextlib import contextmanager
from .resources import resource_root, worker_command


def stop_worker(worker):
    if worker.poll() is not None:
        return
    if os.name == 'nt':
        worker.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        worker.terminate()
    try:
        worker.wait(timeout=10)
    except subprocess.TimeoutExpired:
        worker.kill()
        worker.wait()


def open_when_ready(url, stop):
    # Do not pass the machine's outbound proxy to local readiness checks.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(100):
        if stop.is_set():
            return
        try:
            with opener.open(url + '/api/session', timeout=.5) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, ValueError):
            pass
        stop.wait(.2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lan', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--open-browser', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Porta deve estar entre 1 e 65535.')
    os.environ['ESTEIRA_LAN'] = '1' if args.lan else '0'
    from .core import FFMPEG, FFPROBE
    for exe in (FFMPEG, FFPROBE):
        try:
            subprocess.run([exe, '-version'], check=True, stdout=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            raise SystemExit('FFmpeg/FFprobe indisponível. Reinstale a aplicação ou consulte README.md.')
    if not (resource_root() / 'frontend/dist/index.html').exists():
        raise SystemExit('Interface ausente. Reinstale a aplicação ou execute npm run build em frontend.')
    host = '0.0.0.0' if args.lan else '127.0.0.1'
    # Fail before spawning a worker or opening an unrelated service in the browser.
    with socket.socket() as sock:
        if os.name == 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind((host, args.port))
        except OSError:
            raise SystemExit(f'A porta {args.port} está ocupada. Feche a outra janela do EsteiraVídeos ou use --port 8001.')
    if os.name == 'nt':
        from .windows_job import contain_processes
        contain_processes()
    worker = subprocess.Popen(worker_command(), cwd=resource_root(),
                              **({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {}))
    time.sleep(.3)
    if worker.poll() is not None:
        raise SystemExit('Não foi possível iniciar o trabalhador. Verifique se outra instância está aberta.')
    url = f'http://127.0.0.1:{args.port}'
    print(f'EsteiraVídeos: {url}', flush=True)
    print('Mantenha esta janela aberta. Para encerrar, pressione Ctrl+C.', flush=True)
    if args.lan:
        for ip in sorted({x[4][0] for x in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}):
            print(f'Wi-Fi: http://{ip}:{args.port}', flush=True)
    stop = threading.Event()
    try:
        import uvicorn

        class Server(uvicorn.Server):
            @contextmanager
            def capture_signals(self):
                yield

        server = Server(uvicorn.Config('backend.app:app', host=host, port=args.port, access_log=False))

        def shutdown(*_):
            server.should_exit = True

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, shutdown)
        if args.open_browser and not args.no_browser:
            threading.Thread(target=open_when_ready, args=(url, stop), daemon=True).start()
        server.run()
    finally:
        stop.set()
        stop_worker(worker)


if __name__ == '__main__':
    main()
