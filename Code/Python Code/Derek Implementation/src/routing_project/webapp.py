"""Local web GUI for running the routing experiments interactively.

Built on the Python standard library only (``http.server`` plus server-sent
events), so the GUI adds no dependencies to the project and runs anywhere the
rest of the code runs.

Start it with::

    python -m routing_project.cli gui

Only one experiment is allowed to run at a time. That is deliberate rather than
a limitation: these experiments measure wall-clock runtime, and two experiments
sharing the CPU would contaminate each other's timings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import threading
import traceback
from typing import Any
from urllib.parse import parse_qs, urlparse

from routing_project.charts import make_charts
from routing_project.datasets import DATASETS
from routing_project.environment import describe_environment
from routing_project.experiments import (
    CHECKPOINT_CONFIG,
    SMALL_CONFIG,
    ExperimentConfig,
    RealDataConfig,
    format_result_summary,
    run_experiment,
    run_parameter_sweep,
    run_real_experiment,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
RAW_DIR = PROJECT_ROOT / "results" / "raw"
GUI_CHART_DIR = PROJECT_ROOT / "results" / "charts" / "gui"
DATA_DIR = PROJECT_ROOT / "data"

# Keep the browser's EventSource connection alive through long gaps between
# events (loading roadNet-PA can take several seconds with no row output).
HEARTBEAT_SECONDS = 10.0


class RunCancelled(Exception):
    """Raised inside the progress callback to unwind a running experiment."""


@dataclass
class Run:
    """State for a single experiment run, shared between worker and readers."""

    run_id: str
    mode: str
    status: str = "running"
    events: list[dict[str, Any]] = field(default_factory=list)
    cancel_requested: bool = False
    condition: threading.Condition = field(default_factory=threading.Condition)

    def append(self, event: dict[str, Any]) -> None:
        with self.condition:
            self.events.append(event)
            self.condition.notify_all()

    def events_from(self, index: int) -> list[dict[str, Any]]:
        with self.condition:
            return self.events[index:]

    def finish(self, status: str) -> None:
        with self.condition:
            self.status = status
            self.condition.notify_all()


class RunManager:
    """Owns the single active run and the worker thread behind it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, Run] = {}
        self._active: Run | None = None
        self._counter = 0

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def active(self) -> Run | None:
        with self._lock:
            return self._active

    def cancel(self, run_id: str) -> bool:
        run = self.get(run_id)
        if run is None or run.status != "running":
            return False
        with run.condition:
            run.cancel_requested = True
            run.condition.notify_all()
        return True

    def start(self, mode: str, options: dict[str, Any]) -> tuple[Run | None, str]:
        with self._lock:
            if self._active is not None and self._active.status == "running":
                return None, "An experiment is already running. Cancel it or wait for it to finish."
            self._counter += 1
            run = Run(run_id=f"run{self._counter}", mode=mode)
            self._runs[run.run_id] = run
            self._active = run

        thread = threading.Thread(target=self._execute, args=(run, mode, options), daemon=True)
        thread.start()
        return run, ""

    def _execute(self, run: Run, mode: str, options: dict[str, Any]) -> None:
        def on_event(event: dict[str, Any]) -> None:
            if run.cancel_requested:
                raise RunCancelled
            run.append(event)

        try:
            rows, output_csv = _dispatch(mode, options, on_event)
            run.append({"type": "log", "message": f"Wrote {len(rows)} rows to {output_csv}"})

            charts: list[str] = []
            if rows:
                run.append({"type": "log", "message": "Generating report charts..."})
                chart_dir = GUI_CHART_DIR / run.run_id
                for path in make_charts(output_csv, chart_dir):
                    if path.suffix == ".svg":
                        charts.append(f"{run.run_id}/{path.name}")

            run.append(
                {
                    "type": "done",
                    "summary": format_result_summary(rows),
                    "charts": charts,
                    "csv": str(output_csv),
                    "row_count": len(rows),
                }
            )
            run.finish("completed")
        except RunCancelled:
            run.append({"type": "cancelled", "message": "Run cancelled."})
            run.finish("cancelled")
        except Exception as error:  # surfaced to the browser rather than the console
            run.append({"type": "error", "message": f"{type(error).__name__}: {error}"})
            traceback.print_exc()
            run.finish("failed")


def _dispatch(mode: str, options: dict[str, Any], on_event) -> tuple[list[dict[str, Any]], Path]:
    """Map a GUI mode plus its options onto the matching experiment runner."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if mode == "small":
        output = RAW_DIR / "gui_small.csv"
        return run_experiment(SMALL_CONFIG, output, on_event=on_event), output

    if mode == "checkpoint":
        output = RAW_DIR / "gui_checkpoint.csv"
        return run_experiment(CHECKPOINT_CONFIG, output, on_event=on_event), output

    if mode == "custom":
        config = ExperimentConfig(
            node_counts=tuple(_int_list(options.get("node_counts"), (50, 250))),
            densities=tuple(options.get("densities") or ("sparse", "moderate")),
            graph_seeds=tuple(_int_list(options.get("graph_seeds"), (11, 23))),
            deterministic_repeats=max(1, int(options.get("repeats", 3))),
            harmony_trials=max(1, int(options.get("trials", 5))),
            harmony_iterations=max(1, int(options.get("iterations", 150))),
            hmcr=float(options.get("hmcr", 0.8)),
            par=float(options.get("par", 0.3)),
            hms=max(1, int(options.get("hms", 30))),
            measure_memory=bool(options.get("measure_memory", True)),
        )
        output = RAW_DIR / "gui_custom.csv"
        return run_experiment(config, output, on_event=on_event), output

    if mode == "real":
        keys = tuple(options.get("datasets") or ("facebook", "oregon1", "roadnet-pa"))
        unknown = [key for key in keys if key not in DATASETS]
        if unknown:
            raise ValueError(f"Unknown dataset(s): {', '.join(unknown)}")
        sample = int(options.get("sample", 8000))
        config = RealDataConfig(
            dataset_keys=keys,
            sample_size=sample if sample > 0 else None,
            deterministic_repeats=max(1, int(options.get("repeats", 3))),
            harmony_trials=max(1, int(options.get("trials", 10))),
            harmony_iterations=max(1, int(options.get("iterations", 250))),
            measure_memory=bool(options.get("measure_memory", True)),
        )
        output = RAW_DIR / "gui_real.csv"
        return run_real_experiment(config, output, DATA_DIR, on_event=on_event), output

    if mode == "sweep":
        output = RAW_DIR / "gui_sweep.csv"
        rows = run_parameter_sweep(
            output,
            node_count=max(2, int(options.get("nodes", 500))),
            trials=max(1, int(options.get("trials", 3))),
            iterations=max(1, int(options.get("iterations", 100))),
            on_event=on_event,
        )
        return rows, output

    raise ValueError(f"Unknown mode {mode!r}")


def _int_list(value: Any, fallback: tuple[int, ...]) -> tuple[int, ...]:
    if not value:
        return fallback
    if isinstance(value, str):
        parts = [piece.strip() for piece in value.replace(",", " ").split()]
    else:
        parts = list(value)
    numbers = tuple(int(part) for part in parts if str(part).strip())
    return numbers or fallback


class Handler(BaseHTTPRequestHandler):
    server_version = "RoutingProjectGUI/1.0"
    manager: RunManager

    def log_message(self, format: str, *args) -> None:  # quieter console
        return

    # ---------------------------------------------------------------- helpers

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    # ----------------------------------------------------------------- routes

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route in ("/", "/index.html"):
            self._send_file(STATIC_DIR / "index.html")
        elif route == "/api/meta":
            self._send_json(
                {
                    "environment": describe_environment(),
                    "datasets": [
                        {
                            "key": dataset.key,
                            "name": dataset.name,
                            "nodes": dataset.nodes,
                            "edges": dataset.edges,
                            "category": dataset.category,
                            "description": dataset.description,
                            "url": dataset.url,
                        }
                        for dataset in DATASETS.values()
                    ],
                }
            )
        elif route == "/api/events":
            self._stream_events(parse_qs(parsed.query))
        elif route.startswith("/charts/"):
            relative = route[len("/charts/") :]
            candidate = (GUI_CHART_DIR / relative).resolve()
            # Path containment check: never serve outside the chart directory.
            if not str(candidate).startswith(str(GUI_CHART_DIR.resolve())):
                self._send_json({"error": "Forbidden"}, status=403)
                return
            self._send_file(candidate)
        else:
            self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        payload = self._read_json()

        if route == "/api/run":
            mode = str(payload.get("mode", "small"))
            run, error = self.manager.start(mode, payload.get("options") or {})
            if run is None:
                self._send_json({"error": error}, status=409)
                return
            self._send_json({"run_id": run.run_id, "mode": run.mode})
        elif route == "/api/cancel":
            ok = self.manager.cancel(str(payload.get("run_id", "")))
            self._send_json({"cancelled": ok})
        else:
            self._send_json({"error": "Not found"}, status=404)

    # ------------------------------------------------------------------- SSE

    def _stream_events(self, query: dict[str, list[str]]) -> None:
        run_id = (query.get("run") or [""])[0]
        run = self.manager.get(run_id)
        if run is None:
            self._send_json({"error": "Unknown run"}, status=404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        cursor = 0
        try:
            while True:
                pending = run.events_from(cursor)
                if pending:
                    cursor += len(pending)
                    for event in pending:
                        self._write_event(event)
                    continue

                with run.condition:
                    finished = run.status != "running" and cursor >= len(run.events)
                    if not finished:
                        run.condition.wait(timeout=HEARTBEAT_SECONDS)
                        continue
                # Terminal marker so the browser can close the stream cleanly.
                self._write_event({"type": "stream_end", "status": run.status})
                return
        except (BrokenPipeError, ConnectionResetError):
            return

    def _write_event(self, event: dict[str, Any]) -> None:
        self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
        self.wfile.flush()


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"manager": RunManager()})
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    server = create_server(host, port)
    url = f"http://{host}:{server.server_address[1]}"
    print(f"Routing project GUI running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        import webbrowser

        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()
