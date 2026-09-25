import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
from data_loader import load_data

st.set_page_config(
    page_title="Clariens — Desempenho Acadêmico",
    page_icon="🎓",
    layout="wide",
)

@st.cache_data
def get_data():
    return load_data()

fact_prova, fact_area, dim_aluno, dim_avaliacao = get_data()

PAGINAS = [
    "🏠 Home",
    "📊 Visão Executiva",
    "🏫 Análise por Unidade",
    "📅 Análise Temporal",
    "👤 Aluno Individual",
    "📈 Score de Risco",
    "💡 Conclusões Executivas",
]

# inicializa session_state na primeira execução
if "pagina" not in st.session_state:
    st.session_state["pagina"] = PAGINAS[0]
if "drill_ra" not in st.session_state:
    st.session_state["drill_ra"] = None
if "drill_unidade" not in st.session_state:
    st.session_state["drill_unidade"] = None

with st.sidebar:
    st.title("🎓 Clariens")
    st.caption("Desempenho Acadêmico 2026")
    st.divider()
    # radio sincronizado com session_state — permite que outras páginas mudem a navegação
    pagina = st.radio(
        "Navegação", PAGINAS,
        index=PAGINAS.index(st.session_state["pagina"]),
        label_visibility="collapsed",
    )
    # atualiza session_state quando o usuário clica no radio manualmente
    if pagina != st.session_state["pagina"]:
        st.session_state["pagina"] = pagina
        st.session_state["drill_ra"] = None  # limpa drill ao navegar manualmente

pagina_ativa = st.session_state["pagina"]

if pagina_ativa == PAGINAS[0]:
    from pages.p0_home import render
elif pagina_ativa == PAGINAS[1]:
    from pages.p1_visao_executiva import render
elif pagina_ativa == PAGINAS[2]:
    from pages.p2_unidade import render
elif pagina_ativa == PAGINAS[3]:
    from pages.p3_temporal import render
elif pagina_ativa == PAGINAS[4]:
    from pages.p4_aluno import render
elif pagina_ativa == PAGINAS[5]:
    from pages.p6_risco import render
else:
    from pages.p5_conclusoes import render

render(fact_prova, fact_area, dim_aluno, dim_avaliacao)
