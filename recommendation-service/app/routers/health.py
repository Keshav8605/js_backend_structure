from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.config import get_settings


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status, index size, and model information.
    """
    from app.main import get_embedding_service, get_faiss_service

    settings = get_settings()
    embedding_service = get_embedding_service()
    faiss_service = get_faiss_service()

    return HealthResponse(
        status="healthy",
        index_size=faiss_service.get_index_size() if faiss_service else 0,
        model_loaded=embedding_service.is_loaded() if embedding_service else False,
        embedding_dimension=settings.embedding_dimension
    )
