import logging
from typing import List, Dict, Any, Optional

from knowledge_graph.traverser import GraphTraverser
from knowledge_graph.ontology import RelationType
from .hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)

class GraphAugmentedRetriever:
    """
    Combines Hybrid Search (Dense Vector + BM25) with Knowledge Graph traversal
    to provide legally accurate, relation-aware context for LLM generation.
    """

    def __init__(self, hybrid_retriever: HybridRetriever, traverser: GraphTraverser):
        self.hybrid_retriever = hybrid_retriever
        self.traverser = traverser

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        expand_hops: int = 1,
        include_amendments: bool = True
    ) -> Dict[str, Any]:
        """
        Executes hybrid search and enriches retrieved chunks with knowledge graph context.
        """
        # 1. Perform Hybrid Search
        chunks = self.hybrid_retriever.search(query=query, top_k=top_k)

        enriched_chunks = []
        doc_graph_contexts: Dict[int, Dict[str, Any]] = {}
        all_warnings: List[str] = []

        # 2. Graph Expansion for each unique document
        for chunk in chunks:
            doc_id = chunk.get("doc_id")
            if not doc_id:
                enriched_chunks.append(chunk)
                continue

            doc_node_id = f"doc_{doc_id}"
            if doc_id not in doc_graph_contexts:
                doc_amended_by = []
                doc_amends = []
                doc_repealed_by = []
                doc_repeals = []
                doc_references = []

                if doc_node_id in self.traverser.graph:
                    # Inbound relationships
                    for src, _, edge_data in self.traverser.graph.in_edges(doc_node_id, data=True):
                        etype = edge_data.get("relation_type")
                        src_node = self.traverser.graph.nodes.get(src, {})
                        src_title = src_node.get("name") or src_node.get("title") or src
                        if etype == RelationType.AMENDS.value:
                            doc_amended_by.append({"node_id": src, "title": src_title})
                            all_warnings.append(f"توجه: مصوبه «{chunk.get('rule_title')}» به موجب مصوبه «{src_title}» اصلاح شده است.")
                        elif etype == RelationType.REPEALS.value:
                            doc_repealed_by.append({"node_id": src, "title": src_title})
                            all_warnings.append(f"هشدار مهم حقوقی: مصوبه «{chunk.get('rule_title')}» به موجب مصوبه «{src_title}» لغو/منسوخ شده است.")

                    # Outbound relationships
                    for _, tgt, edge_data in self.traverser.graph.out_edges(doc_node_id, data=True):
                        etype = edge_data.get("relation_type")
                        tgt_node = self.traverser.graph.nodes.get(tgt, {})
                        tgt_title = tgt_node.get("name") or tgt_node.get("title") or tgt
                        if etype == RelationType.AMENDS.value:
                            doc_amends.append({"node_id": tgt, "title": tgt_title})
                        elif etype == RelationType.REPEALS.value:
                            doc_repeals.append({"node_id": tgt, "title": tgt_title})
                        elif etype == RelationType.REFERENCES.value:
                            doc_references.append({"node_id": tgt, "title": tgt_title})

                doc_graph_contexts[doc_id] = {
                    "doc_id": doc_id,
                    "title": chunk.get("rule_title"),
                    "amended_by": doc_amended_by,
                    "amends": doc_amends,
                    "repealed_by": doc_repealed_by,
                    "repeals": doc_repeals,
                    "references": doc_references
                }

            # Attach graph info to chunk
            chunk_copy = dict(chunk)
            chunk_copy["graph_relations"] = doc_graph_contexts[doc_id]
            enriched_chunks.append(chunk_copy)

        # 3. Format complete Context string for LLM RAG
        context_blocks = []
        for i, chunk in enumerate(enriched_chunks, 1):
            block = (
                f"--- [مستند شماره {i}] ---\n"
                f"{chunk.get('header', '')}\n"
                f"متن مصوبه / ماده: {chunk.get('full_text', '')}\n"
            )
            grel = chunk.get("graph_relations")
            if grel:
                if grel.get("amended_by"):
                    amended_str = ", ".join([x["title"] for x in grel["amended_by"]])
                    block += f"⚡ [وضعیت اصلاح]: این مصوبه طبق ({amended_str}) اصلاح شده است.\n"
                if grel.get("repealed_by"):
                    repealed_str = ", ".join([x["title"] for x in grel["repealed_by"]])
                    block += f"⛔ [وضعیت اعتبار]: این مصوبه طبق ({repealed_str}) منسوخ شده است!\n"
            context_blocks.append(block)

        rag_prompt_context = "\n\n".join(context_blocks)
        if all_warnings:
            unique_warnings = list(dict.fromkeys(all_warnings))
            rag_prompt_context = "### هشدارهای مهم گراف ارتباطات مصوبات:\n" + "\n".join(f"- {w}" for w in unique_warnings) + "\n\n" + rag_prompt_context

        return {
            "query": query,
            "chunks": enriched_chunks,
            "warnings": list(dict.fromkeys(all_warnings)),
            "graph_contexts": doc_graph_contexts,
            "rag_context": rag_prompt_context
        }
