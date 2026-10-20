"""
Unit Tests for ExploreMate Rating & Review Analytics (Task 5 / 13)
Tests rating algorithms with required edge cases:
- 0 reviews
- 1 review
- All 5-star reviews
- Mixed reviews
Validates Bayesian Weighted Average (m = 5) and Wilson Score Lower Bound.
"""

import unittest
from rating_utils import (
    calculate_average_rating,
    calculate_bayesian_rating,
    calculate_wilson_score,
    calculate_rating_distribution,
    get_complete_rating_summary
)

class TestRatingAnalytics(unittest.TestCase):
    
    # -------------------------------------------------------------
    # EDGE CASE 1: 0 Reviews
    # -------------------------------------------------------------
    def test_zero_reviews(self):
        ratings = []
        
        # Simple average of empty list is 0.0
        self.assertEqual(calculate_average_rating(ratings), 0.0)
        
        # Bayesian rating with 0 reviews should equal prior mean C (default 4.0)
        # v = 0, m = 5: (0/(0+5))*0 + (5/(0+5))*4.0 = 4.0
        self.assertEqual(calculate_bayesian_rating(ratings, prior_mean=4.0, m=5), 4.0)
        
        # Wilson score with 0 reviews should be 0.0
        self.assertEqual(calculate_wilson_score(ratings), 0.0)
        
        # Distribution counts should all be 0
        dist = calculate_rating_distribution(ratings)
        self.assertEqual(dist["total_reviews"], 0)
        for star in range(1, 6):
            self.assertEqual(dist["counts"][star], 0)
            self.assertEqual(dist["breakdown"][star]["percentage"], 0.0)

    # -------------------------------------------------------------
    # EDGE CASE 2: 1 Review
    # -------------------------------------------------------------
    def test_single_review_5_star(self):
        ratings = [5]
        
        # Simple average is 5.0
        self.assertEqual(calculate_average_rating(ratings), 5.0)
        
        # Bayesian weighted average: v = 1, m = 5, R = 5.0, C = 4.0
        # (1 / 6) * 5.0 + (5 / 6) * 4.0 = (5 + 20) / 6 = 25 / 6 ≈ 4.17
        expected_bayesian = round((1/6) * 5.0 + (5/6) * 4.0, 2)
        self.assertEqual(calculate_bayesian_rating(ratings, prior_mean=4.0, m=5), expected_bayesian)
        
        # Wilson score: with 1 positive review out of 1, lower bound is strictly < 100% due to sample size penalty
        wilson = calculate_wilson_score(ratings)
        self.assertGreater(wilson, 0.0)
        self.assertLess(wilson, 100.0)
        
        # Distribution
        dist = calculate_rating_distribution(ratings)
        self.assertEqual(dist["total_reviews"], 1)
        self.assertEqual(dist["counts"][5], 1)
        self.assertEqual(dist["breakdown"][5]["percentage"], 100.0)

    def test_single_review_1_star(self):
        ratings = [1]
        
        # Simple average is 1.0
        self.assertEqual(calculate_average_rating(ratings), 1.0)
        
        # Bayesian weighted average: v = 1, m = 5, R = 1.0, C = 4.0
        # (1 / 6) * 1.0 + (5 / 6) * 4.0 = (1 + 20) / 6 = 21 / 6 = 3.50
        self.assertEqual(calculate_bayesian_rating(ratings, prior_mean=4.0, m=5), 3.50)
        
        # Wilson score with 0 positive reviews is 0.0
        self.assertEqual(calculate_wilson_score(ratings), 0.0)

    # -------------------------------------------------------------
    # EDGE CASE 3: All 5-Star Reviews
    # -------------------------------------------------------------
    def test_all_five_star_reviews(self):
        ratings = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]  # 10 reviews
        
        self.assertEqual(calculate_average_rating(ratings), 5.0)
        
        # Bayesian: v = 10, m = 5, R = 5.0, C = 4.0
        # (10 / 15) * 5.0 + (5 / 15) * 4.0 = (50 + 20) / 15 = 70 / 15 ≈ 4.67
        expected_bayesian = round((10/15) * 5.0 + (5/15) * 4.0, 2)
        self.assertEqual(calculate_bayesian_rating(ratings, prior_mean=4.0, m=5), expected_bayesian)
        
        # Wilson score: all positive reviews, high score (approx 69% lower bound for n=10 at 95% CI)
        wilson = calculate_wilson_score(ratings)
        self.assertGreater(wilson, 65.0)
        
        # Distribution: 100% 5-star
        dist = calculate_rating_distribution(ratings)
        self.assertEqual(dist["counts"][5], 10)
        self.assertEqual(dist["counts"][4], 0)
        self.assertEqual(dist["breakdown"][5]["percentage"], 100.0)

    # -------------------------------------------------------------
    # EDGE CASE 4: Mixed Reviews
    # -------------------------------------------------------------
    def test_mixed_reviews(self):
        ratings = [5, 4, 4, 3, 2, 1, 5, 5]  # 8 reviews: sum = 29, mean = 3.625
        
        # Arithmetic average: 29 / 8 = 3.62
        self.assertEqual(calculate_average_rating(ratings), 3.62)
        
        # Bayesian weighted average: v = 8, m = 5, R = 3.625, C = 4.0
        # (8 / 13) * 3.625 + (5 / 13) * 4.0 = (29 + 20) / 13 = 49 / 13 ≈ 3.77
        expected_bayesian = round((8/13) * 3.625 + (5/13) * 4.0, 2)
        self.assertEqual(calculate_bayesian_rating(ratings, prior_mean=4.0, m=5), expected_bayesian)
        
        # Positive reviews (>= 4 stars): 5, 4, 4, 5, 5 -> 5 out of 8 (62.5%)
        wilson = calculate_wilson_score(ratings)
        self.assertGreater(wilson, 25.0)
        self.assertLess(wilson, 62.5)  # Lower bound must be less than sample proportion
        
        # Distribution breakdown verification
        dist = calculate_rating_distribution(ratings)
        self.assertEqual(dist["counts"][5], 3)
        self.assertEqual(dist["counts"][4], 2)
        self.assertEqual(dist["counts"][3], 1)
        self.assertEqual(dist["counts"][2], 1)
        self.assertEqual(dist["counts"][1], 1)
        self.assertEqual(dist["total_reviews"], 8)

    def test_complete_summary_aggregation(self):
        ratings = [5, 5, 4]
        summary = get_complete_rating_summary(ratings, prior_mean=4.0, m=5)
        self.assertIn("total_reviews", summary)
        self.assertIn("simple_average", summary)
        self.assertIn("bayesian_rating", summary)
        self.assertIn("wilson_positive_score", summary)
        self.assertIn("distribution", summary)
        self.assertEqual(summary["total_reviews"], 3)

if __name__ == '__main__':
    unittest.main()
