import streamlit as st
import pandas as pd
from utils.data_loader import BigQueryDataLoader
from utils.data_cleaner import DataCleaner
from utils.persona_generator import PersonaGenerator

st.set_page_config(page_title="Persona Filter", layout="centered")
st.title("🚴‍♂️ Persona Filter for Bike Data")

st.write("Click the button below to pull the first rows from the London bicycle dataset in BigQuery, add a persona column, and filter by persona.")

if 'df' not in st.session_state:
    st.session_state.df = None

if st.button("Pull Data and Add Persona", type="primary"):
    with st.spinner("Connecting to BigQuery and loading data..."):
        try:
            data_loader = BigQueryDataLoader()
            df = data_loader.load_bike_data(limit=5000)
            if df is None or df.empty:
                st.error("Loaded data is empty. Please check your data source or credentials.")
                st.session_state.df = None
            else:
                df = DataCleaner.clean_bike_data(df)
                df = PersonaGenerator.add_persona_column(df)
                st.session_state.df = df
                st.success("Successfully loaded data and added persona column!")
        except Exception as e:
            st.error(f"Error loading data from BigQuery: {e}")
            import traceback
            st.code(traceback.format_exc(), language="python")

if st.session_state.df is not None:
    persona_options = ["ALL"]
    if "persona" in st.session_state.df.columns:
        persona_options += sorted(st.session_state.df["persona"].dropna().unique())
    selected_persona = st.selectbox("Select Persona to Filter", persona_options)
    if selected_persona == "ALL":
        filtered_df = st.session_state.df
    else:
        filtered_df = st.session_state.df[st.session_state.df["persona"] == selected_persona]
    st.dataframe(filtered_df.head(20)) 