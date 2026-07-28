"""Tests for the local GUI server.

The server is started on an ephemeral port and driven over real HTTP, so the
routing, JSON contracts, and the server-sent-events stream are all exercised the
same way a browser exercises them.
"""

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from routing_project import webapp


def get_json(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(base: str, path: str, payload: dict):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def read_events(base: str, run_id: str, timeout: float = 120.0):
    """Consume the SSE stream until the terminal marker arrives."""

    events = []
    with urllib.request.urlopen(f"{base}/api/events?run={run_id}", timeout=timeout) as stream:
        for raw in stream:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            events.append(event)
            if event["type"] == "stream_end":
                break
    return events


class WebAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Redirect every output path into a temp directory. Without this the
        # server writes CSVs, environment.json, and charts straight into the
        # working tree, which pollutes the repository on every test run.
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="routing-webapp-test-"))
        cls._saved_paths = (webapp.RAW_DIR, webapp.GUI_CHART_DIR, webapp.DATA_DIR)
        webapp.RAW_DIR = cls.temp_dir / "raw"
        webapp.GUI_CHART_DIR = cls.temp_dir / "charts"
        webapp.DATA_DIR = cls.temp_dir / "data"

        cls.server = webapp.create_server("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        webapp.RAW_DIR, webapp.GUI_CHART_DIR, webapp.DATA_DIR = cls._saved_paths
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_runs_do_not_write_into_the_repository(self):
        """Output paths must be redirectable so tests never touch the repo."""

        self.assertEqual(webapp.RAW_DIR.parent, self.temp_dir)
        self.assertEqual(webapp.GUI_CHART_DIR.parent, self.temp_dir)

        status, data = post_json(
            self.base,
            "/api/run",
            {
                "mode": "custom",
                "options": {
                    "node_counts": "8",
                    "densities": ["sparse"],
                    "graph_seeds": "3",
                    "repeats": 1,
                    "trials": 1,
                    "iterations": 2,
                    "hms": 3,
                    "measure_memory": False,
                },
            },
        )
        self.assertEqual(status, 200)
        read_events(self.base, data["run_id"])

        self.assertTrue((webapp.RAW_DIR / "gui_custom.csv").exists())
        repo_results = Path(webapp.__file__).resolve().parents[2] / "results" / "raw" / "gui_custom.csv"
        self.assertFalse(repo_results.exists(), "run output leaked into the repository")

    def test_index_page_is_served(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as response:
            body = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("Routing Algorithm Lab", body)

    def test_meta_exposes_environment_and_datasets(self):
        meta = get_json(self.base, "/api/meta")
        self.assertIn("python_version", meta["environment"])
        keys = {dataset["key"] for dataset in meta["datasets"]}
        self.assertEqual(keys, {"facebook", "oregon1", "roadnet-pa"})

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            get_json(self.base, "/api/nope")
        self.assertEqual(context.exception.code, 404)

    def test_chart_route_rejects_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            get_json(self.base, "/charts/../../../../etc/passwd")
        self.assertIn(context.exception.code, (403, 404))

    def test_unknown_mode_is_reported_as_an_error_event(self):
        status, data = post_json(self.base, "/api/run", {"mode": "does-not-exist"})
        self.assertEqual(status, 200)
        events = read_events(self.base, data["run_id"])
        self.assertEqual(events[-1]["status"], "failed")
        self.assertTrue(any(event["type"] == "error" for event in events))

    def test_custom_run_streams_rows_and_completes(self):
        status, data = post_json(
            self.base,
            "/api/run",
            {
                "mode": "custom",
                "options": {
                    "node_counts": "10",
                    "densities": ["sparse"],
                    "graph_seeds": "1",
                    "repeats": 1,
                    "trials": 1,
                    "iterations": 3,
                    "hms": 4,
                    "measure_memory": False,
                },
            },
        )
        self.assertEqual(status, 200)
        events = read_events(self.base, data["run_id"])
        kinds = [event["type"] for event in events]

        self.assertEqual(kinds[0], "start")
        self.assertIn("graph", kinds)
        self.assertEqual(events[-1], {"type": "stream_end", "status": "completed"})

        rows = [event["row"] for event in events if event["type"] == "row"]
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["algorithm"] for row in rows}, {"dijkstra", "bellman_ford", "astar", "harmony_search"})

        done = next(event for event in events if event["type"] == "done")
        self.assertEqual(done["row_count"], 4)
        self.assertTrue(done["charts"], "expected report charts to be generated")

        # The predicted row total must match what actually streamed, or the
        # progress bar in the GUI would be wrong.
        start = events[0]
        self.assertEqual(start["row_total"], len(rows))

    def test_second_run_is_refused_while_one_is_active(self):
        long_options = {
            "mode": "custom",
            "options": {
                "node_counts": "60",
                "densities": ["moderate"],
                "graph_seeds": "1 2",
                "repeats": 2,
                "trials": 30,
                "iterations": 400,
                "measure_memory": False,
            },
        }
        status, first = post_json(self.base, "/api/run", long_options)
        self.assertEqual(status, 200)
        try:
            conflict_status, conflict = post_json(self.base, "/api/run", {"mode": "small"})
            self.assertEqual(conflict_status, 409)
            self.assertIn("already running", conflict["error"])
        finally:
            post_json(self.base, "/api/cancel", {"run_id": first["run_id"]})

        events = read_events(self.base, first["run_id"])
        self.assertEqual(events[-1]["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
