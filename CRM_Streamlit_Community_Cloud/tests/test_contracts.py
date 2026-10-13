from copy import deepcopy
import json
from pathlib import Path
import pytest

from crm.contracts import validate_payload, validate_index, CERTIFICATION_CHECKS
from crm.errors import ContractError
from crm.repository import DemoRepository
from crm.charts import build_figure

ROOT = Path(__file__).resolve().parents[1]

def test_all_demo_snapshots(manifest):
    repository = DemoRepository(ROOT, manifest)
    index = repository.list_contexts()
    assert len(index) == 9
    assert sum(row["is_default"] for row in index) == 1
    for row in index:
        doc = repository.get_snapshot(row)
        assert doc["certification"]["status"] == "DEMO"
        for chart in doc["charts"]:
            figure = build_figure(chart)
            assert len(figure.data) == len(chart["traces"])


def test_demo_is_not_live(sample, manifest):
    with pytest.raises(ContractError):
        validate_payload(json.dumps(sample), manifest, "databricks", "DEMO-ONLY")


def test_valid_certified_fixture(certified, manifest):
    doc = validate_payload(json.dumps(certified), manifest, "databricks", "test-release")
    assert doc["cards"][0]["value"] == certified["cards"][0]["value"]

@pytest.mark.parametrize("check", CERTIFICATION_CHECKS)
def test_missing_approval_fails(certified, manifest, check):
    certified["certification"][check] = False
    with pytest.raises(ContractError):
        validate_payload(json.dumps(certified), manifest, "databricks", "test-release")

@pytest.mark.parametrize("field,value", [
    ("source_sha256", "wrong"), ("page_id", "unknown"),
    ("page_title", "Fake"), ("is_default", "true"), ("as_of", "2026-10-13"),
])
def test_invalid_metadata(sample, manifest, field, value):
    sample[field] = value
    with pytest.raises(ContractError):
        validate_payload(json.dumps(sample), manifest, "demo")


def test_wrong_release(certified, manifest):
    with pytest.raises(ContractError):
        validate_payload(json.dumps(certified), manifest, "databricks", "different")


def test_blank_is_not_coerced_to_zero(sample, manifest):
    sample["cards"][0]["value"] = None
    sample["cards"][0]["formatted_value"] = ""
    doc = validate_payload(json.dumps(sample), manifest, "demo")
    assert doc["cards"][0]["value"] is None
    assert doc["cards"][0]["formatted_value"] == ""


def test_total_is_not_recalculated(sample, manifest):
    sample["tables"][0]["rows"][-1][1] = "distinct total from source"
    doc = validate_payload(json.dumps(sample), manifest, "demo")
    assert doc["tables"][0]["rows"][-1][1] == "distinct total from source"

@pytest.mark.parametrize("mutator", [
    lambda d: d["cards"][0].update(value=float("nan")),
    lambda d: d["cards"][0].update(source_visual_id="unknown"),
    lambda d: d["cards"][0].update(measure="SUM(Amount)"),
    lambda d: d["charts"][0]["traces"][0].update(kind="javascript"),
    lambda d: d["charts"][0]["traces"][0].update(y=[1]),
    lambda d: d["tables"][0]["rows"].append(["bad"]),
    lambda d: d["cards"][1].update(id=d["cards"][0]["id"]),
])
def test_invalid_visual(sample, manifest, mutator):
    mutator(sample)
    with pytest.raises(ContractError):
        validate_payload(json.dumps(sample), manifest, "demo")


def test_default_not_guessed(manifest):
    rows = DemoRepository(ROOT, manifest).list_contexts()
    for row in rows:
        row["is_default"] = False
    with pytest.raises(ContractError):
        validate_index(rows, manifest)


def test_duplicate_context_rejected(manifest):
    rows = DemoRepository(ROOT, manifest).list_contexts()
    with pytest.raises(ContractError):
        validate_index(rows + [deepcopy(rows[0])], manifest)
