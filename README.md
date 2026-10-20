# LynowCut

**Menos peso. Mais espaço.**

O LynowCut é um aplicativo de desktop para Windows que comprime imagens, vídeos, áudios, PDFs e documentos localmente. Os arquivos não precisam ser enviados para uma nuvem e os originais são preservados.

## Recursos

- Redução por porcentagem ou tamanho máximo.
- Compressão de imagens com saída em JPEG, PNG, WebP e AVIF.
- Otimização de PDFs e documentos modernos do Office.
- Compressão de vídeo e extração de áudio com FFmpeg opcional.
- Remoção de metadados pessoais.
- Criação de arquivos ZIP.
- Fila visual, comparação e relatório CSV.

## Download

Baixe a versão mais recente em [GitHub Releases](https://github.com/arthurlynow098/LynowCut/releases/latest).

Depois do download, extraia todo o conteúdo de `LynowCut-Windows-x64.zip` e abra `LynowCut.exe`. A pasta `_internal` deve permanecer ao lado do executável.

## Rodar pelo código-fonte

Requer Python 3.12 no Windows.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Também é possível usar `INICIAR.bat`.

## Gerar o aplicativo

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean LynowCut.spec
```

O resultado será criado em `dist\LynowCut`. Distribua a pasta inteira, não apenas o executável.

## Áudio e vídeo

O pacote principal não inclui o FFmpeg para manter o download menor. O próprio aplicativo oferece a instalação opcional dos recursos de áudio e vídeo.

## Site

A landing page está em [`site/dist`](site/dist). Ela segue o padrão visual da família Lynow, com a identidade laranja e o tigre do LynowCut.

## Licença

Distribuído sob a [licença MIT](LICENSE).
