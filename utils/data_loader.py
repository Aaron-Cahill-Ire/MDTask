import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.oauth2 import service_account
import os
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class BigQueryDataLoader:
    def __init__(self, project_id=None, dataset_id=None, table_id=None, credentials_path=None):
        self._using_demo_data = False
        self.client = None
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.dataset_id = dataset_id or "bigquery-public-data.london_bicycles"
        self.table_id = table_id or "cycle_hire"
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self._initialize_client()

    def _initialize_client(self):
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
                self.client = bigquery.Client(credentials=credentials, project=self.project_id)
            else:
                self.client = bigquery.Client(project=self.project_id)
            self._test_connection()
        except Exception as e:
            print(f"Error initializing BigQuery client: {e}")
            self.client = None

    def _test_connection(self):
        try:
            self.client.query("SELECT 1").result()
            print("BigQuery connection successful.")
        except Exception as e:
            print(f"BigQuery connection test failed: {e}")
            self.client = None

    @st.cache_data(ttl=3600) # Cache for 1 hour to avoid refetching
    def load_station_data(_self):
        """
        Loads and caches the cycle station data with coordinates.
        The _self parameter is used because st.cache_data works on functions, not methods directly.
        """
        print("Fetching station data from BigQuery (will be cached for 1 hour)...")
        if not _self.client:
            print("Cannot load station data, BigQuery client not available.")
            return pd.DataFrame(columns=['name', 'latitude', 'longitude'])

        stations_table = "bigquery-public-data.london_bicycles.cycle_stations"
        query = f"SELECT name, latitude, longitude FROM `{stations_table}` WHERE installed = true"
        try:
            df_stations = _self.client.query(query).to_dataframe()
            return df_stations
        except Exception as e:
            print(f"Error fetching station data: {e}")
            return pd.DataFrame(columns=['name', 'latitude', 'longitude'])

    def load_bike_data(self, limit=50000):
        """
        Loads bike trip data and joins it with station coordinates directly in BigQuery.
        """
        full_trips_table = f"{self.dataset_id}.{self.table_id}"
        stations_table = "bigquery-public-data.london_bicycles.cycle_stations"

        query = f"""
        WITH trips AS (
            SELECT *
            FROM `{full_trips_table}`
            WHERE DATE(start_date) >= '2022-01-01' AND DATE(start_date) <= '2022-12-31'
            LIMIT {limit}
        )
        SELECT
            trips.*,
            start_stn.latitude AS start_lat,
            start_stn.longitude AS start_lon,
            end_stn.latitude AS end_lat,
            end_stn.longitude AS end_lon
        FROM trips
        LEFT JOIN `{stations_table}` AS start_stn
            ON trips.start_station_name = start_stn.name
        LEFT JOIN `{stations_table}` AS end_stn
            ON trips.end_station_name = end_stn.name
        """

        try:
            if self.client is None:
                raise Exception("BigQuery client not initialized or connection failed")
            
            print("Executing JOIN query on BigQuery to fetch trips with coordinates...")
            df = self.client.query(query).to_dataframe()
            print(f"Successfully loaded {len(df)} rows with coordinates.")
            
            # Ensure coordinate columns exist even if the query fails to create them
            for col in ['start_lat', 'start_lon', 'end_lat', 'end_lon']:
                if col not in df.columns:
                    df[col] = np.nan
            
            return df
        except Exception as e:
            print(f"BigQuery query failed: {e}. Falling back to demo data.")
            self._using_demo_data = True
            return self._create_demo_data()

    def _create_demo_data(self):
        """
        Create demo data when BigQuery is not available.
        This version now includes simulated coordinate columns to match the real query output.
        """
        print("Creating demo dataset...")
        np.random.seed(42)
        n_samples = 10000

        station_names = [
            "Great Tower Street, Monument", "Grosvenor Road, Pimlico", "Exhibition Road, Knightsbridge",
            "British Museum, Bloomsbury", "Hyde Park Corner, Hyde Park", "Victoria & Albert Museum, South Kensington",
            "London Bridge Station, Southwark", "King's Cross Station, King's Cross", "Canary Wharf Station, Canary Wharf",
        ]
        
        # Simulate coordinates for the demo stations
        station_coords = {name: [51.5074 + np.random.uniform(-0.15, 0.15), -0.1278 + np.random.uniform(-0.2, 0.2)] for name in station_names}

        data = {
            'rental_id': range(1, n_samples + 1),
            'duration': np.random.exponential(1200, n_samples),
            'bike_id': np.random.randint(1, 1000, n_samples),
            'start_date': pd.to_datetime(np.random.choice(pd.date_range('2022-01-01', '2022-12-31', freq='h'), n_samples)),
            'start_station_name': np.random.choice(station_names, n_samples),
            'end_station_name': np.random.choice(station_names, n_samples),
        }
        df = pd.DataFrame(data)

        # Add derived columns that the rest of the app expects
        df['end_date'] = df['start_date'] + pd.to_timedelta(df['duration'], unit='s')
        df['duration_minutes'] = df['duration'] / 60
        
        # Add simulated coordinates by mapping from the station name
        df['start_lat'] = df['start_station_name'].map(lambda x: station_coords.get(x, [None, None])[0])
        df['start_lon'] = df['start_station_name'].map(lambda x: station_coords.get(x, [None, None])[1])
        df['end_lat'] = df['end_station_name'].map(lambda x: station_coords.get(x, [None, None])[0])
        df['end_lon'] = df['end_station_name'].map(lambda x: station_coords.get(x, [None, None])[1])

        print("Created demo data with simulated coordinates.")
        return df
    

