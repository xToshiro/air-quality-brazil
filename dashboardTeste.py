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

# Intervalo de Tempo com Calendário e mapa interativo
if st.session_state["dados_tabela"] is not None:
    st.sidebar.write("### Intervalo de Tempo")
    df = st.session_state["dados_tabela"]

    if "date" in df.columns:
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        df = df.dropna(subset=['date'])
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()

        date_input = st.sidebar.date_input(
            "Selecione o Intervalo de Tempo:",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
            data_inicio, data_fim = date_input
            df = df[(df['date'] >= pd.Timestamp(data_inicio)) & (df['date'] <= pd.Timestamp(data_fim))]

    # Campo para Selecionar o Identificador do Dispositivo
    st.sidebar.write("### Coluna do Identificador do Dispositivo")
    col_id = st.sidebar.selectbox("Selecione a Coluna do Identificador", df.columns, index=df.columns.get_loc("moqa_id") if "moqa_id" in df.columns else 0)

    if col_id and "latitude" in df.columns and "longitude" in df.columns:
        # Capturar coordenadas únicas
        dispositivos = df[[col_id, "latitude", "longitude"]].dropna().drop_duplicates()

        # Calcular limites (bounding box)
        min_lat, max_lat = dispositivos['latitude'].min(), dispositivos['latitude'].max()
        min_lon, max_lon = dispositivos['longitude'].min(), dispositivos['longitude'].max()
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # Plotar dispositivos no mapa
        st.write("### Localização dos Dispositivos no Mapa")
        mapa = px.scatter_mapbox(
            dispositivos,
            lat="latitude",
            lon="longitude",
            hover_name=col_id,
            color_discrete_sequence=["#006400"],  # Verde escuro
            size=[15] * len(dispositivos),  # Tamanho fixo maior dos pontos
            height=600
        )
        mapa.update_layout(
            mapbox_style="open-street-map",
            mapbox_center={"lat": center_lat, "lon": center_lon},
            mapbox_zoom=11,  # Zoom ajustado para focar nos dispositivos
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )
        st.plotly_chart(mapa, use_container_width=True)

    else:
        st.sidebar.warning("Certifique-se de que a tabela contém 'latitude', 'longitude' e o identificador selecionado.")

    # Tabela filtrada
    st.write("### Dados Filtrados")
    st.dataframe(df)
else:
    st.sidebar.info("Carregue um banco e selecione uma tabela para visualizar os dados.")
