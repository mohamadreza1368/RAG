"""
ماژول جامع بازیابی ترکیبی و مقایسه معیارهای مشابهت (Hybrid Retriever & Similarity Evaluator)
پشتیبانی از انواع روش‌های سنجش مشابهت معنایی، لغوی و ترکیبی:
  1. Dense Cosine Similarity (زاویه کسینوسی بردارها)
  2. Dense Dot Product (حاصل‌ضرب برداری)
  3. Lexical BM25Plus (تطابق واژگانی و کلیدواژه‌ای دقیق)
  4. Hybrid RRF (ادغام رتبه‌ای متقابل - Reciprocal Rank Fusion)
  5. Hybrid Weighted Linear Combination (ترکیب خطی نرمال‌شده با ضریب آلفا)
  6. مقایسه جامع تمام معیارها به صورت همزمان (Side-by-Side Comparison)
"""

import logging
from typing import List, Dict, Any, Optional

from vector_store.client import QdrantStore
from embeddings.manager import EmbeddingManager
from .bm25_index import BM25SearchIndex

logger = logging.getLogger(__name__)


def is_toc_chunk(chunk: Dict[str, Any]) -> bool:
    """تشخیص چانک‌های فهرست مطالب یا مقدمات غیراصلی جهت جلوگیری از سوگیری نتایج"""
    if chunk.get("is_toc") or chunk.get("chunk_type") == "table_of_contents":
        return True
    
    sec_path = " > ".join(chunk.get("section_path") or [])
    if "فهرست مطالب" in sec_path or "فهرست عناوین" in sec_path:
        return True

    content = chunk.get("content") or chunk.get("full_text") or ""
    first_lines = "\n".join(content.splitlines()[:5])
    if "فهرست مطالب" in first_lines:
        return True

    return False


class HybridRetriever:
    """
    موتور جستجوی ترکیبی و ارزیابی معیارهای مختلف مشابهت حقوقی
    """

    def __init__(
        self,
        vector_store: QdrantStore,
        embedding_manager: EmbeddingManager,
        bm25_index: BM25SearchIndex,
        rrf_k: int = 60,
        dense_weight: float = 1.0,
        lexical_weight: float = 1.0
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.bm25_index = bm25_index
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.lexical_weight = lexical_weight

    # -------------------------------------------------------------
    # ۱. جستجوی معنایی برداری خالص (Dense Vector Search)
    # -------------------------------------------------------------
    def search_dense(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        filter_toc: bool = True
    ) -> List[Dict[str, Any]]:
        """جستجوی شباهت معنایی برداری (Cosine / Dot)"""
        try:
            query_vector = self.embedding_manager.embed_query(query)
            results = self.vector_store.search(
                query_vector=query_vector,
                top_k=top_k * 2 if filter_toc else top_k,
                filters=filters
            )
        except Exception as e:
            logger.warning("خطا در جستجوی وکتوری: %s", e)
            return []

        if filter_toc:
            filtered = [r for r in results if not is_toc_chunk(r)]
            results = filtered if filtered else results

        return results[:top_k]

    # -------------------------------------------------------------
    # ۲. جستجوی واژگانی خالص (Lexical BM25 Search)
    # -------------------------------------------------------------
    def search_lexical(
        self,
        query: str,
        top_k: int = 10,
        filter_toc: bool = True
    ) -> List[Dict[str, Any]]:
        """جستجوی واژگانی مبتنی بر کلمات کلیدی، عبارات و شماره مواد با BM25"""
        results = self.bm25_index.search(query=query, top_k=top_k * 2 if filter_toc else top_k)
        if filter_toc:
            filtered = [r for r in results if not is_toc_chunk(r)]
            results = filtered if filtered else results

        return results[:top_k]

    # -------------------------------------------------------------
    # ۳. جستجوی ترکیبی رتبه‌ای متقابل (Hybrid RRF)
    # -------------------------------------------------------------
    def search_hybrid_rrf(
        self,
        query: str,
        top_k: int = 10,
        dense_top_k: int = 25,
        bm25_top_k: int = 25,
        filters: Optional[Dict[str, Any]] = None,
        filter_toc: bool = True
    ) -> List[Dict[str, Any]]:
        """ادغام رتبه‌ای برداری و لغوی با الگوریتم Reciprocal Rank Fusion (مقاوم در برابر ناهمگونی توزیع امتیازها)"""
        dense_results = self.search_dense(query=query, top_k=dense_top_k, filters=filters, filter_toc=False)
        bm25_results = self.search_lexical(query=query, top_k=bm25_top_k, filter_toc=False)

        rrf_scores: Dict[str, float] = {}
        items_by_id: Dict[str, Dict[str, Any]] = {}
        ranks_dense: Dict[str, int] = {}
        ranks_bm25: Dict[str, int] = {}

        for rank, res in enumerate(dense_results, start=1):
            cid = res["chunk_id"]
            items_by_id[cid] = res
            ranks_dense[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (self.dense_weight / (self.rrf_k + rank))

        for rank, res in enumerate(bm25_results, start=1):
            cid = res["chunk_id"]
            if cid not in items_by_id:
                items_by_id[cid] = res
            ranks_bm25[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (self.lexical_weight / (self.rrf_k + rank))

        # مرتب‌سازی بر اساس RRF Score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        merged_results = []
        for cid in sorted_chunk_ids:
            item = items_by_id[cid]
            if filter_toc and is_toc_chunk(item):
                continue
            item_copy = dict(item)
            item_copy["rrf_score"] = rrf_scores[cid]
            item_copy["similarity_score"] = round(rrf_scores[cid], 5)
            item_copy["dense_rank"] = ranks_dense.get(cid)
            item_copy["bm25_rank"] = ranks_bm25.get(cid)
            item_copy["method"] = "Hybrid RRF"
            merged_results.append(item_copy)
            if len(merged_results) >= top_k:
                break

        return merged_results

    # -------------------------------------------------------------
    # ۴. جستجوی ترکیبی خطی با ضریب آلفا (Hybrid Weighted Linear)
    # -------------------------------------------------------------
    def search_hybrid_weighted(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.7,
        dense_top_k: int = 30,
        bm25_top_k: int = 30,
        filters: Optional[Dict[str, Any]] = None,
        filter_toc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        ترکیب خطی نرمال‌سازی‌شده امتیاز وکتور و BM25:
        Score = alpha * Normalized_Dense + (1 - alpha) * Normalized_BM25
        (alpha=0.7 یعنی ۷۰٪ سهم معنایی بردار و ۳۰٪ سهم تطابق واژگانی کلمات کلیدی)
        """
        dense_results = self.search_dense(query=query, top_k=dense_top_k, filters=filters, filter_toc=False)
        bm25_results = self.search_lexical(query=query, top_k=bm25_top_k, filter_toc=False)

        if not dense_results and not bm25_results:
            return []

        # ۱. نرمال‌سازی امتیازهای Dense (Min-Max)
        dense_scores = [r.get("score", 0.0) for r in dense_results] or [0.0]
        min_d, max_d = min(dense_scores), max(dense_scores)
        denom_d = (max_d - min_d) if (max_d - min_d) > 1e-6 else 1.0

        dense_map = {}
        items_by_id = {}
        for r in dense_results:
            cid = r["chunk_id"]
            items_by_id[cid] = r
            raw_s = float(r.get("score", 0.0))
            dense_map[cid] = (raw_s - min_d) / denom_d

        # ۲. نرمال‌سازی امتیازهای BM25 (Min-Max)
        bm25_scores = [r.get("score", 0.0) for r in bm25_results] or [0.0]
        min_b, max_b = min(bm25_scores), max(bm25_scores)
        denom_b = (max_b - min_b) if (max_b - min_b) > 1e-6 else 1.0

        bm25_map = {}
        for r in bm25_results:
            cid = r["chunk_id"]
            if cid not in items_by_id:
                items_by_id[cid] = r
            raw_s = float(r.get("score", 0.0))
            bm25_map[cid] = (raw_s - min_b) / denom_b

        # ۳. ادغام خطی با ضریب alpha
        combined_scores = {}
        for cid in items_by_id:
            s_dense = dense_map.get(cid, 0.0)
            s_bm25 = bm25_map.get(cid, 0.0)
            combined_scores[cid] = (alpha * s_dense) + ((1.0 - alpha) * s_bm25)

        sorted_cids = sorted(combined_scores.keys(), key=lambda cid: combined_scores[cid], reverse=True)

        merged_results = []
        for cid in sorted_cids:
            item = items_by_id[cid]
            if filter_toc and is_toc_chunk(item):
                continue
            item_copy = dict(item)
            item_copy["weighted_score"] = combined_scores[cid]
            item_copy["similarity_score"] = round(combined_scores[cid], 4)
            item_copy["norm_dense_score"] = round(dense_map.get(cid, 0.0), 4)
            item_copy["norm_bm25_score"] = round(bm25_map.get(cid, 0.0), 4)
            item_copy["method"] = f"Hybrid Weighted (α={alpha})"
            merged_results.append(item_copy)
            if len(merged_results) >= top_k:
                break

        return merged_results

    # -------------------------------------------------------------
    # ۵. توزیع‌کننده عمومی جستجو (General Unified Search)
    # -------------------------------------------------------------
    def search(
        self,
        query: str,
        mode: str = "hybrid_rrf",
        top_k: int = 10,
        alpha: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        filter_toc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        اجرای جستجو با معیار مشابهت انتخابی:
          - 'hybrid_rrf': ترکیب رتبه‌ای وکتور + BM25 (پیش‌فرض)
          - 'hybrid_weighted': ترکیب خطی وزن‌دار با ضریب alpha
          - 'cosine' / 'dense': شباهت برداری کسینوسی خالص
          - 'bm25' / 'lexical': تطابق دقیق کلمات کلیدی با BM25
        """
        clean_mode = (mode or "hybrid_rrf").lower().strip()

        if clean_mode in ["hybrid_rrf", "rrf"]:
            return self.search_hybrid_rrf(query=query, top_k=top_k, filters=filters, filter_toc=filter_toc)

        elif clean_mode in ["hybrid_weighted", "weighted", "alpha"]:
            return self.search_hybrid_weighted(query=query, top_k=top_k, alpha=alpha, filters=filters, filter_toc=filter_toc)

        elif clean_mode in ["cosine", "dense", "vector"]:
            dense_res = self.search_dense(query=query, top_k=top_k, filters=filters, filter_toc=filter_toc)
            for r in dense_res:
                r["method"] = "Dense Vector (Cosine)"
                r["similarity_score"] = round(float(r.get("score", 0)), 4)
            return dense_res

        elif clean_mode in ["bm25", "lexical", "keyword"]:
            lex_res = self.search_lexical(query=query, top_k=top_k, filter_toc=filter_toc)
            for r in lex_res:
                r["method"] = "Lexical BM25Plus"
                r["similarity_score"] = round(float(r.get("score", 0)), 4)
            return lex_res

        else:
            logger.warning("حالت جستجوی ناشناخته '%s'؛ استفاده از حالت پیش‌فرض hybrid_rrf", mode)
            return self.search_hybrid_rrf(query=query, top_k=top_k, filters=filters, filter_toc=filter_toc)

    # -------------------------------------------------------------
    # ۶. ابزار مقایسه همزمان تمام معیارهای مشابهت (Side-by-Side Comparison)
    # -------------------------------------------------------------
    def compare_all(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        filter_toc: bool = True
    ) -> Dict[str, Any]:
        """
        اجرای یک پرسش بر روی تمام معیارهای شباهت به صورت موازی و تولید ماتریس مقایسه:
          1. Dense Cosine
          2. BM25 Lexical
          3. Hybrid RRF
          4. Hybrid Weighted (Alpha)
        """
        logger.info("در حال اجرای مقایسه چندگانه معیارهای مشابهت برای: '%s'", query)

        res_dense = self.search(query=query, mode="dense", top_k=top_k, filters=filters, filter_toc=filter_toc)
        res_bm25 = self.search(query=query, mode="bm25", top_k=top_k, filters=filters, filter_toc=filter_toc)
        res_rrf = self.search(query=query, mode="hybrid_rrf", top_k=top_k, filters=filters, filter_toc=filter_toc)
        res_weighted = self.search(query=query, mode="hybrid_weighted", top_k=top_k, alpha=alpha, filters=filters, filter_toc=filter_toc)

        # استخراج چانک‌های مشترک بین تمام روش‌ها (Consensus / Overlap Analysis)
        ids_dense = set(r["chunk_id"] for r in res_dense)
        ids_bm25 = set(r["chunk_id"] for r in res_bm25)
        ids_rrf = set(r["chunk_id"] for r in res_rrf)
        ids_weighted = set(r["chunk_id"] for r in res_weighted)

        consensus_ids = ids_dense.intersection(ids_bm25)

        return {
            "query": query,
            "top_k": top_k,
            "metrics": {
                "dense_cosine": res_dense,
                "lexical_bm25": res_bm25,
                "hybrid_rrf": res_rrf,
                "hybrid_weighted": res_weighted
            },
            "consensus_count": len(consensus_ids),
            "consensus_chunk_ids": list(consensus_ids)
        }
