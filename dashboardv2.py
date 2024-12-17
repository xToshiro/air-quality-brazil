import os
import json
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuração inicial do Streamlit
st.set_page_config(page_title="Qualidade do Ar no Brasil", layout="wide")

# Função para carregar dados JSON
@st.cache_data
def load_json_data():
    with open('./data/estados.json', 'r', encoding='utf-8-sig') as f:
        estados = pd.DataFrame(json.load(f))
    with open('./data/municipios.json', 'r', encoding='utf-8-sig') as f:
        municipios = pd.DataFrame(json.load(f))
    return estados, municipios

# Função para listar bancos de dados SQLite
def list_sqlite_databases(path):
    return [f for f in os.listdir(path) if f.endswith('.sqlite')]

# Função para listar tabelas no banco de dados SQLite
def list_tables_in_sqlite(db_path):
    with sqlite3.connect(db_path) as conn:
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(query, conn)
    return tables['name'].tolist()

# Função para carregar dados da tabela
def load_table_data(db_path, table_name):
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df

# Carregar dados JSON
estados, municipios = load_json_data()

# Inicializar Session State para persistir banco e tabela
if "dados_tabela" not in st.session_state:
    st.session_state["dados_tabela"] = None
if "tabela_selecionada" not in st.session_state:
    st.session_state["tabela_selecionada"] = None
if "banco_selecionado" not in st.session_state:
    st.session_state["banco_selecionado"] = None
if "tabelas_disponiveis" not in st.session_state:
    st.session_state["tabelas_disponiveis"] = []

# Sidebar - Configurações de Filtros
st.sidebar.header("Configurações de Filtros")

# Fonte de Dados SQLite
st.sidebar.write("### Fonte de Dados (SQLite)")
fonte_dados_dir = "./data/air-quality-data/"
bancos_sqlite = list_sqlite_databases(fonte_dados_dir)

# Selecione o banco de dados
novo_banco = st.sidebar.selectbox("Selecione o Banco de Dados", bancos_sqlite, index=None, placeholder="Escolha um banco de dados...")

# Botão para carregar tabelas
if st.sidebar.button("Carregar Fonte de Dados") and novo_banco:
    db_path = os.path.join(fonte_dados_dir, novo_banco)
    st.session_state["tabelas_disponiveis"] = list_tables_in_sqlite(db_path)
    st.session_state["banco_selecionado"] = novo_banco
    st.session_state["dados_tabela"] = None
    st.session_state["tabela_selecionada"] = None
    st.sidebar.success(f"Banco de Dados '{novo_banco}' carregado com sucesso!")

# Exibir seleção de tabela apenas se o banco estiver carregado
if st.session_state["banco_selecionado"]:
    tabela_selecionada = st.sidebar.selectbox(
        "Selecione a Tabela",
        st.session_state["tabelas_disponiveis"],
        index=st.session_state["tabelas_disponiveis"].index(st.session_state["tabela_selecionada"])
        if st.session_state["tabela_selecionada"] in st.session_state["tabelas_disponiveis"] else None,
        placeholder="Escolha uma tabela...",
        key="tabela_selecionada_key"
    )

    # Carregar os dados da tabela selecionada
    if tabela_selecionada and tabela_selecionada != st.session_state["tabela_selecionada"]:
        st.session_state["tabela_selecionada"] = tabela_selecionada
        db_path = os.path.join(fonte_dados_dir, st.session_state["banco_selecionado"])
        st.session_state["dados_tabela"] = load_table_data(db_path, tabela_selecionada)

# Mostrar dados carregados
if st.session_state["dados_tabela"] is not None:
    st.write(f"### Dados da Tabela: {st.session_state['tabela_selecionada']}")
    st.dataframe(st.session_state["dados_tabela"])

# Filtros de Estado e Cidade
st.sidebar.write("---")
estado_selecionado = st.sidebar.selectbox("Estado", estados['nome'].sort_values())
cidades_estado = municipios[municipios['codigo_uf'] == estados[estados['nome'] == estado_selecionado]['codigo_uf'].values[0]]
cidade_selecionada = st.sidebar.selectbox("Cidade", cidades_estado['nome'].sort_values())
intervalo_tempo = st.sidebar.slider("Intervalo de Tempo (anos)", 2000, 2024, (2010, 2020))

# Mapa Interativo
estado_info = estados[estados['nome'] == estado_selecionado].iloc[0]
cidade_info = cidades_estado[cidades_estado['nome'] == cidade_selecionada].iloc[0]

mapa = px.scatter_mapbox(
    pd.DataFrame({
        'Nome': [estado_selecionado, cidade_selecionada],
        'Latitude': [estado_info['latitude'], cidade_info['latitude']],
        'Longitude': [estado_info['longitude'], cidade_info['longitude']],
        'Tipo': ['Estado', 'Cidade']
    }),
    lat="Latitude",
    lon="Longitude",
    text="Nome",
    zoom=6 if cidade_selecionada else 4,
    height=600
)

mapa.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})

# Layout principal com mapa
col1, col2 = st.columns([1, 3])
with col1:
    st.sidebar.markdown("### Selecione os parâmetros ao lado.")
with col2:
    st.plotly_chart(mapa, use_container_width=True)
