import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import metrics as m


def render(fact_prova, fact_area, dim_aluno, dim_avaliacao):
    st.title("💡 Conclusões Executivas")
    st.caption(
        "🗺️ **Responde:** Quais 3 ações de gestão acadêmica você recomendaria? "
        "| 9 insights com dados · 3 recomendações acionáveis · Regras de negócio · Metodologia."
    )

    dp = fact_prova.merge(dim_aluno[["RA", "Unidade", "Serie", "Ciclo"]], on="RA", how="left")

    # ── KPIs de contexto ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de Alunos", m.total_alunos(fact_prova))
    c2.metric("% Proficientes", f"{m.perc_proficientes(fact_prova)*100:.1f}%",
              f"{(m.perc_proficientes(fact_prova) - 0.80)*100:+.1f} pp vs meta 80%",
              delta_color="inverse")
    c3.metric("Nota Média Geral", f"{m.nota_media(fact_prova):.1f}")
    c4.metric("Alunos em Risco", m.total_alunos_em_risco(fact_prova))
    c5.metric("Unidades acima da meta", "1 de 6", delta_color="off")

    st.divider()

    # ── Insights ──────────────────────────────────────────────────────────────
    st.subheader("🔍 Insights Encontrados nos Dados")
    insights = [
        ("1. Apenas VITORIA DA CONQUISTA atinge a meta de 80% de proficiência",
         "Com **83,4%** de proficiência, é a única unidade acima da meta institucional. "
         "ITUMBIARA é o caso mais crítico: **40,7%** de proficiência — menos da metade da meta — "
         "e concentra **20 dos 50 alunos em risco** (40% do total). "
         "O gap entre a melhor e a pior unidade é de **42,7 pp**, indicando desigualdade estrutural entre campi."),
        ("2. Ciclo Básico (séries 9–10) está sistematicamente abaixo do Clínico (11–12)",
         "A proficiência do Ciclo Básico é **47,3%** contra **71,3%** do Ciclo Clínico — diferença de **24 pp**. "
         "A série 9 tem apenas **42,2%** de proficiência, a mais baixa de todas. "
         "Isso sugere que a transição para o ciclo médico é um ponto de ruptura que exige atenção pedagógica específica."),
        ("3. CM (Clínica Médica) é a área mais fraca em 5 das 6 unidades",
         "Com média de **58,6%** de acerto, CM é a área com pior desempenho na instituição. "
         "É a área mais fraca em ARAGUARI (54,0%), BARREIRAS (56,3%), ITUMBIARA (53,2%), "
         "SALVADOR (61,8%) e VITORIA DA CONQUISTA (65,6%). "
         "Apenas EUNAPOLIS foge ao padrão, com CIR como área mais fraca (54,7%)."),
        ("4. Avaliações de Desempenho superam as Diagnósticas em 2,2 pontos",
         "A nota média nas avaliações de **Desempenho** (AV2 e AV4) é **63,2**, "
         "contra **61,0** nas **Diagnósticas** (AV1 e AV3). "
         "O ganho de apenas 2,2 pontos indica que o aprendizado ao longo do semestre é modesto e pode ser ampliado."),
        ("5. Há evolução positiva de AV1 para AV4, mas ela não é homogênea",
         "A nota média institucional sobe de **60,9** (AV1) para **64,1** (AV4), ganho de **3,2 pts**. "
         "VITORIA DA CONQUISTA lidera: 65,8 → 72,1 (+6,3 pts). "
         "ITUMBIARA estagna: 57,0 → 56,1 (−0,9 pts), único campus com regressão."),
        ("6. 50 alunos atendem ao critério de risco composto (6,9% do total)",
         "O critério combina nota < 50 em ≥ 2 avaliações **e** tendência de queda entre períodos. "
         "ITUMBIARA concentra 40% desses alunos (20/50), seguida de ARAGUARI (11). "
         "VITORIA DA CONQUISTA tem apenas 2 alunos em risco."),
        ("7. Série 9 concentra o maior percentual de alunos em risco (15,1%)",
         "A série 9 tem **19 dos 50 alunos em risco** — **15,1%** dos seus 126 alunos, "
         "o maior percentual de todas as séries. "
         "A série 10 tem 7,6%, a série 12 tem 5,7% e a série 11 apenas 2,6%. "
         "O risco é portanto concentrado na entrada do Ciclo Básico, não distribuído uniformemente, "
         "o que aponta para dificuldade de adaptação ao currículo médico nos primeiros anos."),
        ("8. GO é a área mais forte em 4 das 6 unidades; o gap interno varia até 10,7 pp",
         "Cirurgia (GO) lidera o desempenho em ARAGUARI (64,7%), ITUMBIARA (58,4%), "
         "SALVADOR (66,4%) e VITORIA DA CONQUISTA (70,9%). "
         "PREV lidera em BARREIRAS (66,3%) e EUNAPOLIS (64,6%). "
         "O gap entre área mais forte e mais fraca dentro de cada unidade varia de **4,6 pp** (SALVADOR) "
         "a **10,7 pp** (ARAGUARI), indicando que ARAGUARI tem desequilíbrio interno relevante "
         "mesmo com proficiência geral próxima da média institucional."),
        ("9. A AV3 provoca queda institucional de 7,4 pp em relação à AV2; ITUMBIARA não responde ao ensino",
         "A proficiência cai de **64,5%** (AV2) para **57,1%** (AV3) — queda de **7,4 pp** "
         "no início do 2º semestre, padrão que se repete na nota média (62,4 → 61,2). "
         "Isso sugere dificuldade de retomada após o recesso e pode indicar necessidade de "
         "avaliação diagnóstica mais preparatória no início de cada semestre. "
         "Adicionalmente, ITUMBIARA apresenta gap Diagnóstica→Desempenho de apenas **3,2 pp**, "
         "contra média de **8,9 pp** nas demais unidades — o ensino não está convertendo em ganho "
         "de desempenho, o que diferencia ITUMBIARA de um problema pontual para um problema estrutural."),
    ]
    for titulo, corpo in insights:
        with st.expander(titulo, expanded=True):
            st.markdown(corpo)

    st.divider()

    # ── Gráficos resumo ───────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Proficiência por Unidade")
        prof_u = m.proficiencia_por_grupo(dp, ["Unidade"]).sort_values("Proficiencia")
        cores = ["#2ca02c" if v >= 80 else "#d62728" for v in prof_u["Proficiencia"]]
        fig = go.Figure(go.Bar(
            x=prof_u["Proficiencia"], y=prof_u["Unidade"], orientation="h",
            marker_color=cores,
            text=prof_u["Proficiencia"].map(lambda v: f"{v:.1f}%"), textposition="outside",
        ))
        fig.add_vline(x=80, line_dash="dash", line_color="gray", annotation_text="Meta 80%")
        fig.update_layout(xaxis=dict(range=[0, 105]), yaxis_title=None,
                          margin=dict(l=0, r=40, t=10, b=10), height=260)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Proficiência por Série e Ciclo")
        prof_s = m.proficiencia_por_grupo(dp, ["Serie", "Ciclo"]).sort_values("Serie")
        prof_s["Label"] = prof_s["Serie"].astype(str) + "º — " + prof_s["Ciclo"]
        cores_s = ["#2ca02c" if v >= 80 else "#d62728" for v in prof_s["Proficiencia"]]
        fig_s = go.Figure(go.Bar(
            x=prof_s["Label"], y=prof_s["Proficiencia"], marker_color=cores_s,
            text=prof_s["Proficiencia"].map(lambda v: f"{v:.1f}%"), textposition="outside",
        ))
        fig_s.add_hline(y=80, line_dash="dash", line_color="gray")
        fig_s.update_layout(yaxis=dict(range=[0, 105], title="% Proficientes"), xaxis_title=None,
                            margin=dict(l=0, r=0, t=10, b=10), height=260)
        st.plotly_chart(fig_s, use_container_width=True)

    st.divider()

    # ── Recomendações ─────────────────────────────────────────────────────────
    st.subheader("📌 Recomendações de Gestão Acadêmica")
    st.markdown("""
**1. Programa de intervenção imediata em ITUMBIARA e no Ciclo Básico**

ITUMBIARA tem 40,7% de proficiência e 20 alunos em risco — o pior resultado em ambos os indicadores.
As séries 9 e 10 têm proficiência de 42,2% e 50,9%, respectivamente.
Recomenda-se criar um programa de reforço com tutoria individualizada, usando a lista de alunos em risco
gerada pelo critério composto como ponto de partida imediato.

---

**2. Reforço específico em Clínica Médica (CM) em toda a instituição**

CM é a área mais fraca em 5 das 6 unidades, com média de 58,6% — 6,3 pp abaixo da área mais forte (PREV).
Isso indica problema de conteúdo transversal, não isolado a uma unidade.
Recomenda-se revisar material didático, carga horária e metodologia de CM,
com foco especial em ARAGUARI (54,0%) e ITUMBIARA (53,2%).

---

**3. Investigar e replicar as práticas de VITORIA DA CONQUISTA**

Com 83,4% de proficiência, crescimento consistente (+6,3 pts de AV1 a AV4) e apenas 2 alunos em risco,
VITORIA DA CONQUISTA é o benchmark da instituição.
Recomenda-se mapear suas práticas pedagógicas e modelo de acompanhamento de alunos
para replicar nas demais unidades, especialmente ITUMBIARA e BARREIRAS.
""")

    st.divider()

    # ── Metodologia e regras ──────────────────────────────────────────────────
    st.subheader("📋 Metodologia, Premissas e Regras de Negócio")
    col_m, col_r = st.columns(2)

    with col_m:
        st.markdown("**Fonte e tratamento dos dados**")
        st.markdown("""
- Bases sintéticas em Excel (`Dados_Prova` e `Dados_Area`)
- `RA` como Texto, `Data_Prova` como Date, `Serie` como Inteiro
- `Periodo_Letivo` convertido de int64 para string
- Nota_Avalia e Perc_* de faltosos nulificados para evitar contaminação
- Label da faixa 1 padronizado (`"1 - 0 a 39.99"` → `"1 - <40"`)
- Star schema: `dim_Aluno`, `dim_Avaliacao`, `fact_Prova`, `fact_Area`
- `Status_Participacao` e `Perc_*` removidos de `fact_Area` — reconstruídos em runtime
- Chave composta: `RA + Avaliacao` — sem duplicatas confirmado em auditoria
        """)
        st.markdown("**Ferramenta**")
        st.markdown("""
- Python 3.8 + Pandas + Plotly + Streamlit
- Camada de métricas centralizada em `src/metrics.py`
- Todas as agregações passam por funções explícitas — sem `.groupby()` inline nas páginas
        """)

    with col_r:
        st.markdown("**Regras de negócio aplicadas**")
        regras = pd.DataFrame([
            ["Participante válido", "Status_Participacao = 'Presente'"],
            ["Proficiente", "Nota_Avalia ≥ 60"],
            ["Meta institucional", "80% dos participantes proficientes"],
            ["Faixa 1", "Nota < 40"],
            ["Faixa 2", "40 ≤ Nota < 50"],
            ["Faixa 3", "50 ≤ Nota < 55"],
            ["Faixa 4", "55 ≤ Nota < 60"],
            ["Faixa 5", "Nota ≥ 60"],
            ["PCPc", "Nota_Avalia / 100 (apenas presentes)"],
            ["Conceito PCP 1", "PCPc < 0,40"],
            ["Conceito PCP 2", "0,40 ≤ PCPc < 0,60"],
            ["Conceito PCP 3", "0,60 ≤ PCPc < 0,75"],
            ["Conceito PCP 4", "0,75 ≤ PCPc < 0,90"],
            ["Conceito PCP 5", "PCPc ≥ 0,90"],
            ["Acertos por área", "Máx. 20 questões; Perc = Acertos / 20"],
        ], columns=["Regra", "Definição"])
        st.dataframe(regras, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Critério de priorização de alunos em risco**")
    st.info(
        "Um aluno é classificado **em risco** quando atende simultaneamente:\n\n"
        "1. **Nota < 50 em 2 ou mais avaliações** — descarta quedas pontuais\n"
        "2. **Tendência de queda** — AV2 < AV1 ou AV4 < AV3\n\n"
        "Faltosos são excluídos. O critério é conservador por design: foca nos casos "
        "com dificuldade estrutural persistente, não em quedas isoladas."
    )
