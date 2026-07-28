import math
import unittest

from routing_project.algorithms import astar, bellman_ford, dijkstra, harmony_search
from routing_project.graph import WeightedGraph


def known_graph():
    graph = WeightedGraph()
    graph.add_edge(0, 1, 2)
    graph.add_edge(0, 2, 5)
    graph.add_edge(1, 2, 1)
    graph.add_edge(1, 3, 4)
    graph.add_edge(2, 3, 1)
    return graph


class AlgorithmTests(unittest.TestCase):
    def test_exact_algorithms_find_known_shortest_path(self):
        graph = known_graph()

        for algorithm in (dijkstra, bellman_ford, astar):
            result = algorithm(graph, 0, 3)
            self.assertTrue(result.success, algorithm.__name__)
            self.assertEqual(result.path, [0, 1, 2, 3])
            self.assertEqual(result.cost, 4)

    def test_astar_zero_heuristic_matches_dijkstra(self):
        graph = known_graph()

        dijkstra_result = dijkstra(graph, 0, 3)
        astar_result = astar(graph, 0, 3, heuristic=lambda _: 0)

        self.assertEqual(astar_result.path, dijkstra_result.path)
        self.assertEqual(astar_result.cost, dijkstra_result.cost)

    def test_bellman_ford_detects_negative_cycle(self):
        graph = WeightedGraph(directed=True)
        graph.add_edge(0, 1, 1)
        graph.add_edge(1, 2, -3)
        graph.add_edge(2, 1, 1)

        result = bellman_ford(graph, 0, 2)

        self.assertFalse(result.success)
        self.assertTrue(result.metadata["negative_cycle"])
        self.assertEqual(result.cost, -math.inf)

    def test_harmony_search_returns_valid_path(self):
        graph = known_graph()

        result = harmony_search(graph, 0, 3, hms=8, iterations=20, seed=123)

        self.assertTrue(result.success)
        self.assertEqual(result.path[0], 0)
        self.assertEqual(result.path[-1], 3)
        self.assertEqual(result.cost, graph.path_cost(result.path))


if __name__ == "__main__":
    unittest.main()
