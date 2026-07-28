"""Dependency-free SVG chart generation for the project report.

Design notes
------------
* Colour is assigned per *algorithm*, so an algorithm keeps the same hue in every
  chart in the report. Colour never follows a bar's rank.
* The palette is the validated four-slot categorical set (blue / orange / aqua /
  yellow). Two of those slots sit below 3:1 contrast on a light surface, so every
  mark carries a visible direct label and every chart has a table twin in
  ``results_summary.md``.
* Runtime, basic-operation counts, and peak memory span several orders of
  magnitude across these algorithms. Drawing those as linear bars would make
  three of the four bars invisible, so they are drawn as dot plots on a
  logarithmic axis, where position (not length from zero) carries the value.
  Path cost and the Harmony Search gap stay as bars because their values are
  directly comparable.
"""

from __future__ import annotations

import csv
from collections import defaultdict
import math
import os
from pathlib import Path
from statistics import mean

from routing_project.environment import describe_environment, format_environment
from routing_project.experiments import harmony_gap, is_timing_row


# Validated categorical slots (light surface #fcfcfb).
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_1 = "#2a78d6"

ALGORITHM_COLORS = {
    "dijkstra": "#2a78d6",
    "bellman_ford": "#eb6834",
    "astar": "#1baf7a",
    "harmony_search": "#eda100",
}

ALGORITHM_LABELS = {
    "dijkstra": "Dijkstra",
    "bellman_ford": "Bellman-Ford",
    "astar": "A*",
    "harmony_search": "Harmony Search",
}

# Single-quoted inside the family list: these values are interpolated into
# double-quoted SVG attributes, and a nested double quote would end the
# attribute early and corrupt the markup.
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def make_charts(input_csv: Path, output_dir: Path) -> list[Path]:
    rows = _read_rows(input_csv)
    output_dir.mkdir(parents=True, exist_ok=True)
    timing = [row for row in rows if is_timing_row(row)]
    memory = [row for row in rows if not is_timing_row(row)]

    outputs: list[Path] = []

    runtime = _mean_by_algorithm(timing, "runtime_ms")
    if runtime:
        outputs.append(
            _dot_plot_log(
                runtime,
                "Mean runtime by algorithm",
                "Runtime (ms, log scale)",
                output_dir / "runtime_by_algorithm.svg",
                unit="ms",
            )
        )

    cost = _mean_by_algorithm(timing, "path_cost")
    if cost:
        outputs.append(
            _bar_chart(
                cost,
                "Mean path cost by algorithm",
                "Path cost",
                output_dir / "path_cost_by_algorithm.svg",
            )
        )

    operations = _mean_operations(timing)
    if operations:
        outputs.append(
            _dot_plot_log(
                operations,
                "Basic operations by algorithm",
                "Operations per run (log scale)",
                output_dir / "basic_operations_by_algorithm.svg",
                unit="",
                subtitle=(
                    "Units differ: edge examinations for Dijkstra / Bellman-Ford / A*, "
                    "candidate path evaluations for Harmony Search."
                ),
            )
        )

    peak = _mean_by_algorithm(memory, "peak_memory_kb")
    if peak:
        outputs.append(
            _dot_plot_log(
                peak,
                "Peak memory by algorithm",
                "Peak allocation (KiB, log scale)",
                output_dir / "peak_memory_by_algorithm.svg",
                unit="KiB",
            )
        )

    gap_by_size = _hs_gap_by_size(timing)
    if gap_by_size:
        outputs.append(
            _bar_chart(
                gap_by_size,
                "Harmony Search gap above optimal, by graph size",
                "Mean gap above Dijkstra (%)",
                output_dir / "hs_gap_by_size.svg",
                color=SERIES_1,
                value_format="{:.1f}%",
            )
        )

    outputs.append(_summary_report(rows, input_csv, output_dir, outputs))
    return outputs


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _mean_by_algorithm(rows: list[dict[str, str]], field: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.get(field):
            grouped[row["algorithm"]].append(float(row[field]))
    return {algorithm: mean(values) for algorithm, values in grouped.items() if values}


def _mean_operations(rows: list[dict[str, str]]) -> dict[str, float]:
    """Mean count of each algorithm's characteristic basic operation.

    The heap-based searches and Bellman-Ford count edge examinations; Harmony
    Search counts candidate path evaluations. These are different units of work,
    so the chart shows scale of effort rather than a like-for-like race.
    """

    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        raw = row.get("edge_examinations") or row.get("path_evaluations")
        if raw:
            grouped[row["algorithm"]].append(float(raw))
    return {algorithm: mean(values) for algorithm, values in grouped.items() if values}


def _hs_gap_by_size(rows: list[dict[str, str]]) -> dict[str, float]:
    """Mean Harmony Search relative gap above Dijkstra, grouped by input size.

    Grouping is keyed on (graph source, node count), not node count alone. Two
    different SNAP networks sampled to the same node count are different inputs,
    and pooling them would average away the structural difference that is the
    whole point of running on real data.
    """

    grouped: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if not row.get("nodes"):
            continue
        source = row.get("graph_source") or "synthetic"
        grouped[(source, int(row["nodes"]))].append(row)

    result: dict[str, float] = {}
    for source, size in sorted(grouped, key=lambda key: (key[0], key[1])):
        gap = harmony_gap(grouped[(source, size)])
        if gap is None:
            continue
        if source.startswith("snap:"):
            label = f"{source.removeprefix('snap:')}\n{size:,}"
        else:
            label = f"{size:,}"
        result[label] = gap["relative"] * 100
    return result


def _hs_error_by_graph(rows: list[dict[str, str]]) -> dict[str, float]:
    """Retained for the summary text: mean absolute cost gap versus Dijkstra."""

    gap = harmony_gap([row for row in rows if is_timing_row(row)])
    return {"HS mean error": gap["absolute"]} if gap else {}


def _label_for(key: str) -> str:
    return ALGORITHM_LABELS.get(key, key.replace("_", " "))


def _summary_report(rows: list[dict[str, str]], input_csv: Path, output_dir: Path, chart_paths: list[Path]) -> Path:
    timing = [row for row in rows if is_timing_row(row)]
    memory = [row for row in rows if not is_timing_row(row)]
    summary = _summary_table(rows)
    gap = harmony_gap(timing)
    graph_count = len({row["graph_id"] for row in rows})
    output_path = output_dir / "results_summary.md"
    source_label = os.path.relpath(input_csv, start=output_dir).replace("\\", "/")

    runtime = _mean_by_algorithm(timing, "runtime_ms")
    fastest = min(runtime, key=runtime.get) if runtime else ""
    cost = _mean_by_algorithm(timing, "path_cost")
    lowest_cost = min(cost, key=cost.get) if cost else ""

    lines = [
        "# Experiment Results Summary",
        "",
        f"Source CSV: `{source_label}`",
        "",
        "## Machine used to generate these results",
        "",
        format_environment(describe_environment()),
        "",
        "## Visuals",
        "",
    ]
    for chart_path in chart_paths:
        if chart_path.suffix != ".svg":
            continue
        label = chart_path.stem.replace("_", " ").capitalize()
        lines.append(f"![{label}]({chart_path.name})")
        lines.append("")

    lines.extend(
        [
            "## Algorithm averages",
            "",
            "Runtime, path cost, and operation counts come from clean timing runs. "
            "Peak memory comes from separate runs instrumented with `tracemalloc`, "
            "which inflates runtime and is therefore never mixed into the timing columns.",
            "",
            "| Algorithm | Mean runtime (ms) | Mean path cost | Basic operations | Peak memory (KiB) | Success rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for algorithm, values in summary.items():
        peak = f"{values['peak_memory_kb']:,.1f}" if values["peak_memory_kb"] else "-"
        operations = f"{values['operations']:,.0f}" if values["operations"] else "-"
        lines.append(
            f"| {_label_for(algorithm)} | {values['runtime_ms']:.3f} | {values['path_cost']:.3f} "
            f"| {operations} | {peak} | {values['success_rate']:.1%} |"
        )

    size_gap = _hs_gap_by_size(timing)
    if size_gap:
        lines.extend(
            [
                "",
                "## Harmony Search solution quality by input",
                "",
                "| Input (nodes) | Mean gap above optimal |",
                "| --- | ---: |",
            ]
        )
        for size, value in size_gap.items():
            # Chart labels wrap on newlines; a Markdown table cell must not.
            lines.append(f"| {size.replace(chr(10), ' - ')} | {value:.2f}% |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- The data includes {len(timing)} timing runs and {len(memory)} memory runs "
            f"across {graph_count} graph instance(s).",
        ]
    )
    if fastest:
        lines.append(f"- `{fastest}` had the fastest average runtime in this run.")
    if lowest_cost:
        lines.append(f"- `{lowest_cost}` had the lowest average path cost.")
    if gap is not None:
        lines.append(
            f"- Harmony Search averaged {gap['absolute']:.3f} cost units ({gap['relative']:.1%}) "
            f"above Dijkstra, and matched the optimal cost on {gap['optimal_rate']:.1%} of runs."
        )
    lines.extend(
        [
            "- Dijkstra is the exact benchmark, so it anchors the path-quality comparison.",
            "- Bellman-Ford is expected to be slower because it relaxes every edge on every pass.",
            "- A* uses a zero heuristic here, so it is algorithmically equivalent to Dijkstra; "
            "any runtime difference between the two is measurement noise, not a real speedup.",
            "- Harmony Search is approximate; the question is whether its path cost stays close "
            "enough to Dijkstra to justify the extra runtime, and whether that holds as graphs grow.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _summary_table(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    timing = [row for row in rows if is_timing_row(row)]
    memory = [row for row in rows if not is_timing_row(row)]
    runtime = _mean_by_algorithm(timing, "runtime_ms")
    cost = _mean_by_algorithm(timing, "path_cost")
    peak = _mean_by_algorithm(memory, "peak_memory_kb")
    operations = _mean_operations(timing)

    success: dict[str, list[bool]] = defaultdict(list)
    for row in timing:
        success[row["algorithm"]].append(row.get("success") == "True")

    return {
        algorithm: {
            "runtime_ms": runtime.get(algorithm, 0.0),
            "path_cost": cost.get(algorithm, 0.0),
            "peak_memory_kb": peak.get(algorithm, 0.0),
            "operations": operations.get(algorithm, 0.0),
            "success_rate": (sum(success[algorithm]) / len(success[algorithm])) if success.get(algorithm) else 0.0,
        }
        for algorithm in runtime
    }


def _svg_header(width: int, height: int, title: str, subtitle: str = "") -> list[str]:
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{_escape(title)}">',
        f'<rect width="100%" height="100%" fill="{SURFACE}"/>',
        f'<text x="32" y="34" font-family="{FONT}" font-size="17" font-weight="600" '
        f'fill="{INK_PRIMARY}">{_escape(title)}</text>',
    ]
    if subtitle:
        pieces.append(
            f'<text x="32" y="54" font-family="{FONT}" font-size="12" '
            f'fill="{INK_MUTED}">{_escape(subtitle)}</text>'
        )
    return pieces


def _axis_label(text: str, x: float, y: float, anchor: str = "middle") -> str:
    """Render a possibly multi-line category label as stacked tspans."""

    lines = text.split("\n")
    spans = "".join(
        f'<tspan x="{x:.1f}" dy="{0 if index == 0 else 14}">{_escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{FONT}" '
        f'font-size="12" fill="{INK_SECONDARY}">{spans}</text>'
    )


def _bar_chart(
    values: dict[str, float],
    title: str,
    y_label: str,
    output_path: Path,
    color: str | None = None,
    value_format: str = "{:,.2f}",
    subtitle: str = "",
) -> Path:
    width, height = 760, 430
    left, right, top, bottom = 96, 40, 86 if subtitle else 70, 86
    chart_width = width - left - right
    chart_height = height - top - bottom
    max_value = max(values.values(), default=1.0) or 1.0

    count = max(1, len(values))
    slot = chart_width / count
    bar_width = min(96.0, slot * 0.55)

    pieces = _svg_header(width, height, title, subtitle)
    pieces.append(
        f'<text x="32" y="{top - 18}" font-family="{FONT}" font-size="12" '
        f'fill="{INK_SECONDARY}">{_escape(y_label)}</text>'
    )

    # Hairline gridlines with tick labels.
    for step in range(5):
        fraction = step / 4
        y = height - bottom - fraction * chart_height
        pieces.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            f'stroke="{GRIDLINE}" stroke-width="1"/>'
        )
        pieces.append(
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="{FONT}" '
            f'font-size="11" fill="{INK_MUTED}" style="font-variant-numeric:tabular-nums">'
            f'{_format_tick(max_value * fraction)}</text>'
        )

    for index, (label, value) in enumerate(values.items()):
        bar_height = (value / max_value) * chart_height if max_value else 0.0
        x = left + slot * index + (slot - bar_width) / 2
        y = height - bottom - bar_height
        fill = color or ALGORITHM_COLORS.get(label, SERIES_1)
        # 4px rounded data-end anchored to the baseline.
        pieces.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{max(bar_height, 1.0):.1f}" '
            f'rx="4" fill="{fill}"/>'
        )
        pieces.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="12" font-weight="600" fill="{INK_PRIMARY}" '
            f'style="font-variant-numeric:tabular-nums">{_escape(value_format.format(value))}</text>'
        )
        pieces.append(_axis_label(_label_for(label), x + bar_width / 2, height - bottom + 24))

    pieces.append(
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" '
        f'stroke="{BASELINE}" stroke-width="1"/>'
    )
    pieces.append("</svg>")
    output_path.write_text("\n".join(pieces), encoding="utf-8")
    return output_path


def _dot_plot_log(
    values: dict[str, float],
    title: str,
    x_label: str,
    output_path: Path,
    unit: str = "",
    subtitle: str = "",
) -> Path:
    """Horizontal dot plot on a log axis, for values spanning several decades."""

    positive = {label: value for label, value in values.items() if value > 0}
    if not positive:
        return _bar_chart(values, title, x_label, output_path)

    width = 760
    row_height = 46
    left, right = 168, 96
    top = 88 if subtitle else 72
    bottom = 62
    height = top + row_height * len(positive) + bottom
    chart_width = width - left - right

    low_exponent = math.floor(math.log10(min(positive.values())))
    high_exponent = math.ceil(math.log10(max(positive.values())))
    if high_exponent <= low_exponent:
        high_exponent = low_exponent + 1
    span = high_exponent - low_exponent

    def x_of(value: float) -> float:
        return left + (math.log10(value) - low_exponent) / span * chart_width

    pieces = _svg_header(width, height, title, subtitle)
    pieces.append(
        f'<text x="32" y="{top - 16}" font-family="{FONT}" font-size="12" '
        f'fill="{INK_SECONDARY}">{_escape(x_label)}</text>'
    )

    # Decade gridlines.
    for exponent in range(low_exponent, high_exponent + 1):
        x = x_of(10**exponent)
        pieces.append(
            f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{height - bottom + 6}" '
            f'stroke="{GRIDLINE}" stroke-width="1"/>'
        )
        pieces.append(
            f'<text x="{x:.1f}" y="{height - bottom + 24:.1f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="11" fill="{INK_MUTED}" '
            f'style="font-variant-numeric:tabular-nums">{_format_decade(exponent)}</text>'
        )

    for index, (label, value) in enumerate(positive.items()):
        y = top + row_height * index + row_height / 2
        fill = ALGORITHM_COLORS.get(label, SERIES_1)
        x = x_of(value)
        # 2px connector from the axis floor keeps the row scannable without
        # implying length-from-zero on a log scale.
        pieces.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{fill}" stroke-width="2" opacity="0.35"/>'
        )
        pieces.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{fill}"/>')
        pieces.append(
            f'<text x="{left - 16}" y="{y + 4:.1f}" text-anchor="end" font-family="{FONT}" '
            f'font-size="12" fill="{INK_SECONDARY}">{_escape(_label_for(label))}</text>'
        )
        suffix = f" {unit}" if unit else ""
        pieces.append(
            f'<text x="{x + 14:.1f}" y="{y + 4:.1f}" font-family="{FONT}" font-size="12" '
            f'font-weight="600" fill="{INK_PRIMARY}" style="font-variant-numeric:tabular-nums">'
            f'{_escape(_format_value(value) + suffix)}</text>'
        )

    pieces.append(
        f'<line x1="{left}" y1="{height - bottom + 6}" x2="{width - right}" y2="{height - bottom + 6}" '
        f'stroke="{BASELINE}" stroke-width="1"/>'
    )
    pieces.append("</svg>")
    output_path.write_text("\n".join(pieces), encoding="utf-8")
    return output_path


def _format_decade(exponent: int) -> str:
    if exponent < 0:
        return f"{10.0**exponent:g}"
    return f"{10**exponent:,}"


def _format_value(value: float) -> str:
    if value >= 1000:
        return f"{value:,.0f}"
    if value >= 10:
        return f"{value:.1f}"
    if value >= 0.01:
        return f"{value:.3f}"
    return f"{value:.4f}"


def _format_tick(value: float) -> str:
    if value >= 1000:
        return f"{value:,.0f}"
    if value >= 10:
        return f"{value:.0f}"
    return f"{value:.1f}"


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
