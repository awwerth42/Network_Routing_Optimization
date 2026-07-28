import json
import time
import sys


def load_graph(json_file):
    """
    Loads an adjacency list from a JSON file.

    Expected format:

    {
        "adjacency_list": {
            "1": [4, 17, 25],
            "2": [5, 18],
            ...
        }
    }
    """
    with open(json_file, "r") as f:
        data = json.load(f)

    graph = {
        int(node): [int(neighbor) for neighbor in neighbors]
        for node, neighbors in data["adjacency_list"].items()
    }

    for neighbors in list(graph.values()):
        for neighbor in neighbors:
            graph.setdefault(neighbor, [])

    return graph


def bellman_ford(graph, start, goal):
    """
    Finds a shortest path using the Bellman-Ford algorithm.

    Assumes every edge has weight = 1.
    """
    if start not in graph:
        raise ValueError(f"Node {start} not found.")

    if goal not in graph:
        raise ValueError(f"Node {goal} not found.")

    distances = {node: float("inf") for node in graph}
    distances[start] = 0
    previous = {}

    edges = [
        (node, neighbor, 1)
        for node, neighbors in graph.items()
        for neighbor in neighbors
    ]

    # Relax every edge up to |V| - 1 times.
    for _ in range(len(graph) - 1):
        changed = False

        for source, destination, weight in edges:
            if distances[source] == float("inf"):
                continue

            new_distance = distances[source] + weight

            if new_distance < distances[destination]:
                distances[destination] = new_distance
                previous[destination] = source
                changed = True

        if not changed:
            break

    # Included for completeness if weighted input is added later.
    for source, destination, weight in edges:
        if (
            distances[source] != float("inf")
            and distances[source] + weight < distances[destination]
        ):
            raise ValueError("Graph contains a negative-weight cycle.")

    if distances[goal] == float("inf"):
        return None, None

    path = []
    current = goal

    while current != start:
        path.append(current)
        current = previous[current]

    path.append(start)
    path.reverse()

    return path, distances[goal]


def main():
    start = int(sys.argv[1])
    goal = int(sys.argv[2])
    graph = load_graph(sys.argv[3])

    starttime = time.perf_counter()
    path, distance = bellman_ford(graph, start, goal)
    endtime = time.perf_counter()

    print(f"{goal}, {endtime - starttime:.9f}")

    # if path is None:
    #     print("\nNo path exists.")
    # else:
    #     print("\nShortest Path:")
    #     print(" -> ".join(map(str, path)))
    #     print(f"\nTotal Cost: {distance}")


if __name__ == "__main__":
    main()
