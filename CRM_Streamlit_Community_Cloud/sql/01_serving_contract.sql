-- Execute pelo administrador/engenharia, NAO pelo service principal da aplicacao.
-- Substitua seu_catalogo. A criacao destas tabelas NAO migra DAX nem RLS.
-- Insira apenas resultados avaliados e aprovados para cada contexto de acesso.
CREATE SCHEMA IF NOT EXISTS seu_catalogo.crm_app;

CREATE TABLE IF NOT EXISTS seu_catalogo.crm_app.dashboard_snapshots (
  snapshot_id STRING NOT NULL,
  release_id STRING NOT NULL,
  source_sha256 STRING NOT NULL,
  page_id STRING NOT NULL,
  page_title STRING NOT NULL,
  quarter STRING NOT NULL,
  context_id STRING NOT NULL,
  context_label STRING NOT NULL,
  is_default BOOLEAN NOT NULL,
  payload_json STRING NOT NULL,
  payload_sha256 STRING NOT NULL,
  certified BOOLEAN NOT NULL,
  is_active BOOLEAN NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS seu_catalogo.crm_app.dashboard_access (
  viewer_key STRING NOT NULL,
  release_id STRING NOT NULL,
  snapshot_id STRING NOT NULL,
  active BOOLEAN NOT NULL
) USING DELTA;

CREATE OR REPLACE VIEW seu_catalogo.crm_app.dashboard_serving AS
SELECT a.viewer_key, s.*
FROM seu_catalogo.crm_app.dashboard_snapshots AS s
INNER JOIN seu_catalogo.crm_app.dashboard_access AS a
  ON a.snapshot_id = s.snapshot_id AND a.release_id = s.release_id
WHERE a.active = TRUE AND s.certified = TRUE AND s.is_active = TRUE
  AND s.expires_at > current_timestamp();

-- Usar o Application ID do service principal, nao uma identidade generica publica.
-- Conceder CAN USE no SQL Warehouse na configuracao de permissoes do warehouse.
-- GRANT USE CATALOG ON CATALOG seu_catalogo TO `SEU_SERVICE_PRINCIPAL_ID`;
-- GRANT USE SCHEMA ON SCHEMA seu_catalogo.crm_app TO `SEU_SERVICE_PRINCIPAL_ID`;
-- GRANT SELECT ON VIEW seu_catalogo.crm_app.dashboard_serving TO `SEU_SERVICE_PRINCIPAL_ID`;
-- NAO conceder SELECT nas tabelas de Pipeline nem permissoes de escrita.
-- Rever permissoes herdadas, grupos e propriedade antes de aprovar a conta tecnica.

-- Regras de publicacao (validadas adicionalmente pela aplicacao):
-- 1. Unicidade de release_id + snapshot_id em snapshots.
-- 2. Unicidade de viewer_key + release_id + snapshot_id em access.
-- 3. Um is_default por viewer_key + release_id + page_id.
-- 4. O default vem da regra homologada no modelo e dos dados, nao de current_date().
-- 5. payload_sha256 = sha2(payload_json, 256), sobre o JSON exato armazenado.
-- 6. Nunca associar um snapshot global a um utilizador com RLS mais restritiva.
-- 7. Publicar novas releases sem alterar a release ativa; trocar o secret apos UAT.
-- 8. Expiracao nao e substituto de refresh: o pipeline tem de atualizar snapshots.
