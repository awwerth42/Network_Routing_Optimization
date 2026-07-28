from pathlib import Path
import re

import matplotlib.pyplot as plt


# Directory containing this script and the result files.
DATA_DIRECTORY = Path(__file__).resolve().parent

# Files to plot. Add more result files here if needed.
RESULT_FILES = [
    "results_aster.txt",
    "results_bellman_ford.txt",
    "results_dijkstra.txt",
    "results_harmony_search.txt",
]


def algorithm_name_from_filename(file_path: Path) -> str:
    """Convert a filename such as results_bellman_ford.txt to Bellman Ford."""
    name = file_path.stem

    if name.startswith("results_"):
        name = name[len("results_"):]

    return name.replace("_", " ").title()


def load_results(file_path: Path) -> tuple[list[int], list[float]]:
    """Read node counts and execution times from a comma-separated text file."""
    node_counts: list[int] = []
    execution_times: list[float] = []

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            parts = [part.strip() for part in line.split(",")]

            if len(parts) != 2:
                raise ValueError(
                    f"{file_path.name}, line {line_number}: "
                    "expected exactly two comma-separated values."
                )

            try:
                node_count = int(parts[0])
                execution_time = float(parts[1])
            except ValueError as error:
                raise ValueError(
                    f"{file_path.name}, line {line_number}: "
                    "the first value must be an integer and the second a number."
                ) from error

            node_counts.append(node_count)
            execution_times.append(execution_time)

    if not node_counts:
        raise ValueError(f"{file_path.name} contains no usable data.")

    return node_counts, execution_times


def create_plot(file_path: Path, output_directory: Path) -> Path:
    """Create and save one green execution-time plot."""
    node_counts, execution_times = load_results(file_path)
    algorithm_name = algorithm_name_from_filename(file_path)

    plt.figure(figsize=(9, 6))
    plt.plot(
        node_counts,
        execution_times,
        color="green",
        marker="o",
        linewidth=2,
        markersize=6,
    )

    plt.title(f"{algorithm_name} Execution Time")
    plt.xlabel("Number of Nodes")
    plt.ylabel("Execution Time (seconds)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", algorithm_name.lower())
    output_path = output_directory / f"{safe_name}_execution_time.png"

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    return output_path


def main() -> None:
    output_directory = DATA_DIRECTORY / "plots"
    output_directory.mkdir(exist_ok=True)

    created_plots: list[Path] = []

    for filename in RESULT_FILES:
        file_path = DATA_DIRECTORY / filename

        if not file_path.exists():
            print(f"Skipping missing file: {file_path.name}")
            continue

        output_path = create_plot(file_path, output_directory)
        created_plots.append(output_path)
        print(f"Created: {output_path}")

    if not created_plots:
        raise FileNotFoundError(
            "None of the configured result files were found."
        )


if __name__ == "__main__":
    main()
