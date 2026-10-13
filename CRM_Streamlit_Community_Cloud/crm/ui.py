"""Renderizacao sem groupby, contagens, percentagens ou totais calculados no cliente."""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from crm.quarters import Quarter, comparison_windows
from crm.charts import build_figure


def choose_context(index: list[dict]) -> dict:
    pages = {row["page_id"]: row["page_title"] for row in index}
    page_ids = list(pages)
    preferred = next((key for key in page_ids if pages[key] == "Quarter Performance"), page_ids[0])
    page_id = st.sidebar.selectbox(
        "Página", page_ids, index=page_ids.index(preferred),
        format_func=pages.get, key="selected_page",
    )
    rows = [row for row in index if row["page_id"] == page_id]
    default = next(row for row in rows if row["is_default"])
    quarters = sorted({row["quarter"] for row in rows}, key=Quarter.parse)
    quarter = st.sidebar.selectbox(
        "Selected Quarter", quarters, index=quarters.index(default["quarter"]),
        key=f"quarter_{page_id}",
    )
    choices = [row for row in rows if row["quarter"] == quarter]
    ids = [row["context_id"] for row in choices]
    labels = {row["context_id"]: row["context_label"] for row in choices}
    default_id = default["context_id"] if default["quarter"] == quarter else ids[0]
    selected_id = st.sidebar.selectbox(
        "Contexto completo de filtros", ids, index=ids.index(default_id),
        format_func=labels.get, key=f"context_{page_id}_{quarter}",
    )
    st.sidebar.caption(
        "Cada opção corresponde a uma combinação de filtros avaliada na origem. "
        "Não sao criados filtros livres sobre resultados agregados."
    )
    return next(row for row in choices if row["context_id"] == selected_id)



def render_dashboard(doc: dict, mode: str, allow_downloads: bool) -> None:
    st.title(doc["page_title"])
    st.caption(f"Selected Quarter: {doc['quarter']} | {doc['context_label']} | Carga: {doc['as_of']}")
    if mode == "demo":
        st.warning(
            "DEMONSTRAÇÃO: todos os valores abaixo sao sintéticos. "
            "Não foram extraidos do Power BI nem representam resultados do CRM."
        )
    elif mode == "reference":
        st.warning(
            "REFERÊNCIA: pacote enviado pelo utilizador. Os atestados declarados no ficheiro "
            "não foram verificados automaticamente contra o Power BI."
        )
    else:
        st.info(
            "Resultados com atestados de homologação para este contexto fixo. "
            "A interface não reproduz automaticamente todas as interações do Power BI."
        )
    if doc["cards"]:
        for offset in range(0, len(doc["cards"]), 3):
            batch = doc["cards"][offset:offset + 3]
            for column, card in zip(st.columns(len(batch)), batch, strict=True):
                with column:
                    st.metric(card["label"], card["formatted_value"], help=card["measure"])
    st.caption(
        "Current reflete os dados carregados do trimestre selecionado. "
        "Previous e LY sao trimestres completos, sem ajuste por dias decorridos."
    )
    for chart in doc["charts"]:
        with st.container(border=True):
            st.subheader(chart["title"])
            st.plotly_chart(build_figure(chart), width="stretch", key=f"chart_{chart['id']}")
    if doc["tables"]:
        columns = st.columns(min(2, len(doc["tables"])))
        for index, table in enumerate(doc["tables"]):
            with columns[index % len(columns)]:
                st.subheader(table["title"])
                # Totais e linhas já chegam avaliados. Não existe soma ou pivot nesta camada.
                st.dataframe(pd.DataFrame(table["rows"], columns=table["columns"]),
                             hide_index=True, width="stretch")
    with st.expander("Períodos, filtros e rastreabilidade"):
        st.dataframe(pd.DataFrame(comparison_windows(doc["quarter"])),
                     hide_index=True, width="stretch")
        st.caption("As datas acima sao limites de calendario, não resultados de medidas DAX.")
        st.json(doc["filter_context"], expanded=False)
        st.json({"snapshot_id": doc["snapshot_id"], "release_id": doc["release_id"],
                 "source_sha256": doc["source_sha256"], "certification": doc["certification"]}, expanded=False)
    if doc["notes"]:
        with st.expander("Notas do resultado"):
            for note in doc["notes"]:
                st.text(note)
    if allow_downloads:
        st.download_button(
            "Exportar este resultado (JSON)",
            data=json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"crm_{doc['quarter']}_{doc['snapshot_id']}.json",
            mime="application/json",
        )


def render_coverage(manifest: dict) -> None:
    st.header("Regras e cobertura da migração")
    st.warning(
        "Esta entrega e uma interface de apresentacao com conector de resultados. "
        "O DAX, o Power Query e a RLS completos ainda não foram recuperados do PBIX. "
        "O catalogo abaixo não significa que as 23 páginas estejam implementadas."
    )
    for rule in manifest["guardrails"]:
        st.text(rule)
    st.dataframe(pd.DataFrame(manifest["pages"]).rename(columns={
        "id": "ID original", "title": "Página original", "hidden": "Oculta no PBIX"
    }), hide_index=True, width="stretch")
    st.caption("HTML customizado, Deneb, bookmarks, drillthrough e cross-filtering não estao reproduzidos.")
    st.code(manifest["source_sha256"], language=None)
