"""Versioned, bounded and transactional optional Windows media installation."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import urllib.request
import zipfile

from .engine import check_cancel

VERSION = '9.0.2'
URL = f'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-{VERSION}-essentials_build.zip'
SHA256 = '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba'
MAX_DOWNLOAD = 250 * 1024 * 1024
MAX_BINARY = 300 * 1024 * 1024


def install(root, event=None, *, opener=urllib.request.urlopen, runner=subprocess.run):
    event = event or threading.Event()
    root = Path(root)
    check_cancel(event)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f'media-{VERSION}'
    if target.exists():
        raise RuntimeError('A pasta desta versão de mídia já existe. Remova-a para reinstalar.')
    with tempfile.TemporaryDirectory(prefix='.media-', dir=root) as temp:
        temp = Path(temp)
        archive = temp / 'download.zip'
        digest = hashlib.sha256()
        total = 0
        with opener(URL, timeout=30) as response, archive.open('wb') as output:
            while True:
                check_cancel(event)
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD:
                    raise RuntimeError('Download de mídia excedeu o limite permitido.')
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != SHA256:
            raise RuntimeError('A verificação SHA-256 do pacote de mídia falhou.')
        stage = temp / 'ready'
        stage.mkdir()
        with zipfile.ZipFile(archive) as package:
            for name in ('ffmpeg.exe', 'ffprobe.exe'):
                matches = [i for i in package.infolist() if i.filename.replace('\\', '/').endswith('/bin/' + name)]
                if len(matches) != 1 or matches[0].file_size > MAX_BINARY:
                    raise RuntimeError('Pacote de mídia inválido.')
                check_cancel(event)
                with package.open(matches[0]) as source, (stage / name).open('wb') as output:
                    while chunk := source.read(1024 * 1024):
                        check_cancel(event)
                        output.write(chunk)
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        for name in ('ffmpeg', 'ffprobe'):
            check_cancel(event)
            result = runner([str(stage / (name + '.exe')), '-version'], check=True, capture_output=True, timeout=15, creationflags=flags)
            if VERSION not in result.stdout.decode(errors='replace').splitlines()[0]:
                raise RuntimeError('Versão inesperada dos recursos de mídia.')
        result = runner([str(stage / 'ffmpeg.exe'), '-hide_banner', '-encoders'], check=True, capture_output=True, timeout=15, creationflags=flags)
        if not all(codec in result.stdout.decode(errors='replace') for codec in ('libx264', 'aac', 'libmp3lame')):
            raise RuntimeError('Codificadores obrigatórios ausentes.')
        check_cancel(event)
        stage.rename(target)
    return target
