import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import metrics as m


def render(fact_prova, fact_area, dim_aluno, dim_avaliacao):
    st.title("📈 Score de Risco Contínuo")
    st.caption(
        "Ranqueamento de alunos por gravidade combinando **nível** (onde está) e "
        "**trajetória OLS** (para onde está indo). Score 0–100: quanto maior, maior o risco."
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("Filtros")
        unidades = ["Todas"] + sorted(dim_aluno["Unidade"].unique())
        sel_unidade = st.selectbox("Unidade", unidades)
        sel_ciclos = st.multiselect("Ciclo", sorted(dim_aluno["Ciclo"].unique()),
                                    default=sorted(dim_aluno["Ciclo"].unique()))
        sel_series = st.multiselect("Série", sorted(dim_aluno["Serie"].unique()),
                                    default=sorted(dim_aluno["Serie"].unique()))

    # ── Dados ─────────────────────────────────────────────────────────────────
    dp = fact_prova.merge(
        dim_aluno[["RA", "Unidade", "Serie", "Ciclo"]], on="RA", how="left"
    )
    mask = dp["Ciclo"].isin(sel_ciclos) & dp["Serie"].isin(sel_series)
    if sel_unidade != "Todas":
        mask &= dp["Unidade"] == sel_unidade
    dp_f = dp[mask]

    df_score = m.score_risco_continuo(dp_f, dim_aluno)

    if df_score.empty:
        st.info("Nenhum aluno com dados suficientes para esta seleção.")
        return

    # ── KPIs ──────────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Alunos analisados", len(df_score))
    c2.metric("Score médio", f"{df_score['Score'].mean():.1f}")
    c3.metric("🔴 Crítico", len(df_score[df_score["Quadrante"] == "🔴 Crítico"]))
    c4.metric("🟠 Alerta", len(df_score[df_score["Quadrante"] == "🟠 Alerta"]))
    c5.metric("🟡 Recuperação", len(df_score[df_score["Quadrante"] == "🟡 Recuperação"]))

    st.divider()

    # ── Scatter nível × trajetória ────────────────────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Mapa de Risco — Nível × Trajetória")
        st.caption(
            "Eixo X: nota média (nível). Eixo Y: inclinação OLS (trajetória). "
            "Linha vermelha = nota 50. Linha cinza = trajetória zero."
        )

        cor_map = {
            "🔴 Crítico": "#d62728",
            "🟠 Alerta": "#ff7f0e",
            "🟡 Recuperação": "#f7c948",
            "🟢 Sólido": "#2ca02c",
        }

        fig = px.scatter(
            df_score,
            x="Nivel", y="Trajetoria",
            color="Quadrante",
            color_discrete_map=cor_map,
            hover_data={"Aluno": True, "Score": True, "Unidade": True,
                        "Serie": True, "Nivel": ":.1f", "Trajetoria": ":.2f"},
            labels={"Nivel": "Nota Média", "Trajetoria": "Trajetória (OLS)"},
            size_max=8,
        )
        fig.add_vline(x=50, line_dash="dash", line_color="red", opacity=0.5,
                      annotation_text="Nota 50", annotation_position="top right")
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5,
                      annotation_text="Trajetória zero", annotation_position="right")
        fig.update_traces(marker=dict(size=7, opacity=0.75))
        fig.update_layout(
            legend=dict(orientation="h", y=-0.2),
            margin=dict(l=0, r=0, t=10, b=10), height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Distribuição por Quadrante")
        quad_count = df_score["Quadrante"].value_counts().reset_index()
        quad_count.columns = ["Quadrante", "Alunos"]
        fig_bar = go.Figure(go.Bar(
            x=quad_count["Alunos"], y=quad_count["Quadrante"], orientation="h",
            marker_color=[cor_map.get(q, "#999") for q in quad_count["Quadrante"]],
            text=quad_count["Alunos"], textposition="outside",
        ))
        fig_bar.update_layout(
            xaxis=dict(range=[0, quad_count["Alunos"].max() * 1.2]),
            yaxis_title=None, showlegend=False,
            margin=dict(l=0, r=40, t=10, b=10), height=200,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Score por Unidade")
        score_u = df_score.groupby("Unidade")["Score"].mean().sort_values(ascending=False).reset_index()
        score_u["Score"] = score_u["Score"].round(1)
        fig_u = go.Figure(go.Bar(
            x=score_u["Score"], y=score_u["Unidade"], orientation="h",
            marker_color="#d62728",
            text=score_u["Score"], textposition="outside",
        ))
        fig_u.update_layout(
            xaxis=dict(range=[0, 100], title="Score médio de risco"),
            yaxis_title=None, showlegend=False,
            margin=dict(l=0, r=40, t=10, b=10), height=220,
        )
        st.plotly_chart(fig_u, use_container_width=True)

    st.divider()

    # ── Tabela ranqueada ───────────────────────────────────────────────────────
    st.subheader("Ranking de Risco — Alunos Ordenados por Score")
    st.caption("Apenas alunos com ≥ 2 avaliações presentes. Score mais alto = maior prioridade de intervenção.")

    tabela = (
        df_score[["Quadrante", "Score", "Aluno", "Unidade", "Serie", "Ciclo", "Nivel", "Trajetoria"]]
        .sort_values("Score", ascending=False)
        .reset_index(drop=True)
    )
    tabela.index += 1
    tabela.columns = ["Quadrante", "Score", "Aluno", "Unidade", "Série", "Ciclo",
                      "Nota Média", "Trajetória OLS"]

    # highlight por quadrante
    def _highlight(row):
        cores = {
            "🔴 Crítico":     "background-color: #ffd5d5",
            "🟠 Alerta":      "background-color: #ffe8cc",
            "🟡 Recuperação": "background-color: #fff9cc",
            "🟢 Sólido":      "",
        }
        return [cores.get(row["Quadrante"], "")] * len(row)

    st.dataframe(
        tabela.style.apply(_highlight, axis=1),
        use_container_width=True, height=420,
    )

    # ── Metodologia ───────────────────────────────────────────────────────────
    with st.expander("📐 Metodologia do Score"):
        st.markdown("""
**Nível** — média simples das avaliações presentes (onde o aluno está hoje).

**Trajetória OLS** — inclinação da reta de mínimos quadrados nas 4 avaliações:
```
β = (−3×AV1 − 1×AV2 + 1×AV3 + 3×AV4) / 20
```
Negativo = queda. Positivo = melhora. Zero = estagnação.

**Score de risco** (0–100):
```
score = 0.6 × (1 − nível/100) + 0.4 × max(0, −trajetória/30)
```
- Nível contribui 60%: aluno com nota baixa tem risco estrutural
- Trajetória contribui 40%: queda agrava o risco; melhora não reduz (max 0)
- Normalizado para 0–100 e truncado nos extremos

**Quadrantes** (mediana de nível como divisor):

| | Nível baixo | Nível alto |
|---|---|---|
| **Queda** | 🔴 Crítico | 🟠 Alerta |
| **Melhora/estável** | 🟡 Recuperação | 🟢 Sólido |
        """)
