import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import VectorStoreConfig

logger = logging.getLogger(__name__)

class QdrantStore:
    """Manages legal chunk vectors and metadata payloads in Qdrant."""

    def __init__(self, config: Optional[VectorStoreConfig] = None):
        self.config = config or VectorStoreConfig()
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initializes the Qdrant client (local embedded disk or remote)."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError:
            raise ImportError("qdrant-client is not installed. Please install it via 'pip install qdrant-client'.")

        if self.config.use_remote:
            logger.info("Connecting to remote Qdrant at %s", self.config.remote_url)
            self.client = QdrantClient(
                url=self.config.remote_url,
                api_key=self.config.api_key if self.config.api_key else None
            )
        else:
            self.config.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info("Using embedded local Qdrant at %s", self.config.storage_path)
            self.client = QdrantClient(path=str(self.config.storage_path))

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Creates the Qdrant collection if it does not exist."""
        from qdrant_client.models import Distance, VectorParams

        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]

        if self.config.collection_name not in collection_names:
            metric = Distance.COSINE
            if self.config.distance_metric.lower() == "dot":
                metric = Distance.DOT
            elif self.config.distance_metric.lower() == "euclid":
                metric = Distance.EUCLID

            logger.info(
                "Creating collection '%s' with dimension %d and metric %s",
                self.config.collection_name, self.config.vector_size, self.config.distance_metric
            )
            self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(
                    size=self.config.vector_size,
                    distance=metric
                )
            )
        else:
            logger.info("Collection '%s' already exists in Qdrant.", self.config.collection_name)

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]], batch_size: int = 100):
        """
        Upserts chunk vectors and payload metadata into Qdrant.
        `chunks` is a list of dictionary representations of LegalChunks.
        """
        from qdrant_client.models import PointStruct

        total = len(chunks)
        logger.info("Upserting %d chunk points into collection '%s'...", total, self.config.collection_name)

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            chunk_id = chunk.get("chunk_id", f"chunk_{i}")
            
            # Use deterministic hash or sequential integer / UUID for point id
            point_id = hash(chunk_id) & 0x7FFFFFFFFFFFFFFF # positive 64-bit int
            
            payload = {
                "chunk_id": chunk_id,
                "doc_id": chunk.get("doc_id"),
                "rule_id": chunk.get("doc_id"),
                "chunk_type": chunk.get("chunk_type"),
                "article_number": chunk.get("article_number"),
                "clause_number": chunk.get("clause_number"),
                "note_number": chunk.get("note_number"),
                "section_path": chunk.get("section_path", []),
                "header": chunk.get("header", ""),
                "content": chunk.get("content", ""),
                "full_text": chunk.get("full_text", ""),
                "token_count": chunk.get("token_count", 0),
                "parent_rule_id": chunk.get("parent_rule_id"),
                "rule_title": chunk.get("rule_title", ""),
                "category_title": chunk.get("category_title", ""),
                "approval_institution": chunk.get("approval_institution", ""),
                "approval_date": chunk.get("approval_date", ""),
                "status": chunk.get("status", "معتبر")
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

            if len(points) >= batch_size:
                self.client.upsert(
                    collection_name=self.config.collection_name,
                    points=points
                )
                points = []

        if points:
            self.client.upsert(
                collection_name=self.config.collection_name,
                points=points
            )

        logger.info("Successfully upserted %d chunk vectors.", total)

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search on Qdrant.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = None
        if filters:
            conditions = []
            for k, v in filters.items():
                if v is not None:
                    conditions.append(FieldCondition(key=k, match=MatchValue(value=v)))
            if conditions:
                query_filter = Filter(must=conditions)

        # qdrant_client query_points / search
        try:
            # Modern qdrant-client >= 1.10 uses query_points
            results = self.client.query_points(
                collection_name=self.config.collection_name,
                query=query_vector,
                limit=top_k,
                query_filter=query_filter
            ).points
        except AttributeError:
            results = self.client.search(
                collection_name=self.config.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter
            )

        formatted_results = []
        for point in results:
            formatted_results.append({
                "score": float(point.score),
                "chunk_id": point.payload.get("chunk_id"),
                "doc_id": point.payload.get("doc_id"),
                "chunk_type": point.payload.get("chunk_type"),
                "article_number": point.payload.get("article_number"),
                "header": point.payload.get("header"),
                "content": point.payload.get("content"),
                "full_text": point.payload.get("full_text"),
                "section_path": point.payload.get("section_path"),
                "rule_title": point.payload.get("rule_title"),
                "approval_institution": point.payload.get("approval_institution"),
                "status": point.payload.get("status"),
                "payload": point.payload
            })

        return formatted_results

    def count(self) -> int:
        """Returns the total number of points in the collection."""
        res = self.client.count(collection_name=self.config.collection_name)
        return res.count
