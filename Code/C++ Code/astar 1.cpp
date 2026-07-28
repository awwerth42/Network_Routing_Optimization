#include "common.hpp"

static int heuristic(int /*node*/, int /*target*/) {
    // The original as-Skitter graph and these generated edge lists have no
    // coordinates, so h(n)=0 is the valid admissible heuristic.
    return 0;
}

// Based on the original A* code. With h(n)=0, it follows the same search order
// as Dijkstra while retaining the A* f(n)=g(n)+h(n) structure.
AlgorithmResult runAStar(const Graph& graph, int source, int target) {
    const int INF = std::numeric_limits<int>::max() / 4;
    std::vector<int> gScore(graph.size(), INF);
    std::vector<int> previous(graph.size(), -1);
    using Item = std::pair<int, int>;
    std::priority_queue<Item, std::vector<Item>, std::greater<Item>> open;

    const auto start = std::chrono::steady_clock::now();
    gScore[source] = 0;
    open.push({heuristic(source, target), source});
    while (!open.empty()) {
        auto [fScore, node] = open.top();
        open.pop();
        if (fScore != gScore[node] + heuristic(node, target)) continue;
        if (node == target) break;
        for (const Edge& edge : graph[node]) {
            const int tentative = gScore[node] + edge.weight;
            if (tentative < gScore[edge.to]) {
                gScore[edge.to] = tentative;
                previous[edge.to] = node;
                open.push({tentative + heuristic(edge.to, target), edge.to});
            }
        }
    }
    const auto stop = std::chrono::steady_clock::now();
    return {std::chrono::duration<double, std::milli>(stop-start).count(),
            gScore[target], buildPath(source, target, previous)};
}
