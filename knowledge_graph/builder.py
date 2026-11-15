"""
ماژول ساخت گراف دانش قوانین و مقررات (Knowledge Graph Builder)
تبدیل خودکار اسناد خام، دسته‌بندی‌ها، مواد قانونی و روابط بین‌سندی به گراف جهت‌دار کامل (Multi-relational Directed Graph)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
import networkx as nx

from .ontology import (
    NodeType,
    RelationType,
    LINK_TYPE_MAPPING,
    GraphNode,
    GraphEdge,
)
from preprocessor.normalizer import clean_html, normalize_persian_text, extract_numeric_article

logger = logging.getLogger("regulatory_crawler")


class KnowledgeGraphBuilder:
    """سازنده گراف دانش قوانین، مقررات، مواد حقوقی و روابط تنقیحی"""

    def __init__(self):
        # نگهداری گره‌ها و یال‌ها
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        # شیء گراف NetworkX برای الگوریتم‌های گرافی و پیمایش
        self.graph = nx.DiGraph()

    def add_node(self, node: GraphNode) -> None:
        """افزودن گره به مخزن و گراف NetworkX"""
        self.nodes[node.id] = node
        self.graph.add_node(
            node.id,
            label=node.label.value,
            name=node.name,
            **node.properties
        )

    def add_edge(self, edge: GraphEdge) -> None:
        """افزودن یال به مخزن و گراف NetworkX"""
        self.edges.append(edge)
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation_type=edge.relation_type.value,
            label_fa=edge.label_fa,
            **edge.properties
        )

    def load_categories(self, categories_path: Path) -> None:
        """بارگذاری دسته‌بندی‌های موضوعی و ایجاد درخت رده‌بندی در گراف"""
        if not categories_path.exists():
            logger.warning(f"فایل دسته‌بندی‌ها یافت نشد: {categories_path}")
            return

        cat_list = json.loads(categories_path.read_text(encoding="utf-8"))
        logger.info(f"در حال ساخت گره‌های دسته‌بندی ({len(cat_list)} دسته)...")

        for cat in cat_list:
            cat_id = cat["id"]
            title = normalize_persian_text(cat.get("title") or f"دسته {cat_id}")
            node_id = f"cat_{cat_id}"

            cat_node = GraphNode(
                id=node_id,
                label=NodeType.CATEGORY,
                name=title,
                properties={
                    "category_id": cat_id,
                    "order": cat.get("order", 0)
                }
            )
            self.add_node(cat_node)

        # ایجاد یال‌های سلسله‌مراتب دسته‌بندی‌ها
        for cat in cat_list:
            parent_id = cat.get("parentId")
            if parent_id:
                source_id = f"cat_{parent_id}"
                target_id = f"cat_{cat['id']}"
                if source_id in self.nodes and target_id in self.nodes:
                    self.add_edge(GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relation_type=RelationType.PARENT_CATEGORY_OF,
                        label_fa="شامل زیردسته"
                    ))

    def load_document_package(self, doc_data: dict) -> None:
        """
        تبدیل کامل یک پکیج سند به زیرگراف شامل:
        سند ⬅️ نسخه ⬅️ مرجع تصویب ⬅️ مواد و تبصره‌ها ⬅️ پیوست‌ها ⬅️ روابط بین‌سندی (نسخ، اصلاح و...)
        """
        rule_id = doc_data["rule_id"]
        source_url = doc_data.get("source_url") or f"https://cmr.seo.ir/ShowRules?Id={rule_id}"
        rule_info = doc_data.get("rule_info") or {}
        active_version = doc_data.get("active_version") or {}

        # ۱. گره سند اصلی (DocumentNode)
        title = active_version.get("title") or rule_info.get("title") or f"سند {rule_id}"
        normalized_title = normalize_persian_text(title)
        doc_node_id = f"doc_{rule_id}"

        doc_type = None
        if rule_info.get("ruleType"):
            doc_type = rule_info["ruleType"].get("title")

        doc_node = GraphNode(
            id=doc_node_id,
            label=NodeType.DOCUMENT,
            name=normalized_title,
            properties={
                "rule_id": rule_id,
                "document_type": doc_type,
                "source_url": source_url,
                "raw_title": title,
            }
        )
        self.add_node(doc_node)

        # اتصال به دسته‌بندی موضوعی
        category_id = doc_data.get("category_id") or rule_info.get("categoryId")
        if category_id:
            cat_node_id = f"cat_{category_id}"
            if cat_node_id in self.nodes:
                self.add_edge(GraphEdge(
                    source_id=doc_node_id,
                    target_id=cat_node_id,
                    relation_type=RelationType.BELONGS_TO_CATEGORY,
                    label_fa="متعلق به دسته"
                ))

        # ۲. گره مرجع تصویب (AuthorityNode)
        authority_name = None
        app_inst = active_version.get("approvalInstitution")
        if isinstance(app_inst, dict):
            authority_name = app_inst.get("title")
        elif isinstance(app_inst, str):
            authority_name = app_inst

        if authority_name:
            auth_title = normalize_persian_text(authority_name)
            auth_node_id = f"auth_{hash(auth_title) & 0xffffffff}"
            if auth_node_id not in self.nodes:
                self.add_node(GraphNode(
                    id=auth_node_id,
                    label=NodeType.AUTHORITY,
                    name=auth_title
                ))
            # یال صدور سند توسط مرجع
            self.add_edge(GraphEdge(
                source_id=doc_node_id,
                target_id=auth_node_id,
                relation_type=RelationType.ISSUED_BY,
                label_fa="تصویب‌شده توسط"
            ))

        # ۳. گره نسخه سند (VersionNode)
        version_id = active_version.get("id")
        ver_node_id = f"ver_{version_id}" if version_id else f"ver_def_{rule_id}"

        # استخراج وضعیت تنقیحی
        status_name = None
        t_stat = active_version.get("tanghihStatus")
        if isinstance(t_stat, dict):
            status_name = t_stat.get("title")
        elif isinstance(t_stat, str):
            status_name = t_stat

        ver_node = GraphNode(
            id=ver_node_id,
            label=NodeType.VERSION,
            name=f"نسخه {active_version.get('version', 'اصلی')} - {normalized_title[:40]}...",
            properties={
                "version_number": active_version.get("version"),
                "approval_date": active_version.get("approvalDate"),
                "status": status_name,
                "is_released": active_version.get("isReleased", True)
            }
        )
        self.add_node(ver_node)

        # یال انتساب نسخه به سند
        self.add_edge(GraphEdge(
            source_id=doc_node_id,
            target_id=ver_node_id,
            relation_type=RelationType.HAS_VERSION,
            label_fa="دارای نسخه"
        ))

        # ۴. گره‌های پیوست‌ها (AttachmentNode)
        for att in doc_data.get("attachments", []):
            att_id = att.get("id")
            att_name = att.get("name") or f"پیوست {att_id}"
            att_node_id = f"att_{att_id}"

            att_node = GraphNode(
                id=att_node_id,
                label=NodeType.ATTACHMENT,
                name=att_name,
                properties={
                    "file_id": att_id,
                    "file_type": att.get("fileType"),
                    "local_path": att.get("local_path"),
                    "file_size": att.get("file_size_bytes")
                }
            )
            self.add_node(att_node)

            self.add_edge(GraphEdge(
                source_id=ver_node_id,
                target_id=att_node_id,
                relation_type=RelationType.HAS_ATTACHMENT,
                label_fa="دارای پیوست رسمی"
            ))

        # ۵. گره‌های فصول، مواد، بندها و تبصره‌ها (Legal Articles & Sections)
        raw_parts = doc_data.get("parts") or []
        parts_by_id = {p["id"]: p for p in raw_parts}

        for p in raw_parts:
            p_id = p["id"]
            p_type_raw = p.get("rulePartType") or "ماده"
            p_title = normalize_persian_text(p.get("title") or "")
            p_body_norm = normalize_persian_text(p.get("body") or "")

            # تشخیص نوع گره حقوقی
            if p_type_raw in ["فصل", "بخش"]:
                node_label = NodeType.SECTION
                edge_to_parent_type = RelationType.HAS_SECTION
                edge_label_fa = "دارای بخش/فصل"
            elif p_type_raw == "تبصره":
                node_label = NodeType.NOTE
                edge_to_parent_type = RelationType.HAS_NOTE
                edge_label_fa = "دارای تبصره"
            elif p_type_raw == "بند":
                node_label = NodeType.CLAUSE
                edge_to_parent_type = RelationType.HAS_CLAUSE
                edge_label_fa = "دارای بند"
            else:
                node_label = NodeType.ARTICLE
                edge_to_parent_type = RelationType.HAS_ARTICLE
                edge_label_fa = "دارای ماده"

            part_node_id = f"part_{p_id}"
            part_node = GraphNode(
                id=part_node_id,
                label=node_label,
                name=p_title if p_title else f"{p_type_raw} {p_id}",
                properties={
                    "part_id": p_id,
                    "rule_id": rule_id,
                    "section_type": p_type_raw,
                    "article_number": extract_numeric_article(p_title),
                    "content": p_body_norm,
                    "raw_body": p.get("body", ""),
                    "order_no": p.get("orderNo", 0),
                    "status": p.get("tanghihStatusTitle")
                }
            )
            self.add_node(part_node)

            # اتصال به والد ساختاری:
            parent_id = p.get("parentId")
            if parent_id and parent_id in parts_by_id:
                # اگر پدر دارد به گره پدرش متصل می‌شود
                parent_node_id = f"part_{parent_id}"
                self.add_edge(GraphEdge(
                    source_id=parent_node_id,
                    target_id=part_node_id,
                    relation_type=edge_to_parent_type,
                    label_fa=edge_label_fa
                ))
            else:
                # اگر در سطح ریشه است به خود نسخه متصل می‌شود
                self.add_edge(GraphEdge(
                    source_id=ver_node_id,
                    target_id=part_node_id,
                    relation_type=edge_to_parent_type,
                    label_fa=edge_label_fa
                ))

        # ۶. یال‌های روابط بین‌سندی و تنقیحی (AMENDS, REPEALS, RELATED_TO)
        for dep in doc_data.get("dependencies", []):
            dep_id = dep.get("id")
            link_type_code = dep.get("linkType")
            dep_ver = dep.get("dependentVersion") or {}
            target_ver_id = dep_ver.get("id")
            target_title = normalize_persian_text(dep_ver.get("title") or "سند نامشخص")

            rel_type, rel_label_fa = LINK_TYPE_MAPPING.get(
                link_type_code,
                (RelationType.RELATED_TO, "مرتبط با")
            )

            # شناسه گره مقصد در گراف
            target_node_id = f"ver_{target_ver_id}" if target_ver_id else f"doc_ext_{dep_id}"

            # اگر گره مقصد هنوز در گراف ایجاد نشده باشد، یک گره موقت با عنوان رسمی اضافه می‌کنیم
            if target_node_id not in self.nodes:
                self.add_node(GraphNode(
                    id=target_node_id,
                    label=NodeType.DOCUMENT,
                    name=target_title,
                    properties={
                        "version_id": target_ver_id,
                        "description": clean_html(dep_ver.get("description")),
                        "is_stub": True
                    }
                ))

            # ایجاد یال اصلی رابطه حقوقی
            self.add_edge(GraphEdge(
                source_id=doc_node_id,
                target_id=target_node_id,
                relation_type=rel_type,
                label_fa=rel_label_fa,
                properties={
                    "dependency_id": dep_id,
                    "link_type_code": link_type_code,
                    "description": clean_html(dep_ver.get("description")),
                    "evidence_text": dep_ver.get("title")
                }
            ))

    def build_from_directory(self, raw_data_dir: Path) -> nx.DiGraph:
        """ساخت گراف جامع با خواندن تمام دسته‌بندی‌ها و اسناد موجود"""
        # ۱. بارگذاری دسته‌ها
        cat_file = raw_data_dir / "categories.json"
        if cat_file.exists():
            self.load_categories(cat_file)

        # ۲. بارگذاری اسناد خام
        rules_dir = raw_data_dir / "rules"
        doc_files = list(rules_dir.glob("*.json")) if rules_dir.exists() else []

        sample_file = raw_data_dir / "sample_71485.json"
        if sample_file.exists() and sample_file not in doc_files:
            doc_files.append(sample_file)

        logger.info(f"شروع ساخت گراف دانش از روی {len(doc_files)} سند خام...")
        for df in doc_files:
            try:
                data = json.loads(df.read_text(encoding="utf-8"))
                self.load_document_package(data)
            except Exception as e:
                logger.error(f"خطا در ایجاد گره‌های سند {df.name}: {e}")

        logger.info(
            f"✅ گراف دانش با موفقیت ساخته شد: "
            f"{self.graph.number_of_nodes()} گره و {self.graph.number_of_edges()} یال رابطه‌ای."
        )
        return self.graph

    def get_summary_statistics(self) -> Dict[str, Any]:
        """گزارش آماری دقیق از توزیع انواع گره‌ها و روابط در گراف"""
        node_counts: Dict[str, int] = {}
        for n in self.nodes.values():
            lbl = n.label.value
            node_counts[lbl] = node_counts.get(lbl, 0) + 1

        edge_counts: Dict[str, int] = {}
        for e in self.edges:
            rel = e.relation_type.value
            edge_counts[rel] = edge_counts.get(rel, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts
        }
