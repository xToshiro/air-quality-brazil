import os
import json
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime

# Initial Streamlit Configuration
st.set_page_config(
    page_title="Air Quality Brazil - Dashboard",
    layout="wide",
    page_icon="🌎",
)

# Custom green theme CSS
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
        /* Adjust color for success button when active */
        .stButton>button:active {
            background-color: #98FB98; /* Light green active */
            color: black;
        }
    </style>
    """,
    unsafe_allow_html=True
)


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

        # Display filtered results
        st.write("### Device Locations on the Map")
        device_locations = df_filtered[[device_id_col, "latitude", "longitude"]].dropna().drop_duplicates()
        map_chart = px.scatter_mapbox(
            device_locations,
            lat="latitude",
            lon="longitude",
            hover_name=device_id_col,
            color_discrete_sequence=["#006400"],
            size=[15] * len(device_locations),
            height=600
        )
        map_chart.update_layout(mapbox_style="open-street-map", mapbox_zoom=11)
        st.plotly_chart(map_chart, use_container_width=True)

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