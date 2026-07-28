"""Experiment pipeline for the routing algorithm comparison."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
import tracemalloc
from typing import Callable, Iterable

from routing_project.algorithms import AlgorithmResult, astar, bellman_ford, dijkstra, harmony_search
from routing_project.datasets import get_dataset, load_snap_graph
from routing_project.environment import write_environment
from routing_project.graph import WeightedGraph, generate_connected_graph


CSV_FIELDS = [
    "algorithm",
    "graph_id",
    "nodes",
    "edges",
    "density",
    "source",
    "target",
    "path_cost",
    "runtime_ms",
    "success",
    "graph_source",
    "run_type",
    "expanded_nodes",
    "edge_examinations",
    "relaxations",
    "path_evaluations",
    "peak_memory_kb",
    "seed",
    "hmcr",
    "par",
    "hms",
    "iterations",
]

# Rows tagged "timing" are clean runs used for runtime analysis. Rows tagged
# "memory" are run under tracemalloc, which inflates runtime, so their
# runtime_ms must be excluded from timing summaries.
TIMING_RUN = "timing"
MEMORY_RUN = "memory"


@dataclass(frozen=True)
class ExperimentConfig:
    node_counts: tuple[int, ...]
    densities: tuple[str, ...]
    graph_seeds: tuple[int, ...]
    deterministic_repeats: int = 3
    harmony_trials: int = 5
    harmony_iterations: int = 150
    hmcr: float = 0.8
    par: float = 0.3
    hms: int = 30
    measure_memory: bool = True


SMALL_CONFIG = ExperimentConfig(
    node_counts=(20, 50),
    densities=("sparse", "moderate"),
    graph_seeds=(11, 23),
    deterministic_repeats=2,
    harmony_trials=3,
    harmony_iterations=80,
)


CHECKPOINT_CONFIG = ExperimentConfig(
    node_counts=(50, 250, 1000),
    densities=("sparse", "moderate", "dense"),
    graph_seeds=(11, 23, 37),
    deterministic_repeats=5,
    harmony_trials=30,
    harmony_iterations=250,
)


def rows_per_graph(config) -> int:
    """How many CSV rows one graph produces, used for progress estimates."""

    memory_runs = 4 if getattr(config, "measure_memory", False) else 0
    return 3 * config.deterministic_repeats + config.harmony_trials + memory_runs


def _emit(on_event: Callable[[dict], None] | None, **event) -> None:
    """Deliver a progress event, if anyone is listening.

    A callback that raises is how a caller signals cancellation, so the
    exception is deliberately allowed to propagate and abort the run.
    """

    if on_event is not None:
        on_event(event)


def run_experiment(
    config: ExperimentConfig,
    output_csv: Path,
    on_event: Callable[[dict], None] | None = None,
) -> list[dict[str, object]]:
    """Run the configured experiment grid and write normalized CSV rows."""

    graph_total = len(config.node_counts) * len(config.densities) * len(config.graph_seeds)
    _emit(
        on_event,
        type="start",
        kind="synthetic",
        graph_total=graph_total,
        row_total=graph_total * rows_per_graph(config),
    )

    rows: list[dict[str, object]] = []
    graph_index = 0
    for node_count in config.node_counts:
        for density in config.densities:
            for graph_seed in config.graph_seeds:
                graph = generate_connected_graph(node_count, density=density, seed=graph_seed)
                graph_id = f"v{node_count}_{density}_seed{graph_seed}"
                source, target = 0, node_count - 1
                graph_index += 1
                _emit(
                    on_event,
                    type="graph",
                    graph_id=graph_id,
                    index=graph_index,
                    total=graph_total,
                    nodes=graph.node_count(),
                    edges=graph.edge_count(),
                    density=density,
                )
                rows.extend(
                    _run_graph_trials(
                        graph,
                        graph_id,
                        density,
                        source,
                        target,
                        config,
                        graph_seed,
                        on_event=on_event,
                    )
                )

    write_rows(output_csv, rows)
    write_environment(output_csv.parent / "environment.json")
    return rows


def run_parameter_sweep(
    output_csv: Path,
    node_count: int = 500,
    trials: int = 3,
    iterations: int = 100,
    progress: bool = False,
    on_event: Callable[[dict], None] | None = None,
) -> list[dict[str, object]]:
    """Run the Harmony Search parameter sweep from the checkpoint-one plan."""

    graph = generate_connected_graph(node_count, density="moderate", seed=101)
    source, target = 0, node_count - 1
    combination_total = 27
    _emit(
        on_event,
        type="start",
        kind="sweep",
        graph_total=combination_total,
        row_total=combination_total * trials,
    )
    _emit(
        on_event,
        type="graph",
        graph_id=f"v{node_count}_moderate_seed101",
        index=0,
        total=combination_total,
        nodes=graph.node_count(),
        edges=graph.edge_count(),
        density="moderate",
    )

    rows: list[dict[str, object]] = []
    combination_index = 0
    for hmcr in (0.7, 0.8, 0.9):
        for par in (0.1, 0.3, 0.5):
            for hms in (10, 30, 50):
                if progress:
                    print(f"Sweeping HMCR={hmcr}, PAR={par}, HMS={hms}")
                combination_index += 1
                _emit(
                    on_event,
                    type="log",
                    message=f"HMCR={hmcr}, PAR={par}, HMS={hms} "
                    f"({combination_index}/{combination_total})",
                )
                for trial in range(trials):
                    result = harmony_search(
                        graph,
                        source,
                        target,
                        hmcr=hmcr,
                        par=par,
                        hms=hms,
                        iterations=iterations,
                        seed=10_000 + trial,
                    )
                    row = result_to_row(
                        result,
                        graph,
                        f"v{node_count}_moderate_seed101",
                        "moderate",
                        source,
                        target,
                    )
                    _emit(on_event, type="row", row=row)
                    rows.append(
                        row
                    )
    write_rows(output_csv, rows)
    write_environment(output_csv.parent / "environment.json")
    return rows


@dataclass(frozen=True)
class RealDataConfig:
    """Settings for experiments on real SNAP networks.

    ``sample_size`` bounds the BFS sample. Bellman-Ford is Theta(V * E), so the
    full million-node road networks are not runnable in pure Python within the
    semester; sampling is what keeps the classical benchmark in the comparison.
    """

    dataset_keys: tuple[str, ...] = ("facebook", "oregon1", "roadnet-pa")
    sample_size: int | None = 8000
    deterministic_repeats: int = 3
    harmony_trials: int = 10
    harmony_iterations: int = 250
    hmcr: float = 0.8
    par: float = 0.3
    hms: int = 30
    measure_memory: bool = True
    weight_seed: int = 2400


def run_real_experiment(
    config: RealDataConfig,
    output_csv: Path,
    data_dir: Path,
    progress: bool = False,
    on_event: Callable[[dict], None] | None = None,
) -> list[dict[str, object]]:
    """Run every algorithm on real SNAP networks and write normalized CSV rows."""

    graph_total = len(config.dataset_keys)
    _emit(
        on_event,
        type="start",
        kind="real",
        graph_total=graph_total,
        row_total=graph_total * rows_per_graph(config),
    )

    rows: list[dict[str, object]] = []
    for index, key in enumerate(config.dataset_keys):
        dataset = get_dataset(key)
        if progress:
            print(f"Loading {dataset.name} from {dataset.url}")
        _emit(on_event, type="log", message=f"Loading {dataset.name} (downloads once, then cached)")
        loaded = load_snap_graph(
            dataset,
            data_dir,
            sample_size=config.sample_size,
            weight_seed=config.weight_seed,
        )
        graph = loaded.graph
        average_degree = 2 * graph.edge_count() / max(1, graph.node_count())
        if progress:
            print(
                f"  {dataset.name}: {graph.node_count()} nodes, {graph.edge_count()} edges, "
                f"avg degree {average_degree:.2f} (source={loaded.source}, target={loaded.target})"
            )
        _emit(
            on_event,
            type="graph",
            graph_id=loaded.graph_id,
            index=index + 1,
            total=graph_total,
            nodes=graph.node_count(),
            edges=graph.edge_count(),
            density=dataset.category,
            label=dataset.name,
            average_degree=round(average_degree, 2),
            original_nodes=loaded.original_nodes,
            original_edges=loaded.original_edges,
            sampled=loaded.sampled,
        )
        rows.extend(
            _run_graph_trials(
                graph,
                loaded.graph_id,
                dataset.category,
                loaded.source,
                loaded.target,
                config,
                graph_seed=7000 + index,
                graph_source=f"snap:{dataset.key}",
                on_event=on_event,
            )
        )

    write_rows(output_csv, rows)
    write_environment(output_csv.parent / "environment.json")
    return rows


def write_rows(output_csv: Path, rows: Iterable[dict[str, object]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def measure_peak_memory(function: Callable[..., AlgorithmResult], *args, **kwargs) -> tuple[AlgorithmResult, float]:
    """Run ``function`` under tracemalloc and report peak allocation in KiB.

    The graph is built before this call, so the peak reflects the memory the
    algorithm itself allocates (distance tables, priority queue, harmony
    memory) rather than the size of the input graph. tracemalloc adds
    significant overhead, so these runs are recorded separately from timing
    runs and never mixed into runtime averages.
    """

    tracemalloc.start()
    try:
        result = function(*args, **kwargs)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, round(peak_bytes / 1024, 3)


def result_to_row(
    result: AlgorithmResult,
    graph: WeightedGraph,
    graph_id: str,
    density: str,
    source: int,
    target: int,
    run_type: str = TIMING_RUN,
    peak_memory_kb: float | None = None,
    node_total: int | None = None,
    edge_total: int | None = None,
    graph_source: str = "synthetic",
) -> dict[str, object]:
    metadata = result.metadata
    return {
        "algorithm": result.algorithm,
        "graph_id": graph_id,
        "nodes": graph.node_count() if node_total is None else node_total,
        "edges": graph.edge_count() if edge_total is None else edge_total,
        "density": density,
        "source": source,
        "target": target,
        "path_cost": round(result.cost, 6) if result.success else "",
        "runtime_ms": round(result.runtime_ms, 6),
        "success": result.success,
        "graph_source": graph_source,
        "run_type": run_type,
        "expanded_nodes": metadata.get("expanded_nodes", ""),
        "edge_examinations": metadata.get("edge_examinations", ""),
        "relaxations": metadata.get("relaxations", ""),
        "path_evaluations": metadata.get("path_evaluations", ""),
        "peak_memory_kb": "" if peak_memory_kb is None else peak_memory_kb,
        "seed": metadata.get("seed", ""),
        "hmcr": metadata.get("hmcr", ""),
        "par": metadata.get("par", ""),
        "hms": metadata.get("hms", ""),
        "iterations": metadata.get("iterations", ""),
    }


def is_timing_row(row: dict[str, object]) -> bool:
    """Treat rows without an explicit run_type as timing rows (legacy CSVs)."""

    return str(row.get("run_type", "") or TIMING_RUN) == TIMING_RUN


def _numeric(rows: Iterable[dict[str, object]], field: str) -> list[float]:
    values = []
    for row in rows:
        raw = row.get(field, "")
        if raw not in ("", None):
            values.append(float(raw))
    return values


def summarize_by_algorithm(rows: Iterable[dict[str, object]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["algorithm"]), []).append(row)

    summary: dict[str, dict[str, float]] = {}
    for algorithm, items in grouped.items():
        timing = [item for item in items if is_timing_row(item)] or items
        memory_rows = [item for item in items if not is_timing_row(item)]

        runtimes = _numeric(timing, "runtime_ms")
        costs = _numeric(timing, "path_cost")
        peaks = _numeric(memory_rows, "peak_memory_kb")
        # Bellman-Ford counts relaxations; the heap-based searches count edge
        # examinations; Harmony Search counts candidate path evaluations.
        operations = _numeric(timing, "edge_examinations") or _numeric(timing, "path_evaluations")

        summary[algorithm] = {
            "mean_runtime_ms": mean(runtimes) if runtimes else 0.0,
            "mean_path_cost": mean(costs) if costs else 0.0,
            "success_rate": sum(str(item["success"]) == "True" for item in timing) / len(timing),
            "mean_peak_memory_kb": mean(peaks) if peaks else 0.0,
            "mean_basic_operations": mean(operations) if operations else 0.0,
        }
    return summary


def format_result_summary(rows: Iterable[dict[str, object]]) -> str:
    """Build a short human-readable interpretation of experiment rows."""

    row_list = list(rows)
    summary = summarize_by_algorithm(row_list)
    if not row_list or not summary:
        return "No result rows were available to summarize."

    fastest = min(summary, key=lambda algorithm: summary[algorithm]["mean_runtime_ms"])
    lowest_cost = min(summary, key=lambda algorithm: summary[algorithm]["mean_path_cost"])
    graph_count = len({str(row["graph_id"]) for row in row_list})
    gap = harmony_gap(row_list)

    lines = [
        "",
        "Result perspective:",
        f"- Compared {len(summary)} algorithms across {graph_count} graph instance(s) and {len(row_list)} total runs.",
        f"- Fastest average runtime: {fastest} ({summary[fastest]['mean_runtime_ms']:.3f} ms).",
        f"- Lowest average path cost: {lowest_cost} ({summary[lowest_cost]['mean_path_cost']:.3f}).",
    ]
    peak_holder = max(summary, key=lambda algorithm: summary[algorithm]["mean_peak_memory_kb"])
    if summary[peak_holder]["mean_peak_memory_kb"] > 0:
        lines.append(
            f"- Highest peak memory: {peak_holder} "
            f"({summary[peak_holder]['mean_peak_memory_kb']:.1f} KiB)."
        )
    if gap is not None:
        lines.append(
            f"- Harmony Search averaged {gap['absolute']:.3f} cost units "
            f"({gap['relative']:.1%}) above Dijkstra, and matched the optimal cost "
            f"on {gap['optimal_rate']:.1%} of runs."
        )
    lines.extend(
        [
            "- Dijkstra is the exact benchmark; matching its path cost means an algorithm found an optimal route.",
            "- Harmony Search is approximate, so its value is judged by how close it gets to Dijkstra and how much runtime it needs.",
        ]
    )
    return "\n".join(lines)


def harmony_gap(rows: Iterable[dict[str, object]]) -> dict[str, float] | None:
    """Compare Harmony Search cost against Dijkstra on matching graph instances.

    Returns both the absolute cost difference and the relative gap. The relative
    gap is the meaningful one for the report, because absolute cost units are
    not comparable across graphs of different sizes.
    """

    dijkstra_cost: dict[str, float] = {}
    harmony_costs: dict[str, list[float]] = {}
    for row in rows:
        if not is_timing_row(row):
            continue
        path_cost = row.get("path_cost")
        if path_cost in ("", None):
            continue
        graph_id = str(row["graph_id"])
        algorithm = str(row["algorithm"])
        cost = float(path_cost)
        if algorithm == "dijkstra":
            dijkstra_cost.setdefault(graph_id, cost)
        elif algorithm == "harmony_search":
            harmony_costs.setdefault(graph_id, []).append(cost)

    absolute: list[float] = []
    relative: list[float] = []
    for graph_id, costs in harmony_costs.items():
        optimal = dijkstra_cost.get(graph_id)
        if optimal is None:
            continue
        for cost in costs:
            absolute.append(cost - optimal)
            if optimal > 0:
                relative.append((cost - optimal) / optimal)

    if not absolute:
        return None
    return {
        "absolute": mean(absolute),
        "relative": mean(relative) if relative else 0.0,
        "optimal_rate": sum(value == 0 for value in absolute) / len(absolute),
    }


def _mean_harmony_error(rows: list[dict[str, object]]) -> float | None:
    gap = harmony_gap(rows)
    return None if gap is None else gap["absolute"]


def _run_graph_trials(
    graph: WeightedGraph,
    graph_id: str,
    density: str,
    source: int,
    target: int,
    config: ExperimentConfig,
    graph_seed: int,
    graph_source: str = "synthetic",
    on_event: Callable[[dict], None] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    node_total = graph.node_count()
    edge_total = graph.edge_count()

    def record(result: AlgorithmResult, run_type: str, peak: float | None = None) -> dict[str, object]:
        built = row(result, run_type, peak)
        _emit(on_event, type="row", row=built)
        return built

    def row(result: AlgorithmResult, run_type: str, peak: float | None = None) -> dict[str, object]:
        return result_to_row(
            result,
            graph,
            graph_id,
            density,
            source,
            target,
            run_type=run_type,
            peak_memory_kb=peak,
            node_total=node_total,
            edge_total=edge_total,
            graph_source=graph_source,
        )

    exact_algorithms = (dijkstra, bellman_ford, astar)
    for algorithm in exact_algorithms:
        for _ in range(config.deterministic_repeats):
            rows.append(record(algorithm(graph, source, target), TIMING_RUN))
        if config.measure_memory:
            result, peak = measure_peak_memory(algorithm, graph, source, target)
            rows.append(record(result, MEMORY_RUN, peak))

    harmony_kwargs = {
        "hmcr": config.hmcr,
        "par": config.par,
        "hms": config.hms,
        "iterations": config.harmony_iterations,
    }
    for trial in range(config.harmony_trials):
        result = harmony_search(graph, source, target, seed=graph_seed * 1000 + trial, **harmony_kwargs)
        rows.append(record(result, TIMING_RUN))

    if config.measure_memory:
        result, peak = measure_peak_memory(
            harmony_search, graph, source, target, seed=graph_seed * 1000, **harmony_kwargs
        )
        rows.append(record(result, MEMORY_RUN, peak))
    return rows
