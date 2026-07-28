#include "common.hpp"

struct Candidate { std::vector<int> path; int fitness; };

static Candidate randomWalk(const Graph& graph, int source, int target,
                            int maxSteps, std::mt19937& rng) {
    std::vector<int> path{source};
    std::vector<bool> seen(graph.size(), false);
    seen[source] = true;
    int current = source;
    for (int step = 0; step < maxSteps && current != target; ++step) {
        std::vector<int> choices;
        for (const Edge& edge : graph[current])
            if (!seen[edge.to] || edge.to == target) choices.push_back(edge.to);
        if (choices.empty()) break;

        // Preserve the original randomized search, with a small pitch-adjustment
        // preference for a node numerically closer to the target.
        std::uniform_real_distribution<double> probability(0.0, 1.0);
        int next;
        if (probability(rng) < 0.25) {
            next = *std::min_element(choices.begin(), choices.end(),
                [target](int a, int b){ return std::abs(target-a) < std::abs(target-b); });
        } else {
            std::uniform_int_distribution<int> pick(0, static_cast<int>(choices.size())-1);
            next = choices[pick(rng)];
        }
        path.push_back(next);
        seen[next] = true;
        current = next;
    }
    const int NOT_FOUND = 1000000000;
    return {path, current == target ? static_cast<int>(path.size())-1 : NOT_FOUND};
}

// Based on the original Harmony Search project: initialize harmony memory with
// random walks, improvise new candidates, replace the worst harmony, and return
// the best path found. It remains approximate rather than guaranteed optimal.
AlgorithmResult runHarmonySearch(const Graph& graph, int source, int target,
                                 unsigned int seed) {
    const int harmonyMemorySize = 50;
    const int iterations = std::max(5000, target * 5);
    const int maxSteps = std::min(500, std::max(50, target / 2));
    std::mt19937 rng(seed);
    std::vector<Candidate> memory;
    memory.reserve(harmonyMemorySize);

    const auto start = std::chrono::steady_clock::now();
    for (int i=0; i<harmonyMemorySize; ++i)
        memory.push_back(randomWalk(graph, source, target, maxSteps, rng));
    for (int i=0; i<iterations; ++i) {
        Candidate candidate = randomWalk(graph, source, target, maxSteps, rng);
        auto worst = std::max_element(memory.begin(), memory.end(),
            [](const Candidate& a, const Candidate& b){ return a.fitness < b.fitness; });
        if (candidate.fitness < worst->fitness) *worst = std::move(candidate);
    }
    auto best = std::min_element(memory.begin(), memory.end(),
        [](const Candidate& a, const Candidate& b){ return a.fitness < b.fitness; });
    const auto stop = std::chrono::steady_clock::now();
    const int NOT_FOUND = 1000000000;
    if (best == memory.end() || best->fitness == NOT_FOUND)
        return {std::chrono::duration<double, std::milli>(stop-start).count(),
                NOT_FOUND, {}};
    return {std::chrono::duration<double, std::milli>(stop-start).count(),
            best->fitness, best->path};
}
