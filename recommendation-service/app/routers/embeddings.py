from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    SyncEmbeddingRequest,
    SyncEmbeddingResponse,
    DeleteEmbeddingResponse
)


router = APIRouter()


@router.post("/batch", response_model=BatchEmbeddingResponse)
async def batch_generate_embeddings(request: BatchEmbeddingRequest):
    """
    Batch generate embeddings for multiple videos.

    This endpoint generates embeddings for all provided videos and adds them
    to the FAISS index. Existing embeddings for the same video IDs will be
    preserved (use sync for updates).
    """
    from app.main import get_embedding_service, get_faiss_service

    embedding_service = get_embedding_service()
    faiss_service = get_faiss_service()

    if not embedding_service or not faiss_service:
        raise HTTPException(status_code=503, detail="Services not initialized")

    # Generate embeddings
    videos_data = [
        {
            "video_id": v.video_id,
            "title": v.title,
            "description": v.description
        }
        for v in request.videos
    ]

    try:
        embeddings = embedding_service.generate_batch_embeddings(videos_data)
        added = faiss_service.add_embeddings(embeddings)

        # Save index after batch update
        faiss_service.save_index()

        return BatchEmbeddingResponse(
            processed=len(embeddings),
            failed=len(request.videos) - len(embeddings),
            index_size=faiss_service.get_index_size()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


@router.post("/sync", response_model=SyncEmbeddingResponse)
async def sync_embeddings(request: SyncEmbeddingRequest):
    """
    Sync embeddings for all provided videos.

    This endpoint:
    1. Checks which videos already have embeddings
    2. Generates embeddings only for new videos
    3. Rebuilds the index if needed

    Use this for incremental updates triggered from Node.js.
    """
    from app.main import get_embedding_service, get_faiss_service

    embedding_service = get_embedding_service()
    faiss_service = get_faiss_service()

    if not embedding_service or not faiss_service:
        raise HTTPException(status_code=503, detail="Services not initialized")

    # Find videos that need embeddings
    existing_ids = set(faiss_service.get_all_video_ids())
    new_videos = [
        {
            "video_id": v.video_id,
            "title": v.title,
            "description": v.description
        }
        for v in request.videos
        if v.video_id not in existing_ids
    ]

    new_count = 0
    if new_videos:
        try:
            embeddings = embedding_service.generate_batch_embeddings(new_videos)
            new_count = faiss_service.add_embeddings(embeddings)
            faiss_service.save_index()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

    return SyncEmbeddingResponse(
        total_videos=len(request.videos),
        new_embeddings=new_count,
        existing_embeddings=len(existing_ids),
        index_size=faiss_service.get_index_size()
    )


@router.delete("/{video_id}", response_model=DeleteEmbeddingResponse)
async def delete_embedding(video_id: str):
    """
    Remove embedding for a specific video.

    Note: This marks the embedding for removal. A full index rebuild
    may be needed for optimal performance after many deletions.
    """
    from app.main import get_faiss_service

    faiss_service = get_faiss_service()

    if not faiss_service:
        raise HTTPException(status_code=503, detail="FAISS service not initialized")

    if faiss_service.remove_embedding(video_id):
        # Rebuild index to actually remove the embedding
        faiss_service.rebuild_index()
        faiss_service.save_index()

        return DeleteEmbeddingResponse(
            success=True,
            message=f"Embedding for video {video_id} removed successfully"
        )
    else:
        return DeleteEmbeddingResponse(
            success=False,
            message=f"No embedding found for video {video_id}"
        )
