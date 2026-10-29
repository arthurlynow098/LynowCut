from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files
root = Path(SPECPATH)
datas = [(str(root/'assets'), 'assets')]
for package in ('pypdfium2', 'pypdfium2_raw', 'pikepdf', 'pillow_heif', 'PIL', 'PySide6', 'shiboken6'):
    datas += collect_data_files(package, includes=['**/LICENSE*', '**/COPYING*', '**/NOTICE*', '**/licenses/**'])
# FFmpeg is optional and downloaded by the application when the user enables
# audio/video features. Keeping it out of the base package makes the primary
# LynowCut download dramatically smaller.
a = Analysis([str(root/'main.py')], pathex=[str(root)], binaries=[], datas=datas, hiddenimports=['pikepdf', 'PIL.WebPImagePlugin', 'PIL.AvifImagePlugin', 'pillow_heif', 'pypdfium2'], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf', 'PySide6.QtQuick', 'PySide6.QtQml'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LynowCut', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, icon=str(root/'assets'/'lynowcut.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LynowCut')
