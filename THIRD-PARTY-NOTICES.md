# Componentes de terceiros

A licença MIT em LICENSE cobre o código LynowCut. Cada dependência mantém suas próprias condições. A distribuição gerada contém DEPENDENCY-LICENSES.json com versões, URLs e textos de licença extraídos dos pacotes instalados; inclui também ferramentas de build/teste, que não necessariamente são incorporadas ao executável. BUILD-DEPENDENCIES.txt registra o ambiente completo.

Componentes principais a conferir ao distribuir:

- Python: licença PSF e avisos das bibliotecas incorporadas.
- PySide6/Qt e Shiboken: LGPL/GPL ou licença comercial, conforme o componente. A distribuição usa bibliotecas dinâmicas; preserve arquivos e avisos, permita substituição das bibliotecas nos termos aplicáveis e disponibilize as informações/fontes correspondentes exigidas pela licença escolhida. Consulte https://doc.qt.io/qtforpython-6/licenses.html.
- Pillow e pillow-heif: licenças próprias e dos codecs nativos incluídos nas wheels. Não remova os avisos fornecidos pelos pacotes.
- pikepdf/qpdf e pypdfium2/PDFium: preserve licenças e avisos dos componentes nativos. Os hooks do empacotador e o inventário devem ser conferidos a cada atualização.
- PyInstaller: GPL com exceção de distribuição do bootloader; consulte o texto distribuído pelo projeto.
- Inter: SIL Open Font License em assets/fonts/OFL.txt, incluída junto dos assets.

FFmpeg é opcional e não integra o ZIP principal. A aplicação baixa a build Essentials versionada de Gyan, que pode conter componentes GPL. Página da build e fontes/instruções: https://www.gyan.dev/ffmpeg/builds/. Condições do FFmpeg: https://ffmpeg.org/legal.html. Distribuições personalizadas que incluam FFmpeg devem incluir suas licenças e cumprir os requisitos de fonte correspondentes; esta nota não concede uma licença alternativa.

Antes de uma distribuição assinada, revise os arquivos efetivamente incorporados e preserve os avisos nativos, além do inventário de pacotes Python. Não declare que todo o pacote é MIT.
