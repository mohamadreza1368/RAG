import logging
import os
import socket
from pathlib import Path
from typing import List, Union, Optional
import numpy as np

logger = logging.getLogger(__name__)

def setup_hf_proxy():
    """Detects and configures local proxy for Hugging Face downloads if available."""
    if not os.environ.get("HTTPS_PROXY") and not os.environ.get("HTTP_PROXY"):
        try:
            s = socket.socket()
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", 10808)) == 0:
                os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
                os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"
                logger.info("Automatically enabled proxy http://127.0.0.1:10808 for Hugging Face.")
            s.close()
        except Exception:
            pass

class EmbeddingManager:
    """
    Manages text embeddings using Hugging Face models like google/embeddinggemma-2.
    Supports task-specific prompt steering (query vs document) and dimensionality truncation (MRL).
    """

    def __init__(
        self,
        model_name: str = "google/embeddinggemma-2",
        dimension: int = 768,
        device: Optional[str] = None,
        normalize_embeddings: bool = True
    ):
        self.model_name = model_name
        self.dimension = dimension
        self.normalize_embeddings = normalize_embeddings
        self.device = device
        self.model = None

    def load_model(self):
        """Loads the embedding model."""
        if self.model is not None:
            return

        setup_hf_proxy()
        from sentence_transformers import SentenceTransformer

        local_model_path = Path("models/embeddinggemma-2")
        target_model = self.model_name
        if self.model_name == "google/embeddinggemma-2" and (local_model_path / "model.safetensors").exists():
            target_model = str(local_model_path.resolve())
            logger.info("Using local model directory: %s", target_model)

        logger.info("Loading embedding model '%s' (dimension=%d)...", target_model, self.dimension)
        try:
            self.model = SentenceTransformer(
                target_model,
                device=self.device,
                trust_remote_code=True
            )
            # If the model supports truncate_dim
            if hasattr(self.model, "truncate_dim") and self.dimension:
                self.model.truncate_dim = self.dimension
            logger.info("Successfully loaded embedding model '%s'.", self.model_name)
        except Exception as e:
            logger.error("Failed to load '%s': %s", self.model_name, e)
            raise e

    def embed_documents(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> List[List[float]]:
        """
        Generates vector embeddings for documents / chunks.
        Applies 'document' task instruction if available on the model.
        """
        self.load_model()
        if not texts:
            return []

        # Check if the model has a registered 'document' prompt
        kwargs = {
            "batch_size": batch_size,
            "show_progress_bar": show_progress,
            "normalize_embeddings": self.normalize_embeddings
        }
        
        # Check prompt support
        if hasattr(self.model, "prompts") and "document" in self.model.prompts:
            kwargs["prompt_name"] = "document"

        embeddings = self.model.encode(texts, **kwargs)
        
        # In case MRL slicing is needed manually
        if self.dimension and embeddings.shape[1] > self.dimension:
            embeddings = embeddings[:, :self.dimension]
            if self.normalize_embeddings:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / np.maximum(norms, 1e-12)

        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """
        Generates vector embedding for a single user query.
        Applies 'query' task instruction if available.
        """
        self.load_model()
        kwargs = {
            "normalize_embeddings": self.normalize_embeddings
        }
        if hasattr(self.model, "prompts") and "query" in self.model.prompts:
            kwargs["prompt_name"] = "query"

        embedding = self.model.encode(query, **kwargs)

        if self.dimension and len(embedding) > self.dimension:
            embedding = embedding[:self.dimension]
            if self.normalize_embeddings:
                norm = np.linalg.norm(embedding)
                embedding = embedding / max(norm, 1e-12)

        return embedding.tolist()
