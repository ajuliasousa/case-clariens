import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import metrics as m

ORDEM_AVALIACOES = ["AV1T-2026.1", "AV2T-2026.1", "AV3T-2026.2", "AV4T-2026.2"]
AREAS = ["CIR", "CM", "GO", "PED", "PREV"]
CORES_FAIXA = {
    "1 - <40": "#d62728", "2 - 40 a 49.99": "#ff7f0e",
    "3 - 50 a 54.99": "#ffdd57", "4 - 55 a 59.99": "#aec7e8", "5 - 60+": "#2ca02c",
}
CONCEITO_LABEL = {"1": "⬛ 1", "2": "🟥 2", "3": "🟨 3", "4": "🟦 4", "5": "🟩 5"}


def _tendencia(notas: list) -> str:
    if len(notas) < 2:
        return "—"
    delta = notas[-1] - notas[0]
    if delta > 3:  return f"📈 Alta (+{delta:.0f} pts)"
    if delta < -3: return f"📉 Queda ({delta:.0f} pts)"
    return f"➡️ Estável ({delta:+.0f} pts)"


def render(fact_prova, fact_area, dim_aluno, dim_avaliacao):
    st.title("👤 Aluno Individual")
    st.caption(
        "🗺️ **Responde:** Quais alunos devem ser priorizados para reverter o desempenho? "
        "| Alunos em risco aparecem no topo com ⚠️ · Use 'Ver →' em Análise por Unidade para chegar aqui diretamente."
    )

    # ras_risco calculado sobre fact_prova completo apenas para ordenação global
    ras_risco_global = m.alunos_em_risco(fact_prova)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("Buscar Aluno")
        sel_unidade = st.selectbox("Unidade", ["Todas"] + sorted(dim_aluno["Unidade"].unique()))

        dim_f = dim_aluno if sel_unidade == "Todas" else dim_aluno[dim_aluno["Unidade"] == sel_unidade]

        # ras_risco filtrado pela unidade selecionada — corrige contagem e ordenação
        fp_unidade = fact_prova[fact_prova["RA"].isin(dim_f["RA"])]
        ras_risco_unidade = m.alunos_em_risco(fp_unidade)

        dim_f = dim_f.copy()
        dim_f["em_risco"] = dim_f["RA"].isin(ras_risco_unidade)
        dim_f = dim_f.sort_values(["em_risco", "Aluno"], ascending=[False, True])

        # prefixo ⚠️ visível no próprio label de cada aluno em risco
        opcoes = [
            ("⚠️ " if r else "") + ra + " — " + nome
            for ra, nome, r in zip(dim_f["RA"], dim_f["Aluno"], dim_f["em_risco"])
        ]
        opcoes_ra = dim_f["RA"].tolist()

        # drill-through: pré-seleciona aluno vindo de P2 via session_state
        drill_ra = st.session_state.get("drill_ra")
        if drill_ra and drill_ra in opcoes_ra:
            idx_default = opcoes_ra.index(drill_ra)
        else:
            idx_default = 0

        sel_idx = st.selectbox(
            "Aluno (⚠️ = em risco)", range(len(opcoes)),
            format_func=lambda i: opcoes[i],
            index=idx_default,
        )
        # limpa drill_ra após uso para não forçar seleção em navegações futuras
        if drill_ra:
            st.session_state["drill_ra"] = None

        st.caption("⚠️ Alunos em risco aparecem no topo da lista")

    ra_sel = opcoes_ra[sel_idx]
    info = dim_aluno[dim_aluno["RA"] == ra_sel].iloc[0]
    em_risco = ra_sel in ras_risco_unidade

    dp_aluno = (
        fact_prova[fact_prova["RA"] == ra_sel]
        .merge(dim_avaliacao[["Avaliacao", "Tipo_Avaliacao", "Data_Prova"]], on="Avaliacao", how="left")
        .sort_values("Avaliacao")
    )
    da_aluno = m._enrich_area(fact_area[fact_area["RA"] == ra_sel], fact_prova).sort_values("Avaliacao")

    # fact_prova filtrado pela unidade do aluno — usado para médias de referência
    fp_ref = fact_prova[fact_prova["RA"].isin(
        dim_aluno[dim_aluno["Unidade"] == info["Unidade"]]["RA"]
    )]
    fa_ref = fact_area[fact_area["RA"].isin(fp_ref["RA"])]

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    col_info, col_flag = st.columns([3, 2])
    with col_info:
        st.subheader(info["Aluno"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RA", info["RA"])
        c2.metric("Unidade", info["Unidade"])
        c3.metric("Série", str(info["Serie"]))
        c4.metric("Ciclo", info["Ciclo"].replace("Ciclo ", ""))
        c5, c6 = st.columns(2)
        c5.metric("Enamedista", info["Enamedista"])
        notas = dp_aluno[dp_aluno["Status_Participacao"] == "Presente"]["Nota_Avalia"].tolist()
        c6.metric("Tendência Geral", _tendencia(notas))
    with col_flag:
        st.markdown("###")
        if em_risco:
            st.error("🔴 **ALUNO EM RISCO** — nota < 50 em 2+ avaliações com tendência de queda")
            st.caption("Critério: nota < 50 em ≥ 2 avaliações + queda entre períodos")
        else:
            st.success("🟢 **Sem alerta de risco** — desempenho dentro dos critérios")

    st.divider()

    # ── Histórico de notas | Faixa e Conceito PCP ─────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Histórico de Notas")
        dp_pres = dp_aluno[dp_aluno["Status_Participacao"] == "Presente"]

        # média da unidade via fp_ref (fact_prova já filtrado pela unidade do aluno)
        media_u = m.nota_media_por_grupo(fp_ref, ["Avaliacao"])
        media_u["Avaliacao"] = media_u["Avaliacao"].astype(str)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dp_pres["Avaliacao"].astype(str), y=dp_pres["Nota_Avalia"],
            marker_color=[CORES_FAIXA.get(str(d), "#999") for d in dp_pres["Desempenho"]],
            text=dp_pres["Nota_Avalia"], textposition="outside", name="Nota",
        ))
        fig.add_trace(go.Scatter(
            x=media_u["Avaliacao"], y=media_u["Nota_Media"], mode="lines+markers",
            name=f"Média {info['Unidade']}", line=dict(color="#1f77b4", dash="dash"),
            marker=dict(size=6),
        ))
        fig.add_hline(y=60, line_dash="dot", line_color="green",
                      annotation_text="Proficiência (60)", annotation_position="top left")
        fig.add_hline(y=50, line_dash="dot", line_color="red",
                      annotation_text="Risco (50)", annotation_position="bottom right")
        fig.update_layout(yaxis=dict(range=[0, 110], title="Nota"), xaxis_title="Avaliação",
                          legend=dict(orientation="h", y=-0.3),
                          margin=dict(l=0, r=0, t=10, b=10), height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Faixa e Conceito PCP")
        for _, row in dp_aluno.iterrows():
            av = str(row["Avaliacao"])
            if row["Status_Participacao"] != "Presente":
                st.markdown(f"**{av}** — ❌ Faltoso")
                continue
            st.markdown(
                f"**{av}** `{row.get('Tipo_Avaliacao', '')}`  \n"
                f"Nota: **{int(row['Nota_Avalia'])}** &nbsp;|&nbsp; "
                f"Faixa: **{row['Desempenho']}** &nbsp;|&nbsp; "
                f"PCPc: **{row['PCPc']:.2f}** &nbsp;|&nbsp; "
                f"Conceito: {CONCEITO_LABEL.get(str(row['Conceito_PCP']), str(row['Conceito_PCP']))}"
            )

    st.divider()

    # ── Radar de áreas | Evolução por área ────────────────────────────────────
    col_c, col_d = st.columns(2)
    da_pres = da_aluno[da_aluno["Status_Participacao"] == "Presente"]

    with col_c:
        st.subheader("Perfil por Área (média das avaliações)")
        if len(da_pres) == 0:
            st.info("Sem dados de participação.")
        else:
            medias_aluno = da_pres[m.PERC_AREAS].mean() * 100
            medias_aluno.index = AREAS

            # média de referência: fa_ref e fp_ref já filtrados pela unidade do aluno
            medias_unidade = m.perc_medio_por_area(fa_ref, fp_ref) * 100

            fig_r = go.Figure()
            for vals, name, color, fill in [
                (medias_aluno, info["Aluno"].split()[0],
                 "#d62728" if em_risco else "#2ca02c",
                 "rgba(214,39,40,0.2)" if em_risco else "rgba(44,160,44,0.2)"),
                (medias_unidade, f"Média {info['Unidade']}", "#1f77b4", "rgba(31,119,180,0.1)"),
            ]:
                fig_r.add_trace(go.Scatterpolar(
                    r=vals.tolist() + [vals.iloc[0]], theta=AREAS + [AREAS[0]],
                    fill="toself", name=name, line_color=color, fillcolor=fill,
                    line_dash="solid" if name != f"Média {info['Unidade']}" else "dash",
                ))
            fig_r.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                legend=dict(orientation="h", y=-0.2),
                margin=dict(l=40, r=40, t=30, b=40), height=360,
            )
            st.plotly_chart(fig_r, use_container_width=True)

    with col_d:
        st.subheader("Evolução por Área ao longo das Avaliações")
        if len(da_pres) == 0:
            st.info("Sem dados de participação.")
        else:
            evo_area = m.perc_area_por_grupo(
                da_aluno[["RA", "Avaliacao"] + m.AREAS],
                fact_prova, ["Avaliacao"]
            )
            evo_area["Avaliacao"] = evo_area["Avaliacao"].astype(str)
            fig_area = px.line(evo_area, x="Avaliacao", y="Perc_Acerto", color="Area",
                               markers=True,
                               labels={"Avaliacao": "Avaliação", "Perc_Acerto": "% Acerto",
                                       "Area": "Área"})
            fig_area.add_hline(y=60, line_dash="dash", line_color="green",
                               annotation_text="60%", annotation_position="top left")
            fig_area.update_layout(yaxis=dict(range=[0, 105]),
                                   legend=dict(orientation="h", y=-0.3),
                                   margin=dict(l=0, r=0, t=10, b=10), height=360)
            st.plotly_chart(fig_area, use_container_width=True)

    st.divider()

    # ── Tabela resumo ─────────────────────────────────────────────────────────
    st.subheader("Resumo Completo por Avaliação")
    resumo = dp_aluno[["Avaliacao", "Tipo_Avaliacao", "Data_Prova",
                        "Status_Participacao", "Nota_Avalia",
                        "Desempenho", "PCPc", "Conceito_PCP"]].copy()
    resumo["Avaliacao"] = resumo["Avaliacao"].astype(str)
    resumo["Data_Prova"] = resumo["Data_Prova"].dt.strftime("%d/%m/%Y")
    resumo["PCPc"] = resumo["PCPc"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    resumo.columns = ["Avaliação", "Tipo", "Data", "Status", "Nota", "Faixa", "PCPc", "Conceito PCP"]
    st.dataframe(resumo, use_container_width=True, hide_index=True)

    n_risco_unidade = len(ras_risco_unidade)
    if n_risco_unidade:
        st.divider()
        escopo = f"em {info['Unidade']}" if sel_unidade != "Todas" else "na base"
        st.caption(f"Total de alunos em risco {escopo}: **{n_risco_unidade}**")
        if ra_sel in ras_risco_unidade:
            idx = ras_risco_unidade.index(ra_sel)
            prox = ras_risco_unidade[(idx + 1) % n_risco_unidade]
            nome_prox = dim_aluno[dim_aluno["RA"] == prox]["Aluno"].values[0]
            st.caption(f"Próximo em risco: **{nome_prox}** (RA {prox}) — use o seletor na sidebar")
