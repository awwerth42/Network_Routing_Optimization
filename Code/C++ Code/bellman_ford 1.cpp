#include "common.hpp"

struct BFEdge { int from; int to; int weight; };

// Based on the original Bellman-Ford implementation. Each undirected adjacency
// is converted to a directed relaxation edge. Early stopping is used when a
// complete pass makes no changes.
AlgorithmResult runBellmanFord(const Graph& graph, int source, int target) {
    std::vector<BFEdge> edges;
    for (int from = 1; from < static_cast<int>(graph.size()); ++from)
        for (const Edge& edge : graph[from]) edges.push_back({from, edge.to, edge.weight});

    const int INF = std::numeric_limits<int>::max() / 4;
    std::vector<int> distance(graph.size(), INF);
    std::vector<int> previous(graph.size(), -1);

    const auto start = std::chrono::steady_clock::now();
    distance[source] = 0;
    for (std::size_t pass = 1; pass + 1 < graph.size(); ++pass) {
        bool changed = false;
        for (const BFEdge& edge : edges) {
            if (distance[edge.from] == INF) continue;
            const int candidate = distance[edge.from] + edge.weight;
            if (candidate < distance[edge.to]) {
                distance[edge.to] = candidate;
                previous[edge.to] = edge.from;
                changed = true;
            }
        }
        if (!changed) break;
    }
    const auto stop = std::chrono::steady_clock::now();
    return {std::chrono::duration<double, std::milli>(stop-start).count(),
            distance[target], buildPath(source, target, previous)};
}
