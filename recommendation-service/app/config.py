from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Model Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # FAISS Configuration
    faiss_index_path: str = "./data/faiss_index"

    # Scoring Weights (explainable)
    embedding_weight: float = 0.5
    recency_weight: float = 0.3
    popularity_weight: float = 0.2

    # Recency decay (days)
    recency_decay_days: int = 90

    # Popularity normalization (max views)
    max_views_for_normalization: int = 1_000_000

    # User profile weights
    watched_weight: float = 0.3
    liked_weight: float = 0.7

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
