#!/usr/bin/env python3
"""
Ranking Engine Module
Calculates repository scores based on Thrust usage and popularity metrics.
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any


class RankingEngine:
    """Calculates and manages repository ranking scores"""

    def __init__(self):
        # Scoring weights
        self.thrust_weight = 0.6
        self.popularity_weight = 0.4

        # Scoring parameters
        self.thrust_usage_base = 10  # Base number for logarithmic scaling
        self.star_base = 100  # Base number for star scoring
        self.fork_multiplier = 0.3  # Weight for forks vs stars
        self.recency_decay_days = 365  # How many days for recency to decay by 50%

    def calculate_scores(
        self, thrust_usage: int, stars: int, forks: int, last_updated: str
    ) -> Dict[str, float]:
        """Calculate all scores for a repository"""

        # Calculate Thrust usage score
        thrust_score = self._calculate_thrust_score(thrust_usage)

        # Calculate popularity score
        popularity_score = self._calculate_popularity_score(stars, forks, last_updated)

        # Calculate combined score
        combined_score = (
            thrust_score * self.thrust_weight
            + popularity_score * self.popularity_weight
        )

        return {
            "thrust_score": thrust_score,
            "popularity_score": popularity_score,
            "combined_score": combined_score,
        }

    def _calculate_thrust_score(self, thrust_usage: int) -> float:
        """Calculate score based on Thrust library usage count"""
        if thrust_usage == 0:
            return 0.0

        # Use logarithmic scaling to prevent repositories with very high usage
        # from completely dominating the scores
        # Score ranges from 0 to 100
        score = 100 * math.log(thrust_usage + 1) / math.log(self.thrust_usage_base + 1)

        # Cap at 100
        return min(score, 100.0)

    def _calculate_popularity_score(
        self, stars: int, forks: int, last_updated: str
    ) -> float:
        """Calculate score based on repository popularity metrics"""

        # Base popularity score from stars and forks
        # Forks are weighted less than stars
        popularity_raw = stars + (forks * self.fork_multiplier)

        if popularity_raw == 0:
            return 0.0

        # Use logarithmic scaling for popularity too
        popularity_score = (
            100 * math.log(popularity_raw + 1) / math.log(self.star_base + 1)
        )

        # Apply recency factor
        recency_factor = self._calculate_recency_factor(last_updated)

        # Final popularity score with recency adjustment
        final_score = popularity_score * recency_factor

        return min(final_score, 100.0)

    def _calculate_recency_factor(self, last_updated: str) -> float:
        """Calculate recency factor based on last update time"""
        if not last_updated:
            return 0.5  # Default factor for unknown update time

        try:
            # Parse the GitHub timestamp
            update_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            current_time = datetime.now(timezone.utc)

            # Calculate days since last update
            days_since_update = (current_time - update_time).days

            # Calculate recency factor (exponential decay)
            # Factor ranges from 1.0 (very recent) to ~0.1 (very old)
            decay_rate = (
                math.log(0.5) / self.recency_decay_days
            )  # 50% decay in specified days
            recency_factor = math.exp(decay_rate * days_since_update)

            # Ensure minimum factor
            return max(recency_factor, 0.1)

        except Exception:
            return 0.5  # Default factor if parsing fails

    def get_ranking_explanation(
        self, scores: Dict[str, float], details: Dict[str, Any]
    ) -> str:
        """Generate a human-readable explanation of the ranking"""
        thrust_usage = details.get("thrust_usage", 0)
        stars = details.get("stars", 0)
        forks = details.get("forks", 0)

        explanation_parts = []

        # Thrust score explanation
        if thrust_usage == 0:
            explanation_parts.append("No Thrust usage detected")
        elif thrust_usage < 5:
            explanation_parts.append(f"Low Thrust usage ({thrust_usage} occurrences)")
        elif thrust_usage < 20:
            explanation_parts.append(
                f"Moderate Thrust usage ({thrust_usage} occurrences)"
            )
        else:
            explanation_parts.append(f"High Thrust usage ({thrust_usage} occurrences)")

        # Popularity explanation
        if stars < 10:
            explanation_parts.append("Low popularity")
        elif stars < 100:
            explanation_parts.append("Moderate popularity")
        elif stars < 1000:
            explanation_parts.append("High popularity")
        else:
            explanation_parts.append("Very high popularity")

        return "; ".join(explanation_parts)

    def update_weights(self, thrust_weight: float, popularity_weight: float):
        """Update scoring weights (should sum to 1.0)"""
        total = thrust_weight + popularity_weight
        self.thrust_weight = thrust_weight / total
        self.popularity_weight = popularity_weight / total

