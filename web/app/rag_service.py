import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Ensure project root is in sys.path so rag_ecosystem and other modules are directly importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class EcosystemRAGService:
    """
    Unified RAG Gateway Service for Web Application.
    Connects to the RAG Ecosystem Registry, supporting multiple pluggable RAG domains.
    Default domain: 'regulatory' (Iranian Capital Market Regulations with Hybrid Weighted similarity).
    """

    def __init__(self):
        self._registry = None

    def _get_registry(self):
        if self._registry is None:
            try:
                from rag_ecosystem import rag_registry
                self._registry = rag_registry
            except Exception as e:
                logger.error(f"Failed to load RAG Ecosystem Registry: {e}", exc_info=True)
                return None
        return self._registry

    def list_engines(self) -> List[Dict[str, Any]]:
        """
        Return all registered domain RAG engines.
        """
        reg = self._get_registry()
        if not reg:
            return []
        return reg.list_engines()

    def retrieve(
        self,
        query: str,
        engine_id: Optional[str] = None,
        top_k: int = 4,
        mode: Optional[str] = None,
        alpha: Optional[float] = None,
        filter_toc: Optional[bool] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatches retrieval to the requested engine (or default engine).
        Defaults to 'hybrid_weighted' mode with alpha=0.7 and TOC filtering.
        """
        reg = self._get_registry()
        if not reg:
            logger.error("RAG Registry unavailable.")
            return None

        # Fallback to regulatory if engine_id is None or empty
        target_engine = engine_id or os.getenv("RAG_DEFAULT_ENGINE", "regulatory")
        active_mode = (mode or os.getenv("RAG_MODE", "hybrid_weighted")).strip()
        active_alpha = alpha if alpha is not None else float(os.getenv("RAG_ALPHA", "0.7"))
        active_filter_toc = filter_toc if filter_toc is not None else (
            os.getenv("RAG_FILTER_TOC", "true").lower() in ("true", "1", "yes")
        )

        return reg.retrieve(
            query=query,
            engine_id=target_engine,
            top_k=top_k,
            mode=active_mode,
            alpha=active_alpha,
            filter_toc=active_filter_toc,
            **kwargs
        )

# Global service instance
ecosystem_rag_service = EcosystemRAGService()
regulatory_rag_service = ecosystem_rag_service  # Backward compatibility alias
