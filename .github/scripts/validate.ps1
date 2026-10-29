$ErrorActionPreference = 'Stop'
function Invoke-Python {
    & python @args
    if ($LASTEXITCODE -ne 0) { throw "Python failed: $args" }
}
New-Item -ItemType Directory -Force release-output | Out-Null
Invoke-Python -c "from pathlib import Path; from lynowcut.media_install import install; print(install(Path('.').resolve()))"
$mediaVersion = (python -c "from lynowcut.media_install import VERSION; print(VERSION)").Trim()
$env:PATH = "${PWD}\media-$mediaVersion;$env:PATH"
Invoke-Python -c "from lynowcut.engine import binary; print(binary('ffmpeg')); print(binary('ffprobe'))"
$env:LYNOWCUT_REQUIRE_MEDIA = '1'
if (-not $env:LIBREOFFICE -or -not (Test-Path -LiteralPath $env:LIBREOFFICE)) {
    throw 'LibreOffice must be installed for the document compatibility gate.'
}
Invoke-Python -m unittest discover -s tests -v
Invoke-Python -m PyInstaller --noconfirm --clean LynowCut.spec
Copy-Item LICENSE, THIRD-PARTY-NOTICES.md, README.md, LEIA-ME-PRIMEIRO.md -Destination dist\LynowCut
Invoke-Python -m piplicenses --format=json --with-license-file --with-urls --output-file=dist/LynowCut/DEPENDENCY-LICENSES.json
Invoke-Python -m pip freeze --all | Out-File -Encoding utf8 dist\LynowCut\BUILD-DEPENDENCIES.txt
$revision = (git rev-parse HEAD).Trim()
@{commit=$revision; python=(python --version); runner=$env:ImageOS; runnerVersion=$env:ImageVersion; mediaVersion=$mediaVersion; signed=$false} | ConvertTo-Json | Set-Content -Encoding utf8 dist\LynowCut\BUILD-INFO.json
Compress-Archive -Path dist\LynowCut -DestinationPath release-output\LynowCut-Windows-x64.zip -CompressionLevel Optimal
Expand-Archive release-output\LynowCut-Windows-x64.zip release-package
$exe = (Resolve-Path release-package\LynowCut\LynowCut.exe).Path
$diagnostics = Join-Path $PWD 'release-output\smoke-test'
$env:QT_QPA_PLATFORM = 'offscreen'
$env:PYTHONHOME = $null; $env:PYTHONPATH = $null
$process = Start-Process -FilePath $exe -ArgumentList @('--self-test', "`"$diagnostics`"") -PassThru -WindowStyle Hidden
if (-not $process.WaitForExit(180000)) { $process.Kill(); throw 'Packaged application timed out.' }
if ($process.ExitCode -ne 0 -or -not (Test-Path "$diagnostics\self-test.json")) { throw 'Packaged application self-test failed.' }
$hash = (Get-FileHash release-output\LynowCut-Windows-x64.zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  LynowCut-Windows-x64.zip" | Set-Content -Encoding ascii release-output\SHA256SUMS.txt
@"
## Windows alpha — validação e limitações

Commit: $revision

Pacote portátil x64: extraia o ZIP completo e abra LynowCut\LynowCut.exe. Não exige Python.
Testes do motor, documentos reais com LibreOffice e verificação do executável extraído foram executados antes desta publicação. Consulte BUILD-INFO.json e BUILD-DEPENDENCIES.txt no pacote.

- Pré-lançamento experimental; preserve seus originais e confira os resultados.
- PDFs preservam texto, links e formulários por padrão. Achatar PDF é opcional e destrutivo.
- Imagens podem perder qualidade e resolução; a meta de tamanho não é garantida.
- Documentos: imagens internas podem perder qualidade; propriedades pessoais não são removidas. Documentos com indicadores de assinatura são recusados.
- ZIP: um pacote por arquivo, sem extração ou agrupamento de fila.
- Áudio/vídeo exige instalação opcional do FFmpeg $mediaVersion, com versão e hash fixos. Não está incluído no ZIP.
- Vídeo conserva apenas a primeira faixa de vídeo/áudio; legendas, anexos e características HDR podem ser perdidos.
- Sem assinatura Authenticode: o Windows pode mostrar aviso de editor desconhecido.

Confira SHA256SUMS.txt antes de executar. Licenças de terceiros e inventário acompanham o pacote.
"@ | Set-Content -Encoding utf8 release-output\RELEASE-NOTES.md
