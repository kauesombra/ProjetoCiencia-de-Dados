# Projeto 1 — Economia e Emprego Formal (Ceará)

Análise exploratória e dashboard sobre economia e emprego formal nos
municípios do Ceará, com dados do IBGE/SIDRA (disciplina de Ciência de
Dados).

## Equipe

- Kauê Sombra
- Derek

## Objetivo

Integrar tabelas do SIDRA (pelo código IBGE do município) para produzir
uma análise reproduzível e um dashboard sobre economia e emprego formal
nos municípios cearenses.

## Perguntas de análise

1. Qual é o PIB per capita dos municípios em 2022?
2. Como a intensidade de ocupação formal (CEMPRE) se relaciona com o PIB
   per capita?
3. Qual a composição setorial do VAB (2021) entre os municípios?
4. Existe associação entre estrutura setorial (2021) e emprego/salário
   (2022)? *(defasagem de 1 ano — associação, não causalidade)*

## Bases de dados

| Tabela | Ano | Conteúdo |
|---|---|---|
| 9509 | 2022 | CEMPRE — empresas, pessoal ocupado, salários |
| 5938 | 2021 | PIB, VAB e estrutura setorial |
| 5938 | 2022 | PIB total |
| 4709 | 2022 | Censo — população |
| — | 2022 | Malha municipal do Ceará (geojson) |

Chave de integração: `territorio_codigo` (código IBGE, 7 dígitos).
Brasil e Ceará são referências e não entram em somas municipais.

## Cuidados metodológicos

- PIB em **mil reais**, população em pessoas — multiplicar por 1.000 no
  per capita.
- Estrutura setorial é de 2021, CEMPRE/Censo de 2022 — cruzamentos entre
  elas têm defasagem de 1 ano.
- CEMPRE mede só emprego **formal**; chamar de *intensidade de ocupação
  formal*, não "taxa de emprego".
- Valores nominais — variação 2021→2022 não é crescimento real.
- Pareamento sempre por `territorio_codigo`, nunca por nome.
- Sem aprendizado de máquina. Sem conclusões causais.

## Estrutura do repositório

```
projeto-1/
  dados/{raw, processed, analytical}
  notebooks/    # análise reproduzível
  src/          # funções de carga (io_dados.py)
  app/          # dashboard Streamlit
  docs/         # acompanhamento.pdf, slides.pdf
```

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1) Gera a base analítica integrada (lê dados/raw, grava dados/analytical)
python src/processamento.py

# 2) Abre os notebooks de exploração (opcional)
jupyter lab notebooks/

# 3) Roda o dashboard localmente
streamlit run app/app.py
```

## Dashboard

O dashboard (`app/app.py`) lê exclusivamente `dados/analytical/base_municipios_tema1.csv`
(gerado por `src/processamento.py`) e `dados/raw/dados_comuns/malha_municipal_ce_2022.geojson` —
nenhuma chamada ao SIDRA em tempo de execução. Ele traz:

- KPIs (PIB per capita, intensidade de ocupação formal, salário médio, participação industrial);
- filtros por perfil setorial dominante, faixa de população e município;
- mapa coroplético e ranking por indicador (comparação territorial);
- dispersão estrutura setorial (2021) × emprego/remuneração (2022), com aviso de defasagem temporal;
- três evidências visuais de cruzamento entre bases (PIB × Censo × CEMPRE; CEMPRE × estrutura setorial; PIB × Censo);
- aba de fontes, metodologia e limitações.

### Publicar no Streamlit Community Cloud

1. Suba este repositório no GitHub (já incluindo `dados/analytical/base_municipios_tema1.csv`
   gerado — o Streamlit Cloud não roda `processamento.py` sozinho, então gere o CSV localmente
   e faça commit dele).
2. Em https://share.streamlit.io, clique em "New app", selecione o repositório, a branch e o
   caminho `app/app.py`.
3. Deploy. A URL pública gerada não exige login — é essa URL que vai no PDF final e no README.

## Fontes

URLs, filtros e hashes de cada arquivo: `dados/raw/fontes.csv`.
Descrição completa das tabelas: `dados/raw/README_DADOS.md`.