import unittest

from routing_project.graph import WeightedGraph, generate_connected_graph


class GraphTests(unittest.TestCase):
    def test_add_edge_and_path_cost(self):
        graph = WeightedGraph()
        graph.add_edge(0, 1, 4)
        graph.add_edge(1, 2, 6)

        self.assertTrue(graph.has_edge(0, 1))
        self.assertTrue(graph.has_edge(1, 0))
        self.assertEqual(graph.path_cost([0, 1, 2]), 10)
        self.assertEqual(graph.edge_count(), 2)

    def test_generated_graph_is_connected(self):
        graph = generate_connected_graph(30, density="sparse", seed=7)
        visited = {0}
        stack = [0]
        while stack:
            node = stack.pop()
            for edge in graph.neighbors(node):
                if edge.to not in visited:
                    visited.add(edge.to)
                    stack.append(edge.to)

        self.assertEqual(len(visited), 30)


if __name__ == "__main__":
    unittest.main()
