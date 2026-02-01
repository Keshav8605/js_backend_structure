from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    PersonalizedRecommendationRequest,
    PersonalizedRecommendationResponse,
    SimilarVideosResponse,
    RecommendationItem,
    SimilarVideoItem,
    ScoreBreakdown
)
from app.services.scoring_service import ScoringService
from app.services.user_profile_service import UserProfileService
from app.config import get_settings


router = APIRouter()


@router.post("/personalized", response_model=PersonalizedRecommendationResponse)
async def get_personalized_recommendations(request: PersonalizedRecommendationRequest):
    """
    Get personalized video recommendations for a user.

    This endpoint:
    1. Computes user preference vector from watch history and likes
    2. Searches FAISS for similar videos
    3. Scores each candidate using: 0.5*similarity + 0.3*recency + 0.2*popularity
    4. Returns ranked recommendations with explainable score breakdowns
    """
    from app.main import get_faiss_service

    faiss_service = get_faiss_service()

    if not faiss_service:
        raise HTTPException(status_code=503, detail="FAISS service not initialized")

    settings = get_settings()

    # Initialize services
    user_profile_service = UserProfileService(dimension=settings.embedding_dimension)
    scoring_service = ScoringService()

    # Compute user vector
    user_vector, profile_explanation = user_profile_service.compute_from_faiss_service(
        faiss_service,
        request.watched_video_ids,
        request.liked_video_ids
    )

    if user_vector is None:
        # No user history - return empty recommendations
        return PersonalizedRecommendationResponse(
            recommendations=[],
            user_profile_computed=False,
            watched_count=len(request.watched_video_ids),
            liked_count=len(request.liked_video_ids)
        )

    # Search for similar videos
    exclude_ids = set(request.exclude_video_ids)
    similar_videos = faiss_service.search(
        user_vector,
        k=request.limit * 2,  # Over-fetch for scoring
        exclude_ids=exclude_ids
    )

    # Score and rank candidates
    scored_recommendations = []
    for video in similar_videos:
        video_id = video["video_id"]
        embedding_similarity = video["similarity"]

        # Get metadata for scoring
        metadata = request.video_metadata.get(video_id)
        if metadata:
            views = metadata.views
            created_at = metadata.created_at
        else:
            # Default values if metadata not provided
            views = 0
            created_at = "2024-01-01T00:00:00Z"

        # Calculate final score
        final_score, breakdown = scoring_service.score_video(
            embedding_similarity,
            views,
            created_at
        )

        scored_recommendations.append(RecommendationItem(
            video_id=video_id,
            final_score=final_score,
            score_breakdown=ScoreBreakdown(**breakdown)
        ))

    # Sort by final score (descending)
    scored_recommendations.sort(key=lambda x: x.final_score, reverse=True)

    # Limit to requested number
    scored_recommendations = scored_recommendations[:request.limit]

    return PersonalizedRecommendationResponse(
        recommendations=scored_recommendations,
        user_profile_computed=True,
        watched_count=profile_explanation.get("watched_count", 0),
        liked_count=profile_explanation.get("liked_count", 0)
    )


@router.get("/similar/{video_id}", response_model=SimilarVideosResponse)
async def get_similar_videos(video_id: str, limit: int = 10):
    """
    Get videos similar to a specific video.

    Uses the video's embedding to find nearest neighbors in the FAISS index.
    """
    from app.main import get_faiss_service

    faiss_service = get_faiss_service()

    if not faiss_service:
        raise HTTPException(status_code=503, detail="FAISS service not initialized")

    # Get the video's embedding
    video_embedding = faiss_service.get_embedding(video_id)

    if video_embedding is None:
        raise HTTPException(
            status_code=404,
            detail=f"No embedding found for video {video_id}"
        )

    # Search for similar videos (exclude the source video)
    similar = faiss_service.search(
        video_embedding,
        k=limit,
        exclude_ids={video_id}
    )

    similar_items = [
        SimilarVideoItem(
            video_id=v["video_id"],
            similarity_score=round(v["similarity"], 4)
        )
        for v in similar
    ]

    return SimilarVideosResponse(
        video_id=video_id,
        similar_videos=similar_items
    )
