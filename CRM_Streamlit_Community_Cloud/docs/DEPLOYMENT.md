# Guia de publicação e operacao

## 1. Repositório

Use um repositório privado para preservar também os nomes internos do modelo.
O pacote contem metadados tecnicos derivados do PBIX, embora não inclua o PBIX,
linhas do CRM, logos, credenciais ou configurações de conexao extraidas da fonte.

O entrypoint e `streamlit_app.py` na raiz. `requirements.txt` esta na mesma raiz.
O caminho do entrypoint e relativo ao repositório e distingue maiusculas de minusculas.
Não sao necessarios Dockerfile, app.yaml, Procfile ou um servidor Databricks Apps.
A pasta `crm/` deve ser enviada inteira, não apenas o entrypoint.

O workflow `.github/workflows/ci.yml` instala dependencias, compila Python e executa
pytest em Python 3.12/3.13. Os smoke tests usam Streamlit AppTest e não precisam
de dados reais nem secrets. O resultado do workflow não e prova de equivalencia DAX.

## 2. Community Cloud

Em https://share.streamlit.io/ use Create app > Yup, I have an app. Selecione o
repositório, branch `main` e entrypoint `streamlit_app.py`. Em Advanced settings,
selecione Python 3.12. A primeira publicação pode usar apenas a demo, sem secrets.

O Cloud instala `requirements.txt`; não e necessario instalar bibliotecas manualmente
na plataforma. Os exemplos de secrets deste pacote não sao carregados automaticamente.
Alteracoes no código devem ser submetidas ao GitHub e verificadas no app e nos logs.
Nunca altere o app para mostrar dados reais como fallback de uma falha de autenticação.

Configure a visibilidade e os utilizadores da aplicacao no Community Cloud conforme
a politica da organizacao. Um repositório privado, por si so, não substitui as
permissoes do app, a autenticação OIDC nem a autorização dos dados.

## 3. Microsoft Entra ID

Registe uma aplicacao OIDC para este dashboard e configure callbacks absolutos.
Use tenant especifico, client_id, client_secret e a discovery URL do exemplo.
O expected_issuer deve coincidir EXATAMENTE com o claim `iss` emitido pelo IdP.
O código usa os claims `iss`, `sub` e `exp` de `st.user`; não aceita email, headers
ou parametros fornecidos pelo browser como identidade autorizadora.

O provider deve devolver os claims padrao, incluindo exp. Uma identidade expirada
obriga a novo login; a duracao do cookie Streamlit não e usada como prova de validade.
O client_secret OIDC não e intercambiavel com o segredo Databricks.
Mantenha segredos e rotacao de credenciais fora do repositório.

## 4. Modo reference (homologação sem Databricks)

Copie o exemplo `secrets.reference.example.toml` para os Secrets do Cloud, preencha
a configuração OIDC e a release. Depois do login, envie um JSON contendo um snapshot
ou uma lista de snapshots. O limite e 8 MB por pacote, 100 snapshots e 2 MB por snapshot.
Cada resultado precisa de `authorized_viewer_key` igual ao identificador mostrado
na barra lateral. Nenhum resultado fica disponivel para outros utilizadores do app.

A chave pode ser calculada administrativamente:

```bash
python scripts/viewer_key.py --issuer "https://ISSUER" --subject "SUB_DO_UTILIZADOR"
```

O valor e SHA-256 do JSON compacto [issuer, subject], codificado em UTF-8. Não use
email ou um subject proveniente de outro registo de aplicacao; sub pode variar por cliente.

Este modo serve para rever um ficheiro que o utilizador já possui, não para criar
um repositório multiutilizador de dados. Os atestados declarados no JSON não sao
assinaturas nem comprovam automaticamente equivalencia com o Power BI.

## 5. Modo databricks (fonte central)

O backend permanece no Databricks SQL; a aplicacao Python e executada no Community Cloud.

1. Prepare resultados avaliados sob os contextos e acessos corretos do modelo.
2. Crie as tabelas/vista indicadas em `sql/01_serving_contract.sql`.
3. Publique a release com snapshots, hashes, expiracao e grants por viewer_key.
4. Conceda ao service principal CAN USE no warehouse e SELECT apenas na vista
   aprovada, alem dos USE CATALOG/USE SCHEMA necessarios. Reveja permissoes herdadas.
5. Preencha os Secrets: app.mode, expected_release, OIDC, hostname, HTTP Path,
   client_id/client_secret Databricks e serving_view.
6. Teste dois utilizadores com acessos diferentes, um utilizador sem grants,
   revogacao de grants, expiracao e tentativas de selecionar outro contexto.

O conector usa OAuth M2M. Portanto current_user() no Databricks representa a conta
técnica, NÃO o viewer OIDC. A aplicacao restringe todas as consultas por viewer_key,
release, origem, estado e expiracao. O backend tem de fornecer snapshots já
compatibilizados com a RLS original. A tabela de grants não transforma agregados
globais em resultados equivalentes a RLS automaticamente.

O hostname e o endpoint OAuth/SQL devem ser acessiveis a partir da hospedagem do app.
Se a rede corporativa exige acesso exclusivamente privado não disponivel ao Community
Cloud, esta topologia não deve ser aprovada sem uma solucao de conectividade suportada.
Nessa situacao, a mesma interface requer um ambiente de hospedagem compativel com a rede.

## 6. Atualizacao, limites e rollback

A aplicacao le resultados; não executa refresh do Power BI, ingestao ou migração SQL.
Um pipeline externo deve publicar snapshots consistentes e indicar a carga em as_of.
Aumentar a frequencia de rerun não atualiza um snapshot que não foi regenerado.

Não existe cache global de dados reais nem tokens. Cada rerun volta a verificar o
indice autorizado e a leitura do contexto no Databricks. Uma revogacao produz efeito
na proxima consulta, não remove retroativamente conteudo já mostrado no browser.
O botao de atualizar solicita nova leitura; as ligacoes SQL sao fechadas apos cada consulta.

O contrato limita o indice a 10.000 contextos, 5.000 linhas por tabela e 2.000 pontos
por serie. Exceder um limite provoca erro, nunca truncagem silenciosa de indicadores.
Estes sao limites definidos pelo projeto, não limites oficiais do Community Cloud.

Uma nova release e publicada separadamente; depois de UAT, altere expected_release
nos Secrets. Para rollback, volte a release anterior ainda válida e/ou reative o
Power BI original, que permanece inalterado. Não utilize estado local como armazenamento persistente.

## 7. Diagnostico

| Sintoma | Verificacao |
|---|---|
| ModuleNotFoundError | Entry point e requirements na raiz; pasta crm enviada; conferir logs de instalacao |
| Demo aparece | app.mode ausente ou explicitamente demo; exemplos de TOML não sao secrets ativos |
| Identidade de outro emissor | Ajustar expected_issuer ao tenant e claim iss do provider |
| Sessão sem validade verificavel | Confirmar exp no ID token e refazer login |
| Nenhum contexto autorizado | viewer_key, release, grants, certified, is_active e expires_at |
| Falha de integridade | SHA-256 dos bytes UTF-8 do payload armazenado, sem reformatar depois do hash |
| Default inválido | Exatamente um default por página/identidade/release, definido na origem |
| Valor não coincide com PBI | Revalidar snapshot, filtros, RLS, grain, BLANK e medidas; não corrigir na UI |
| Conexao SQL falha | Endpoint/rede, credenciais M2M, permisos e warehouse; não expor tokens nos logs |

Os erros gerais mostram um código de diagnostico. O código não imprime tokens,
claims, dados de negocio ou mensagens integrais do conector nos logs.
