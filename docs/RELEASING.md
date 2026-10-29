# Publicar uma alpha Windows

1. Atualize as dependências diretas nos requirements e resolva num venv limpo de Python 3.12.10/Windows x64. Instale `requirements-test.txt`, execute `python -m pip freeze --all` e atualize `requirements-lock.txt`. Revise todo o diff; o lock inclui dependências transitivas de runtime, build e teste.
2. Mudanças de FFmpeg exigem atualizar URL/version/hash em `media_install.py`, verificar o pacote do fornecedor e executar instalação e testes reais. Não substitua o hash fixo por um hash obtido no momento de instalar.
3. Abra uma PR. Exija o workflow Windows aprovado e revise o artefato: testes sem mídia ignorada, compatibilidade Office/ODF com LibreOffice, aplicativo extraído funcionando e qualidade visual de amostras reais.
4. Atualize a matriz de capacidades, versão anunciada e notas. Crie uma nova tag `vX.Y.Z-alpha` sobre o commit aprovado. Não mova tags publicadas nem substitua silenciosamente o ZIP de uma versão anterior.
5. O workflow de Release valida tudo novamente e publica ZIP, SHA256SUMS e notas. Tags alpha/beta/rc são pré-lançamentos. O disparo manual exige uma tag existente. Acompanhe a execução até terminar; criar a tag não prova que a publicação foi concluída.
6. Confirme o download, checksum, estrutura `LynowCut/LynowCut.exe` + `_internal`, avisos de licença e comportamento em Windows 10/11 x64 sem Python. Registre a verificação manual nas notas. O modo diagnóstico é automatizado e não substitui avaliação visual.

## Authenticode

A alpha atual é explicitamente não assinada. Um certificado e serviço de assinatura do editor precisam ser obtidos antes de habilitar assinatura; nenhum certificado ou segredo deve ser colocado no Git.

Quando o editor dispuser deles, adicione uma etapa de assinatura protegida entre o build e o ZIP, usando um serviço de assinatura ou um certificado acessível apenas ao ambiente de Release. Com Windows SDK, o procedimento equivalente é `signtool sign /fd SHA256 /tr <servidor RFC3161 do provedor> /td SHA256 /sha1 <identificador do certificado> dist\LynowCut\LynowCut.exe`. Use o identificador do certificado instalado, sem exportar sua chave privada.

Valide com `signtool verify /pa /all /v` e `Get-AuthenticodeSignature`. Faça o workflow falhar se assinatura ou timestamp não forem válidos. Atualize `signed` no BUILD-INFO somente a partir dessa verificação, depois execute o teste do pacote assinado e gere o checksum do ZIP final. Registre o nome esperado do editor nas notas; reputação do Windows não é garantida pela assinatura.

O digest do GitHub e SHA256SUMS ajudam a detectar download corrompido; não substituem autenticação do editor ou atestação de origem. A configuração atual automatiza o build e fixa versões, mas não promete reprodução byte a byte.
