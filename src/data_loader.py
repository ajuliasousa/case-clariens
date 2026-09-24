import pandas as pd
from pathlib import Path

EXCEL_PATH = Path(__file__).parent.parent / "data" / "Avaliacao_Analista_dados_Candidato.xlsx"

ORDEM_AVALIACOES = ["AV1T-2026.1", "AV2T-2026.1", "AV3T-2026.2", "AV4T-2026.2"]


def _load_raw():
    prova = pd.read_excel(EXCEL_PATH, sheet_name="Dados_Prova", dtype={"RA": str})
    area = pd.read_excel(EXCEL_PATH, sheet_name="Dados_Area", dtype={"RA": str})
    return prova, area


def _treat(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["RA"] = df["RA"].astype(str).str.strip()
    df["Data_Prova"] = pd.to_datetime(df["Data_Prova"])
    df["Serie"] = df["Serie"].astype(int)
    # Periodo_Letivo vem como int64 (20261, 20262) — converter para string
    df["Periodo_Letivo"] = df["Periodo_Letivo"].astype(str).str.strip()
    df["Avaliacao"] = pd.Categorical(df["Avaliacao"], categories=ORDEM_AVALIACOES, ordered=True)

    # Faltosos têm Nota_Avalia=0 e Desempenho/Conceito_PCP='Sem nota'/'Sem conceito'
    # Nulificar métricas de faltosos para evitar contaminação em agregações
    faltoso = df["Status_Participacao"] == "Faltoso"
    if "Nota_Avalia" in df.columns:
        df.loc[faltoso, "Nota_Avalia"] = pd.NA
        df["Nota_Avalia"] = df["Nota_Avalia"].astype("Int64")
    if "PCPc" in df.columns:
        df.loc[faltoso, "PCPc"] = pd.NA
    for col in ["CIR", "CM", "GO", "PED", "PREV"]:
        if col in df.columns:
            df.loc[faltoso, col] = pd.NA
            df[col] = df[col].astype("Int64")
    for col in ["Perc_CIR", "Perc_CM", "Perc_GO", "Perc_PED", "Perc_PREV"]:
        if col in df.columns:
            df.loc[faltoso, col] = pd.NA

    # Padronizar label da faixa 1 (base usa '1 - 0 a 39.99', regra de negócio é '1 - <40')
    if "Desempenho" in df.columns:
        df["Desempenho"] = df["Desempenho"].str.replace("1 - 0 a 39.99", "1 - <40", regex=False)

    return df


def load_data():
    """Carrega, trata e retorna (df_prova, df_area, dim_aluno, dim_avaliacao)."""
    prova, area = _load_raw()
    prova = _treat(prova)
    area = _treat(area)

    dim_aluno = (
        prova[["RA", "Aluno", "Unidade", "Serie", "Ciclo", "Enamedista"]]
        .drop_duplicates(subset="RA")
        .reset_index(drop=True)
    )

    dim_avaliacao = (
        prova[["Avaliacao", "Periodo_Letivo", "Data_Prova", "Tipo_Avaliacao"]]
        .drop_duplicates(subset="Avaliacao")
        .sort_values("Avaliacao")
        .reset_index(drop=True)
    )

    # ── fact_prova: medidas brutas apenas; colunas calculadas derivadas em runtime ──
    # Desempenho, PCPc e Conceito_PCP são derivados de Nota_Avalia pelas regras de
    # negócio — mantidos aqui apenas para exibição na ficha do aluno (p4), não
    # usados em nenhum cálculo agregado.
    fact_prova = prova[["RA", "Avaliacao", "Status_Participacao", "Nota_Avalia",
                        "Desempenho", "PCPc", "Conceito_PCP"]]

    # ── fact_area: apenas acertos brutos; Perc_* removidos (derivados: col/20) ──
    # Status_Participacao removido: já existe em fact_prova para a mesma chave
    # RA+Avaliacao, sem nenhuma divergência — redundância confirmada em auditoria.
    fact_area = area[["RA", "Avaliacao",
                      "CIR", "CM", "GO", "PED", "PREV"]]

    return fact_prova, fact_area, dim_aluno, dim_avaliacao
