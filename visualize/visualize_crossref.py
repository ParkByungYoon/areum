"""gospels_crossrefs.json → 인터랙티브 네트워크 그래프 HTML 생성"""
import json
import os

INPUT_PATH = "data/gospels_crossrefs.json"
OUTPUT_PATH = "visualize/gospels_network.html"

BOOK_COLORS = {
    "마태복음": "#4A90D9",
    "마가복음": "#27AE60",
    "누가복음": "#E67E22",
    "요한복음": "#9B59B6",
}

BOOK_SHORT = {
    "마태복음": "마태",
    "마가복음": "마가",
    "누가복음": "누가",
    "요한복음": "요한",
}


def build_graph(data):
    ep_index = {
        (ep["book"], ep["chapter_start"], ep["verse_start"]): i
        for i, ep in enumerate(data)
    }

    nodes = [
        {
            "id": i,
            "label": BOOK_SHORT[ep["book_name"]] + " " + str(ep["chapter_start"]) + "장",
            "title": ep["episode"],
            "book": ep["book_name"],
            "color": BOOK_COLORS[ep["book_name"]],
            "chapter": ep["chapter_start"],
        }
        for i, ep in enumerate(data)
    ]

    seen_edges = set()
    links = []
    for i, ep in enumerate(data):
        for c in ep["connected_episodes"]:
            j_key = (c["book"], c["chapter_start"], c["verse_start"])
            j = ep_index.get(j_key)
            if j is None:
                continue
            edge_key = (min(i, j), max(i, j))
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                links.append({"source": i, "target": j})

    return nodes, links


def generate_html(nodes, links):
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    links_json = json.dumps(links, ensure_ascii=False)

    legend_items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">'
        f'<div style="width:14px;height:14px;border-radius:50%;background:{color}"></div>'
        f'<span>{book}</span></div>'
        for book, color in BOOK_COLORS.items()
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>사복음서 서사적 병행 네트워크</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ margin: 0; background: #1a1a2e; font-family: 'Malgun Gothic', sans-serif; color: #eee; }}
  #tooltip {{
    position: absolute; background: rgba(0,0,0,0.85); color: #fff;
    padding: 8px 12px; border-radius: 8px; font-size: 13px;
    pointer-events: none; display: none; max-width: 220px; line-height: 1.5;
  }}
  #legend {{
    position: absolute; top: 16px; left: 16px;
    background: rgba(255,255,255,0.08); padding: 12px 16px; border-radius: 10px;
    font-size: 13px;
  }}
  #info {{
    position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
    font-size: 12px; color: #aaa;
  }}
  .link {{ stroke: #ffffff22; stroke-width: 1.5px; }}
  .link.highlighted {{ stroke: #ffffff99; stroke-width: 2.5px; }}
  .node circle {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; }}
  .node text {{ font-size: 10px; fill: #ddd; pointer-events: none; text-anchor: middle; dominant-baseline: central; }}
</style>
</head>
<body>
<div id="tooltip"></div>
<div id="legend">
  <div style="font-weight:bold;margin-bottom:8px">사복음서 서사적 병행</div>
  {legend_items}
</div>
<div id="info">노드 클릭 시 연결 강조 · 드래그로 이동 가능</div>
<svg id="graph"></svg>

<script>
const nodes = {nodes_json};
const links = {links_json};

const width = window.innerWidth, height = window.innerHeight;
const svg = d3.select("#graph").attr("width", width).attr("height", height);

const defs = svg.append("defs");
const g = svg.append("g");

svg.call(d3.zoom().scaleExtent([0.3, 3]).on("zoom", e => g.attr("transform", e.transform)));

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(90))
  .force("charge", d3.forceManyBody().strength(-280))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collision", d3.forceCollide(28));

const link = g.append("g").selectAll("line")
  .data(links).join("line").attr("class", "link");

const node = g.append("g").selectAll("g")
  .data(nodes).join("g").attr("class", "node")
  .call(d3.drag()
    .on("start", (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on("drag", (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on("end", (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }}));

node.append("circle")
  .attr("r", 18)
  .attr("fill", d => d.color)
  .attr("fill-opacity", 0.85);

node.append("text")
  .text(d => d.title.length > 8 ? d.title.slice(0, 7) + "…" : d.title)
  .attr("dy", 0);

const tooltip = d3.select("#tooltip");

node.on("mouseover", (e, d) => {{
    tooltip.style("display", "block")
      .html("<b>" + d.title + "</b><br>" + d.book + " " + d.chapter + "장");
  }})
  .on("mousemove", e => {{
    tooltip.style("left", (e.pageX + 12) + "px").style("top", (e.pageY - 10) + "px");
  }})
  .on("mouseout", () => tooltip.style("display", "none"))
  .on("click", (e, d) => {{
    const neighborIds = new Set(
      links.filter(l => l.source.id === d.id || l.target.id === d.id)
           .flatMap(l => [l.source.id, l.target.id])
    );
    link.classed("highlighted", l => l.source.id === d.id || l.target.id === d.id);
    node.select("circle")
      .attr("stroke-width", n => n.id === d.id ? 3.5 : neighborIds.has(n.id) ? 2.5 : 1.5)
      .attr("fill-opacity", n => n.id === d.id || neighborIds.has(n.id) ? 1.0 : 0.3);
  }});

simulation.on("tick", () => {{
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => "translate(" + d.x + "," + d.y + ")");
}});
</script>
</body>
</html>"""


def main():
    with open(INPUT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    nodes, links = build_graph(data)
    html = generate_html(nodes, links)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"완료: {OUTPUT_PATH} (노드 {len(nodes)}개, 엣지 {len(links)}개)")
    print(f"브라우저에서 열기: {os.path.abspath(OUTPUT_PATH)}")


if __name__ == "__main__":
    main()
