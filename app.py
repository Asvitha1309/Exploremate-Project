import os
import json
import math
import time
from datetime import datetime
from flask import Flask, jsonify, request, render_template, send_from_directory
import requests
from config import (
    CARBON_EMISSION_CONFIG, GEMINI_API_KEY, GOOGLE_PLACES_API_KEY,
    ROAD_FACTOR, RAIN_PROB_THRESHOLD, WALK_MAX_KM, CYCLE_MAX_KM, GEMINI_MODEL
)
from rating_utils import get_complete_rating_summary

app = Flask(__name__, static_folder="static", template_folder="templates")

# Base directories
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Rate limiting storage for /api/chat: { ip_address: [timestamp, ...] }
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30
chat_rate_limit_store = {}

def load_json_file(filename):
    """Safely loads a JSON file from the data directory with fallback."""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

def save_json_file(filename, data):
    """Safely saves a JSON file to the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False

def haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance between two coordinates in km."""
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def is_pondy_query(query_str):
    """
    Robust check for Pondicherry and Puducherry variations, extra spaces, and common typos.
    """
    if not query_str:
        return True
    
    clean = query_str.strip().lower()
    pondy_variants = [
        "pondicherry", "puducherry", "pondy", "puducheri",
        "pondychery", "puducherry union territory", "pondicherri", "puducheery"
    ]
    
    if clean in pondy_variants:
        return True
    
    # Check substring or fuzzy start
    if any(clean.startswith(v) or v in clean for v in ["pondi", "puduch", "pondy"]):
        return True
        
    return False

def interpret_weather_code(code):
    """Maps WMO weather codes to human labels and rain detection."""
    rain_codes = {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
    is_rain = code in rain_codes

    code_map = {
        0: ("Clear Skies & Sunny", "fa-sun", "Sunny"),
        1: ("Mainly Clear", "fa-cloud-sun", "Mild Sun"),
        2: ("Partly Cloudy", "fa-cloud-sun", "Partly Cloudy"),
        3: ("Overcast Clouds", "fa-cloud", "Cloudy"),
        45: ("Foggy & Misty", "fa-smog", "Foggy"),
        48: ("Rime Fog", "fa-smog", "Foggy"),
        51: ("Light Drizzle", "fa-cloud-rain", "Drizzle"),
        53: ("Moderate Drizzle", "fa-cloud-rain", "Drizzle"),
        55: ("Dense Drizzle", "fa-cloud-rain", "Drizzle"),
        61: ("Slight Rain Shower", "fa-cloud-showers-heavy", "Rain"),
        63: ("Moderate Rain", "fa-cloud-showers-heavy", "Rain"),
        65: ("Heavy Rain Downpour", "fa-cloud-showers-heavy", "Heavy Rain"),
        80: ("Scattered Rain Showers", "fa-cloud-showers-heavy", "Showers"),
        81: ("Moderate Rain Showers", "fa-cloud-showers-heavy", "Showers"),
        82: ("Violent Rain Showers", "fa-cloud-showers-heavy", "Heavy Showers"),
        95: ("Thunderstorm Expected", "fa-bolt", "Thunderstorm"),
        96: ("Thunderstorm with Slight Hail", "fa-bolt", "Thunderstorm"),
        99: ("Severe Thunderstorm", "fa-bolt", "Thunderstorm")
    }

    desc, icon, short = code_map.get(code, ("Pleasant Coastal Breeze", "fa-sun", "Fair"))
    return {
        "code": code,
        "description": desc,
        "icon": icon,
        "short": short,
        "is_rain": is_rain
    }

def get_slot_clothing_advice(slot_name, is_rain, temp_c):
    """Suggests eco-conscious clothing advice based on time slot and weather."""
    if is_rain:
        return "Waterproof rain jacket/poncho, quick-dry shorts, waterproof footwear & compact umbrella. Keep electronics in dry bags."
    
    if slot_name == "morning":
        if temp_c > 28:
            return "Light organic cotton shirt, UV-blocking sunglasses, wide-brim hat & eco-friendly mineral sunscreen."
        return "Breathable linen shirt, comfortable walking sandals & hydration flask."
    elif slot_name == "afternoon":
        return "UV protective light layers, breathable activewear, sunglasses & stay hydrated in shaded arcades."
    else:  # evening
        return "Relaxed casual linen or cotton tee, light airy cardigan for sea breeze, and walking sneakers for promenade strolling."

def fetch_weather_data(lat, lon):
    """Fetches Open-Meteo weather with robust slot parsing and resilient static fallback."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current_weather=true&"
            f"hourly=temperature_2m,precipitation_probability,weathercode&"
            f"daily=weathercode,temperature_2m_max,temperature_2m_min&"
            f"timezone=auto"
        )
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current_weather", {})
            hourly = data.get("hourly", {})
            curr_code = curr.get("weathercode", 0)
            curr_temp = curr.get("temperature", 29.5)
            
            times = hourly.get("time", [])
            hourly_temps = hourly.get("temperature_2m", [])
            hourly_precip = hourly.get("precipitation_probability", [])
            hourly_codes = hourly.get("weathercode", [])
            
            today_prefix = datetime.now().strftime("%Y-%m-%d")
            slot_indices = {"morning": [], "afternoon": [], "evening": []}
            for idx, t_str in enumerate(times):
                if t_str.startswith(today_prefix) or len(times) <= 24:
                    try:
                        hour = int(t_str.split("T")[1].split(":")[0])
                    except Exception:
                        hour = idx % 24
                    if 8 <= hour <= 11:
                        slot_indices["morning"].append(idx)
                    elif 12 <= hour <= 16:
                        slot_indices["afternoon"].append(idx)
                    elif 17 <= hour <= 21:
                        slot_indices["evening"].append(idx)

            if not slot_indices["morning"]: slot_indices["morning"] = [9, 10]
            if not slot_indices["afternoon"]: slot_indices["afternoon"] = [13, 14, 15]
            if not slot_indices["evening"]: slot_indices["evening"] = [18, 19, 20]

            def summarize_slot(indices, default_offset):
                temps = [hourly_temps[i] for i in indices if i < len(hourly_temps)]
                precips = [hourly_precip[i] for i in indices if i < len(hourly_precip)]
                codes = [hourly_codes[i] for i in indices if i < len(hourly_codes)]
                
                avg_temp = round(sum(temps) / len(temps), 1) if temps else round(curr_temp + default_offset, 1)
                max_precip = max(precips) if precips else 10
                rain_code_found = next((c for c in codes if interpret_weather_code(c)["is_rain"]), None)
                sel_code = rain_code_found if rain_code_found is not None else (codes[0] if codes else curr_code)
                w_info = interpret_weather_code(sel_code)
                is_rain = (max_precip >= RAIN_PROB_THRESHOLD) or w_info["is_rain"]
                return avg_temp, max_precip, w_info, is_rain

            m_temp, m_precip, m_weather, m_rain = summarize_slot(slot_indices["morning"], -1.5)
            a_temp, a_precip, a_weather, a_rain = summarize_slot(slot_indices["afternoon"], 2.0)
            e_temp, e_precip, e_weather, e_rain = summarize_slot(slot_indices["evening"], -1.0)

            return {
                "source": "Open-Meteo Live API",
                "current": {
                    "temperature": curr_temp,
                    "windspeed": curr.get("windspeed", 12),
                    "weathercode": curr_code,
                    "weather": interpret_weather_code(curr_code)
                },
                "slots": {
                    "morning": {
                        "time_range": "08:00 AM - 12:00 PM",
                        "temp": round(m_temp, 1),
                        "precip_prob": m_precip,
                        "weather": m_weather,
                        "clothing": get_slot_clothing_advice("morning", m_rain, m_temp),
                        "is_rain": m_rain
                    },
                    "afternoon": {
                        "time_range": "12:00 PM - 05:00 PM",
                        "temp": round(a_temp, 1),
                        "precip_prob": a_precip,
                        "weather": a_weather,
                        "clothing": get_slot_clothing_advice("afternoon", a_rain, a_temp),
                        "is_rain": a_rain
                    },
                    "evening": {
                        "time_range": "05:00 PM - 09:30 PM",
                        "temp": round(e_temp, 1),
                        "precip_prob": e_precip,
                        "weather": e_weather,
                        "clothing": get_slot_clothing_advice("evening", e_rain, e_temp),
                        "is_rain": e_rain
                    }
                }
            }
    except Exception as e:
        print(f"Open-Meteo live call: {e}. Using static resilient fallback.")

    return {
        "source": "using offline weather data",
        "current": {
            "temperature": 29.8,
            "windspeed": 14.2,
            "weathercode": 1,
            "weather": interpret_weather_code(1)
        },
        "slots": {
            "morning": {
                "time_range": "08:00 AM - 12:00 PM",
                "temp": 28.5,
                "precip_prob": 12,
                "weather": interpret_weather_code(1),
                "clothing": get_slot_clothing_advice("morning", False, 28.5),
                "is_rain": False
            },
            "afternoon": {
                "time_range": "12:00 PM - 05:00 PM",
                "temp": 31.0,
                "precip_prob": 15,
                "weather": interpret_weather_code(2),
                "clothing": get_slot_clothing_advice("afternoon", False, 31.0),
                "is_rain": False
            },
            "evening": {
                "time_range": "05:00 PM - 09:30 PM",
                "temp": 28.0,
                "precip_prob": 10,
                "weather": interpret_weather_code(0),
                "clothing": get_slot_clothing_advice("evening", False, 28.0),
                "is_rain": False
            }
        }
    }


# ==========================================
# WEB & STATIC ASSETS ROUTES
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serves files from the assets directory (e.g., logo.png)."""
    return send_from_directory(ASSETS_DIR, filename)

# ==========================================
# CORE DESTINATION & SEARCH API (Task 2)
# ==========================================

@app.route("/api/city", methods=["GET"])
def get_city():
    query = request.args.get("q", "Pondicherry").strip()
    
    # Check if query matches Pondicherry / Puducherry (or is empty default)
    if is_pondy_query(query):
        pondy_data = load_json_file("pondicherry.json")
        places = pondy_data.get("places", [])
        accommodations = pondy_data.get("accommodations", [])
        restaurants = pondy_data.get("restaurants", [])
        safety_numbers = pondy_data.get("safety_numbers", {})
        transit_hubs = pondy_data.get("transit_hubs", {})
        
        weather = fetch_weather_data(11.9338, 79.8358)
        indoor_places = [p for p in places if p.get("indoor", False)]
        outdoor_places = [p for p in places if not p.get("indoor", False)]

        return jsonify({
            "status": "success",
            "supported": True,
            "destination": "Pondicherry",
            "tagline": pondy_data.get("tagline", "The French Riviera of the East · Eco-Heritage Coastal Haven"),
            "full_guide_available": True,
            "coordinates": {"lat": 11.9338, "lon": 79.8358},
            "weather": weather,
            "places_summary": {
                "total": len(places),
                "indoor_count": len(indoor_places),
                "outdoor_count": len(outdoor_places)
            },
            "places": {
                "indoor": indoor_places,
                "outdoor": outdoor_places,
                "all": places
            },
            "accommodations": accommodations,
            "restaurants": restaurants,
            "transit_hubs": transit_hubs,
            "safety_numbers": safety_numbers
        })

    # STRICT TASK 2 REQUIREMENT:
    # If the user searches any other place (Paris, Goa, etc.), do NOT show Pondicherry results.
    # Show centered message: "<Place> will be developed in the future. ExploreMate currently supports Pondicherry only."
    place_name = query.title()
    return jsonify({
        "status": "unsupported",
        "supported": False,
        "destination": place_name,
        "full_guide_available": False,
        "message": f"{place_name} will be developed in the future. ExploreMate currently supports Pondicherry only."
    }), 200

# ==========================================
# PLACES ENDPOINTS
# ==========================================

@app.route("/api/places", methods=["GET"])
def get_places():
    pondy_data = load_json_file("pondicherry.json")
    places = pondy_data.get("places", [])
    
    interest = request.args.get("interest", "").lower().strip()
    indoor_filter = request.args.get("indoor", "").lower().strip()

    filtered = places
    if indoor_filter in ["true", "1"]:
        filtered = [p for p in filtered if p.get("indoor") is True]
    elif indoor_filter in ["false", "0"]:
        filtered = [p for p in filtered if p.get("indoor") is False]

    if interest and interest != "all":
        filtered = [p for p in filtered if p.get("interest", "").lower() == interest]

    indoor = [p for p in filtered if p.get("indoor") is True]
    outdoor = [p for p in filtered if p.get("indoor") is False]

    places_by_id = {p["id"]: p for p in places}
    def enrich_place(p):
        item = dict(p)
        item["nearby_places"] = [
            {
                "id": nid,
                "name": places_by_id[nid]["name"],
                "rating": places_by_id[nid].get("rating"),
                "indoor": places_by_id[nid].get("indoor")
            }
            for nid in item.get("nearby_place_ids", []) if nid in places_by_id
        ]
        return item

    return jsonify({
        "status": "success",
        "count": len(filtered),
        "places": [enrich_place(p) for p in filtered],
        "indoor": [enrich_place(p) for p in indoor],
        "outdoor": [enrich_place(p) for p in outdoor]
    })

@app.route("/api/places/<place_id>", methods=["GET"])
def get_place_detail(place_id):
    pondy_data = load_json_file("pondicherry.json")
    places = pondy_data.get("places", [])
    restaurants = pondy_data.get("restaurants", [])
    accommodations = pondy_data.get("accommodations", [])
    
    places_by_id = {p["id"]: p for p in places}
    if place_id not in places_by_id:
        return jsonify({"status": "error", "message": "Place not found"}), 404
    
    target = dict(places_by_id[place_id])
    target_lat = target.get("lat")
    target_lon = target.get("long")

    # Resolve nearby places
    target["nearby_places"] = [
        {
            "id": nid,
            "name": places_by_id[nid]["name"],
            "rating": places_by_id[nid].get("rating"),
            "image": places_by_id[nid].get("image"),
            "indoor": places_by_id[nid].get("indoor")
        }
        for nid in target.get("nearby_place_ids", []) if nid in places_by_id
    ]

    # Calculate nearby restaurants and accommodations with distance
    nearby_food = []
    for f in restaurants:
        dist = haversine_distance_km(target_lat, target_lon, f.get("lat", target_lat), f.get("lon", target_lon))
        item = dict(f)
        item["distance_km"] = dist
        item["walking_minutes"] = max(1, round((dist / 4.5) * 60))
        nearby_food.append(item)
    nearby_food.sort(key=lambda x: x["distance_km"])
    target["nearby_restaurants"] = nearby_food[:3]

    nearby_stays = []
    for s in accommodations:
        dist = haversine_distance_km(target_lat, target_lon, s.get("lat", target_lat), s.get("lon", target_lon))
        item = dict(s)
        item["distance_km"] = dist
        item["walking_minutes"] = max(1, round((dist / 4.5) * 60))
        nearby_stays.append(item)
    nearby_stays.sort(key=lambda x: x["distance_km"])
    target["nearby_accommodations"] = nearby_stays[:3]

    # Include shopping recommendations
    shopping_places = [
        {"id": p["id"], "name": p["name"], "rating": p["rating"], "summary": p["review_summary"]}
        for p in places if p.get("interest") == "shopping" and p["id"] != place_id
    ]
    target["shopping_recommendations"] = shopping_places[:3]

    return jsonify({
        "status": "success",
        "place": target
    })

# ==========================================
# RESTAURANTS NEAR TWO PLACES (Task 5)
# ==========================================

@app.route("/api/restaurants/near-route", methods=["GET"])
def get_restaurants_near_route():
    """
    When user selects two places, suggests related restaurants near both based on distance.
    """
    place1_id = request.args.get("place1")
    place2_id = request.args.get("place2")

    pondy_data = load_json_file("pondicherry.json")
    places_by_id = {p["id"]: p for p in pondy_data.get("places", [])}
    restaurants = pondy_data.get("restaurants", [])

    p1 = places_by_id.get(place1_id)
    p2 = places_by_id.get(place2_id)

    if not p1 or not p2:
        return jsonify({"status": "success", "restaurants": restaurants[:4]})

    scored_food = []
    for r in restaurants:
        d1 = haversine_distance_km(p1["lat"], p1["long"], r["lat"], r["lon"])
        d2 = haversine_distance_km(p2["lat"], p2["long"], r["lat"], r["lon"])
        avg_d = (d1 + d2) / 2.0
        item = dict(r)
        item["distance_from_place1_km"] = d1
        item["distance_from_place2_km"] = d2
        item["average_distance_km"] = round(avg_d, 2)
        scored_food.append(item)

    scored_food.sort(key=lambda x: x["average_distance_km"])
    return jsonify({
        "status": "success",
        "route_context": {
            "place1": p1["name"],
            "place2": p2["name"]
        },
        "restaurants": scored_food
    })

# ==========================================
# WEATHER & ITINERARY (Tasks 2, 9)
# ==========================================

@app.route("/api/weather", methods=["GET"])
def get_weather():
    lat = request.args.get("lat", 11.9338, type=float)
    lon = request.args.get("lon", 79.8358, type=float)
    weather = fetch_weather_data(lat, lon)
    return jsonify({
        "status": "success",
        "data": weather
    })

def format_time_ampm(total_minutes):
    """Formats minutes from midnight into 12-hour AM/PM string."""
    hours = (total_minutes // 60) % 24
    mins = total_minutes % 60
    period = "AM" if hours < 12 else "PM"
    display_hour = hours % 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour:02d}:{mins:02d} {period}"

def compute_leg_info(p1, p2):
    """
    Computes real Haversine distance with road winding factor (1.3)
    and travel times across walk, cycle, car, bus using CARBON_EMISSION_CONFIG speeds.
    """
    lat1, lon1 = p1.get("lat"), p1.get("long") or p1.get("lon")
    lat2, lon2 = p2.get("lat"), p2.get("long") or p2.get("lon")
    
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return {
            "from_name": p1.get("name", "Unknown"),
            "to_name": p2.get("name", "Unknown"),
            "distance_km": None,
            "distance_text": "distance unavailable",
            "travel_times": {
                "walk_min": None,
                "cycle_min": None,
                "car_min": None,
                "bus_min": None
            },
            "walk_recommended": False
        }
        
    raw_haversine = haversine_distance_km(lat1, lon1, lat2, lon2)
    dist_km = round(raw_haversine * ROAD_FACTOR, 2)
    
    modes = CARBON_EMISSION_CONFIG.get("modes", {})
    walk_spd = modes.get("walk", {}).get("speed_kmh", 4.5)
    cycle_spd = modes.get("cycle", {}).get("speed_kmh", 14.0)
    car_spd = modes.get("car", {}).get("speed_kmh", 28.0)
    bus_spd = modes.get("bus", {}).get("speed_kmh", 22.0)
    
    walk_min = round((dist_km / walk_spd) * 60)
    cycle_min = round((dist_km / cycle_spd) * 60)
    car_min = max(1, round((dist_km / car_spd) * 60))
    bus_min = max(1, round((dist_km / bus_spd) * 60))
    
    return {
        "from_name": p1.get("name"),
        "to_name": p2.get("name"),
        "distance_km": dist_km,
        "distance_text": f"{dist_km} km",
        "raw_haversine_km": raw_haversine,
        "travel_times": {
            "walk_min": walk_min,
            "cycle_min": cycle_min,
            "car_min": car_min,
            "bus_min": bus_min
        },
        "walk_recommended": walk_min <= 90 and dist_km <= WALK_MAX_KM
    }

@app.route("/api/itinerary", methods=["GET"])
def get_itinerary():
    rain_simulated = request.args.get("rain_simulated", "false").lower() in ["true", "1", "yes"]
    weather = fetch_weather_data(11.9338, 79.8358)
    slots = weather.get("slots", {})
    
    # Check rain per slot
    slot_rain = {
        "morning": rain_simulated or slots.get("morning", {}).get("is_rain", False) or slots.get("morning", {}).get("precip_prob", 0) >= RAIN_PROB_THRESHOLD,
        "afternoon": rain_simulated or slots.get("afternoon", {}).get("is_rain", False) or slots.get("afternoon", {}).get("precip_prob", 0) >= RAIN_PROB_THRESHOLD,
        "evening": rain_simulated or slots.get("evening", {}).get("is_rain", False) or slots.get("evening", {}).get("precip_prob", 0) >= RAIN_PROB_THRESHOLD
    }
    any_rain = any(slot_rain.values())

    pondy_data = load_json_file("pondicherry.json")
    places = pondy_data.get("places", [])
    restaurants = pondy_data.get("restaurants", [])
    places_by_id = {p["id"]: p for p in places}

    used_place_ids = set()
    used_restaurant_ids = set()

    def get_indoor_substitute(desired_interest, preferred_id=None):
        if preferred_id and preferred_id in places_by_id and places_by_id[preferred_id].get("indoor") and preferred_id not in used_place_ids:
            return places_by_id[preferred_id]
        indoor_candidates = [p for p in places if p.get("indoor") and p["id"] not in used_place_ids]
        matched = [p for p in indoor_candidates if p.get("interest") == desired_interest]
        if matched:
            return matched[0]
        if indoor_candidates:
            return indoor_candidates[0]
        return None

    def get_unused_restaurant(near_place=None):
        unused = [r for r in restaurants if r["id"] not in used_restaurant_ids]
        if not unused:
            return restaurants[0] if restaurants else None
        if near_place and near_place.get("lat") and (near_place.get("long") or near_place.get("lon")):
            plat = near_place["lat"]
            plon = near_place.get("long") or near_place.get("lon")
            unused.sort(key=lambda r: haversine_distance_km(plat, plon, r.get("lat", plat), r.get("lon", plon)))
        selected = unused[0]
        used_restaurant_ids.add(selected["id"])
        return selected

    slot_configs = [
        # Morning Slot (08:30 AM - 12:00 PM)
        {
            "slot": "morning",
            "candidate_id": "french-quarter",
            "indoor_sub_id": "aurobindo-ashram",
            "desired_interest": "heritage",
            "tip_outdoor": "Quiet colonial streets with blooming bougainvillea before traffic starts.",
            "tip_indoor": "Silent meditation sanctuary with flower-covered samadhi courtyard."
        },
        {
            "slot": "morning",
            "candidate_id": "promenade-beach",
            "indoor_sub_id": "cluny-embroidery",
            "desired_interest": "coastal",
            "tip_outdoor": "Brisk sea breeze stroll along the basalt seawall and Gandhi memorial.",
            "tip_indoor": "Artisanal 19th-century embroidery centre and sheltered heritage courtyard."
        },
        # Afternoon Slot (01:15 PM - 05:00 PM)
        {
            "slot": "afternoon",
            "candidate_id": "botanical-garden",
            "indoor_sub_id": "pondicherry-museum",
            "desired_interest": "nature",
            "tip_outdoor": "Shaded 200-year-old mahogany trees and rare tropical flora.",
            "tip_indoor": "Sheltered galleries featuring Roman Arikamedu excavations and bronze artifacts."
        },
        {
            "slot": "afternoon",
            "candidate_id": "casablanca-boutique",
            "indoor_sub_id": "casablanca-boutique",
            "desired_interest": "shopping",
            "tip_outdoor": "Covered boutique floors featuring organic linens, books, and artisanal pottery.",
            "tip_indoor": "Air-conditioned multi-level shopping haven safe from rain and heat."
        },
        # Evening Slot (05:00 PM - 08:30 PM)
        {
            "slot": "evening",
            "candidate_id": "french-war-memorial",
            "indoor_sub_id": "sacred-heart-basilica",
            "desired_interest": "heritage",
            "tip_outdoor": "Historic victory column honor memorial on the oceanfront boulevard.",
            "tip_indoor": "Neo-Gothic basilica illuminated by magnificent crimson stained-glass panels."
        },
        {
            "slot": "evening",
            "candidate_id": "aayi-mandapam",
            "indoor_sub_id": "manakula-vinayagar",
            "desired_interest": "heritage",
            "tip_outdoor": "Grecian white neoclassical monument set in peaceful Bharathi Park gardens.",
            "tip_indoor": "Ancient golden vimana shrine with evening camphor aarti and heritage carvings."
        }
    ]

    built_stops = []
    slot_start_clock = {
        "morning": 510,     # 08:30 AM
        "afternoon": 795,   # 01:15 PM
        "evening": 1020     # 05:00 PM
    }

    current_slot_name = None
    current_time_min = 510

    for cfg in slot_configs:
        s_name = cfg["slot"]
        if s_name != current_slot_name:
            current_slot_name = s_name
            current_time_min = slot_start_clock[s_name]

        is_slot_rainy = slot_rain[s_name]
        candidate = places_by_id.get(cfg["candidate_id"])
        if not candidate:
            continue

        is_outdoor = not candidate.get("indoor", False)
        
        # Determine if swap is needed (only outdoor stops in rainy slots are swapped)
        if is_outdoor and is_slot_rainy:
            sub = get_indoor_substitute(cfg["desired_interest"], cfg["indoor_sub_id"])
            if sub and sub["id"] not in used_place_ids:
                chosen_place = sub
                is_swapped = True
                orig_name = candidate.get("name")
                precip = slots.get(s_name, {}).get("precip_prob", 80)
                reason = "Rain simulation active" if rain_simulated else f"Rain forecast ({precip}% chance) during {s_name} slot"
                tip = cfg["tip_indoor"]
            else:
                chosen_place = candidate
                is_swapped = False
                orig_name = None
                reason = None
                tip = cfg["tip_outdoor"]
        else:
            chosen_place = candidate
            is_swapped = False
            orig_name = None
            reason = None
            tip = cfg["tip_outdoor"]

        used_place_ids.add(chosen_place["id"])
        
        # Timing
        visit_duration = chosen_place.get("visit_minutes", 60)
        start_str = format_time_ampm(current_time_min)
        end_time_min = current_time_min + visit_duration
        end_str = format_time_ampm(end_time_min)
        current_time_min = end_time_min

        # Weather badge
        slot_w = slots.get(s_name, {})
        w_short = "Rain Active" if (is_slot_rainy and (is_swapped or chosen_place.get("indoor"))) else slot_w.get("weather", {}).get("short", "Sunny")
        if rain_simulated and is_slot_rainy:
            w_short = "Simulated Rain"

        stop_dict = {
            "slot": s_name,
            "place_id": chosen_place["id"],
            "name": chosen_place.get("name"),
            "title": chosen_place.get("name"),
            "place": chosen_place,
            "start_time": start_str,
            "end_time": end_str,
            "label": f"{s_name.capitalize()} ({start_str} - {end_str})",
            "visit_minutes": visit_duration,
            "indoor": chosen_place.get("indoor", False),
            "crowd_level": "High" if s_name == "evening" else ("Medium" if s_name == "afternoon" else "Low"),
            "is_rush_hour": s_name == "evening",
            "weather_badge": w_short,
            "temp": slot_w.get("temp", 29.0),
            "clothing": slot_w.get("clothing", "Breathable linen and walking shoes"),
            "swapped": is_swapped,
            "original_place": orig_name,
            "swap_reason": reason,
            "tip": tip
        }
        built_stops.append(stop_dict)

    # Attach meal suggestions with zero duplicate restaurants
    if len(built_stops) >= 2:
        lunch_rest = get_unused_restaurant(built_stops[1]["place"])
        built_stops[1]["suggested_food"] = {
            "meal": "Lunch",
            "restaurant": lunch_rest,
            "timing_note": "Open 12:00 PM - French-Tamil courtyard luncheon"
        }
    if built_stops:
        dinner_rest = get_unused_restaurant(built_stops[-1]["place"])
        built_stops[-1]["suggested_food"] = {
            "meal": "Dinner",
            "restaurant": dinner_rest,
            "timing_note": "Open 07:30 PM - South Indian thali & coastal specialties"
        }

    # Compute real Haversine legs between consecutive stops
    for i in range(len(built_stops) - 1):
        leg = compute_leg_info(built_stops[i]["place"], built_stops[i + 1]["place"])
        built_stops[i]["leg_to_next"] = leg

    # Banner messaging
    if any_rain:
        if rain_simulated:
            banner_message = "Rain simulation active: outdoor plans moved indoors to sheltered cultural havens."
        else:
            rainy_slots = [s.capitalize() for s, r in slot_rain.items() if r]
            banner_message = f"Rain forecast during {' & '.join(rainy_slots)}: outdoor activities moved to sheltered cultural spots."
        banner_type = "rain_alert"
        surface_tabs = ["stay", "food"]
    else:
        banner_message = "Clear conditions forecast. Enjoy your outdoor-friendly eco itinerary!"
        banner_type = "sunny_info"
        surface_tabs = []

    # Final uniqueness validation
    seen = set()
    unique_stops = []
    for s in built_stops:
        pid = s["place"]["id"]
        if pid not in seen:
            seen.add(pid)
            unique_stops.append(s)

    return jsonify({
        "status": "success",
        "is_pivoted": any_rain,
        "banner_message": banner_message,
        "banner_type": banner_type,
        "surface_tabs": surface_tabs,
        "stops": unique_stops
    })


# ==========================================
# STAY & FOOD (Tasks 5, 6)
# ==========================================

@app.route("/api/stay", methods=["GET"])
def get_stay():
    pondy_data = load_json_file("pondicherry.json")
    stay = pondy_data.get("accommodations", [])
    sort_by = request.args.get("sort", "price_asc").lower()

    if sort_by == "price_asc":
        stay = sorted(stay, key=lambda x: x.get("price_per_night", 0))
    elif sort_by == "price_desc":
        stay = sorted(stay, key=lambda x: x.get("price_per_night", 0), reverse=True)
    elif sort_by == "rating":
        stay = sorted(stay, key=lambda x: x.get("rating", 0), reverse=True)

    return jsonify({
        "status": "success",
        "count": len(stay),
        "accommodations": stay
    })

@app.route("/api/food", methods=["GET"])
def get_food():
    pondy_data = load_json_file("pondicherry.json")
    food = pondy_data.get("restaurants", [])
    return jsonify({
        "status": "success",
        "count": len(food),
        "restaurants": food
    })

# ==========================================
# REVIEWS & RATINGS SYSTEM (Task 5 / 13)
# ==========================================

@app.route("/api/reviews", methods=["GET"])
def get_reviews():
    place_id = request.args.get("place_id", "").strip()
    reviews = load_json_file("reviews.json")
    
    if place_id:
        reviews = [r for r in reviews if r.get("place_id") == place_id]
        
    ratings_list = [r["rating"] for r in reviews if "rating" in r]
    analytics = get_complete_rating_summary(ratings_list, prior_mean=4.0, m=5)

    return jsonify({
        "status": "success",
        "place_id": place_id,
        "analytics": analytics,
        "reviews": reviews
    })

@app.route("/api/reviews", methods=["POST"])
def post_review():
    data = request.get_json(silent=True) or {}
    place_id = data.get("place_id", "").strip()
    user_name = data.get("user_name", "").strip()
    user_email = data.get("user_email", "").strip().lower()
    review_text = data.get("review_text", "").strip()
    rating = data.get("rating")

    # Validations
    if not place_id or not user_name or not user_email:
        return jsonify({"status": "error", "message": "Name, email, and place are required."}), 400
    
    try:
        rating_int = int(rating)
        if not (1 <= rating_int <= 5):
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Rating must be an integer between 1 and 5."}), 400
    
    if len(review_text) > 500:
        return jsonify({"status": "error", "message": "Review text cannot exceed 500 characters."}), 400

    reviews = load_json_file("reviews.json")
    
    # Check one review per user per place
    already_reviewed = any(
        r.get("place_id") == place_id and r.get("user_email", "").lower() == user_email
        for r in reviews
    )
    if already_reviewed:
        return jsonify({"status": "error", "message": "You have already submitted a review for this place."}), 400

    new_entry = {
        "id": f"rev-{int(time.time() * 1000)}",
        "place_id": place_id,
        "user_name": user_name,
        "user_email": user_email,
        "rating": rating_int,
        "review_text": review_text,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    reviews.append(new_entry)
    save_json_file("reviews.json", reviews)

    # Return updated analytics
    place_ratings = [r["rating"] for r in reviews if r.get("place_id") == place_id]
    analytics = get_complete_rating_summary(place_ratings, prior_mean=4.0, m=5)

    return jsonify({
        "status": "success",
        "message": "Review submitted successfully!",
        "review": new_entry,
        "analytics": analytics
    })

# ==========================================
# CARBON FOOTPRINT CALCULATOR (Phase 4)
# ==========================================

@app.route("/api/carbon", methods=["GET"])
def get_carbon():
    pondy_data = load_json_file("pondicherry.json")
    places_by_id = {p["id"]: p for p in pondy_data.get("places", [])}

    from_id = request.args.get("from_id", "french-quarter")
    to_id = request.args.get("to_id", "matrimandir-centre")
    custom_distance = request.args.get("distance_km", type=float)

    from_place = places_by_id.get(from_id)
    to_place = places_by_id.get(to_id)

    if custom_distance and custom_distance > 0:
        distance_km = custom_distance
    elif from_place and to_place:
        distance_km = haversine_distance_km(
            from_place["lat"], from_place["long"],
            to_place["lat"], to_place["long"]
        )
    else:
        distance_km = 3.5

    modes_config = CARBON_EMISSION_CONFIG["modes"]
    results = []
    car_factor = modes_config["car"]["co2_per_km_kg"]
    car_total_co2 = round(distance_km * car_factor, 3)

    for mode_key, mode_info in modes_config.items():
        co2_total = round(distance_km * mode_info["co2_per_km_kg"], 3)
        saved_vs_car = round(max(0.0, car_total_co2 - co2_total), 3)
        duration_minutes = round((distance_km / mode_info["speed_kmh"]) * 60)

        results.append({
            "mode": mode_key,
            "name": mode_info["name"],
            "icon": mode_info["icon"],
            "badge": mode_info["badge"],
            "is_zero_emission": mode_info["is_zero_emission"],
            "is_lowest_carbon": mode_key in ["walk", "cycle"],
            "co2_kg": co2_total,
            "co2_saved_vs_car_kg": saved_vs_car,
            "estimated_minutes": duration_minutes,
            "factor_per_km_kg": mode_info["co2_per_km_kg"]
        })

    return jsonify({
        "status": "success",
        "route": {
            "from_place": from_place.get("name") if from_place else "Origin",
            "to_place": to_place.get("name") if to_place else "Destination",
            "distance_km": distance_km
        },
        "source_citation": CARBON_EMISSION_CONFIG["source_citation"],
        "label": CARBON_EMISSION_CONFIG["label"],
        "disclaimer": CARBON_EMISSION_CONFIG["disclaimer"],
        "baseline_car_co2_kg": car_total_co2,
        "modes": results
    })

# ==========================================
# SAFETY & BEFORE YOU GO (Tasks 7, 8)
# ==========================================

@app.route("/api/safety", methods=["GET"])
def get_safety():
    pondy_data = load_json_file("pondicherry.json")
    safety = load_json_file("safety.json")
    return jsonify({
        "status": "success",
        "data": safety,
        "official_numbers": pondy_data.get("safety_numbers", {})
    })

@app.route("/api/guides", methods=["GET"])
def get_guides():
    guides = load_json_file("guides.json")
    return jsonify({
        "status": "success",
        "data": guides
    })

# ==========================================
# TRANSLATION SERVICE (Bug 3)
# ==========================================

@app.route("/api/translate", methods=["POST"])
def translate_text():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    source_lang = data.get("from", "auto")
    target_lang = data.get("to", "ta")
    
    if not text:
        return jsonify({"status": "error", "message": "Text is required"}), 400
        
    # 1. Primary Source: Check local pre-verified translations first
    verified_file = os.path.join(BASE_DIR, "data", "translation_verified_results.json")
    if not os.path.exists(verified_file):
        verified_file = os.path.join(r"c:\Users\K.Asvitha\Desktop\exploremate++", "translation_verified_results.json")
    if os.path.exists(verified_file):
        try:
            with open(verified_file, "r", encoding="utf-8") as vf:
                vdata = json.load(vf)
                for item in vdata:
                    if item.get("phrase", "").strip().lower() == text.lower():
                        t_lang_name = "Tamil" if target_lang in ["ta", "tamil"] else target_lang.capitalize()
                        if t_lang_name in item.get("translations", {}):
                            return jsonify({
                                "status": "success",
                                "translation": item["translations"][t_lang_name],
                                "provider": "Local Verified Database",
                                "source": text
                            })
        except Exception as e:
            print(f"Verified translation lookup: {e}")

    # Check chapters.json for stored text_ta
    chapters = load_json_file("chapters.json")
    for ch in chapters:
        if ch.get("text_en", "").strip().lower() == text.lower() or ch.get("title", "").strip().lower() == text.lower():
            if ch.get("text_ta") and target_lang in ["ta", "tamil"]:
                return jsonify({
                    "status": "success",
                    "translation": ch["text_ta"],
                    "provider": "Curated Heritage Archive",
                    "source": text
                })

    # 2. Try Gemini API with valid model if GEMINI_API_KEY is present
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = (
                f"Translate the following text from {source_lang} to {target_lang}. "
                "Return ONLY the direct translation without explanation or quotes:\n"
                f"{text}"
            )
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            if response and hasattr(response, "text") and response.text:
                return jsonify({
                    "status": "success",
                    "translation": response.text.strip(),
                    "provider": "Gemini AI",
                    "source": text
                })
        except Exception as e:
            print(f"Gemini translation failed: {e}")

    # 3. Try MyMemory API free tier
    try:
        url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text[:400])}&langpair={source_lang}|{target_lang}"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            mdata = res.json()
            trans = mdata.get("responseData", {}).get("translatedText")
            if trans and trans.strip() and not trans.startswith("MYMEMORY WARNING"):
                return jsonify({
                    "status": "success",
                    "translation": trans.strip(),
                    "provider": "MyMemory",
                    "source": text
                })
    except Exception as e:
        print(f"MyMemory translation failed: {e}")

    # 4. Resilient Fallback: Always return valid JSON with English text & small friendly notice
    return jsonify({
        "status": "success",
        "translation": text,
        "provider": "Local Fallback",
        "notice": "Translation service temporarily offline. Displaying original text.",
        "source": text
    }), 200

# ==========================================
# CHAPTERS SERVICE (Bug 2)
# ==========================================

@app.route("/api/chapters", methods=["GET"])
def get_chapters_route():
    chapters = load_json_file("chapters.json")
    return jsonify({
        "status": "success",
        "count": len(chapters),
        "chapters": chapters
    })


# ==========================================
# GEMINI AI CHATBOT (Task 10)
# ==========================================

@app.route("/api/chat", methods=["POST"])
def chat():
    # Rate Limiting check
    client_ip = request.remote_addr or "127.0.0.1"
    now = time.time()
    req_history = chat_rate_limit_store.get(client_ip, [])
    # Filter requests within the window
    req_history = [t for t in req_history if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(req_history) >= RATE_LIMIT_MAX_REQUESTS:
        return jsonify({
            "status": "error",
            "message": "Rate limit exceeded. Please wait a minute before sending more questions."
        }), 429
    req_history.append(now)
    chat_rate_limit_store[client_ip] = req_history

    # Input validation
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"status": "error", "message": "No message provided."}), 400
    if len(user_message) > 500:
        return jsonify({"status": "error", "message": "Message exceeds maximum length of 500 characters."}), 400

    # Collect live app context sent from client (or defaults)
    client_itinerary = data.get("itinerary_stops", [])
    current_time_str = datetime.now().strftime("%I:%M %p")

    # Destination Grounding Data
    pondy_data = load_json_file("pondicherry.json")
    places = pondy_data.get("places", [])
    accommodations = pondy_data.get("accommodations", [])
    restaurants = pondy_data.get("restaurants", [])
    safety = pondy_data.get("safety_numbers", {})

    places_summary = "\n".join([
        f"- {p.get('name', 'Place')}: {p.get('interest', 'attraction')} ({'indoor' if p.get('indoor') else 'outdoor'}), open {p.get('opening_hours', {}).get('display', 'Daily')}, fee: {p.get('guidelines', {}).get('entry_fee', 'Free')}, best time: {p.get('guidelines', {}).get('best_time_to_visit', 'Anytime')}, crowd peak: {p.get('crowd_levels', {}).get('rush_hours', 'Evening')}"
        for p in places
    ])

    stays_summary = "\n".join([
        f"- {s['name']}: ₹{s['price_per_night']}/night in {s['area']} (Phone: {s['phone']}, Booking: {s['booking_url']})"
        for s in accommodations
    ])

    food_summary = "\n".join([
        f"- {f['name']}: {f['cuisine']} in {f['area']} (Phone: {f['phone']}, Open: {f['opening_hours']['display']})"
        for f in restaurants
    ])

    system_instruction = (
        "You are ExploreMate's AI travel assistant. Help users plan trips, suggest places, and answer questions about the website.\n"
        f"The current local time is {current_time_str}.\n"
        "Ground your answers ONLY in the verified ExploreMate destination data provided below.\n"
        "If the user asks about something outside this verified data, say: 'I don't have verified data on that' instead of guessing.\n\n"
        "VERIFIED DATA:\n"
        f"Places:\n{places_summary}\n\n"
        f"Accommodations:\n{stays_summary}\n\n"
        f"Restaurants:\n{food_summary}\n\n"
        f"Emergency Helplines: Police {safety.get('police')}, Ambulance {safety.get('ambulance')}, Women {safety.get('women_helpline')}, Tourist {safety.get('tourist_helpline')}, Puducherry Tourism {safety.get('puducherry_tourism')}.\n\n"
        "ITINERARY COMMAND CAPABILITY:\n"
        "If the user asks to add, remove, or change a stop in their live itinerary (e.g. 'Add Matrimandir in morning', 'Remove museum'), include a command at the end in JSON format:\n"
        "ITINERARY_ACTION: {\"action\": \"add|remove|swap\", \"place_id\": \"<place_id>\", \"slot\": \"morning|afternoon|evening\"}\n"
        "Keep responses friendly, concise, and helpful."
    )

    # 1. Try official google-genai SDK if GEMINI_API_KEY is present
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt_content = f"{system_instruction}\n\nUser Question: {user_message}"
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_content,
            )
            
            reply_text = response.text if response and hasattr(response, "text") else ""
            if reply_text:
                # Check for ITINERARY_ACTION command
                itinerary_action = None
                if "ITINERARY_ACTION:" in reply_text:
                    parts = reply_text.split("ITINERARY_ACTION:")
                    reply_text = parts[0].strip()
                    try:
                        itinerary_action = json.loads(parts[1].strip())
                    except Exception:
                        pass

                return jsonify({
                    "status": "success",
                    "reply": reply_text,
                    "mode": "gemini_genai_sdk",
                    "itinerary_action": itinerary_action
                })
        except Exception as e:
            print(f"google-genai call failed: {e}. Falling back to grounded assistant.")

    # 2. Resilient Grounded Local Assistant (if no key or API offline)
    msg_lower = user_message.lower()
    itinerary_action = None

    # Handle smart itinerary commands locally
    if "matrimandir" in msg_lower and ("add" in msg_lower or "put" in msg_lower):
        itinerary_action = {"action": "add", "place_id": "matrimandir-centre", "slot": "morning"}
        reply = "I've added the Matrimandir Visitor Centre & Gardens to your morning itinerary slot! Remember to obtain your free entry pass upon arrival."
    elif "museum" in msg_lower and "remove" in msg_lower:
        itinerary_action = {"action": "remove", "place_id": "pondicherry-museum", "slot": "afternoon"}
        reply = "I've removed the Pondicherry Museum from your itinerary."
    elif any(k in msg_lower for k in ["rain", "weather", "shower", "pivot"]):
        reply = (
            "ExploreMate Weather Intelligence: If rain or thunderstorms occur in Pondicherry, "
            "our adaptive system automatically swaps open-air stops for covered heritage sanctuaries like "
            "Sri Aurobindo Ashram, Pondicherry Museum, and Casablanca Boutique. "
            "You can test this right now using the 'Simulate Rain' toggle in the navbar!"
        )
    elif any(k in msg_lower for k in ["food", "eat", "restaurant", "café", "cafe", "dinner", "lunch"]):
        reply = (
            "ExploreMate Dining Guide: For verified eco-conscious dining, visit Coromandel Café (White Town) for French Continental, "
            "Café des Arts (Rue Suffren) for Breton crêpes, Surguru Spot for banana-leaf South Indian dosas (₹110), "
            "or Tanto Pizzeria in Kuilapalayam for wood-fired artisanal pizzas."
        )
    elif any(k in msg_lower for k in ["stay", "hotel", "resort", "room", "price"]):
        reply = (
            "ExploreMate Accommodations: We feature verified stays with exact prices: Villa Shanti (₹6,500/night in White Town), "
            "Maison Perumal (₹5,200/night in Heritage Town), Promenade Seafront (₹4,800/night), "
            "Auroville Green Guesthouse (₹2,200/night), and Dune Eco Village (₹7,900/night). All prices verified as of March 2026."
        )
    elif any(k in msg_lower for k in ["safety", "hospital", "police", "ambulance", "emergency", "helpline"]):
        reply = (
            "ExploreMate Emergency Directory: Police: 100, Ambulance: 108, Fire: 101, Women Helpline: 1091, "
            "Tourist Helpline: 1363, and Puducherry Tourism: +91 413 2234500. "
            "Nearby 24/7 hospital: Indira Gandhi Govt General Hospital (+91 413 2336050) in White Town."
        )
    elif any(k in msg_lower for k in ["carbon", "co2", "footprint", "cycle", "walk"]):
        reply = (
            "ExploreMate Carbon Route: Walking or cycling produces 0.00 kg CO2! "
            "By choosing cycling over a car for a 5 km route, you save approximately 0.85 kg of CO2 based on official DEFRA estimates. "
            "Try the Carbon Route tab to see all 5 transport modes!"
        )
    elif any(k in msg_lower for k in ["train", "bus", "station", "transit", "irctc", "redbus"]):
        reply = (
            "ExploreMate Transit: Puducherry Railway Station (PDY) on Subbiah Salai connects to Chennai and major hubs (IRCTC booking available). "
            "The New Bus Stand on Maraimalai Adigal Salai runs 24/7 buses via PRTC/TNSTC and redBus."
        )
    else:
        reply = (
            "ExploreMate AI Assistant: Welcome to Puducherry! I can help you plan your itinerary, find verified restaurants, "
            "check crowd levels and opening hours, or arrange zero-carbon walking routes. What would you like to explore?"
        )

    return jsonify({
        "status": "success",
        "reply": reply,
        "mode": "grounded_local_assistant",
        "itinerary_action": itinerary_action,
        "note": "Running in local grounded mode. Add GEMINI_API_KEY in .env to activate Gemini GenAI cloud features."
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
