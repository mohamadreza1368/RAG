import logging
from typing import Dict, Any, List, Optional
from .base import BaseRAGEngine

logger = logging.getLogger(__name__)

class RAGEcosystemRegistry:
    """
    Central Registry for managing and orchestrating multiple domain RAG engines.
    Provides dynamic discovery, unified retrieval dispatching, and health monitoring.
    """

    def __init__(self):
        self._engines: Dict[str, BaseRAGEngine] = {}
        self._default_engine_id: Optional[str] = None

    def register(self, engine: BaseRAGEngine, set_as_default: bool = False) -> None:
        """
        Register a new RAG engine in the ecosystem.
        """
        engine_id = engine.engine_id.lower().strip()
        self._engines[engine_id] = engine
        logger.info(f"Registered RAG Engine: '{engine.display_name}' (ID: {engine_id})")

        if set_as_default or self._default_engine_id is None:
            self._default_engine_id = engine_id

    def unregister(self, engine_id: str) -> bool:
        """
        Remove an engine from the registry.
        """
        clean_id = engine_id.lower().strip()
        if clean_id in self._engines:
            del self._engines[clean_id]
            if self._default_engine_id == clean_id:
                self._default_engine_id = next(iter(self._engines.keys())) if self._engines else None
            return True
        return False

    def get(self, engine_id: Optional[str] = None) -> Optional[BaseRAGEngine]:
        """
        Retrieve a registered RAG engine by ID, or return the default engine.
        """
        if not engine_id:
            engine_id = self._default_engine_id

        if not engine_id:
            return None

        clean_id = engine_id.lower().strip()
        return self._engines.get(clean_id)

    def list_engines(self) -> List[Dict[str, Any]]:
        """
        List all registered RAG engines and their metadata.
        """
        result = []
        for engine_id, engine in self._engines.items():
            info = engine.get_info()
            info["is_default"] = (engine_id == self._default_engine_id)
            result.append(info)
        return result

    def retrieve(
        self,
        query: str,
        engine_id: Optional[str] = None,
        top_k: int = 4,
        mode: Optional[str] = None,
        alpha: Optional[float] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Unified retrieval entry point. Dispatches the query to the designated engine.
        """
        engine = self.get(engine_id)
        if not engine:
            logger.error(f"RAG Engine '{engine_id}' not found in registry.")
            return None

        return engine.retrieve(query=query, top_k=top_k, mode=mode, alpha=alpha, **kwargs)

    def check_all_health(self) -> Dict[str, Any]:
        """
        Run health check across all registered engines.
        """
        status = {}
        for engine_id, engine in self._engines.items():
            status[engine_id] = engine.health_check()
        return status


# Global Singleton Instance for the Ecosystem
rag_registry = RAGEcosystemRegistry()
