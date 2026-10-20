# LynowCut — direção do produto

## Proposta

**“Escolha quanto o arquivo pode pesar. Veja o que muda. Salve uma cópia menor.”**

O cliente compra uma tarefa resolvida: enviar uma apresentação, anexar um PDF, entregar uma pasta de fotos ou economizar armazenamento. Um posicionamento mais forte que “compressor para tudo” é **preparar arquivos para caber no destino, com controle visível sobre a qualidade**.

O nome adotado é **LynowCut**, conforme a marca escrita e a linha LynowMic. A menção “Little Cut” na fala foi interpretada como referência a esse nome; pode ser alterado antes da distribuição.

## Identidade

O tigre de dentes de sabre associa o nome Cut à ideia de corte preciso. Aproveitar a ilustração enviada como elemento de marca, sem transformar todas as telas em uma vitrine da mascote. Base creme `#F6F3EC`, carvão `#242824` e laranja `#C84D24`. Textos curtos em português, informação de tamanho sempre visível e estados que expliquem o resultado.

A alpha implementa essa direção em Tkinter para fornecer um motor real e um caminho simples até o executável. O LynowMic usa C#/WPF; este projeto não reutiliza o código nem reproduz sua arquitetura. Se a continuidade técnica da linha for prioritária, migrar a camada visual para WPF e manter o comportamento de compressão documentado como referência.

## Diferenciais a desenvolver

Estas são propostas; não são recursos já entregues nem alegações de exclusividade de mercado.

| Prioridade | Recurso | Benefício concreto |
|---|---|---|
| 1 | Meta de tamanho com orçamento de qualidade | Usuário decide o limite; programa explica se exige reduzir resolução ou qualidade. A alpha já mede a meta e busca qualidade de imagem. |
| 2 | Comparação sincronizada com zoom de 100% | Decisão baseada em legibilidade e detalhes; alpha tem comparação simples lado a lado. |
| 3 | Orçamento de pasta inteira | “Esta pasta precisa caber em 500 MB”; distribuir a redução entre arquivos, evitando sacrificar todos igualmente. |
| 4 | Amostra antes do processamento longo | Testar um trecho de vídeo e estimar tempo/qualidade antes de codificar o vídeo inteiro. |
| 5 | Receitas salvas | “Anexo de 10 MB”, “Fotos do catálogo”, “Vídeo para enviar”; limites editáveis, sem depender de supostos limites fixos de plataformas. |
| 6 | Pasta monitorada e integração ao Explorer | Fluxo de trabalho de quem processa arquivos diariamente, com opt-in e destino explícito. |
| 7 | PDF adaptativo | Recompressão de imagens incorporadas, protegendo texto, formulários e acessibilidade. Exige um motor e testes adicionais. |
| 8 | Duplicatas com revisão | Localizar cópias idênticas por hash; mostrar e pedir ação explícita antes de apagar. |

## Organização sugerida para versão comercial

Quatro áreas claras: **Comprimir**, **Converter**, **Recortar e extrair**, **Histórico**. A alpha concentra as operações em uma única tela e não possui histórico persistente.

Na tela principal: adicionar arquivos, decidir meta, ver qualidade prevista, escolher destino e iniciar. Opções técnicas devem ficar em detalhes, não atrapalhar o primeiro uso. Ao concluir, mostrar economia medida e deixar abrir a pasta do resultado com um clique.

## Caminho até venda

1. Compilar e testar em Windows 10/11 x64 com arquivos reais, Unicode nos nomes, caminhos longos, pouco disco e cancelamento em cada etapa.
2. Validar instalador/desinstalador, empacotamento das ferramentas e assinatura de código. Manter a distribuição com todos os arquivos e avisos necessários.
3. Revisar licenças das dependências, builds FFmpeg e codecs escolhidos para o modelo de distribuição. Não assumir que toda build de terceiros tem as mesmas condições.
4. Melhorar PDF e comparação; medir qualidade visual e tempo em um conjunto de arquivos representativo.
5. Introduzir histórico local, receitas e relatórios completos incluindo erros. Só então adicionar licenciamento e pagamento.
6. Realizar um beta fechado e definir preço a partir do valor observado. Não há pesquisa de preços ou análise competitiva abrangente nesta entrega.

Como hipótese de negócio, licença pessoal com compra única combina com um utilitário local; automações e receitas de equipe podem justificar uma edição profissional. Evitar assinatura obrigatória antes de demonstrar valor recorrente. O modelo e o preço precisam ser validados com usuários.

## Fora do escopo inicial

“Limpar RAM” não deve ser a promessa principal. O espaço recuperado deve ser demonstrado em bytes e arquivos; não vender ganho de FPS ou aceleração genérica do computador. “Extrair dados brutos” precisa ser definido por formato e necessidade: áudio de vídeo, páginas de PDF, frames ou arquivos dentro de um contêiner são tarefas diferentes.
