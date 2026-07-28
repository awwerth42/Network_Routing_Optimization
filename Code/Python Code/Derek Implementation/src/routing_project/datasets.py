"""Real-world network datasets from the Stanford SNAP collection.

Source: https://snap.stanford.edu/data/

The synthetic generator in :mod:`routing_project.graph` builds graphs by drawing
each possible edge with a fixed probability, so edge count grows with the square
of the node count. Real networks do not behave that way: a road network has a
nearly constant average degree, while a social graph has a heavy-tailed degree
distribution. Running the same algorithms on both lets the report separate
"what the algorithms do" from "what our graph generator does".

Two deliberate modelling choices are documented here because they must be stated
in the report:

1. SNAP ships these graphs unweighted. Routing needs weights, so a deterministic
   pseudo-random weight is derived from the edge endpoints. The weight depends
   only on the endpoint pair and the seed, never on file or traversal order, so
   the same edge always receives the same weight even when the graph is sampled.
2. Bellman-Ford is Theta(V * E), which makes the full million-node road networks
   infeasible in pure Python within the semester. Large graphs are therefore
   reduced with a breadth-first sample that preserves local topology and stays
   connected by construction.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import gzip
from pathlib import Path
from typing import Iterator
import urllib.request

from routing_project.graph import WeightedGraph


SNAP_BASE_URL = "https://snap.stanford.edu/data"


@dataclass(frozen=True)
class SnapDataset:
    """Metadata for one SNAP network."""

    key: str
    name: str
    filename: str
    nodes: int
    edges: int
    category: str
    description: str

    @property
    def url(self) -> str:
        return f"{SNAP_BASE_URL}/{self.filename}"


DATASETS: dict[str, SnapDataset] = {
    "facebook": SnapDataset(
        key="facebook",
        name="ego-Facebook",
        filename="facebook_combined.txt.gz",
        nodes=4039,
        edges=88234,
        category="social",
        description=(
            "Combined Facebook ego networks. Dense, heavy-tailed degree "
            "distribution; a high-degree contrast case against the road network."
        ),
    ),
    "oregon1": SnapDataset(
        key="oregon1",
        name="Oregon-1 autonomous systems",
        filename="oregon1_010331.txt.gz",
        nodes=10670,
        edges=22002,
        category="internet",
        description=(
            "Autonomous-system peering graph inferred from Oregon route views, "
            "31 March 2001. Real internet routing topology."
        ),
    ),
    "roadnet-pa": SnapDataset(
        key="roadnet-pa",
        name="roadNet-PA",
        filename="roadNet-PA.txt.gz",
        nodes=1088092,
        edges=1541898,
        category="road",
        description=(
            "Pennsylvania road network. Intersections are nodes and road "
            "segments are edges; near-constant average degree, unlike the "
            "synthetic generator."
        ),
    ),
}


def get_dataset(key: str) -> SnapDataset:
    try:
        return DATASETS[key]
    except KeyError as exc:
        available = ", ".join(sorted(DATASETS))
        raise ValueError(f"Unknown dataset {key!r}. Available: {available}.") from exc


def download_dataset(dataset: SnapDataset, data_dir: Path) -> Path:
    """Download ``dataset`` into ``data_dir`` unless it is already cached."""

    data_dir.mkdir(parents=True, exist_ok=True)
    destination = data_dir / dataset.filename
    if destination.exists() and destination.stat().st_size > 0:
        return destination

    request = urllib.request.Request(dataset.url, headers={"User-Agent": "routing-project/0.1"})
    temporary = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
        while chunk := response.read(1 << 16):
            handle.write(chunk)
    temporary.replace(destination)
    return destination


def iter_edges(path: Path) -> Iterator[tuple[int, int]]:
    """Stream ``(source, target)`` pairs from a SNAP gzipped edge list.

    SNAP edge lists are tab-separated with ``#`` comment headers. Streaming
    keeps peak memory proportional to the graph rather than the file.
    """

    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line or line[0] == "#":
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            yield int(parts[0]), int(parts[1])


def edge_weight_for(source: int, target: int, seed: int, min_weight: int, max_weight: int) -> int:
    """Derive a deterministic weight from an unordered endpoint pair.

    SNAP graphs are unweighted, so weights are synthesised. Using an
    order-independent integer hash (rather than a sequential RNG) guarantees the
    same edge gets the same weight in the full graph and in any sample, which is
    what makes sampled runs comparable to full-graph runs.
    """

    low, high = (source, target) if source <= target else (target, source)
    value = (low * 0x9E3779B1) ^ (high * 0x85EBCA6B) ^ (seed * 0xC2B2AE35)
    value &= 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    value ^= value >> 16
    return min_weight + (value % (max_weight - min_weight + 1))


def build_adjacency(path: Path) -> dict[int, list[int]]:
    """Build an undirected, de-duplicated adjacency map from a SNAP edge list.

    Some SNAP files (the road networks in particular) list every undirected
    edge once in each direction. Left alone that would double every degree and
    the reported edge count, so neighbour lists are de-duplicated in a single
    pass at the end rather than by tracking a set of seen edges while parsing.
    """

    adjacency: dict[int, list[int]] = {}
    for source, target in iter_edges(path):
        if source == target:
            continue
        adjacency.setdefault(source, []).append(target)
        adjacency.setdefault(target, []).append(source)

    for node, neighbors in adjacency.items():
        if len(neighbors) > 1:
            adjacency[node] = list(dict.fromkeys(neighbors))
    return adjacency


def breadth_first_order(adjacency: dict[int, list[int]], root: int, limit: int | None = None) -> list[int]:
    """Return nodes in BFS order from ``root``, stopping after ``limit`` nodes.

    Because the result is a BFS frontier, the last node returned is among the
    hop-furthest from the root in the sampled region. Using it as the routing
    target avoids trivially short queries.
    """

    order: list[int] = [root]
    seen = {root}
    queue = deque([root])
    while queue:
        if limit is not None and len(order) >= limit:
            break
        node = queue.popleft()
        for neighbor in adjacency.get(node, ()):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            order.append(neighbor)
            queue.append(neighbor)
            if limit is not None and len(order) >= limit:
                break
    return order


def _default_root(adjacency: dict[int, list[int]]) -> int:
    """Pick a deterministic, well-connected starting node."""

    best_node = None
    best_degree = -1
    for node in sorted(adjacency):
        degree = len(adjacency[node])
        if degree > best_degree:
            best_node, best_degree = node, degree
    if best_node is None:
        raise ValueError("Graph has no nodes.")
    return best_node


@dataclass
class LoadedGraph:
    """A SNAP graph prepared for routing experiments."""

    graph: WeightedGraph
    dataset: SnapDataset
    source: int
    target: int
    sampled: bool
    original_nodes: int
    original_edges: int

    @property
    def graph_id(self) -> str:
        suffix = f"_sample{self.graph.node_count()}" if self.sampled else "_full"
        return f"snap_{self.dataset.key}{suffix}"


def load_snap_graph(
    dataset: SnapDataset,
    data_dir: Path,
    sample_size: int | None = None,
    weight_seed: int = 2400,
    min_weight: int = 1,
    max_weight: int = 100,
    root: int | None = None,
) -> LoadedGraph:
    """Download, parse, weight, and optionally sample a SNAP network."""

    if sample_size is not None and sample_size < 2:
        raise ValueError("sample_size must be at least 2.")

    path = download_dataset(dataset, data_dir)
    adjacency = build_adjacency(path)
    original_nodes = len(adjacency)
    original_edges = sum(len(neighbors) for neighbors in adjacency.values()) // 2

    start = _default_root(adjacency) if root is None else root
    if start not in adjacency:
        raise ValueError(f"Root node {start} is not present in {dataset.name}.")

    # BFS from a single root also restricts the result to one connected
    # component, which is what guarantees every source-target query is solvable.
    order = breadth_first_order(adjacency, start, limit=sample_size)
    keep = set(order)
    sampled = sample_size is not None

    graph = WeightedGraph(directed=False)
    for node in order:
        graph.add_node(node)
    for node in order:
        for neighbor in adjacency[node]:
            if neighbor in keep and node < neighbor:
                graph.add_edge(
                    node,
                    neighbor,
                    edge_weight_for(node, neighbor, weight_seed, min_weight, max_weight),
                )

    return LoadedGraph(
        graph=graph,
        dataset=dataset,
        source=order[0],
        target=order[-1],
        sampled=sampled,
        original_nodes=original_nodes,
        original_edges=original_edges,
    )
