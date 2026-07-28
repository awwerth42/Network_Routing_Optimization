#pragma once
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <limits>
#include <queue>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

struct Edge { int to; int weight; };
using Graph = std::vector<std::vector<Edge>>;

struct AlgorithmResult {
    double milliseconds = 0.0;
    int distance = std::numeric_limits<int>::max();
    std::vector<int> path;
};

inline Graph loadGraph(const std::string& filename, int expectedNodes) {
    std::ifstream input(filename);
    if (!input) throw std::runtime_error("Could not open " + filename);
    Graph graph(expectedNodes + 1);
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream in(line);
        int u, v;
        if (!(in >> u >> v)) continue;
        if (u < 1 || v < 1 || u > expectedNodes || v > expectedNodes) {
            throw std::runtime_error("Dataset contains a node outside 1..N");
        }
        graph[u].push_back({v, 1});
        graph[v].push_back({u, 1});
    }
    return graph;
}

inline std::vector<int> buildPath(int source, int target, const std::vector<int>& previous) {
    std::vector<int> path;
    if (target < 0 || target >= static_cast<int>(previous.size())) return path;
    int current = target;
    while (current != -1) {
        path.push_back(current);
        if (current == source) break;
        current = previous[current];
    }
    if (path.empty() || path.back() != source) return {};
    std::reverse(path.begin(), path.end());
    return path;
}

AlgorithmResult runDijkstra(const Graph&, int, int);
AlgorithmResult runBellmanFord(const Graph&, int, int);
AlgorithmResult runAStar(const Graph&, int, int);
AlgorithmResult runHarmonySearch(const Graph&, int, int, unsigned int);
