"""Explicit diagnostic mode exercised against the extracted Windows distribution."""
import json
from pathlib import Path
import subprocess


def run(folder):
    from PIL import Image
    import pikepdf
    from pillow_heif import from_pillow
    from PySide6.QtWidgets import QApplication
    from .app import MainWindow
    from .engine import Options, binary, process, resource

    root = Path(folder).resolve(); root.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    window = MainWindow(); window.show(); app.processEvents()
    for name in ('assets/fonts/Inter.ttf', 'assets/lynowcut.ico', 'assets/mascot-ui.png'):
        assert resource(name).is_file(), name
    source = root / 'photo.bmp'
    Image.effect_noise((640, 480), 70).convert('RGB').save(source)
    checked = ['Qt window', 'assets']
    for fmt in ('WebP', 'JPEG', 'PNG', 'AVIF'):
        result = process(source, root / 'out', Options(image_format=fmt))
        assert result.output
        with Image.open(result.output) as image: image.load()
        checked.append(fmt)
    heic = root / 'photo.heic'
    from_pillow(Image.open(source)).save(heic)
    assert process(heic, root / 'out', Options()).output
    checked.append('HEIC')
    pdf = root / 'photo.pdf'
    Image.open(source).save(pdf, 'PDF', quality=99)
    result = process(pdf, root / 'out', Options(reduction=80, flatten_pdf=True))
    assert result.output and 'visualmente' in result.note
    with pikepdf.open(result.output) as document: assert len(document.pages) == 1
    checked.append('PDF structural and visual')
    video = root / 'video.avi'
    subprocess.run([binary('ffmpeg'), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=160x120:rate=15', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '2', '-c:v', 'mpeg4', '-q:v', '2', '-c:a', 'pcm_s16le', str(video)], check=True, timeout=60)
    assert process(video, root / 'out', Options(max_mb=.12)).output
    assert process(video, root / 'out', Options(action='Extrair áudio', max_mb=.05)).output
    checked += ['H.264/AAC', 'MP3']
    window.close(); app.processEvents()
    (root / 'self-test.json').write_text(json.dumps({'passed': checked}, indent=2), encoding='utf-8')
