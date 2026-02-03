# SPDX-License-Identifier: GPL-3.0-or-later

from typing import NamedTuple

from bmesh.types import BMLoop, BMesh
from mathutils import Vector

UVKey = tuple[float, float, int]  # (x, y, vert_index)
AdjacencyGraph = dict[UVKey, set[UVKey]]


class UVNodeData(NamedTuple):
    """Immutable data container for UV node information."""

    uv: Vector
    vert_index: int
    loops: list[BMLoop]


def align_uv_straight_edge(bm: BMesh, uv_layer_name: str, mode="GEOMETRY", keep_length=True) -> bool:
    """
    Straighten selected UV edges.
    """
    uv_layer = bm.loops.layers.uv.get(uv_layer_name)
    if not uv_layer:
        return False

    node_data, graph = _build_uv_graph(bm, uv_layer)

    if not graph:
        return False

    chains = _find_chains(graph)
    if not chains:
        return False

    updates: dict[UVKey, Vector] = {}
    for chain in chains:
        chain_updates = _calculate_straight_chain(chain, node_data, mode, keep_length)
        updates.update(chain_updates)

    _apply_updates(uv_layer, node_data, updates)

    return True


def _build_uv_graph(bm, uv_layer) -> tuple[dict[UVKey, UVNodeData], AdjacencyGraph]:
    """
    Extracts UV selection into a graph representation and node data map.
    Returns: (node_data, adjacency_graph)
    """
    node_data: dict[UVKey, UVNodeData] = {}
    graph: AdjacencyGraph = {}

    for face in bm.faces:
        for loop in face.loops:
            if loop.uv_select_vert:
                uv = loop[uv_layer].uv
                key = (round(uv.x, 6), round(uv.y, 6), loop.vert.index)

                if key not in node_data:
                    node_data[key] = UVNodeData(uv=uv.copy(), vert_index=loop.vert.index, loops=[])
                    graph[key] = set()

                node_data[key].loops.append(loop)

    # Scan loops again to build edges
    # iterate over the collected node_data to avoid re-scanning all faces
    for key, data in node_data.items():
        for loop in data.loops:
            if not loop.uv_select_edge:
                continue

            next_loop = loop.link_loop_next
            if next_loop.uv_select_vert:
                next_uv = next_loop[uv_layer].uv
                next_key = (round(next_uv.x, 6), round(next_uv.y, 6), next_loop.vert.index)

                if next_key in graph:
                    graph[key].add(next_key)
                    graph[next_key].add(key)

    return node_data, graph


def _find_chains(graph: AdjacencyGraph) -> list[list[UVKey]]:
    """
    Traverses the graph to find connected components and orders them into chains.
    """
    visited = set()
    chains = []

    sorted_keys = sorted(graph.keys())

    for start_key in sorted_keys:
        if start_key in visited:
            continue

        # DFS to find component
        component = []
        stack = [start_key]
        visited.add(start_key)

        while stack:
            curr = stack.pop()
            component.append(curr)
            for neighbor in graph[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)

        if len(component) > 1:
            ordered = _order_component(component, graph)
            if ordered:
                chains.append(ordered)

    return chains


def _order_component(component: list[UVKey], graph: AdjacencyGraph) -> list[UVKey]:
    """
    Orders a set of connected keys into a linear chain.
    """
    endpoints = [k for k in component if len(graph[k]) == 1]

    start_node = endpoints[0] if endpoints else min(component)

    ordered = [start_node]
    visited_in_chain = {start_node}
    curr = start_node

    # Traverse
    for _ in range(len(component) - 1):
        neighbors = sorted(list(graph[curr]))
        next_node = None
        for n in neighbors:
            if n not in visited_in_chain:
                next_node = n
                break

        if next_node:
            ordered.append(next_node)
            visited_in_chain.add(next_node)
            curr = next_node
        else:
            break

    return ordered


def _calculate_straight_chain(
    chain: list[UVKey], node_data: dict[UVKey, UVNodeData], mode: str, keep_length: bool
) -> dict[UVKey, Vector]:
    """
    Calculates new UV coordinates for a chain.
    """
    if len(chain) <= 1:
        return {}

    start_uv = node_data[chain[0]].uv
    end_uv = node_data[chain[-1]].uv
    direction = end_uv - start_uv

    if abs(direction.x) > abs(direction.y):
        direction.y = 0  # Align Horizontal
    else:
        direction.x = 0  # Align Vertical

    if direction.length < 1e-7:
        return {}

    # to access 3D coordinate
    def get_co(the_key):
        return node_data[the_key].loops[0].vert.co

    dists = [0.0]
    total_dist = 0.0

    if mode == "GEOMETRY":
        for i in range(len(chain) - 1):
            d = (get_co(chain[i + 1]) - get_co(chain[i])).length
            total_dist += d
            dists.append(total_dist)

        if total_dist <= 0:
            mode = "EVEN"

    if mode == "EVEN":
        dists = [float(i) for i in range(len(chain))]
        total_dist = float(len(chain) - 1)

    # Normalize distances (t values 0.0 to 1.0)
    if total_dist > 0:
        t_values = [d / total_dist for d in dists]
    else:
        t_values = [0.0] * len(chain)

    final_direction = direction
    if keep_length:
        orig_uv_len = sum(
            (node_data[chain[i + 1]].uv - node_data[chain[i]].uv).length
            for i in range(len(chain) - 1)
        )
        if orig_uv_len > 0:
            final_direction = direction.normalized() * orig_uv_len

    base_positions = [start_uv + final_direction * t for t in t_values]

    orig_center = sum((node_data[k].uv for k in chain), Vector((0, 0))) / len(chain)
    new_center = sum(base_positions, Vector((0, 0))) / len(base_positions)
    offset = orig_center - new_center

    new_positions = {}
    for i, key in enumerate(chain):
        new_positions[key] = base_positions[i] + offset

    return new_positions


def _apply_updates(uv_layer, node_data: dict[UVKey, UVNodeData], updates: dict[UVKey, Vector]):
    """
    Applies the calculated UV updates to the BMesh loops.
    """
    for key, new_uv in updates.items():
        if key in node_data:
            for loop in node_data[key].loops:
                loop[uv_layer].uv = new_uv
