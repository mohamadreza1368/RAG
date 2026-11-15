import pickle
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from rank_bm25 import BM25Plus
from preprocessor.normalizer import PersianLegalNormalizer

logger = logging.getLogger(__name__)

class BM25SearchIndex:
    """
    BM25 Lexical Search Index tailored for Persian Legal texts and regulations.
    Supports Persian normalization, tokenization, and article number matching.
    """

    def __init__(self, normalizer: Optional[PersianLegalNormalizer] = None):
        self.normalizer = normalizer or PersianLegalNormalizer()
        self.bm25: Optional[BM25Plus] = None
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []

    def tokenize(self, text: str) -> List[str]:
        """Normalizes and tokenizes Persian legal text into search tokens."""
        if not text:
            return []

        # 1. Normalize
        normalized = self.normalizer.normalize(text)

        # 2. Extract words (Persian letters, digits, ZWNJ)
        tokens = re.findall(r"[\u0600-\u06FF\w]+", normalized.lower())

        # 3. Filter short meaningless tokens (len < 2) unless they are numbers (like ماده 1)
        cleaned_tokens = [t for t in tokens if len(t) >= 2 or t.isdigit()]
        return cleaned_tokens

    def build_index(self, chunks: List[Dict[str, Any]]):
        """Builds BM25 index over the provided chunks."""
        self.corpus_chunks = chunks
        self.tokenized_corpus = []

        logger.info("Tokenizing %d legal chunks for BM25 index...", len(chunks))
        for chunk in chunks:
            # Combine header, article number, and full text for rich lexical representation
            header = chunk.get("header", "")
            full_text = chunk.get("full_text", "")
            rule_title = chunk.get("rule_title", "")
            art_no = str(chunk.get("article_number") or "")

            text_to_index = f"{rule_title} {header} ماده {art_no} {full_text}"
            tokens = self.tokenize(text_to_index)
            self.tokenized_corpus.append(tokens)

        self.bm25 = BM25Plus(self.tokenized_corpus)
        logger.info("BM25 index successfully built with %d documents.", len(self.corpus_chunks))

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Executes BM25 search with a query and returns top_k scored chunks.
        """
        if not self.bm25 or not self.corpus_chunks:
            logger.warning("BM25 index is empty. Cannot perform search.")
            return []

        tokenized_query = self.tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        
        # Rank by score descending
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self.corpus_chunks[idx]
            results.append({
                "score": score,
                "chunk_id": chunk.get("chunk_id"),
                "doc_id": chunk.get("doc_id"),
                "chunk_type": chunk.get("chunk_type"),
                "article_number": chunk.get("article_number"),
                "header": chunk.get("header"),
                "content": chunk.get("content"),
                "full_text": chunk.get("full_text"),
                "section_path": chunk.get("section_path"),
                "rule_title": chunk.get("rule_title"),
                "approval_institution": chunk.get("approval_institution"),
                "status": chunk.get("status"),
                "payload": chunk
            })

        return results

    def save(self, filepath: Path):
        """Serializes the index and chunks to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({
                "chunks": self.corpus_chunks,
                "tokenized_corpus": self.tokenized_corpus,
                "bm25": self.bm25
            }, f)
        logger.info("Saved BM25 index to %s", filepath)

    @classmethod
    def load(cls, filepath: Path) -> "BM25SearchIndex":
        """Loads a pre-built BM25 index from disk."""
        instance = cls()
        with open(filepath, "rb") as f:
            data = pickle.load(f)
            instance.corpus_chunks = data["chunks"]
            instance.tokenized_corpus = data["tokenized_corpus"]
            instance.bm25 = data["bm25"]
        logger.info("Loaded BM25 index from %s (%d documents)", filepath, len(instance.corpus_chunks))
        return instance
