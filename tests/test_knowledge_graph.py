"""
آزمون‌های اعتبارسنجی ماژول گراف دانش (Knowledge Graph Test Suite)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graph.builder import KnowledgeGraphBuilder
from knowledge_graph.traverser import GraphTraverser
from knowledge_graph.ontology import NodeType, RelationType


def test_knowledge_graph_construction():
    print("\n--- ۱. تست ساخت گراف دانش از فایل‌های خام ---")
    builder = KnowledgeGraphBuilder()
    raw_dir = Path("data/raw")
    graph = builder.build_from_directory(raw_dir)

    stats = builder.get_summary_statistics()
    print(f"تعداد گره‌ها: {stats['total_nodes']}")
    print(f"تعداد یال‌ها: {stats['total_edges']}")

    assert stats["total_nodes"] > 50, "حداقل ۵۰ گره باید در گراف باشد"
    assert stats["total_edges"] > 50, "حداقل ۵۰ یال باید در گراف باشد"
    assert NodeType.DOCUMENT.value in stats["nodes_by_type"]
    assert NodeType.ARTICLE.value in stats["nodes_by_type"]
    assert RelationType.REPEALS.value in stats["edges_by_type"]

    print("✅ تست ساخت گراف دانش با موفقیت پاس شد.")


def test_relation_expansion():
    print("\n--- ۲. تست پیمایش و توسعه روابط (Relation Expansion) ---")
    builder = KnowledgeGraphBuilder()
    raw_dir = Path("data/raw")
    builder.build_from_directory(raw_dir)

    traverser = GraphTraverser(builder.graph, builder.nodes)
    expansion = traverser.expand_document_context(71485)

    assert "document" in expansion and expansion["document"] is not None
    assert len(expansion["legal_relations"]) >= 5, "سند ۷۱۴۸۵ باید حداقل ۵ رابطه سندی داشته باشد"
    assert len(expansion["attachments"]) >= 2, "سند ۷۱۴۸۵ باید ۲ پیوست داشته باشد"

    print("روابط استخراج‌شده برای سند ۷۱۴۸۵:")
    for r in expansion["legal_relations"]:
        print(f"  * {r['relation_type']}: {r['target_name'][:50]}")

    print("✅ تست توسعه گراف سند ۷۱۴۸۵ با موفقیت پاس شد.")


if __name__ == "__main__":
    test_knowledge_graph_construction()
    test_relation_expansion()
    print("\n🎉 کلیه آزمون‌های گراف دانش با موفقیت ۱۰۰٪ پاس شدند.")
