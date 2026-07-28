# Routing Algorithm Comparison

CSC 2400 term project comparing routing algorithms on weighted network graphs.
The project evaluates Dijkstra, Bellman-Ford, A*, and Harmony Search to study
runtime, path quality, and the tradeoff between exact classical algorithms and
a nature-inspired metaheuristic.

> **New here? Read [SETUP.md](SETUP.md)** for a full install-and-run walkthrough,
> including every requirement and a troubleshooting section.
>
> This code lives on the `derek_branch` branch, not `main`. Fastest path to a
> working demo — no install, no dependencies:
>
> ```powershell
> git clone -b derek_branch https://github.com/DeezyDeeDEE/Network_Routing_Optimization.git
> cd Network_Routing_Optimization
> $env:PYTHONPATH = "src"; python -m routing_project.cli gui
> ```

## Team

- Aaron Werth
- Spencer Kirksey
- Derek Nelson
- Alan Tate



## Repository Structure

- `src/routing_project/`: graph utilities, algorithm implementations, experiment runner, and CLI.
- `src/routing_project/datasets.py`: SNAP real-network downloader, parser, and sampler.
- `src/routing_project/environment.py`: machine/runtime capture for the report.
- `tests/`: unit and smoke tests for graph generation, algorithms, datasets, and result writing.
- `results/raw/`: generated CSV experiment outputs plus `environment.json`.
- `results/charts/`: generated SVG charts for the report (synthetic graphs).
- `results/charts/real/`: charts for the real SNAP networks.
- `data/`: cache for downloaded SNAP files (git-ignored; recreated on demand).
- `reports/`: checkpoint and project reports.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

If you do not create a virtual environment, run commands with `PYTHONPATH=src`.
On PowerShell:

```powershell
$env:PYTHONPATH = "src"
```

## Run Tests

Preferred:

```powershell
python -m pytest
```

Fallback using only the Python standard library:

```powershell
python -m unittest discover
```

## Analysis Notebook

`analysis.ipynb` walks through the whole study in 19 documented code cells:
each algorithm in turn, the scaling experiment, the real SNAP networks, memory
and basic-operation counts, and the Harmony Search parameter sweep. It is
committed **with all outputs saved**, so GitHub renders the tables and the six
figures without anyone running it.

```powershell
python -m pip install -r requirements-dev.txt
jupyter notebook analysis.ipynb
```

Runtime is about two minutes end to end. It imports the same `routing_project`
library the CLI uses, so nothing in it is reimplemented, and its real-data
numbers reproduce the committed charts in `results/charts/real/`.

## Interactive GUI

The fastest way to see the project work is the built-in web GUI:

```powershell
python -m routing_project.cli gui
```

This starts a local server (default <http://127.0.0.1:8000>) and opens a browser.
From there you can pick an experiment, adjust its parameters, press **Run**, and
watch results stream in live: a progress bar, a running log, stat tiles, and four
charts (runtime, path cost, Harmony Search gap above optimal, peak memory) that
redraw as each run finishes. When the experiment ends, the report-quality SVG
charts are generated and shown at the bottom of the page.

Options: `--port 0` picks a free port, `--host 0.0.0.0` exposes it on the
network, `--no-browser` skips opening a browser.

The GUI uses only the Python standard library (`http.server` plus server-sent
events), so it adds no dependencies. Only one experiment runs at a time — these
measurements are wall-clock timings, and two experiments sharing the CPU would
contaminate each other's results.

## Run Experiments

Quick checkpoint run:

```powershell
python -m routing_project.cli run-small
```

Harmony Search parameter sweep:

```powershell
python -m routing_project.cli run-sweep
```

The default sweep tests all HMCR/PAR/HMS combinations at 500 nodes with 3
trials and 100 iterations per trial. For a larger final-analysis run:

```powershell
python -m routing_project.cli run-sweep --trials 10 --iterations 250
```

Larger checkpoint grid:

```powershell
python -m routing_project.cli run-checkpoint
```

## Real-World Data (Stanford SNAP)

Alongside the synthetic graphs, the project runs on real networks from the
[Stanford Large Network Dataset Collection](https://snap.stanford.edu/data/):

| Key | Network | Nodes | Edges | Why it is included |
| --- | --- | ---: | ---: | --- |
| `facebook` | ego-Facebook | 4,039 | 88,234 | Dense social graph, heavy-tailed degrees |
| `oregon1` | Oregon-1 autonomous systems | 10,670 | 22,002 | Real internet routing topology |
| `roadnet-pa` | roadNet-PA | 1,088,092 | 1,541,898 | True road-network structure |

```powershell
python -m routing_project.cli list-datasets
python -m routing_project.cli run-real
python -m routing_project.cli run-real --datasets facebook oregon1 --sample 5000
```

Files download once into `data/` and are cached. Two modelling decisions matter
for the report:

- **Weights are synthetic.** SNAP ships these graphs unweighted, so each edge
  weight is derived from an order-independent hash of its endpoints plus a seed.
  The same edge always gets the same weight, in the full graph and in any sample.
- **Large graphs are sampled.** Bellman-Ford is `Theta(V * E)`, so the full
  million-node road network is not runnable in pure Python within the semester.
  `--sample N` takes a breadth-first sample, which stays connected by
  construction and preserves local topology. The source is the BFS root and the
  target is the furthest node reached, so queries are not trivially short.

## Charts

```powershell
python -m routing_project.cli make-charts --input results/raw/checkpoint_experiment.csv --output-dir results/charts
python -m routing_project.cli make-charts --input results/raw/real_experiment.csv --output-dir results/charts/real
```

This writes SVG charts and `results_summary.md`, which records the machine used,
per-algorithm averages (runtime, path cost, basic operations, peak memory,
success rate), Harmony Search's gap from optimal broken out by input, and the
main interpretation points for the report.

## Result Files

CSV outputs use these fields:

`algorithm`, `graph_id`, `nodes`, `edges`, `density`, `source`, `target`,
`path_cost`, `runtime_ms`, `success`, `graph_source`, `run_type`,
`expanded_nodes`, `edge_examinations`, `relaxations`, `path_evaluations`,
`peak_memory_kb`, `seed`, `hmcr`, `par`, `hms`, `iterations`.

Two columns control how rows are read:

- `graph_source` is `synthetic` or `snap:<key>`.
- `run_type` is `timing` or `memory`. Memory rows are instrumented with
  `tracemalloc`, which inflates runtime, so their `runtime_ms` is deliberately
  excluded from every timing average. Only memory rows carry `peak_memory_kb`.

Each run also writes `results/raw/environment.json` describing the machine, which
the deliverables require the report to state.

## Current Status

Implemented and tested:

- Connected weighted graph generation.
- Dijkstra shortest path.
- Bellman-Ford shortest path and negative-cycle detection.
- A* with a pluggable heuristic.
- Harmony Search with configurable `HMCR`, `PAR`, `HMS`, iteration count, and seed.
- Real SNAP networks with deterministic weighting and breadth-first sampling.
- Basic-operation counts, peak-memory measurement, and machine capture.
- CSV result generation and dependency-free SVG chart generation.

## Known Limitations

These are measurement caveats to state in the report rather than bugs:

- **A\* uses a zero heuristic**, so it is algorithmically identical to Dijkstra
  here. SNAP ships no coordinates, and the synthetic edge weights are not tied to
  geometry, so no admissible geometric heuristic is available. Any Dijkstra/A\*
  runtime difference is noise. A landmark (ALT) heuristic would be the fix.
- **Bellman-Ford stops early** when a pass changes nothing, so it rarely reaches
  its `Theta(V * E)` worst case. Its measured cost depends on edge ordering.
- **Harmony Search runtime is implementation-sensitive.** Candidate paths are now
  scored once and cached; before that, roughly half its runtime was re-scoring
  harmonies rather than searching.

