from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.faiss_service import FAISSService
from app.routers import embeddings, recommendations, health


# Global service instances
embedding_service: EmbeddingService = None
faiss_service: FAISSService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    global embedding_service, faiss_service

    settings = get_settings()

    # Initialize services
    print("Initializing Embedding Service...")
    embedding_service = EmbeddingService(model_name=settings.embedding_model)

    print("Initializing FAISS Service...")
    faiss_service = FAISSService(
        dimension=settings.embedding_dimension,
        index_path=settings.faiss_index_path
    )

    print(f"Services initialized. Index size: {faiss_service.get_index_size()}")

    yield

    # Cleanup
    print("Saving FAISS index...")
    faiss_service.save_index()
    print("Shutdown complete.")


app = FastAPI(
    title="Video Recommendation Service",
    description="AI-based video recommendation system using embeddings and FAISS",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_embedding_service() -> EmbeddingService:
    return embedding_service


def get_faiss_service() -> FAISSService:
    return faiss_service


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(embeddings.router, prefix="/embeddings", tags=["Embeddings"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
