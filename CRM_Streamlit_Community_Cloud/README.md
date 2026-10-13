# CRM Reporting - GitHub + Streamlit Community Cloud

Código-fonte para publicar uma interface CRM no Streamlit Community Cloud a partir
 de um repositório GitHub. O PBIX original não e alterado nem incluido neste repositório.

**Estado da entrega:** demonstração preparada para publicação, com resultados sintéticos,
leitura de pacotes JSON de referência e conector Databricks. O modelo DAX/Power Query/RLS
completo não foi recuperado; este pacote não constitui a migração integral homologada
das 23 páginas do Power BI. Não troque as medidas desconhecidas por somas ou contagens presumidas.

## Publicar a demonstração

1. Extraia o ZIP. Crie no GitHub um repositório, preferencialmente privado, com o nome
   `crm-reporting-streamlit`. Use um repositório vazio, sem README inicial.
2. Coloque o CONTEUDO desta pasta na raiz do repositório. A raiz deve conter
   `streamlit_app.py`, `requirements.txt`, `crm/`, `metadata/`, `demo/` e `.streamlit/`.
   Não envie apenas o ZIP. Preserve a pasta oculta `.streamlit/` e o `.gitignore`.
3. Aceda a https://share.streamlit.io/ e autorize o acesso ao repositório GitHub.
   Selecione **Create app**, **Yup, I have an app** e preencha:
   - Repository: `SEU_USUARIO/crm-reporting-streamlit`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
4. Em **Advanced settings**, selecione **Python 3.12**. Não sao necessarios secrets para a demo.
5. Publique. Os valores da página Quarter Performance sao explicitamente sintéticos.
   As alteracoes posteriores devem ser feitas no GitHub. Veja também o estado do workflow CI.

A demonstração contem tres trimestres selecionaveis, tres contextos sintéticos,
tres cartoes, dois graficos e duas tabelas de comparação. As restantes páginas
originais estao inventariadas, não implementadas como dashboards de demonstração.
O renderer pode apresentar outras páginas quando receber contratos compativeis e revistos.

## Enviar o código pelo Git

Execute a partir desta pasta, depois de criar o repositório vazio no GitHub:

```bash
git init -b main
git add .
git status --short
git diff --cached --stat
# Verifique que NÃO existem secrets.toml, .env, PBIX ou dados privados no staging.
git commit -m "Implement CRM dashboard for Streamlit Community Cloud"
git remote add origin https://github.com/SEU_USUARIO/crm-reporting-streamlit.git
git push -u origin main
```

A autenticação do Git usa o mecanismo configurado na sua conta; não inclua passwords
ou tokens na URL. Nunca publique credenciais no repositório, mesmo privado.

## Executar localmente

Python recomendado para o deploy: 3.12. Os testes de lógica desta entrega foram
executados em Python 3.13.5; o workflow fornecido esta configurado para 3.12 e 3.13,
mas ainda não foi executado no seu GitHub.

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Windows PowerShell, sem necessidade de ativar scripts:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Abra o endereco local mostrado no terminal. Sem secrets, so existe acesso a dados ficticios.

## Tres modos de dados

| app.mode | Origem | Uso | Requisitos |
|---|---|---|---|
| `demo` | `demo/snapshots.json` | Verificar interface e deploy, sem dados reais | Nenhuma credencial |
| `reference` | JSON enviado pelo utilizador na sessão | Homologação de resultados exportados, sem Databricks | OIDC, release aprovada e pacote vinculado ao utilizador |
| `databricks` | Vista de resultados avaliados no Databricks SQL | Operacao multiutilizador com resultados autorizados | OIDC, OAuth M2M, serving_view, grants e homologação externa |

GitHub armazena código e fixtures sintéticas. NÃO e a base de dados de produção.
Em `reference`, os ficheiros ficam apenas na memoria da sessão da aplicacao, sem
cache global nem escrita explicita em disco. O modo não substitui RLS centralizada
ou revogacao de acesso a um documento que o proprio utilizador já possui.

## Configurar dados reais

Para JSON de referência, use `.streamlit/secrets.reference.example.toml`.
Para Databricks, use `.streamlit/secrets.example.toml`.

**Local:** copie o exemplo para `.streamlit/secrets.toml` e preencha os valores.
**Community Cloud:** copie o TOML preenchido para **App settings > Secrets**.
Não coloque os secrets reais no GitHub, nem confunda Streamlit Secrets com GitHub Actions Secrets.

O exemplo usa Microsoft Entra ID para OIDC. Configure o callback do provider para
`https://SEU-APP.streamlit.app/oauth2callback`; localmente, configure também
`http://localhost:8501/oauth2callback`. O tenant e o emissor devem ser especificos
 da organizacao, não `common`. O `client_secret` OIDC e distinto do segredo OAuth Databricks.

Gere um cookie_secret forte localmente:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Para Databricks, execute `sql/01_serving_contract.sql` com uma conta administrativa
apos substituir os identificadores. A aplicacao não cria tabelas, não escreve dados
 e não traduz DAX: ela le a vista `dashboard_serving`.

**A criacao das tabelas não as preenche.** A equipa de dados deve publicar snapshots
com resultados avaliados e aprovados, controles de acesso equivalentes, metadados
de contexto e hashes. O processo esta em `docs/DATA_CONTRACT.md`.

## Preservacao da lógica original

As janelas trimestrais usam CreatedOn como referência documentada. Previous e LY
 sao trimestres completos, sem corte proporcional. O default e declarado pela camada
semântica; a interface não escolhe o trimestre pela data do servidor.

Valores, percentagens, BLANK, textos formatados, totais e linhas de comparação chegam
já avaliados. Não ha `groupby`, contagem de RecordId/DealId, recomputacao de QoQ/YoY,
normalizacao de shares ou substituicao de Terminal Snapshot no código da interface.

Os filtros sao contextos COMPLETOS, atomicos e preavaliados. Não ha filtros livres
sobre os resultados agregados. Não basta exportar uma tabela global e filtra-la
no Streamlit: isso pode alterar DISTINCTCOUNT, totais, ALL/REMOVEFILTERS e RLS.

Não estao reproduzidos neste pacote: slicers independentes arbitrarios, todas as
23 páginas, bookmarks, drillthrough, cross-filtering, visuais HTML e Deneb.
As duas interações NoFilter devem ser resolvidas na avaliacao de cada snapshot;
a interface não tenta adivinhar o comportamento dos visuais.

## Estrutura

```text
streamlit_app.py                  # Entrypoint publicado no Community Cloud
requirements.txt                 # Dependencias de runtime
requirements-dev.txt             # Dependencias de testes
crm/
  config.py                      # Leitura e validação dos secrets
  identity.py                    # OIDC e identificador issuer + subject
  repository.py                  # Demo, referência JSON e Databricks
  contracts.py                   # Validação de payload, release e atestados
  quarters.py                    # Apenas limites de datas
  charts.py                      # Graficos sem agregacao
  ui.py                          # Interface
metadata/pbi_manifest.json       # Catalogo de origem sem linhas do CRM
examples/snapshot.pending.json   # Modelo PENDING; não e um resultado aprovado
demo/snapshots.json              # Nove resultados 100% sintéticos
sql/01_serving_contract.sql      # Tabelas e vista do contrato Databricks
scripts/                        # Validação de snapshots e chave de acesso
tests/                          # Lógica, segurança, contratos e smoke tests
.streamlit/                     # Configuração e exemplos SEM credenciais
.github/workflows/ci.yml         # Testes no GitHub; não publica secrets
```

## Testar

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Veja `VALIDATION.md`: 62 testes executados passaram. O modulo de smoke tests do
Streamlit foi ignorado neste ambiente por ausencia do runtime; a instalacao ficou
impedida pela indisponibilidade de acesso ao repositório de pacotes. O workflow
fornecido executa esses testes quando as dependencias forem instaladas no GitHub.
Não houve publicação em GitHub/Community Cloud nem consulta ao seu Databricks.

## Leitura complementar

- `docs/DEPLOYMENT.md`: publicação, identidade, operacao e erros frequentes.
- `docs/DATA_CONTRACT.md`: como preparar resultados sem alterar a semântica.
- `SECURITY.md`: limites de autorização e requisitos para produção.
- `docs/SOURCES.md`: documentacao oficial consultada em 13/10/2026.
