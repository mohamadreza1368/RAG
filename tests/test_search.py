import unittest
import tempfile
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from search.bm25_index import BM25SearchIndex
from vector_store.config import VectorStoreConfig
from vector_store.client import QdrantStore
from search.hybrid_retriever import HybridRetriever
from search.graph_retriever import GraphAugmentedRetriever
from knowledge_graph.builder import KnowledgeGraphBuilder
from knowledge_graph.traverser import GraphTraverser
from knowledge_graph.ontology import RelationType, NodeType

class DummyEmbeddingManager:
    """Mock embedding manager for fast isolated unit tests."""
    def __init__(self, dim=4):
        self.dim = dim
    def embed_query(self, query: str):
        return [0.1] * self.dim
    def embed_documents(self, texts, batch_size=32, show_progress=False):
        return [[0.1 * (i + 1)] * self.dim for i in range(len(texts))]

class TestHybridAndGraphSearch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.qdrant_path = self.temp_dir / "test_qdrant"
        self.bm25_path = self.temp_dir / "test_bm25.pkl"

        # Create sample chunks
        self.sample_chunks = [
            {
                "chunk_id": "chunk_91_1",
                "doc_id": 91,
                "rule_title": "دستورالعمل نهادهای مالی",
                "chunk_type": "article",
                "article_number": 1,
                "header": "[سند: دستورالعمل نهادهای مالی | مرجع: سازمان بورس | ماده: ۱]",
                "content": "ثبت نهادهای مالی نزد سازمان بورس الزامی است.",
                "full_text": "[سند: دستورالعمل نهادهای مالی | مرجع: سازمان بورس | ماده: ۱]\nثبت نهادهای مالی نزد سازمان بورس الزامی است.",
                "section_path": ["فصل اول", "ماده ۱"],
                "status": "معتبر"
            },
            {
                "chunk_id": "chunk_92_1",
                "doc_id": 92,
                "rule_title": "اصلاحیه دستورالعمل نهادهای مالی",
                "chunk_type": "article",
                "article_number": 1,
                "header": "[سند: اصلاحیه دستورالعمل | مرجع: سازمان بورس | ماده: ۱]",
                "content": "ماده ۱ دستورالعمل نهادهای مالی مصوب ۹۱ لغو و این متن جایگزین می‌شود.",
                "full_text": "[سند: اصلاحیه دستورالعمل | مرجع: سازمان بورس | ماده: ۱]\nماده ۱ دستورالعمل نهادهای مالی مصوب ۹۱ لغو و این متن جایگزین می‌شود.",
                "section_path": ["ماده ۱"],
                "status": "معتبر"
            }
        ]

        # Build sample knowledge graph
        self.builder = KnowledgeGraphBuilder()
        self.builder.graph.add_node("doc_91", node_type=NodeType.DOCUMENT.value, title="دستورالعمل نهادهای مالی", doc_id=91)
        self.builder.graph.add_node("doc_92", node_type=NodeType.DOCUMENT.value, title="اصلاحیه دستورالعمل نهادهای مالی", doc_id=92)
        # Doc 92 amends/repeals Doc 91
        self.builder.graph.add_edge("doc_92", "doc_91", relation_type=RelationType.AMENDS.value, note="اصلاح ماده ۱")
        self.builder.graph.add_edge("doc_92", "doc_91", relation_type=RelationType.REPEALS.value, note="لغو ماده ۱ قبلی")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bm25_index(self):
        index = BM25SearchIndex()
        index.build_index(self.sample_chunks)
        index.save(self.bm25_path)

        loaded_index = BM25SearchIndex.load(self.bm25_path)
        results = loaded_index.search("نهادهای مالی سازمان بورس", top_k=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["chunk_id"], "chunk_91_1")

    def test_qdrant_and_hybrid_retriever(self):
        # 1. BM25
        bm25 = BM25SearchIndex()
        bm25.build_index(self.sample_chunks)

        # 2. Qdrant
        vec_config = VectorStoreConfig(storage_path=self.qdrant_path, vector_size=4)
        store = QdrantStore(config=vec_config)
        embed_mgr = DummyEmbeddingManager(dim=4)
        vectors = embed_mgr.embed_documents(["text 1", "text 2"])
        store.upsert_chunks(self.sample_chunks, vectors)

        self.assertEqual(store.count(), 2)

        # 3. Hybrid search
        hybrid = HybridRetriever(
            vector_store=store,
            embedding_manager=embed_mgr,
            bm25_index=bm25
        )
        hybrid_results = hybrid.search(query="ثبت نهادهای مالی", top_k=2)
        self.assertEqual(len(hybrid_results), 2)
        self.assertIn("rrf_score", hybrid_results[0])

    def test_graph_augmented_retriever(self):
        bm25 = BM25SearchIndex()
        bm25.build_index(self.sample_chunks)

        vec_config = VectorStoreConfig(storage_path=self.qdrant_path, vector_size=4)
        store = QdrantStore(config=vec_config)
        embed_mgr = DummyEmbeddingManager(dim=4)
        vectors = embed_mgr.embed_documents(["text 1", "text 2"])
        store.upsert_chunks(self.sample_chunks, vectors)

        hybrid = HybridRetriever(vector_store=store, embedding_manager=embed_mgr, bm25_index=bm25)
        traverser = GraphTraverser(self.builder.graph)
        graph_retriever = GraphAugmentedRetriever(hybrid, traverser)

        res = graph_retriever.retrieve(query="ثبت نهادهای مالی", top_k=2)
        self.assertIn("chunks", res)
        self.assertIn("rag_context", res)
        # Should generate legal warning that Doc 91 is amended/repealed by Doc 92
        self.assertTrue(len(res["warnings"]) > 0)
        print("Generated Warnings:", res["warnings"])

if __name__ == "__main__":
    unittest.main()
