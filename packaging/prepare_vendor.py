"""Download pinned, verified Windows FFmpeg. Never installs into PATH."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import ssl
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'build/vendor'


def main():
    config = json.loads((ROOT / 'packaging/ffmpeg.json').read_text())
    VENDOR.mkdir(parents=True, exist_ok=True)
    archive = VENDOR / config['file']
    if not archive.exists() or hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest() != config['sha256']:
        print('Baixando FFmpeg Windows (~200 MB), validado por SHA256 fixado no repositório.', flush=True)
        temp = archive.with_suffix('.download')
        context = ssl.create_default_context()
        with urllib.request.urlopen(config['url'], context=context, timeout=120) as r, temp.open('wb') as f:
            shutil.copyfileobj(r, f, 1024 * 1024)
        if hashlib.file_digest(temp.open('rb'), 'sha256').hexdigest() != config['sha256']:
            temp.unlink()
            raise RuntimeError('Checksum FFmpeg incorreto. Nenhum executável será usado.')
        temp.replace(archive)
    licenses = VENDOR / 'licenses'
    licenses.mkdir(exist_ok=True)
    ffmpeg = VENDOR / 'ffmpeg'
    ffmpeg.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for exe in ('ffmpeg.exe', 'ffprobe.exe'):
            names = [name for name in z.namelist() if name.endswith('/bin/' + exe)]
            if len(names) != 1:
                raise RuntimeError('Arquivo FFmpeg não tem a estrutura esperada.')
            with z.open(names[0]) as src, (ffmpeg / exe).open('wb') as dst:
                shutil.copyfileobj(src, dst)
        # Retain every license, README, build configuration and dependency notice shipped upstream.
        for name in z.namelist():
            if name.endswith('/') or '/bin/' in name:
                continue
            parts = Path(name).parts[1:]
            if not parts or '..' in parts:
                raise RuntimeError('Caminho inseguro no pacote FFmpeg.')
            target = licenses / 'ffmpeg' / Path(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)
    (licenses / 'ffmpeg-provenance.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    shutil.copyfile(Path(sys.base_prefix) / 'LICENSE.txt', licenses / 'Python-LICENSE.txt')
    records = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata['Name']
        records.append({'name': name, 'version': dist.version, 'license': dist.metadata.get('License-Expression') or dist.metadata.get('License'), 'home': dist.metadata.get('Home-page')})
        for file in dist.files or []:
            if any(part.lower().startswith(('license', 'copying', 'notice')) for part in file.parts):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    dest = licenses / 'python-packages' / name / Path(*file.parts)
                    if '..' in file.parts:
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
    (licenses / 'python-packages.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    for package in (ROOT / 'frontend/node_modules').rglob('package.json'):
        if 'node_modules' not in str(package):
            continue
        try:
            meta = json.loads(package.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        name = meta.get('name', '').replace('/', '__').replace('@', '')
        if not name:
            continue
        for file in package.parent.iterdir():
            if file.is_file() and file.name.lower().startswith(('license', 'copying', 'notice')):
                dest = licenses / 'javascript' / name / file.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file, dest)
    shutil.copyfile(ROOT / 'packaging/THIRD-PARTY.txt', licenses / 'THIRD-PARTY.txt')


if __name__ == '__main__':
    main()
