from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
import re

from crm.errors import ConfigurationError


@dataclass(frozen=True)
class Settings:
    mode: str = "demo"
    allow_downloads: bool = False
    expected_release: str = ""
    expected_issuer: str = ""
    provider_name: str = "microsoft"
    server_hostname: str = ""
    http_path: str = ""
    client_id: str = field(default="", repr=False)
    client_secret: str = field(default="", repr=False)
    serving_view: str = ""


def quoted_identifier(value: str) -> str:
    """Identificadores nunca vem dos widgets; apenas da configuração do servidor."""
    parts = value.split(".")
    if len(parts) != 3 or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p) for p in parts):
        raise ConfigurationError("serving_view deve ser catalogo.esquema.vista, sem SQL.")
    return ".".join(f"`{p}`" for p in parts)


def _text(section: Mapping[str, Any], name: str, default: str = "") -> str:
    value = section.get(name, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} deve ser texto.")
    return value.strip()


def load_settings(secrets: Mapping[str, Any]) -> Settings:
    app = secrets.get("app", {})
    db = secrets.get("databricks", {})
    security = secrets.get("security", {})
    if not all(isinstance(s, Mapping) for s in (app, db, security)):
        raise ConfigurationError("As secoes dos secrets devem ser tabelas TOML.")
    mode = _text(app, "mode", "demo")
    if mode not in {"demo", "reference", "databricks"}:
        raise ConfigurationError("app.mode deve ser demo, reference ou databricks.")
    downloads = app.get("allow_downloads", mode == "demo")
    if type(downloads) is not bool:
        raise ConfigurationError("allow_downloads deve ser true ou false.")
    if mode == "demo":
        return Settings(mode=mode, allow_downloads=downloads)
    settings = Settings(
        mode=mode, allow_downloads=downloads,
        expected_release=_text(app, "expected_release"),
        expected_issuer=_text(security, "expected_issuer"),
        provider_name=_text(security, "provider_name", "microsoft"),
        server_hostname=_text(db, "server_hostname"),
        http_path=_text(db, "http_path"),
        client_id=_text(db, "client_id"),
        client_secret=_text(db, "client_secret"),
        serving_view=_text(db, "serving_view"),
    )
    required = ["expected_release", "expected_issuer", "provider_name"]
    if mode == "databricks":
        required += ["server_hostname", "http_path", "client_id", "client_secret", "serving_view"]
    for key in required:
        if not getattr(settings, key):
            raise ConfigurationError(f"Configuração obrigatória ausente: {key}.")
    if not settings.expected_issuer.startswith("https://"):
        raise ConfigurationError("expected_issuer exige HTTPS.")
    if mode == "databricks" and not re.fullmatch(r"[A-Za-z0-9.-]+", settings.server_hostname):
        raise ConfigurationError("server_hostname não deve conter https://, porta ou caminho.")
    if mode == "databricks" and not re.fullmatch(r"/sql/1\.0/warehouses/[A-Za-z0-9-]+", settings.http_path):
        raise ConfigurationError("Configure o HTTP Path de um Databricks SQL Warehouse.")
    if not re.fullmatch(r"[A-Za-z0-9-]+", settings.provider_name):
        raise ConfigurationError("provider_name inválido.")
    if mode == "databricks":
        quoted_identifier(settings.serving_view)
    auth = secrets.get("auth", {})
    if not isinstance(auth, Mapping):
        raise ConfigurationError("A secao auth deve ser uma tabela TOML.")
    provider = auth.get(settings.provider_name, {})
    if not isinstance(provider, Mapping):
        raise ConfigurationError("Configure o provedor OIDC em auth.")
    for key in ("redirect_uri", "cookie_secret"):
        if not _text(auth, key):
            raise ConfigurationError(f"Falta auth.{key}.")
    for key in ("client_id", "client_secret", "server_metadata_url"):
        if not _text(provider, key):
            raise ConfigurationError(f"Falta auth.{settings.provider_name}.{key}.")
    return settings
