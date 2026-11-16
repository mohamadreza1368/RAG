"""
اسکریپت خط فرمان اجرای جستجوی پیشرفته حقوقی و مقایسه چندگانه معیارهای مشابهت
(Advanced Legal Search CLI & Multi-Metric Similarity Benchmark)
"""

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


def format_snippet(text: str, max_chars: int = 140) -> str:
    """خلاصه‌سازی تک‌خطی متن جهت نمایش جدولی"""
    clean = " ".join((text or "").split())
    if len(clean) > max_chars:
        return clean[:max_chars] + "..."
    return clean


def print_comparison_matrix(comparison_result: dict):
    """نمایش زیبای ماتریس مقایسه معیارهای مختلف مشابهت در کنار یکدیگر"""
    query = comparison_result["query"]
    metrics = comparison_result["metrics"]
    top_k = comparison_result["top_k"]

    print("\n" + "=" * 90)
    print(f"📊 ماتریس ارزیابی و مقایسه جامع معیارهای مشابهت (Side-by-Side Similarity Benchmark)")
    print(f"🔍 پرسش: «{query}»")
    print("=" * 90)

    method_titles = {
        "dense_cosine": "۱. برداری کسینوسی (Dense Cosine)",
        "lexical_bm25": "۲. واژگانی دقیق (BM25Plus)",
        "hybrid_rrf": "۳. ترکیب رتبه‌ای (Hybrid RRF)",
        "hybrid_weighted": "۴. ترکیب وزن‌دار خطی (Hybrid Weighted α=0.7)"
    }

    for method_key, method_label in method_titles.items():
        results = metrics.get(method_key, [])
        print(f"\n🔹 {method_label}:")
        print(f"{'رتبه':<5} | {'امتیاز':<10} | {'شماره ماده / بخش':<20} | {'عنوان مصوبه و متن'}")
        print("-" * 88)
        if not results:
            print("  (هیچ نتیجه‌ای یافت نشد)")
            continue

        for idx, r in enumerate(results, start=1):
            score = r.get("similarity_score", r.get("score", 0.0))
            art = r.get("article_number")
            art_str = f"ماده {art}" if art else (r.get("paragraph_number") or r.get("chunk_type") or "-")
            title = r.get("rule_title") or r.get("document_title") or ""
            snippet = format_snippet(r.get("content") or r.get("full_text") or "", 60)
            print(f"#{idx:<4} | {score:<10} | {art_str:<20} | {title} | {snippet}")

    consensus = comparison_result.get("consensus_chunk_ids", [])
    print("\n" + "-" * 90)
    print(f"💡 تحلیل همگرایی (Consensus Analysis):")
    print(f"  • تعداد چانک‌های مشترک بین روش برداری و روش واژگانی: {len(consensus)}")
    if consensus:
        print(f"  • چانک‌های دارای بالاترین قطعیت مشترک: {consensus[:3]}")
    print("=" * 90 + "\n")


def run_query(
    query: str,
    top_k: int = 5,
    model_name: str = "google/embeddinggemma-2",
    dim: int = 768,
    qdrant_path: Path = Path("data/qdrant_db"),
    bm25_path: Path = Path("data/search/bm25.pkl"),
    graph_path: Path = Path("data/graph/graph.json"),
    mode: str = "hybrid_rrf",
    alpha: float = 0.7,
    filter_toc: bool = True,
    compare_mode: bool = False,
    with_graph: bool = True
):
    # 1. Initialize Vector Store & Embeddings
    vec_config = VectorStoreConfig(storage_path=qdrant_path, vector_size=dim)
    qdrant = QdrantStore(config=vec_config)
    embed_mgr = EmbeddingManager(model_name=model_name, dimension=dim)

    # 2. Load BM25
    bm25 = BM25SearchIndex.load(bm25_path)

    # 3. Initialize Hybrid Retriever
    hybrid_retriever = HybridRetriever(
        vector_store=qdrant,
        embedding_manager=embed_mgr,
        bm25_index=bm25
    )

    # 4. If Comparison Mode is requested
    if compare_mode:
        comparison_res = hybrid_retriever.compare_all(
            query=query,
            top_k=top_k,
            alpha=alpha,
            filter_toc=filter_toc
        )
        print_comparison_matrix(comparison_res)
        return

    # 5. Single Mode Search (with optional Graph Augmentation)
    print("\n" + "=" * 80)
    print(f"🔍 Regulatory Legal Search Query: {query}")
    print(f"⚙️ Similarity Metric: {mode.upper()} | Alpha: {alpha} | Filter TOC: {filter_toc} | Top K: {top_k}")
    print("=" * 80)

    if with_graph and graph_path.exists():
        traverser = GraphTraverser.load_from_json(graph_path)
        retriever = GraphAugmentedRetriever(hybrid_retriever, traverser)
        result = retriever.retrieve(
            query=query,
            top_k=top_k,
            mode=mode,
            alpha=alpha,
            filter_toc=filter_toc
        )
        chunks = result["chunks"]
        warnings = result.get("warnings", [])
    else:
        chunks = hybrid_retriever.search(
            query=query,
            mode=mode,
            top_k=top_k,
            alpha=alpha,
            filter_toc=filter_toc
        )
        warnings = []

    # Display Graph Warnings
    if warnings:
        print("\n⚠️ [هشدارهای حقوقی گراف دانش]:")
        for w in warnings:
            print(f"  • {w}")

    # Display Retrieved Results
    print(f"\n📋 [نتایج بازیابی شده ({len(chunks)} مورد)]:\n")
    for i, c in enumerate(chunks, 1):
        score = c.get("similarity_score", c.get("score", 0.0))
        art = c.get("article_number")
        art_str = f"ماده {art}" if art else (c.get("paragraph_number") or c.get("chunk_type") or "متن")
        status = c.get("status") or "نامشخص"
        method = c.get("method", mode)

        print(f"--- رتبه {i} | {art_str} (وضعیت: {status}) ---")
        print(f"روش سنجش: {method} | امتیاز محاسبه‌شده: {score}")
        print(f"شناسه چانک: {c.get('chunk_id')}")
        print(f"عنوان مصوبه: {c.get('rule_title') or c.get('document_title')}")
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
    parser = argparse.ArgumentParser(description="Query the Regulatory Legal Knowledge RAG with multiple similarity metrics.")
    parser.add_argument("--query", "-q", type=str, required=True, help="Persian legal query")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of chunks to return")
    parser.add_argument("--model", type=str, default="google/embeddinggemma-2")
    parser.add_argument("--dim", type=int, default=768)
    parser.add_argument(
        "--mode",
        choices=["hybrid_weighted", "hybrid_rrf", "cosine", "dense", "bm25", "lexical"],
        default="hybrid_weighted",
        help="Similarity metric: hybrid_weighted (default), hybrid_rrf, cosine, bm25"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.7,
        help="Weight for dense vector similarity in hybrid_weighted mode (0.0 to 1.0, default: 0.7)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare all similarity metrics side-by-side for this query"
    )
    parser.add_argument(
        "--include-toc",
        action="store_true",
        help="Include table of contents (TOC) pages in search results (default: False)"
    )
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
        alpha=args.alpha,
        filter_toc=not args.include_toc,
        compare_mode=args.compare,
        with_graph=not args.no_graph
    )
