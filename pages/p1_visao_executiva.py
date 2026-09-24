import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import metrics as m

META_PROFICIENCIA = 0.80
ORDEM_AVALIACOES = ["AV1T-2026.1", "AV2T-2026.1", "AV3T-2026.2", "AV4T-2026.2"]
ORDEM_FAIXAS = ["1 - <40", "2 - 40 a 49.99", "3 - 50 a 54.99", "4 - 55 a 59.99", "5 - 60+"]
CORES_FAIXAS = {
    "1 - <40":        "#d62728",
    "2 - 40 a 49.99": "#ff7f0e",
    "3 - 50 a 54.99": "#ffdd57",
    "4 - 55 a 59.99": "#aec7e8",
    "5 - 60+":        "#2ca02c",
}


def _kpi(col, label, value, delta=None, delta_color="normal"):
    col.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def render(fact_prova, fact_area, dim_aluno, dim_avaliacao):
    st.title("📊 Visão Executiva Institucional")
    st.caption(
        "🗺️ **Responde:** Qual é o panorama geral da instituição e quais unidades estão abaixo da meta de 80%? "
        "| Navegue para 🏫 Análise por Unidade para aprofundar em cada campus."
    )

    df = fact_prova.merge(dim_aluno[["RA", "Unidade", "Serie", "Ciclo", "Enamedista"]], on="RA", how="left")

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
        sel_enamedistas = st.multiselect("Enamedista", sorted(dim_aluno["Enamedista"].unique()),
                                         default=sorted(dim_aluno["Enamedista"].unique()))
        sel_avaliacoes = st.multiselect("Avaliação", ORDEM_AVALIACOES, default=ORDEM_AVALIACOES)
        tipos_av = sorted(dim_avaliacao["Tipo_Avaliacao"].dropna().unique())
        sel_tipos = st.multiselect("Tipo de Avaliação", tipos_av, default=tipos_av)
        sel_faixas = st.multiselect("Faixa de Desempenho", ORDEM_FAIXAS, default=ORDEM_FAIXAS)
        conceitos_disp = ["1", "2", "3", "4", "5"]
        sel_conceitos = st.multiselect("Conceito PCP", conceitos_disp, default=conceitos_disp)

    # avaliacoes filtradas por tipo
    avs_tipo = dim_avaliacao[dim_avaliacao["Tipo_Avaliacao"].isin(sel_tipos)]["Avaliacao"].tolist()
    avs_ativas = [a for a in sel_avaliacoes if a in avs_tipo]

    mask_base = (
        df["Unidade"].isin(sel_unidades) &
        df["Serie"].isin(sel_series) &
        df["Ciclo"].isin(sel_ciclos) &
        df["Enamedista"].isin(sel_enamedistas) &
        df["Avaliacao"].isin(avs_ativas)
    )
    # df_base: sem filtros de classificação — usado para risco (critério sequencial por aluno)
    df_base = df[mask_base]
    # df_f: adiciona filtros de Faixa/Conceito para KPIs e gráficos de desempenho
    # faltosos preservados via 'Sem nota'/'Sem conceito' para manter contagens de participação
    mask_class = (
        df["Desempenho"].isin(sel_faixas + ["Sem nota"]) &
        df["Conceito_PCP"].isin(sel_conceitos + ["Sem conceito"])
    )
    df_f = df[mask_base & mask_class]

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.subheader("Indicadores Gerais")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _kpi(c1, "Total de Alunos",     str(m.total_alunos(df_f)))
    _kpi(c2, "Total Registros",     str(m.total_registros(df_f)))
    _kpi(c3, "Participações",       str(m.total_participantes(df_f)))
    _kpi(c4, "Ausências",           str(m.total_faltosos(df_f)))
    _kpi(c5, "% Participação",      f"{m.perc_participacao(df_f)*100:.1f}%")

    prof = m.perc_proficientes(df_f)
    _kpi(c6, "% Proficientes", f"{prof*100:.1f}%",
         f"{(prof - META_PROFICIENCIA)*100:+.1f} pp vs meta 80%",
         delta_color="normal" if prof >= META_PROFICIENCIA else "inverse")

    c7, c8, c9, c10, c11 = st.columns(5)
    _kpi(c7,  "% Abaixo de 50", f"{m.perc_abaixo_50(df_f)*100:.1f}%")
    _kpi(c8,  "Nota Média",     f"{m.nota_media(df_f):.1f}")
    _kpi(c9,  "Nota Mediana",   f"{m.nota_mediana(df_f):.1f}")
    _kpi(c10, "Maior Nota",     f"{m.maior_nota(df_f):.0f}")
    _kpi(c11, "Menor Nota",     f"{m.menor_nota(df_f):.0f}")

    c12, c13, c14 = st.columns(3)
    _kpi(c12, "PCPc Médio", f"{m.pcpc_medio(df_f):.3f}")
    # risco calculado sobre df_base (todas as avaliações do aluno, sem filtro de classificação)
    n_risco = m.total_alunos_em_risco(df_base)
    perc_risco = m.perc_alunos_em_risco(df_base)
    _kpi(c13, "Alunos em Risco", str(n_risco),
         f"{perc_risco*100:.1f}% do total", delta_color="inverse" if n_risco > 0 else "off")
    # gap calculado com fa_f (fact_area filtrado pelos RAs presentes em df_f)
    fa_f_kpi = fact_area[fact_area["RA"].isin(df_f[df_f["Status_Participacao"] == "Presente"]["RA"].unique())]
    _kpi(c14, "Gap Melhor/Pior Área",
         f"{m.gap_melhor_pior_area(fa_f_kpi, df_f):.1f} pp")

    st.divider()

    # ── Proficiência por unidade vs meta | Distribuição por faixa ─────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Proficiência por Unidade vs Meta (80%)")
        prof_u = m.proficiencia_por_grupo(df_f, ["Unidade"]).sort_values("Proficiencia")
        cores = ["#2ca02c" if v >= 80 else "#d62728" for v in prof_u["Proficiencia"]]
        fig = go.Figure(go.Bar(
            x=prof_u["Proficiencia"], y=prof_u["Unidade"], orientation="h",
            marker_color=cores,
            text=prof_u["Proficiencia"].map(lambda v: f"{v:.1f}%"), textposition="outside",
        ))
        fig.add_vline(x=80, line_dash="dash", line_color="gray",
                      annotation_text="Meta 80%", annotation_position="top right")
        fig.update_layout(xaxis=dict(range=[0, 105], title="% Proficientes"),
                          yaxis_title=None, margin=dict(l=0, r=40, t=10, b=10), height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        tab_faixa, tab_conceito = st.tabs(["Faixa de Desempenho", "Conceito PCP"])

        with tab_faixa:
            dist = m.distribuicao_faixa(df_f)
            dist["Faixa"] = pd.Categorical(
                dist["Faixa"],
                categories=ORDEM_FAIXAS, ordered=True)
            dist = dist.sort_values("Faixa")
            fig_pie = go.Figure(go.Pie(
                labels=dist["Faixa"].astype(str), values=dist["Qtd"],
                marker_colors=[CORES_FAIXAS.get(str(f), "#999") for f in dist["Faixa"]],
                hole=0.4, textinfo="percent+label", sort=False,
            ))
            fig_pie.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=10), height=280)
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab_conceito:
            CORES_CONCEITO = {"1": "#d62728", "2": "#ff7f0e", "3": "#ffdd57",
                              "4": "#aec7e8", "5": "#2ca02c"}
            pres_f = m._presentes(df_f)
            conc = (pres_f["Conceito_PCP"].astype(str)
                    .value_counts().reset_index()
                    .rename(columns={"index": "Conceito", "Conceito_PCP": "Qtd"}))
            conc.columns = ["Conceito", "Qtd"]
            conc = conc[conc["Conceito"].isin(["1","2","3","4","5"])].sort_values("Conceito")
            fig_conc = go.Figure(go.Pie(
                labels=conc["Conceito"].map(lambda c: f"Conceito {c}"),
                values=conc["Qtd"],
                marker_colors=[CORES_CONCEITO.get(c, "#999") for c in conc["Conceito"]],
                hole=0.4, textinfo="percent+label", sort=False,
            ))
            fig_conc.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=10), height=280)
            st.plotly_chart(fig_conc, use_container_width=True)

    st.divider()

    # ── Evolução nota média | Evolução proficiência — por unidade ────────────
    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Evolução da Nota Média por Unidade")
        evo_u = m.nota_media_por_grupo(df_f, ["Unidade", "Avaliacao"])
        evo_u["Avaliacao"] = evo_u["Avaliacao"].astype(str)
        fig_line = px.line(evo_u, x="Avaliacao", y="Nota_Media", color="Unidade", markers=True,
                           labels={"Avaliacao": "Avaliação", "Nota_Media": "Nota Média"})
        fig_line.add_hline(y=60, line_dash="dash", line_color="green",
                           annotation_text="Proficiência (60)", annotation_position="bottom right")
        fig_line.update_layout(yaxis=dict(range=[30, 85]),
                               legend=dict(orientation="h", y=-0.3),
                               margin=dict(l=0, r=0, t=10, b=10), height=320)
        st.plotly_chart(fig_line, use_container_width=True)

    with col_d:
        st.subheader("Evolução da Proficiência por Unidade")
        evo_prof_u = m.proficiencia_por_grupo(df_f, ["Unidade", "Avaliacao"])
        evo_prof_u["Avaliacao"] = evo_prof_u["Avaliacao"].astype(str)
        fig_prof = px.line(evo_prof_u, x="Avaliacao", y="Proficiencia", color="Unidade",
                           markers=True,
                           labels={"Avaliacao": "Avaliação", "Proficiencia": "% Proficientes"})
        fig_prof.add_hline(y=80, line_dash="dash", line_color="red",
                           annotation_text="Meta 80%", annotation_position="bottom right")
        fig_prof.update_layout(yaxis=dict(range=[0, 105]),
                               legend=dict(orientation="h", y=-0.3),
                               margin=dict(l=0, r=0, t=10, b=10), height=320)
        st.plotly_chart(fig_prof, use_container_width=True)

    st.divider()

    # ── Heatmap nota média unidade × avaliação ────────────────────────────────
    st.subheader("Nota Média por Unidade e Avaliação")
    heat = m.nota_media_por_grupo(df_f, ["Unidade", "Avaliacao"])
    heat["Avaliacao"] = heat["Avaliacao"].astype(str)
    heat_pivot = heat.pivot(index="Unidade", columns="Avaliacao", values="Nota_Media")
    heat_pivot = heat_pivot[[c for c in ORDEM_AVALIACOES if c in heat_pivot.columns]]
    fig_heat = go.Figure(go.Heatmap(
        z=heat_pivot.values, x=heat_pivot.columns.tolist(), y=heat_pivot.index.tolist(),
        colorscale="RdYlGn", zmid=60,
        text=[[f"{v:.1f}" for v in row] for row in heat_pivot.values],
        texttemplate="%{text}", colorbar=dict(title="Nota Média"),
    ))
    fig_heat.update_layout(xaxis_title="Avaliação", yaxis_title=None,
                           margin=dict(l=0, r=0, t=10, b=10), height=280)
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # ── Desempenho por área — visão institucional ────────────────────────────────
    st.subheader("📚 Desempenho por Área de Conhecimento")
    fa_f = fact_area[fact_area["RA"].isin(df_f["RA"].unique())]

    col_e, col_f = st.columns([2, 3])

    with col_e:
        # ranking das 5 áreas com barra horizontal
        medias_inst = m.perc_medio_por_area(fa_f, df_f) * 100
        medias_inst = medias_inst.sort_values()
        cores_area = ["#d62728" if v == medias_inst.min() else
                      "#2ca02c" if v == medias_inst.max() else "#1f77b4"
                      for v in medias_inst]
        fig_rank = go.Figure(go.Bar(
            x=medias_inst.values, y=medias_inst.index, orientation="h",
            marker_color=cores_area,
            text=[f"{v:.1f}%" for v in medias_inst.values], textposition="outside",
        ))
        fig_rank.add_vline(x=60, line_dash="dash", line_color="green",
                           annotation_text="60%", annotation_position="top right")
        fig_rank.update_layout(
            xaxis=dict(range=[0, 85], title="% Acerto Médio"),
            yaxis_title=None, margin=dict(l=0, r=50, t=10, b=10), height=260,
        )
        st.plotly_chart(fig_rank, use_container_width=True)
        gap = medias_inst.max() - medias_inst.min()
        st.caption(
            f"✅ Mais forte: **{medias_inst.idxmax()}** ({medias_inst.max():.1f}%)    "
            f"⚠️ Mais fraca: **{medias_inst.idxmin()}** ({medias_inst.min():.1f}%)    "
            f"Gap: **{gap:.1f} pp**"
        )

    with col_f:
        # heatmap unidade × área
        da_f_inst = m._enrich_area(fa_f, df_f).merge(
            dim_aluno[["RA", "Unidade"]], on="RA", how="left"
        )
        area_u = m.perc_area_por_grupo(da_f_inst, df_f, ["Unidade", "Area"])
        heat_area = area_u.pivot(index="Unidade", columns="Area", values="Perc_Acerto")
        fig_ha = go.Figure(go.Heatmap(
            z=heat_area.values,
            x=heat_area.columns.tolist(),
            y=heat_area.index.tolist(),
            colorscale="RdYlGn", zmid=60,
            text=[[f"{v:.1f}%" for v in row] for row in heat_area.values],
            texttemplate="%{text}", colorbar=dict(title="% Acerto"),
        ))
        fig_ha.update_layout(
            xaxis_title="Área", yaxis_title=None,
            margin=dict(l=0, r=0, t=10, b=10), height=260,
        )
        st.plotly_chart(fig_ha, use_container_width=True)

    st.divider()

    # ── Alunos em risco — distribuição por grupo ───────────────────────────────
    st.subheader("🚨 Alunos em Risco — Distribuição por Grupo")
    st.caption(
        "Critério: nota < 50 em ≥2 avaliações + tendência de queda (AV2 < AV1 ou AV4 < AV3). "
        "Severidade: 🟡 Moderado = 2 av. | 🟠 Alto = 3 av. | 🔴 Crítico = 4 av."
    )

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        # risco por unidade
        risco_u = m.risco_por_grupo(df_base, dim_aluno, ["Unidade"])
        total_u = df_base.groupby("Unidade")["RA"].nunique().reset_index(name="Total")
        risco_u = risco_u.merge(total_u, on="Unidade", how="left")
        risco_u["%"] = (risco_u["Alunos em Risco"] / risco_u["Total"] * 100).round(1)
        risco_u = risco_u.sort_values("Alunos em Risco", ascending=True)
        fig_ru = go.Figure(go.Bar(
            x=risco_u["Alunos em Risco"], y=risco_u["Unidade"], orientation="h",
            marker_color="#d62728",
            text=risco_u.apply(lambda r: f"{int(r['Alunos em Risco'])} ({r['%']:.1f}%)", axis=1),
            textposition="outside",
        ))
        fig_ru.update_layout(
            title="Por Unidade", xaxis=dict(range=[0, risco_u["Alunos em Risco"].max() * 1.4]),
            yaxis_title=None, margin=dict(l=0, r=80, t=30, b=10), height=280,
        )
        st.plotly_chart(fig_ru, use_container_width=True)
        # drill P1 → P4: seleciona unidade e navega para ficha de alunos em risco
        st.caption("Ver alunos em risco de uma unidade:")
        unidades_risco = risco_u.sort_values("%", ascending=False)["Unidade"].tolist()
        col_sel, col_btn = st.columns([3, 1])
        unidade_drill = col_sel.selectbox(
            "Unidade", unidades_risco, key="p1_drill_unidade", label_visibility="collapsed"
        )
        if col_btn.button("👤 Ver alunos", key="p1_drill_btn"):
            st.session_state["pagina"] = "🏫 Análise por Unidade"
            st.session_state["drill_unidade"] = unidade_drill
            st.rerun()

    with col_r2:
        # risco por ciclo
        df_base_ciclo = df_base.drop_duplicates("RA")[["RA", "Ciclo"]]
        risco_c = m.risco_por_grupo(df_base, dim_aluno, ["Ciclo"])
        total_c = df_base_ciclo.groupby("Ciclo")["RA"].nunique().reset_index(name="Total")
        risco_c = risco_c.merge(total_c, on="Ciclo", how="left")
        risco_c["%"] = (risco_c["Alunos em Risco"] / risco_c["Total"] * 100).round(1)
        fig_rc = go.Figure(go.Bar(
            x=risco_c["Ciclo"],
            y=risco_c["Alunos em Risco"],
            marker_color=["#1f77b4", "#ff7f0e"],
            text=risco_c.apply(lambda r: f"{int(r['Alunos em Risco'])} ({r['%']:.1f}%)", axis=1),
            textposition="outside",
        ))
        fig_rc.update_layout(
            title="Por Ciclo", yaxis=dict(range=[0, risco_c["Alunos em Risco"].max() * 1.4]),
            xaxis_title=None, margin=dict(l=0, r=0, t=30, b=10), height=280,
        )
        st.plotly_chart(fig_rc, use_container_width=True)

    with col_r3:
        # distribuicao de severidade
        sev = m.severidade_risco(df_base)
        if not sev.empty:
            sev_count = sev["Label"].value_counts().reset_index()
            sev_count.columns = ["Severidade", "Alunos"]
            ordem_sev = ["🟡 Moderado (2 av.)", "🟠 Alto (3 av.)", "🔴 Crítico (4 av.)"]
            sev_count["Severidade"] = pd.Categorical(
                sev_count["Severidade"], categories=ordem_sev, ordered=True
            )
            sev_count = sev_count.sort_values("Severidade")
            fig_sev = go.Figure(go.Bar(
                x=sev_count["Severidade"].astype(str),
                y=sev_count["Alunos"],
                marker_color=["#ffdd57", "#ff7f0e", "#d62728"],
                text=sev_count["Alunos"], textposition="outside",
            ))
            fig_sev.update_layout(
                title="Por Severidade",
                yaxis=dict(range=[0, sev_count["Alunos"].max() * 1.4]),
                xaxis_title=None, margin=dict(l=0, r=0, t=30, b=10), height=280,
            )
            st.plotly_chart(fig_sev, use_container_width=True)
