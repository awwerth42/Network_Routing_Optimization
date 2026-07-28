# CSC 2400 Term Project: Second Checkpoint Report

Aaron Werth, Spencer Kirksey, Derek Nelson, Alan Tate

## Project Status

Our project investigates routing on weighted network graphs by comparing three
classical algorithms, Dijkstra, Bellman-Ford, and A*, with the nature-inspired
Harmony Search algorithm. Since the first checkpoint, the project plan has been
translated into a working Python repository with organized source code, tests,
experiment scripts, result folders, and chart generation.

The current codebase includes a reusable weighted graph representation and a
connected random graph generator. The generator creates positive integer edge
weights and supports sparse, moderate, and dense graph settings so each
algorithm can be evaluated on the same graph instances. This directly supports
the checkpoint-one plan to compare runtime, path cost, and Harmony Search
behavior as graph size and density change.

## Coding Progress

Dijkstra is implemented as the primary benchmark using a priority queue.
Bellman-Ford is implemented as a general classical baseline and includes
negative-cycle detection for correctness testing. A* is implemented with a
pluggable heuristic; the experiments use a zero heuristic on random weighted
graphs so the algorithm remains directly comparable to Dijkstra, while the code
also supports coordinate-based heuristics for later experiments.

Harmony Search is implemented as the main nature-inspired algorithm. Candidate
solutions are encoded as valid source-to-target paths. The implementation uses
Harmony Memory Consideration Rate, Pitch Adjustment Rate, Harmony Memory Size,
iteration count, and random seed as configurable parameters. It also records
convergence history so the team can study how the best path cost changes over
time.

All algorithms return a shared result format containing the path, path cost,
runtime, success status, and metadata. This makes the experiment code simpler
and allows results from all algorithms to be written to the same CSV format.

## Results Generation

The repository includes command-line tools for a quick small experiment, a
larger checkpoint grid, a Harmony Search parameter sweep, and chart generation.
The small experiment is intended for fast verification before committing code.
The checkpoint grid uses the planned graph sizes of 50, 250, and 1000 nodes
across sparse, moderate, and dense graphs. The parameter sweep uses the planned
values `HMCR={0.7, 0.8, 0.9}`, `PAR={0.1, 0.3, 0.5}`, and
`HMS={10, 30, 50}`.

Experiment results are saved in `results/raw/` as CSV files. Charts are saved in
`results/charts/` as SVG files, including runtime comparisons, path-cost
comparisons, and Harmony Search error relative to Dijkstra. This gives the team
the tables and graphs needed for the final project report.

## Experiment Decisions

The team decided to use randomly generated connected graphs as the main
controlled experiment data. This makes it possible to vary node count, density,
and random seed while keeping every algorithm on the same graph instance. The
project may still add real network topology data later, but random graphs are
the safest way to guarantee consistent, repeatable comparisons for the second
checkpoint.

For A*, the current experiments use a zero heuristic because the random edge
weights are not based on physical distance. This keeps A* optimal and comparable
to Dijkstra. If the project later uses coordinate-based graphs where geometric
distance is meaningful, the existing A* interface can use a Euclidean heuristic.

For Harmony Search, multiple trials are used because the algorithm is
stochastic. The result CSV records the seed and parameter settings so runs can
be reproduced and compared.

## Challenges and Next Steps

The main technical challenge is ensuring Harmony Search is evaluated fairly.
Unlike Dijkstra, Bellman-Ford, and A*, Harmony Search is approximate and
parameter-sensitive. Poor settings for HMCR, PAR, or HMS could make the
algorithm look worse than it is, so the parameter sweep is important before the
final report.

Another challenge is runtime. Large dense graphs and repeated Harmony Search
trials can produce many experiment runs. The next step is to run the small
experiment first, confirm the outputs, then run the larger checkpoint grid and
parameter sweep as time allows.

