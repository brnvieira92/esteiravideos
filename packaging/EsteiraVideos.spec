# Run from repository root: pyinstaller packaging/EsteiraVideos.spec --noconfirm --clean
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata
root = Path(SPECPATH).parent
vendor = root / 'build' / 'vendor'
datas = [(str(root / 'frontend' / 'dist'), 'frontend/dist'),
         (str(vendor / 'licenses'), 'licenses')]
for package in ('fastapi', 'starlette', 'uvicorn', 'pydantic', 'anyio'):
    datas += copy_metadata(package)
a = Analysis([str(root / 'packaging' / 'launcher.py')],
             pathex=[str(root), str(root / 'packaging')],
             binaries=[(str(vendor / 'ffmpeg' / name), 'ffmpeg') for name in ('ffmpeg.exe', 'ffprobe.exe')],
             datas=datas,
             hiddenimports=collect_submodules('uvicorn') + ['backend.app','backend.worker','packaging_smoke'],
             excludes=['pytest', 'httpx', 'tkinter'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EsteiraVideos',
          console=True, upx=False, icon=str(root / 'packaging' / 'app.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='EsteiraVideos')
