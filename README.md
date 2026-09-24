# Dashboard Analítico — Desempenho Acadêmico

Solução analítica desenvolvida em Python + Streamlit para análise de desempenho acadêmico de uma instituição de ensino médico com 6 unidades, séries 9–12 e 4 avaliações ao longo de 2026.

---

## Visão Geral

O projeto transforma duas bases de dados brutas (notas e acertos por área de conhecimento) em um dashboard interativo com drill-through, permitindo navegar da visão institucional até a ficha individual de cada aluno.

**Dados:** 720 alunos · 4 avaliações · 6 unidades · 2.880 registros por tabela

---

## Estrutura do Projeto

```
├── app.py                  # Entrada da aplicação e roteamento
├── src/
│   ├── data_loader.py      # Ingestão, tratamento e modelagem (star schema)
│   └── metrics.py          # Camada de métricas (28+ funções)
├── pages/
│   ├── p0_home.py          # Home — mapa de navegação
│   ├── p1_visao_executiva.py
│   ├── p2_unidade.py
│   ├── p3_temporal.py
│   ├── p4_aluno.py
│   └── p5_conclusoes.py
└── requirements.txt
```

---

## Modelagem — Star Schema

Os dados brutos foram modelados em star schema para eliminar redundância e garantir contexto de filtro correto nas métricas:

| Tabela | Tipo | Descrição |
|---|---|---|
| `fact_prova` | Fato | Nota, PCPc, Conceito PCP, status de participação por RA × Avaliação |
| `fact_area` | Fato | Acertos por área (CIR, CM, GO, PED, PREV) por RA × Avaliação |
| `dim_aluno` | Dimensão | RA, Nome, Unidade, Série, Ciclo, Enamedista |
| `dim_avaliacao` | Dimensão | Avaliação, Período Letivo, Data, Tipo |

Faltosos são nulificados na ingestão — não contaminam médias, proficiência ou PCPc.

---

## Páginas do Dashboard

| Página | O que responde |
|---|---|
| 🏠 Home | Mapa de navegação e contexto dos dados |
| 📊 Visão Executiva | Panorama institucional, KPIs, proficiência por unidade vs. meta de 80% |
| 🏫 Análise por Unidade | Comparativo entre unidades, desempenho por área, alunos em risco |
| 📅 Análise Temporal | Evolução AV1→AV4, Diagnóstica vs. Desempenho, Ciclo Básico vs. Clínico |
| 👤 Aluno Individual | Ficha completa com histórico, evolução por área e flag de risco |
| 💡 Conclusões | Insights, recomendações de gestão e documentação das regras de negócio |

**Drill-through:** Visão Executiva → Unidade → Aluno Individual

---

## Principais Métricas Implementadas

- Participação: total de alunos, participantes, faltosos, % participação
- Desempenho: nota média, mediana, maior/menor nota, % proficientes (≥ 60), % abaixo de 50
- PCP: PCPc médio, Conceito PCP (1–5), distribuição por faixa
- Áreas: % médio de acerto por área, área mais forte/fraca, gap melhor/pior área
- Risco: alunos em risco com critério composto (nota < 50 em 2+ avaliações + tendência de queda), severidade (moderado/alto/crítico)
- Comparativo: gap unidade vs. instituição, proficiência por grupo

---

## Regra de Priorização de Alunos em Risco

Critério composto aplicado apenas a participantes válidos:

1. Nota < 50 em **2 ou mais avaliações** — risco persistente, não pontual
2. **Tendência de queda** — AV2 < AV1 ou AV4 < AV3

Diferencia alunos com dificuldade estrutural daqueles com queda isolada.

---

## Como Executar

```bash
# 1. Clone o repositório
git clone https://github.com/<seu-usuario>/<repo>.git
cd <repo>

# 2. Crie o ambiente virtual e instale as dependências
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Adicione o arquivo de dados em data/
# (não versionado — ver .gitignore)

# 4. Rode a aplicação
streamlit run app.py
```

Acesse em http://localhost:8501

---

## Stack

- **Python 3.8** · Pandas · NumPy
- **Streamlit 1.40** — interface e navegação
- **Plotly** — gráficos interativos (barras, radar, heatmap, linha, donut)
- **OpenPyXL** — leitura do Excel
