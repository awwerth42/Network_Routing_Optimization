#include "common.hpp"
#include <filesystem>
#include <iostream>

using Runner = AlgorithmResult (*)(const Graph&, int, int);

static void writeHeader(std::ofstream& out) {
    out << "Graph Size,Source,Target,Run 1 (ms),Run 2 (ms),Run 3 (ms),Run 4 (ms),Run 5 (ms),Mean Time (ms),Distance,Path Length\n";
}

static double mean(const std::vector<double>& values) {
    double total=0.0; for (double v: values) total += v; return total/values.size();
}

static void writeRow(std::ofstream& out, int size, const std::vector<double>& times,
                     const AlgorithmResult& result) {
    out << size << ",1," << size;
    out << std::fixed << std::setprecision(6);
    for (double value : times) out << ',' << value;
    out << ',' << mean(times) << ',';
    if (result.distance >= 1000000000) out << "Not found,0\n";
    else out << result.distance << ',' << result.path.size() << "\n";
}

int main(int argc, char* argv[]) {
    try {
        const std::string dataDirectory = argc >= 2 ? argv[1] : "Datasets";
        const std::string resultsDirectory = argc >= 3 ? argv[2] : "Results";
        std::filesystem::create_directories(resultsDirectory);
        const std::vector<int> sizes{10,64,100,128,256,512,1024,2048,4096};

        std::ofstream dijkstraOut(resultsDirectory + "/dijkstra_results.csv");
        std::ofstream bellmanOut(resultsDirectory + "/bellman_ford_results.csv");
        std::ofstream astarOut(resultsDirectory + "/astar_results.csv");
        std::ofstream harmonyOut(resultsDirectory + "/harmony_search_results.csv");
        std::ofstream combined(resultsDirectory + "/combined_mean_results.csv");
        writeHeader(dijkstraOut); writeHeader(bellmanOut); writeHeader(astarOut); writeHeader(harmonyOut);
        combined << "Graph Size,Dijkstra Mean (ms),Bellman-Ford Mean (ms),A* Mean (ms),Harmony Search Mean (ms)\n";

        std::cout << "Source node is always 1. Target node is always the graph size.\n";
        std::cout << "Each algorithm is timed 5 times per graph. Loading is excluded.\n\n";

        for (int size : sizes) {
            const Graph graph = loadGraph(dataDirectory + "/graph_" + std::to_string(size) + ".txt", size);
            std::vector<double> dt, bt, at, ht;
            AlgorithmResult dr, br, ar, hr;
            for (int run=0; run<5; ++run) { dr=runDijkstra(graph,1,size); dt.push_back(dr.milliseconds); }
            for (int run=0; run<5; ++run) { br=runBellmanFord(graph,1,size); bt.push_back(br.milliseconds); }
            for (int run=0; run<5; ++run) { ar=runAStar(graph,1,size); at.push_back(ar.milliseconds); }
            for (int run=0; run<5; ++run) { hr=runHarmonySearch(graph,1,size,2400u+size*10u+run); ht.push_back(hr.milliseconds); }
            writeRow(dijkstraOut,size,dt,dr); writeRow(bellmanOut,size,bt,br);
            writeRow(astarOut,size,at,ar); writeRow(harmonyOut,size,ht,hr);
            combined << size << std::fixed << std::setprecision(6) << ',' << mean(dt) << ',' << mean(bt) << ',' << mean(at) << ',' << mean(ht) << '\n';
            std::cout << "Finished graph size " << size << "\n";
        }
        std::cout << "\nCSV files created in " << resultsDirectory << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n'; return 1;
    }
}
