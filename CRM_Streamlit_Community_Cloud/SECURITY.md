# Segurança

## Sem credenciais no GitHub

Não publicar .streamlit/secrets.toml, .env, tokens, ficheiros de chaves, PBIX ou
exportacoes do CRM. .gitignore e uma protecao preventiva, não remove segredos
já commitados. Se ocorrer exposicao, revogue/rode o segredo e trate o historico do Git.

Os exemplos de TOML contem apenas placeholders. No Community Cloud use os Secrets
 da aplicacao. Não ha headers de Databricks Apps ou tokens de utilizador confiados
automaticamente neste ambiente de hospedagem.

## Identidade versus autorização

OIDC confirma identidade. Os claims usados sao iss/sub/exp a partir de st.user,
verificados pelo fluxo OIDC do Streamlit. Email, query strings e headers fornecidos
pelo utilizador não sao aceites como principal de acesso.

OAuth M2M autentica o service principal perante Databricks, não o viewer. Todas as
consultas incluem parametros de viewer_key, release, source_sha256, estado e validade.
A vista faz a associacao explicita entre viewer_key e snapshots autorizados.
Isso não implementa automaticamente a RLS original. Os snapshots devem ter sido
avaliados sob contextos de acesso semanticamente equivalentes ANTES de conceder grants.

Um service principal comprometido pode ler tudo que a vista lhe permite. Use
permissoes minimas, secrets protegidos, rotacao e revisão de grants herdados.
Não conceda permissao de escrita ou SELECT em Pipeline. Este modelo e autorização
na aplicacao com dados preautorizados, não delegacao nativa da identidade do viewer ao Unity Catalog.

## Ficheiros de referência

O modo reference le o ficheiro fornecido pelo proprio utilizador e vinculado a sua
identidade. O pacote e isolado na sessão e não e um dataset publico compartilhado.
Os atestados do JSON não sao assinados nem verificados contra um servico de homologação.
O modo e destinado a UAT de documentos já autorizados, não a substituicao de controles
centrais de acesso ou protecao de documentos fora da aplicacao.

## Execução

Somente SQL fixo e parametrizado; o nome da vista e configurado no servidor e
validado como identificador de tres partes. Não existe campo para enviar SQL,
DAX, código Python, HTML ou JavaScript pelo browser.

Sem cache global de resultados/tokens; conexões SQL encerradas apos a consulta.
Os limites de tamanho evitam exibir agregados parcialmente truncados. Downloads
reais desativados por padrao. Habilita-los exige aprovacao de politica de exportacao.

Autenticação e autorização devem ser testadas com utilizadores distintos antes de
produção. A confidencialidade não pode depender do URL ser dificil de descobrir,
do repositório ser privado ou de todos usarem a mesma conta técnica.
