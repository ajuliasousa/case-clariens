import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import metrics as m

ORDEM_AVALIACOES = ["AV1T-2026.1", "AV2T-2026.1", "AV3T-2026.2", "AV4T-2026.2"]
CORES_UNIDADES = {
    "ARAGUARI": "#1f77b4", "BARREIRAS": "#ff7f0e", "EUNAPOLIS": "#2ca02c",
    "ITUMBIARA": "#d62728", "SALVADOR": "#9467bd", "VITORIA DA CONQUISTA": "#8c564b",
}


def _multiline(fig, df, x_col, y_col, group_col, cores, marker_size=7):
    for grupo in df[group_col].unique():
        d = df[df[group_col] == grupo].sort_values(x_col)
        fig.add_trace(go.Scatter(
            x=d[x_col], y=d[y_col], mode="lines+markers", name=str(grupo),
            line=dict(color=cores.get(str(grupo))), marker=dict(size=marker_size),
        ))


def render(fact_prova, fact_area, dim_aluno, dim_avaliacao):
    st.title("📅 Análise Temporal")
    st.caption(
        "🗺️ **Responde:** Existe melhora ou piora ao longo das avaliações? Ela ocorre de forma homogênea entre unidades? "
        "| Diagnóstica vs Desempenho · Evolução por período letivo · Ciclo Básico vs Clínico."
    )

    dp = (fact_prova
          .merge(dim_aluno[["RA", "Unidade", "Serie", "Ciclo"]], on="RA", how="left")
          .merge(dim_avaliacao[["Avaliacao", "Tipo_Avaliacao", "Periodo_Letivo"]], on="Avaliacao", how="left"))
    da = m._enrich_area(fact_area, fact_prova).merge(
        dim_aluno[["RA", "Unidade", "Serie", "Ciclo"]], on="RA", how="left"
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("Filtros")
        sel_unidades = st.multiselect("Unidade", sorted(dim_aluno["Unidade"].unique()),
                                      default=sorted(dim_aluno["Unidade"].unique()))
        sel_series = st.multiselect("Série", sorted(dim_aluno["Serie"].unique()),
                                    default=sorted(dim_aluno["Serie"].unique()))
        sel_ciclos = st.multiselect("Ciclo", sorted(dim_aluno["Ciclo"].unique()),
                                    default=sorted(dim_aluno["Ciclo"].unique()))
        tipos_av = sorted(dim_avaliacao["Tipo_Avaliacao"].dropna().unique())
        sel_tipos = st.multiselect("Tipo de Avaliação", tipos_av, default=tipos_av)

    avs_ativas = dim_avaliacao[dim_avaliacao["Tipo_Avaliacao"].isin(sel_tipos)]["Avaliacao"].tolist()

    dp_f = dp[
        dp["Unidade"].isin(sel_unidades) &
        dp["Serie"].isin(sel_series) &
        dp["Ciclo"].isin(sel_ciclos) &
        dp["Avaliacao"].isin(avs_ativas)
    ]
    da_f = da[
        da["Unidade"].isin(sel_unidades) &
        da["Serie"].isin(sel_series) &
        da["Ciclo"].isin(sel_ciclos) &
        da["Avaliacao"].isin(avs_ativas)
    ]

    # ── Nota média por unidade | por série ────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Nota Média por Avaliação — por Unidade")
        evo_u = m.nota_media_por_grupo(dp_f, ["Unidade", "Avaliacao"])
        evo_u["Avaliacao"] = evo_u["Avaliacao"].astype(str)
        fig = go.Figure()
        _multiline(fig, evo_u, "Avaliacao", "Nota_Media", "Unidade", CORES_UNIDADES)
        fig.add_hline(y=60, line_dash="dash", line_color="green",
                      annotation_text="60", annotation_position="top left")
        fig.update_layout(yaxis=dict(range=[40, 85], title="Nota Média"),
                          xaxis_title="Avaliação", legend=dict(orientation="h", y=-0.3),
                          margin=dict(l=0, r=0, t=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Nota Média por Avaliação — por Série")
        evo_s = m.nota_media_por_grupo(dp_f, ["Serie", "Avaliacao"])
        evo_s["Avaliacao"] = evo_s["Avaliacao"].astype(str)
        evo_s["Serie"] = evo_s["Serie"].astype(str)
        fig_s = px.line(evo_s, x="Avaliacao", y="Nota_Media", color="Serie", markers=True,
                        labels={"Nota_Media": "Nota Média", "Avaliacao": "Avaliação", "Serie": "Série"})
        fig_s.add_hline(y=60, line_dash="dash", line_color="green",
                        annotation_text="60", annotation_position="top left")
        fig_s.update_layout(yaxis=dict(range=[40, 85]), legend=dict(orientation="h", y=-0.3),
                            margin=dict(l=0, r=0, t=10, b=10), height=340)
        st.plotly_chart(fig_s, use_container_width=True)

    st.divider()

    # ── Diagnóstica vs Desempenho ─────────────────────────────────────────────
    st.subheader("Diagnóstica vs Desempenho")
    col_c, col_d = st.columns(2)

    with col_c:
        tipo_nota = m.nota_media_por_grupo(dp_f, ["Tipo_Avaliacao", "Avaliacao"])
        tipo_nota["Avaliacao"] = tipo_nota["Avaliacao"].astype(str)
        fig_t = px.bar(tipo_nota, x="Avaliacao", y="Nota_Media", color="Tipo_Avaliacao",
                       barmode="group",
                       labels={"Nota_Media": "Nota Média", "Avaliacao": "Avaliação",
                               "Tipo_Avaliacao": "Tipo"},
                       color_discrete_map={"Diagnóstica": "#1f77b4", "Desempenho": "#ff7f0e"})
        fig_t.add_hline(y=60, line_dash="dash", line_color="green")
        fig_t.update_layout(yaxis=dict(range=[40, 85]), legend=dict(orientation="h", y=-0.3),
                            margin=dict(l=0, r=0, t=10, b=10), height=300)
        st.plotly_chart(fig_t, use_container_width=True)

    with col_d:
        tipo_prof = m.proficiencia_por_grupo(dp_f, ["Tipo_Avaliacao", "Avaliacao"])
        tipo_prof["Avaliacao"] = tipo_prof["Avaliacao"].astype(str)
        fig_tp = px.bar(tipo_prof, x="Avaliacao", y="Proficiencia", color="Tipo_Avaliacao",
                        barmode="group",
                        labels={"Proficiencia": "% Proficientes", "Avaliacao": "Avaliação",
                                "Tipo_Avaliacao": "Tipo"},
                        color_discrete_map={"Diagnóstica": "#1f77b4", "Desempenho": "#ff7f0e"})
        fig_tp.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Meta 80%")
        fig_tp.update_layout(yaxis=dict(range=[0, 105]), legend=dict(orientation="h", y=-0.3),
                             margin=dict(l=0, r=0, t=10, b=10), height=300)
        st.plotly_chart(fig_tp, use_container_width=True)

    # ── Cruzamento: alunos em risco × tipo de avaliação ──────────────────────
    st.markdown("**Alunos em Risco por Tipo de Avaliação**")
    st.caption(
        "Compara nota média e % abaixo de 50 dos alunos em risco vs sem risco, "
        "separado por Diagnóstica e Desempenho."
    )

    import pandas as _pd
    ras_risco_f = m.alunos_em_risco(dp_f)
    dp_tipo = dp_f.copy()
    dp_tipo["Grupo"] = dp_tipo["RA"].isin(ras_risco_f).map(
        {True: "🔴 Em Risco", False: "🟢 Sem Risco"}
    )

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        nota_tg = m.nota_media_por_grupo(dp_tipo, ["Tipo_Avaliacao", "Grupo"])
        fig_ntg = px.bar(
            nota_tg, x="Tipo_Avaliacao", y="Nota_Media", color="Grupo", barmode="group",
            labels={"Nota_Media": "Nota Média", "Tipo_Avaliacao": "Tipo", "Grupo": ""},
            color_discrete_map={"🔴 Em Risco": "#d62728", "🟢 Sem Risco": "#2ca02c"},
            text_auto=".1f",
        )
        fig_ntg.add_hline(y=60, line_dash="dash", line_color="green",
                          annotation_text="Proficiência (60)")
        fig_ntg.update_layout(
            yaxis=dict(range=[0, 80], title="Nota Média"),
            xaxis_title=None, legend=dict(orientation="h", y=-0.25),
            margin=dict(l=0, r=0, t=10, b=10), height=300,
        )
        st.plotly_chart(fig_ntg, use_container_width=True)

    with col_r2:
        rows_ab = []
        for tipo in dp_tipo["Tipo_Avaliacao"].dropna().unique():
            for grupo in ["🔴 Em Risco", "🟢 Sem Risco"]:
                sub = m._presentes(dp_tipo[
                    (dp_tipo["Tipo_Avaliacao"] == tipo) & (dp_tipo["Grupo"] == grupo)
                ])
                if len(sub):
                    perc = (sub["Nota_Avalia"].astype(float) < 50).sum() / len(sub) * 100
                    rows_ab.append({"Tipo": tipo, "Grupo": grupo, "% Abaixo 50": round(perc, 1)})
        df_ab = _pd.DataFrame(rows_ab)
        fig_ab = px.bar(
            df_ab, x="Tipo", y="% Abaixo 50", color="Grupo", barmode="group",
            labels={"% Abaixo 50": "% Abaixo de 50", "Tipo": "Tipo", "Grupo": ""},
            color_discrete_map={"🔴 Em Risco": "#d62728", "🟢 Sem Risco": "#2ca02c"},
            text_auto=".1f",
        )
        fig_ab.add_hline(y=50, line_dash="dash", line_color="orange",
                         annotation_text="50%")
        fig_ab.update_layout(
            yaxis=dict(range=[0, 105], title="% Abaixo de 50"),
            xaxis_title=None, legend=dict(orientation="h", y=-0.25),
            margin=dict(l=0, r=0, t=10, b=10), height=300,
        )
        st.plotly_chart(fig_ab, use_container_width=True)

    if ras_risco_f:
        st.caption(
            f"⚠️ Alunos em risco ({len(ras_risco_f)}) têm ~77% dos registros abaixo de 50 "
            "**tanto em Diagnóstica quanto em Desempenho** — o problema é estrutural, "
            "não específico de um tipo de avaliação."
        )


    st.divider()

    # ── Proficiência por unidade | PCPc por unidade ───────────────────────────
    col_e, col_f = st.columns(2)

    with col_e:
        st.subheader("Evolução da Proficiência por Unidade")
        prof_u = m.proficiencia_por_grupo(dp_f, ["Unidade", "Avaliacao"])
        prof_u["Avaliacao"] = prof_u["Avaliacao"].astype(str)
        fig_pu = go.Figure()
        _multiline(fig_pu, prof_u, "Avaliacao", "Proficiencia", "Unidade", CORES_UNIDADES)
        fig_pu.add_hline(y=80, line_dash="dash", line_color="red",
                         annotation_text="Meta 80%", annotation_position="top left")
        fig_pu.update_layout(yaxis=dict(range=[0, 105], title="% Proficientes"),
                             xaxis_title="Avaliação", legend=dict(orientation="h", y=-0.3),
                             margin=dict(l=0, r=0, t=10, b=10), height=340)
        st.plotly_chart(fig_pu, use_container_width=True)

    with col_f:
        st.subheader("Evolução do PCPc Médio por Unidade")
        pcpc_u = m.pcpc_por_grupo(dp_f, ["Unidade", "Avaliacao"])
        pcpc_u["Avaliacao"] = pcpc_u["Avaliacao"].astype(str)
        fig_pc = go.Figure()
        _multiline(fig_pc, pcpc_u, "Avaliacao", "PCPc_Medio", "Unidade", CORES_UNIDADES)
        fig_pc.add_hline(y=0.60, line_dash="dash", line_color="green",
                         annotation_text="Conceito 3 (0,60)", annotation_position="top left")
        fig_pc.update_layout(yaxis=dict(range=[0.3, 0.9], title="PCPc Médio"),
                             xaxis_title="Avaliação", legend=dict(orientation="h", y=-0.3),
                             margin=dict(l=0, r=0, t=10, b=10), height=340)
        st.plotly_chart(fig_pc, use_container_width=True)

    st.divider()

    # ── Evolução por área — agregada e por unidade ─────────────────────────────
    st.subheader("Evolução do % de Acerto por Área")

    tab_agr, tab_uni = st.tabs(["Instituição", "Por Unidade"])

    with tab_agr:
        evo_area = m.perc_area_por_grupo(da_f, dp_f, ["Avaliacao"])
        evo_area["Avaliacao"] = evo_area["Avaliacao"].astype(str)
        fig_area = px.line(evo_area, x="Avaliacao", y="Perc_Acerto", color="Area", markers=True,
                           labels={"Avaliacao": "Avaliação", "Perc_Acerto": "% Acerto", "Area": "Área"})
        fig_area.add_hline(y=60, line_dash="dash", line_color="green",
                           annotation_text="60%", annotation_position="top left")
        fig_area.update_layout(yaxis=dict(range=[40, 85]), legend=dict(orientation="h", y=-0.2),
                               margin=dict(l=0, r=0, t=10, b=10), height=320)
        st.plotly_chart(fig_area, use_container_width=True)

    with tab_uni:
        st.caption("Selecione uma área para ver a evolução de cada unidade ao longo das avaliações.")
        AREAS = ["CIR", "CM", "GO", "PED", "PREV"]
        area_sel = st.selectbox("Selecionar Área", AREAS, key="p3_area_sel")
        evo_area_u = m.perc_area_por_grupo(da_f, dp_f, ["Unidade", "Avaliacao"])
        evo_area_u["Avaliacao"] = evo_area_u["Avaliacao"].astype(str)
        evo_area_u_fil = evo_area_u[evo_area_u["Area"] == area_sel]
        fig_au = go.Figure()
        _multiline(fig_au, evo_area_u_fil, "Avaliacao", "Perc_Acerto", "Unidade", CORES_UNIDADES)
        fig_au.add_hline(y=60, line_dash="dash", line_color="green",
                         annotation_text="60%", annotation_position="top left")
        fig_au.update_layout(
            yaxis=dict(range=[30, 90], title=f"% Acerto — {area_sel}"),
            xaxis_title="Avaliação", legend=dict(orientation="h", y=-0.3),
            margin=dict(l=0, r=0, t=10, b=10), height=340,
        )
        st.plotly_chart(fig_au, use_container_width=True)

    st.divider()

    # ── Comparativo por Período Letivo ─────────────────────────────────────────
    st.subheader("📆 Comparativo por Período Letivo")
    st.caption("2026.1 = AV1 (Diagnóstica) + AV2 (Desempenho) · 2026.2 = AV3 (Diagnóstica) + AV4 (Desempenho)")

    CORES_PERIODO = {"20261": "#1f77b4", "20262": "#ff7f0e"}
    LABEL_PERIODO = {"20261": "2026.1 (1º sem.)", "20262": "2026.2 (2º sem.)"}
    dp_f["Periodo_Label"] = dp_f["Periodo_Letivo"].astype(str).map(LABEL_PERIODO)

    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
        st.markdown("**Nota Média por Período e Tipo**")
        pl_nota = m.nota_media_por_grupo(dp_f, ["Periodo_Letivo", "Tipo_Avaliacao"])
        pl_nota["Período"] = pl_nota["Periodo_Letivo"].astype(str).map(LABEL_PERIODO)
        fig_pl = px.bar(pl_nota, x="Período", y="Nota_Media", color="Tipo_Avaliacao",
                        barmode="group",
                        labels={"Nota_Media": "Nota Média", "Tipo_Avaliacao": "Tipo"},
                        color_discrete_map={"Diagnóstica": "#1f77b4", "Desempenho": "#ff7f0e"})
        fig_pl.add_hline(y=60, line_dash="dash", line_color="green")
        fig_pl.update_layout(yaxis=dict(range=[55, 70]), legend=dict(orientation="h", y=-0.3),
                             margin=dict(l=0, r=0, t=10, b=10), height=300)
        st.plotly_chart(fig_pl, use_container_width=True)

    with col_p2:
        st.markdown("**% Proficientes por Período e Tipo**")
        pl_prof = m.proficiencia_por_grupo(dp_f, ["Periodo_Letivo", "Tipo_Avaliacao"])
        pl_prof["Período"] = pl_prof["Periodo_Letivo"].astype(str).map(LABEL_PERIODO)
        fig_pp = px.bar(pl_prof, x="Período", y="Proficiencia", color="Tipo_Avaliacao",
                        barmode="group",
                        labels={"Proficiencia": "% Proficientes", "Tipo_Avaliacao": "Tipo"},
                        color_discrete_map={"Diagnóstica": "#1f77b4", "Desempenho": "#ff7f0e"})
        fig_pp.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Meta 80%")
        fig_pp.update_layout(yaxis=dict(range=[0, 105]), legend=dict(orientation="h", y=-0.3),
                             margin=dict(l=0, r=0, t=10, b=10), height=300)
        st.plotly_chart(fig_pp, use_container_width=True)

    with col_p3:
        st.markdown("**PCPc Médio por Período e Tipo**")
        pl_pcpc = m.pcpc_por_grupo(dp_f, ["Periodo_Letivo", "Tipo_Avaliacao"])
        pl_pcpc["Período"] = pl_pcpc["Periodo_Letivo"].astype(str).map(LABEL_PERIODO)
        fig_pc2 = px.bar(pl_pcpc, x="Período", y="PCPc_Medio", color="Tipo_Avaliacao",
                         barmode="group",
                         labels={"PCPc_Medio": "PCPc Médio", "Tipo_Avaliacao": "Tipo"},
                         color_discrete_map={"Diagnóstica": "#1f77b4", "Desempenho": "#ff7f0e"})
        fig_pc2.add_hline(y=0.60, line_dash="dash", line_color="green",
                          annotation_text="Conceito 3")
        fig_pc2.update_layout(yaxis=dict(range=[0.5, 0.75]), legend=dict(orientation="h", y=-0.3),
                              margin=dict(l=0, r=0, t=10, b=10), height=300)
        st.plotly_chart(fig_pc2, use_container_width=True)

    # proficiência por unidade × período letivo — heatmap
    st.markdown("**Proficiência por Unidade e Período Letivo (%)**")
    pl_u = m.proficiencia_por_grupo(dp_f, ["Unidade", "Periodo_Letivo"])
    pl_u["Período"] = pl_u["Periodo_Letivo"].astype(str).map(LABEL_PERIODO)
    heat_pl = pl_u.pivot(index="Unidade", columns="Período", values="Proficiencia")
    fig_hpl = go.Figure(go.Heatmap(
        z=heat_pl.values, x=heat_pl.columns.tolist(), y=heat_pl.index.tolist(),
        colorscale="RdYlGn", zmid=80,
        text=[[f"{v:.1f}%" for v in row] for row in heat_pl.values],
        texttemplate="%{text}", colorbar=dict(title="% Profic."),
    ))
    fig_hpl.update_layout(xaxis_title=None, yaxis_title=None,
                          margin=dict(l=0, r=0, t=10, b=10), height=260)
    st.plotly_chart(fig_hpl, use_container_width=True)

    st.divider()

    # ── Ciclo Básico vs Clínico ───────────────────────────────────────────────
    st.subheader("Ciclo Básico (9–10) vs Ciclo Clínico (11–12)")
    col_g, col_h = st.columns(2)
    CORES_CICLO = {"Ciclo Básico": "#1f77b4", "Ciclo Clínico": "#ff7f0e"}

    with col_g:
        ciclo_nota = m.nota_media_por_grupo(dp_f, ["Ciclo", "Avaliacao"])
        ciclo_nota["Avaliacao"] = ciclo_nota["Avaliacao"].astype(str)
        fig_cn = px.line(ciclo_nota, x="Avaliacao", y="Nota_Media", color="Ciclo", markers=True,
                         labels={"Nota_Media": "Nota Média", "Avaliacao": "Avaliação"},
                         color_discrete_map=CORES_CICLO)
        fig_cn.add_hline(y=60, line_dash="dash", line_color="green")
        fig_cn.update_layout(yaxis=dict(range=[40, 85]), legend=dict(orientation="h", y=-0.3),
                             margin=dict(l=0, r=0, t=10, b=10), height=300)
        st.plotly_chart(fig_cn, use_container_width=True)

    with col_h:
        ciclo_prof = m.proficiencia_por_grupo(dp_f, ["Ciclo", "Avaliacao"])
        ciclo_prof["Avaliacao"] = ciclo_prof["Avaliacao"].astype(str)
        fig_cp = px.line(ciclo_prof, x="Avaliacao", y="Proficiencia", color="Ciclo", markers=True,
                         labels={"Proficiencia": "% Proficientes", "Avaliacao": "Avaliação"},
                         color_discrete_map=CORES_CICLO)
        fig_cp.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Meta 80%")
        fig_cp.update_layout(yaxis=dict(range=[0, 105]), legend=dict(orientation="h", y=-0.3),
                             margin=dict(l=0, r=0, t=10, b=10), height=300)
        st.plotly_chart(fig_cp, use_container_width=True)
