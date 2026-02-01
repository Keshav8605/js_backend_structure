from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ============ Request Schemas ============

class VideoForEmbedding(BaseModel):
    video_id: str
    title: str
    description: str


class BatchEmbeddingRequest(BaseModel):
    videos: list[VideoForEmbedding]


class SyncEmbeddingRequest(BaseModel):
    videos: list[VideoForEmbedding]


class VideoMetadata(BaseModel):
    views: int = 0
    created_at: str  # ISO format datetime string


class PersonalizedRecommendationRequest(BaseModel):
    user_id: str
    watched_video_ids: list[str] = Field(default_factory=list)
    liked_video_ids: list[str] = Field(default_factory=list)
    video_metadata: dict[str, VideoMetadata] = Field(default_factory=dict)
    limit: int = 20
    exclude_video_ids: list[str] = Field(default_factory=list)


# ============ Response Schemas ============

class HealthResponse(BaseModel):
    status: str
    index_size: int
    model_loaded: bool
    embedding_dimension: int


class BatchEmbeddingResponse(BaseModel):
    processed: int
    failed: int
    index_size: int


class SyncEmbeddingResponse(BaseModel):
    total_videos: int
    new_embeddings: int
    existing_embeddings: int
    index_size: int


class ScoreBreakdown(BaseModel):
    embedding_similarity: float
    recency_score: float
    popularity_score: float
    weights: dict[str, float]
    formula: str


class RecommendationItem(BaseModel):
    video_id: str
    final_score: float
    score_breakdown: ScoreBreakdown


class PersonalizedRecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]
    user_profile_computed: bool
    watched_count: int
    liked_count: int


class SimilarVideoItem(BaseModel):
    video_id: str
    similarity_score: float


class SimilarVideosResponse(BaseModel):
    video_id: str
    similar_videos: list[SimilarVideoItem]


class DeleteEmbeddingResponse(BaseModel):
    success: bool
    message: str
