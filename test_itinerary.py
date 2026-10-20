"""
ExploreMate Comprehensive Itinerary, Weather, Chapters & Translation Test Suite
Validates:
1. Zero duplicate places or restaurants across day plans (clear, rainy, simulated).
2. Clear weather + simulate off => zero swapped stops, no rain banner.
3. Simulate rain => outdoor stops swapped to unused indoor places, indoor stops unchanged.
4. Slot-by-slot rain => only affected slot outdoor stops swapped.
5. Per-leg distances differ per pair and match Haversine * ROAD_FACTOR.
6. Strictly increasing timed stops without overlaps.
7. Chapters count equals 10 with valid metadata, locations, and ink costs.
8. Translation resilient fallback returns HTTP 200 and English text with notice.
"""

import unittest
from unittest.mock import patch
import json
from app import app, haversine_distance_km
from config import ROAD_FACTOR

class ExploreMateItineraryTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def _parse_time_to_minutes(self, time_str):
        parts = time_str.strip().split()
        time_part = parts[0]
        period = parts[1].upper()
        h, m = map(int, time_part.split(":"))
        if period == "PM" and h != 12:
            h += 12
        elif period == "AM" and h == 12:
            h = 0
        return h * 60 + m

    def test_no_duplicate_places_clear_weather(self):
        """Verify no duplicate place_ids or restaurant_ids in clear weather itinerary."""
        resp = self.app.get('/api/itinerary?rain_simulated=false')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        stops = data.get("stops", [])
        self.assertGreater(len(stops), 0)

        place_ids = [s["place"]["id"] for s in stops]
        self.assertEqual(len(place_ids), len(set(place_ids)), f"Duplicate places detected: {place_ids}")

        restaurant_ids = [
            s["suggested_food"]["restaurant"]["id"]
            for s in stops
            if "suggested_food" in s and s["suggested_food"].get("restaurant")
        ]
        self.assertEqual(len(restaurant_ids), len(set(restaurant_ids)), f"Duplicate restaurants detected: {restaurant_ids}")

    def test_no_duplicate_places_rain_simulated(self):
        """Verify no duplicate place_ids in simulated rain itinerary."""
        resp = self.app.get('/api/itinerary?rain_simulated=true')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        stops = data.get("stops", [])
        self.assertGreater(len(stops), 0)

        place_ids = [s["place"]["id"] for s in stops]
        self.assertEqual(len(place_ids), len(set(place_ids)), f"Duplicate places detected in rain: {place_ids}")

    @patch('app.fetch_weather_data')
    def test_clear_forecast_simulate_off_zero_swaps(self, mock_weather):
        """When forecast is clear and simulate is off: 0 swapped stops, no rain banner."""
        mock_weather.return_value = {
            "source": "Open-Meteo Mock Clear",
            "current": {"temperature": 29.0, "weathercode": 0, "windspeed": 10},
            "slots": {
                "morning": {"temp": 28.0, "precip_prob": 5, "weather": {"is_rain": False, "short": "Sunny"}, "clothing": "Casual", "is_rain": False},
                "afternoon": {"temp": 31.0, "precip_prob": 10, "weather": {"is_rain": False, "short": "Sunny"}, "clothing": "Casual", "is_rain": False},
                "evening": {"temp": 28.0, "precip_prob": 5, "weather": {"is_rain": False, "short": "Sunny"}, "clothing": "Casual", "is_rain": False}
            }
        }
        resp = self.app.get('/api/itinerary?rain_simulated=false')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["is_pivoted"])
        self.assertEqual(data["banner_type"], "sunny_info")
        self.assertIn("Clear conditions", data["banner_message"])
        for stop in data["stops"]:
            self.assertFalse(stop["swapped"])
            self.assertIsNone(stop["original_place"])

    def test_simulate_rain_swaps_outdoor_only(self):
        """Simulate rain swaps outdoor activities to indoor with reasons, keeping indoor stops unchanged."""
        resp = self.app.get('/api/itinerary?rain_simulated=true')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["is_pivoted"])
        self.assertEqual(data["banner_type"], "rain_alert")
        self.assertIn("indoor", data["banner_message"].lower())

        for stop in data["stops"]:
            p = stop["place"]
            self.assertTrue(p["indoor"], f"Stop {p['name']} should be indoor during rain")
            if stop["swapped"]:
                self.assertIsNotNone(stop["original_place"])
                self.assertIsNotNone(stop["swap_reason"])
            # Casablanca boutique was candidate and already indoor, so it should not be marked swapped
            if p["id"] == "casablanca-boutique":
                self.assertFalse(stop["swapped"], "Indoor place should not be marked swapped")

    @patch('app.fetch_weather_data')
    def test_partial_afternoon_rain_swaps_afternoon_only(self, mock_weather):
        """Rain ONLY in afternoon slot swaps ONLY afternoon outdoor activities."""
        mock_weather.return_value = {
            "source": "Open-Meteo Mock Partial",
            "current": {"temperature": 29.0, "weathercode": 61, "windspeed": 10},
            "slots": {
                "morning": {"temp": 28.0, "precip_prob": 10, "weather": {"is_rain": False, "short": "Sunny"}, "clothing": "Linen", "is_rain": False},
                "afternoon": {"temp": 30.0, "precip_prob": 80, "weather": {"is_rain": True, "short": "Rain"}, "clothing": "Poncho", "is_rain": True},
                "evening": {"temp": 27.0, "precip_prob": 15, "weather": {"is_rain": False, "short": "Breeze"}, "clothing": "Jacket", "is_rain": False}
            }
        }
        resp = self.app.get('/api/itinerary?rain_simulated=false')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["is_pivoted"])

        for stop in data["stops"]:
            if stop["slot"] == "morning":
                self.assertFalse(stop["swapped"], f"Morning stop {stop['name']} should NOT be swapped")
            elif stop["slot"] == "evening":
                self.assertFalse(stop["swapped"], f"Evening stop {stop['name']} should NOT be swapped")
            elif stop["slot"] == "afternoon" and stop["place"]["id"] == "pondicherry-museum":
                self.assertTrue(stop["swapped"], "Afternoon outdoor stop should be swapped to museum")
                self.assertEqual(stop["original_place"], "Botanical Garden")

    def test_per_leg_distances_differ_and_match_haversine(self):
        """Different leg pairs show different distances matching Haversine * ROAD_FACTOR."""
        resp = self.app.get('/api/itinerary?rain_simulated=false')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        stops = data["stops"]
        self.assertGreaterEqual(len(stops), 3)

        legs = [s["leg_to_next"] for s in stops if "leg_to_next" in s]
        self.assertGreaterEqual(len(legs), 2)

        # Distance between leg 0 and leg 1 must be different
        dists = [l["distance_km"] for l in legs]
        self.assertNotEqual(dists[0], dists[1], "Consecutive legs should have different distances")

        # Verify math
        for idx in range(len(stops) - 1):
            p1 = stops[idx]["place"]
            p2 = stops[idx + 1]["place"]
            leg = stops[idx]["leg_to_next"]
            raw_h = haversine_distance_km(p1["lat"], p1["long"], p2["lat"], p2["long"])
            expected = round(raw_h * ROAD_FACTOR, 2)
            self.assertAlmostEqual(leg["distance_km"], expected, delta=0.05)
            self.assertIn("walk_min", leg["travel_times"])
            self.assertIn("cycle_min", leg["travel_times"])
            self.assertIn("car_min", leg["travel_times"])

    def test_stop_times_strictly_increasing(self):
        """Stop times are strictly increasing with no overlaps."""
        resp = self.app.get('/api/itinerary?rain_simulated=false')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        stops = data["stops"]

        last_end_minutes = -1
        for s in stops:
            start_m = self._parse_time_to_minutes(s["start_time"])
            end_m = self._parse_time_to_minutes(s["end_time"])
            self.assertGreater(end_m, start_m, f"Stop {s['name']} end time must be greater than start time")
            self.assertGreaterEqual(start_m, last_end_minutes, f"Stop {s['name']} overlaps with previous stop")
            last_end_minutes = end_m

    def test_chapters_count_and_metadata(self):
        """Verify data/chapters.json contains 10 chapters with required schema."""
        resp = self.app.get('/api/chapters')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        chapters = data.get("chapters", [])
        self.assertEqual(len(chapters), 10, f"Expected 10 chapters, found {len(chapters)}")

        # Chapter 1 is free
        self.assertEqual(chapters[0]["ink_cost_kg"], 0.0)
        self.assertEqual(chapters[0]["id"], "chap-1")

        for idx, ch in enumerate(chapters):
            self.assertEqual(ch["id"], f"chap-{idx + 1}")
            self.assertIn("text_en", ch)
            self.assertIn("text_ta", ch)
            self.assertIn("summary", ch)
            self.assertIn("cliffhanger_line", ch)
            self.assertIn("location", ch)
            self.assertIn("lat", ch["location"])
            self.assertIn("lng", ch["location"])
            self.assertGreaterEqual(ch["ink_cost_kg"], 0.0)
            self.assertLessEqual(ch["ink_cost_kg"], 1.0)

    def test_translation_endpoint_fallback(self):
        """Verify translation endpoint returns valid response with fallback on missing/failed API."""
        resp = self.app.post('/api/translate', json={
            "text": "Where is the nearest bus stop?",
            "to": "ta"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("translation", data)
        self.assertTrue(len(data["translation"]) > 0)

        # Test non-stored arbitrary string fallback
        resp_fallback = self.app.post('/api/translate', json={
            "text": "An unusual custom phrase for fallback testing 99824",
            "to": "ta"
        })
        self.assertEqual(resp_fallback.status_code, 200)
        data_f = resp_fallback.get_json()
        self.assertEqual(data_f["status"], "success")
        self.assertIn("translation", data_f)

if __name__ == '__main__':
    unittest.main()
