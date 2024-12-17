import os
import json
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime

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

# Inicializar Session State
if "dados_tabela" not in st.session_state:
    st.session_state["dados_tabela"] = None
if "tabela_selecionada" not in st.session_state:
    st.session_state["tabela_selecionada"] = None
if "banco_selecionado" not in st.session_state:
    st.session_state["banco_selecionado"] = None
if "tabelas_disponiveis" not in st.session_state:
    st.session_state["tabelas_disponiveis"] = []

# Sidebar - Configurações
st.sidebar.header("Configurações de Filtros")

# Fonte de Dados SQLite
st.sidebar.write("### Fonte de Dados (SQLite)")
fonte_dados_dir = "./data/air-quality-data/"
bancos_sqlite = list_sqlite_databases(fonte_dados_dir)

# Seleção de banco de dados
novo_banco = st.sidebar.selectbox("Selecione o Banco de Dados", bancos_sqlite, index=None, placeholder="Escolha um banco de dados...")

# Botão para carregar tabelas
if st.sidebar.button("Carregar Fonte de Dados") and novo_banco:
    db_path = os.path.join(fonte_dados_dir, novo_banco)
    st.session_state["tabelas_disponiveis"] = list_tables_in_sqlite(db_path)
    st.session_state["banco_selecionado"] = novo_banco
    st.session_state["dados_tabela"] = None
    st.session_state["tabela_selecionada"] = None
    st.sidebar.success(f"Banco de Dados '{novo_banco}' carregado com sucesso!")

# Seleção de Tabela
if st.session_state["banco_selecionado"]:
    tabela_selecionada = st.sidebar.selectbox(
        "Selecione a Tabela",
        st.session_state["tabelas_disponiveis"],
        index=None,
        placeholder="Escolha uma tabela...",
        key="tabela_selecionada_key"
    )

    if tabela_selecionada and tabela_selecionada != st.session_state["tabela_selecionada"]:
        st.session_state["tabela_selecionada"] = tabela_selecionada
        db_path = os.path.join(fonte_dados_dir, st.session_state["banco_selecionado"])
        st.session_state["dados_tabela"] = load_table_data(db_path, tabela_selecionada)

# Intervalo de Tempo com Calendário
if st.session_state["dados_tabela"] is not None:
    st.sidebar.write("### Intervalo de Tempo")
    df = st.session_state["dados_tabela"]

    if "date" in df.columns:
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        df = df.dropna(subset=['date'])
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()

        # Calendário de seleção
        date_input = st.sidebar.date_input(
            "Selecione o Intervalo de Tempo:",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )

        # Verifica se o intervalo foi selecionado corretamente
        if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
            data_inicio, data_fim = date_input
            dados_filtrados = df[(df['date'] >= pd.Timestamp(data_inicio)) & (df['date'] <= pd.Timestamp(data_fim))]
            st.write(f"### Dados Filtrados de {data_inicio} a {data_fim}")
            st.dataframe(dados_filtrados)
        else:
            st.sidebar.info("Selecione um intervalo de datas (início e fim).")
    else:
        st.sidebar.warning("A tabela selecionada não contém o campo 'date'.")

# Filtros de Estado e Cidade
st.sidebar.write("---")
estado_selecionado = st.sidebar.selectbox("Estado", estados['nome'].sort_values())
cidades_estado = municipios[municipios['codigo_uf'] == estados[estados['nome'] == estado_selecionado]['codigo_uf'].values[0]]
cidade_selecionada = st.sidebar.selectbox("Cidade", cidades_estado['nome'].sort_values())

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
