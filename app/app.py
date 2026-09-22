"""
Dashboard — Economia e emprego formal nos municípios do Ceará (Tema 1)

O dashboard lê SOMENTE arquivos estáticos versionados no repositório
(dados/analytical e dados/raw/dados_comuns). Nenhuma chamada à API do
SIDRA em tempo de execução.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Configuração e carga de dados
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Economia e Emprego Formal — Ceará",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_BASE = BASE_DIR / "dados" / "analytical" / "base_municipios_tema1.csv"
CAMINHO_MALHA = BASE_DIR / "dados" / "raw" / "dados_comuns" / "malha_municipal_ce_2022.geojson"


@st.cache_data
def carregar_dados():
    df = pd.read_csv(CAMINHO_BASE, sep=";", encoding="utf-8-sig")
    df["territorio_codigo"] = df["territorio_codigo"].astype(str)
    with open(CAMINHO_MALHA, encoding="utf-8") as f:
        malha = json.load(f)
    return df, malha


try:
    df, malha_geojson = carregar_dados()
except FileNotFoundError:
    st.error(
        "Não foi possível encontrar `dados/analytical/base_municipios_tema1.csv`. "
        "Rode `python src/processamento.py` a partir da raiz do projeto antes de "
        "abrir o dashboard."
    )
    st.stop()

ROTULOS = {
    "pib_per_capita_2022": "PIB per capita 2022 (R$)",
    "intensidade_ocupacao_formal_pct": "Intensidade de ocupação formal (%)",
    "cempre_salario_medio_mensal_reais": "Salário médio mensal (R$)",
    "participacao_industria_2021_pct": "Participação da indústria no VAB 2021 (%)",
    "participacao_agropecuaria_2021_pct": "Participação da agropecuária no VAB 2021 (%)",
    "participacao_servicos_2021_pct": "Participação dos serviços no VAB 2021 (%)",
    "participacao_adm_publica_2021_pct": "Participação da adm. pública no VAB 2021 (%)",
    "unidades_locais_por_mil_hab": "Unidades locais por mil habitantes (2022)",
    "taxa_crescimento_geometrico_pct": "Taxa de crescimento geométrico pop. (%, 2010–2022)",
}

# ---------------------------------------------------------------------------
# Cabeçalho / Visão geral
# ---------------------------------------------------------------------------

st.title("Economia e emprego formal nos municípios do Ceará")
st.caption("Dados: IBGE/SIDRA — tabelas 9509 (CEMPRE), 5938 (PIB/VAB) e 4709 (Censo) | Malha municipal 2022")

with st.container(border=True):
    col_txt, col_use = st.columns([2, 1])
    with col_txt:
        st.markdown(
            "**Problema:** como a estrutura econômica dos municípios cearenses se "
            "relaciona com emprego formal, remuneração e crescimento populacional? "
            "O dashboard integra 184 municípios do Ceará a partir de quatro tabelas "
            "do SIDRA (CEMPRE 2022, PIB/VAB 2021 e 2022, e Censo 2022), pareadas pelo "
            "código IBGE do município."
        )
    with col_use:
        st.markdown(
            "**Como usar:** ajuste os filtros na barra lateral para restringir a "
            "análise a um grupo de municípios; os KPIs, o mapa, o ranking e os "
            "gráficos de cruzamento são recalculados automaticamente."
        )

# ---------------------------------------------------------------------------
# Filtros (barra lateral)
# ---------------------------------------------------------------------------

st.sidebar.header("Filtros")

perfis = sorted(df["perfil_setorial_dominante"].dropna().unique())
perfis_sel = st.sidebar.multiselect(
    "Perfil setorial dominante (VAB 2021)", options=perfis, default=perfis,
    help="Setor com maior participação no VAB municipal de 2021 (classificação exploratória, não oficial).",
)

pop_min, pop_max = int(df["populacao_2022"].min()), int(df["populacao_2022"].max())
faixa_pop = st.sidebar.slider(
    "População residente 2022", min_value=pop_min, max_value=pop_max,
    value=(pop_min, pop_max), step=1000, format="%d",
)

municipios_sel = st.sidebar.multiselect(
    "Restringir a municípios específicos (opcional)",
    options=sorted(df["territorio_nome"]), default=[],
)

st.sidebar.caption(
    "Estado inicial: todos os 184 municípios do Ceará, todos os perfis setoriais, "
    "toda a faixa populacional."
)

df_f = df[
    df["perfil_setorial_dominante"].isin(perfis_sel)
    & df["populacao_2022"].between(*faixa_pop)
]
if municipios_sel:
    df_f = df_f[df_f["territorio_nome"].isin(municipios_sel)]

if df_f.empty:
    st.warning(
        "Nenhum município atende aos filtros selecionados. Ajuste os filtros na "
        "barra lateral (por exemplo, amplie a faixa de população ou selecione mais "
        "perfis setoriais)."
    )
    st.stop()

st.caption(f"Municípios no filtro atual: **{df_f.shape[0]} de {df.shape[0]}**")

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

st.subheader("Indicadores essenciais")
k1, k2, k3, k4 = st.columns(4)
k1.metric("PIB per capita médio · 2022", f"R$ {df_f['pib_per_capita_2022'].mean():,.0f}".replace(",", "."))
k2.metric("Intensidade de ocupação formal média · 2022", f"{df_f['intensidade_ocupacao_formal_pct'].mean():.1f}%")
k3.metric("Salário médio mensal (média simples) · 2022", f"R$ {df_f['cempre_salario_medio_mensal_reais'].mean():,.0f}".replace(",", "."))
k4.metric("Participação industrial média no VAB · 2021", f"{df_f['participacao_industria_2021_pct'].mean():.1f}%")
st.caption(
    "Médias simples entre os municípios do filtro atual (não ponderadas pela "
    "população). Intensidade de ocupação formal = pessoal ocupado no CEMPRE / "
    "população residente — mede vínculos formais no município, não taxa de emprego."
)

st.divider()

# ---------------------------------------------------------------------------
# Abas principais
# ---------------------------------------------------------------------------

aba_territorio, aba_missao, aba_cruzamento, aba_fontes = st.tabs(
    ["🗺️ Comparação territorial", "🎯 Estrutura × emprego", "🔗 Cruzamento entre bases", "📎 Fontes e metodologia"]
)

# --- Aba 1: Comparação territorial -----------------------------------------
with aba_territorio:
    st.markdown("#### Onde estão os maiores e menores valores no Ceará")
    indicador = st.radio(
        "Indicador do mapa e do ranking",
        options=list(ROTULOS.keys())[:4],
        format_func=lambda c: ROTULOS[c],
        horizontal=True,
    )

    col_mapa, col_rank = st.columns([3, 2])

    with col_mapa:
        fig_mapa = px.choropleth_map(
            df_f, geojson=malha_geojson, locations="territorio_codigo",
            featureidkey="properties.codarea", color=indicador,
            hover_name="territorio_nome",
            hover_data={indicador: ":.1f", "territorio_codigo": False},
            color_continuous_scale="Viridis", map_style="carto-positron",
            zoom=5.6, center={"lat": -5.2, "lon": -39.3}, opacity=0.85,
            labels={indicador: ROTULOS[indicador]},
        )
        fig_mapa.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=480)
        st.plotly_chart(fig_mapa, width='stretch')
        st.caption(
            "Municípios fora do filtro atual aparecem sem cor no mapa. "
            "Fonte: malha municipal do Ceará 2022 (código IBGE `codarea`)."
        )

    with col_rank:
        n_rank = st.slider("Municípios no ranking", 5, 30, 10)
        ordem = st.toggle("Mostrar os menores valores (em vez dos maiores)", value=False)
        rank_df = df_f.sort_values(indicador, ascending=ordem).head(n_rank)
        fig_rank = px.bar(
            rank_df.sort_values(indicador), x=indicador, y="territorio_nome",
            orientation="h", labels={indicador: ROTULOS[indicador], "territorio_nome": ""},
        )
        fig_rank.update_layout(height=480, margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig_rank, width='stretch')

# --- Aba 2: Análise específica da missão ------------------------------------
with aba_missao:
    st.markdown("#### Pergunta orientadora: como a estrutura econômica (2021) se relaciona com emprego formal e remuneração (2022)?")
    st.info(
        "⚠️ A estrutura setorial é de **2021** e o CEMPRE é de **2022**: o cruzamento "
        "abaixo é uma **associação exploratória com defasagem de um ano**, não um "
        "retrato simultâneo nem uma relação causal.",
        icon="⚠️",
    )

    eixo_x = st.selectbox(
        "Variável de estrutura setorial (2021, eixo X)",
        options=["participacao_industria_2021_pct", "participacao_agropecuaria_2021_pct",
                 "participacao_servicos_2021_pct", "participacao_adm_publica_2021_pct"],
        format_func=lambda c: ROTULOS[c],
    )
    eixo_y = st.selectbox(
        "Indicador de emprego/remuneração (2022, eixo Y)",
        options=["intensidade_ocupacao_formal_pct", "cempre_salario_medio_mensal_reais"],
        format_func=lambda c: ROTULOS[c],
    )

    fig_disp = px.scatter(
        df_f, x=eixo_x, y=eixo_y, color="perfil_setorial_dominante",
        size="populacao_2022", size_max=40, hover_name="territorio_nome",
        trendline="ols", trendline_scope="overall",
        labels={eixo_x: ROTULOS[eixo_x], eixo_y: ROTULOS[eixo_y], "perfil_setorial_dominante": "Perfil setorial"},
    )
    fig_disp.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_disp, width='stretch')

    corr = df_f[eixo_x].corr(df_f[eixo_y])
    st.caption(
        f"Correlação de Pearson no filtro atual: **r = {corr:.2f}**. Tamanho da bolha "
        "= população 2022. Correlação não implica causalidade; ver limitações na aba "
        "'Fontes e metodologia'."
    )

# --- Aba 3: Cruzamento entre bases ------------------------------------------
with aba_cruzamento:
    st.markdown("#### Pelo menos duas evidências visuais derivadas de tabelas integradas")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**1) PIB per capita × intensidade de ocupação formal** _(PIB × Censo × CEMPRE, 2022)_")
        fig1 = px.scatter(
            df_f, x="pib_per_capita_2022", y="intensidade_ocupacao_formal_pct",
            hover_name="territorio_nome", color="perfil_setorial_dominante",
            labels={"pib_per_capita_2022": ROTULOS["pib_per_capita_2022"],
                    "intensidade_ocupacao_formal_pct": ROTULOS["intensidade_ocupacao_formal_pct"],
                    "perfil_setorial_dominante": "Perfil setorial"},
            log_x=True,
        )
        fig1.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig1, width='stretch')
        st.caption("Eixo X em escala logarítmica devido à forte assimetria do PIB per capita entre municípios.")

    with c2:
        st.markdown("**2) Salário médio por perfil setorial dominante** _(CEMPRE 2022 × estrutura setorial 2021)_")
        fig2 = px.box(
            df_f, x="perfil_setorial_dominante", y="cempre_salario_medio_mensal_reais",
            points="all", labels={"perfil_setorial_dominante": "Perfil setorial dominante (VAB 2021)",
                                    "cempre_salario_medio_mensal_reais": ROTULOS["cempre_salario_medio_mensal_reais"]},
        )
        fig2.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig2, width='stretch')
        st.caption("Cada ponto é um município; a caixa mostra mediana e quartis do salário médio dentro de cada perfil.")

    st.markdown("---")
    st.markdown("**3) Variação nominal do PIB (2021→2022) × crescimento populacional (2010→2022)** _(PIB × Censo)_")
    fig3 = px.scatter(
        df_f, x="taxa_crescimento_geometrico_pct", y="variacao_pib_nominal_2021_2022_pct",
        hover_name="territorio_nome", color="perfil_setorial_dominante",
        labels={"taxa_crescimento_geometrico_pct": ROTULOS["taxa_crescimento_geometrico_pct"],
                "variacao_pib_nominal_2021_2022_pct": "Variação nominal do PIB 2021–2022 (%)",
                "perfil_setorial_dominante": "Perfil setorial"},
    )
    fig3.add_hline(y=0, line_dash="dot", line_color="gray")
    fig3.add_vline(x=0, line_dash="dot", line_color="gray")
    fig3.update_layout(height=440, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig3, width='stretch')
    st.caption(
        "Variação de PIB **nominal** (preços correntes, sem deflator) — não deve ser "
        "lida como crescimento real da economia."
    )

# --- Aba 4: Fontes e metodologia --------------------------------------------
with aba_fontes:
    st.markdown("#### Tabelas do SIDRA utilizadas")
    st.table(pd.DataFrame([
        {"Tabela": "9509 — CEMPRE", "Período": "2022", "Conteúdo": "Unidades locais, empresas, pessoal ocupado, assalariados, salários"},
        {"Tabela": "5938 — PIB municipal", "Período": "2021", "Conteúdo": "PIB, VAB total e composição setorial (agropecuária, indústria, serviços, adm. pública)"},
        {"Tabela": "5938 — PIB municipal", "Período": "2022", "Conteúdo": "PIB total (única variável disponível nesse ano)"},
        {"Tabela": "4709 — Censo Demográfico", "Período": "2022", "Conteúdo": "População recenseada, variação desde 2010, taxa de crescimento geométrico"},
        {"Tabela": "Malha municipal do Ceará", "Período": "2022", "Conteúdo": "Geometria dos 184 municípios (uso cartográfico, não é uma das 3 tabelas SIDRA exigidas)"},
    ]))

    st.markdown("#### Metodologia")
    st.markdown(
        "- **Chave de integração:** `territorio_codigo` (código IBGE de 7 dígitos) — nunca por nome de município.\n"
        "- **Junção:** `outer join` das 4 tabelas pelo território, com verificação de correspondência "
        "(184/184 municípios pareados em todas as tabelas — 100%).\n"
        "- **Símbolos especiais do SIDRA** (`-`, `0`, `X`, `..`, `...`): convertidos para ausência (`NaN`) "
        "quando aplicável, nunca para zero silencioso.\n"
        "- **PIB per capita:** `PIB (mil R$) × 1.000 / população`, ambos de 2022.\n"
        "- **Intensidade de ocupação formal:** pessoal ocupado no CEMPRE / população residente × 100 — "
        "mede vínculos formais localizados no município, **não** é taxa de emprego (não cobre informalidade "
        "nem desemprego, e inclui quem trabalha no município mas reside em outro).\n"
        "- **Perfil setorial dominante:** setor (agropecuária, indústria, serviços ou administração pública) "
        "com maior participação no VAB municipal de 2021 — classificação **exploratória construída pela "
        "equipe**, não é um indicador oficial do IBGE.\n"
    )

    st.markdown("#### Limitações")
    st.markdown(
        "- Estrutura setorial (2021) cruzada com CEMPRE/PIB/população (2022): **defasagem de 1 ano**, "
        "tratada como associação, não retrato simultâneo.\n"
        "- Valores de PIB e VAB são **nominais** (preços correntes); variações entre anos não são "
        "deflacionadas e não representam crescimento real.\n"
        "- CEMPRE cobre apenas o **mercado formal**; não mede trabalho informal nem desemprego.\n"
        "- Nenhuma conclusão neste dashboard é causal — todas as relações mostradas são associações "
        "observacionais.\n"
        "- Sem uso de aprendizado de máquina, conforme requisito do projeto.\n"
    )

    st.markdown("#### Autoria")
    st.markdown("Projeto 1 — Ciência de Dados. Equipe: Kauê Sombra, Derek. Tema 1 — Economia e emprego formal.")
    st.caption(f"Base analítica: `dados/analytical/base_municipios_tema1.csv` ({df.shape[0]} municípios).")
