import pandas as pd
from typing import Dict, Any, List

class ConsumerTypeAnalyzer:
    """
    Minimalistic analyzer providing brand recommendations for each persona.
    """
    
    # Brand recommendations for each persona
    PERSONA_BRANDS = {
        "Morning Commuter": [
            "Starbucks", "Dunkin'", "Fitbit", "Apple Watch", "Nike", "Under Armour",
            "Transit apps", "Premium coffee brands", "Fitness trackers"
        ],
        "Evening Commuter": [
            "Uber Eats", "DoorDash", "Netflix", "Spotify", "Social media platforms",
            "Restaurant chains", "Entertainment apps"
        ],
        "Weekend Explorer": [
            "Instagram", "TikTok", "Airbnb", "Eventbrite", "Local breweries",
            "Adventure gear brands", "Tourist attractions", "Social platforms"
        ],
        "Fitness": [
            "Peloton", "MyFitnessPal", "Garmin", "Lululemon", "CrossFit",
            "Protein brands", "Gym chains", "Fitness apps"
        ],
        "Tourist/Long Leisure": [
            "TripAdvisor", "Booking.com", "Museums", "Cultural institutions",
            "Tourism boards", "Local experiences", "Travel brands"
        ]
    }
    
    @staticmethod
    def get_brand_recommendations(persona: str) -> List[str]:
        """
        Get brand recommendations for a specific persona.
        
        Args:
            persona (str): The selected persona
            
        Returns:
            List[str]: List of recommended brands
        """
        if persona == "ALL":
            return ["Multi-segment brands", "Universal platforms", "Community-focused brands"]
        
        return ConsumerTypeAnalyzer.PERSONA_BRANDS.get(persona, []) 