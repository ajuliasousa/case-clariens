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
AREAS = ["CIR", "CM", "GO", "PED", "PREV"]


def _kpi(col, label, value, delta=None, delta_color="normal"):
    col.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def render(fact_prova, fact_area, dim_aluno, dim_avaliacao):
    st.title("🏫 Análise por Unidade")
    st.caption(
        "🗺️ **Responde:** Quais unidades precisam de intervenção e quais áreas explicam? "
        "| Use a tab Comparativo para visão geral · tab Detalhe para aprofundar · botão 'Ver →' para ficha do aluno."
    )

    dp_all = fact_prova.merge(
        dim_aluno[["RA", "Unidade", "Serie", "Ciclo", "Enamedista"]], on="RA", how="left"
    )
    da_all = m._enrich_area(fact_area, fact_prova).merge(
        dim_aluno[["RA", "Unidade", "Serie", "Ciclo"]], on="RA", how="left"
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("Filtros")
        # lê drill_unidade vindo de P1 para pré-selecionar a unidade
        _drill_u = st.session_state.pop("drill_unidade", None)
        _unidades = sorted(dim_aluno["Unidade"].unique())
        _idx_u = _unidades.index(_drill_u) if _drill_u and _drill_u in _unidades else 0
        unidade_sel = st.selectbox("Unidade", _unidades, index=_idx_u)
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
        sel_conceitos = st.multiselect("Conceito PCP", ["1", "2", "3", "4", "5"],
                                       default=["1", "2", "3", "4", "5"])

    avs_tipo = dim_avaliacao[dim_avaliacao["Tipo_Avaliacao"].isin(sel_tipos)]["Avaliacao"].tolist()
    avs_ativas = [a for a in sel_avaliacoes if a in avs_tipo]

    def _apply_filters_base(df, unidade=None):
        """Filtros estruturais apenas (Série, Ciclo, Enamedista, Avaliação).
        Usado para métricas comparativas e cálculo de risco — Faixa/Conceito não se aplicam
        a agregações: filtrar por Faixa 5 e calcular % proficientes retornaria 100% sempre.
        """
        mask = (
            df["Serie"].isin(sel_series) &
            df["Ciclo"].isin(sel_ciclos) &
            df["Enamedista"].isin(sel_enamedistas) &
            df["Avaliacao"].isin(avs_ativas)
        )
        if unidade:
            mask &= df["Unidade"] == unidade
        return df[mask]

    def _apply_filters(df, unidade=None):
        """Filtros completos incluindo Faixa e Conceito PCP.
        Faltosos preservados via 'Sem nota'/'Sem conceito' para contagens de participação.
        """
        mask = (
            df["Serie"].isin(sel_series) &
            df["Ciclo"].isin(sel_ciclos) &
            df["Enamedista"].isin(sel_enamedistas) &
            df["Avaliacao"].isin(avs_ativas) &
            df["Desempenho"].isin(sel_faixas + ["Sem nota"]) &
            df["Conceito_PCP"].isin(sel_conceitos + ["Sem conceito"])
        )
        if unidade:
            mask &= df["Unidade"] == unidade
        return df[mask]

    # dp/dp_inst: filtros completos (KPIs de desempenho e distribuição da unidade)
    dp = _apply_filters(dp_all, unidade_sel)
    dp_inst = _apply_filters(dp_all)
    # dp_base/dp_base_inst: sem Faixa/Conceito (métricas comparativas e risco)
    dp_base = _apply_filters_base(dp_all, unidade_sel)
    dp_base_inst = _apply_filters_base(dp_all)

    da = da_all[
        (da_all["Unidade"] == unidade_sel) &
        da_all["Serie"].isin(sel_series) &
        da_all["Ciclo"].isin(sel_ciclos) &
        da_all["Avaliacao"].isin(avs_ativas)
    ]
    da_inst = da_all[
        da_all["Serie"].isin(sel_series) &
        da_all["Ciclo"].isin(sel_ciclos) &
        da_all["Avaliacao"].isin(avs_ativas)
    ]

    # ras_risco calculado aqui — escopo de render(), visível tanto em tab_det
    # quanto no expander, sem depender da ordem de renderização dos blocos internos
    ras_risco = m.alunos_em_risco(dp_base)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_comp, tab_det = st.tabs(["📊 Comparativo — Todas as Unidades", f"🔍 Detalhe — {unidade_sel}"])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — Comparativo lado a lado de todas as unidades
    # ════════════════════════════════════════════════════════════════════════
    with tab_comp:
        st.subheader("Visão Comparativa das 6 Unidades")
        st.caption("Use os filtros da sidebar para refinar. Unidade selecionada é destacada.")

        unidades = sorted(dim_aluno["Unidade"].unique())

        # Tabela-resumo: _apply_filters_base para não contaminar métricas com Faixa/Conceito
        rows = []
        for u in unidades:
            dp_u = _apply_filters_base(dp_all, u)
            da_u = da_all[
                (da_all["Unidade"] == u) &
                da_all["Serie"].isin(sel_series) &
                da_all["Ciclo"].isin(sel_ciclos) &
                da_all["Avaliacao"].isin(avs_ativas)
            ]
            medias_u = m.perc_medio_por_area(da_u, dp_u) * 100
            rows.append({
                "Unidade": u,
                "Alunos": m.total_alunos(dp_u),
                "% Part.": f"{m.perc_participacao(dp_u)*100:.1f}%",
                "Nota Média": round(m.nota_media(dp_u), 1),
                "% Profic.": f"{m.perc_proficientes(dp_u)*100:.1f}%",
                "% <50": f"{m.perc_abaixo_50(dp_u)*100:.1f}%",
                "PCPc Médio": round(m.pcpc_medio(dp_u), 3),
                "Em Risco": m.total_alunos_em_risco(dp_u),
                "Área Forte": f"{medias_u.idxmax()} ({medias_u.max():.0f}%)",
                "Área Fraca": f"{medias_u.idxmin()} ({medias_u.min():.0f}%)",
            })

        df_comp = pd.DataFrame(rows)

        # highlight por coluna: isin sobre a coluna Unidade garante alinhamento de índice
        # independente de reordenação do DataFrame
        unidade_mask = (df_comp["Unidade"] == unidade_sel).values
        styled = df_comp.style.apply(
            lambda _: ["background-color: #1a3a5c; color: white" if flag else ""
                       for flag in unidade_mask],
            axis=0
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Proficiência por Unidade")
            prof_all = m.proficiencia_por_grupo(dp_base_inst, ["Unidade"]).sort_values("Proficiencia")
            cores = ["#2ca02c" if v >= 80 else "#d62728" for v in prof_all["Proficiencia"]]
            fig = go.Figure(go.Bar(
                x=prof_all["Proficiencia"], y=prof_all["Unidade"], orientation="h",
                marker_color=cores,
                text=prof_all["Proficiencia"].map(lambda v: f"{v:.1f}%"), textposition="outside",
            ))
            fig.add_vline(x=80, line_dash="dash", line_color="gray",
                          annotation_text="Meta 80%", annotation_position="top right")
            fig.update_layout(xaxis=dict(range=[0, 110], title="% Proficientes"),
                              yaxis_title=None, margin=dict(l=0, r=40, t=10, b=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("Nota Média por Unidade")
            nota_all = m.nota_media_por_grupo(dp_base_inst, ["Unidade"]).sort_values("Nota_Media")
            fig2 = go.Figure(go.Bar(
                x=nota_all["Nota_Media"], y=nota_all["Unidade"], orientation="h",
                marker_color=["#1f77b4" if u == unidade_sel else "#aec7e8"
                              for u in nota_all["Unidade"]],
                text=nota_all["Nota_Media"].map(lambda v: f"{v:.1f}"), textposition="outside",
            ))
            fig2.add_vline(x=60, line_dash="dash", line_color="green",
                           annotation_text="Proficiência (60)", annotation_position="top right")
            fig2.update_layout(xaxis=dict(range=[0, 85], title="Nota Média"),
                               yaxis_title=None, margin=dict(l=0, r=40, t=10, b=10), height=300)
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("Proficiência por Unidade e Avaliação (%)")
        prof_ua = m.proficiencia_por_grupo(dp_base_inst, ["Unidade", "Avaliacao"])
        prof_ua["Avaliacao"] = prof_ua["Avaliacao"].astype(str)
        pivot_prof = prof_ua.pivot(index="Unidade", columns="Avaliacao", values="Proficiencia")
        pivot_prof = pivot_prof[[c for c in ORDEM_AVALIACOES if c in pivot_prof.columns]]
        fig_h = go.Figure(go.Heatmap(
            z=pivot_prof.values, x=pivot_prof.columns.tolist(), y=pivot_prof.index.tolist(),
            colorscale="RdYlGn", zmid=80,
            text=[[f"{v:.1f}%" for v in row] for row in pivot_prof.values],
            texttemplate="%{text}", colorbar=dict(title="% Profic."),
        ))
        fig_h.update_layout(xaxis_title="Avaliação", yaxis_title=None,
                            margin=dict(l=0, r=0, t=10, b=10), height=280)
        st.plotly_chart(fig_h, use_container_width=True)

        st.divider()

        st.subheader("% Acerto por Área — Todas as Unidades")
        area_all = m.perc_area_por_grupo(da_inst, dp_base_inst, ["Unidade", "Area"])
        fig_area = px.bar(area_all, x="Area", y="Perc_Acerto", color="Unidade", barmode="group",
                          labels={"Perc_Acerto": "% Acerto", "Area": "Área"})
        fig_area.add_hline(y=60, line_dash="dot", line_color="green",
                           annotation_text="60%", annotation_position="top left")
        fig_area.update_layout(yaxis=dict(range=[0, 100]),
                               legend=dict(orientation="h", y=-0.25),
                               margin=dict(l=0, r=0, t=10, b=10), height=350)
        st.plotly_chart(fig_area, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — Detalhe da unidade selecionada
    # ════════════════════════════════════════════════════════════════════════
    with tab_det:
        st.caption(f"Unidade: **{unidade_sel}** — {m.total_alunos(dp_base)} alunos")

        # ── KPIs ──────────────────────────────────────────────────────────
        st.subheader("Indicadores da Unidade")
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        gap = m.gap_unidade_vs_instituicao(dp_base, dp_base_inst)
        prof_u = m.perc_proficientes(dp_base)

        _kpi(c1, "Total Alunos", str(m.total_alunos(dp_base)))
        _kpi(c2, "% Participação", f"{m.perc_participacao(dp_base)*100:.1f}%")
        _kpi(c3, "Nota Média", f"{m.nota_media(dp_base):.1f}",
             f"{gap:+.1f} vs inst. ({m.nota_media(dp_base_inst):.1f})",
             delta_color="normal" if gap >= 0 else "inverse")
        _kpi(c4, "% Proficientes", f"{prof_u*100:.1f}%",
             f"{(prof_u - META_PROFICIENCIA)*100:+.1f} pp vs meta 80%",
             delta_color="normal" if prof_u >= META_PROFICIENCIA else "inverse")
        _kpi(c5, "% Abaixo de 50", f"{m.perc_abaixo_50(dp_base)*100:.1f}%")
        _kpi(c6, "PCPc Médio", f"{m.pcpc_medio(dp_base):.3f}")
        _kpi(c7, "Alunos em Risco", str(len(ras_risco)))

        st.divider()

        # ── Radar de áreas | Barras comparativas ──────────────────────────
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Desempenho por Área")
            medias_u = m.perc_medio_por_area(da, dp_base) * 100
            medias_i = m.perc_medio_por_area(da_inst, dp_base_inst) * 100

            fig_radar = go.Figure()
            for vals, name, color, fill in [
                (medias_u, unidade_sel, "#1f77b4", "rgba(31,119,180,0.2)"),
                (medias_i, "Instituição", "#ff7f0e", "rgba(255,127,14,0.1)"),
            ]:
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals.tolist() + [vals.iloc[0]], theta=AREAS + [AREAS[0]],
                    fill="toself", name=name, line_color=color, fillcolor=fill,
                    line_dash="solid" if name == unidade_sel else "dash",
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                legend=dict(orientation="h", y=-0.15),
                margin=dict(l=40, r=40, t=30, b=40), height=360,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_b:
            st.subheader("Área mais forte e mais fraca")
            comp = pd.DataFrame({
                "Área": AREAS,
                unidade_sel: medias_u.values,
                "Instituição": medias_i.values,
            }).melt(id_vars="Área", var_name="Escopo", value_name="% Acerto")

            fig_bar = px.bar(comp, x="Área", y="% Acerto", color="Escopo", barmode="group",
                             color_discrete_map={unidade_sel: "#1f77b4", "Instituição": "#ff7f0e"})
            fig_bar.add_hline(y=60, line_dash="dot", line_color="green",
                              annotation_text="60%", annotation_position="top left")
            fig_bar.update_layout(yaxis=dict(range=[0, 100]),
                                  legend=dict(orientation="h", y=-0.25),
                                  margin=dict(l=0, r=0, t=10, b=10), height=300)
            st.plotly_chart(fig_bar, use_container_width=True)

            col_m, col_p = st.columns(2)
            col_m.success(f"✅ Mais forte: **{medias_u.idxmax()}** ({medias_u.max():.1f}%)")
            col_p.error(f"⚠️ Mais fraca: **{medias_u.idxmin()}** ({medias_u.min():.1f}%)")

        st.divider()

        # ── Proficiência por série | Risco por série/ciclo ────────────────
        col_c, col_d = st.columns(2)

        with col_c:
            st.subheader("Proficiência por Série")
            prof_s = m.proficiencia_por_grupo(dp_base, ["Serie"]).sort_values("Serie")
            cores = ["#2ca02c" if v >= 80 else "#d62728" for v in prof_s["Proficiencia"]]
            fig_s = go.Figure(go.Bar(
                x=prof_s["Serie"].astype(str), y=prof_s["Proficiencia"],
                marker_color=cores,
                text=prof_s["Proficiencia"].map(lambda v: f"{v:.1f}%"), textposition="outside",
            ))
            fig_s.add_hline(y=80, line_dash="dash", line_color="gray", annotation_text="Meta 80%")
            fig_s.update_layout(xaxis_title="Série", yaxis=dict(range=[0, 110], title="% Proficientes"),
                                margin=dict(l=0, r=0, t=10, b=10), height=300)
            st.plotly_chart(fig_s, use_container_width=True)

        with col_d:
            st.subheader("Alunos em Risco por Série e Ciclo")
            if not ras_risco:
                st.info("Nenhum aluno em risco nesta seleção.")
            else:
                risco_serie = m.risco_por_grupo(dp_base, dim_aluno, ["Serie", "Ciclo"]).sort_values("Serie")
                risco_serie["Série"] = risco_serie["Serie"].astype(str) + " — " + risco_serie["Ciclo"]
                fig_r = px.bar(risco_serie, x="Alunos em Risco", y="Série", orientation="h",
                               color="Alunos em Risco", color_continuous_scale="Reds",
                               text="Alunos em Risco")
                fig_r.update_layout(showlegend=False, coloraxis_showscale=False,
                                    margin=dict(l=0, r=0, t=10, b=10), height=300)
                st.plotly_chart(fig_r, use_container_width=True)

        st.divider()

        # ── Heatmap nota média série × avaliação ──────────────────────────
        st.subheader("Nota Média por Série e Avaliação")
        heat = m.nota_media_por_grupo(dp_base, ["Serie", "Avaliacao"])
        heat["Avaliacao"] = heat["Avaliacao"].astype(str)
        heat["Serie"] = heat["Serie"].astype(str)
        heat_pivot = heat.pivot(index="Serie", columns="Avaliacao", values="Nota_Media")
        heat_pivot = heat_pivot[[c for c in ORDEM_AVALIACOES if c in heat_pivot.columns]]
        fig_heat = go.Figure(go.Heatmap(
            z=heat_pivot.values, x=heat_pivot.columns.tolist(), y=heat_pivot.index.tolist(),
            colorscale="RdYlGn", zmid=60,
            text=[[f"{v:.1f}" for v in row] for row in heat_pivot.values],
            texttemplate="%{text}", colorbar=dict(title="Nota Média"),
        ))
        fig_heat.update_layout(xaxis_title="Avaliação", yaxis_title="Série",
                               margin=dict(l=0, r=0, t=10, b=10), height=260)
        st.plotly_chart(fig_heat, use_container_width=True)

        st.divider()

        # ── Desempenho por área × série ─────────────────────────────────────────
        st.subheader("% Acerto por Área e Série")
        da_serie = da[
            da["Serie"].isin(sel_series) &
            da["Ciclo"].isin(sel_ciclos) &
            da["Avaliacao"].isin(avs_ativas)
        ]
        area_s = m.perc_area_por_grupo(da_serie, dp_base, ["Serie", "Area"])
        area_s["Serie"] = area_s["Serie"].astype(str)
        fig_as = px.bar(
            area_s, x="Area", y="Perc_Acerto", color="Serie", barmode="group",
            labels={"Perc_Acerto": "% Acerto", "Area": "Área", "Serie": "Série"},
        )
        fig_as.add_hline(y=60, line_dash="dot", line_color="green",
                         annotation_text="60%", annotation_position="top left")
        fig_as.update_layout(
            yaxis=dict(range=[0, 100]),
            legend=dict(orientation="h", y=-0.25),
            margin=dict(l=0, r=0, t=10, b=10), height=300,
        )
        st.plotly_chart(fig_as, use_container_width=True)


        # ── Tabela alunos em risco com drill-through ────────────────────────────────
        with st.expander(f"📋 Lista de alunos em risco — {unidade_sel} ({len(ras_risco)} alunos)"):
            if not ras_risco:
                st.info("Nenhum aluno em risco nesta seleção.")
            else:
                # monta tabela enriquecida: notas + area_fraca + tendencia + severidade
                pivot_notas = (
                    dp_base[dp_base["RA"].isin(ras_risco) & (dp_base["Status_Participacao"] == "Presente")]
                    .pivot_table(index="RA", columns="Avaliacao", values="Nota_Avalia")
                    .reset_index()
                )
                pivot_notas.columns = [str(c) for c in pivot_notas.columns]

                # area mais fraca por aluno
                fa_risco = fact_area[fact_area["RA"].isin(ras_risco)]
                fp_risco = fact_prova[fact_prova["RA"].isin(ras_risco)]
                area_fraca_rows = []
                for ra in ras_risco:
                    med = m.perc_medio_por_area(
                        fa_risco[fa_risco["RA"] == ra],
                        fp_risco[fp_risco["RA"] == ra]
                    ) * 100
                    area_fraca_rows.append({"RA": ra, "Area Fraca": f"{med.idxmin()} ({med.min():.0f}%)"})
                df_area_fraca = pd.DataFrame(area_fraca_rows)

                # tendencia por aluno
                def _tend(row):
                    avs = [str(a) for a in m.ORDEM_AVALIACOES]
                    notas = [row.get(a) for a in avs if row.get(a) is not None]
                    notas = [n for n in notas if pd.notna(n)]
                    if len(notas) < 2:
                        return "→ Estável"
                    delta = notas[-1] - notas[0]
                    if delta > 3:  return f"↑ Alta (+{delta:.0f})"
                    if delta < -3: return f"↓ Queda ({delta:.0f})"
                    return f"→ Estável ({delta:+.0f})"

                # severidade
                sev = m.severidade_risco(dp_base)[["RA", "Label"]].rename(columns={"Label": "Severidade"})

                tabela = (
                    dim_aluno[dim_aluno["RA"].isin(ras_risco)][["RA", "Aluno", "Serie", "Ciclo"]]
                    .merge(pivot_notas, on="RA", how="left")
                    .merge(df_area_fraca, on="RA", how="left")
                    .merge(sev, on="RA", how="left")
                    .sort_values("Serie")
                    .reset_index(drop=True)
                )
                tabela["Tendência"] = tabela.apply(_tend, axis=1)
                # exibe tabela + botão de drill-through por aluno
                st.caption("Clique em \"Ver ficha →\" para abrir a ficha individual do aluno.")
                col_tabela, col_btns = st.columns([5, 1])
                with col_tabela:
                    st.dataframe(tabela, use_container_width=True, hide_index=True)
                with col_btns:
                    st.markdown("**Ficha**")
                    for _, row in tabela.iterrows():
                        if st.button("Ver →", key=f"drill_{row['RA']}"):
                            st.session_state["drill_ra"] = row["RA"]
                            st.session_state["pagina"] = "👤 Aluno Individual"
                            st.rerun()
