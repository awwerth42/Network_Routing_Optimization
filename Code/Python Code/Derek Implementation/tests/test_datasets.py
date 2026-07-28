"""Tests for the SNAP dataset loader.

These tests never touch the network. A tiny gzipped edge list is written to a
temporary directory using the real dataset filename, so download_dataset finds
it already cached and the parsing/sampling/weighting path runs unchanged.
"""

import gzip
import tempfile
import unittest
from pathlib import Path

from routing_project.datasets import (
    DATASETS,
    SnapDataset,
    breadth_first_order,
    build_adjacency,
    edge_weight_for,
    get_dataset,
    iter_edges,
    load_snap_graph,
)


FIXTURE = SnapDataset(
    key="fixture",
    name="fixture network",
    filename="fixture.txt.gz",
    nodes=6,
    edges=6,
    category="test",
    description="tiny hand-built graph",
)

# A 6-node path with one shortcut, written with a comment header and with one
# edge duplicated in both directions the way SNAP road networks are shipped.
FIXTURE_TEXT = """# Directed graph: fixture.txt
# Nodes: 6 Edges: 6
# FromNodeId\tToNodeId
0\t1
1\t0
1\t2
2\t3
3\t4
4\t5
0\t5
"""


def write_fixture(directory: Path) -> Path:
    path = directory / FIXTURE.filename
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(FIXTURE_TEXT)
    return path


class DatasetRegistryTests(unittest.TestCase):
    def test_registry_covers_the_three_planned_networks(self):
        self.assertEqual(sorted(DATASETS), ["facebook", "oregon1", "roadnet-pa"])

    def test_urls_point_at_snap(self):
        for dataset in DATASETS.values():
            self.assertTrue(dataset.url.startswith("https://snap.stanford.edu/data/"))

    def test_unknown_key_lists_available_options(self):
        with self.assertRaises(ValueError) as context:
            get_dataset("not-a-dataset")
        self.assertIn("facebook", str(context.exception))


class ParsingTests(unittest.TestCase):
    def test_comment_lines_are_skipped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fixture(Path(temp_dir))
            edges = list(iter_edges(path))
        self.assertEqual(len(edges), 7)
        self.assertEqual(edges[0], (0, 1))

    def test_reciprocal_edges_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_fixture(Path(temp_dir))
            adjacency = build_adjacency(path)

        # 0-1 appears in both directions but must count once.
        self.assertEqual(adjacency[0], [1, 5])
        self.assertEqual(sum(len(values) for values in adjacency.values()) // 2, 6)


class WeightTests(unittest.TestCase):
    def test_weight_is_order_independent(self):
        self.assertEqual(edge_weight_for(3, 91, 2400, 1, 100), edge_weight_for(91, 3, 2400, 1, 100))

    def test_weight_is_deterministic_and_in_range(self):
        for source in range(50):
            for target in range(source + 1, 50):
                weight = edge_weight_for(source, target, 2400, 1, 100)
                self.assertEqual(weight, edge_weight_for(source, target, 2400, 1, 100))
                self.assertGreaterEqual(weight, 1)
                self.assertLessEqual(weight, 100)

    def test_different_seeds_give_different_weightings(self):
        first = [edge_weight_for(a, a + 1, 1, 1, 100) for a in range(200)]
        second = [edge_weight_for(a, a + 1, 2, 1, 100) for a in range(200)]
        self.assertNotEqual(first, second)


class SamplingTests(unittest.TestCase):
    def test_breadth_first_order_respects_limit(self):
        adjacency = {0: [1, 2], 1: [0, 3], 2: [0], 3: [1]}
        self.assertEqual(len(breadth_first_order(adjacency, 0, limit=3)), 3)
        self.assertEqual(len(breadth_first_order(adjacency, 0, limit=None)), 4)

    def test_full_load_keeps_every_node_and_edge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_fixture(Path(temp_dir))
            loaded = load_snap_graph(FIXTURE, Path(temp_dir), sample_size=None)

        self.assertEqual(loaded.original_nodes, 6)
        self.assertEqual(loaded.original_edges, 6)
        self.assertEqual(loaded.graph.node_count(), 6)
        self.assertEqual(loaded.graph.edge_count(), 6)
        self.assertFalse(loaded.sampled)

    def test_sampled_graph_is_connected_and_bounded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_fixture(Path(temp_dir))
            loaded = load_snap_graph(FIXTURE, Path(temp_dir), sample_size=4)

        graph = loaded.graph
        self.assertEqual(graph.node_count(), 4)
        self.assertTrue(loaded.sampled)

        visited = {loaded.source}
        stack = [loaded.source]
        while stack:
            for edge in graph.neighbors(stack.pop()):
                if edge.to not in visited:
                    visited.add(edge.to)
                    stack.append(edge.to)
        self.assertEqual(len(visited), graph.node_count())

    def test_sampling_preserves_weights_of_surviving_edges(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_fixture(Path(temp_dir))
            full = load_snap_graph(FIXTURE, Path(temp_dir), sample_size=None).graph
            sample = load_snap_graph(FIXTURE, Path(temp_dir), sample_size=4).graph

        for source, target, weight in sample.edges():
            self.assertEqual(full.edge_weight(source, target), weight)

    def test_endpoints_are_distinct_and_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_fixture(Path(temp_dir))
            loaded = load_snap_graph(FIXTURE, Path(temp_dir), sample_size=None)

        self.assertNotEqual(loaded.source, loaded.target)
        self.assertTrue(loaded.graph.has_node(loaded.source))
        self.assertTrue(loaded.graph.has_node(loaded.target))

    def test_sample_size_below_two_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            write_fixture(Path(temp_dir))
            with self.assertRaises(ValueError):
                load_snap_graph(FIXTURE, Path(temp_dir), sample_size=1)


if __name__ == "__main__":
    unittest.main()
