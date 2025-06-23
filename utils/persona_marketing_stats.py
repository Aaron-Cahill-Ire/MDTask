import pandas as pd
from typing import Dict, Any

def compute_marketing_stats(df: pd.DataFrame, persona: str) -> Dict[str, Any]:
    """
    Compute marketing-relevant statistics for a given persona.
    Generates data for top stations, corridors, and a complete station footprint.
    """
    full_df = df.copy()
    
    if persona != "ALL":
        df = df[df["persona"] == persona].copy()
    
    stats = {}
    if df.empty:
        return {"error": "No data for this persona."}

    # --- DESCRIPTIVE STATS ---
    stats["trip_count"] = len(df)
    
    top_start_counts = df["start_station_name"].value_counts().head(5)
    stats["top_start_stations"] = top_start_counts.to_dict()
    top_end_counts = df["end_station_name"].value_counts().head(5)
    stats["top_end_stations"] = top_end_counts.to_dict()
    
    # --- Coordinate Data Generation ---
    start_coord_lookup = df.dropna(subset=['start_lat', 'start_lon']).drop_duplicates(subset=['start_station_name']).set_index('start_station_name')
    end_coord_lookup = df.dropna(subset=['end_lat', 'end_lon']).drop_duplicates(subset=['end_station_name']).set_index('end_station_name')

    top_starts_with_coords = []
    for station_name, count in top_start_counts.items():
        if station_name in start_coord_lookup.index:
            station_details = start_coord_lookup.loc[station_name]
            top_starts_with_coords.append({'name': station_name, 'count': int(count), 'lat': station_details['start_lat'], 'lon': station_details['start_lon']})
    stats['top_start_stations_with_coords'] = top_starts_with_coords
    
    top_ends_with_coords = []
    for station_name, count in top_end_counts.items():
        if station_name in end_coord_lookup.index:
            station_details = end_coord_lookup.loc[station_name]
            top_ends_with_coords.append({'name': station_name, 'count': int(count), 'lat': station_details['end_lat'], 'lon': station_details['end_lon']})
    stats['top_end_stations_with_coords'] = top_ends_with_coords
    
    # Get ALL unique stations used by the persona for map display
    if persona != "ALL":
        # Get start station counts
        start_station_counts = df['start_station_name'].value_counts()
        end_station_counts = df['end_station_name'].value_counts()
        
        # Create start stations with counts
        start_stations = df[['start_station_name', 'start_lat', 'start_lon']].rename(columns={'start_station_name': 'name', 'start_lat': 'lat', 'start_lon': 'lon'})
        start_stations['count'] = start_stations['name'].map(start_station_counts)
        
        # Create end stations with counts
        end_stations = df[['end_station_name', 'end_lat', 'end_lon']].rename(columns={'end_station_name': 'name', 'end_lat': 'lat', 'end_lon': 'lon'})
        end_stations['count'] = end_stations['name'].map(end_station_counts)
        
        # Combine and aggregate counts for stations that appear as both start and end
        all_persona_stations = pd.concat([start_stations, end_stations]).dropna()
        all_persona_stations = all_persona_stations.groupby(['name', 'lat', 'lon'])['count'].sum().reset_index()
        
        stats['persona_stations_with_coords'] = all_persona_stations.to_dict('records')
    else:
        stats['persona_stations_with_coords'] = []

    # --- PRESCRIPTIVE #1: TOP TRAVEL CORRIDORS ---
    corridor_counts = df.groupby(['start_station_name', 'end_station_name']).agg(
        count=('rental_id', 'size'),
        start_lat=('start_lat', 'first'), start_lon=('start_lon', 'first'),
        end_lat=('end_lat', 'first'), end_lon=('end_lon', 'first')
    ).sort_values(by='count', ascending=False).head(5)
    
    formatted_corridors = {f"{start} → {end}": data['count'] for (start, end), data in corridor_counts.iterrows()}
    stats["top_travel_corridors"] = formatted_corridors
    
    corridors_with_coords = []
    for (start, end), data in corridor_counts.iterrows():
        if pd.notna(data['start_lat']) and pd.notna(data['end_lat']):
            corridors_with_coords.append({
                "route_name": f"{start} → {end}", "count": int(data['count']),
                "start_coords": [data['start_lat'], data['start_lon']], "end_coords": [data['end_lat'], data['end_lon']]
            })
    stats["top_travel_corridors_with_coords"] = corridors_with_coords

    # --- PRESCRIPTIVE #2: HIGH CONCENTRATION STATIONS ---
    if persona != "ALL":
        station_persona_counts = df.groupby('start_station_name').size()
        station_total_counts = full_df.groupby('start_station_name').size()
        concentration_data = []
        overall_persona_ratio = (len(df) / len(full_df)) * 100
        for station in station_total_counts.index:
            total_trips = station_total_counts.get(station, 0)
            persona_trips = station_persona_counts.get(station, 0)
            if total_trips >= 10:
                concentration_pct = (persona_trips / total_trips) * 100
                relative_concentration = concentration_pct / overall_persona_ratio if overall_persona_ratio > 0 else 0
                concentration_data.append({'station': station, 'persona_trips': persona_trips, 'total_trips': total_trips, 'concentration_pct': concentration_pct, 'relative_concentration': relative_concentration})
        
        concentration_df = pd.DataFrame(concentration_data)
        if not concentration_df.empty:
            top_concentration_stations = concentration_df.nlargest(5, 'relative_concentration')
            stats["opportunity_stations"] = {row['station']: {'Persona %': f"{row['concentration_pct']:.1f}%", 'Concentration': f"{row['relative_concentration']:.2f}x", 'Trips': int(row['persona_trips'])} for _, row in top_concentration_stations.iterrows()}
            coord_lookup = full_df.dropna(subset=['start_lat', 'start_lon']).set_index('start_station_name')[['start_lat', 'start_lon']].drop_duplicates()
            stations_with_coords = {}
            for _, row in top_concentration_stations.iterrows():
                station = row['station']
                if station in coord_lookup.index:
                    coords = coord_lookup.loc[station]
                    stations_with_coords[station] = {'lat': coords['start_lat'], 'lon': coords['start_lon'], 'concentration': row['relative_concentration'], 'persona_pct': row['concentration_pct']}
            stats["opportunity_stations_with_coords"] = stations_with_coords
    else:
        stats["opportunity_stations"] = {}
        stats["opportunity_stations_with_coords"] = {}
    
    # --- Time and Duration Logic ---
    if "start_date" in df.columns:
        start_datetime = pd.to_datetime(df["start_date"])
        stats["trips_by_hour"] = start_datetime.dt.hour.value_counts().reindex(range(24), fill_value=0).sort_index().to_dict()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        stats["trips_by_day_of_week"] = start_datetime.dt.day_name().value_counts().reindex(day_order, fill_value=0).to_dict()
        
        # --- SEASONAL/MONTHLY ANALYSIS ---
        # Calculate monthly usage patterns for seasonal analysis
        monthly_counts = start_datetime.dt.month.value_counts().sort_index()
        # Ensure all 12 months are represented (fill missing months with 0)
        all_months = pd.Series(index=range(1, 13), data=0)
        monthly_counts = monthly_counts.reindex(all_months.index, fill_value=0)
        
        # Convert to percentage for better visualization
        total_trips = len(df)
        if total_trips > 0:
            monthly_percentages = (monthly_counts / total_trips * 100).tolist()
        else:
            monthly_percentages = [0] * 12
        
        stats["monthly_usage_percentages"] = monthly_percentages
        
        # Also store raw counts for reference
        stats["monthly_usage_counts"] = monthly_counts.to_dict()
        
    if "duration_minutes" in df.columns:
        durations = df["duration_minutes"].dropna()
        if not durations.empty:
            stats["trip_duration_mean_min"] = round(durations.mean(), 2)
            stats["trip_duration_median_min"] = round(durations.median(), 2)
            stats["trip_duration_25th_min"] = round(durations.quantile(0.25), 2)
            stats["trip_duration_75th_min"] = round(durations.quantile(0.75), 2)

    return stats