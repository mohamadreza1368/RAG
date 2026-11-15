import logging
from typing import List, Dict, Any, Optional

from vector_store.client import QdrantStore
from embeddings.manager import EmbeddingManager
from .bm25_index import BM25SearchIndex

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    Hybrid Retriever combining Dense Vector Search (Qdrant) and Lexical Search (BM25)
    using Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        vector_store: QdrantStore,
        embedding_manager: EmbeddingManager,
        bm25_index: BM25SearchIndex,
        rrf_k: int = 60,
        dense_weight: float = 1.0,
        lexical_weight: float = 1.0
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.bm25_index = bm25_index
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.lexical_weight = lexical_weight

    def search(
        self,
        query: str,
        top_k: int = 10,
        dense_top_k: int = 25,
        bm25_top_k: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval:
        1. Embeds query & searches Qdrant
        2. Queries BM25 index
        3. Merges via Reciprocal Rank Fusion (RRF)
        """
        logger.info("Executing hybrid search for query: '%s'", query)

        # 1. Dense search
        dense_results = []
        try:
            query_vector = self.embedding_manager.embed_query(query)
            dense_results = self.vector_store.search(
                query_vector=query_vector,
                top_k=dense_top_k,
                filters=filters
            )
        except Exception as e:
            logger.warning("Dense search encountered an error, falling back to lexical: %s", e)

        # 2. BM25 search
        bm25_results = self.bm25_index.search(query=query, top_k=bm25_top_k)

        # 3. Reciprocal Rank Fusion
        rrf_scores: Dict[str, float] = {}
        items_by_id: Dict[str, Dict[str, Any]] = {}
        ranks_dense: Dict[str, int] = {}
        ranks_bm25: Dict[str, int] = {}

        for rank, res in enumerate(dense_results, start=1):
            cid = res["chunk_id"]
            items_by_id[cid] = res
            ranks_dense[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (self.dense_weight / (self.rrf_k + rank))

        for rank, res in enumerate(bm25_results, start=1):
            cid = res["chunk_id"]
            if cid not in items_by_id:
                items_by_id[cid] = res
            ranks_bm25[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (self.lexical_weight / (self.rrf_k + rank))

        # Sort by RRF score descending
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

        merged_results = []
        for cid in sorted_chunk_ids:
            item = items_by_id[cid]
            item_copy = dict(item)
            item_copy["rrf_score"] = rrf_scores[cid]
            item_copy["dense_rank"] = ranks_dense.get(cid)
            item_copy["bm25_rank"] = ranks_bm25.get(cid)
            merged_results.append(item_copy)

        logger.info("Hybrid search returned %d merged chunks.", len(merged_results))
        return merged_results
