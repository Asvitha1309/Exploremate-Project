import os
from dotenv import load_dotenv

load_dotenv()

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Google Places API configuration (Optional)
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

# Itinerary & Routing Configuration
ROAD_FACTOR = 1.3  # Road winding factor applied to straight-line Haversine
RAIN_PROB_THRESHOLD = 50  # Precipitation probability (%) to trigger indoor rain swap
WALK_MAX_KM = 3.5  # Maximum recommended walking distance
CYCLE_MAX_KM = 12.0  # Maximum recommended cycling distance


# DEFRA (UK Department for Environment, Food & Rural Affairs)
# 2023 Government GHG Conversion Factors for Company Reporting
# All emission figures are official estimates in kg CO2e per passenger-kilometer (pkm)
CARBON_EMISSION_CONFIG = {
    "source_citation": "UK Department for Environment, Food & Rural Affairs (DEFRA) GHG Conversion Factors (2023)",
    "label": "estimates",
    "disclaimer": "All carbon figures are DEFRA-based indicative travel estimates per passenger-kilometer.",
    "modes": {
        "walk": {
            "name": "Walking",
            "icon": "fa-person-walking",
            "co2_per_km_kg": 0.000,
            "badge": "Zero Emission",
            "is_zero_emission": True,
            "speed_kmh": 4.5
        },
        "cycle": {
            "name": "Bicycle",
            "icon": "fa-bicycle",
            "co2_per_km_kg": 0.000,
            "badge": "Eco Active transit",
            "is_zero_emission": True,
            "speed_kmh": 14.0
        },
        "bus": {
            "name": "Local Bus",
            "icon": "fa-bus-simple",
            "co2_per_km_kg": 0.0965,
            "badge": "Shared Transit",
            "is_zero_emission": False,
            "speed_kmh": 22.0
        },
        "train": {
            "name": "Rail / Train",
            "icon": "fa-train",
            "co2_per_km_kg": 0.0355,
            "badge": "Low Carbon Transit",
            "is_zero_emission": False,
            "speed_kmh": 35.0
        },
        "car": {
            "name": "Petrol Car",
            "icon": "fa-car",
            "co2_per_km_kg": 0.1705,
            "badge": "High Carbon Baseline",
            "is_zero_emission": False,
            "speed_kmh": 28.0
        }
    }
}
