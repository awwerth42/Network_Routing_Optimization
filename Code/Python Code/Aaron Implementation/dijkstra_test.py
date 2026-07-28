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

    # JSON keys are strings, convert them to integers
    graph = {
        int(node): neighbors
        for node, neighbors in data["adjacency_list"].items()
    }

    return graph


def dijkstra(graph, start, goal):
    """
    Finds the shortest path using Dijkstra's algorithm.

    Assumes every edge has weight = 1.
    """

    if start not in graph:
        raise ValueError(f"Node {start} not found.")

    if goal not in graph:
        raise ValueError(f"Node {goal} not found.")

    # Distance from start to each node
    distances = {
        node: float("inf")
        for node in graph
    }

    distances[start] = 0

    # Used to reconstruct the path
    previous = {}

    # Priority queue stores (distance, node)
    priority_queue = [(0, start)]

    while priority_queue:

        current_distance, current = heapq.heappop(priority_queue)

        # Skip stale queue entries
        if current_distance > distances[current]:
            continue

        # Stop once we've reached the destination
        if current == goal:
            break

        # Visit neighbors
        for neighbor in graph[current]:

            weight = 1
            new_distance = current_distance + weight

            if new_distance < distances[neighbor]:

                distances[neighbor] = new_distance
                previous[neighbor] = current

                heapq.heappush(
                    priority_queue,
                    (new_distance, neighbor)
                )

    if distances[goal] == float("inf"):
        return None, None

    # Reconstruct shortest path
    path = []

    current = goal

    while current != start:
        path.append(current)
        current = previous[current]

    path.append(start)

    path.reverse()

    return path, distances[goal]

def main():


    # start = int(input("Start node: "))
    # goal = int(input("Goal node: "))
    start = int(sys.argv[1])
    #print(start)
    goal = int(sys.argv[2])
    #print(goal)
    #graph = load_graph("graph.json")
    graph = load_graph(sys.argv[3])

    # start = time.perf_counter()
    starttime = time.perf_counter()
    path, distance = dijkstra(graph, start, goal)
    endtime = time.perf_counter()

    #print(f"Execution time: {endtime - starttime:.9f} seconds")
    print(f"{goal}, {endtime - starttime:.9f}")

    #if path is None:
    #    print("\nNo path exists.")
    #else:
    #    print("\nShortest Path:")
    #    print(" -> ".join(map(str, path)))

    #    print(f"\nTotal Cost: {distance}")


if __name__ == "__main__":
    main()
