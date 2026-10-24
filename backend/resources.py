"""Resolve read-only application resources in a checkout or PyInstaller bundle."""
import os
import sys
from pathlib import Path


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))


def executable(name):
    override = os.getenv('ESTEIRA_' + name.upper())
    if override:
        return override
    if getattr(sys, 'frozen', False):
        bundled = resource_root() / 'ffmpeg' / (name + ('.exe' if os.name == 'nt' else ''))
        if not bundled.is_file():
            raise RuntimeError(f'Instalação incompleta: {bundled.name} ausente. Reinstale o EsteiraVídeos.')
        return str(bundled)
    return name


def worker_command():
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--worker']
    return [sys.executable, '-m', 'backend.worker']
