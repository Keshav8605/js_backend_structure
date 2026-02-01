import faiss
import numpy as np
import json
import os
from typing import Optional
from pathlib import Path


class FAISSService:
    """Service for managing FAISS vector index operations."""

    def __init__(self, dimension: int = 384, index_path: str = "./data/faiss_index"):
        """
        Initialize FAISS service.

        Args:
            dimension: Embedding vector dimension (default 384 for all-MiniLM-L6-v2)
            index_path: Directory path for persisting the index
        """
        self.dimension = dimension
        self.index_path = Path(index_path)

        # Create index directory if it doesn't exist
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(dimension)

        # Mappings between video IDs and index positions
        self.id_to_idx: dict[str, int] = {}
        self.idx_to_id: dict[int, str] = {}

        # Track embeddings for potential updates
        self.embeddings_store: dict[str, np.ndarray] = {}

        # Load existing index if available
        self._load_index()

    def _load_index(self) -> bool:
        """Load index and mappings from disk if they exist."""
        index_file = self.index_path / "index.faiss"
        mapping_file = self.index_path / "id_mapping.json"
        embeddings_file = self.index_path / "embeddings.npy"

        if index_file.exists() and mapping_file.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(index_file))

                # Load mappings
                with open(mapping_file, "r") as f:
                    data = json.load(f)
                    self.id_to_idx = data.get("id_to_idx", {})
                    # Convert string keys back to int for idx_to_id
                    self.idx_to_id = {int(k): v for k, v in data.get("idx_to_id", {}).items()}

                # Load embeddings store if exists
                if embeddings_file.exists():
                    embeddings_data = np.load(embeddings_file, allow_pickle=True).item()
                    self.embeddings_store = embeddings_data

                print(f"Loaded FAISS index with {self.index.ntotal} vectors")
                return True
            except Exception as e:
                print(f"Error loading index: {e}")
                self._reset_index()
                return False
        return False

    def _reset_index(self):
        """Reset to empty index."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_to_idx = {}
        self.idx_to_id = {}
        self.embeddings_store = {}

    def add_embeddings(self, embeddings: dict[str, np.ndarray]) -> int:
        """
        Add or update embeddings in the index.

        Args:
            embeddings: Dictionary mapping video_id to embedding vector

        Returns:
            Number of embeddings added
        """
        added = 0

        for video_id, embedding in embeddings.items():
            # Ensure embedding is the right shape
            if embedding.shape[0] != self.dimension:
                print(f"Skipping {video_id}: wrong dimension {embedding.shape[0]}")
                continue

            # Store embedding
            self.embeddings_store[video_id] = embedding

            # If video already exists, we need to rebuild (FAISS doesn't support update)
            if video_id not in self.id_to_idx:
                idx = self.index.ntotal
                self.index.add(embedding.reshape(1, -1).astype('float32'))
                self.id_to_idx[video_id] = idx
                self.idx_to_id[idx] = video_id
                added += 1

        return added

    def remove_embedding(self, video_id: str) -> bool:
        """
        Mark a video for removal (requires rebuild to fully remove).

        Args:
            video_id: Video ID to remove

        Returns:
            True if video was found and marked for removal
        """
        if video_id in self.embeddings_store:
            del self.embeddings_store[video_id]
            # Note: FAISS doesn't support direct removal, need to rebuild
            return True
        return False

    def rebuild_index(self):
        """Rebuild the entire index from stored embeddings."""
        if not self.embeddings_store:
            self._reset_index()
            return

        # Create new index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_to_idx = {}
        self.idx_to_id = {}

        # Add all embeddings
        video_ids = list(self.embeddings_store.keys())
        embeddings_array = np.array([self.embeddings_store[vid] for vid in video_ids]).astype('float32')

        self.index.add(embeddings_array)

        for idx, video_id in enumerate(video_ids):
            self.id_to_idx[video_id] = idx
            self.idx_to_id[idx] = video_id

        print(f"Rebuilt index with {self.index.ntotal} vectors")

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 20,
        exclude_ids: Optional[set[str]] = None
    ) -> list[dict]:
        """
        Search for k nearest neighbors.

        Args:
            query_vector: Query embedding vector
            k: Number of results to return
            exclude_ids: Set of video IDs to exclude from results

        Returns:
            List of dicts with 'video_id' and 'similarity' keys
        """
        if self.index.ntotal == 0:
            return []

        exclude_ids = exclude_ids or set()

        # Over-fetch to account for exclusions
        fetch_k = min(k * 3, self.index.ntotal)

        # Ensure query is the right shape
        query = query_vector.reshape(1, -1).astype('float32')

        # Search
        distances, indices = self.index.search(query, fetch_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            video_id = self.idx_to_id.get(idx)
            if video_id and video_id not in exclude_ids:
                results.append({
                    "video_id": video_id,
                    "similarity": float(dist)
                })
                if len(results) >= k:
                    break

        return results

    def get_embedding(self, video_id: str) -> Optional[np.ndarray]:
        """Get the embedding for a specific video."""
        return self.embeddings_store.get(video_id)

    def get_embeddings(self, video_ids: list[str]) -> dict[str, np.ndarray]:
        """Get embeddings for multiple videos."""
        return {
            vid: self.embeddings_store[vid]
            for vid in video_ids
            if vid in self.embeddings_store
        }

    def has_embedding(self, video_id: str) -> bool:
        """Check if a video has an embedding."""
        return video_id in self.embeddings_store

    def get_index_size(self) -> int:
        """Return the number of vectors in the index."""
        return self.index.ntotal

    def get_all_video_ids(self) -> list[str]:
        """Return all video IDs in the index."""
        return list(self.id_to_idx.keys())

    def save_index(self):
        """Persist index and mappings to disk."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_path / "index.faiss"))

            # Save mappings
            with open(self.index_path / "id_mapping.json", "w") as f:
                json.dump({
                    "id_to_idx": self.id_to_idx,
                    "idx_to_id": {str(k): v for k, v in self.idx_to_id.items()}
                }, f)

            # Save embeddings store
            np.save(self.index_path / "embeddings.npy", self.embeddings_store)

            print(f"Saved FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            print(f"Error saving index: {e}")
            raise
