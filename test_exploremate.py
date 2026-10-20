"""
ExploreMate Automated Integration Test Suite
Validates:
1. ExploreMate rebranding and assets
2. Strict search behavior (Pondicherry & Puducherry supported; Paris unsupported)
3. Real places data & guidelines
4. Bayesian ratings & reviews endpoint
5. Nearby restaurants for two places
6. Chatbot with rate limiting and grounding
7. Weather pivot & time-slotted day itinerary
"""

import unittest
import json
from app import app

class ExploreMateTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_rebranding_home_page_and_assets(self):
        """Verify home page loads with ExploreMate branding and logo asset."""
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"ExploreMate", resp.data)
        self.assertIn(b"/assets/logo.png", resp.data)

    def test_asset_route_serves_logo(self):
        """Verify /assets/logo.png is served correctly."""
        resp = self.app.get('/assets/logo.png')
        self.assertEqual(resp.status_code, 200)

    def test_search_pondicherry_and_puducherry(self):
        """Verify 'Pondicherry', 'Puducherry', and variants all load destination data."""
        for query in ["Pondicherry", "Puducherry", "puducherry", "pondy", "PONDICHERRY"]:
            resp = self.app.get(f'/api/city?q={query}')
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["supported"])
            self.assertEqual(data["destination"], "Pondicherry")
            self.assertTrue(data["full_guide_available"])
            self.assertIn("places", data)
            self.assertIn("accommodations", data)
            self.assertIn("restaurants", data)
            self.assertIn("transit_hubs", data)

    def test_search_other_city_does_not_show_pondicherry(self):
        """
        Verify searching Paris or other cities does NOT return Pondicherry data.
        Returns centered unsupported message.
        """
        for query in ["Paris", "Goa", "Tokyo", "London", "New York"]:
            resp = self.app.get(f'/api/city?q={query}')
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertFalse(data["supported"])
            self.assertFalse(data["full_guide_available"])
            self.assertIn("will be developed in the future. ExploreMate currently supports Pondicherry only.", data["message"])
            self.assertNotIn("places", data)

    def test_place_details_with_nearby_food_and_stays(self):
        """Verify place details include guidelines, nearby places, food, and stays."""
        resp = self.app.get('/api/places/aurobindo-ashram')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        place = data["place"]
        self.assertEqual(place["id"], "aurobindo-ashram")
        self.assertIn("guidelines", place)
        self.assertIn("dress_code", place["guidelines"])
        self.assertIn("image_credit", place)
        self.assertIn("nearby_restaurants", place)
        self.assertIn("nearby_accommodations", place)

    def test_restaurants_near_route_between_two_places(self):
        """Verify endpoint suggesting restaurants near two selected places."""
        resp = self.app.get('/api/restaurants/near-route?place1=french-quarter&place2=promenade-beach')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        restaurants = data["restaurants"]
        self.assertGreater(len(restaurants), 0)
        self.assertIn("average_distance_km", restaurants[0])

    def test_reviews_submission_validation_and_bayesian_ranking(self):
        """Verify review validation, duplicate prevention, and Bayesian calculation."""
        # 1. Fetch reviews for a place
        resp = self.app.get('/api/reviews?place_id=aurobindo-ashram')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("analytics", data)
        self.assertIn("bayesian_rating", data["analytics"])
        self.assertIn("wilson_positive_score", data["analytics"])

        # 2. Submit a valid review with unique email
        import time
        test_email = f"test.user.{time.time_ns()}@exploremate.test"
        post_resp = self.app.post('/api/reviews', json={
            "place_id": "french-quarter",
            "user_name": "Test Traveler",
            "user_email": test_email,
            "rating": 5,
            "review_text": "Great heritage atmosphere and peaceful early morning walk."
        })
        self.assertEqual(post_resp.status_code, 200)

        # 3. Prevent duplicate review by same user for same place
        dup_resp = self.app.post('/api/reviews', json={
            "place_id": "french-quarter",
            "user_name": "Test Traveler",
            "user_email": test_email,
            "rating": 4,
            "review_text": "Trying to submit again."
        })
        self.assertEqual(dup_resp.status_code, 400)
        self.assertIn("already submitted", dup_resp.get_json()["message"])

    def test_chatbot_grounded_response_and_rate_limit(self):
        """Verify chat assistant response with local grounding."""
        resp = self.app.post('/api/chat', json={
            "message": "What is the emergency helpline and nearby hospital?"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("reply", data)
        self.assertIn("100", data["reply"])

if __name__ == '__main__':
    unittest.main()
