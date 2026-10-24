"""Executable entry point. A frozen worker must not recursively start the server."""
import multiprocessing
import sys


def main():
    multiprocessing.freeze_support()
    for stream in (sys.stdout,sys.stderr):
        if stream and hasattr(stream,'reconfigure'): stream.reconfigure(encoding='utf-8')
    if '--check-worker-lock' in sys.argv[1:]:
        from backend.worker import lock_worker
        lock=lock_worker()
        return
    if '--worker' in sys.argv[1:]:
        from backend.worker import main as worker_main
        worker_main()
        return
    if '--smoke-test' in sys.argv[1:]:
        from packaging_smoke import main as smoke_main
        smoke_main()
        return
    from backend.run import main as server_main
    if getattr(sys, 'frozen', False) and '--open-browser' not in sys.argv and '--no-browser' not in sys.argv:
        sys.argv.append('--open-browser')
    server_main()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        if e.code and getattr(sys, 'frozen', False) and sys.stdin and sys.stdin.isatty():
            print(str(e), file=sys.stderr)
            input('Pressione Enter para fechar…')
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        if getattr(sys, 'frozen', False) and sys.stdin and sys.stdin.isatty():
            input('Falha ao iniciar. Copie a mensagem acima. Pressione Enter para fechar…')
        raise
