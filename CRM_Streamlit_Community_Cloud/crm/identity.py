"""Identidade OIDC verificada por Streamlit; autorização aplicada no repositório."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import time
from typing import Any, Mapping

from crm.errors import AccessDenied


@dataclass(frozen=True)
class Viewer:
    key: str
    display_name: str


def make_viewer_key(issuer: str, subject: str) -> str:
    """Vincula o subject ao issuer; email não e usado como chave de autorização."""
    if not isinstance(issuer, str) or not issuer or not isinstance(subject, str) or not subject:
        raise AccessDenied("Identidade incompleta.")
    canonical = json.dumps([issuer, subject], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def viewer_from_claims(claims: Mapping[str, Any], expected_issuer: str,
                       now: float | None = None) -> Viewer:
    """So chamar com st.user, nunca com headers, query params ou JSON do navegador."""
    issuer, subject = claims.get("iss"), claims.get("sub")
    if not expected_issuer or issuer != expected_issuer or not isinstance(subject, str) or not subject:
        raise AccessDenied("Identidade não pertence ao emissor configurado.")
    exp = claims.get("exp")
    now = time.time() if now is None else now
    if type(exp) not in (int, float) or not math.isfinite(exp) or exp <= now:
        raise AccessDenied("Sessão expirada ou sem validade verificavel. Entre novamente.")
    name = claims.get("name") or "Utilizador autenticado"
    return Viewer(make_viewer_key(issuer, subject), str(name)[:200])


def require_viewer(settings):
    import streamlit as st
    if not st.user.is_logged_in:
        st.title("CRM Reporting")
        st.info("Autentique-se para consultar os dados autorizados.")
        if st.button("Entrar", type="primary"):
            st.login(settings.provider_name)
        st.stop()
    try:
        viewer = viewer_from_claims(st.user.to_dict(), settings.expected_issuer)
    except AccessDenied as exc:
        st.error(str(exc))
        if st.button("Terminar sessão e entrar novamente"):
            st.logout()
        st.stop()
    with st.sidebar:
        st.caption(viewer.display_name)
        if st.button("Sair"):
            st.logout()
        with st.expander("Identificador de acesso"):
            st.code(viewer.key, language=None)
            st.caption("Enviar ao administrador para conceder os contextos autorizados.")
    return viewer
