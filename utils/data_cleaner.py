import pandas as pd
import numpy as np

class DataCleaner:
    @staticmethod
    def clean_bike_data(df: pd.DataFrame) -> pd.DataFrame:
        # Store original shape for reporting
        original_shape = df.shape
        
        # Standardize column names
        df.columns = [col.lower() for col in df.columns]
        
        # Remove duplicate rows
        df = df.drop_duplicates()
        
        # Drop columns with all NA
        df = df.dropna(axis=1, how='all')
        
        # Remove rows where end coordinates are missing
        # Note: The column names from your BigQuery query are 'end_lat' and 'end_lon'
        # not 'end_latitude' and 'end_longitude'
        if 'end_lat' in df.columns and 'end_lon' in df.columns:
            rows_before = len(df)
            df = df.dropna(subset=['end_lat', 'end_lon'])
            rows_removed = rows_before - len(df)
            if rows_removed > 0:
                print(f"Removed {rows_removed} rows with missing end coordinates ({rows_removed/rows_before*100:.1f}%)")
        
        # Also remove rows where start coordinates are missing (optional but recommended)
        if 'start_lat' in df.columns and 'start_lon' in df.columns:
            rows_before = len(df)
            df = df.dropna(subset=['start_lat', 'start_lon'])
            rows_removed = rows_before - len(df)
            if rows_removed > 0:
                print(f"Removed {rows_removed} rows with missing start coordinates ({rows_removed/rows_before*100:.1f}%)")
        
        # Fill remaining NA values
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
            elif pd.api.types.is_bool_dtype(df[col]):
                # Convert boolean columns to int to avoid NA ambiguity
                df[col] = df[col].astype(float).fillna(0).astype(int)
            else:
                df[col] = df[col].fillna("")

        if 'duration' in df.columns and 'duration_minutes' not in df.columns:
                df['duration_minutes'] = df['duration'] / 60

        # Remove trips with duration longer than 6 hours (360 minutes)
        if 'duration_minutes' in df.columns:
            rows_before = len(df)
            df = df[df['duration_minutes'] <= 360]
            rows_removed = rows_before - len(df)
            if rows_removed > 0:
                print(f"Removed {rows_removed} trips with duration longer than 6 hours ({rows_removed/rows_before*100:.1f}%)")

        if 'start_date' in df.columns and 'start_date_time' not in df.columns:
            df['start_date_time'] = pd.to_datetime(df['start_date'])

        if 'end_date' in df.columns and 'end_date_time' not in df.columns:
            df['end_date_time'] = pd.to_datetime(df['end_date'])

        print(f"Data cleaned: {original_shape} -> {df.shape}")
        return df
    
    