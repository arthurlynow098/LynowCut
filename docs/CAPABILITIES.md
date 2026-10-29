# Capacidades e limites da alpha

Esta matriz descreve o código atual. O ZIP de uma Release corresponde à sua tag, não à branch main.

| Operação | Suporte | Limitações |
|---|---|---|
| Imagens | JPEG, PNG, WebP, BMP, TIFF, GIF estático, AVIF e HEIC/HEIF; saída WebP/JPEG/PNG/AVIF | Animações/múltiplas páginas recusadas; JPEG não aceita transparência; perdas e redimensionamento proporcional opcional, ativado por padrão; codec HEIF depende da build |
| PDF padrão | Otimização estrutural; preserva texto e objetos | Meta não garantida; PDFs criptografados ou com indicadores comuns de assinatura são recusados; PDF/A e acessibilidade precisam de validação específica |
| Achatar PDF | Redução visual opcional, desligada por padrão e com confirmação | Pode remover texto pesquisável, links, formulários e acessibilidade; não é preservação semântica |
| Documentos | DOCX/DOCM/PPTX/PPTM/XLSX/XLSM/ODT/ODS/ODP/EPUB, recompressão do contêiner e imagens nos diretórios reconhecidos | JPEG interno pode perder qualidade; ganho não garantido; propriedades pessoais permanecem; documentos com indicadores conhecidos de assinatura recusados; validação de compatibilidade automatizada cobre DOCX/PPTX/XLSX/ODT, demais formatos são experimentais |
| Criar ZIP | Qualquer arquivo, sem alterar seus bytes | Um ZIP por arquivo; não agrupa fila nem extrai/reotimiza arquivos ZIP existentes |
| Vídeo | FFmpeg opcional, MP4 H.264/AAC, recorte | Primeira faixa de vídeo/áudio; sem legendas/anexos; HDR pode perder características; meta aproximada medida ao final |
| Áudio | FFmpeg opcional, MP3 e extração de áudio | Primeira faixa; compressão com perdas; meta mínima depende da duração |
| Metadados | EXIF comum de imagens, informações PDF e metadados/capítulos de mídia quando selecionado | Não remove propriedades de documentos; perfis ICC de imagens preservados; não é ferramenta de anonimização |
| Saída e cancelamento | Nomes exclusivos, entrada preservada, limpeza de saídas incompletas | Resultados concluídos antes de cancelar permanecem; operações nativas aguardam ponto seguro |
| Plataforma | Pacote portátil Windows x64 | Sem instalador, atualização automática ou Authenticode; codecs opcionais precisam de rede para instalação guiada |

Metas são calculadas em bytes, com MB decimais. “Meta não atingida” é um resultado esperado quando o limite não é viável. “Sem ganho” evita salvar compressões maiores sem recorte. Confirme aparência, conteúdo e propriedades antes de usar uma saída.
