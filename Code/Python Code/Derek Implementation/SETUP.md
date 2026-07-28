# Setup and Run Guide

How to get the Routing Algorithm Lab running and open the GUI, from nothing.

If you just want the short version, jump to [Quick start](#quick-start).

---

## 1. Requirements

| Requirement | Details |
| --- | --- |
| **Python** | 3.10 or newer. Developed and tested on **CPython 3.14.3**. |
| **Third-party packages** | **None.** Every import is Python standard library. |
| **Web browser** | Any modern browser (Chrome, Edge, Firefox, Safari). Needs `EventSource`, supported since ~2011. |
| **Operating system** | Windows, macOS, or Linux. Developed on Windows 11. |
| **Disk space** | ~1 MB for the code. Up to **~10 MB** more if you download all three SNAP datasets. |
| **Memory** | ~50 MB for normal use. Loading **roadNet-PA** briefly peaks at **~322 MB**, so have ~500 MB free if you use it. |
| **Internet** | Only needed the **first** time you run a real-data experiment. Everything else works offline. |

There is nothing to `pip install` to run this project. The optional dev
dependency (`pytest`) is only a convenience — the tests run under the built-in
`unittest` module.

### Verify your Python

```powershell
python --version
```

You need `3.10.0` or higher. If `python` is not found, see
[Troubleshooting](#8-troubleshooting).

---

## 2. Quick start

Three commands:

```powershell
git clone -b derek_branch https://github.com/DeezyDeeDEE/Network_Routing_Optimization.git
cd Network_Routing_Optimization
$env:PYTHONPATH = "src"; python -m routing_project.cli gui
```

> **The `-b derek_branch` matters.** The repository's default branch (`main`)
> holds a different folder layout and does **not** contain the Python package,
> so a plain `git clone` will not work. Everything described in this guide lives
> on `derek_branch`.

Your browser opens at <http://127.0.0.1:8000>. Pick **Quick check** and press
**Run experiment** — it finishes in well under a second.

On macOS or Linux the last line is:

```bash
PYTHONPATH=src python3 -m routing_project.cli gui
```

---

## 3. Get the code

**With Git:**

```powershell
git clone -b derek_branch https://github.com/DeezyDeeDEE/Network_Routing_Optimization.git
cd Network_Routing_Optimization
```

The `-b derek_branch` flag is required — the default `main` branch has a
different structure and does not contain the Python package. If you already
cloned without it:

```powershell
git checkout derek_branch
```

**Without Git:** on the GitHub page, switch the branch selector from `main` to
`derek_branch` **first**, then use "Code" → "Download ZIP". Extract it and `cd`
into the extracted folder.

Every command below is run **from the repository root** — the folder containing
`README.md`, `pyproject.toml`, `src/`, and `tests/`.

---

## 4. Make the package importable

The code lives in `src/routing_project/`, which Python does not look in by
default. Pick **one** of these two options.

### Option A — Set the path (fastest, no install)

Nothing is installed and nothing is modified on your system. You must set this
in **every new terminal**, because it only lasts for that session.

Windows PowerShell:
```powershell
$env:PYTHONPATH = "src"
```

Windows Command Prompt (`cmd.exe`):
```bat
set PYTHONPATH=src
```

macOS / Linux:
```bash
export PYTHONPATH=src
```

### Option B — Virtual environment and install (best for repeated use)

Set it up once; afterwards you only activate the environment. This isolates the
project from your system Python.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

After this, `PYTHONPATH` is not needed — `python -m routing_project.cli` works
directly. In new terminals, just re-run the activate line.

> If `Activate.ps1` is blocked by PowerShell, see
> [Troubleshooting](#8-troubleshooting).

### Confirm it worked

```powershell
python -m routing_project.cli list-datasets
```

You should see the three SNAP datasets. If you get
`No module named routing_project`, the path step did not take effect.

---

## 5. Open the GUI

```powershell
python -m routing_project.cli gui
```

The terminal prints:

```
Routing project GUI running at http://127.0.0.1:8000
Press Ctrl+C to stop.
```

and your default browser opens automatically. If it doesn't, open that URL
yourself.

**Leave the terminal open** — closing it stops the server. Press `Ctrl+C` to
stop when you're finished.

### Options

| Flag | Purpose |
| --- | --- |
| `--port 8080` | Use a specific port. |
| `--port 0` | Let the OS pick any free port (it is printed). Use this if 8000 is taken. |
| `--host 0.0.0.0` | Allow other machines on your network to connect. |
| `--no-browser` | Don't open a browser automatically. |

Example:

```powershell
python -m routing_project.cli gui --port 0
```

---

## 6. Using the GUI

The left panel configures the experiment; the right panel shows results live.

### Choosing an experiment

| Mode | What it does | Typical time |
| --- | --- | --- |
| **Quick check** | 8 small synthetic graphs (20 and 50 nodes). Confirms everything works. | **< 1 second** |
| **Real networks from Stanford SNAP** | Runs on ego-Facebook, Oregon-1, and roadNet-PA. | **~1.5 min** (plus a one-time ~10 MB download) |
| **Custom synthetic grid** | You choose node counts, densities, seeds, and Harmony Search settings. | Depends on your settings |
| **Full synthetic grid** | 27 graphs: 50/250/1000 nodes × sparse/moderate/dense × 3 seeds. 1,323 runs. | **~2 min 15 s** |
| **Harmony Search parameter sweep** | All 27 combinations of HMCR × PAR × HMS. | **~7 seconds** |

Start with **Quick check** to confirm the setup before running anything long.

### What the controls mean

- **Datasets** *(real mode)* — which SNAP networks to run.
- **BFS sample size** — how many nodes to keep from a large graph. Bellman-Ford
  is Θ(V·E), so the full 1.09-million-node road network is not runnable in pure
  Python. Sampling walks outward breadth-first from a starting node, which keeps
  the result connected. `0` means use the full graph — **do not do this with
  roadNet-PA.**
- **HS trials** — how many times to repeat Harmony Search. It is random, so more
  trials give a more reliable average.
- **HS iterations** — how long each Harmony Search run searches for.
- **Timing repeats** — how many times each exact algorithm is re-timed.
- **HMS** — Harmony Memory Size, how many candidate paths are kept.
- **Measure peak memory** — adds one extra instrumented run per algorithm. These
  are recorded separately because the instrumentation inflates runtime, and are
  never mixed into the timing averages.

### Reading the results

While a run is in progress you'll see a progress bar, a live log, four stat
tiles, four charts that redraw as results arrive, and a running averages table.

- **Mean runtime** and **Peak memory** use a **logarithmic** axis — the
  algorithms differ by several orders of magnitude, so a normal axis would make
  three of the four bars invisible.
- **Mean path cost** — Dijkstra is the exact optimum, so it is the benchmark.
  Bellman-Ford and A\* should match it exactly; Harmony Search usually won't.
- **Harmony Search gap above optimal** — the percentage by which Harmony Search
  missed the true shortest path. This is the most interesting chart in the
  project.

When the run finishes, the report-quality SVG charts appear at the bottom of the
page.

### Notes

- **Only one experiment runs at a time.** This is deliberate: the project
  measures wall-clock runtime, and two experiments sharing the CPU would corrupt
  each other's timings. Use **Cancel** to stop a run early.
- The first real-data run downloads from `snap.stanford.edu` and caches into
  `data/`. Later runs are offline and instant.

---

## 7. Command-line alternative

The GUI is optional — everything is available from the terminal:

```powershell
python -m routing_project.cli run-small          # quick synthetic check
python -m routing_project.cli run-checkpoint     # full synthetic grid
python -m routing_project.cli run-real           # real SNAP networks
python -m routing_project.cli run-sweep          # Harmony Search parameter sweep
python -m routing_project.cli list-datasets      # show available SNAP datasets
python -m routing_project.cli make-charts --input results/raw/real_experiment.csv --output-dir results/charts/real
```

Add `--help` to any command to see its options.

### Verify the install with the test suite

```powershell
python -m unittest discover
```

Expect `Ran 36 tests ... OK` in about a second. The tests set up their own
import path, so they work even if you skipped step 4.

---

## 8. Troubleshooting

**`python` is not recognised, or it opens the Microsoft Store**
Windows ships a placeholder. Use the launcher instead — substitute `py` for
`python` in every command:
```powershell
py -m routing_project.cli gui
```
If that also fails, install Python from <https://www.python.org/downloads/> and
tick **"Add python.exe to PATH"** during installation.

**`ModuleNotFoundError: No module named 'routing_project'`**
The path step didn't apply. Check that you are in the repository root (`ls`
should show `src` and `pyproject.toml`), then redo step 4. Remember
`$env:PYTHONPATH` only lasts for the current terminal window.

**`invalid choice: 'gui'`, or there is no `src/` folder at all**
You are on the wrong branch. `ls` will show `Code`, `Reports`, and
`Tables & Graphs` instead of `src` and `tests`. Fix it with:
```powershell
git checkout derek_branch
```

**`OSError: [Errno 98] Address already in use` / `[WinError 10048]`**
Port 8000 is taken. Let the OS choose one:
```powershell
python -m routing_project.cli gui --port 0
```

**PowerShell: "running scripts is disabled on this system"**
This blocks `Activate.ps1`. Allow it for the current window only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then run the activate command again. Or just use Option A and skip the venv.

**The browser doesn't open**
Open the printed URL manually — usually <http://127.0.0.1:8000>. Use
`--no-browser` to suppress the automatic launch.

**Windows Firewall prompt on startup**
Choose **Cancel** / deny. The server binds to `127.0.0.1` (your machine only) and
does not need network access. Only allow it if you deliberately used
`--host 0.0.0.0`.

**Real-data download fails (`URLError`, timeout, or certificate error)**
You need internet access for the first real-data run. On a restricted network,
set a proxy first:
```powershell
$env:HTTPS_PROXY = "http://your-proxy:port"
```
You can also download the three files manually from
<https://snap.stanford.edu/data/> and place them in a `data/` folder in the
repository root, keeping their original names:
`facebook_combined.txt.gz`, `oregon1_010331.txt.gz`, `roadNet-PA.txt.gz`.

**roadNet-PA is slow or uses a lot of memory**
Expected. It has 1,088,092 nodes, so parsing takes ~12 seconds and briefly peaks
around 322 MB before sampling drops it to ~5 MB. Deselect it, or lower the
sample size, if your machine is constrained.

**A run seems stuck**
Large graphs can take a while between progress updates — loading roadNet-PA
produces no output for ~12 seconds. Check the log panel for the last message. If
you want to stop, press **Cancel**, or `Ctrl+C` in the terminal.

**"An experiment is already running"**
Only one run is permitted at a time so that timings stay accurate. Press
**Cancel**, or wait for the current run to finish.

---

## 9. Where the output goes

| Path | Contents |
| --- | --- |
| `results/raw/*.csv` | Every individual run, one row each. |
| `results/raw/environment.json` | The machine the results were produced on. |
| `results/charts/` | Report charts from the synthetic experiments. |
| `results/charts/real/` | Report charts from the SNAP experiments. |
| `results/charts/gui/` | Charts from GUI runs (scratch; not committed to Git). |
| `data/` | Cached SNAP downloads (not committed to Git). |

`results_summary.md` in each chart folder contains the machine description, the
per-algorithm averages table, the Harmony Search gap broken down by input, and
the interpretation notes for the report.
