import argparse
import logging
from pathlib import Path

from vector_store.config import VectorStoreConfig
from vector_store.client import QdrantStore
from embeddings.manager import EmbeddingManager
from search.bm25_index import BM25SearchIndex
from search.hybrid_retriever import HybridRetriever
from search.graph_retriever import GraphAugmentedRetriever
from knowledge_graph.traverser import GraphTraverser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SearchRunner")

def run_query(
    query: str,
    top_k: int = 5,
    model_name: str = "google/embeddinggemma-2",
    dim: int = 768,
    qdrant_path: Path = Path("data/qdrant_db"),
    bm25_path: Path = Path("data/search/bm25.pkl"),
    graph_path: Path = Path("data/graph/graph.json"),
    mode: str = "hybrid",
    with_graph: bool = True
):
    print("\n" + "=" * 80)
    print(f"🔍 Regulatory Legal Search Query: {query}")
    print(f"⚙️ Mode: {mode.upper()} | Model: {model_name} | Top K: {top_k}")
    print("=" * 80)

    # 1. Initialize Vector Store & Embeddings
    vec_config = VectorStoreConfig(storage_path=qdrant_path, vector_size=dim)
    qdrant = QdrantStore(config=vec_config)
    embed_mgr = EmbeddingManager(model_name=model_name, dimension=dim)

    # 2. Load BM25
    bm25 = BM25SearchIndex.load(bm25_path)

    # 3. Configure Weights according to mode
    dense_w = 1.0 if mode in ["hybrid", "vector"] else 0.0
    bm25_w = 1.0 if mode in ["hybrid", "bm25"] else 0.0

    hybrid_retriever = HybridRetriever(
        vector_store=qdrant,
        embedding_manager=embed_mgr,
        bm25_index=bm25,
        dense_weight=dense_w,
        lexical_weight=bm25_w
    )

    if with_graph and graph_path.exists():
        traverser = GraphTraverser.load_from_json(graph_path)
        retriever = GraphAugmentedRetriever(hybrid_retriever, traverser)
        result = retriever.retrieve(query=query, top_k=top_k)
        chunks = result["chunks"]
        warnings = result.get("warnings", [])
    else:
        chunks = hybrid_retriever.search(query=query, top_k=top_k)
        warnings = []

    # Display Graph Warnings
    if warnings:
        print("\n⚠️ [هشدارهای حقوقی گراف دانش]:")
        for w in warnings:
            print(f"  • {w}")

    # Display Retrieved Results
    print(f"\n📋 [نتایج بازیابی شده ({len(chunks)} مورد)]:\n")
    for i, c in enumerate(chunks, 1):
        rrf = c.get("rrf_score", 0.0)
        drank = c.get("dense_rank", "-")
        brank = c.get("bm25_rank", "-")
        art = c.get("article_number")
        art_str = f"ماده {art}" if art else (c.get("chunk_type") or "متن")
        status = c.get("status") or "نامشخص"

        print(f"--- رتبه {i} | {art_str} (وضعیت: {status}) ---")
        print(f"امتیاز ترکیبی RRF: {rrf:.5f} [رتبه برداری: {drank} | رتبه متنی: {brank}]")
        print(f"شناسه چانک: {c.get('chunk_id')}")
        print(f"عنوان مصوبه: {c.get('rule_title')}")
        if c.get("section_path"):
            print(f"موقعیت ساختاری: {' > '.join(c['section_path'])}")
        
        grel = c.get("graph_relations")
        if grel:
            if grel.get("amended_by"):
                print("⚡ اصلاح‌شده توسط:", [x["title"] for x in grel["amended_by"]])
            if grel.get("repealed_by"):
                print("⛔ منسوخ‌شده توسط:", [x["title"] for x in grel["repealed_by"]])

        print(f"متن:\n{c.get('full_text') or c.get('content')}\n")

    print("=" * 80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the Regulatory Legal Knowledge RAG.")
    parser.add_argument("--query", "-q", type=str, required=True, help="Persian legal query")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of chunks to return")
    parser.add_argument("--model", type=str, default="google/embeddinggemma-2")
    parser.add_argument("--dim", type=int, default=768)
    parser.add_argument("--mode", choices=["hybrid", "vector", "bm25"], default="hybrid")
    parser.add_argument("--no-graph", action="store_true", help="Disable graph augmentation")
    parser.add_argument("--qdrant-path", type=Path, default=Path("data/qdrant_db"))
    parser.add_argument("--bm25-path", type=Path, default=Path("data/search/bm25.pkl"))
    parser.add_argument("--graph-path", type=Path, default=Path("data/graph/graph.json"))

    args = parser.parse_args()
    run_query(
        query=args.query,
        top_k=args.top_k,
        model_name=args.model,
        dim=args.dim,
        qdrant_path=args.qdrant_path,
        bm25_path=args.bm25_path,
        graph_path=args.graph_path,
        mode=args.mode,
        with_graph=not args.no_graph
    )
