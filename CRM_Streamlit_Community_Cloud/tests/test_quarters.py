import pytest
from crm.quarters import Quarter, comparison_windows

@pytest.mark.parametrize("label,previous,ly", [
    ("Q1-2026", "Q4-2025", "Q1-2025"),
    ("Q4-2026", "Q3-2026", "Q4-2025"),
    ("Q2-2024", "Q1-2024", "Q2-2023"),
])
def test_windows(label, previous, ly):
    rows = comparison_windows(label)
    assert rows[1]["Trimestre"] == previous
    assert rows[2]["Trimestre"] == ly


def test_full_historical_period():
    rows = comparison_windows("Q4-2026")
    assert rows[0]["Fim exclusivo"] == "2027-01-01"
    assert rows[1]["Início inclusivo"] == "2026-07-01"
    assert rows[1]["Fim inclusivo"] == "2026-09-30"
    assert rows[2]["Fim inclusivo"] == "2025-12-31"

@pytest.mark.parametrize("bad", ["Q0-2026", "Q5-2026", "2026-Q4", "Q4-26", "", "Q1-0001"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        Quarter.parse(bad)
