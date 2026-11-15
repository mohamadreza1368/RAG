"""
صادرکننده گراف دانش به فرمت‌های استاندارد گراف (JSON Graph، Neo4j Cypher و RDF Triples)
"""

import json
from pathlib import Path
from typing import Dict, Any
from .builder import KnowledgeGraphBuilder


class GraphExporter:
    """صادرکننده گراف دانش به ابزارهای تحلیلی و پایگاه‌های داده گرافی"""

    def __init__(self, builder: KnowledgeGraphBuilder):
        self.builder = builder

    def to_cytoscape_json(self, output_file: Path) -> dict:
        """خروجی استاندارد JSON سازگار با ابزارهای فرانت‌اند (D3.js / Cytoscape / Vis.js)"""
        elements = {
            "nodes": [],
            "edges": []
        }

        for n in self.builder.nodes.values():
            elements["nodes"].append({
                "id": n.id,
                "label": n.label.value,
                "name": n.name,
                "properties": {k: v for k, v in n.properties.items() if k not in ["raw_body"]}
            })

        for idx, e in enumerate(self.builder.edges):
            elements["edges"].append({
                "id": f"edge_{idx}",
                "source": e.source_id,
                "target": e.target_id,
                "relation": e.relation_type.value,
                "label_fa": e.label_fa,
                "properties": e.properties
            })

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(elements, ensure_ascii=False, indent=2), encoding="utf-8")
        return elements

    def to_triples_tsv(self, output_file: Path) -> None:
        """خروجی سه‌تایی‌های گراف دانش (Subject - Predicate - Object) به فرمت TSV"""
        lines = ["Subject_ID\tSubject_Name\tPredicate\tPredicate_FA\tObject_ID\tObject_Name"]
        for e in self.builder.edges:
            s_node = self.builder.nodes.get(e.source_id)
            t_node = self.builder.nodes.get(e.target_id)
            if s_node and t_node:
                s_name = s_node.name.replace("\t", " ").replace("\n", " ")
                t_name = t_node.name.replace("\t", " ").replace("\n", " ")
                lines.append(f"{e.source_id}\t{s_name}\t{e.relation_type.value}\t{e.label_fa or ''}\t{e.target_id}\t{t_name}")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines), encoding="utf-8")

    def to_neo4j_cypher(self, output_file: Path) -> None:
        """تولید دستورات Cypher برای ایمپورت مستقیم در پایگاه داده Neo4j"""
        lines = ["// --- دستورات ایجاد گره‌ها و یال‌ها در Neo4j ---"]

        # ساخت گره‌ها
        for n in self.builder.nodes.values():
            props = {
                "id": n.id,
                "name": n.name,
            }
            # پاکسازی رشته‌ها برای Cypher
            escaped_props = ", ".join(f"{k}: '{str(v).replace('\'', '')}'" for k, v in props.items())
            lines.append(f"MERGE (n:{n.label.value} {{{escaped_props}}});")

        # ساخت یال‌ها
        for e in self.builder.edges:
            rel = e.relation_type.value
            lbl_fa = e.label_fa or ""
            lines.append(
                f"MATCH (s {{id: '{e.source_id}'}}), (t {{id: '{e.target_id}'}}) "
                f"MERGE (s)-[:{rel} {{label_fa: '{lbl_fa}'}}]->(t);"
            )

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines), encoding="utf-8")
