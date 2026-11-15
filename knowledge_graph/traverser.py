"""
موتور پیمایش و توسعه چندمرحله‌ای گراف دانش (Multi-hop Graph Traversal & Relation Expansion)
مطابق با الزامات بخش ۱۲.۳ و ۱۲.۴ سند معماری regulatory_rag_design_roadmap.md
"""

from typing import List, Dict, Set, Optional, Any
import networkx as nx
from .ontology import RelationType, NodeType, GraphNode, GraphEdge


class GraphTraverser:
    """پیمایش گراف و استخراج زیرگراف مرتبط (Sub-graph Extraction) برای پاسخ‌گویی دقیق RAG"""

    def __init__(self, graph: nx.DiGraph, nodes_dict: Dict[str, GraphNode]):
        self.graph = graph
        self.nodes = nodes_dict

    def expand_document_context(self, rule_id: int, max_depth: int = 1) -> Dict[str, Any]:
        """
        توسعه گراف پیرامون یک سند:
        بازیابی اسناد نسخ‌کننده، اسناد اصلاح‌کننده، پیوست‌ها و مواد اصلی
        """
        doc_node_id = f"doc_{rule_id}"
        if doc_node_id not in self.graph:
            return {"error": f"سند {rule_id} در گراف یافت نشد."}

        doc_node = self.nodes.get(doc_node_id)

        # ۱. استخراج گره‌های نسخه و مرجع تصویب
        versions = []
        authorities = []
        categories = []
        attachments = []
        legal_relations = []  # روابط نسخ، اصلاح، ارجاع و ارتباط

        for target in self.graph.successors(doc_node_id):
            edge_data = self.graph.get_edge_data(doc_node_id, target)
            rel_type = edge_data.get("relation_type")
            target_node = self.nodes.get(target)
            if not target_node:
                continue

            if rel_type == RelationType.HAS_VERSION.value:
                versions.append(target_node.model_dump())
                # پیوست‌های متصل به نسخه
                for v_child in self.graph.successors(target):
                    v_edge = self.graph.get_edge_data(target, v_child)
                    if v_edge.get("relation_type") == RelationType.HAS_ATTACHMENT.value:
                        att_node = self.nodes.get(v_child)
                        if att_node:
                            attachments.append(att_node.model_dump())

            elif rel_type == RelationType.ISSUED_BY.value:
                authorities.append(target_node.model_dump())

            elif rel_type == RelationType.BELONGS_TO_CATEGORY.value:
                categories.append(target_node.model_dump())

            elif rel_type in [
                RelationType.REPEALS.value,
                RelationType.AMENDS.value,
                RelationType.RELATED_TO.value,
                RelationType.REFERENCES.value,
            ]:
                legal_relations.append({
                    "direction": "OUTBOUND",
                    "relation_type": rel_type,
                    "label_fa": edge_data.get("label_fa"),
                    "target_id": target,
                    "target_name": target_node.name,
                    "description": edge_data.get("description")
                })

        # ۲. روابط ورودی (اگر سندی دیگر این سند را نسخ یا اصلاح کرده باشد)
        for source in self.graph.predecessors(doc_node_id):
            edge_data = self.graph.get_edge_data(source, doc_node_id)
            rel_type = edge_data.get("relation_type")
            source_node = self.nodes.get(source)
            if not source_node:
                continue

            if rel_type in [
                RelationType.REPEALS.value,
                RelationType.AMENDS.value,
                RelationType.RELATED_TO.value,
                RelationType.REFERENCES.value,
            ]:
                legal_relations.append({
                    "direction": "INBOUND",
                    "relation_type": rel_type,
                    "label_fa": edge_data.get("label_fa"),
                    "source_id": source,
                    "source_name": source_node.name,
                    "description": edge_data.get("description")
                })

        # ۳. استخراج خلاصه مواد و فصول متصل
        articles = []
        for v in versions:
            v_id = v["id"]
            for child_id in self.graph.successors(v_id):
                child_node = self.nodes.get(child_id)
                if child_node and child_node.label in [NodeType.ARTICLE, NodeType.SECTION]:
                    # استخراج تبصره‌های متصل به ماده
                    sub_notes = []
                    for note_id in self.graph.successors(child_id):
                        n_node = self.nodes.get(note_id)
                        if n_node:
                            sub_notes.append({
                                "id": n_node.id,
                                "type": n_node.label.value,
                                "name": n_node.name,
                                "content": n_node.properties.get("content")
                            })

                    articles.append({
                        "id": child_node.id,
                        "type": child_node.label.value,
                        "name": child_node.name,
                        "article_number": child_node.properties.get("article_number"),
                        "content": child_node.properties.get("content"),
                        "notes": sub_notes
                    })

        return {
            "document": doc_node.model_dump() if doc_node else None,
            "categories": categories,
            "authorities": authorities,
            "attachments": attachments,
            "legal_relations": legal_relations,
            "total_articles": len(articles),
            "articles": articles
        }

    def find_legal_paths_between(self, start_id: str, end_id: str) -> List[List[Dict[str, Any]]]:
        """پیدا کردن کلیه مسیرهای ارتباطی و استنادی میان دو موجودیت در گراف"""
        if start_id not in self.graph or end_id not in self.graph:
            return []

        # تبدیل گراف به جهت‌ناپذیر برای کشف ارتباط در هر دو جهت
        undirected = self.graph.to_undirected()
        try:
            paths = list(nx.all_simple_paths(undirected, source=start_id, target=end_id, cutoff=3))
            formatted_paths = []
            for path in paths[:5]:
                nodes_info = [
                    {
                        "id": nid,
                        "label": self.nodes[nid].label.value,
                        "name": self.nodes[nid].name
                    }
                    for nid in path if nid in self.nodes
                ]
                formatted_paths.append(nodes_info)
            return formatted_paths
        except Exception:
            return []
