"""Entrypoint para GitHub + Streamlit Community Cloud.

Local: python -m streamlit run streamlit_app.py
Sem secrets: demonstração sintética. Produção: OIDC + Databricks + resultados homologados.
"""
from pathlib import Path
import logging
import uuid

import streamlit as st

from crm.config import load_settings
from crm.contracts import load_manifest
from crm.errors import AccessDenied, ConfigurationError, ContractError
from crm.identity import require_viewer
from crm.repository import DatabricksRepository, DemoRepository, ReferenceRepository
from crm.ui import choose_context, render_coverage, render_dashboard

ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger("crm_app")


def main() -> None:
    st.set_page_config(page_title="CRM Reporting", layout="wide")
    try:
        # Ausencia de secrets e esperada para a demo. TOML inválido não e ignorado.
        try:
            secrets = st.secrets.to_dict()
        except FileNotFoundError:
            secrets = {}
        settings = load_settings(secrets)
        manifest = load_manifest(ROOT)
        st.sidebar.title("CRM Reporting")
        st.sidebar.caption("STREAMLIT COMMUNITY CLOUD")
        if settings.mode != "demo":
            viewer = require_viewer(settings)
            if settings.mode == "reference":
                uploaded = st.sidebar.file_uploader("Pacote de resultados homologados", type=["json"])
                if uploaded is None:
                    st.title("CRM Reporting")
                    st.info("Envie um JSON de resultados avaliados e homologados, vinculado a sua identidade. Não envie PBIX ou dados brutos.")
                    return
                repository = ReferenceRepository(uploaded.getvalue(), viewer, manifest, settings.expected_release)
            else:
                repository = DatabricksRepository(settings, viewer, manifest)
        else:
            st.sidebar.info("Modo demonstração | dados sintéticos")
            repository = DemoRepository(ROOT, manifest)
        index = repository.list_contexts()
        if not index:
            st.warning("Não existem contextos ativos autorizados para esta identidade e release.")
            return
        screen = st.sidebar.radio("Navegação", ["Dashboard", "Regras e cobertura"])
        if screen == "Regras e cobertura":
            render_coverage(manifest)
            return
        selected = choose_context(index)
        if st.sidebar.button("Atualizar dados"):
            st.rerun()
        # Nenhum cache global de resultados ou de tokens entre utilizadores.
        doc = repository.get_snapshot(selected)
        render_dashboard(doc, settings.mode, settings.allow_downloads)
    except (ConfigurationError, ContractError, AccessDenied, ValueError) as exc:
        st.error(str(exc))
    except Exception as exc:
        event = uuid.uuid4().hex[:12]
        # Não regista parametros, payloads, claims ou excecoes que possam conter tokens.
        LOGGER.error("CRM event=%s exception_type=%s", event, type(exc).__name__)
        st.error(f"Falha ao carregar a aplicacao. Código de diagnostico: {event}.")


if __name__ == "__main__":
    main()
