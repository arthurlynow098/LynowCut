@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto error
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean LynowCut.spec
if errorlevel 1 goto error
echo Pronto: dist\LynowCut\LynowCut.exe
 echo Distribua a pasta LynowCut inteira, e nao apenas o executavel.
pause
exit /b 0
:error
echo Falha na compilacao. Confira a mensagem acima.
pause
exit /b 1
