# LynowCut
## Menos peso. Mais espaço.

**0.1.0 alpha · Aplicativo desktop · Windows como plataforma de distribuição**

LynowCut é uma primeira implementação funcional de um utilitário local para reduzir o peso de arquivos. A identidade usa o tigre de dentes de sabre enviado pelo Arthur, com laranja queimado, creme e carvão. Não é um site: a interface é um aplicativo Python/Tkinter, empacotável como programa Windows independente.

> Este pacote contém o projeto e os scripts de compilação. Não contém um `.exe` Windows previamente compilado ou testado. O motor foi testado em Linux. A validação da interface e do pacote no Windows ainda é necessária.

### Começar no Windows

1. Instale **Python 3.12 x64** do site oficial https://www.python.org/downloads/windows/ incluindo o Python Launcher.
2. Extraia o ZIP inteiro para uma pasta sua, como `Documentos\LynowCut`. Não execute dentro do ZIP.
3. Clique duas vezes em **INICIAR.bat**. Na primeira execução é necessária internet para instalar Pillow e pikepdf. Não é preciso executar como administrador.
4. Adicione arquivos, selecione a operação, escolha a meta e a pasta de saída.
5. Clique em **Comprimir / processar**. Cada resultado recebe outro nome; o original é preservado.
6. Dê duplo clique na linha para ver tamanho original, tamanho final, meta, observações e caminho salvo.

Para vídeo e áudio, são necessários **FFmpeg e FFprobe**, com os codificadores `libx264`, `aac` e `libmp3lame`. Se eles estiverem ausentes, clique em **Instalar recursos de mídia** na lateral do aplicativo. O LynowCut baixa a build Essentials para Windows, verifica o SHA-256 publicado pelo fornecedor e instala os dois executáveis apenas na pasta local `bin`.

Crie uma pasta `bin` na raiz do projeto e coloque nela `ffmpeg.exe` e `ffprobe.exe`, ou instale as duas ferramentas no PATH. Quando ausentes, imagens/PDF/ZIP continuam funcionando; a operação de mídia mostra o que falta.

### Gerar o executável

Clique em **GERAR-EXE.bat** no Windows. Ele instala as dependências de compilação, executa os testes e usa PyInstaller para gerar:

```
dist/
  LynowCut/
    LynowCut.exe
    _internal/
```

Distribua **a pasta LynowCut inteira**, ou um ZIP dela. Este é um executável portátil com arquivos de suporte; não é um instalador. A máquina que receber a pasta não precisa de Python instalado. Binários de mídia colocados em `bin` antes da compilação serão incluídos. Confira suas condições de redistribuição antes de distribuir uma build com essas ferramentas.

O workflow `.github/workflows/windows.yml` permite gerar o pacote no GitHub Actions: crie um repositório com o conteúdo desta pasta na raiz, abra **Actions → Build Windows alpha → Run workflow** e baixe o artefato após uma execução bem-sucedida. O workflow não publica releases e não foi executado durante esta entrega. Sem FFmpeg no PATH ou no pacote, o teste de mídia é marcado como ignorado.

### Recursos implementados

| Recurso | Comportamento nesta alpha |
|---|---|
| Porcentagem personalizada | Redução de 1% a 95% sobre os bytes de cada original; 30% significa manter até aproximadamente 70% do peso original. |
| Tamanho máximo | Meta em MB decimais por arquivo: 10 MB = 10.000.000 bytes. Selecione “Tamanho máximo”; nesse modo a porcentagem é ignorada. |
| Imagens | JPG, PNG, WebP, BMP e TIFF de um quadro; saída WebP, JPEG ou PNG. Dimensões preservadas; orientação EXIF aplicada. |
| Busca de qualidade | JPEG/WebP: busca uma qualidade alta que caiba na meta, respeitando o limite mínimo escolhido. Se isso não bastar e “Ajustar resolução” estiver ativo, reduz as dimensões proporcionalmente em etapas para perseguir metas agressivas. |
| Transparência | WebP/PNG mantêm canal alfa. JPEG é recusado para imagens com transparência. |
| PDF | Otimização de streams e estrutura, sem rasterizar páginas ou recomprimir imagens incorporadas. Mantém texto selecionável. |
| Documentos | Word (`DOCX/DOCM`), PowerPoint (`PPTX/PPTM`), Excel (`XLSX/XLSM`), OpenDocument e EPUB são recompactados; imagens JPEG/PNG internas são otimizadas quando há ganho. A estrutura e a extensão original são preservadas. |
| Vídeo | MP4/MOV/MKV/AVI/WebM/M4V → MP4 H.264/AAC, orçamento de bitrate e duas etapas de codificação. |
| Áudio | MP3/WAV/FLAC/AAC/OGG/M4A → MP3; meta de bitrate calculada a partir da duração. |
| Recorte de mídia | Informe início e duração em segundos. Duração vazia mantém o restante. Usa recodificação. |
| Extração de áudio | Operação própria para salvar a primeira faixa de áudio em MP3. |
| ZIP | Um ZIP por arquivo, sem perdas; serve para dados brutos e documentos. Não é um extrator de arquivos ZIP. |
| Processamento em lote | Fila sequencial, com falha isolada por arquivo. Campos são capturados ao iniciar. |
| Comparação | Prévia lado a lado de imagens processadas; ajustada à janela, sem medição objetiva da qualidade visual. |
| Relatório | CSV com tamanhos em bytes, meta, status e destino de cada resultado processado com sucesso. |
| Cancelamento | Interrompe processos de mídia; imagens/PDF aguardam o ponto seguro seguinte. Resultados já concluídos permanecem. |
| Proteção dos originais | Nunca substitui a entrada. Saídas existentes ganham um sufixo numérico. |
| Sem ganho | Na compressão sem recorte, resultados iguais ou maiores são descartados. Conversões de áudio, ZIP e recortes podem ser salvos maiores. |

### O que a meta significa

Não existe um algoritmo capaz de garantir qualquer redução para qualquer arquivo sem alterar seu conteúdo. JPEG, MP4 e muitos PDFs já contêm dados comprimidos. O programa tenta a meta e mede o resultado; ele nunca mostra sucesso de meta sem comparar os bytes reais.

- **Meta atingida:** tamanho final menor ou igual à meta.
- **Meta não atingida:** resultado útil foi salvo, mas continua acima da meta.
- **Sem ganho:** o resultado da compressão não ficou menor; nenhuma cópia foi publicada.
- **Erro:** arquivo incompatível, inválido, ferramenta ausente ou outra falha. Duplo clique mostra o detalhe.

Imagens não são redimensionadas automaticamente. Um limite de qualidade mais alto pode impedir a redução desejada. PNG é otimizado sem perda de pixels; PDF é otimizado estruturalmente. Esses dois formatos e ZIP podem não alcançar a porcentagem escolhida. Em mídia, o orçamento reserva uma margem para o contêiner, mas a saída ainda é medida e a meta não é garantida.

### Limites que você deve conhecer

- A interface ainda não foi validada visualmente em Windows; não há certificação de compatibilidade com todas as instalações Windows 10/11.
- Não inclui instalador, atualização automática, assinatura digital de código, ativação comercial, conta ou pagamentos.
- Vídeo preserva a primeira faixa de vídeo não marcada como capa e a primeira faixa de áudio. Outras faixas, legendas, capítulos quando removidos e anexos não são preservados. HDR/10-bit pode perder características na conversão para YUV420p de 8 bits; não use esta alpha como fluxo HDR profissional.
- PDF com indicação comum de assinatura digital ou criptografado é recusado. A checagem de assinatura é conservadora e não substitui um validador; não processe documentos assinados nesta alpha. PDF/A, acessibilidade e formulários precisam de verificação específica após edição.
- “Remover metadados” remove campos comuns de EXIF/document info/XMP e tags de contêiner. Não remove nomes ou dados visíveis, comentários de documento, todos os anexos ou todos os identificadores internos. Não garante anonimização. Perfis ICC de imagens são mantidos quando disponíveis para reduzir alterações de cor.
- TIFF multipágina e imagens animadas são recusados para evitar descartar quadros silenciosamente.
- Arquivos grandes podem exigir bastante RAM, armazenamento temporário e tempo de CPU. O lote sequencial limita concorrência, mas não impõe um teto de RAM.
- O aplicativo não usa rede no processamento. A instalação das dependências e a obtenção de ferramentas exigem conexão.
- Não possui “limpador de RAM”, limpeza do Windows, apagamento de temporários do usuário, deduplicação ou extração arbitrária de dados brutos.

### Desenvolvimento e testes

```
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
```

Os 11 testes cobrem metas atingidas/não atingidas, preservação do original e dimensões, colisões de nomes, transparência, recusa de animações, remoção de EXIF comum, cancelamento antes do início, ZIP reversível, preservação de páginas/conteúdo PDF, recusa de PDF com indicador de assinatura, entradas numéricas inválidas e vídeo/extração de áudio. O teste de mídia é ignorado se FFmpeg/FFprobe não estão disponíveis.

Nesta entrega, os 11 passaram em Linux com Pillow 12.3.0, pikepdf 10.17.0 e FFmpeg instalado. Isso valida o motor nesses casos, não a distribuição Windows nem a qualidade visual em todos os arquivos.

### Estrutura

- `lynowcut/engine.py`: processamento independente da interface.
- `lynowcut/app.py`: interface desktop e fila com worker em segundo plano.
- `assets/`: identidade enviada pelo usuário e ícone derivado.
- `tests/`: testes com arquivos gerados, sem dados privados.
- `LynowCut.spec`: empacotamento para Windows.
- `PRODUTO.md`: posicionamento, diferenciais e prioridades de evolução.

### Referências técnicas

- Pillow: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
- pikepdf: https://pikepdf.readthedocs.io/en/stable/api/main.html
- FFmpeg: https://ffmpeg.org/ffmpeg.html
- PyInstaller: https://pyinstaller.org/en/stable/
