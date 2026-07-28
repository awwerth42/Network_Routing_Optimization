"""Graph data structures and generators for routing experiments."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Iterable


@dataclass(frozen=True)
class Edge:
    """A weighted edge from the current node to ``to``."""

    to: int
    weight: float


class WeightedGraph:
    """Adjacency-list weighted graph.

    The experiments use undirected graphs by default because routing links are
    usually bidirectional in the project model. The algorithms also work on
    directed graphs when ``directed=True``.
    """

    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        self._adjacency: dict[int, list[Edge]] = {}
        # Parallel weight index so edge_weight/has_edge/path_cost are O(1) dict
        # lookups instead of linear scans over the adjacency list. Without this,
        # Harmony Search spends most of its runtime re-scanning adjacency lists
        # to score candidate paths, which inflates its measured cost relative to
        # the classical algorithms and makes the comparison unfair.
        self._weights: dict[int, dict[int, float]] = {}
        self.coordinates: dict[int, tuple[float, float]] = {}

    def add_node(self, node: int, coordinate: tuple[float, float] | None = None) -> None:
        self._adjacency.setdefault(node, [])
        self._weights.setdefault(node, {})
        if coordinate is not None:
            self.coordinates[node] = coordinate

    def add_edge(self, source: int, target: int, weight: float) -> None:
        self.add_node(source)
        self.add_node(target)
        self._replace_or_append(source, target, weight)
        if not self.directed:
            self._replace_or_append(target, source, weight)

    def _replace_or_append(self, source: int, target: int, weight: float) -> None:
        edges = self._adjacency[source]
        if target in self._weights[source]:
            for index, edge in enumerate(edges):
                if edge.to == target:
                    edges[index] = Edge(target, weight)
                    break
        else:
            edges.append(Edge(target, weight))
        self._weights[source][target] = weight

    def nodes(self) -> list[int]:
        """Return nodes in sorted order.

        Prefer :meth:`iter_nodes` or :meth:`node_count` on large graphs; this
        sorts on every call.
        """

        return sorted(self._adjacency)

    def iter_nodes(self):
        """Iterate nodes in insertion order without sorting."""

        return iter(self._adjacency)

    def node_count(self) -> int:
        return len(self._adjacency)

    def neighbors(self, node: int) -> list[Edge]:
        return list(self._adjacency.get(node, []))

    def has_node(self, node: int) -> bool:
        return node in self._adjacency

    def has_edge(self, source: int, target: int) -> bool:
        return target in self._weights.get(source, ())

    def edge_weight(self, source: int, target: int) -> float:
        try:
            return self._weights[source][target]
        except KeyError as exc:
            raise KeyError(f"No edge from {source} to {target}.") from exc

    def edge_count(self) -> int:
        count = sum(len(edges) for edges in self._adjacency.values())
        return count if self.directed else count // 2

    def edges(self) -> list[tuple[int, int, float]]:
        result: list[tuple[int, int, float]] = []
        seen: set[tuple[int, int]] = set()
        for source, edges in self._adjacency.items():
            for edge in edges:
                key = (source, edge.to) if self.directed else tuple(sorted((source, edge.to)))
                if key in seen:
                    continue
                seen.add(key)
                result.append((source, edge.to, edge.weight))
        return result

    def path_cost(self, path: Iterable[int]) -> float:
        nodes = list(path)
        if len(nodes) < 2:
            return 0.0
        weights = self._weights
        return sum(weights[nodes[index]][nodes[index + 1]] for index in range(len(nodes) - 1))


def density_to_probability(density: str) -> float:
    values = {
        "sparse": 0.04,
        "moderate": 0.12,
        "dense": 0.25,
    }
    try:
        return values[density]
    except KeyError as exc:
        raise ValueError(f"Unknown density {density!r}; use sparse, moderate, or dense.") from exc


def generate_connected_graph(
    node_count: int,
    density: str = "sparse",
    seed: int | None = None,
    min_weight: int = 1,
    max_weight: int = 100,
    directed: bool = False,
    with_coordinates: bool = True,
) -> WeightedGraph:
    """Generate a connected weighted graph with reproducible randomness."""

    if node_count < 2:
        raise ValueError("node_count must be at least 2.")
    if min_weight <= 0 or max_weight < min_weight:
        raise ValueError("Weights must be positive and max_weight must be >= min_weight.")

    rng = random.Random(seed)
    graph = WeightedGraph(directed=directed)
    for node in range(node_count):
        coordinate = (rng.random(), rng.random()) if with_coordinates else None
        graph.add_node(node, coordinate)

    # First build a random spanning tree so the graph is connected.
    for node in range(1, node_count):
        parent = rng.randrange(0, node)
        graph.add_edge(parent, node, rng.randint(min_weight, max_weight))

    probability = density_to_probability(density)
    for source in range(node_count):
        for target in range(source + 1, node_count):
            if graph.has_edge(source, target):
                continue
            if rng.random() < probability:
                graph.add_edge(source, target, rng.randint(min_weight, max_weight))

    return graph


def euclidean_heuristic(graph: WeightedGraph, target: int) -> callable:
    """Return a coordinate-distance heuristic for A*.

    This is useful for coordinate-based generated graphs. Experiments default to
    a zero heuristic because random edge weights are not tied to geometry.
    """

    def heuristic(node: int) -> float:
        if node not in graph.coordinates or target not in graph.coordinates:
            return 0.0
        x1, y1 = graph.coordinates[node]
        x2, y2 = graph.coordinates[target]
        return math.dist((x1, y1), (x2, y2))

    return heuristic
