DEREK IMPLEMENTATION - Python routing algorithm comparison
==========================================================

Compares Dijkstra, Bellman-Ford, A*, and Harmony Search on both synthetic
graphs and real networks from the Stanford SNAP collection.

Requires Python 3.10+. There are NO third-party dependencies - everything
used is Python standard library.


HOW TO RUN
----------
Open a terminal IN THIS FOLDER. The path contains spaces, so quote it:

    cd "Code/Python Code/Derek Implementation"

Then make the package importable for the session:

    Windows PowerShell:   $env:PYTHONPATH = "src"
    Windows cmd.exe:      set PYTHONPATH=src
    macOS / Linux:        export PYTHONPATH=src

Then run any of these:

    python -m routing_project.cli gui             Interactive web GUI (opens
                                                  a browser; run experiments
                                                  and watch them live)
    python -m routing_project.cli run-small       Quick check, under 1 second
    python -m routing_project.cli run-real        Real SNAP networks
    python -m routing_project.cli run-checkpoint  Full synthetic grid
    python -m routing_project.cli run-sweep       Harmony Search parameter sweep
    python -m routing_project.cli list-datasets   Show available SNAP datasets

Verify everything works (needs no setup at all):

    python -m unittest discover

Expect "Ran 36 tests ... OK".


WHERE THE RESULTS ARE IN THIS REPOSITORY
----------------------------------------
Running the commands above writes into results/ inside THIS folder. The
committed copies of those outputs live elsewhere in the repo, following the
team's folder layout:

    Results/Python Results-Derek/raw/       CSV data, one row per run
    Results/Python Results-Derek/charts/    charts from synthetic graphs
    Results/Python Results-Derek/charts/real/   charts from the SNAP networks

results_summary.md in each charts folder lists the machine used, the
per-algorithm averages, and the interpretation notes for the report.


DATA USED
---------
Three real networks from https://snap.stanford.edu/data/ :

    ego-Facebook        4,039 nodes / 88,234 edges   (complete graph)
    Oregon-1 AS        10,670 nodes / 22,002 edges   (sampled to 8,000)
    roadNet-PA      1,088,092 nodes / 1,541,898 edges (sampled to 8,000)

Two things to note when citing these results:

  * SNAP ships these graphs UNWEIGHTED. Routing needs weights, so each edge
    weight is derived from a hash of its two endpoint IDs plus a fixed seed
    (2400), in the range 1-100. The same edge always gets the same weight,
    so runs are reproducible.

  * The two large graphs are breadth-first subsamples, not the full networks.
    Bellman-Ford is Theta(V*E), so the full million-node road network is not
    runnable in pure Python within the semester. A BFS sample stays connected
    by construction.


KNOWN LIMITATIONS (state these in the report)
---------------------------------------------
  * A* uses a zero heuristic, so it is algorithmically identical to Dijkstra
    here. SNAP provides no node coordinates and the synthetic weights are not
    tied to geometry, so no admissible geometric heuristic was available. Any
    runtime difference between A* and Dijkstra is measurement noise.

  * Bellman-Ford stops early once a pass changes nothing, so it rarely reaches
    its Theta(V*E) worst case. Its measured cost depends on edge ordering.

  * Each graph was tested on a single source-to-target query, not averaged
    over many node pairs.


FULL DOCUMENTATION
------------------
SETUP.md in this folder has the complete install guide, all requirements, and
a troubleshooting section. README.md has the project overview and the result
file format.
