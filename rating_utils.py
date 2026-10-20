"""
ExploreMate Review & Rating Analytics Module
Implements:
1. Bayesian Weighted Average: (v / (v + m)) * R + (m / (v + m)) * C  (m = 5)
2. Wilson Score Lower Bound for % positive ranking
3. Rating distribution and star statistics
"""

import math

def calculate_average_rating(ratings):
    """Calculates simple arithmetic mean of ratings list."""
    if not ratings:
        return 0.0
    return round(sum(ratings) / len(ratings), 2)

def calculate_bayesian_rating(ratings, prior_mean=4.0, m=5):
    """
    Computes Bayesian Weighted Average:
    (v / (v + m)) * R + (m / (v + m)) * C
    
    Parameters:
    - ratings: list of integers/floats (1 to 5)
    - prior_mean (C): global baseline rating prior (default 4.0)
    - m: minimum confidence weight (specified as 5)
    """
    v = len(ratings)
    if v == 0:
        return round(float(prior_mean), 2)
    
    r = sum(ratings) / v
    weighted = (v / (v + m)) * r + (m / (v + m)) * prior_mean
    return round(weighted, 2)

def calculate_wilson_score(ratings, positive_threshold=4, confidence=1.96):
    """
    Computes Wilson score lower bound for '% positive' ranking.
    A positive review is defined as rating >= positive_threshold (default 4 stars).
    confidence = 1.96 corresponds to 95% confidence interval.
    
    Returns score as a percentage [0.0 to 100.0].
    """
    n = len(ratings)
    if n == 0:
        return 0.0
    
    positives = sum(1 for r in ratings if r >= positive_threshold)
    p = positives / n
    z = confidence
    z2 = z * z
    
    denominator = 1.0 + (z2 / n)
    centre = p + (z2 / (2.0 * n))
    spread = z * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))
    
    lower_bound = (centre - spread) / denominator
    lower_bound = max(0.0, min(1.0, lower_bound))
    return round(lower_bound * 100.0, 1)

def calculate_rating_distribution(ratings):
    """
    Computes distribution counts and percentages from 5-star to 1-star.
    """
    total = len(ratings)
    distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    
    for r in ratings:
        star = int(round(r))
        if 1 <= star <= 5:
            distribution[star] += 1
            
    percentages = {}
    for star in range(5, 0, -1):
        count = distribution[star]
        pct = round((count / total) * 100, 1) if total > 0 else 0.0
        percentages[star] = {
            "count": count,
            "percentage": pct
        }
        
    return {
        "total_reviews": total,
        "counts": distribution,
        "breakdown": percentages
    }

def get_complete_rating_summary(ratings, prior_mean=4.0, m=5):
    """Aggregates all rating metrics into a structured summary."""
    return {
        "total_reviews": len(ratings),
        "simple_average": calculate_average_rating(ratings),
        "bayesian_rating": calculate_bayesian_rating(ratings, prior_mean=prior_mean, m=m),
        "wilson_positive_score": calculate_wilson_score(ratings),
        "distribution": calculate_rating_distribution(ratings)
    }
