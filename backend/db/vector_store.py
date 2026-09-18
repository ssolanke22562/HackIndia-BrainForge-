import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import faiss
import numpy as np
from backend.config import settings

logger = logging.getLogger(__name__)

class VectorStore:
    """FAISS-backed vector store using Inner Product on L2-normalized vectors (Cosine Similarity)."""

    def __init__(self, dimension: int = 384, storage_dir: Optional[Path] = None):
        self.dimension = dimension
        self.storage_dir = storage_dir or settings.vector_path
        self.index_file = self.storage_dir / "index.faiss"
        self.map_file = self.storage_dir / "id_map.json"
        
        self.index: faiss.IndexFlatIP = faiss.IndexFlatIP(self.dimension)
        self.chunk_id_map: List[str] = []
        
        # Attempt loading existing index
        self.load()

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2 normalize vectors for cosine similarity computation."""
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if len(vectors.shape) == 1:
            vectors = vectors.reshape(1, -1)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0.0] = 1.0
        return vectors / norms

    def add_vectors(self, vectors: np.ndarray, chunk_ids: List[str]) -> List[int]:
        """Normalize and add vectors to the FAISS index with chunk UUID mapping."""
        if len(vectors) != len(chunk_ids):
            raise ValueError(f"Vector count ({len(vectors)}) does not match chunk_ids count ({len(chunk_ids)})")
        
        if len(chunk_ids) == 0:
            return []

        norm_vectors = self._normalize(vectors)
        start_idx = self.index.ntotal
        self.index.add(norm_vectors)
        self.chunk_id_map.extend(chunk_ids)
        
        # Automatically persist changes
        self.save()
        
        logger.info(f"Added {len(chunk_ids)} vectors to FAISS index (Total: {self.index.ntotal})")
        return list(range(start_idx, self.index.ntotal))

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search top-k nearest neighbors by cosine similarity."""
        if self.index.ntotal == 0:
            return []

        norm_query = self._normalize(query_vector)
        actual_k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(norm_query, actual_k)
        
        results: List[Tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self.chunk_id_map):
                results.append((self.chunk_id_map[idx], float(score)))
        
        return results

    def save(self) -> None:
        """Serialize FAISS index and chunk ID map to disk."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.index_file))
            with open(self.map_file, "w", encoding="utf-8") as f:
                json.dump(self.chunk_id_map, f, indent=2)
            logger.debug(f"Saved FAISS index with {self.index.ntotal} vectors to {self.index_file}")
        except Exception as e:
            logger.error(f"Failed to save FAISS vector store: {e}")
            raise

    def load(self) -> bool:
        """Load FAISS index and chunk ID map from disk if available."""
        if self.index_file.exists() and self.map_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.map_file, "r", encoding="utf-8") as f:
                    self.chunk_id_map = json.load(f)
                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors from {self.index_file}")
                return True
            except Exception as e:
                logger.warning(f"Could not load FAISS index from disk ({e}), re-initializing empty index.")
                self.index = faiss.IndexFlatIP(self.dimension)
                self.chunk_id_map = []
                return False
        return False

    def count(self) -> int:
        """Return total vector count in index."""
        return self.index.ntotal

    def reset(self) -> None:
        """Reset index and id mapping."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunk_id_map = []
        self.save()

# Singleton instance
vector_store = VectorStore(dimension=settings.EMBEDDING_DIMENSION)
