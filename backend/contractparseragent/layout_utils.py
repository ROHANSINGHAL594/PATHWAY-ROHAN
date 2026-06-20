# layout_utils.py
# Utility for computing x, y positions for flowchart nodes

from collections import deque, defaultdict
from typing import List, Dict, Any

X_SPACING = 400
Y_SPACING = 300

def compute_layout(nodes: List[Dict], edges_dict: Dict[str, List[str]]) -> Dict[str, Dict[str, float]]:
    """
    Computes (x, y) positions using a topological/level-based layout.
    """
    adj = defaultdict(list)
    in_degree = defaultdict(int)
    all_node_ids = set(n['id'] for n in nodes)
    for src, targets in edges_dict.items():
        if not isinstance(targets, list): targets = [targets]
        for tgt in targets:
            adj[src].append(tgt)
            in_degree[tgt] += 1
            all_node_ids.add(src)
            all_node_ids.add(tgt)
    queue = deque([n for n in all_node_ids if in_degree[n] == 0])
    levels = defaultdict(int)
    for n in queue:
        levels[n] = 0
    processed = set(queue)
    while queue:
        curr = queue.popleft()
        current_level = levels[curr]
        for neighbor in adj[curr]:
            new_level = current_level + 1
            if new_level > levels[neighbor]:
                levels[neighbor] = new_level
            in_degree[neighbor] -= 1
            if in_degree[neighbor] <= 0:
                queue.append(neighbor)
                processed.add(neighbor)
    for n in all_node_ids:
        if n not in processed:
            levels[n] = 0
    nodes_by_level = defaultdict(list)
    for n_id, lvl in levels.items():
        nodes_by_level[lvl].append(n_id)
    positions = {}
    for lvl, node_ids in nodes_by_level.items():
        node_ids.sort()
        for idx, n_id in enumerate(node_ids):
            positions[n_id] = {
                "x": lvl * X_SPACING,
                "y": idx * Y_SPACING
            }
    return positions


def apply_layout(flowchart: Dict[str, Any]) -> Dict[str, Any]:
    """Assign computed x/y positions to every node in-place."""
    nodes = flowchart.get("nodes", []) or []
    edges = flowchart.get("edges", []) or []

    edges_dict: Dict[str, List[str]] = {}
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src is None or tgt is None:
            continue
        edges_dict.setdefault(src, []).append(tgt)

    positions = compute_layout(nodes, edges_dict)
    for node in nodes:
        node_id = node.get("id")
        pos = positions.get(node_id, {"x": 0, "y": 0})
        node["position"] = {"x": pos["x"], "y": pos["y"]}

    return flowchart
