import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Optional


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service with a pre-trained model.

        Args:
            model_name: Name of the sentence-transformer model to use.
                       Default is 'all-MiniLM-L6-v2' (384 dimensions, fast, good quality)
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def generate_embedding(self, title: str, description: str) -> np.ndarray:
        """
        Generate a normalized embedding from video title and description.

        Args:
            title: Video title
            description: Video description

        Returns:
            Normalized embedding vector (numpy array)
        """
        # Combine title and description
        text = f"{title}. {description}"

        # Generate embedding with normalization for cosine similarity
        embedding = self.model.encode(text, normalize_embeddings=True)

        return embedding

    def generate_batch_embeddings(
        self,
        videos: list[dict]
    ) -> dict[str, np.ndarray]:
        """
        Generate embeddings for multiple videos efficiently using batching.

        Args:
            videos: List of dicts with 'video_id', 'title', 'description' keys

        Returns:
            Dictionary mapping video_id to embedding vector
        """
        if not videos:
            return {}

        # Prepare texts for batch encoding
        texts = [f"{v['title']}. {v['description']}" for v in videos]

        # Batch encode with normalization
        embeddings = self.model.encode(texts, normalize_embeddings=True)

        # Create mapping
        result = {}
        for video, embedding in zip(videos, embeddings):
            result[video['video_id']] = embedding

        return result

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        return self.dimension

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
