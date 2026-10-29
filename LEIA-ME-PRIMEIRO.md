# LynowCut — guia da alpha

O pacote Windows publicado é portátil e experimental. A versão 0.1.0-alpha original tem limitações adicionais descritas nas notas da Release. As correções posteriores só estarão no binário de uma nova tag; atualizar a documentação não altera um ZIP já publicado.

## Usar o pacote Windows

1. Abra [Releases](https://github.com/arthurlynow098/LynowCut/releases) e leia as notas da versão desejada.
2. Baixe `LynowCut-Windows-x64.zip` e, quando disponível, `SHA256SUMS.txt`.
3. Confira o hash com `Get-FileHash .\LynowCut-Windows-x64.zip -Algorithm SHA256`.
4. Extraia tudo para uma pasta com permissão de escrita, como `Documentos\LynowCut`.
5. Abra `LynowCut\LynowCut.exe`. A pasta `_internal` precisa permanecer ao lado dele. Python não é necessário.

O aplicativo ainda não possui assinatura Authenticode. O Windows pode exibir aviso de editor desconhecido. O checksum confere o download; não equivale a uma assinatura do editor.

## Capacidades e limites

A referência comum ao README, ao site e a este guia é [docs/CAPABILITIES.md](docs/CAPABILITIES.md). Confira os resultados antes de descartar suas cópias de trabalho.

- As metas usam MB decimais (1 MB = 1.000.000 bytes) e são objetivos, não garantias. O resultado mostra a medição real.
- A redução de resolução de imagens vem ativada e pode ser desligada. Compressão com perdas modifica pixels mesmo sem alterar dimensões.
- PDF recebe otimização estrutural por padrão. A opção separada **Achatar PDF** vem desligada e pede confirmação: pode remover texto pesquisável, links, formulários e acessibilidade. Ela não deve ser usada para documentos cuja estrutura precisa ser preservada.
- Documentos modernos mantêm o contêiner, mas JPEGs internos podem perder qualidade. Propriedades pessoais do documento não são removidas. Indicadores conhecidos de assinatura provocam recusa; isso não é uma validação completa de assinaturas.
- ZIP cria um pacote por arquivo, sem reunir a fila em um pacote e sem extrair ZIPs existentes.
- Resultados sem ganho são descartados na compressão sem recorte. ZIP, extração de áudio e recortes podem produzir arquivos maiores.
- A saída usa nomes novos; os arquivos de entrada não são sobrescritos. Cancelamento aguarda o próximo ponto seguro e mantém resultados já concluídos.

## Áudio e vídeo opcionais

O ZIP principal não inclui FFmpeg. Pela interface, instale os recursos de mídia. A instalação baixa a versão Windows x64 fixada em `lynowcut/media_install.py`, confere seu SHA-256 previamente registrado, valida versão/codificadores e ativa os dois executáveis juntos em `media-<versão>` ao lado do aplicativo. É necessário acesso à internet e permissão de escrita nessa pasta. O botão permite cancelar o download; uma leitura de rede pode aguardar até o timeout de 30 segundos.

Para instalação manual, coloque `ffmpeg.exe` e `ffprobe.exe` em `bin` ao lado do programa ou no PATH. Precisam oferecer `libx264`, `aac` e `libmp3lame`. Arquivos em `bin` não são incluídos automaticamente pelo PyInstaller. Não redistribua ferramentas externas sem observar suas licenças.

Vídeo é convertido para MP4 H.264/AAC; áudio para MP3. Apenas a primeira faixa de vídeo e de áudio é usada. Legendas e anexos não são preservados. HDR/10-bit pode perder características na conversão para YUV420p de 8 bits. Início e duração são informados em segundos. Não use esta alpha como fluxo de preservação profissional.

## Executar o código-fonte

Requer Windows x64 e Python 3.12.14 para reproduzir o ambiente de validação.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`INICIAR.bat` é uma alternativa para desenvolvimento. Ele não é necessário para quem baixou o executável.

## Testar e empacotar

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean LynowCut.spec
```

O teste de mídia pode ser ignorado num ambiente local sem FFmpeg. Nos workflows de validação/publicação ele é obrigatório, com versão fixa, e documentos são convertidos para PDF pelo LibreOffice como verificação independente. Os testes incluem preservação de originais, colisões, metas inalcançáveis, transparência, assinaturas, consentimento de PDF, cancelamento, ZIP reversível e falhas de instalação. Não equivalem a uma garantia de qualidade para todos os arquivos.

`windows.yml` roda em push, pull request e manualmente. `release.yml` só publica uma tag existente depois de executar a mesma validação, criar e extrair o ZIP e abrir o aplicativo empacotado em modo diagnóstico. Esse modo é `LynowCut.exe --self-test <pasta-de-diagnóstico>`; não substitui avaliação visual humana.

A pasta inteira `dist\LynowCut` deve ser distribuída. O pacote inclui licença do projeto, inventário/licenças das dependências e informações do build. É um build automatizado com versões fixadas; não se afirma reprodução idêntica byte a byte. O sistema Windows e a ferramenta de compatibilidade podem receber atualizações.

## Publicar e assinar

Consulte [docs/RELEASING.md](docs/RELEASING.md) para atualizar o lock, validar uma tag, produzir notas e adotar Authenticode. A licença MIT do código LynowCut não substitui licenças de terceiros; consulte [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
