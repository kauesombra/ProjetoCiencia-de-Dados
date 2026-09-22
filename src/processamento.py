"""
Processamento e integração das bases do Tema 1 — Economia e emprego
formal (Ceará).

Lê exclusivamente a camada raw, nunca sobrescreve os arquivos originais.
Produz uma única tabela analítica (grão: município) em
dados/analytical/base_municipios_tema1.csv, pronta para o dashboard.

Regras aplicadas (ver docs/analise_exploratoria.md e README.md):
- Chave de integração: territorio_codigo (código IBGE de 7 dígitos).
- Município = nivel_territorial_codigo "N6" (Brasil e Ceará são
  referências e não entram nas junções).
- PIB em mil reais; per capita multiplicado por 1.000 para ficar em R$.
- Estrutura setorial é de 2021; CEMPRE, PIB total e população são de
  2022 — cruzamentos entre elas têm defasagem temporal de 1 ano
  (marcada explicitamente nas colunas/documentação, nunca escondida).
- CEMPRE mede emprego FORMAL, não trabalho total: a razão pessoal
  ocupado / população é chamada de "intensidade de ocupação formal",
  nunca de "taxa de emprego".
- Nenhum símbolo especial do SIDRA (-, 0, X, .., ...) é convertido
  silenciosamente em zero.
"""

from pathlib import Path
import pandas as pd

from io_dados import (
    carregar_todas_as_bases,
    filtrar_municipios,
    SIMBOLOS_ESPECIAIS_SIDRA,
)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dados" / "processed"
ANALYTICAL_DIR = BASE_DIR / "dados" / "analytical"

# Códigos de variável usados de cada tabela (ver dados/raw/README_DADOS.md)
VAR = {
    "pib_2022": "37",
    "pib_2021": "37",
    "vab_total_2021": "498",
    "vab_agro_2021": "513",
    "part_agro_2021": "516",
    "vab_ind_2021": "517",
    "part_ind_2021": "520",
    "vab_serv_2021": "6575",
    "part_serv_2021": "6574",
    "vab_adm_2021": "525",
    "part_adm_2021": "528",
    "unidades_locais": "706",
    "empresas": "367",
    "ocupado_total": "707",
    "ocupado_assalariado": "708",
    "salarios_total": "662",
    "salario_medio": "10143",
    "populacao_2022": "93",
    "var_pop_abs": "5936",
    "tcg": "10605",
}


def _extrair(df: pd.DataFrame, codigo_var: str, novo_nome: str) -> pd.DataFrame:
    """Filtra municípios (N6), seleciona uma variável pelo código e
    devolve territorio_codigo/territorio_nome + a coluna renomeada,
    convertendo para numérico e preservando símbolos especiais como
    ausência (NaN) documentada — nunca como zero silencioso."""
    sub = filtrar_municipios(df)
    sub = sub[sub["variavel_codigo"] == codigo_var].copy()
    n_especiais = sub["valor"].astype(str).isin(SIMBOLOS_ESPECIAIS_SIDRA).sum()
    if n_especiais:
        print(f"  aviso: {n_especiais} símbolo(s) especial(is) em {novo_nome} -> tratado(s) como ausente")
    sub["valor"] = pd.to_numeric(sub["valor"], errors="coerce")
    sub = sub.rename(columns={"valor": novo_nome})
    return sub[["territorio_codigo", "territorio_nome", novo_nome]]


def _limpar_nome_municipio(nome: pd.Series) -> pd.Series:
    """Remove o sufixo ' - CE' do território para exibição no dashboard."""
    return nome.str.replace(r"\s*-\s*CE$", "", regex=True)


def construir_base_integrada() -> pd.DataFrame:
    print("Carregando tabelas raw...")
    bases = carregar_todas_as_bases()

    cempre, pib22, estrutura21, censo22 = (
        bases["cempre"], bases["pib_2022"], bases["estrutura_2021"], bases["censo_2022"]
    )

    print("Extraindo variáveis por tabela...")
    partes = [
        _extrair(pib22, VAR["pib_2022"], "pib_mil_reais_2022"),
        _extrair(estrutura21, VAR["pib_2021"], "pib_mil_reais_2021"),
        _extrair(estrutura21, VAR["vab_total_2021"], "vab_total_mil_reais_2021"),
        _extrair(estrutura21, VAR["vab_agro_2021"], "vab_agropecuaria_mil_reais_2021"),
        _extrair(estrutura21, VAR["part_agro_2021"], "participacao_agropecuaria_2021_pct"),
        _extrair(estrutura21, VAR["vab_ind_2021"], "vab_industria_mil_reais_2021"),
        _extrair(estrutura21, VAR["part_ind_2021"], "participacao_industria_2021_pct"),
        _extrair(estrutura21, VAR["vab_serv_2021"], "vab_servicos_mil_reais_2021"),
        _extrair(estrutura21, VAR["part_serv_2021"], "participacao_servicos_2021_pct"),
        _extrair(estrutura21, VAR["vab_adm_2021"], "vab_adm_publica_mil_reais_2021"),
        _extrair(estrutura21, VAR["part_adm_2021"], "participacao_adm_publica_2021_pct"),
        _extrair(cempre, VAR["unidades_locais"], "cempre_unidades_locais"),
        _extrair(cempre, VAR["empresas"], "cempre_empresas"),
        _extrair(cempre, VAR["ocupado_total"], "cempre_pessoal_ocupado_total"),
        _extrair(cempre, VAR["ocupado_assalariado"], "cempre_pessoal_ocupado_assalariado"),
        _extrair(cempre, VAR["salarios_total"], "cempre_salarios_mil_reais_2022"),
        _extrair(cempre, VAR["salario_medio"], "cempre_salario_medio_mensal_reais"),
        _extrair(censo22, VAR["populacao_2022"], "populacao_2022"),
        _extrair(censo22, VAR["var_pop_abs"], "variacao_absoluta_pop_2010_2022"),
        _extrair(censo22, VAR["tcg"], "taxa_crescimento_geometrico_pct"),
    ]

    print("Integrando pelo territorio_codigo (chave IBGE)...")
    base = partes[0]
    for parte in partes[1:]:
        antes = base.shape[0]
        base = base.merge(
            parte.drop(columns=["territorio_nome"]),
            on="territorio_codigo", how="outer",
        )
        assert base.shape[0] == antes or antes == 0, "cardinalidade inesperada na junção 1:1"

    n_total = base.shape[0]
    n_completos = base.drop(columns=["territorio_codigo", "territorio_nome"]).notna().all(axis=1).sum()
    print(f"Cardinalidade esperada: 184 municípios (junção 1:1 por território)")
    print(f"Correspondência: {base.shape[0]} municípios na base integrada; "
          f"{n_completos}/{n_total} ({100*n_completos/n_total:.1f}%) com todas as variáveis presentes")

    base["territorio_nome"] = _limpar_nome_municipio(base["territorio_nome"])

    # --- Indicadores derivados (documentados em docs/analise_exploratoria.md) ---
    base["pib_per_capita_2022"] = base["pib_mil_reais_2022"] * 1000 / base["populacao_2022"]
    base["intensidade_ocupacao_formal_pct"] = (
        base["cempre_pessoal_ocupado_total"] / base["populacao_2022"] * 100
    )
    base["unidades_locais_por_mil_hab"] = (
        base["cempre_unidades_locais"] / base["populacao_2022"] * 1000
    )
    base["proporcao_assalariados_pct"] = (
        base["cempre_pessoal_ocupado_assalariado"] / base["cempre_pessoal_ocupado_total"] * 100
    )
    base["salarios_por_assalariado_mil_reais"] = (
        base["cempre_salarios_mil_reais_2022"] / base["cempre_pessoal_ocupado_assalariado"]
    )
    # Variação nominal do PIB 2021->2022 (defasagem: estrutura setorial é 2021)
    base["variacao_pib_nominal_2021_2022_pct"] = (
        (base["pib_mil_reais_2022"] - base["pib_mil_reais_2021"]) / base["pib_mil_reais_2021"] * 100
    )

    # Perfil setorial dominante (exploratório, não oficial) — maior participação entre os 4 setores
    setores_pct = base[[
        "participacao_agropecuaria_2021_pct", "participacao_industria_2021_pct",
        "participacao_servicos_2021_pct", "participacao_adm_publica_2021_pct",
    ]].rename(columns=lambda c: c.replace("participacao_", "").replace("_2021_pct", ""))
    base["perfil_setorial_dominante"] = setores_pct.idxmax(axis=1).str.capitalize()

    colunas_ordenadas = [
        "territorio_codigo", "territorio_nome",
        "populacao_2022", "variacao_absoluta_pop_2010_2022", "taxa_crescimento_geometrico_pct",
        "pib_mil_reais_2022", "pib_mil_reais_2021", "pib_per_capita_2022", "variacao_pib_nominal_2021_2022_pct",
        "vab_total_mil_reais_2021",
        "vab_agropecuaria_mil_reais_2021", "participacao_agropecuaria_2021_pct",
        "vab_industria_mil_reais_2021", "participacao_industria_2021_pct",
        "vab_servicos_mil_reais_2021", "participacao_servicos_2021_pct",
        "vab_adm_publica_mil_reais_2021", "participacao_adm_publica_2021_pct",
        "perfil_setorial_dominante",
        "cempre_unidades_locais", "cempre_empresas",
        "cempre_pessoal_ocupado_total", "cempre_pessoal_ocupado_assalariado",
        "proporcao_assalariados_pct", "unidades_locais_por_mil_hab", "intensidade_ocupacao_formal_pct",
        "cempre_salarios_mil_reais_2022", "cempre_salario_medio_mensal_reais",
        "salarios_por_assalariado_mil_reais",
    ]
    base = base[colunas_ordenadas].sort_values("territorio_codigo").reset_index(drop=True)
    return base


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTICAL_DIR.mkdir(parents=True, exist_ok=True)

    base = construir_base_integrada()

    saida = ANALYTICAL_DIR / "base_municipios_tema1.csv"
    base.to_csv(saida, sep=";", index=False, encoding="utf-8-sig")
    print(f"\nBase analítica salva em: {saida}")
    print(f"Linhas: {base.shape[0]} | Colunas: {base.shape[1]}")

    ausencias = base.drop(columns=["territorio_codigo", "territorio_nome"]).isna().sum()
    ausencias = ausencias[ausencias > 0]
    if len(ausencias):
        print("\nColunas com valores ausentes (símbolo especial documentado, não imputado):")
        print(ausencias.to_string())
    else:
        print("\nNenhum valor ausente nas variáveis selecionadas.")


if __name__ == "__main__":
    main()
