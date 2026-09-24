import pandas as pd

AREAS = ["CIR", "CM", "GO", "PED", "PREV"]
PERC_AREAS = ["Perc_CIR", "Perc_CM", "Perc_GO", "Perc_PED", "Perc_PREV"]
ORDEM_AVALIACOES = ["AV1T-2026.1", "AV2T-2026.1", "AV3T-2026.2", "AV4T-2026.2"]
NOTA_PROFICIENTE = 60
NOTA_RISCO = 50
MAX_ACERTOS_AREA = 20


# ── Helpers internos ──────────────────────────────────────────────────────────

def _presentes(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra participantes válidos. fact_area requer _enrich_area antes de chamar."""
    return df[df["Status_Participacao"] == "Presente"]


def _enrich_area(fact_area: pd.DataFrame, fact_prova: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstrói Status_Participacao e Perc_* em runtime.
    Perc_* = Acertos / 20 — derivado, não armazenado no modelo.
    """
    status = fact_prova[["RA", "Avaliacao", "Status_Participacao"]]
    df = fact_area.merge(status, on=["RA", "Avaliacao"], how="left")
    for col in AREAS:
        df[f"Perc_{col}"] = df[col] / MAX_ACERTOS_AREA
    return df


def _prof_series(s: pd.Series) -> float:
    """% de registros com nota >= NOTA_PROFICIENTE em uma Series."""
    if len(s) == 0:
        return 0.0
    return (s >= NOTA_PROFICIENTE).sum() / len(s)


# ── Participação ──────────────────────────────────────────────────────────────

def total_alunos(df_prova: pd.DataFrame) -> int:
    """Alunos distintos por RA."""
    return df_prova["RA"].nunique()


def total_registros(df_prova: pd.DataFrame) -> int:
    """Total de registros RA × Avaliação."""
    return len(df_prova)


def total_participantes(df_prova: pd.DataFrame) -> int:
    """Registros com Status = Presente."""
    return len(_presentes(df_prova))


def total_faltosos(df_prova: pd.DataFrame) -> int:
    """Registros com Status = Faltoso."""
    return len(df_prova[df_prova["Status_Participacao"] == "Faltoso"])


def perc_participacao(df_prova: pd.DataFrame) -> float:
    t = total_registros(df_prova)
    return total_participantes(df_prova) / t if t else 0.0


# ── Desempenho escalar ────────────────────────────────────────────────────────

def nota_media(df_prova: pd.DataFrame) -> float:
    return _presentes(df_prova)["Nota_Avalia"].mean()


def nota_mediana(df_prova: pd.DataFrame) -> float:
    return _presentes(df_prova)["Nota_Avalia"].median()


def maior_nota(df_prova: pd.DataFrame) -> float:
    return _presentes(df_prova)["Nota_Avalia"].max()


def menor_nota(df_prova: pd.DataFrame) -> float:
    return _presentes(df_prova)["Nota_Avalia"].min()


def perc_proficientes(df_prova: pd.DataFrame) -> float:
    return _prof_series(_presentes(df_prova)["Nota_Avalia"])


def perc_abaixo_50(df_prova: pd.DataFrame) -> float:
    p = _presentes(df_prova)
    if len(p) == 0:
        return 0.0
    return (p["Nota_Avalia"] < NOTA_RISCO).sum() / len(p)


def pcpc_medio(df_prova: pd.DataFrame) -> float:
    return _presentes(df_prova)["PCPc"].mean()


def gap_unidade_vs_instituicao(df_prova_unidade: pd.DataFrame,
                                df_prova_completo: pd.DataFrame) -> float:
    return nota_media(df_prova_unidade) - nota_media(df_prova_completo)


# ── Desempenho agrupado — substitui todos os groupby das páginas ──────────────

def nota_media_por_grupo(df_prova: pd.DataFrame, grupos: list) -> pd.DataFrame:
    """
    Nota média de presentes agrupada por qualquer combinação de colunas.
    Uso: nota_media_por_grupo(df, ['Unidade', 'Avaliacao'])
    """
    p = _presentes(df_prova)
    return (
        p.groupby(grupos, observed=True)["Nota_Avalia"]
        .mean()
        .reset_index()
        .rename(columns={"Nota_Avalia": "Nota_Media"})
        .sort_values(grupos)
    )


def proficiencia_por_grupo(df_prova: pd.DataFrame, grupos: list) -> pd.DataFrame:
    """
    % de proficientes (Nota >= 60) de presentes agrupado por qualquer combinação de colunas.
    Uso: proficiencia_por_grupo(df, ['Unidade'])
         proficiencia_por_grupo(df, ['Ciclo', 'Avaliacao'])
    """
    p = _presentes(df_prova)
    return (
        p.groupby(grupos, observed=True)["Nota_Avalia"]
        .apply(_prof_series)
        .mul(100)
        .reset_index()
        .rename(columns={"Nota_Avalia": "Proficiencia"})
        .sort_values(grupos)
    )


def pcpc_por_grupo(df_prova: pd.DataFrame, grupos: list) -> pd.DataFrame:
    """PCPc médio de presentes agrupado por qualquer combinação de colunas."""
    p = _presentes(df_prova)
    return (
        p.groupby(grupos, observed=True)["PCPc"]
        .mean()
        .reset_index()
        .rename(columns={"PCPc": "PCPc_Medio"})
        .sort_values(grupos)
    )


def distribuicao_faixa(df_prova: pd.DataFrame) -> pd.DataFrame:
    """Contagem de presentes por faixa de desempenho."""
    p = _presentes(df_prova)
    return (
        p.groupby("Desempenho", observed=True)
        .size()
        .reset_index(name="Qtd")
        .rename(columns={"Desempenho": "Faixa"})
    )


# ── Áreas ─────────────────────────────────────────────────────────────────────

def perc_medio_por_area(fact_area: pd.DataFrame, fact_prova: pd.DataFrame) -> pd.Series:
    """% médio de acerto por área (escalar por área)."""
    df = fact_area if "Status_Participacao" in fact_area.columns else _enrich_area(fact_area, fact_prova)
    p = _presentes(df)
    return p[PERC_AREAS].mean().rename(lambda c: c.replace("Perc_", ""))


def perc_area_por_grupo(fact_area: pd.DataFrame, fact_prova: pd.DataFrame,
                        grupos: list) -> pd.DataFrame:
    """
    % médio de acerto por área agrupado por qualquer combinação de colunas.
    Retorna formato longo: grupos_sem_area + ['Area', 'Perc_Acerto'].
    'Area' não deve constar em grupos — é criada pelo melt interno.
    fact_area pode ser o fato bruto ou já enriquecido com _enrich_area.
    """
    if "Status_Participacao" not in fact_area.columns:
        df = _enrich_area(fact_area, fact_prova)
    else:
        df = fact_area
    p = _presentes(df)
    # remove 'Area' dos grupos: a coluna só existe após o melt, não antes
    grupos_base = [g for g in grupos if g != "Area"]
    return (
        p.groupby(grupos_base, observed=True)[PERC_AREAS]
        .mean()
        .reset_index()
        .melt(id_vars=grupos_base, var_name="Area", value_name="Perc_Acerto")
        .assign(Area=lambda d: d["Area"].str.replace("Perc_", ""),
                Perc_Acerto=lambda d: d["Perc_Acerto"] * 100)
        .sort_values(grupos_base)
    )


def gap_melhor_pior_area(fact_area: pd.DataFrame, fact_prova: pd.DataFrame) -> float:
    """Retorna gap em pontos percentuais (0-100)."""
    medias = perc_medio_por_area(fact_area, fact_prova)
    return (medias.max() - medias.min()) * 100


def nota_mediana_por_grupo(df_prova: pd.DataFrame, grupos: list) -> pd.DataFrame:
    """Nota mediana de presentes agrupada por qualquer combinação de colunas."""
    p = _presentes(df_prova)
    return (
        p.groupby(grupos, observed=True)["Nota_Avalia"]
        .median()
        .reset_index()
        .rename(columns={"Nota_Avalia": "Nota_Mediana"})
        .sort_values(grupos)
    )


def distribuicao_faixa_por_grupo(df_prova: pd.DataFrame, grupos: list) -> pd.DataFrame:
    """
    Contagem de presentes por faixa de desempenho agrupada por qualquer combinação de colunas.
    Retorna formato longo: grupos + ['Desempenho', 'Qtd'].
    """
    p = _presentes(df_prova)
    return (
        p.groupby(grupos + ["Desempenho"], observed=True)
        .size()
        .reset_index(name="Qtd")
        .sort_values(grupos)
    )


# ── Risco ─────────────────────────────────────────────────────────────────────

def alunos_em_risco(df_prova: pd.DataFrame) -> list:
    """
    Critério composto (apenas presentes):
    1. Nota < 50 em 2 ou mais avaliações
    2. Tendência de queda: AV2 < AV1 ou AV4 < AV3
    """
    p = _presentes(df_prova).copy()
    p["Avaliacao"] = pd.Categorical(p["Avaliacao"], categories=ORDEM_AVALIACOES, ordered=True)
    pivot = p.pivot_table(index="RA", columns="Avaliacao", values="Nota_Avalia")

    abaixo_50 = (pivot < NOTA_RISCO).sum(axis=1) >= 2

    queda = pd.Series(False, index=pivot.index)
    if "AV1T-2026.1" in pivot.columns and "AV2T-2026.1" in pivot.columns:
        queda |= pivot["AV2T-2026.1"] < pivot["AV1T-2026.1"]
    if "AV3T-2026.2" in pivot.columns and "AV4T-2026.2" in pivot.columns:
        queda |= pivot["AV4T-2026.2"] < pivot["AV3T-2026.2"]

    return pivot[abaixo_50 & queda].index.tolist()


def risco_por_grupo(df_prova: pd.DataFrame, dim_aluno: pd.DataFrame,
                    grupos: list) -> pd.DataFrame:
    """Contagem de alunos em risco agrupada por qualquer combinação de colunas de dim_aluno."""
    ras_risco = alunos_em_risco(df_prova)
    return (
        dim_aluno[dim_aluno["RA"].isin(ras_risco)]
        .groupby(grupos).size()
        .reset_index(name="Alunos em Risco")
        .sort_values(grupos)
    )


def total_alunos_em_risco(df_prova: pd.DataFrame) -> int:
    return len(alunos_em_risco(df_prova))


def perc_alunos_em_risco(df_prova: pd.DataFrame) -> float:
    t = total_alunos(df_prova)
    return total_alunos_em_risco(df_prova) / t if t else 0.0


def severidade_risco(df_prova: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna DataFrame com RA e nível de severidade para alunos em risco:
      Nível 1 — 2 avaliações abaixo de 50  (risco moderado)
      Nível 2 — 3 avaliações abaixo de 50  (risco alto)
      Nível 3 — 4 avaliações abaixo de 50  (risco crítico)
    Apenas alunos que já atendem o critério composto de alunos_em_risco.
    """
    ras_risco = alunos_em_risco(df_prova)
    if not ras_risco:
        return pd.DataFrame(columns=["RA", "Avaliacoes_Abaixo_50", "Severidade", "Label"])
    p = _presentes(df_prova).copy()
    p["Avaliacao"] = pd.Categorical(p["Avaliacao"], categories=ORDEM_AVALIACOES, ordered=True)
    pivot = p.pivot_table(index="RA", columns="Avaliacao", values="Nota_Avalia")
    contagem = (pivot.loc[ras_risco] < NOTA_RISCO).sum(axis=1).reset_index()
    contagem.columns = ["RA", "Avaliacoes_Abaixo_50"]
    contagem["Severidade"] = contagem["Avaliacoes_Abaixo_50"].map({2: 1, 3: 2, 4: 3})
    contagem["Label"] = contagem["Severidade"].map(
        {1: "🟡 Moderado (2 av.)", 2: "🟠 Alto (3 av.)", 3: "🔴 Crítico (4 av.)"}
    )
    return contagem
