# Network_Routing_Optimization
The purpose of this project is compare algorithms on weighted graphs with 4 different algorithms.
This project will use Dijkstra's, Bellman Ford, A*, and Harmoncy search as the comparisons. We will also
be comparing the efficiency between C++ algorithms and Python algorithms as well.

## Team
- Spencer Kirksey(https://github.com/DeezyDeeDEE) - Organizer
- Aaron Werth(https://github.com/awwerth42) - Python Collaborator
- Derek Nelson(https://github.com/Nex-png) - Python Collaborator
- Alan Tate(https://github.com/Reaper51322) - C++ Collaborator

## Structure
- `/Code/Python Folder/`: code that contains the implementations of Derek and Aaron
- `/Code/C++ Folder/`: Code that contains the implementation of the algorithms from Alan
- `/Reports/`: Contains the reports of the implementations of Alan and Derek's Code
- `/Results/`: These are the results of our work
- `/Datasets/`: These are the datasets that we use for our code
- `/Tables & Graphs/`: Contains the graphs of Aaron's, Alan's, and Derek's implementations.

# How To Run Code For Each Implementation
## Derek Implementation
### Setup
- Navigate to `/Code/Python/Derek Implementation/`


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


```powershell
python -m routing_project.cli list-datasets
python -m routing_project.cli run-real
python -m routing_project.cli run-real --datasets facebook oregon1 --sample 5000
```

Files download once into `data/` and are cached. Two modelling decisions matter
for the report:


## Charts

```powershell
python -m routing_project.cli make-charts --input results/raw/checkpoint_experiment.csv --output-dir results/charts
python -m routing_project.cli make-charts --input results/raw/real_experiment.csv --output-dir results/charts/real
```
## Aaron Implementation
- Navigate to `/Code/Python/Aaron Implementation/`
To run, simply input the following
```powershell
./topscript.sh
```

## Alan Implementation
- Navigate to `/Code/C++ Code/`
## Commands to Run
.\routing_benchmark.exe Datasets Results  ,   .\run_all.ps1
 
g++ Code\benchmark_main.cpp Code\dijkstra.cpp Code\bellman_ford.cpp Code\astar.cpp Code\harmony_search.cpp -o routing_benchmark.exe -std=c++17 -O2
 
.\routing.exe dijkstra Datasets\graph_4096.txt 1 2500
 
