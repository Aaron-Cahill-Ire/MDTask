import streamlit as st
import pandas as pd
from utils.data_loader import BigQueryDataLoader
from utils.data_cleaner import DataCleaner
from utils.persona_generator import PersonaGenerator
from utils.persona_marketing_stats import compute_marketing_stats
from utils.consumer_type_analyzer import ConsumerTypeAnalyzer
from utils.visualisations import create_prescriptive_map, create_seasonal_trends_chart
from streamlit_folium import st_folium
import traceback

# --- Page Configuration ---
st.set_page_config(page_title="Persona Marketing Stats", layout="wide")

# --- Sidebar for Configuration ---
st.sidebar.title("⚙️ Configuration")
persona_method = st.sidebar.radio(
    "Choose Persona Generation Method",
    ("Rule-Based (Simple)", "K-Means Clustering (Advanced)"),
    help="""
    - **Rule-Based:** Uses simple, hand-coded rules to assign personas.
    - **K-Means Clustering:** Uses machine learning to find natural groups in the data.
    """
)

# --- Main Page Content ---
st.title("💡 Prescriptive Marketing Insights for Bike Data")
st.write("""
This dashboard analyzes bike rental data to provide **prescriptive insights** for offline advertising campaigns. 
Select a persona generation method in the sidebar, then load the data to see tailored recommendations.
""")

# --- Session State Initialization ---
if 'df' not in st.session_state:
    st.session_state.df = None
if 'last_method' not in st.session_state:
    st.session_state.last_method = None

# --- Data Loading and Processing ---
# Invalidate data if the method changes, prompting the user to reload
if st.session_state.last_method != persona_method:
    st.session_state.df = None
    st.info(f"Method changed to **{persona_method}**. Please click the button below to load and generate new insights.")

if st.button("Load Data and Generate Insights", type="primary"):
    with st.spinner(f"Connecting to BigQuery, cleaning data, and generating personas using **{persona_method}**..."):
        try:
            data_loader = BigQueryDataLoader()
            df = data_loader.load_bike_data(limit=50000)
            if df is None or df.empty:
                st.error("Loaded data is empty. Please check your data source or credentials.")
                st.session_state.df = None
            else:
                df = DataCleaner.clean_bike_data(df)

                # Conditional Persona Generation based on sidebar selection
                if persona_method == "Rule-Based (Simple)":
                    df = PersonaGenerator.add_persona_column(df)
                else: # K-Means Clustering
                    if 'start_date' in df.columns:
                        df['hour'] = pd.to_datetime(df['start_date']).dt.hour
                        df['is_weekend'] = (pd.to_datetime(df['start_date']).dt.weekday >= 5).astype(int)
                        df['is_weekday'] = (pd.to_datetime(df['start_date']).dt.weekday < 5).astype(int)
                    if 'duration_minutes' not in df.columns and 'duration' in df.columns:
                        df['duration_minutes'] = df['duration'] / 60
                    df = PersonaGenerator.add_persona_column(df, use_clustering=True)

                st.session_state.df = df
                st.session_state.last_method = persona_method
                st.success(f"Successfully loaded data and generated insights using {persona_method}!")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.code(traceback.format_exc(), language="python")

# --- Main Display Logic ---
if st.session_state.df is not None:
    df_for_analysis = st.session_state.df

    persona_options = ["ALL"]
    if "persona" in df_for_analysis.columns:
        persona_options += sorted(df_for_analysis["persona"].dropna().unique())
    
    selected_persona = st.selectbox(
        "**Select a Persona to Analyze**",
        persona_options,
        help="Choose a persona to see specific statistics and recommendations."
    )

    stats = compute_marketing_stats(df_for_analysis, selected_persona)
    
    if "error" in stats:
        st.warning(stats["error"])
    else:
        st.header(f"Campaign Strategy for Persona: {selected_persona}")

        # --- PRESCRIPTIVE INSIGHTS SECTION ---
        st.markdown("---")
        st.subheader("✅ Actionable Recommendations Map")
        st.info("This map shows the most valuable places to advertise for the selected persona. Use the layer control in the top right to toggle views.")

        # Create and display the prescriptive map with all required data
        prescriptive_map = create_prescriptive_map(
            corridors_data=stats.get("top_travel_corridors_with_coords"),
            top_start_stations_data=stats.get("top_start_stations_with_coords"),
            top_end_stations_data=stats.get("top_end_stations_with_coords"),
            persona_stations_data=stats.get("persona_stations_with_coords")
        )
        st_folium(prescriptive_map, width='100%', height=500)

        with st.expander("Reveal Insights Data"):
            prescriptive_col1, prescriptive_col2 = st.columns(2)
            with prescriptive_col1:
                st.markdown("**🎯 Top Travel Corridors**")
                if stats.get("top_travel_corridors"):
                    corridor_df = pd.DataFrame(list(stats["top_travel_corridors"].items()), columns=["Route", "Total Trips"])
                    st.table(corridor_df)
                else:
                    st.write("No specific corridor data available.")

            with prescriptive_col2:
                st.markdown("**High Concentration Stations**")
                if stats.get("opportunity_stations"):
                    opportunity_df = pd.DataFrame.from_dict(stats["opportunity_stations"], orient='index')
                    st.table(opportunity_df)
                else:
                    st.write("Not applicable for 'ALL' persona or no unique opportunities found.")

        # --- DESCRIPTIVE STATISTICS SECTION ---
        st.markdown("---")
        st.subheader("📊 Supporting Data")
        
        st.markdown("**Trip Duration (minutes):**")
        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric(label="Mean Duration", value=stats.get("trip_duration_mean_min", "N/A"))
        metric2.metric(label="Median Duration", value=stats.get("trip_duration_median_min", "N/A"))
        metric3.metric(label="25th Percentile", value=stats.get("trip_duration_25th_min", "N/A"))
        metric4.metric(label="75th Percentile", value=stats.get("trip_duration_75th_min", "N/A"))
        
        desc_col1, desc_col2 = st.columns(2)
        with desc_col1:
            st.markdown("**Trips by Hour of Day**")
            st.bar_chart(pd.Series(stats.get("trips_by_hour", {})))
            st.markdown("**Top 5 Start Stations**")
            top_start_df = pd.DataFrame(list(stats.get("top_start_stations", {}).items()), columns=["Station", "Trips"])
            st.table(top_start_df)

        with desc_col2:
            st.markdown("**Trips by Day of Week**")
            st.bar_chart(pd.Series(stats.get("trips_by_day_of_week", {})))
            st.markdown("**Top 5 End Stations**")
            top_end_df = pd.DataFrame(list(stats.get("top_end_stations", {}).items()), columns=["Station", "Trips"])
            st.table(top_end_df)
        
        # --- SEASONAL ANALYSIS SECTION ---
        st.markdown("---")
        st.subheader("🌤️ Seasonal Usage Patterns")
        st.info(f"This chart shows how {selected_persona} usage varies throughout the year, helping identify the best months for seasonal marketing campaigns.")
        
        if stats.get("monthly_usage_percentages"):
            seasonal_chart = create_seasonal_trends_chart(stats["monthly_usage_percentages"])
            st.plotly_chart(seasonal_chart, use_container_width=True)
            
            # Add seasonal insights
            monthly_data = stats["monthly_usage_percentages"]
            peak_month_idx = monthly_data.index(max(monthly_data)) if monthly_data else 0
            low_month_idx = monthly_data.index(min(monthly_data)) if monthly_data else 0
            
            month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
            
            seasonal_col1, seasonal_col2, seasonal_col3 = st.columns(3)
            with seasonal_col1:
                st.metric("Peak Month", month_names[peak_month_idx], f"{max(monthly_data):.1f}% of trips")
            with seasonal_col2:
                st.metric("Lowest Month", month_names[low_month_idx], f"{min(monthly_data):.1f}% of trips")
            with seasonal_col3:
                seasonal_variance = max(monthly_data) - min(monthly_data) if monthly_data else 0
                st.metric("Seasonal Variance", f"{seasonal_variance:.1f}%", "Peak to Low difference")
        else:
            st.warning("No seasonal data available for this persona.")

        # --- CONSUMER TYPE ANALYSIS SECTION ---
        st.markdown("---")
        st.subheader("👥 Brand Recommendations")
        st.info(f"This section shows recommended brands that align with the {selected_persona} persona for potential partnerships and marketing opportunities.")
        
        # Get brand recommendations for the selected persona
        brand_recommendations = ConsumerTypeAnalyzer.get_brand_recommendations(selected_persona)
        
        if not brand_recommendations:
            st.warning(f"No brand recommendations found for persona: {selected_persona}")
        else:
            # Display brand recommendations in a clean format
            st.markdown("**🏷️ Recommended Brands for Partnerships**")
            
            # Create columns for better layout
            num_brands = len(brand_recommendations)
            if num_brands <= 6:
                cols = st.columns(2)
                for i, brand in enumerate(brand_recommendations):
                    col_idx = i % 2
                    with cols[col_idx]:
                        st.markdown(f"• **{brand}**")
            else:
                cols = st.columns(3)
                for i, brand in enumerate(brand_recommendations):
                    col_idx = i % 3
                    with cols[col_idx]:
                        st.markdown(f"• **{brand}**")
            
            # Add insights about the brand selection
            st.markdown("---")
            st.subheader("💡 Partnership Strategy")
            
            strategy_col1, strategy_col2 = st.columns(2)
            
            with strategy_col1:
                st.markdown("**🎯 Targeting Approach**")
                if selected_persona == "Morning Commuter":
                    st.markdown("Focus on brands that serve busy professionals during morning hours - coffee, fitness, and transit-related services.")
                elif selected_persona == "Evening Commuter":
                    st.markdown("Target entertainment, food delivery, and social media brands that align with evening lifestyle.")
                elif selected_persona == "Weekend Explorer":
                    st.markdown("Partner with experience-focused brands, social platforms, and local businesses for weekend activities.")
                elif selected_persona == "Fitness":
                    st.markdown("Collaborate with fitness brands, health apps, and wellness-focused companies.")
                elif selected_persona == "Tourist/Long Leisure":
                    st.markdown("Work with tourism brands, cultural institutions, and travel-related services.")
                else:
                    st.markdown("Multi-segment approach targeting universal brands and community-focused platforms.")
            
            with strategy_col2:
                st.markdown("**📈 Expected Benefits**")
                st.markdown("• **Increased brand visibility** through targeted partnerships")
                st.markdown("• **Enhanced user experience** with relevant brand integrations")
                st.markdown("• **Revenue opportunities** from partnership agreements")
                st.markdown("• **Market expansion** into new consumer segments")