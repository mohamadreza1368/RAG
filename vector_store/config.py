from pathlib import Path
from pydantic import BaseModel, Field

class VectorStoreConfig(BaseModel):
    """Configuration for Qdrant Vector Store."""
    storage_path: Path = Field(
        default=Path("data/qdrant_db"),
        description="Local directory for embedded Qdrant database storage."
    )
    collection_name: str = Field(
        default="regulatory_legal_chunks",
        description="Qdrant collection name for regulatory chunks."
    )
    vector_size: int = Field(
        default=768,
        description="Dimension of the embedding vectors (e.g. 768 for embeddinggemma-2)."
    )
    distance_metric: str = Field(
        default="Cosine",
        description="Distance metric for similarity search (Cosine, Dot, Euclid)."
    )
    use_remote: bool = Field(
        default=False,
        description="Whether to connect to a remote Qdrant server."
    )
    remote_url: str = Field(
        default="http://localhost:6333",
        description="URL for remote Qdrant server if use_remote=True."
    )
    api_key: str = Field(
        default="",
        description="API key for cloud/remote Qdrant if applicable."
    )
