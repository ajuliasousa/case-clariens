import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import metrics as m


MAPA = [
    ("📊", "Visão Executiva",
     "Qual é o panorama geral? Quais unidades estão abaixo da meta de 80%?",
     "KPIs institucionais · Proficiência por unidade · Evolução AV1→AV4 · Risco por grupo",
     "📊 Visão Executiva"),
    ("🏫", "Análise por Unidade",
     "Quais unidades precisam de intervenção? Quais áreas explicam o resultado?",
     "Comparativo 6 unidades · Radar de áreas · Risco por série · Drill-through para aluno",
     "🏫 Análise por Unidade"),
    ("📅", "Análise Temporal",
     "Existe melhora ao longo das avaliações? Ela é homogênea entre unidades?",
     "Evolução AV1→AV4 · Diagnóstica vs Desempenho · Período letivo · Ciclo Básico vs Clínico",
     "📅 Análise Temporal"),
    ("👤", "Aluno Individual",
     "Quais alunos devem ser priorizados para reverter o desempenho?",
     "Ficha do aluno · Histórico de notas · Radar por área · Flag de risco · Drill-through de P2",
     "👤 Aluno Individual"),
    ("💡", "Conclusões Executivas",
     "Quais 3 ações de gestão acadêmica você recomendaria?",
     "9 insights com dados · 3 recomendações acionáveis · Regras de negócio · Metodologia",
     "💡 Conclusões Executivas"),
]


def render(fact_prova, fact_area, dim_aluno, dim_avaliacao):
    st.title("🎓 Clariens — Desempenho Acadêmico 2026")
    st.caption(
        "Solução analítica para 6 unidades · 4 séries (9–12) · 4 avaliações (AV1–AV4) · "
        "720 alunos · 2.880 registros"
    )

    # ── KPIs de contexto ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Alunos", m.total_alunos(fact_prova))
    c2.metric("Unidades", dim_aluno["Unidade"].nunique())
    c3.metric("Avaliações", dim_avaliacao["Avaliacao"].nunique())
    prof = m.perc_proficientes(fact_prova)
    c4.metric("% Proficientes", f"{prof*100:.1f}%",
              f"{(prof-0.80)*100:+.1f} pp vs meta 80%",
              delta_color="normal" if prof >= 0.80 else "inverse")
    c5.metric("Alunos em Risco", m.total_alunos_em_risco(fact_prova),
              f"{m.perc_alunos_em_risco(fact_prova)*100:.1f}% do total",
              delta_color="inverse")

    st.divider()

    # ── Mapa de navegação ─────────────────────────────────────────────────────
    st.subheader("🗺️ Mapa do Dashboard")
    st.caption("Cada página responde a perguntas específicas do case. Clique em 'Ir para →' para navegar.")

    for icone, nome, pergunta, conteudo, pagina_key in MAPA:
        with st.container(border=True):
            col_txt, col_btn = st.columns([5, 1])
            with col_txt:
                st.markdown(f"**{icone} {nome}**")
                st.markdown(f"*{pergunta}*")
                st.caption(conteudo)
            with col_btn:
                st.markdown("###")
                if st.button("Ir para →", key=f"nav_{pagina_key}"):
                    st.session_state["pagina"] = pagina_key
                    st.rerun()

    st.divider()

    # ── Fluxo de análise recomendado ──────────────────────────────────────────
    st.subheader("🔄 Fluxo de Análise Recomendado")
    st.markdown("""
1. **Visão Executiva** → identifique as unidades abaixo da meta e os grupos de risco
2. **Análise por Unidade** → aprofunde em cada unidade: áreas fracas, séries críticas, lista de alunos em risco
3. **Análise Temporal** → verifique se há evolução ou regressão ao longo das avaliações
4. **Aluno Individual** → acesse a ficha de qualquer aluno em risco via drill-through de P2
5. **Conclusões Executivas** → leia os 9 insights e as 3 recomendações de gestão acadêmica
""")

    st.divider()
    st.caption(
        "Regras de negócio: Proficiente = Nota ≥ 60 · Meta = 80% · "
        "Risco = nota < 50 em ≥2 avaliações + tendência de queda · "
        "Perc. área = Acertos / 20 · PCPc = Nota / 100"
    )
