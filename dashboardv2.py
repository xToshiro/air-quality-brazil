import os
import json
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime
from PIL import Image
import base64
from scipy.interpolate import griddata
import numpy as np

# Initial Streamlit Configuration
st.set_page_config(
    page_title="Air Quality Brazil - Dashboard",
    layout="wide",
    page_icon="🌎",
)

# Custom CSS for sidebar styling
st.markdown(
    """
    <style>
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #196a19; /* Dark green sidebar */
        }
        /* Title and headers styling */
        h1, h2, h3, h4 {
            color: #006400; /* Dark green headers */
        }
        /* General background color */
        .css-18e3th9 {
            background-color: #f8fff8;
        }
        /* Button styling */
        .stButton>button {
            background-color: #228B22; /* Forest green */
            color: white;
            border-radius: 10px;
        }
        .stButton>button:hover {
            background-color: #006400; /* Dark green hover */
        }
        /* Logo container styling */
        .logo-container {
            background-color: #e0e0e0; /* Light gray background */
            border-radius: 15px; /* Rounded corners */
            padding: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .logo-container img {
            width: 100%; /* Responsive width */
            max-width: 300px; /* Max width for the logo */
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Helper function to convert an image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Load and display the logo in a styled container
logo_path = "./images/logo_footer.png"
if os.path.exists(logo_path):
    logo_base64 = image_to_base64(logo_path)
    logo_html = f"""
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}" alt="TRAMA Logo">
    </div>
    """
    st.sidebar.markdown(logo_html, unsafe_allow_html=True)
else:
    st.sidebar.error("Logo not found. Please check the path and file name.")
    
# Function to load JSON data
@st.cache_data
def load_json_data():
    with open('./data/estados.json', 'r', encoding='utf-8-sig') as f:
        states = pd.DataFrame(json.load(f))
    with open('./data/municipios.json', 'r', encoding='utf-8-sig') as f:
        cities = pd.DataFrame(json.load(f))
    return states, cities

# Function to list SQLite databases in a directory
def list_sqlite_databases(path):
    return [f for f in os.listdir(path) if f.endswith('.sqlite')]

# Function to list tables within a SQLite database
def list_tables_in_sqlite(db_path):
    with sqlite3.connect(db_path) as conn:
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(query, conn)
    return tables['name'].tolist()

# Function to load data from a specific table
def load_table_data(db_path, table_name):
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df

# Load JSON data
states, cities = load_json_data()

# Initialize session state for managing selections
if "loaded_data" not in st.session_state:
    st.session_state["loaded_data"] = None
if "selected_table" not in st.session_state:
    st.session_state["selected_table"] = None
if "selected_database" not in st.session_state:
    st.session_state["selected_database"] = None
if "available_tables" not in st.session_state:
    st.session_state["available_tables"] = []

# Sidebar filters
st.sidebar.header("Data Configuration")

# SQLite Data Source
st.sidebar.subheader("Data Source (SQLite)")
data_directory = "./data/air-quality-data/"
sqlite_databases = list_sqlite_databases(data_directory)

# Dropdown to select database
new_database = st.sidebar.selectbox("Select a Database", sqlite_databases, index=None, placeholder="Choose a database...")

# Button to load tables
if st.sidebar.button("Load Data Source") and new_database:
    db_path = os.path.join(data_directory, new_database)
    st.session_state["available_tables"] = list_tables_in_sqlite(db_path)
    st.session_state["selected_database"] = new_database
    st.session_state["loaded_data"] = None
    st.session_state["selected_table"] = None
    st.sidebar.success(f"Database '{new_database}' loaded successfully!")

# Table selection
if st.session_state["selected_database"]:
    selected_table = st.sidebar.selectbox(
        "Select a Table",
        st.session_state["available_tables"],
        index=None,
        placeholder="Choose a table..."
    )

    if selected_table and selected_table != st.session_state["selected_table"]:
        st.session_state["selected_table"] = selected_table
        db_path = os.path.join(data_directory, st.session_state["selected_database"])
        st.session_state["loaded_data"] = load_table_data(db_path, selected_table)

# Main content
if st.session_state["loaded_data"] is not None:
    df = st.session_state["loaded_data"]

    # Sidebar filter for time range
    st.sidebar.subheader("Filter by Time Range")
    if "date" in df.columns:
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        df = df.dropna(subset=['date'])

        min_date = df['date'].min().date()
        max_date = df['date'].max().date()

        date_input = st.sidebar.date_input(
            "Select Date Range:",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
            start_date, end_date = date_input
            df = df[(df['date'] >= pd.Timestamp(start_date)) & (df['date'] <= pd.Timestamp(end_date))]

    # Device ID filter
    st.sidebar.subheader("Device Filters")
    device_id_col = st.sidebar.selectbox("Device Identifier Column", df.columns)
    unique_devices = df[device_id_col].dropna().unique()
    selected_devices = st.sidebar.multiselect("Select Devices", unique_devices, default=unique_devices)

    # Column selection for measurements
    hour_col = st.sidebar.selectbox("Hour Column", df.columns, index=None)
    temp_col = st.sidebar.selectbox("Temperature Column", df.columns, index=None)
    humidity_col = st.sidebar.selectbox("Humidity Column", df.columns, index=None)
    pm_col = st.sidebar.selectbox("Particulate Matter Column", df.columns, index=None)

       # Apply data filtering and validation
    if temp_col and humidity_col and pm_col:
        # Combine date and hour into a single datetime column
        if hour_col:
            df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df[hour_col].astype(str), errors='coerce')
        else:
            df['datetime'] = df['date']
        df = df.dropna(subset=['datetime'])

        # Filter by selected devices
        df = df[df[device_id_col].isin(selected_devices)]

        # Sidebar sliders for temperature, humidity, and particulate matter
        st.sidebar.subheader("Measurement Filters")
        temp_min, temp_max = df[temp_col].min(), df[temp_col].max()
        temp_range = st.sidebar.slider("Temperature (°C)", float(temp_min - 5), float(temp_max + 5), (float(temp_min), float(temp_max)))

        humid_min, humid_max = df[humidity_col].min(), df[humidity_col].max()
        humidity_range = st.sidebar.slider("Relative Humidity (%)", float(humid_min - 5), float(humid_max + 5), (float(humid_min), float(humid_max)))

        pm_min, pm_max = df[pm_col].min(), df[pm_col].max()
        pm_range = st.sidebar.slider("Particulate Matter (µg/m³)", float(pm_min - 5), float(pm_max + 5), (float(pm_min), float(pm_max)))

        # Apply measurement filters
        df_filtered = df[
            (df[temp_col].between(temp_range[0], temp_range[1])) &
            (df[humidity_col].between(humidity_range[0], humidity_range[1])) &
            (df[pm_col].between(pm_range[0], pm_range[1]))
        ]

       # Calculate stats for each device
        stats = (
            df_filtered.groupby(device_id_col)
            .agg(
                temp_min=(temp_col, "min"),
                temp_max=(temp_col, "max"),
                temp_mean=(temp_col, lambda x: round(x.mean(), 2)),
                temp_min_time=("datetime", lambda x: df_filtered.loc[x.idxmin(), "datetime"]),
                temp_max_time=("datetime", lambda x: df_filtered.loc[x.idxmax(), "datetime"]),
                humid_min=(humidity_col, "min"),
                humid_max=(humidity_col, "max"),
                humid_mean=(humidity_col, lambda x: round(x.mean(), 2)),
                humid_min_time=("datetime", lambda x: df_filtered.loc[x.idxmin(), "datetime"]),
                humid_max_time=("datetime", lambda x: df_filtered.loc[x.idxmax(), "datetime"]),
                pm_min=(pm_col, "min"),
                pm_max=(pm_col, "max"),
                pm_mean=(pm_col, lambda x: round(x.mean(), 2)),
                pm_min_time=("datetime", lambda x: df_filtered.loc[x.idxmin(), "datetime"]),
                pm_max_time=("datetime", lambda x: df_filtered.loc[x.idxmax(), "datetime"]),
                latitude=("latitude", "first"),
                longitude=("longitude", "first"),
            )
            .reset_index()
        )

        # Prepare hover data for the map
        stats["hover_info"] = stats.apply(
            lambda row: (
                f"Device: {row[device_id_col]}<br>"
                f"Temperature: Min {row['temp_min']:.2f}°C at {row['temp_min_time']}<br>"
                f"Temperature: Max {row['temp_max']:.2f}°C at {row['temp_max_time']}<br>"
                f"Temperature: Mean {row['temp_mean']:.2f}°C<br>"
                f"Humidity: Min {row['humid_min']:.2f}% at {row['humid_min_time']}<br>"
                f"Humidity: Max {row['humid_max']:.2f}% at {row['humid_max_time']}<br>"
                f"Humidity: Mean {row['humid_mean']:.2f}%<br>"
                f"Particulate Matter: Min {row['pm_min']:.2f} µg/m³ at {row['pm_min_time']}<br>"
                f"Particulate Matter: Max {row['pm_max']:.2f} µg/m³ at {row['pm_max_time']}<br>"
                f"Particulate Matter: Mean {row['pm_mean']:.2f} µg/m³"
            ),
            axis=1,
        )

        # Display map with hover data
        st.write("### Device Locations with Measurements")
        map_chart = px.scatter_mapbox(
            stats,
            lat="latitude",
            lon="longitude",
            hover_name="hover_info",
            color_discrete_sequence=["#006400"],
            size=[15] * len(stats),
            height=600
        )

        # Update layout to increase font size in hover boxes
        map_chart.update_layout(
            mapbox_style="open-street-map",
            mapbox_zoom=11,
            hoverlabel=dict(
                font_size=14,  # Set the font size for hover text
                font_family="Arial"  # Optionally, set a font family
            )
        )
        
        st.plotly_chart(map_chart, use_container_width=True)

        # More visuaisations
        st.sidebar.subheader("More Charts")

        # Switch para habilitar ou desabilitar o mapa de calor
        heatmap_enabled = st.sidebar.checkbox("Enable Heatmap Visualization")

        if heatmap_enabled:
            # Campo para selecionar a variável
            heatmap_variable = st.sidebar.selectbox(
                "Select Variable for Heatmap",
                ["Temperature", "Humidity", "Particulate Matter"],
                index=0  # Pré-selecionado como "Temperature"
            )
            
            # Campo para selecionar a estatística
            heatmap_stat = st.sidebar.radio(
                "Select Statistic",
                ["Min", "Max", "Mean"],
                index=1  # Pré-selecionado como "Max"
            )
            
            # Slider para ajustar o raio do mapa de calor
            heatmap_radius = st.sidebar.slider(
                "Adjust Heatmap Radius",
                min_value=1,  # Valor mínimo do raio
                max_value=100,  # Valor máximo do raio
                value=20,  # Valor padrão
                step=1  # Incremento
            )
            
            # Slider para ajustar a transparência do mapa de calor
            heatmap_opacity = st.sidebar.slider(
                "Adjust Heatmap Transparency",
                min_value=0.1,  # Transparência mínima
                max_value=1.0,  # Opacidade máxima
                value=0.8,  # Valor padrão
                step=0.1  # Incremento
            )
            
            # Mapeando a variável para a coluna correspondente no DataFrame
            variable_map = {
                "Temperature": temp_col,
                "Humidity": humidity_col,
                "Particulate Matter": pm_col
            }
            
            selected_column = variable_map[heatmap_variable]
            
            # Ajustando o DataFrame com base na estatística selecionada
            stat_map = {
                "Min": "min",
                "Max": "max",
                "Mean": lambda x: round(x.mean(), 2)
            }
            
            # Capturando valores únicos de cada dispositivo
            unique_device_data = (
                df_filtered.groupby([device_id_col, "latitude", "longitude"])
                .agg({selected_column: stat_map[heatmap_stat]})
                .reset_index()
                .rename(columns={selected_column: "value"})
            )
            
            # Normalizando os valores para comparação visual
            unique_device_data["normalized_value"] = (
                (unique_device_data["value"] - unique_device_data["value"].min()) /
                (unique_device_data["value"].max() - unique_device_data["value"].min())
            )

            # Verificar se existem dados suficientes para o mapa de calor
            if unique_device_data.empty:
                st.warning("No data available for the selected configuration.")
            else:
                st.write(f"### Heatmap for {heatmap_stat} {heatmap_variable}")
                
                # Configurando o mapa de calor com comparação de valores únicos
                heatmap_chart = px.density_mapbox(
                    unique_device_data,
                    lat="latitude",
                    lon="longitude",
                    z="value",  # Usar valores reais para densidade
                    radius=heatmap_radius,  # Usar valor ajustável pelo slider
                    center=dict(lat=unique_device_data["latitude"].mean(), lon=unique_device_data["longitude"].mean()),
                    mapbox_style="open-street-map",
                    color_continuous_scale="Inferno",  # Escala de cores para valores quentes
                    title=f"{heatmap_stat} {heatmap_variable} Heatmap",
                )
                
                # Aplicar a transparência ao heatmap
                heatmap_chart.update_traces(opacity=heatmap_opacity)
                
                # Atualizando configurações do layout do mapa de calor
                heatmap_chart.update_layout(
                    mapbox_zoom=10,  # Ajustando o zoom padrão
                    coloraxis_colorbar=dict(
                        title=f"{heatmap_variable} ({heatmap_stat})",
                        titleside="right"
                    )
                )
                
                # Exibir o heatmap no Streamlit
                st.plotly_chart(heatmap_chart, use_container_width=True)
                
        # Scatter Plot Visualization
        if st.sidebar.checkbox("Enable Scatter Plot"):
            st.sidebar.subheader("Scatter Plot Configuration")
            
            # Dropdowns to select x and y variables
            x_variable = st.sidebar.selectbox("Select X Variable", df_filtered.columns)
            y_variable = st.sidebar.selectbox("Select Y Variable", df_filtered.columns)
            
            # Select color grouping
            color_group = st.sidebar.selectbox("Group by Color", [None] + list(df_filtered.columns), index=0)
            
            # Display scatter plot
            st.write("### Scatter Plot")
            scatter_fig = px.scatter(
                df_filtered,
                x=x_variable,
                y=y_variable,
                color=color_group,
                title=f"Scatter Plot: {x_variable} vs {y_variable}",
                labels={x_variable: x_variable, y_variable: y_variable},
                template="plotly_white"
            )
            st.plotly_chart(scatter_fig, use_container_width=True)

        # Correlation Matrix Heatmap with Dynamic Sizing
        if st.sidebar.checkbox("Enable Correlation Heatmap"):
            st.sidebar.subheader("Correlation Matrix Configuration")
            
            # Allow user to select columns for the correlation matrix
            numeric_columns = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            selected_columns = st.sidebar.multiselect(
                "Select Columns for Correlation Matrix",
                numeric_columns,
                default=numeric_columns  # Pre-select all numeric columns by default
            )
            
            if selected_columns:
                # Compute correlation matrix only for selected columns
                correlation_matrix = df_filtered[selected_columns].corr()
                
                # Dynamically set figure size based on the number of variables
                num_vars = len(selected_columns)
                fig_width = 400 + (num_vars * 40)  # Base width plus additional per variable
                fig_height = 400 + (num_vars * 40)  # Base height plus additional per variable
                
                # Display correlation matrix heatmap
                st.write("### Correlation Matrix Heatmap")
                correlation_fig = px.imshow(
                    correlation_matrix,
                    text_auto=True,
                    color_continuous_scale="RdBu_r",
                    title="Correlation Matrix",
                    labels=dict(color="Correlation"),
                )
                
                # Update layout to adjust figure size dynamically
                correlation_fig.update_layout(
                    autosize=False,
                    width=fig_width,
                    height=fig_height,
                    margin=dict(l=10, r=10, t=40, b=10)  # Reduce margins for better fit
                )
                
                st.plotly_chart(correlation_fig, use_container_width=False)  # Disable container width for custom sizing
            else:
                st.warning("Please select at least one column to compute the correlation matrix.")
                
        
        # Advanced Statistical Summary with Side-by-Side Boxplots
        if st.sidebar.checkbox("Enable Statistical Summary"):
            st.sidebar.subheader("Statistical Summary Configuration")
            
            # Allow user to select columns for statistical analysis
            numeric_columns = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            selected_stats_columns = st.sidebar.multiselect(
                "Select Columns for Statistical Summary",
                numeric_columns,
                default=numeric_columns  # Pre-select all numeric columns by default
            )
            
            if selected_stats_columns:
                # Compute descriptive statistics for selected columns
                stats_summary = df_filtered[selected_stats_columns].describe().transpose()
                st.write("### Statistical Summary")
                st.dataframe(stats_summary)
                
                # Generate side-by-side boxplots
                st.write("### Boxplots for Selected Variables")
                from plotly.subplots import make_subplots
                import plotly.graph_objects as go

                # Create a subplot for boxplots
                fig = make_subplots(rows=1, cols=len(selected_stats_columns), shared_yaxes=True)

                for idx, variable in enumerate(selected_stats_columns, start=1):
                    fig.add_trace(
                        go.Box(
                            y=df_filtered[variable],
                            name=variable,
                            boxmean=True  # Show mean on the boxplot
                        ),
                        row=1, col=idx
                    )
                
                # Update layout for better display
                fig.update_layout(
                    title="Boxplots for Selected Variables",
                    template="plotly_white",
                    showlegend=False,
                    height=500,
                    width=300 * len(selected_stats_columns),  # Adjust width dynamically
                    margin=dict(l=40, r=40, t=40, b=40)
                )
                
                # Display the combined boxplots
                st.plotly_chart(fig, use_container_width=False)
            else:
                st.warning("Please select at least one column for the statistical summary and boxplots.")

        # Temperature line chart
        st.write("### Temperature Over Time")
        st.plotly_chart(
            px.line(df_filtered, x='datetime', y=temp_col, color=device_id_col, title="Temperature Over Time")
        )

        # Humidity line chart
        st.write("### Relative Humidity")
        st.plotly_chart(
            px.line(df_filtered, x='datetime', y=humidity_col, color=device_id_col, title="Relative Humidity (%)")
        )

        # Particulate Matter chart
        st.write("### Particulate Matter Levels")
        st.plotly_chart(
            px.line(df_filtered, x='datetime', y=pm_col, color=device_id_col, title="Particulate Matter (µg/m³)")
        )

        # Display the filtered data in a table
        st.write("### Filtered Data Table")
        st.dataframe(df_filtered)

    else:
        st.sidebar.warning("Please select all required columns (Temperature, Humidity, and Particulate Matter).")

else:
    st.info("Please load a database and select a table to begin.")

# About Section (in a hidden expander)
with st.expander("About the Project"):
    st.markdown("""
    **Laboratory of Transport and Environment (TRAMA)**  
    Department of Transport Engineering (DET)  
    Federal University of Ceará (UFC)  

    **Developer:** Jairo Ivo Castro Brito  
    [GitHub Repository](https://github.com/xToshiro/)
    """)