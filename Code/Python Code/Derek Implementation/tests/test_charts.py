import csv
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from routing_project.charts import make_charts


class ChartTests(unittest.TestCase):
    def test_make_charts_writes_summary_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_path = temp_path / "results.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["algorithm", "graph_id", "path_cost", "runtime_ms", "success"],
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerow(
                    {"algorithm": "dijkstra", "graph_id": "g1", "path_cost": 10, "runtime_ms": 1, "success": "True"}
                )
                writer.writerow(
                    {
                        "algorithm": "harmony_search",
                        "graph_id": "g1",
                        "path_cost": 12,
                        "runtime_ms": 3,
                        "success": "True",
                    }
                )

            outputs = make_charts(csv_path, temp_path / "charts")
            summary_path = temp_path / "charts" / "results_summary.md"

            self.assertIn(summary_path, outputs)
            text = summary_path.read_text(encoding="utf-8")
            self.assertIn("Experiment Results Summary", text)
            # The deliverables require the report to state the machine used.
            self.assertIn("Machine used to generate these results", text)

    def test_memory_runs_are_excluded_from_runtime_averages(self):
        """A tracemalloc-instrumented run must not drag the timing average up."""

        fields = [
            "algorithm",
            "graph_id",
            "nodes",
            "path_cost",
            "runtime_ms",
            "success",
            "run_type",
            "peak_memory_kb",
            "edge_examinations",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_path = temp_path / "results.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerow(
                    {
                        "algorithm": "dijkstra",
                        "graph_id": "g1",
                        "nodes": 50,
                        "path_cost": 10,
                        "runtime_ms": 1.0,
                        "success": "True",
                        "run_type": "timing",
                        "peak_memory_kb": "",
                        "edge_examinations": 40,
                    }
                )
                writer.writerow(
                    {
                        "algorithm": "dijkstra",
                        "graph_id": "g1",
                        "nodes": 50,
                        "path_cost": 10,
                        "runtime_ms": 500.0,
                        "success": "True",
                        "run_type": "memory",
                        "peak_memory_kb": 64.0,
                        "edge_examinations": 40,
                    }
                )

            make_charts(csv_path, temp_path / "charts")
            text = (temp_path / "charts" / "results_summary.md").read_text(encoding="utf-8")

        # 1.000 ms is the timing-only mean; 250.500 would be the polluted mean.
        self.assertIn("| 1.000 |", text)
        self.assertNotIn("250.500", text)
        self.assertIn("64.0", text)

    def test_generated_svgs_are_well_formed_xml(self):
        """A nested double quote in an attribute silently corrupts the markup."""

        fields = ["algorithm", "graph_id", "nodes", "path_cost", "runtime_ms", "success", "run_type"]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_path = temp_path / "results.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for algorithm, runtime, cost in [
                    ("dijkstra", 1.0, 10),
                    ("bellman_ford", 40.0, 10),
                    ("astar", 1.1, 10),
                    ("harmony_search", 900.0, 14),
                ]:
                    writer.writerow(
                        {
                            "algorithm": algorithm,
                            "graph_id": "g1",
                            "nodes": 500,
                            "path_cost": cost,
                            "runtime_ms": runtime,
                            "success": "True",
                            "run_type": "timing",
                        }
                    )

            outputs = make_charts(csv_path, temp_path / "charts")
            svgs = [path for path in outputs if path.suffix == ".svg"]
            self.assertTrue(svgs)
            for svg in svgs:
                root = ElementTree.parse(svg).getroot()
                self.assertTrue(root.tag.endswith("svg"), f"{svg.name} is not an <svg> root")


if __name__ == "__main__":
    unittest.main()
