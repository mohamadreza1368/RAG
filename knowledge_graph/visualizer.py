"""
تولیدکننده نمایشگر گراف تعاملی در مرورگر (Interactive HTML Graph Visualizer)
بر پایه Vis-Network جهت کاوش بصری گره‌ها، مواد و روابط تنقیحی
"""

import json
from pathlib import Path
from .builder import KnowledgeGraphBuilder


COLOR_MAP = {
    "Category": "#3498db",      # آبی
    "Document": "#e74c3c",      # قرمز
    "Version": "#e67e22",       # نارنجی
    "Section": "#16a085",       # سبز تیره
    "Article": "#2ecc71",       # سبز روشن
    "Note": "#1abc9c",          # فیروزه‌ای
    "Clause": "#27ae60",        # زمردی
    "Authority": "#9b59b6",     # بنفش
    "Attachment": "#f39c12",    # کهربایی
}


class GraphVisualizer:
    """ایجاد داشبورد تعاملی HTML برای مشاهده و تحلیل شبکه قوانین"""

    def __init__(self, builder: KnowledgeGraphBuilder):
        self.builder = builder

    def generate_html(self, output_html: Path, max_nodes: int = 500) -> None:
        """تولید فایل HTML یکپارچه با امکان جستجو، زوم، فیلتر و کلیک روی گره‌ها"""
        vis_nodes = []
        vis_edges = []

        # گره‌ها
        for n in list(self.builder.nodes.values())[:max_nodes]:
            lbl = n.label.value
            color = COLOR_MAP.get(lbl, "#95a5a6")
            name_short = n.name[:45] + "..." if len(n.name) > 45 else n.name

            vis_nodes.append({
                "id": n.id,
                "label": name_short,
                "title": f"<b>{lbl}</b><br>{n.name}",
                "color": {"background": color, "border": "#2c3e50"},
                "group": lbl,
                "shape": "dot",
                "size": 25 if lbl in ["Document", "Category"] else 15,
                "full_data": {
                    "id": n.id,
                    "label": lbl,
                    "name": n.name,
                    "properties": {k: v for k, v in n.properties.items() if k != "raw_body"}
                }
            })

        node_id_set = {vn["id"] for vn in vis_nodes}

        # یال‌ها
        for idx, e in enumerate(self.builder.edges):
            if e.source_id in node_id_set and e.target_id in node_id_set:
                vis_edges.append({
                    "id": f"e_{idx}",
                    "from": e.source_id,
                    "to": e.target_id,
                    "label": e.label_fa or e.relation_type.value,
                    "arrows": "to",
                    "font": {"size": 10, "align": "middle", "strokeWidth": 2, "strokeColor": "#fff"},
                    "color": {"color": "#7f8c8d", "highlight": "#e74c3c"}
                })

        html_template = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>کاوشگر گراف دانش قوانین و مقررات بازار سرمایه</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Tahoma, 'Vazirmatn', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
            background: #f8f9fa;
        }}
        #sidebar {{
            width: 340px;
            background: #ffffff;
            border-left: 1px solid #dee2e6;
            padding: 15px;
            box-sizing: border-box;
            overflow-y: auto;
            box-shadow: -2px 0 5px rgba(0,0,0,0.05);
        }}
        #network {{
            flex: 1;
            height: 100vh;
        }}
        h2 {{ font-size: 16px; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; color: #fff; font-size: 11px; margin-bottom: 8px; }}
        .property-box {{ background: #f1f3f5; padding: 10px; border-radius: 6px; font-size: 12px; margin-top: 10px; }}
        .stat-item {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed #e9ecef; font-size: 12px; }}
        .legend {{ margin-top: 15px; }}
        .legend-item {{ display: flex; align-items: center; margin-bottom: 6px; font-size: 11px; }}
        .legend-color {{ width: 14px; height: 14px; border-radius: 50%; margin-left: 8px; }}
    </style>
</head>
<body>
    <div id="sidebar">
        <h2>📊 گراف دانش قوانین بازار سرمایه</h2>
        <div id="stats">
            <div class="stat-item"><span>تعداد کل گره‌ها:</span><b>{len(vis_nodes)}</b></div>
            <div class="stat-item"><span>تعداد کل یال‌ها:</span><b>{len(vis_edges)}</b></div>
        </div>

        <div class="legend">
            <b>راهنمای گره‌ها:</b>
            <div class="legend-item"><div class="legend-color" style="background:#e74c3c;"></div><span>سند رسمی (Document)</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#3498db;"></div><span>دسته‌بندی (Category)</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#2ecc71;"></div><span>ماده قانونی (Article)</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#1abc9c;"></div><span>تبصره / بند (Note/Clause)</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#9b59b6;"></div><span>مرجع تصویب (Authority)</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#f39c12;"></div><span>پیوست / فرم (Attachment)</span></div>
        </div>

        <hr style="margin: 15px 0; border: none; border-top: 1px solid #dee2e6;">

        <div id="inspector">
            <h3>🔍 مشخصات گره انتخابی</h3>
            <p style="color:#7f8c8d; font-size:12px;">روی هر گره در گراف کلیک کنید تا اطلاعات، متادیتا و متن کامل آن اینجا نمایش داده شود.</p>
        </div>
    </div>
    <div id="network"></div>

    <script type="text/javascript">
        var nodesData = {json.dumps(vis_nodes, ensure_ascii=False)};
        var edgesData = {json.dumps(vis_edges, ensure_ascii=False)};

        var container = document.getElementById('network');
        var data = {{
            nodes: new vis.DataSet(nodesData),
            edges: new vis.DataSet(edgesData)
        }};
        var options = {{
            nodes: {{
                font: {{ face: 'Tahoma', size: 12 }},
                borderWidth: 2
            }},
            edges: {{
                smooth: {{ type: 'cubicBezier', forceDirection: 'none' }},
                arrows: {{ to: {{ enabled: true, scaleFactor: 0.7 }} }}
            }},
            physics: {{
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {{
                    gravitationalConstant: -40,
                    centralGravity: 0.005,
                    springLength: 90,
                    springConstant: 0.18
                }},
                stabilization: {{ iterations: 120 }}
            }}
        }};
        var network = new vis.Network(container, data, options);

        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodesData.find(n => n.id === nodeId);
                if (node && node.full_data) {{
                    var d = node.full_data;
                    var html = '<div>';
                    html += '<span class="badge" style="background:' + node.color.background + '">' + d.label + '</span>';
                    html += '<h4 style="margin: 6px 0; font-size: 13px;">' + d.name + '</h4>';
                    html += '<div class="property-box">';
                    for (var key in d.properties) {{
                        var val = d.properties[key];
                        if (val !== null && val !== undefined && val !== '') {{
                            html += '<div style="margin-bottom:6px;"><b>' + key + ':</b> ' + String(val).replace(/\\n/g, '<br>') + '</div>';
                        }}
                    }}
                    html += '</div></div>';
                    document.getElementById('inspector').innerHTML = html;
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html_template, encoding="utf-8")
