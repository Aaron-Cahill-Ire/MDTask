import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import AntPath

def _get_top_20_percent_threshold(station_data, count_key='count'):
    """
    Helper function to calculate the threshold for top 20% of stations.
    
    Args:
        station_data: List of station dictionaries with usage counts
        count_key: Key name for the count field (default: 'count')
    
    Returns:
        float: The threshold value - stations with counts >= this value are in top 20%
    """
    if not station_data:
        return 0
    
    # Extract counts and sort in descending order
    counts = [station.get(count_key, 0) for station in station_data]
    counts.sort(reverse=True)
    
    # Calculate the index for top 20%
    # Ensure index is at least 0 and within bounds
    top_20_index = min(len(counts) - 1, int(len(counts) * 0.2))
    
    # Return the threshold value (minimum count to be in top 20%)
    return counts[top_20_index] if top_20_index >= 0 else 0

def create_prescriptive_map(corridors_data, top_start_stations_data=None, top_end_stations_data=None, persona_stations_data=None):
    """
    Creates a professional, interactive Folium map to visualize prescriptive insights.
    - Shows Top Start Stations (green pins) and Top End Stations (red pins) for a persona.
    - Shows the Top 20% of all stations used by a persona (blue dots).
    - Shows Popular Corridors with animated lines indicating direction.
    - Shows Round Trip Hotspots (purple pins).
    """
    london_center = [51.5074, -0.1278]
    m = folium.Map(location=london_center, zoom_start=12, tiles='CartoDB positron')

    # --- Layer Groups ---
    start_pin_group = folium.FeatureGroup(name='🟢 Top Start Stations', show=True).add_to(m)
    end_pin_group = folium.FeatureGroup(name='🔴 Top End Stations', show=True).add_to(m)
    corridor_group = folium.FeatureGroup(name='➡️ Popular Corridors (A → B)', show=True).add_to(m)
    round_trip_group = folium.FeatureGroup(name='🔄 Round Trip Hotspots', show=True).add_to(m)
    
    # --- Layer: Persona Station Footprint (Top 20% Blue Dots) ---
    if persona_stations_data:
        # Determine the count key based on available data structure
        sample_station = persona_stations_data[0] if persona_stations_data else {}
        count_key = 'count' if 'count' in sample_station else 'usage' if 'usage' in sample_station else 'usage_count'
        
        top_20_threshold = _get_top_20_percent_threshold(persona_stations_data, count_key)
        
        persona_footprint_group = folium.FeatureGroup(name='🔵 Persona Station Footprint (Top 20%)', show=True).add_to(m)
        for station in persona_stations_data:
            # Only show stations in the top 20% of usage for this persona
            station_count = station.get(count_key, 0)
            if 'lat' in station and 'lon' in station and station_count >= top_20_threshold:
                folium.CircleMarker(
                    location=[station['lat'], station['lon']],
                    radius=3, color='#3186cc', fill=True, fill_color='#3186cc', fill_opacity=0.7,
                    tooltip=f"Station: {station.get('name', 'Unknown')} ({station_count} trips)"
                ).add_to(persona_footprint_group)

    # --- Layer: Top Start/End Station Pins ---
    if top_start_stations_data:
        for station in top_start_stations_data:
            popup_html = f"""<div style="font-family: Arial, sans-serif; font-size: 14px;"><h4 style="margin:0 0 5px 0; color:#2ECC71;">🟢 Top Start Station</h4><b>Station:</b> {station['name']}<br><b>Total Starts:</b> {station['count']}</div>"""
            folium.Marker(location=[station['lat'], station['lon']], popup=folium.Popup(popup_html, max_width=300), tooltip=f"Top Start: {station['name']} ({station['count']} trips)", icon=folium.Icon(color='green', icon='arrow-up', prefix='fa')).add_to(start_pin_group)
            
    if top_end_stations_data:
        for station in top_end_stations_data:
            popup_html = f"""<div style="font-family: Arial, sans-serif; font-size: 14px;"><h4 style="margin:0 0 5px 0; color:#E74C3C;">🔴 Top End Station</h4><b>Station:</b> {station['name']}<br><b>Total Ends:</b> {station['count']}</div>"""
            folium.Marker(location=[station['lat'], station['lon']], popup=folium.Popup(popup_html, max_width=300), tooltip=f"Top End: {station['name']} ({station['count']} trips)", icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa')).add_to(end_pin_group)
            
    # --- Layer: Corridors and Round Trips ---
    if corridors_data:
        round_trip_stations = {}
        for route in corridors_data:
            is_round_trip = route.get('start_coords') == route.get('end_coords')
            if is_round_trip and 'start_coords' in route:
                station_name = route['route_name'].split(' → ')[0]
                coords = tuple(route['start_coords'])
                if coords not in round_trip_stations:
                    round_trip_stations[coords] = {'name': station_name, 'count': route['count']}
                else:
                    round_trip_stations[coords]['count'] += route['count']
            elif 'start_coords' in route and 'end_coords' in route:
                popup_html = f"""<div style="font-family: Arial, sans-serif; font-size: 14px;"><h4 style="margin:0 0 5px 0; color:#FF5733;">➡️ Popular Corridor</h4><b>Route:</b> {route['route_name']}<br><b>Total Trips:</b> {route['count']}</div>"""
                AntPath(
                    locations=[route['start_coords'], route['end_coords']],
                    weight=5, color='#FF5733', delay=800, dash_array=[10, 20],
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(corridor_group)

        for coords, data in round_trip_stations.items():
            popup_html = f"""<div style="font-family: Arial, sans-serif; font-size: 14px;"><h4 style="margin:0 0 5px 0; color:#8E44AD;">🔄 Round Trip Hotspot</h4><b>Station:</b> {data['name']}<br><b>Round Trips:</b> {data['count']}</div>"""
            folium.Marker(location=list(coords), popup=folium.Popup(popup_html, max_width=300), tooltip=f"Round Trip Hotspot: {data['name']}", icon=folium.Icon(color='purple', icon='refresh', prefix='fa')).add_to(round_trip_group)
            
    # --- Custom Legend ---
    legend_html = '''
    <div style="position: fixed; bottom: 20px; right: 20px; width: 290px; 
                background-color: rgba(255, 255, 255, 0.95); border: 2px solid #bbb;
                z-index:9999; font-size:14px; padding: 15px; border-radius: 8px;
                color: #333; font-family: Arial, sans-serif; box-shadow: 3px 3px 10px rgba(0,0,0,0.2);">
    <h4 style="margin-top:0; margin-bottom:10px; text-align:center; border-bottom: 1px solid #ccc; padding-bottom: 5px;">Map Legend</h4>
    <p style="margin: 5px 0;"><i class="fa fa-arrow-up" style="color:green;"></i>   Top Start Station</p>
    <p style="margin: 5px 0;"><i class="fa fa-flag-checkered" style="color:red;"></i>   Top End Station</p>
    <p style="margin: 5px 0;"><i class="fa fa-long-arrow-right" style="color:#FF5733;"></i>   Popular Corridor (A → B)</p>
    <p style="margin: 5px 0;"><i class="fa fa-refresh" style="color:#8E44AD;"></i>   Round Trip Hotspot</p>
    <p style="margin: 5px 0;"><i class="fa fa-circle" style="color:#3186cc;"></i>   Persona Station Footprint (Top 20%)</p>
    <p style="margin: 8px 0 0 0; font-size: 12px; font-style: italic; border-top: 1px solid #ddd; padding-top: 8px;">Animated lines show travel direction.</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(m)
    return m

def create_temporal_chart(hourly_distribution):
    """Create temporal activity chart showing hourly patterns"""
    hours = list(range(24))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=hourly_distribution, mode='lines+markers', name='Activity Level',
        line=dict(color='#1f77b4', width=3), marker=dict(size=8, color='#1f77b4')
    ))
    fig.update_layout(
        title="Daily Activity Pattern", xaxis_title="Hour of Day", yaxis_title="Number of Trips",
        template="plotly_white", height=400, showlegend=False,
        xaxis=dict(tickmode='array', tickvals=list(range(0, 24, 2)), ticktext=[f"{h:02d}:00" for h in range(0, 24, 2)])
    )
    fig.add_vrect(x0=7, x1=9, fillcolor="#ff7f0e", opacity=0.2, annotation_text="Morning Rush", annotation_position="top left")
    fig.add_vrect(x0=17, x1=19, fillcolor="#ff7f0e", opacity=0.2, annotation_text="Evening Rush", annotation_position="top right")
    return fig

def create_location_heatmap(station_data):
    """Create interactive map with station usage heatmap - showing only top 20% of stations"""
    london_center = [51.5074, -0.1278]
    m = folium.Map(location=london_center, zoom_start=12, tiles='OpenStreetMap')
    
    if not station_data:
        return m
    
    # Calculate top 20% threshold based on usage percentage
    top_20_threshold = _get_top_20_percent_threshold(station_data, 'percentage')
    
    for station in station_data:
        # Only show stations in top 20%
        if station['percentage'] >= top_20_threshold:
            if station['percentage'] > 5:
                color, radius = '#d62728', 12
            elif station['percentage'] > 2:
                color, radius = '#ff7f0e', 8
            else:
                color, radius = '#2ca02c', 6
            folium.CircleMarker(
                location=[station['lat'], station['lon']], radius=radius,
                popup=f"<b>{station['name']}</b><br>Usage: {station['usage']} trips<br>Percentage: {station['percentage']:.1f}%",
                color=color, fillColor=color, fillOpacity=0.7, weight=2
            ).add_to(m)
    
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <p><b>Station Usage (Top 20%)</b></p>
    <p><i class="fa fa-circle" style="color:#d62728"></i> High (>5%)</p>
    <p><i class="fa fa-circle" style="color:#ff7f0e"></i> Medium (2-5%)</p>
    <p><i class="fa fa-circle" style="color:#2ca02c"></i> Low (≥{top_20_threshold:.1f}%)</p>
    <p style="font-size: 11px; font-style: italic;">Threshold: {top_20_threshold:.1f}%</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    return m

def create_duration_distribution_chart(durations, persona_name):
    """Create trip duration distribution chart"""
    if not durations or len(durations) == 0:
        return go.Figure().update_layout(title=f"No duration data for {persona_name}")
    fig = px.histogram(x=durations, nbins=30, title=f"Trip Duration Distribution - {persona_name}", color_discrete_sequence=['#1f77b4'])
    fig.update_layout(xaxis_title="Duration (minutes)", yaxis_title="Number of Trips", template="plotly_white", height=400)
    mean_duration = np.mean(durations)
    fig.add_vline(x=mean_duration, line_dash="dash", line_color="#d62728", annotation_text=f"Average: {mean_duration:.1f} min")
    return fig

def create_seasonal_trends_chart(monthly_data):
    """Create seasonal trends visualization"""
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months, y=monthly_data, mode='lines+markers', name='Usage %', line=dict(color='#2ca02c', width=3), marker=dict(size=8, color='#2ca02c'), fill='tonexty'))
    fig.update_layout(title="Seasonal Usage Patterns", xaxis_title="Month", yaxis_title="Usage Percentage", template="plotly_white", height=400, showlegend=False)
    return fig

def create_day_of_week_chart(dow_data):
    """Create day of week usage chart"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    y_values = list(dow_data.values()) if isinstance(dow_data, dict) else dow_data
    fig = px.bar(x=days, y=y_values, title="Usage by Day of Week", color=y_values, color_continuous_scale='Viridis')
    fig.update_layout(xaxis_title="Day of Week", yaxis_title="Number of Trips", template="plotly_white", height=400)
    fig.update(layout_coloraxis_showscale=False)
    return fig