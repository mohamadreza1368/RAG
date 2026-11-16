from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class RAGSourceItem(BaseModel):
    chunk_id: Optional[str] = None
    rule_title: str = "مستند قانونی"
    article: Optional[str] = None
    article_no: Optional[int] = None
    status: str = "معتبر"
    section_path: Optional[str] = ""
    score: Optional[float] = None
    similarity_mode: Optional[str] = None
    snippet: str = ""
    is_toc: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RAGRetrievalResponse(BaseModel):
    engine_id: str
    engine_name: str
    rag_context: str
    warnings: List[str] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    mode: str = "hybrid_weighted"
    alpha: Optional[float] = 0.7
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseRAGEngine(ABC):
    """
    Abstract Base Class for all RAG Engines in the Ecosystem.
    Any new domain RAG (e.g., Financial Reports, Legal Penal, Internal SOPs)
    must implement this interface to seamlessly plug into the ecosystem.
    """

    engine_id: str = "base"
    display_name: str = "موتور پایه RAG"
    description: str = "موتور بازیابی اطلاعات"
    icon: str = "layers"  # Lucide icon identifier (scale, book, file-text, etc.)
    version: str = "1.0.0"
    enabled: bool = True

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        mode: Optional[str] = None,
        alpha: Optional[float] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Execute retrieval for the given query and return a formatted dictionary
        matching RAGRetrievalResponse structure.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check connectivity to storage, indices, and models.
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        Return metadata describing this RAG engine.
        """
        return {
            "id": self.engine_id,
            "name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "version": self.version,
            "enabled": self.enabled,
        }
