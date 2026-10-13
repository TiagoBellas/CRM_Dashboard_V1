import json
import pytest
from crm.identity import Viewer, make_viewer_key
from crm.repository import ReferenceRepository, INDEX_FIELDS
from crm.errors import AccessDenied, ContractError

KEY = make_viewer_key("https://issuer.example", "user")


def test_reference_is_private_to_identity(certified, manifest):
    certified["authorized_viewer_key"] = KEY
    repo = ReferenceRepository(json.dumps(certified).encode(), Viewer(KEY, "User"), manifest, "test-release")
    index = repo.list_contexts()
    assert len(index) == 1
    assert repo.get_snapshot(index[0])["snapshot_id"] == certified["snapshot_id"]


def test_reference_rejects_other_identity(certified, manifest):
    certified["authorized_viewer_key"] = make_viewer_key("https://issuer.example", "other")
    with pytest.raises(AccessDenied):
        ReferenceRepository(json.dumps(certified).encode(), Viewer(KEY, "User"), manifest, "test-release")


def test_reference_requires_explicit_identity_binding(certified, manifest):
    with pytest.raises(AccessDenied):
        ReferenceRepository(json.dumps(certified).encode(), Viewer(KEY, "User"), manifest, "test-release")


def test_reference_rejects_demo(sample, manifest):
    sample["authorized_viewer_key"] = KEY
    with pytest.raises(ContractError):
        ReferenceRepository(json.dumps(sample).encode(), Viewer(KEY, "User"), manifest, "DEMO-ONLY")

@pytest.mark.parametrize("raw", [b"not json", b"[]", b"null", b"\xff"])
def test_invalid_reference(raw, manifest):
    with pytest.raises(ContractError):
        ReferenceRepository(raw, Viewer(KEY, "User"), manifest, "test-release")
