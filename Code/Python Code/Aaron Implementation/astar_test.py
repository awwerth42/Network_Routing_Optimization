import json
import heapq
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

    # Ensure nodes that only appear as neighbors are still represented.
    for neighbors in list(graph.values()):
        for neighbor in neighbors:
            graph.setdefault(neighbor, [])

    return graph


def heuristic(node, goal):
    """
    Returns an admissible heuristic estimate.

    The input graph contains no coordinates or other geometric information,
    so the safest estimate is 0. This keeps A* correct and makes it behave
    like Dijkstra's algorithm on this unweighted graph.
    """
    return 0


def astar(graph, start, goal):
    """
    Finds a shortest path using the A* search algorithm.

    Assumes every edge has weight = 1.
    """
    if start not in graph:
        raise ValueError(f"Node {start} not found.")

    if goal not in graph:
        raise ValueError(f"Node {goal} not found.")

    distances = {node: float("inf") for node in graph}
    distances[start] = 0

    previous = {}

    # Priority queue stores (estimated total cost, path cost, node).
    priority_queue = [(heuristic(start, goal), 0, start)]

    while priority_queue:
        _, current_distance, current = heapq.heappop(priority_queue)

        if current_distance > distances[current]:
            continue

        if current == goal:
            break

        for neighbor in graph[current]:
            weight = 1
            new_distance = current_distance + weight

            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                previous[neighbor] = current

                estimated_total = new_distance + heuristic(neighbor, goal)
                heapq.heappush(
                    priority_queue,
                    (estimated_total, new_distance, neighbor)
                )

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
    path, distance = astar(graph, start, goal)
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
