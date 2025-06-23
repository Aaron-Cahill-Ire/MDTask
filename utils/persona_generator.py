import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging

class PersonaGenerator:
    """
    Assigns personas to rows in a DataFrame using either rule-based or K-means clustering.
    """
    
    def __init__(self, n_clusters=5, random_state=42):
        """
        Initialize the PersonaGenerator with clustering parameters.
        
        Args:
            n_clusters (int): Number of clusters for K-means (default: 5)
            random_state (int): Random state for reproducibility (default: 42)
        """
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = None
        self.scaler = StandardScaler()
        self.logger = logging.getLogger("PersonaGenerator")

    @staticmethod
    def assign_persona_rule_based(row):
        """
        Rule-based persona assignment using hardcoded business rules.
        Uses the same 5 personas as K-means clustering and considers all 4 dimensions:
        duration_minutes, hour, is_weekend, is_weekday.
        
        Args:
            row: DataFrame row with trip data
            
        Returns:
            str: Persona name
        """
        # Extract basic values
        duration = row.get('duration_minutes', None)
        hour = row.get('hour', None)
        is_weekend = row.get('is_weekend', 0)
        is_weekday = row.get('is_weekday', 0)
        
        # Handle missing values by creating from start_date if available
        if hour is None and 'start_date' in row:
            try:
                start_datetime = pd.to_datetime(row['start_date'])
                hour = start_datetime.hour
            except:
                hour = None
        
        if is_weekend == 0 and is_weekday == 0 and 'start_date' in row:
            try:
                start_datetime = pd.to_datetime(row['start_date'])
                weekday = start_datetime.weekday()
                is_weekend = 1 if weekday >= 5 else 0
                is_weekday = 1 if weekday < 5 else 0
            except:
                is_weekend = 0
                is_weekday = 0
        
        if duration is None:
            if 'duration' in row:
                duration = row['duration'] / 60
            elif 'duration_ms' in row:
                duration = row['duration_ms'] / 60000
            else:
                duration = None
        
        # Handle missing values
        if duration is None or hour is None:
            return 'General User'
        
        # Tourist/Long Leisure - Very long trips, mixed days
        # Based on Cluster 3 characteristics: very long trips, mixed days
        if duration > 90:
            return 'Tourist/Long Leisure'
        
        # Weekend Explorer - Slightly longer trips, afternoon, weekend
        # Based on Cluster 1 characteristics: weekend, afternoon hours, moderate duration
        if (is_weekend and 30 <= duration <= 70 and 12 <= hour <= 18):
            return 'Weekend Explorer'
        
        # Fitness - Moderate-long duration, afternoon, weekday
        # Based on Cluster 4 characteristics: moderate-long duration, afternoon, weekday
        if (is_weekday and 45 <= duration <= 80 and 14 <= hour <= 19):
            return 'Fitness'
        
        # Evening Commuter - Short rides, evening hours, weekday
        # Based on Cluster 0 characteristics: short rides, evening hours, weekday
        if (is_weekday and duration < 30 and 16 <= hour <= 21):
            return 'Evening Commuter'
        
        # Morning Commuter - Short rides, morning hours, weekday
        # Based on Cluster 2 characteristics: short rides, morning hours, weekday
        if (is_weekday and duration < 30 and 6 <= hour <= 11):
            return 'Morning Commuter'
        
        # Additional rules for edge cases
        
        # Weekend morning fitness/leisure
        if (is_weekend and 20 <= duration <= 60 and 7 <= hour <= 12):
            return 'Weekend Explorer'
        
        # Late night rides (likely evening commuters)
        if (is_weekday and duration < 35 and (hour >= 22 or hour <= 2)):
            return 'Evening Commuter'
        
        # Early morning fitness
        if (is_weekday and 30 <= duration <= 70 and 5 <= hour <= 8):
            return 'Fitness'
        
        # Long weekend rides
        if (is_weekend and 60 <= duration <= 90):
            return 'Tourist/Long Leisure'
        
        # Default fallback based on most common patterns
        if is_weekend:
            return 'Weekend Explorer'
        elif hour < 12:
            return 'Morning Commuter'
        elif hour >= 16:
            return 'Evening Commuter'
        else:
            return 'Fitness'

    def assign_persona_clustering(self, df):
        """
        Assign personas using K-means clustering with specified features.
        Automatically creates required columns from start_date if they don't exist.
        
        Args:
            df (pd.DataFrame): DataFrame with required columns
            
        Returns:
            pd.DataFrame: DataFrame with 'persona' column added
        """
        try:
            df_work = df.copy()
            
            # Ensure required columns exist by creating them from start_date if needed
            if 'start_date' in df_work.columns:
                start_datetime = pd.to_datetime(df_work['start_date'], errors='coerce')
                
                # Create hour column if it doesn't exist
                if 'hour' not in df_work.columns:
                    df_work['hour'] = start_datetime.dt.hour
                
                # Create is_weekend column if it doesn't exist
                if 'is_weekend' not in df_work.columns:
                    df_work['is_weekend'] = (start_datetime.dt.weekday >= 5).astype(int)
                
                # Create is_weekday column if it doesn't exist
                if 'is_weekday' not in df_work.columns:
                    df_work['is_weekday'] = (start_datetime.dt.weekday < 5).astype(int)
            
            # Create duration_minutes if it doesn't exist
            if 'duration_minutes' not in df_work.columns:
                if 'duration' in df_work.columns:
                    df_work['duration_minutes'] = df_work['duration'] / 60
                elif 'duration_ms' in df_work.columns:
                    df_work['duration_minutes'] = df_work['duration_ms'] / 60000
                else:
                    raise ValueError("No duration column found. Need 'duration', 'duration_ms', or 'duration_minutes'")
            
            # Ensure required columns exist
            required_columns = ['duration_minutes', 'hour', 'is_weekend', 'is_weekday']
            missing_columns = [col for col in required_columns if col not in df_work.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns after auto-creation: {missing_columns}")
            
            # Select features for clustering
            features = df_work[required_columns].copy()
            
            # Handle missing values
            features = features.fillna(features.mean())
            
            # Standardize features
            X = self.scaler.fit_transform(features)
            
            # Perform K-means clustering
            self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=self.random_state)
            cluster_labels = self.kmeans.fit_predict(X)
            
            # Create persona names based on cluster characteristics
            persona_names = self._generate_persona_names(df_work, cluster_labels)
            
            # Add persona column to DataFrame
            df_result = df.copy()
            df_result['persona'] = [persona_names[label] for label in cluster_labels]
            df_result['cluster'] = cluster_labels
            
            return df_result
            
        except Exception as e:
            self.logger.error(f"Error in assign_persona_clustering: {e}")
            # Fallback to rule-based assignment
            df_result = df.copy()
            df_result['persona'] = df.apply(self.assign_persona_rule_based, axis=1)
            return df_result

    def _generate_persona_names(self, df, cluster_labels):
        """
        Fixed mapping of cluster numbers to specific persona names.
        Based on the user's cluster analysis results:
        - Cluster 0: Evening Commuter (short rides, evening hours, weekday)
        - Cluster 1: Weekend Explorer (slightly longer trips, afternoon, weekend)
        - Cluster 2: Morning Commuter (short rides, morning hours, weekday)
        - Cluster 3: Tourist/Long Leisure (very long trips, mixed days)
        - Cluster 4: Fitness/Casual Long (moderate-long duration, afternoon)
        
        Args:
            df (pd.DataFrame): Original DataFrame
            cluster_labels (np.array): Cluster labels from K-means
            
        Returns:
            list: List of persona names for each cluster
        """
        # Fixed mapping based on user's cluster analysis
        fixed_persona_mapping = {
            0: "Evening Commuter",      # 🔵 Cluster 0 → Evening Commuter
            1: "Weekend Explorer",      # 🟣 Cluster 1 → Weekend Explorer
            2: "Morning Commuter",      # 🔵 Cluster 2 → Morning Commuter  
            3: "Tourist/Long Leisure", # 🔴 Cluster 3 → Tourist/Long Leisure
            4: "Fitness"   # 🟡 Cluster 4 → Fitness/Casual Long
        }
        
        # Generate persona names using fixed mapping
        persona_names = []
        for cluster_id in range(self.n_clusters):
            if cluster_id in fixed_persona_mapping:
                persona_names.append(fixed_persona_mapping[cluster_id])
            else:
                persona_names.append(f"Cluster_{cluster_id}")
        
        return persona_names

    @classmethod
    def add_persona_column(cls, df: pd.DataFrame, use_clustering=True, n_clusters=5) -> pd.DataFrame:
        """
        Adds a 'persona' column to the DataFrame.
        Automatically handles column creation and method selection.
        
        Args:
            df (pd.DataFrame): Input DataFrame
            use_clustering (bool): Whether to use clustering (True) or rule-based (False)
            n_clusters (int): Number of clusters for K-means (default: 5)
            
        Returns:
            pd.DataFrame: DataFrame with 'persona' column added
        """
        if df is None or df.empty:
            raise ValueError("DataFrame is empty or None")
        
        # Ensure we have the minimum required data
        if 'start_date' not in df.columns:
            raise ValueError("DataFrame must contain 'start_date' column for persona generation")
        
        if use_clustering:
            # Use clustering approach
            generator = cls(n_clusters=n_clusters)
            return generator.assign_persona_clustering(df)
        else:
            # Use rule-based approach
            df_result = df.copy()
            df_result['persona'] = df.apply(cls.assign_persona_rule_based, axis=1)
            return df_result