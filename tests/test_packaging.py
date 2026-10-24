from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
from backend import resources
from backend.run import stop_worker


def test_checkout_resources():
    assert (resources.resource_root() / 'frontend/package.json').exists()
    assert resources.worker_command() == [sys.executable, '-m', 'backend.worker']


def test_frozen_resources_and_worker(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    monkeypatch.delenv('ESTEIRA_FFMPEG', raising=False)
    assert resources.resource_root() == tmp_path
    assert resources.worker_command() == [sys.executable, '--worker']
    with pytest.raises(RuntimeError, match='Instalação incompleta'):
        resources.executable('ffmpeg')
    folder = tmp_path / 'ffmpeg'
    folder.mkdir()
    name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
    (folder / name).write_bytes(b'packaged resource')
    assert resources.executable('ffmpeg') == str(folder / name)
    monkeypatch.setenv('ESTEIRA_FFMPEG', '/explicit/ffmpeg')
    assert resources.executable('ffmpeg') == '/explicit/ffmpeg'


def test_stop_finished_worker():
    # A finished worker must not signal a possibly recycled PID.
    stop_worker(SimpleNamespace(poll=lambda: 0))
