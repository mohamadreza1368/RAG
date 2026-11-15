import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from vector_store.config import VectorStoreConfig
from vector_store.client import QdrantStore
from embeddings.manager import EmbeddingManager
from search.bm25_index import BM25SearchIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Indexer")

def load_all_chunks(chunks_dir: Path) -> List[Dict[str, Any]]:
    """Loads all chunk JSON files from the chunks directory."""
    all_chunks = []
    chunk_files = list(chunks_dir.glob("*_chunks.json"))
    logger.info("Found %d chunk files in %s", len(chunk_files), chunks_dir)

    for cfile in chunk_files:
        try:
            with open(cfile, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_chunks.extend(data)
                elif isinstance(data, dict) and "chunks" in data:
                    all_chunks.extend(data["chunks"])
        except Exception as e:
            logger.error("Error reading %s: %s", cfile, e)

    logger.info("Loaded total of %d legal chunks.", len(all_chunks))
    return all_chunks

def run_indexer(
    chunks_dir: Path = Path("data/processed/chunks"),
    model_name: str = "google/embeddinggemma-2",
    dimension: int = 768,
    batch_size: int = 16,
    qdrant_path: Path = Path("data/qdrant_db"),
    bm25_path: Path = Path("data/search/bm25.pkl")
):
    chunks = load_all_chunks(chunks_dir)
    if not chunks:
        logger.warning("No chunks found to index! Please run preprocessor first.")
        return

    # 1. Build and Save BM25 Index
    logger.info("--- Step 1: Building BM25 Index ---")
    bm25_index = BM25SearchIndex()
    bm25_index.build_index(chunks)
    bm25_index.save(bm25_path)

    # 2. Vector Embedding & Qdrant Upsert
    logger.info("--- Step 2: Vector Embeddings with %s ---", model_name)
    embed_mgr = EmbeddingManager(model_name=model_name, dimension=dimension)
    
    texts_to_embed = [c.get("full_text") or c.get("content", "") for c in chunks]
    logger.info("Generating embeddings for %d texts...", len(texts_to_embed))
    vectors = embed_mgr.embed_documents(texts_to_embed, batch_size=batch_size)

    logger.info("--- Step 3: Storing in Qdrant Vector Store ---")
    vec_config = VectorStoreConfig(storage_path=qdrant_path, vector_size=dimension)
    qdrant = QdrantStore(config=vec_config)
    qdrant.upsert_chunks(chunks, vectors)

    logger.info("=" * 60)
    logger.info("INDEXING COMPLETE!")
    logger.info("BM25 Index stored at: %s", bm25_path)
    logger.info("Qdrant DB stored at:   %s", qdrant_path)
    logger.info("Total Points:          %d", qdrant.count())
    logger.info("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Qdrant Vector & BM25 Indexes for Regulatory RAG.")
    parser.add_argument("--chunks-dir", type=Path, default=Path("data/processed/chunks"))
    parser.add_argument("--model", type=str, default="google/embeddinggemma-2")
    parser.add_argument("--dim", type=int, default=768)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--qdrant-path", type=Path, default=Path("data/qdrant_db"))
    parser.add_argument("--bm25-path", type=Path, default=Path("data/search/bm25.pkl"))

    args = parser.parse_args()
    run_indexer(
        chunks_dir=args.chunks_dir,
        model_name=args.model,
        dimension=args.dim,
        batch_size=args.batch_size,
        qdrant_path=args.qdrant_path,
        bm25_path=args.bm25_path
    )
