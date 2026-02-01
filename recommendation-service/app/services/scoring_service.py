import math
from datetime import datetime
from typing import Optional

from app.config import get_settings


class ScoringService:
    """
    Fully explainable scoring logic for video recommendations.

    Scoring Formula:
        final_score = 0.5 * embedding_similarity + 0.3 * recency_score + 0.2 * popularity_score

    All calculations are transparent and explainable.
    """

    def __init__(self):
        settings = get_settings()
        self.embedding_weight = settings.embedding_weight
        self.recency_weight = settings.recency_weight
        self.popularity_weight = settings.popularity_weight
        self.recency_decay_days = settings.recency_decay_days
        self.max_views = settings.max_views_for_normalization

    def calculate_recency_score(self, created_at: datetime) -> float:
        """
        Calculate recency score with linear decay.

        Formula: max(0, 1 - (days_old / recency_decay_days))

        - Today's video: 1.0
        - 45 days old: 0.5 (assuming 90 day decay)
        - 90+ days old: 0.0

        Args:
            created_at: Video creation datetime

        Returns:
            Recency score between 0.0 and 1.0
        """
        now = datetime.utcnow()
        days_old = (now - created_at).days

        score = max(0.0, 1.0 - (days_old / self.recency_decay_days))
        return round(score, 4)

    def calculate_popularity_score(self, views: int) -> float:
        """
        Calculate popularity score using log normalization.

        Formula: log(views + 1) / log(max_views + 1)

        This gives diminishing returns for very high view counts,
        making the score fairer for newer content.

        Args:
            views: Number of video views

        Returns:
            Popularity score between 0.0 and 1.0
        """
        if views < 0:
            views = 0

        score = math.log(views + 1) / math.log(self.max_views + 1)
        return round(min(1.0, score), 4)

    def calculate_final_score(
        self,
        embedding_similarity: float,
        recency_score: float,
        popularity_score: float
    ) -> tuple[float, dict]:
        """
        Calculate final recommendation score with full breakdown.

        Formula:
            final_score = embedding_weight * embedding_similarity
                        + recency_weight * recency_score
                        + popularity_weight * popularity_score

        Args:
            embedding_similarity: Cosine similarity from FAISS (0.0 to 1.0)
            recency_score: Recency score (0.0 to 1.0)
            popularity_score: Popularity score (0.0 to 1.0)

        Returns:
            Tuple of (final_score, breakdown_dict)
        """
        # Ensure values are in valid range
        embedding_similarity = max(0.0, min(1.0, embedding_similarity))
        recency_score = max(0.0, min(1.0, recency_score))
        popularity_score = max(0.0, min(1.0, popularity_score))

        # Calculate weighted score
        final_score = (
            self.embedding_weight * embedding_similarity +
            self.recency_weight * recency_score +
            self.popularity_weight * popularity_score
        )

        # Build explainable breakdown
        breakdown = {
            "embedding_similarity": round(embedding_similarity, 4),
            "recency_score": round(recency_score, 4),
            "popularity_score": round(popularity_score, 4),
            "weights": {
                "embedding": self.embedding_weight,
                "recency": self.recency_weight,
                "popularity": self.popularity_weight
            },
            "formula": (
                f"{self.embedding_weight} * {embedding_similarity:.4f} + "
                f"{self.recency_weight} * {recency_score:.4f} + "
                f"{self.popularity_weight} * {popularity_score:.4f}"
            )
        }

        return round(final_score, 4), breakdown

    def score_video(
        self,
        embedding_similarity: float,
        views: int,
        created_at_str: str
    ) -> tuple[float, dict]:
        """
        Score a video with all metrics calculated.

        Args:
            embedding_similarity: Cosine similarity from FAISS
            views: Number of video views
            created_at_str: ISO format datetime string

        Returns:
            Tuple of (final_score, breakdown_dict)
        """
        # Parse datetime
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            # Remove timezone info for comparison
            created_at = created_at.replace(tzinfo=None)
        except (ValueError, AttributeError):
            # Default to now if parsing fails
            created_at = datetime.utcnow()

        recency_score = self.calculate_recency_score(created_at)
        popularity_score = self.calculate_popularity_score(views)

        return self.calculate_final_score(
            embedding_similarity,
            recency_score,
            popularity_score
        )
