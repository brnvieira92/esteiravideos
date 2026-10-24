import argparse, os, subprocess, sys, socket, signal
from contextlib import contextmanager
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--lan',action='store_true'); parser.add_argument('--port',type=int,default=8000); args=parser.parse_args()
    os.environ['ESTEIRA_LAN']='1' if args.lan else '0'
    from .core import FFMPEG, FFPROBE
    for exe in (FFMPEG,FFPROBE):
        try: subprocess.run([exe,'-version'],check=True,stdout=subprocess.DEVNULL)
        except (OSError,subprocess.CalledProcessError): raise SystemExit(f'Instale {exe} e adicione ao PATH. Consulte README.md.')
    root=Path(__file__).resolve().parents[1]
    if not (root/'frontend/dist/index.html').exists(): raise SystemExit('Execute npm ci e npm run build na pasta frontend primeiro.')
    worker=subprocess.Popen([sys.executable,'-m','backend.worker'],cwd=root)
    host='0.0.0.0' if args.lan else '127.0.0.1'
    print(f'EsteiraVídeos: http://localhost:{args.port}')
    if args.lan:
        for ip in sorted({x[4][0] for x in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET)}): print(f'Wi-Fi: http://{ip}:{args.port}')
    try:
        import uvicorn
        class Server(uvicorn.Server):
            @contextmanager
            def capture_signals(self):
                yield
        server=Server(uvicorn.Config('backend.app:app',host=host,port=args.port,access_log=False))
        def shutdown(*_): server.should_exit=True
        signal.signal(signal.SIGTERM,shutdown)
        signal.signal(signal.SIGINT,shutdown)
        server.run()
    finally:
        worker.terminate()
        try: worker.wait(timeout=8)
        except subprocess.TimeoutExpired: worker.kill(); worker.wait()

if __name__=='__main__': main()
