import json
import random
import time
import sys
from collections import deque


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


def random_path(graph, start, goal, max_steps, rng):
    """Builds a random simple path from start to goal, if one is found."""
    path = [start]
    visited = {start}

    for _ in range(max_steps):
        current = path[-1]

        if current == goal:
            return path

        choices = [node for node in graph[current] if node not in visited]

        if not choices:
            return None

        next_node = rng.choice(choices)
        path.append(next_node)
        visited.add(next_node)

    return path if path[-1] == goal else None


def shortest_completion(graph, start, goal, blocked=None):
    """Finds a shortest completion path using BFS while avoiding blocked nodes."""
    blocked = set() if blocked is None else set(blocked)
    blocked.discard(start)
    blocked.discard(goal)

    queue = deque([start])
    previous = {start: None}

    while queue:
        current = queue.popleft()

        if current == goal:
            break

        for neighbor in graph[current]:
            if neighbor in blocked or neighbor in previous:
                continue

            previous[neighbor] = current
            queue.append(neighbor)

    if goal not in previous:
        return None

    path = []
    current = goal

    while current is not None:
        path.append(current)
        current = previous[current]

    path.reverse()
    return path


def improvise_harmony(graph, memory, start, goal, hmcr, par, rng):
    """Creates a candidate path using harmony-memory and pitch adjustment."""
    if memory and rng.random() < hmcr:
        base = list(rng.choice(memory))

        # Retain a prefix from a remembered path.
        cut = rng.randrange(1, len(base) + 1)
        prefix = base[:cut]

        # Pitch adjustment changes the final retained node when possible.
        if len(prefix) > 1 and rng.random() < par:
            parent = prefix[-2]
            alternatives = [
                node for node in graph[parent]
                if node not in prefix[:-1]
            ]
            if alternatives:
                prefix[-1] = rng.choice(alternatives)

        completion = shortest_completion(
            graph,
            prefix[-1],
            goal,
            blocked=prefix[:-1]
        )

        if completion is not None:
            return prefix[:-1] + completion

    # Diversification: generate a fresh random path.
    candidate = random_path(graph, start, goal, len(graph), rng)

    # Fall back to a feasible path so the search can continue.
    if candidate is None:
        candidate = shortest_completion(graph, start, goal)

    return candidate


def harmony_search(
    graph,
    start,
    goal,
    harmony_memory_size=20,
    iterations=200,
    hmcr=0.90,
    par=0.30,
    seed=0
):
    """
    Uses Harmony Search to seek a short path from start to goal.

    Path cost is the number of edges. Harmony Search is a metaheuristic, so
    unlike A*, Dijkstra, and Bellman-Ford it is not inherently guaranteed to
    find the optimal path. The BFS completion step keeps candidates feasible.
    """
    if start not in graph:
        raise ValueError(f"Node {start} not found.")

    if goal not in graph:
        raise ValueError(f"Node {goal} not found.")

    if start == goal:
        return [start], 0

    rng = random.Random(seed)
    memory = []

    # Seed the harmony memory with diverse feasible paths.
    for _ in range(harmony_memory_size * 4):
        candidate = random_path(graph, start, goal, len(graph), rng)
        if candidate is not None and candidate not in memory:
            memory.append(candidate)

        if len(memory) >= harmony_memory_size:
            break

    # Ensure at least one feasible harmony exists when a path is reachable.
    fallback = shortest_completion(graph, start, goal)
    if fallback is None:
        return None, None

    if fallback not in memory:
        memory.append(fallback)

    memory.sort(key=lambda path: len(path) - 1)
    memory = memory[:harmony_memory_size]

    for _ in range(iterations):
        candidate = improvise_harmony(
            graph,
            memory,
            start,
            goal,
            hmcr,
            par,
            rng
        )

        if candidate is None:
            continue

        if candidate not in memory:
            memory.append(candidate)
            memory.sort(key=lambda path: len(path) - 1)
            memory = memory[:harmony_memory_size]

    best_path = min(memory, key=lambda path: len(path) - 1)
    return best_path, len(best_path) - 1


def main():
    start = int(sys.argv[1])
    goal = int(sys.argv[2])
    graph = load_graph(sys.argv[3])

    starttime = time.perf_counter()
    path, distance = harmony_search(graph, start, goal)
    endtime = time.perf_counter()

    print(f"{goal}, {endtime - starttime:.9f}")

    # if path is None:
    #     print("\nNo path exists.")
    # else:
    #     print("\nBest Path Found:")
    #     print(" -> ".join(map(str, path)))
    #     print(f"\nTotal Cost: {distance}")


if __name__ == "__main__":
    main()
