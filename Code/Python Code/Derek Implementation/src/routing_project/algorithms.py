"""Shortest-path and Harmony Search algorithm implementations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import heapq
import math
import random
import time
from typing import Callable

from routing_project.graph import WeightedGraph


@dataclass
class AlgorithmResult:
    algorithm: str
    path: list[int]
    cost: float
    runtime_ms: float
    success: bool
    metadata: dict[str, object] = field(default_factory=dict)


def _elapsed_ms(start: int) -> float:
    return (time.perf_counter_ns() - start) / 1_000_000


def _reconstruct_path(previous: dict[int, int], source: int, target: int) -> list[int]:
    if source == target:
        return [source]
    if target not in previous:
        return []
    path = [target]
    while path[-1] != source:
        path.append(previous[path[-1]])
    path.reverse()
    return path


def dijkstra(graph: WeightedGraph, source: int, target: int) -> AlgorithmResult:
    start = time.perf_counter_ns()
    if not graph.has_node(source) or not graph.has_node(target):
        return AlgorithmResult("dijkstra", [], math.inf, _elapsed_ms(start), False, {"error": "missing node"})

    distances = {node: math.inf for node in graph.iter_nodes()}
    previous: dict[int, int] = {}
    distances[source] = 0.0
    queue: list[tuple[float, int]] = [(0.0, source)]
    expanded = 0
    edge_examinations = 0

    while queue:
        current_distance, node = heapq.heappop(queue)
        if current_distance > distances[node]:
            continue
        expanded += 1
        if node == target:
            break
        for edge in graph.neighbors(node):
            edge_examinations += 1
            candidate = current_distance + edge.weight
            if candidate < distances[edge.to]:
                distances[edge.to] = candidate
                previous[edge.to] = node
                heapq.heappush(queue, (candidate, edge.to))

    path = _reconstruct_path(previous, source, target)
    return AlgorithmResult(
        "dijkstra",
        path,
        distances[target],
        _elapsed_ms(start),
        bool(path),
        {"expanded_nodes": expanded, "edge_examinations": edge_examinations},
    )


def bellman_ford(graph: WeightedGraph, source: int, target: int) -> AlgorithmResult:
    start = time.perf_counter_ns()
    if not graph.has_node(source) or not graph.has_node(target):
        return AlgorithmResult("bellman_ford", [], math.inf, _elapsed_ms(start), False, {"error": "missing node"})

    node_total = graph.node_count()
    distances = {node: math.inf for node in graph.iter_nodes()}
    previous: dict[int, int] = {}
    distances[source] = 0.0
    edges = graph.edges()
    relaxations = 0
    edge_examinations = 0

    for _ in range(node_total - 1):
        changed = False
        for source_node, target_node, weight in edges:
            pairs = [(source_node, target_node, weight)]
            if not graph.directed:
                pairs.append((target_node, source_node, weight))
            for left, right, edge_weight in pairs:
                edge_examinations += 1
                if distances[left] + edge_weight < distances[right]:
                    distances[right] = distances[left] + edge_weight
                    previous[right] = left
                    changed = True
                    relaxations += 1
        if not changed:
            break

    for source_node, target_node, weight in edges:
        pairs = [(source_node, target_node, weight)]
        if not graph.directed:
            pairs.append((target_node, source_node, weight))
        for left, right, edge_weight in pairs:
            if distances[left] + edge_weight < distances[right]:
                return AlgorithmResult(
                    "bellman_ford",
                    [],
                    -math.inf,
                    _elapsed_ms(start),
                    False,
                    {
                        "negative_cycle": True,
                        "relaxations": relaxations,
                        "edge_examinations": edge_examinations,
                    },
                )

    path = _reconstruct_path(previous, source, target)
    return AlgorithmResult(
        "bellman_ford",
        path,
        distances[target],
        _elapsed_ms(start),
        bool(path),
        {
            "negative_cycle": False,
            "relaxations": relaxations,
            "edge_examinations": edge_examinations,
        },
    )


def astar(
    graph: WeightedGraph,
    source: int,
    target: int,
    heuristic: Callable[[int], float] | None = None,
) -> AlgorithmResult:
    start = time.perf_counter_ns()
    if not graph.has_node(source) or not graph.has_node(target):
        return AlgorithmResult("astar", [], math.inf, _elapsed_ms(start), False, {"error": "missing node"})

    estimate = heuristic or (lambda _: 0.0)
    g_score = {node: math.inf for node in graph.iter_nodes()}
    previous: dict[int, int] = {}
    g_score[source] = 0.0
    queue: list[tuple[float, float, int]] = [(estimate(source), 0.0, source)]
    expanded = 0
    edge_examinations = 0

    while queue:
        _, current_cost, node = heapq.heappop(queue)
        if current_cost > g_score[node]:
            continue
        expanded += 1
        if node == target:
            break
        for edge in graph.neighbors(node):
            edge_examinations += 1
            candidate = current_cost + edge.weight
            if candidate < g_score[edge.to]:
                previous[edge.to] = node
                g_score[edge.to] = candidate
                heapq.heappush(queue, (candidate + estimate(edge.to), candidate, edge.to))

    path = _reconstruct_path(previous, source, target)
    return AlgorithmResult(
        "astar",
        path,
        g_score[target],
        _elapsed_ms(start),
        bool(path),
        {"expanded_nodes": expanded, "edge_examinations": edge_examinations},
    )


def harmony_search(
    graph: WeightedGraph,
    source: int,
    target: int,
    hmcr: float = 0.8,
    par: float = 0.3,
    hms: int = 30,
    iterations: int = 200,
    seed: int | None = None,
) -> AlgorithmResult:
    """Approximate routing with Harmony Search.

    A harmony is encoded as a valid source-to-target path. Improvisation prefers
    transitions seen in the current harmony memory, occasionally adjusts toward
    the cheapest local edge, and otherwise explores randomly.
    """

    start = time.perf_counter_ns()
    if not 0 <= hmcr <= 1 or not 0 <= par <= 1:
        raise ValueError("hmcr and par must be in [0, 1].")
    if hms <= 0 or iterations < 0:
        raise ValueError("hms must be positive and iterations must be non-negative.")
    if not graph.has_node(source) or not graph.has_node(target):
        return AlgorithmResult("harmony_search", [], math.inf, _elapsed_ms(start), False, {"error": "missing node"})

    rng = random.Random(seed)
    initial = [_random_valid_path(graph, source, target, rng) for _ in range(hms)]
    initial = [path for path in initial if path]
    if not initial:
        fallback = _unweighted_path(graph, source, target)
        if fallback:
            initial.append(fallback)
    if not initial:
        return AlgorithmResult("harmony_search", [], math.inf, _elapsed_ms(start), False, {"error": "no valid path"})

    # Harmony memory stores (cost, path) pairs so a path is scored exactly once.
    # Re-deriving cost inside the sort key would re-score every harmony on every
    # improvement, which is bookkeeping cost rather than search cost.
    memory: list[tuple[float, list[int]]] = [(graph.path_cost(path), path) for path in initial]
    memory.sort(key=lambda item: item[0])
    path_evaluations = len(memory)
    convergence = [memory[0][0]]
    node_count = graph.node_count()
    successor_map = _memory_successor_map([path for _, path in memory])

    for _ in range(iterations):
        candidate = _improvise_path(graph, source, target, successor_map, node_count, hmcr, par, rng)
        if not candidate:
            candidate = _random_valid_path(graph, source, target, rng)
        if not candidate:
            candidate = _unweighted_path(graph, source, target)
        if not candidate:
            convergence.append(convergence[-1])
            continue
        candidate_cost = graph.path_cost(candidate)
        path_evaluations += 1
        if candidate_cost < memory[-1][0]:
            memory[-1] = (candidate_cost, candidate)
            memory.sort(key=lambda item: item[0])
            successor_map = _memory_successor_map([path for _, path in memory])
        convergence.append(memory[0][0])

    best_cost, best = memory[0]
    return AlgorithmResult(
        "harmony_search",
        best,
        best_cost,
        _elapsed_ms(start),
        True,
        {
            "hmcr": hmcr,
            "par": par,
            "hms": hms,
            "iterations": iterations,
            "seed": seed,
            "convergence": convergence,
            "path_evaluations": path_evaluations,
        },
    )


def _random_valid_path(
    graph: WeightedGraph,
    source: int,
    target: int,
    rng: random.Random,
    max_attempts: int = 12,
) -> list[int]:
    max_steps = max(2, graph.node_count())
    for _ in range(max_attempts):
        path = [source]
        visited = {source}
        while path[-1] != target and len(path) <= max_steps:
            neighbors = [edge.to for edge in graph.neighbors(path[-1]) if edge.to not in visited or edge.to == target]
            if not neighbors:
                break
            next_node = rng.choice(neighbors)
            path.append(next_node)
            visited.add(next_node)
        if path[-1] == target:
            return path
    return []


def _improvise_path(
    graph: WeightedGraph,
    source: int,
    target: int,
    successor_map: dict[int, list[int]],
    node_count: int,
    hmcr: float,
    par: float,
    rng: random.Random,
) -> list[int]:
    path = [source]
    visited = {source}

    while path[-1] != target and len(path) <= node_count:
        current = path[-1]
        available = [edge for edge in graph.neighbors(current) if edge.to not in visited or edge.to == target]
        if not available:
            return []

        memory_options = [node for node in successor_map.get(current, []) if node not in visited or node == target]
        if memory_options and rng.random() < hmcr:
            next_node = rng.choice(memory_options)
        else:
            next_node = rng.choice(available).to

        if rng.random() < par:
            next_node = min(available, key=lambda edge: edge.weight).to

        path.append(next_node)
        visited.add(next_node)

    return path if path[-1] == target else []


def _memory_successor_map(memory: list[list[int]]) -> dict[int, list[int]]:
    successors: dict[int, list[int]] = {}
    for harmony in memory:
        for index, node in enumerate(harmony[:-1]):
            candidate = harmony[index + 1]
            successors.setdefault(node, []).append(candidate)
    return successors


def _unweighted_path(graph: WeightedGraph, source: int, target: int) -> list[int]:
    queue: deque[int] = deque([source])
    previous: dict[int, int | None] = {source: None}
    while queue:
        node = queue.popleft()
        if node == target:
            break
        for edge in graph.neighbors(node):
            if edge.to not in previous:
                previous[edge.to] = node
                queue.append(edge.to)
    if target not in previous:
        return []
    path = [target]
    while previous[path[-1]] is not None:
        parent = previous[path[-1]]
        if parent is not None:
            path.append(parent)
    path.reverse()
    return path
