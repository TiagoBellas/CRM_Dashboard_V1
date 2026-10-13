"""Leitura de resultados avaliados, por identidade e release; sem SQL do navegador."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Callable

from crm.config import Settings, quoted_identifier
from crm.contracts import payload_digest, validate_payload, validate_index
from crm.errors import AccessDenied, ContractError
from crm.identity import Viewer

INDEX_FIELDS = (
    "snapshot_id", "page_id", "page_title", "quarter", "context_id", "context_label", "is_default"
)
MAX_CONTEXTS = 10_000


class DemoRepository:
    def __init__(self, root: Path, manifest: dict):
        self.manifest = manifest
        self.docs = json.loads((root / "demo" / "snapshots.json").read_text(encoding="utf-8"))

    def list_contexts(self) -> list[dict]:
        rows = [{key: doc[key] for key in INDEX_FIELDS} for doc in self.docs]
        return validate_index(rows, self.manifest)

    def get_snapshot(self, selected: dict) -> dict:
        found = [doc for doc in self.docs if doc["snapshot_id"] == selected["snapshot_id"]]
        if len(found) != 1:
            raise ContractError("Resultado de demonstração inexistente ou duplicado.")
        for key in INDEX_FIELDS:
            if found[0][key] != selected[key]:
                raise ContractError("Contexto da demonstração inconsistente.")
        return validate_payload(json.dumps(found[0], ensure_ascii=False), self.manifest, "demo")


class ReferenceRepository:
    """Pacote JSON enviado pelo utilizador, restrito a sessão atual.

    Não e carregado do GitHub nem guardado em disco. A identidade vinculada e um
    controlo adicional; as declaracoes do ficheiro não provam equivalencia de RLS.
    """
    def __init__(self, raw: bytes, viewer: Viewer, manifest: dict, expected_release: str):
        if len(raw) > 8_000_000:
            raise ContractError("Pacote de referência superior a 8 MB.")
        try:
            bundle = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ContractError("O ficheiro deve conter JSON UTF-8 valido.") from exc
        docs = bundle if isinstance(bundle, list) else [bundle]
        if not docs or len(docs) > 100:
            raise ContractError("Envie de 1 a 100 snapshots no pacote.")
        self.manifest = manifest
        self.docs = []
        for doc in docs:
            item = validate_payload(json.dumps(doc, ensure_ascii=False), manifest,
                                    "reference", expected_release)
            if item.get("authorized_viewer_key") != viewer.key:
                raise AccessDenied("Pacote de referência não esta vinculado a esta identidade.")
            self.docs.append(item)

    def list_contexts(self) -> list[dict]:
        return validate_index([{key: doc[key] for key in INDEX_FIELDS} for doc in self.docs], self.manifest)

    def get_snapshot(self, selected: dict) -> dict:
        found = [doc for doc in self.docs if all(doc[k] == selected[k] for k in INDEX_FIELDS)]
        if len(found) != 1:
            raise AccessDenied("Contexto não pertence ao pacote desta sessão.")
        return found[0]


class DatabricksExecutor:
    def __init__(self, settings: Settings):
        self.settings = settings

    def __call__(self, statement: str, parameters: dict, maximum_rows: int) -> list[dict]:
        # Imports tardios: a demo não precisa de credenciais nem de conectividade Databricks.
        from databricks import sql
        from databricks.sdk.core import Config, oauth_service_principal
        s = self.settings

        def credentials_provider():
            config = Config(host=f"https://{s.server_hostname}",
                            client_id=s.client_id, client_secret=s.client_secret)
            return oauth_service_principal(config)

        with sql.connect(
            server_hostname=s.server_hostname,
            http_path=s.http_path,
            credentials_provider=credentials_provider,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement, parameters=parameters)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchmany(maximum_rows + 1)
                if len(rows) > maximum_rows:
                    raise ContractError("Consulta excede o limite; nenhum resultado parcial sera mostrado.")
                return [dict(zip(columns, row, strict=True)) for row in rows]


class DatabricksRepository:
    """O Databricks ve o service principal, NÃO o utilizador OIDC.

    A serving_view deve juntar snapshots previamente avaliados sob a politica RLS
    equivalente com os grants de viewer_key. O filtro abaixo restringe novamente
    cada consulta. Não conceder SELECT nas tabelas brutas ao service principal.
    """
    def __init__(self, settings: Settings, viewer: Viewer, manifest: dict,
                 executor: Callable | None = None):
        if not re.fullmatch(r"[0-9a-f]{64}", viewer.key):
            raise AccessDenied("Identificador de acesso inválido.")
        if not settings.expected_release:
            raise ContractError("Release aprovada não configurada.")
        self.settings, self.viewer, self.manifest = settings, viewer, manifest
        self.execute = executor or DatabricksExecutor(settings)
        self.view = quoted_identifier(settings.serving_view)

    def _parameters(self) -> dict:
        return {"viewer_key": self.viewer.key, "release_id": self.settings.expected_release,
                "source_sha256": self.manifest["source_sha256"]}

    @property
    def _predicate(self) -> str:
        return """viewer_key = :viewer_key
          AND release_id = :release_id
          AND source_sha256 = :source_sha256
          AND certified = TRUE AND is_active = TRUE
          AND expires_at > current_timestamp()"""

    def list_contexts(self) -> list[dict]:
        statement = f"""SELECT {', '.join(INDEX_FIELDS)}
            FROM {self.view} WHERE {self._predicate}
            ORDER BY page_title, quarter, context_label
            LIMIT {MAX_CONTEXTS + 1}"""
        rows = self.execute(statement, self._parameters(), MAX_CONTEXTS)
        return validate_index(rows, self.manifest)

    def get_snapshot(self, selected: dict) -> dict:
        parameters = self._parameters() | {
            "snapshot_id": selected["snapshot_id"], "page_id": selected["page_id"],
            "context_id": selected["context_id"], "quarter": selected["quarter"],
        }
        statement = f"""SELECT payload_json, payload_sha256
            FROM {self.view} WHERE {self._predicate}
              AND snapshot_id = :snapshot_id AND page_id = :page_id
              AND context_id = :context_id AND quarter = :quarter
            LIMIT 2"""
        rows = self.execute(statement, parameters, 1)
        if len(rows) != 1:
            raise AccessDenied("Contexto indisponivel, expirado ou acesso revogado.")
        raw, expected = rows[0].get("payload_json"), rows[0].get("payload_sha256")
        if not isinstance(raw, str) or not isinstance(expected, str) or payload_digest(raw) != expected:
            raise ContractError("Integridade do resultado não confirmada.")
        doc = validate_payload(raw, self.manifest, "databricks", self.settings.expected_release)
        for key in INDEX_FIELDS:
            if doc[key] != selected[key]:
                raise ContractError("Payload diverge do contexto selecionado. Recarregue a página.")
        return doc
