from collections import deque, defaultdict

def bfs_distances(start_room, all_rooms):
    distances = {room: float('inf') for room in all_rooms}
    distances[start_room] = 0
    queue = deque([start_room])

    while queue:
        current = queue.popleft()
        for neighbor in current.connections:
            if distances[neighbor] == float('inf'):
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

    return distances

def find_farthest_room(rooms, spawn_rooms, mode="avg"):
    all_distances = []
    for spawn in spawn_rooms:
        distances = bfs_distances(spawn, rooms)
        all_distances.append(distances)

    best_room = None
    best_score = -1

    for room in rooms:
        dists = [dist[room] for dist in all_distances]
        if mode == "avg":
            score = sum(dists) / len(dists)
        elif mode == "min":
            score = min(dists)
        elif mode == "max":
            score = max(dists)
        else:
            raise ValueError("mode must be 'avg', 'min', or 'max'")

        if score > best_score:
            best_score = score
            best_room = room

    return best_room
