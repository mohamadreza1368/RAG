"""
اسکریپت خط فرمان ساخت، کاوش و صادرکردن گراف دانش قوانین و مقررات (Knowledge Graph CLI)

نمونه‌های کاربرد:
  1. ساخت کامل گراف دانش، تولید فایل‌های سه‌تایی (Triples)، کدهای Neo4j و داشبورد تعاملی HTML:
     python run_graph.py --build

  2. توسعه گراف (Relation Expansion) پیرامون یک سند خاص (مثلاً 71485):
     python run_graph.py --expand 71485

  3. مشاهده آمار کلی گره‌ها و یال‌های گراف دانش:
     python run_graph.py --stats
"""

import argparse
import json
from pathlib import Path

from knowledge_graph.builder import KnowledgeGraphBuilder
from knowledge_graph.traverser import GraphTraverser
from knowledge_graph.exporter import GraphExporter
from knowledge_graph.visualizer import GraphVisualizer


def main():
    parser = argparse.ArgumentParser(
        description="سامانه ساخت و تحلیل گراف دانش مقررات بازار سرمایه (Knowledge Graph Engine)"
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="ساخت کامل گراف دانش از روی فایل‌های خام و خروجی به JSON, Cypher و HTML"
    )
    parser.add_argument(
        "--expand",
        type=int,
        default=None,
        help="توسعه و پیمایش روابط گراف برای یک سند خاص (Relation Expansion)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="نمایش آمار و توزیع گره‌ها و یال‌های گراف دانش"
    )

    args = parser.parse_args()

    builder = KnowledgeGraphBuilder()
    raw_dir = Path("data/raw")

    print("==================================================================")
    print("🕸️ موتور ساخت و پردازش گراف دانش قوانین (Knowledge Graph Engine)")
    print("==================================================================")

    # ساخت گراف از داده‌های موجود
    builder.build_from_directory(raw_dir)
    stats = builder.get_summary_statistics()

    if args.stats or (not args.build and args.expand is None):
        print("\n📊 آمار وضعیت گراف دانش:")
        print(f"  - کل گره‌ها (موجودیت‌ها): {stats['total_nodes']:,}")
        print(f"  - کل یال‌ها (روابط): {stats['total_edges']:,}")
        print("\nتوزیع گره‌ها بر اساس نوع:")
        for k, v in stats["nodes_by_type"].items():
            print(f"    * {k}: {v:,}")
        print("\nتوزیع روابط (یال‌ها) بر اساس نوع:")
        for k, v in stats["edges_by_type"].items():
            print(f"    * {k}: {v:,}")

    if args.build:
        out_graph_dir = Path("data/graph")
        out_graph_dir.mkdir(parents=True, exist_ok=True)

        exporter = GraphExporter(builder)
        visualizer = GraphVisualizer(builder)

        # ۱. خروجی JSON گراف
        json_file = out_graph_dir / "graph.json"
        exporter.to_cytoscape_json(json_file)
        print(f"\n📁 خروجی گراف ساختاریافته در {json_file} ذخیره شد.")

        # ۲. خروجی سه‌تایی‌های گراف دانش (Triples TSV)
        triples_file = out_graph_dir / "triples.tsv"
        exporter.to_triples_tsv(triples_file)
        print(f"📁 سه‌تایی‌های گراف دانش (Triples) در {triples_file} ذخیره شد.")

        # ۳. خروجی Cypher برای Neo4j
        cypher_file = out_graph_dir / "neo4j_import.cypher"
        exporter.to_neo4j_cypher(cypher_file)
        print(f"📁 اسکریپت ایمپورت پایگاه داده Neo4j (Cypher) در {cypher_file} ذخیره شد.")

        # ۴. تولید داشبورد گراف تعاملی HTML
        html_file = out_graph_dir / "graph_explorer.html"
        visualizer.generate_html(html_file)
        print(f"🌐 داشبورد بصری و تعاملی گراف در {html_file} آماده مشاهده در مرورگر است.")

    if args.expand:
        traverser = GraphTraverser(builder.graph, builder.nodes)
        print(f"\n🔍 توسعه گراف و استخراج زیرگراف سند {args.expand} (Relation Expansion):")
        result = traverser.expand_document_context(args.expand)

        if "error" in result:
            print(f"❌ {result['error']}")
            return

        doc = result.get("document") or {}
        print(f"  📌 عنوان سند: {doc.get('name')}")
        print(f"  🏷️ مرجع تصویب: {', '.join(a.get('name') for a in result.get('authorities', []))}")
        print(f"  📂 دسته‌بندی: {', '.join(c.get('name') for c in result.get('categories', []))}")
        print(f"  📎 تعداد پیوست‌ها: {len(result.get('attachments', []))}")
        print(f"  📜 تعداد کل مواد استخراج‌شده: {result.get('total_articles', 0)}")

        print("\n  🔗 روابط حقوقی بین‌سندی (نسخ، اصلاح، ارتباط):")
        for rel in result.get("legal_relations", []):
            dir_str = "➡️ خروجی" if rel["direction"] == "OUTBOUND" else "⬅️ ورودی"
            print(f"    - [{dir_str}] {rel['label_fa']} ({rel['relation_type']}) ⬅️ {rel.get('target_name') or rel.get('source_name')}")


if __name__ == "__main__":
    main()
