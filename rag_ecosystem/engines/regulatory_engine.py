import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..base import BaseRAGEngine

logger = logging.getLogger(__name__)

class RegulatoryRAGEngine(BaseRAGEngine):
    """
    RAG Engine for Iranian Capital Market Regulations (Securities and Exchange Organization - SEO).
    Combines:
      - Qdrant Vector Store
      - EmbeddingGemma-2 768d
      - BM25Plus Lexical Index
      - Sliding Window Chunks (900 tokens + 200 overlap)
      - Knowledge Graph Traversal (Amendments, Repeals, Hierarchy)
      - Default 'hybrid_weighted' similarity metric with alpha=0.7 and TOC filtering.
    """

    engine_id: str = "regulatory"
    display_name: str = "مقررات بازار سرمایه (سازمان بورس)"
    description: str = "استعلام و استناد به مصوبات، قوانین و دستورالعمل‌های تنقیح‌شده سازمان بورس با پشتیبانی از گراف دانش و الگوریتم ترکیبی وزن‌دار"
    icon: str = "scale"
    version: str = "2.0.0"
    enabled: bool = True

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(__file__).resolve().parent.parent.parent
        self._retriever = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        if self._initialized:
            return True

        # Ensure root dir is in sys.path
        root_str = str(self.root_dir.resolve())
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

        try:
            from vector_store.config import VectorStoreConfig
            from vector_store.client import QdrantStore
            from embeddings.manager import EmbeddingManager
            from search.bm25_index import BM25SearchIndex
            from search.hybrid_retriever import HybridRetriever
            from search.graph_retriever import GraphAugmentedRetriever
            from knowledge_graph.traverser import GraphTraverser

            qdrant_path = self.root_dir / "data" / "qdrant_db"
            bm25_path = self.root_dir / "data" / "search" / "bm25.pkl"
            graph_path = self.root_dir / "data" / "graph" / "graph.json"

            if not qdrant_path.exists() or not bm25_path.exists():
                logger.warning(f"Regulatory RAG indices not ready at: {qdrant_path} or {bm25_path}")
                return False

            vec_config = VectorStoreConfig(storage_path=qdrant_path, vector_size=768)
            qdrant = QdrantStore(config=vec_config)
            embed_mgr = EmbeddingManager(model_name="google/embeddinggemma-2", dimension=768)
            bm25 = BM25SearchIndex.load(bm25_path)

            hybrid = HybridRetriever(
                vector_store=qdrant,
                embedding_manager=embed_mgr,
                bm25_index=bm25,
                dense_weight=1.0,
                lexical_weight=1.0
            )

            if graph_path.exists():
                traverser = GraphTraverser.load_from_json(graph_path)
                self._retriever = GraphAugmentedRetriever(hybrid, traverser)
            else:
                self._retriever = hybrid

            self._initialized = True
            logger.info("RegulatoryRAGEngine successfully initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RegulatoryRAGEngine: {e}", exc_info=True)
            return False

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        mode: Optional[str] = None,
        alpha: Optional[float] = None,
        filter_toc: Optional[bool] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Executes hybrid search + knowledge graph traversal.
        """
        if not self._ensure_initialized():
            return None

        active_mode = (mode or os.getenv("RAG_MODE", "hybrid_weighted")).strip()
        active_alpha = alpha if alpha is not None else float(os.getenv("RAG_ALPHA", "0.7"))
        active_filter_toc = filter_toc if filter_toc is not None else (
            os.getenv("RAG_FILTER_TOC", "true").lower() in ("true", "1", "yes")
        )

        try:
            from search.graph_retriever import GraphAugmentedRetriever
            if isinstance(self._retriever, GraphAugmentedRetriever):
                res = self._retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    mode=active_mode,
                    alpha=active_alpha,
                    filter_toc=active_filter_toc
                )
                chunks = res.get("chunks", [])
                warnings = res.get("warnings", [])
                rag_context = res.get("rag_context", "")
            else:
                chunks = self._retriever.search(
                    query=query,
                    top_k=top_k,
                    mode=active_mode,
                    alpha=active_alpha,
                    filter_toc=active_filter_toc
                )
                warnings = []
                context_blocks = []
                for i, c in enumerate(chunks, 1):
                    context_blocks.append(f"--- [مستند {i}] ---\n{c.get('header','')}\n{c.get('full_text','')}")
                rag_context = "\n\n".join(context_blocks)

            formatted_sources = []
            for c in chunks:
                art = c.get("article_number")
                art_str = f"ماده {art}" if art else (c.get("chunk_type") or "متن مقرره")
                sec_path = c.get("section_path")
                sec_path_str = " > ".join(sec_path) if isinstance(sec_path, list) else str(sec_path or "")
                score_val = c.get("score")

                formatted_sources.append({
                    "chunk_id": c.get("chunk_id"),
                    "rule_title": c.get("rule_title") or "مصوبه سازمان بورس و اوراق بهادار",
                    "article": art_str,
                    "article_no": art,
                    "status": c.get("status") or "معتبر",
                    "section_path": sec_path_str,
                    "score": round(score_val, 3) if score_val is not None else None,
                    "similarity_mode": active_mode,
                    "alpha": active_alpha,
                    "is_toc": c.get("is_toc", False),
                    "snippet": (c.get("content") or c.get("full_text") or "")[:260] + "..."
                })

            return {
                "engine_id": self.engine_id,
                "engine_name": self.display_name,
                "rag_context": rag_context,
                "warnings": warnings,
                "sources": formatted_sources,
                "mode": active_mode,
                "alpha": active_alpha,
                "total_results": len(formatted_sources)
            }
        except Exception as e:
            logger.error(f"Error during regulatory RAG retrieval: {e}", exc_info=True)
            return None

    def health_check(self) -> Dict[str, Any]:
        """
        Verify storage paths and readiness.
        """
        qdrant_path = self.root_dir / "data" / "qdrant_db"
        bm25_path = self.root_dir / "data" / "search" / "bm25.pkl"
        graph_path = self.root_dir / "data" / "graph" / "graph.json"

        return {
            "engine_id": self.engine_id,
            "initialized": self._initialized,
            "qdrant_ready": qdrant_path.exists(),
            "bm25_ready": bm25_path.exists(),
            "graph_ready": graph_path.exists(),
            "status": "healthy" if (qdrant_path.exists() and bm25_path.exists()) else "pending_indexing"
        }
