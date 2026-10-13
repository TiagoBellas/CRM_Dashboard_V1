"""Contrato de resultados avaliados. Não agrega nem recalcula medidas de negocio."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from crm.errors import ContractError
from crm.quarters import Quarter

MAX_PAYLOAD_BYTES = 2_000_000
MAX_TABLE_ROWS = 5000
CERTIFICATION_CHECKS = (
    "value_parity", "filter_context_parity", "access_policy_parity", "presentation_reviewed"
)


def load_manifest(root: Path) -> dict[str, Any]:
    return json.loads((root / "metadata" / "pbi_manifest.json").read_text(encoding="utf-8"))


def payload_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fail(message: str) -> None:
    raise ContractError(message)


def _string(value: Any, name: str, *, empty: bool = False, maximum: int = 2000) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value):
        _fail(f"Campo de texto inválido: {name}.")
    return value


def _list(value: Any, name: str, maximum: int) -> list:
    if not isinstance(value, list) or len(value) > maximum:
        _fail(f"Lista inválida ou demasiado grande: {name}.")
    return value


def _number(value: Any) -> bool:
    return value is None or (type(value) in (int, float) and math.isfinite(value))


def _no_constant(value: str):
    _fail("JSON contem um número não finito.")


def validate_payload(raw: str, manifest: dict, mode: str,
                     expected_release: str = "") -> dict[str, Any]:
    if mode not in {"demo", "reference", "databricks"}:
        _fail("Modo de execução desconhecido.")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        _fail("Payload ausente ou superior a 2 MB; particione na origem.")
    try:
        doc = json.loads(raw, parse_constant=_no_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("Payload não e JSON valido.") from exc
    if not isinstance(doc, dict) or type(doc.get("schema_version")) is not int or doc["schema_version"] != 1:
        _fail("Versao do contrato não suportada.")
    if doc.get("source_sha256") != manifest["source_sha256"]:
        _fail("Resultado não corresponde ao PBIX de referência.")
    for name in ("snapshot_id", "release_id", "page_id", "context_id", "context_label", "as_of"):
        _string(doc.get(name), name)
    pages = {p["id"]: p for p in manifest["pages"]}
    if doc["page_id"] not in pages or doc.get("page_title") != pages[doc["page_id"]]["title"]:
        _fail("Página ausente do PBIX ou titulo divergente.")
    try:
        Quarter.parse(doc.get("quarter", ""))
        timestamp = datetime.fromisoformat(doc["as_of"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            _fail("as_of deve incluir fuso horario.")
    except (TypeError, ValueError) as exc:
        raise ContractError("Trimestre ou timestamp inválido.") from exc
    if type(doc.get("is_default")) is not bool:
        _fail("is_default deve ser booleano, definido pela camada semântica.")
    if not isinstance(doc.get("filter_context"), dict):
        _fail("O contexto completo de filtros e obrigatório.")
    if len(json.dumps(doc["filter_context"])) > 20_000:
        _fail("Contexto de filtros demasiado grande.")
    cert = doc.get("certification", {})
    if not isinstance(cert, dict):
        _fail("Certificacao ausente.")
    if mode == "demo":
        if cert.get("status") != "DEMO":
            _fail("O modo demo so aceita resultados identificados como DEMO.")
    else:
        if not expected_release or doc["release_id"] != expected_release:
            _fail("Release não aprovada na configuração do servidor.")
        if cert.get("status") != "CERTIFIED":
            _fail("Resultado real ainda não homologado.")
        if cert.get("scope") != "values_in_fixed_context":
            _fail("Escopo de homologação não suportado.")
        for key in CERTIFICATION_CHECKS:
            if cert.get(key) is not True:
                _fail(f"Homologação pendente: {key}.")
        for key in ("semantic_version", "security_version", "approved_by", "evidence_ref"):
            _string(cert.get(key), f"certification.{key}")
    visuals = {v["id"]: v for v in manifest["visuals"] if v["page_id"] == doc["page_id"]}
    used_ids: set[str] = set()

    def component(value: Any) -> dict:
        if not isinstance(value, dict):
            _fail("Componente inválido.")
        component_id = _string(value.get("id"), "id")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", component_id) or component_id in used_ids:
            _fail("ID de componente inválido ou duplicado.")
        used_ids.add(component_id)
        if value.get("source_visual_id") not in visuals:
            _fail("Visual não pertence a página do PBIX.")
        return value

    cards = _list(doc.get("cards"), "cards", 40)
    for item in cards:
        component(item)
        _string(item.get("label"), "card.label")
        _string(item.get("formatted_value"), "card.formatted_value", empty=True)
        if not _number(item.get("value")):
            _fail("Valor do cartao deve ser número finito ou null (BLANK).")
        if item.get("measure") not in visuals[item["source_visual_id"]]["fields"]:
            _fail("Medida do cartao não esta vinculada ao visual original.")
    charts = _list(doc.get("charts"), "charts", 20)
    for item in charts:
        component(item)
        _string(item.get("title"), "chart.title")
        if item.get("barmode", "group") not in {"group", "stack"}:
            _fail("barmode não permitido.")
        for axis in ("y_format", "y2_format"):
            if item.get(axis, "number") not in {"number", "percent"}:
                _fail("Formato de eixo não suportado.")
        for label in ("x_label", "y_label", "y2_label"):
            _string(item.get(label, ""), label, empty=True)
        for trace in _list(item.get("traces"), "traces", 20):
            if not isinstance(trace, dict):
                _fail("Serie de grafico inválida.")
            if trace.get("kind") not in {"bar", "line"} or trace.get("axis", "y") not in {"y", "y2"}:
                _fail("Apenas series bar/line e eixos y/y2 sao permitidos.")
            _string(trace.get("name"), "trace.name")
            x = _list(trace.get("x"), "trace.x", 2000)
            y = _list(trace.get("y"), "trace.y", 2000)
            display = _list(trace.get("display_y"), "trace.display_y", 2000)
            if len(x) != len(y) or len(y) != len(display):
                _fail("Eixos e valores formatados possuem comprimentos diferentes.")
            for value in x:
                _string(value, "trace.x", empty=True)
            if not all(_number(value) for value in y):
                _fail("Serie contem valor não numérico.")
            for value in display:
                _string(value, "trace.display_y", empty=True)
    tables = _list(doc.get("tables"), "tables", 20)
    for item in tables:
        component(item)
        _string(item.get("title"), "table.title")
        columns = _list(item.get("columns"), "table.columns", 100)
        for value in columns:
            _string(value, "table.column")
        if not columns or len(set(columns)) != len(columns):
            _fail("Colunas de tabela vazias ou duplicadas.")
        for row in _list(item.get("rows"), "table.rows", MAX_TABLE_ROWS):
            if not isinstance(row, list) or len(row) != len(columns):
                _fail("Linha da tabela não corresponde as colunas.")
            for value in row:
                if not (value is None or isinstance(value, str) or _number(value)):
                    _fail("Celula da tabela deve ser texto, número ou null.")
                if isinstance(value, str) and len(value) > 10_000:
                    _fail("Celula da tabela demasiado grande.")
    for note in _list(doc.get("notes"), "notes", 30):
        _string(note, "note", maximum=5000)
    if not (cards or charts or tables):
        _fail("Payload não contem componentes de dados.")
    return doc


def validate_index(rows: list[dict], manifest: dict) -> list[dict]:
    """Um default por página; nunca substitui pela data atual ou por max arbitrario."""
    if not rows:
        return rows
    pages = {p["id"]: p["title"] for p in manifest["pages"]}
    keys, snapshots, defaults = set(), set(), {}
    for row in rows:
        if not isinstance(row, dict):
            _fail("Indice inválido.")
        for key in ("page_id", "page_title", "context_id", "context_label", "snapshot_id", "quarter"):
            _string(row.get(key), key)
        if pages.get(row["page_id"]) != row["page_title"]:
            _fail("Página desconhecida no indice.")
        Quarter.parse(row["quarter"])
        key = (row["page_id"], row["quarter"], row["context_id"])
        if key in keys or row["snapshot_id"] in snapshots:
            _fail("Indice contem resultados duplicados para o mesmo contexto.")
        keys.add(key)
        snapshots.add(row["snapshot_id"])
        if type(row.get("is_default")) is not bool:
            _fail("Default do indice deve ser booleano.")
        defaults[row["page_id"]] = defaults.get(row["page_id"], 0) + int(row["is_default"])
    if any(count != 1 for count in defaults.values()):
        _fail("Cada página autorizada deve possuir exatamente um contexto default.")
    return rows
