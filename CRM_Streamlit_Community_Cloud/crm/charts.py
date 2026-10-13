from __future__ import annotations

import html
import plotly.graph_objects as go


def build_figure(chart: dict) -> go.Figure:
    figure = go.Figure()
    for trace in chart["traces"]:
        # Apenas texto e arrays validados. Nunca aceita código, HTML ou specs executaveis.
        common = dict(
            x=[html.escape(x) for x in trace["x"]], y=trace["y"],
            name=html.escape(trace["name"]), yaxis=trace.get("axis", "y"),
            customdata=[html.escape(v) for v in trace["display_y"]],
            hovertemplate="%{x}<br>%{customdata}<extra>%{fullData.name}</extra>",
        )
        if trace["kind"] == "bar":
            figure.add_trace(go.Bar(**common))
        else:
            figure.add_trace(go.Scatter(**common, mode="lines+markers", connectgaps=False))
    percent = lambda key: ".1%" if chart.get(key) == "percent" else ",.0f"
    figure.update_layout(
        height=360, margin=dict(l=20, r=20, t=30, b=30),
        barmode=chart.get("barmode", "group"),
        xaxis=dict(title=html.escape(chart.get("x_label", "")), type="category"),
        yaxis=dict(title=html.escape(chart.get("y_label", "")), tickformat=percent("y_format")),
        legend=dict(orientation="h", y=1.16, x=0),
        hovermode="x unified",
    )
    if any(t.get("axis") == "y2" for t in chart["traces"]):
        figure.update_layout(yaxis2=dict(
            title=html.escape(chart.get("y2_label", "")), tickformat=percent("y2_format"),
            overlaying="y", side="right", showgrid=False,
        ))
    return figure

