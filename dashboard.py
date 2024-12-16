import json
import pandas as pd
import geopandas as gpd
import plotly.express as px
import streamlit as st

# Configuração inicial do Streamlit
st.set_page_config(page_title="Qualidade do Ar no Brasil", layout="wide")

# Função para carregar dados
@st.cache_data
def load_data():
    # Carrega os dados dos arquivos JSON usando utf-8-sig para lidar com BOM
    with open('./data/estados.json', 'r', encoding='utf-8-sig') as f:
        estados = pd.DataFrame(json.load(f))
    with open('./data/municipios.json', 'r', encoding='utf-8-sig') as f:
        municipios = pd.DataFrame(json.load(f))
    return estados, municipios


# Carregar os dados
estados, municipios = load_data()

# Sidebar: Configurações do filtro
st.sidebar.header("Configurações de Filtros")
fonte_dados = st.sidebar.selectbox("Fonte de Dados", ["Fonte 1", "Fonte 2"])
estado_selecionado = st.sidebar.selectbox("Estado", estados['nome'].sort_values())
cidades_estado = municipios[municipios['codigo_uf'] == estados[estados['nome'] == estado_selecionado]['codigo_uf'].values[0]]
cidade_selecionada = st.sidebar.selectbox("Cidade", cidades_estado['nome'].sort_values())
intervalo_tempo = st.sidebar.slider("Intervalo de Tempo (anos)", 2000, 2024, (2010, 2020))

# Mapa interativo
st.sidebar.write("---")
st.sidebar.write("**Mapa Interativo**")

# Dados do estado e cidade selecionados
estado_info = estados[estados['nome'] == estado_selecionado].iloc[0]
cidade_info = cidades_estado[cidades_estado['nome'] == cidade_selecionada].iloc[0]

# Criar mapa com Plotly
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

# Layout principal
col1, col2 = st.columns([1, 3])

with col1:
    st.sidebar.markdown("### Selecione os parâmetros ao lado.")
    
with col2:
    st.plotly_chart(mapa, use_container_width=True)
