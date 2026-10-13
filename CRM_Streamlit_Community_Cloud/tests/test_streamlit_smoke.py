"""Executa no CI com o runtime instalado; não necessita credenciais."""
from pathlib import Path
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_app_starts_in_demo():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    assert not app.error
    assert any(title.value == "Quarter Performance" for title in app.title)
    assert len(app.metric) == 3


def test_quarter_and_context_selection():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.selectbox[1].set_value("Q2-2026").run()
    assert not app.exception
    assert not app.error
    app.sidebar.selectbox[2].set_value("alpha").run()
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 3


def test_coverage_view():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Regras e cobertura").run()
    assert not app.exception
    assert not app.error
    assert "Regras e cobertura" in app.header[0].value
