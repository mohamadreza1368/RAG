from .base import BaseRAGEngine, RAGSourceItem, RAGRetrievalResponse
from .registry import RAGEcosystemRegistry, rag_registry
from .engines.regulatory_engine import RegulatoryRAGEngine

# Auto-register standard ecosystem engines
regulatory_engine = RegulatoryRAGEngine()
rag_registry.register(regulatory_engine, set_as_default=True)

__all__ = [
    "BaseRAGEngine",
    "RAGSourceItem",
    "RAGRetrievalResponse",
    "RAGEcosystemRegistry",
    "rag_registry",
    "regulatory_engine"
]
