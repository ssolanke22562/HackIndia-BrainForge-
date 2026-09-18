import pytest
import numpy as np
from backend.link import recursive_text_split, compute_embeddings
from backend.config import settings

def test_recursive_text_split_small():
    text = "Short text under chunk size."
    chunks = recursive_text_split(text, chunk_size=200, chunk_overlap=20)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_recursive_text_split_paragraphs():
    p1 = "First paragraph about distributed systems and raft consensus." * 4
    p2 = "Second paragraph about vector databases, FAISS, and embeddings." * 4
    full_text = f"{p1}\n\n{p2}"
    chunks = recursive_text_split(full_text, chunk_size=250, chunk_overlap=30)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 300

def test_compute_embeddings_shape_and_norm():
    texts = ["SecondSelf AI PKM platform", "FAISS vector retrieval"]
    embeddings = compute_embeddings(texts)
    assert embeddings.shape == (2, settings.EMBEDDING_DIMENSION)
    # Check L2 unit norm
    norms = np.linalg.norm(embeddings, axis=1)
    for norm in norms:
        assert pytest.approx(norm, abs=1e-4) == 1.0

def test_cosine_similarity_threshold():
    texts = [
        "Machine learning deep neural networks and transformer models",
        "Deep learning transformers and AI neural architectures",
        "Culinary recipe for baking chocolate sourdough bread"
    ]
    embeddings = compute_embeddings(texts)
    
    sim_tech = np.dot(embeddings[0], embeddings[1])
    sim_cooking = np.dot(embeddings[0], embeddings[2])
    
    # Highly related notes should meet tau >= 0.70
    assert sim_tech > 0.70
    # Unrelated notes should be significantly lower
    assert sim_cooking < 0.50
