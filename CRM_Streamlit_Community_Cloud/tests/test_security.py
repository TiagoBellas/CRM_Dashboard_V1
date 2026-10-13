import json
from dataclasses import replace
from unittest.mock import Mock
import pytest

from crm.config import Settings, load_settings, quoted_identifier
from crm.contracts import payload_digest
from crm.errors import AccessDenied, ConfigurationError, ContractError
from crm.identity import Viewer, make_viewer_key, viewer_from_claims
from crm.repository import DatabricksRepository, INDEX_FIELDS

ISSUER = "https://issuer.example/tenant"


def test_demo_needs_no_secrets():
    assert load_settings({}).mode == "demo"


def test_live_cannot_fall_back_to_demo():
    with pytest.raises(ConfigurationError):
        load_settings({"app": {"mode": "databricks"}})


def test_unknown_mode_fails():
    with pytest.raises(ConfigurationError):
        load_settings({"app": {"mode": "production"}})

@pytest.mark.parametrize("bad", ["cat.schema.table; DROP TABLE t", "table", "x.y.z.w", "x.y.`z`", "x.y.z--"])
def test_identifier_injection_rejected(bad):
    with pytest.raises(ConfigurationError):
        quoted_identifier(bad)


def test_valid_identity():
    viewer = viewer_from_claims({"iss": ISSUER, "sub": "A", "exp": 2000}, ISSUER, now=1000)
    assert len(viewer.key) == 64
    assert viewer.key == make_viewer_key(ISSUER, "A")


def test_issuer_scopes_subject():
    assert make_viewer_key(ISSUER, "A") != make_viewer_key(ISSUER + "2", "A")

@pytest.mark.parametrize("claims", [
    {"iss": ISSUER, "sub": "A", "exp": 999},
    {"iss": "https://evil.example", "sub": "A", "exp": 2000},
    {"iss": ISSUER, "sub": "", "exp": 2000},
    {"iss": ISSUER, "sub": "A"},
    {"iss": ISSUER, "sub": "A", "exp": float("inf")},
])
def test_bad_identity_denied(claims):
    with pytest.raises(AccessDenied):
        viewer_from_claims(claims, ISSUER, now=1000)


def repo(manifest, executor):
    settings = Settings(mode="databricks", expected_release="test-release", serving_view="catalog.schema.serving")
    return DatabricksRepository(settings, Viewer(make_viewer_key(ISSUER, "A"), "A"), manifest, executor)


def test_parameterized_queries_and_user_scope(certified, manifest):
    selected = {key: certified[key] for key in INDEX_FIELDS}
    raw = json.dumps(certified)
    execute = Mock(return_value=[{"payload_json": raw, "payload_sha256": payload_digest(raw)}])
    provider = repo(manifest, execute)
    result = provider.get_snapshot(selected)
    assert result["snapshot_id"] == selected["snapshot_id"]
    statement, parameters, limit = execute.call_args.args
    assert "viewer_key = :viewer_key" in statement
    assert "release_id = :release_id" in statement
    assert "source_sha256 = :source_sha256" in statement
    assert "expires_at > current_timestamp()" in statement
    assert parameters["viewer_key"] == make_viewer_key(ISSUER, "A")
    assert selected["snapshot_id"] not in statement
    assert limit == 1


def test_revoked_access_fails(certified, manifest):
    provider = repo(manifest, Mock(return_value=[]))
    with pytest.raises(AccessDenied):
        provider.get_snapshot({key: certified[key] for key in INDEX_FIELDS})


def test_tampered_payload_fails(certified, manifest):
    provider = repo(manifest, Mock(return_value=[{"payload_json": json.dumps(certified), "payload_sha256": "bad"}]))
    with pytest.raises(ContractError):
        provider.get_snapshot({key: certified[key] for key in INDEX_FIELDS})


def test_index_envelope_mismatch_fails(certified, manifest):
    selected = {key: certified[key] for key in INDEX_FIELDS}
    certified["context_label"] = "different"
    raw = json.dumps(certified)
    provider = repo(manifest, Mock(return_value=[{"payload_json": raw, "payload_sha256": payload_digest(raw)}]))
    with pytest.raises(ContractError):
        provider.get_snapshot(selected)


def test_secrets_not_in_repr():
    settings = Settings(client_secret="TOPSECRET", client_id="SECRET_ID")
    assert "TOPSECRET" not in repr(settings)
    assert "SECRET_ID" not in repr(settings)
