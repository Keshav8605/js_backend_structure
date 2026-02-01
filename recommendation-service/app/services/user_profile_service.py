import numpy as np
from typing import Optional

from app.config import get_settings


class UserProfileService:
    """
    Compute user preference vector from watch history and likes.

    User Vector Formula:
        user_vector = normalize(watched_weight * mean(watched_embeddings)
                              + liked_weight * mean(liked_embeddings))

    Default weights: watched=0.3, liked=0.7 (likes indicate stronger preference)
    """

    def __init__(self, dimension: int = 384):
        settings = get_settings()
        self.watched_weight = settings.watched_weight
        self.liked_weight = settings.liked_weight
        self.dimension = dimension

    def compute_user_vector(
        self,
        watched_embeddings: list[np.ndarray],
        liked_embeddings: list[np.ndarray]
    ) -> tuple[Optional[np.ndarray], dict]:
        """
        Compute user preference vector from viewing and like history.

        Args:
            watched_embeddings: List of embedding vectors for watched videos
            liked_embeddings: List of embedding vectors for liked videos

        Returns:
            Tuple of (user_vector, explanation_dict)
            user_vector is None if no history is available
        """
        explanation = {
            "watched_count": len(watched_embeddings),
            "liked_count": len(liked_embeddings),
            "weights": {
                "watched": self.watched_weight,
                "liked": self.liked_weight
            },
            "computation": []
        }

        # No history available
        if not watched_embeddings and not liked_embeddings:
            return None, {
                **explanation,
                "error": "No user history available",
                "vector_computed": False
            }

        # Initialize component vectors
        watched_component = np.zeros(self.dimension)
        liked_component = np.zeros(self.dimension)

        # Compute watched component
        if watched_embeddings:
            watched_mean = np.mean(watched_embeddings, axis=0)
            watched_component = self.watched_weight * watched_mean
            explanation["computation"].append(
                f"watched_component = {self.watched_weight} * mean({len(watched_embeddings)} videos)"
            )

        # Compute liked component
        if liked_embeddings:
            liked_mean = np.mean(liked_embeddings, axis=0)
            liked_component = self.liked_weight * liked_mean
            explanation["computation"].append(
                f"liked_component = {self.liked_weight} * mean({len(liked_embeddings)} videos)"
            )

        # Combine components
        user_vector = watched_component + liked_component

        # Normalize for cosine similarity
        norm = np.linalg.norm(user_vector)
        if norm > 0:
            user_vector = user_vector / norm
            explanation["computation"].append(f"normalized with L2 norm = {norm:.4f}")

        explanation["vector_norm"] = float(norm)
        explanation["vector_computed"] = True

        return user_vector, explanation

    def compute_from_faiss_service(
        self,
        faiss_service,
        watched_video_ids: list[str],
        liked_video_ids: list[str]
    ) -> tuple[Optional[np.ndarray], dict]:
        """
        Convenience method to compute user vector directly from video IDs.

        Args:
            faiss_service: FAISSService instance to get embeddings from
            watched_video_ids: List of watched video IDs
            liked_video_ids: List of liked video IDs

        Returns:
            Tuple of (user_vector, explanation_dict)
        """
        # Get embeddings for watched videos
        watched_embeddings = []
        for vid in watched_video_ids:
            emb = faiss_service.get_embedding(vid)
            if emb is not None:
                watched_embeddings.append(emb)

        # Get embeddings for liked videos
        liked_embeddings = []
        for vid in liked_video_ids:
            emb = faiss_service.get_embedding(vid)
            if emb is not None:
                liked_embeddings.append(emb)

        return self.compute_user_vector(watched_embeddings, liked_embeddings)
