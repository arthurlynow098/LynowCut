from pathlib import Path
root = Path(SPECPATH)
datas = [(str(root/'assets'), 'assets')]
# FFmpeg is optional and downloaded by the application when the user enables
# audio/video features. Keeping it out of the base package makes the primary
# LynowCut download dramatically smaller.
a = Analysis([str(root/'main.py')], pathex=[str(root)], binaries=[], datas=datas, hiddenimports=['pikepdf', 'PIL.WebPImagePlugin', 'PIL.AvifImagePlugin', 'pillow_heif', 'pypdfium2'], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf', 'PySide6.QtQuick', 'PySide6.QtQml'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LynowCut', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, icon=str(root/'assets'/'lynowcut.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LynowCut')
