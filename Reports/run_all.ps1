$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "Compiling the four original C++ algorithm implementations..."
g++ Code/benchmark_main.cpp Code/dijkstra.cpp Code/bellman_ford.cpp Code/astar.cpp Code/harmony_search.cpp -o routing_benchmark.exe -std=c++17 -O2 -Wall -Wextra
Write-Host "Running 5 trials for each algorithm and graph size..."
.\routing_benchmark.exe Datasets Results
Write-Host "Finished. Open the Results folder for the CSV files."
