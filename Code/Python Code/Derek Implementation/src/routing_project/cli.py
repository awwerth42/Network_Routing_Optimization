"""Command-line entry points for experiments and chart generation.

HOW TO RUN THIS PROGRAM FROM THE COMMAND LINE
---------------------------------------------
From the repository root, first make the package importable. Either install it::

    python -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1          (Windows)
    source .venv/bin/activate               (macOS/Linux)
    python -m pip install -e .

or, without installing, set the source path for the session::

    $env:PYTHONPATH = "src"                 (Windows PowerShell)
    export PYTHONPATH=src                   (macOS/Linux)

Then run any of the following commands::

    # 0. Interactive GUI - run experiments in a browser and watch them live.
    python -m routing_project.cli gui

    # 1. Quick synthetic experiment (seconds) - use this to verify the setup.
    python -m routing_project.cli run-small

    # 2. Full synthetic grid: 50/250/1000 nodes x sparse/moderate/dense.
    python -m routing_project.cli run-checkpoint

    # 3. Real-world SNAP networks (downloads data on first run, ~10 MB).
    python -m routing_project.cli run-real
    python -m routing_project.cli run-real --datasets facebook oregon1 --sample 5000

    # 4. Harmony Search parameter sweep over HMCR x PAR x HMS.
    python -m routing_project.cli run-sweep --trials 10 --iterations 250

    # 5. List the available SNAP datasets and their sizes.
    python -m routing_project.cli list-datasets

    # 6. Turn any result CSV into SVG charts plus a Markdown summary.
    python -m routing_project.cli make-charts --input results/raw/real_experiment.csv

Every run writes a CSV to results/raw/ and a machine description to
results/raw/environment.json. Chart output goes to results/charts/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from routing_project.charts import make_charts
from routing_project.datasets import DATASETS
from routing_project.experiments import (
    CHECKPOINT_CONFIG,
    SMALL_CONFIG,
    RealDataConfig,
    format_result_summary,
    run_experiment,
    run_parameter_sweep,
    run_real_experiment,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "results" / "raw"
CHART_DIR = PROJECT_ROOT / "results" / "charts"
DATA_DIR = PROJECT_ROOT / "data"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CSC 2400 routing project tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    small = subparsers.add_parser("run-small", help="Run a quick checkpoint-sized experiment.")
    small.add_argument("--output", type=Path, default=RAW_DIR / "small_experiment.csv")

    checkpoint = subparsers.add_parser("run-checkpoint", help="Run the larger checkpoint grid.")
    checkpoint.add_argument("--output", type=Path, default=RAW_DIR / "checkpoint_experiment.csv")

    sweep = subparsers.add_parser("run-sweep", help="Run the Harmony Search parameter sweep.")
    sweep.add_argument("--output", type=Path, default=RAW_DIR / "harmony_parameter_sweep.csv")
    sweep.add_argument("--nodes", type=int, default=500, help="Number of graph nodes for the sweep.")
    sweep.add_argument("--trials", type=int, default=3, help="Trials per parameter combination.")
    sweep.add_argument("--iterations", type=int, default=100, help="Harmony Search iterations per trial.")

    real = subparsers.add_parser("run-real", help="Run all algorithms on real SNAP networks.")
    real.add_argument("--output", type=Path, default=RAW_DIR / "real_experiment.csv")
    real.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Cache directory for downloads.")
    real.add_argument(
        "--datasets",
        nargs="+",
        choices=sorted(DATASETS),
        default=list(RealDataConfig.dataset_keys),
        help="Which SNAP datasets to run.",
    )
    real.add_argument(
        "--sample",
        type=int,
        default=8000,
        help="BFS sample size per graph; use 0 for the full graph (slow on road networks).",
    )
    real.add_argument("--trials", type=int, default=10, help="Harmony Search trials per graph.")
    real.add_argument("--iterations", type=int, default=250, help="Harmony Search iterations per trial.")

    subparsers.add_parser("list-datasets", help="Show the available SNAP datasets.")

    gui = subparsers.add_parser("gui", help="Launch the interactive web GUI.")
    gui.add_argument("--host", default="127.0.0.1", help="Interface to bind.")
    gui.add_argument("--port", type=int, default=8000, help="Port to bind; 0 picks a free port.")
    gui.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically.")

    charts = subparsers.add_parser("make-charts", help="Create SVG charts from a CSV result file.")
    charts.add_argument("--input", type=Path, default=RAW_DIR / "small_experiment.csv")
    charts.add_argument("--output-dir", type=Path, default=CHART_DIR)

    args = parser.parse_args(argv)

    if args.command == "run-small":
        rows = run_experiment(SMALL_CONFIG, args.output)
        print(f"Wrote {len(rows)} rows to {args.output}")
        print(format_result_summary(rows))
    elif args.command == "run-checkpoint":
        rows = run_experiment(CHECKPOINT_CONFIG, args.output)
        print(f"Wrote {len(rows)} rows to {args.output}")
        print(format_result_summary(rows))
    elif args.command == "run-sweep":
        rows = run_parameter_sweep(
            args.output,
            node_count=args.nodes,
            trials=args.trials,
            iterations=args.iterations,
            progress=True,
        )
        print(f"Wrote {len(rows)} rows to {args.output}")
        print(format_result_summary(rows))
    elif args.command == "run-real":
        config = RealDataConfig(
            dataset_keys=tuple(args.datasets),
            sample_size=args.sample if args.sample > 0 else None,
            harmony_trials=args.trials,
            harmony_iterations=args.iterations,
        )
        rows = run_real_experiment(config, args.output, args.data_dir, progress=True)
        print(f"Wrote {len(rows)} rows to {args.output}")
        print(format_result_summary(rows))
    elif args.command == "list-datasets":
        print(f"{'key':<12} {'nodes':>10} {'edges':>10}  name")
        for key in sorted(DATASETS):
            dataset = DATASETS[key]
            print(f"{key:<12} {dataset.nodes:>10,} {dataset.edges:>10,}  {dataset.name}")
            print(f"{'':<12} {dataset.url}")
    elif args.command == "gui":
        # Imported lazily so the other commands never pay for the server module.
        from routing_project.webapp import serve

        serve(host=args.host, port=args.port, open_browser=not args.no_browser)
    elif args.command == "make-charts":
        outputs = make_charts(args.input, args.output_dir)
        for output in outputs:
            print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
