from copy import deepcopy
import json
from pathlib import Path
import pytest

from crm.contracts import load_manifest

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def manifest():
    return load_manifest(ROOT)

@pytest.fixture
def sample():
    docs = json.loads((ROOT / "demo/snapshots.json").read_text(encoding="utf-8"))
    return deepcopy(next(d for d in docs if d["is_default"]))

@pytest.fixture
def certified(sample):
    # Apenas fixture de testes unitarios. Não e evidencia de homologação de negocio.
    sample["release_id"] = "test-release"
    sample["certification"] = {
        "status": "CERTIFIED", "scope": "values_in_fixed_context",
        "value_parity": True, "filter_context_parity": True,
        "access_policy_parity": True, "presentation_reviewed": True,
        "semantic_version": "test", "security_version": "test",
        "approved_by": "UNIT-TEST-NOT-PRODUCTION", "evidence_ref": "UNIT-TEST-ONLY",
    }
    return sample
