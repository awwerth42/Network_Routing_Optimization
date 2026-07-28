import tempfile
import unittest
from pathlib import Path

from routing_project.experiments import (
    CSV_FIELDS,
    ExperimentConfig,
    format_result_summary,
    run_experiment,
    run_parameter_sweep,
)


class ExperimentTests(unittest.TestCase):
    def test_tiny_experiment_writes_csv(self):
        config = ExperimentConfig(
            node_counts=(8,),
            densities=("sparse",),
            graph_seeds=(5,),
            deterministic_repeats=1,
            harmony_trials=1,
            harmony_iterations=5,
            hms=4,
            measure_memory=False,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "results.csv"
            rows = run_experiment(config, output)

            self.assertTrue(output.exists())
            self.assertEqual(len(rows), 4)
            header = output.read_text(encoding="utf-8").splitlines()[0].split(",")
            self.assertEqual(header, CSV_FIELDS)

    def test_memory_runs_are_tagged_and_measured(self):
        config = ExperimentConfig(
            node_counts=(8,),
            densities=("sparse",),
            graph_seeds=(5,),
            deterministic_repeats=1,
            harmony_trials=1,
            harmony_iterations=5,
            hms=4,
            measure_memory=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_experiment(config, Path(temp_dir) / "results.csv")

            # 4 timing rows plus one memory row per algorithm.
            self.assertEqual(len(rows), 8)
            memory_rows = [row for row in rows if row["run_type"] == "memory"]
            self.assertEqual(len(memory_rows), 4)
            self.assertTrue(all(float(row["peak_memory_kb"]) > 0 for row in memory_rows))
            self.assertTrue(all(row["peak_memory_kb"] == "" for row in rows if row["run_type"] == "timing"))

    def test_environment_json_written_next_to_results(self):
        config = ExperimentConfig(
            node_counts=(8,),
            densities=("sparse",),
            graph_seeds=(5,),
            deterministic_repeats=1,
            harmony_trials=1,
            harmony_iterations=5,
            hms=4,
            measure_memory=False,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            run_experiment(config, Path(temp_dir) / "results.csv")
            self.assertTrue((Path(temp_dir) / "environment.json").exists())

    def test_basic_operation_counters_are_recorded(self):
        config = ExperimentConfig(
            node_counts=(12,),
            densities=("sparse",),
            graph_seeds=(5,),
            deterministic_repeats=1,
            harmony_trials=1,
            harmony_iterations=5,
            hms=4,
            measure_memory=False,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_experiment(config, Path(temp_dir) / "results.csv")

        by_algorithm = {row["algorithm"]: row for row in rows}
        for name in ("dijkstra", "astar", "bellman_ford"):
            self.assertGreater(int(by_algorithm[name]["edge_examinations"]), 0)
        self.assertGreater(int(by_algorithm["bellman_ford"]["relaxations"]), 0)
        self.assertGreater(int(by_algorithm["harmony_search"]["path_evaluations"]), 0)

    def test_parameter_sweep_can_run_at_small_scale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "sweep.csv"
            rows = run_parameter_sweep(output, node_count=12, trials=1, iterations=2)

            self.assertTrue(output.exists())
            self.assertEqual(len(rows), 27)

    def test_result_summary_mentions_fastest_and_benchmark(self):
        rows = [
            {"algorithm": "dijkstra", "graph_id": "g1", "runtime_ms": 2.0, "path_cost": 10, "success": True},
            {"algorithm": "harmony_search", "graph_id": "g1", "runtime_ms": 5.0, "path_cost": 12, "success": True},
        ]

        summary = format_result_summary(rows)

        self.assertIn("Fastest average runtime: dijkstra", summary)
        self.assertIn("Dijkstra is the exact benchmark", summary)


if __name__ == "__main__":
    unittest.main()
