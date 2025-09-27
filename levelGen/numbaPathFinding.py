import numpy as np
import numba
from numba import njit, types
from typing import List, Tuple, Set, Optional, Dict
from enum import Enum
import heapq
import time

# Cell type constants for Numba compatibility
CELL_WALL = 0
CELL_FLOOR = 1
CELL_DOOR = 2
CELL_STAIRS_UP = 3
CELL_STAIRS_DOWN = 4
CELL_ENTRANCE = 5
CELL_EXIT = 6

# Movement type constants
MOVEMENT_GROUND = 0
MOVEMENT_FLYING = 1
MOVEMENT_CLIMBING = 2
MOVEMENT_ETHEREAL = 3

# Heuristic type constants
HEURISTIC_MANHATTAN = 0
HEURISTIC_EUCLIDEAN = 1
HEURISTIC_DIAGONAL = 2

# Original enums for API compatibility
class CellType(Enum):
    WALL = 0
    FLOOR = 1
    DOOR = 2
    STAIRS_UP = 3
    STAIRS_DOWN = 4
    ENTRANCE = 5
    EXIT = 6

class MovementType(Enum):
    GROUND = "ground"
    FLYING = "flying"
    CLIMBING = "climbing"
    ETHEREAL = "ethereal"

@njit
def get_movement_costs_ground():
    """Get movement costs for ground units."""
    costs = np.full(7, np.inf, dtype=np.float32)
    costs[CELL_FLOOR] = 1.0
    costs[CELL_DOOR] = 1.2
    costs[CELL_STAIRS_UP] = 1.5
    costs[CELL_STAIRS_DOWN] = 1.5
    costs[CELL_ENTRANCE] = 1.0
    costs[CELL_EXIT] = 1.0
    return costs

@njit
def get_movement_costs_flying():
    """Get movement costs for flying units."""
    costs = np.ones(7, dtype=np.float32)
    costs[CELL_WALL] = 2.0
    return costs

@njit
def get_movement_costs_climbing():
    """Get movement costs for climbing units."""
    costs = np.ones(7, dtype=np.float32)
    costs[CELL_DOOR] = 1.2
    costs[CELL_WALL] = 3.0
    return costs

@njit
def get_movement_costs_ethereal():
    """Get movement costs for ethereal units."""
    return np.ones(7, dtype=np.float32)

@njit
def get_movement_cost_for_type(cell_type: int, movement_type: int) -> float:
    """Get movement cost for specific cell and movement type."""
    if movement_type == MOVEMENT_GROUND:
        costs = get_movement_costs_ground()
    elif movement_type == MOVEMENT_FLYING:
        costs = get_movement_costs_flying()
    elif movement_type == MOVEMENT_CLIMBING:
        costs = get_movement_costs_climbing()
    else:  # MOVEMENT_ETHEREAL
        costs = get_movement_costs_ethereal()
    
    if cell_type < 0 or cell_type >= len(costs):
        return np.inf
    return costs[cell_type]

@njit
def calculate_heuristic(x1: int, y1: int, x2: int, y2: int, heuristic_type: int) -> float:
    """Calculate heuristic distance between two positions."""
    if heuristic_type == HEURISTIC_MANHATTAN:
        return float(abs(x2 - x1) + abs(y2 - y1))
    elif heuristic_type == HEURISTIC_EUCLIDEAN:
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    else:  # HEURISTIC_DIAGONAL
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        return max(dx, dy) + (1.414 - 1.0) * min(dx, dy)

@njit
def get_neighbors(x: int, y: int, width: int, height: int, allow_diagonal: bool):
    """Get valid neighbor positions."""
    neighbors = []
    
    # Cardinal directions
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            neighbors.append((nx, ny))
    
    # Diagonal directions
    if allow_diagonal:
        diagonal_dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in diagonal_dirs:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                neighbors.append((nx, ny))
    
    return neighbors

@njit
def reconstruct_path(came_from: np.ndarray, start_x: int, start_y: int, 
                    end_x: int, end_y: int, width: int) -> List[Tuple[int, int]]:
    """Reconstruct path from came_from array."""
    path = []
    current_x, current_y = end_x, end_y
    
    while not (current_x == start_x and current_y == start_y):
        path.append((current_x, current_y))
        parent_idx = came_from[current_y, current_x]
        if parent_idx == -1:
            break
        current_y = parent_idx // width
        current_x = parent_idx % width
    
    path.append((start_x, start_y))
    path.reverse()
    return path

@njit
def astar_numba_core(grid: np.ndarray,
                     start_x: int, start_y: int,
                     goal_x: int, goal_y: int,
                     movement_type: int,
                     allow_diagonal: bool,
                     heuristic_type: int) -> Optional[List[Tuple[int, int]]]:
    """
    Core Numba-accelerated A* pathfinding.
    
    Args:
        grid: 2D array with cell types
        start_x, start_y: Starting position
        goal_x, goal_y: Goal position
        movement_type: Movement type constant
        allow_diagonal: Allow diagonal movement
        heuristic_type: Heuristic type constant
    
    Returns:
        List of (x, y) positions forming the path, or None if no path exists
    """
    height, width = grid.shape
    
    # Validate positions
    if not (0 <= start_x < width and 0 <= start_y < height):
        return None
    if not (0 <= goal_x < width and 0 <= goal_y < height):
        return None
    
    # Check if goal is reachable
    goal_cell = grid[goal_y, goal_x]
    goal_cost = get_movement_cost_for_type(goal_cell, movement_type)
    if goal_cost == np.inf:
        return None
    
    if start_x == goal_x and start_y == goal_y:
        return [(start_x, start_y)]
    
    # Initialize arrays
    g_costs = np.full((height, width), np.inf, dtype=np.float32)
    f_costs = np.full((height, width), np.inf, dtype=np.float32)
    came_from = np.full((height, width), -1, dtype=np.int32)
    closed_set = np.zeros((height, width), dtype=np.bool_)
    open_set = np.zeros((height, width), dtype=np.bool_)
    
    # Priority queue as list (f_cost, x, y)
    open_list = [(0.0, start_x, start_y)]
    
    # Initialize start
    g_costs[start_y, start_x] = 0
    h_cost = calculate_heuristic(start_x, start_y, goal_x, goal_y, heuristic_type)
    f_costs[start_y, start_x] = h_cost
    open_set[start_y, start_x] = True
    
    nodes_explored = 0
    max_nodes = width * height * 2  # Safety limit
    
    while len(open_list) > 0 and nodes_explored < max_nodes:
        nodes_explored += 1
        
        # Find node with minimum f_cost
        min_idx = 0
        min_f = open_list[0][0]
        for i in range(1, len(open_list)):
            if open_list[i][0] < min_f:
                min_f = open_list[i][0]
                min_idx = i
        
        # Pop the minimum
        current_f, current_x, current_y = open_list[min_idx]
        open_list.pop(min_idx)
        
        # Skip if already closed
        if closed_set[current_y, current_x]:
            continue
        
        # Mark as closed
        closed_set[current_y, current_x] = True
        open_set[current_y, current_x] = False
        
        # Check if we reached the goal
        if current_x == goal_x and current_y == goal_y:
            return reconstruct_path(came_from, start_x, start_y, goal_x, goal_y, width)
        
        # Explore neighbors
        neighbors = get_neighbors(current_x, current_y, width, height, allow_diagonal)
        
        for nx, ny in neighbors:
            if closed_set[ny, nx]:
                continue
            
            # Get movement cost
            cell_type = grid[ny, nx]
            movement_cost = get_movement_cost_for_type(cell_type, movement_type)
            
            if movement_cost == np.inf:
                continue
            
            # Calculate diagonal penalty
            diagonal_penalty = 1.0
            if allow_diagonal and abs(nx - current_x) + abs(ny - current_y) == 2:
                diagonal_penalty = 1.414
            
            # Calculate tentative g_cost
            tentative_g = g_costs[current_y, current_x] + movement_cost * diagonal_penalty
            
            # Check if this is a better path
            if tentative_g < g_costs[ny, nx]:
                # Update costs
                g_costs[ny, nx] = tentative_g
                h_cost = calculate_heuristic(nx, ny, goal_x, goal_y, heuristic_type)
                f_costs[ny, nx] = tentative_g + h_cost
                
                # Update parent
                came_from[ny, nx] = current_y * width + current_x
                
                # Add to open set if not already there
                if not open_set[ny, nx]:
                    open_list.append((f_costs[ny, nx], nx, ny))
                    open_set[ny, nx] = True
    
    return None  # No path found

@njit
def check_line_of_sight(grid: np.ndarray, x1: int, y1: int, x2: int, y2: int, 
                        movement_type: int) -> bool:
    """Check if there's a clear line of sight between two points using Bresenham's algorithm."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    
    x, y = x1, y1
    
    while True:
        # Check if current position is passable
        if y < 0 or y >= grid.shape[0] or x < 0 or x >= grid.shape[1]:
            return False
        
        cell_type = grid[y, x]
        cost = get_movement_cost_for_type(cell_type, movement_type)
        if cost == np.inf:
            return False
        
        if x == x2 and y == y2:
            break
        
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    
    return True

@njit
def smooth_path_numba(path: List[Tuple[int, int]], grid: np.ndarray, 
                      movement_type: int) -> List[Tuple[int, int]]:
    """Smooth path by removing unnecessary waypoints."""
    if len(path) <= 2:
        return path
    
    smoothed = [path[0]]
    current_idx = 0
    
    while current_idx < len(path) - 1:
        farthest_idx = current_idx + 1
        
        # Find the farthest point we can reach directly
        for i in range(current_idx + 2, len(path)):
            if check_line_of_sight(grid, path[current_idx][0], path[current_idx][1],
                                  path[i][0], path[i][1], movement_type):
                farthest_idx = i
            else:
                break
        
        smoothed.append(path[farthest_idx])
        current_idx = farthest_idx
    
    return smoothed

@njit
def get_reachable_area_numba(grid: np.ndarray, start_x: int, start_y: int,
                             max_distance: int, movement_type: int) -> List[Tuple[int, int]]:
    """Get all positions reachable within a certain distance."""
    height, width = grid.shape
    visited = np.zeros((height, width), dtype=np.bool_)
    reachable = []
    
    # BFS queue: (x, y, distance)
    queue = [(start_x, start_y, 0)]
    queue_start = 0
    visited[start_y, start_x] = True
    
    while queue_start < len(queue):
        x, y, dist = queue[queue_start]
        queue_start += 1
        reachable.append((x, y))
        
        if dist < max_distance:
            neighbors = get_neighbors(x, y, width, height, False)
            for nx, ny in neighbors:
                if not visited[ny, nx]:
                    cell_type = grid[ny, nx]
                    cost = get_movement_cost_for_type(cell_type, movement_type)
                    if cost != np.inf:
                        visited[ny, nx] = True
                        queue.append((nx, ny, dist + 1))
    
    return reachable


class Pathfinder:
    """Numba-accelerated pathfinding system maintaining API compatibility."""
    
    def __init__(self, arena_grid: np.ndarray):
        self.grid = arena_grid
        self.height, self.width = arena_grid.shape
        
        # Cache for frequently used paths
        self.path_cache: Dict[Tuple[int, int, int, int, int], List[Tuple[int, int]]] = {}
        self.cache_max_size = 1000
        
        # Movement type mapping
        self.movement_type_map = {
            MovementType.GROUND: MOVEMENT_GROUND,
            MovementType.FLYING: MOVEMENT_FLYING,
            MovementType.CLIMBING: MOVEMENT_CLIMBING,
            MovementType.ETHEREAL: MOVEMENT_ETHEREAL
        }
        
        # Heuristic type mapping
        self.heuristic_map = {
            "manhattan": HEURISTIC_MANHATTAN,
            "euclidean": HEURISTIC_EUCLIDEAN,
            "diagonal": HEURISTIC_DIAGONAL
        }
        
        # Pre-compile Numba functions with first call
        self._warmup_jit()
    
    def _warmup_jit(self):
        """Warm up JIT compilation."""
        # Small test to compile functions
        test_grid = np.ones((3, 3), dtype=np.int32)
        _ = astar_numba_core(test_grid, 0, 0, 2, 2, MOVEMENT_GROUND, False, HEURISTIC_MANHATTAN)
    
    def heuristic(self, pos1: Tuple[int, int], pos2: Tuple[int, int], 
                  heuristic_type: str = "manhattan") -> float:
        """Calculate heuristic distance between two positions."""
        h_type = self.heuristic_map.get(heuristic_type, HEURISTIC_MANHATTAN)
        return calculate_heuristic(pos1[0], pos1[1], pos2[0], pos2[1], h_type)
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height
    
    def get_movement_cost(self, x: int, y: int, movement_type: MovementType) -> float:
        """Get movement cost for a specific cell and movement type."""
        if not self.is_valid_position(x, y):
            return float('inf')
        
        cell_type = self.grid[y, x]
        m_type = self.movement_type_map[movement_type]
        return get_movement_cost_for_type(cell_type, m_type)
    
    def get_neighbors(self, pos: Tuple[int, int], allow_diagonal: bool = False) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        return get_neighbors(pos[0], pos[1], self.width, self.height, allow_diagonal)
    
    def find_path(self, 
                  start: Tuple[int, int], 
                  goal: Tuple[int, int],
                  movement_type: MovementType = MovementType.GROUND,
                  allow_diagonal: bool = False,
                  heuristic_type: str = "manhattan",
                  use_cache: bool = True) -> Optional[List[Tuple[int, int]]]:
        """
        Find optimal path using Numba-accelerated A* algorithm.
        
        Args:
            start: Starting position (x, y)
            goal: Goal position (x, y)
            movement_type: Type of movement capabilities
            allow_diagonal: Allow diagonal movement
            heuristic_type: Heuristic function to use
            use_cache: Whether to use path caching
        
        Returns:
            List of positions forming the path, or None if no path exists
        """
        # Convert enums to integers for Numba
        m_type = self.movement_type_map[movement_type]
        h_type = self.heuristic_map.get(heuristic_type, HEURISTIC_MANHATTAN)
        
        # Check cache
        cache_key = (*start, *goal, m_type) if use_cache else None
        if cache_key and cache_key in self.path_cache:
            return self.path_cache[cache_key].copy()
        
        # Run Numba-accelerated pathfinding
        path = astar_numba_core(
            self.grid,
            start[0], start[1],
            goal[0], goal[1],
            m_type,
            allow_diagonal,
            h_type
        )
        
        # Cache result
        if use_cache and cache_key and path is not None:
            if len(self.path_cache) >= self.cache_max_size:
                # Remove oldest entry
                self.path_cache.pop(next(iter(self.path_cache)))
            self.path_cache[cache_key] = path.copy()
        
        return path
    
    def find_multiple_paths(self, 
                           start: Tuple[int, int], 
                           goals: List[Tuple[int, int]],
                           movement_type: MovementType = MovementType.GROUND) -> Dict[Tuple[int, int], Optional[List[Tuple[int, int]]]]:
        """Find paths to multiple goals efficiently."""
        results = {}
        
        for goal in goals:
            path = self.find_path(start, goal, movement_type)
            results[goal] = path
        
        return results
    
    def find_nearest_reachable(self, 
                              start: Tuple[int, int],
                              targets: List[Tuple[int, int]],
                              movement_type: MovementType = MovementType.GROUND) -> Optional[Tuple[Tuple[int, int], List[Tuple[int, int]]]]:
        """Find the nearest reachable target and its path."""
        best_target = None
        best_path = None
        min_distance = float('inf')
        
        for target in targets:
            path = self.find_path(start, target, movement_type)
            if path and len(path) < min_distance:
                min_distance = len(path)
                best_target = target
                best_path = path
        
        if best_target:
            return best_target, best_path
        return None
    
    def get_reachable_area(self, 
                          start: Tuple[int, int],
                          max_distance: int,
                          movement_type: MovementType = MovementType.GROUND) -> Set[Tuple[int, int]]:
        """Get all positions reachable within a certain distance."""
        m_type = self.movement_type_map[movement_type]
        reachable_list = get_reachable_area_numba(
            self.grid, start[0], start[1], max_distance, m_type
        )
        return set(reachable_list)
    
    def smooth_path(self, path: List[Tuple[int, int]], 
                   movement_type: MovementType = MovementType.GROUND) -> List[Tuple[int, int]]:
        """Smooth path by removing unnecessary waypoints using line of sight."""
        if not path or len(path) <= 2:
            return path
        
        m_type = self.movement_type_map[movement_type]
        return smooth_path_numba(path, self.grid, m_type)
    
    def _has_line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int], 
                          movement_type: MovementType) -> bool:
        """Check if there's a clear line of sight between two points."""
        m_type = self.movement_type_map[movement_type]
        return check_line_of_sight(self.grid, start[0], start[1], end[0], end[1], m_type)
    
    def _reconstruct_path(self, node) -> List[Tuple[int, int]]:
        """Compatibility method - not used in Numba version."""
        # This is handled internally by the Numba function
        raise NotImplementedError("This method is not used in the Numba version")
    
    def clear_cache(self):
        """Clear the path cache."""
        self.path_cache.clear()
    
    def get_path_length(self, path: List[Tuple[int, int]]) -> float:
        """Calculate the actual length of a path considering diagonal movement."""
        if not path or len(path) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            
            # Diagonal movement costs more
            if abs(x2 - x1) + abs(y2 - y1) == 2:
                total_length += 1.414  # sqrt(2)
            else:
                total_length += 1.0
        
        return total_length


# Performance testing and usage examples
def test_pathfinding_performance():
    """Test pathfinding performance with different scenarios."""
    # Create a test grid
    grid = np.ones((50, 50), dtype=np.int32)  # All floor
    
    # Add some walls
    grid[10:40, 25] = CellType.WALL.value  # Vertical wall
    grid[25, 10:40] = CellType.WALL.value  # Horizontal wall
    grid[25, 25] = CellType.DOOR.value     # Door in the intersection
    
    pathfinder = Pathfinder(grid)
    
    print("Running performance tests...")
    start_time = time.time()
    
    # Test multiple pathfinding scenarios
    test_cases = [
        ((5, 5), (45, 45)),    # Long diagonal path
        ((5, 5), (45, 5)),     # Horizontal path
        ((5, 5), (5, 45)),     # Vertical path
        ((10, 10), (40, 40)),  # Path requiring door usage
    ]
    
    for i, (start, goal) in enumerate(test_cases):
        # Test different movement types
        for movement_type in [MovementType.GROUND, MovementType.FLYING, MovementType.CLIMBING]:
            path = pathfinder.find_path(start, goal, movement_type)
            if path:
                print(f"Test {i+1} ({movement_type.value}): Path length = {len(path)}")
                # Test path smoothing
                smoothed = pathfinder.smooth_path(path, movement_type)
                print(f"  Smoothed path length: {len(smoothed)}")
            else:
                print(f"Test {i+1} ({movement_type.value}): No path found")
    
    end_time = time.time()
    print(f"\nTotal time: {end_time - start_time:.3f} seconds")
    
    # Test reachable area
    print("\nTesting reachable area from (25, 25)...")
    reachable = pathfinder.get_reachable_area((25, 25), 10, MovementType.GROUND)
    print(f"Reachable positions within distance 10: {len(reachable)}")
    
    # Test finding nearest target
    print("\nTesting find nearest reachable...")
    targets = [(45, 45), (5, 45), (45, 5)]
    result = pathfinder.find_nearest_reachable((25, 25), targets, MovementType.GROUND)
    if result:
        target, path = result
        print(f"Nearest target: {target}, Path length: {len(path)}")
    
    return pathfinder


def benchmark_comparison():
    """Compare performance with non-Numba version."""
    sizes = [50, 100, 200]
    
    for size in sizes:
        print(f"\n{'='*50}")
        print(f"Grid size: {size}x{size}")
        
        # Create test grid with obstacles
        grid = np.ones((size, size), dtype=np.int32)
        
        # Add random walls
        np.random.seed(42)
        wall_mask = np.random.random((size, size)) < 0.2
        grid[wall_mask] = CellType.WALL.value
        
        pathfinder = Pathfinder(grid)
        
        # Generate random test cases
        test_cases = []
        for _ in range(10):
            start = (np.random.randint(0, size), np.random.randint(0, size))
            goal = (np.random.randint(0, size), np.random.randint(0, size))
            test_cases.append((start, goal))
        
        # Warm up JIT
        pathfinder.find_path(test_cases[0][0], test_cases[0][1])
        
        # Benchmark
        start_time = time.time()
        paths_found = 0
        total_path_length = 0
        
        for start, goal in test_cases:
            path = pathfinder.find_path(start, goal, MovementType.GROUND, allow_diagonal=True)
            if path:
                paths_found += 1
                total_path_length += len(path)
        
        end_time = time.time()
        
        print(f"Paths found: {paths_found}/{len(test_cases)}")
        if paths_found > 0:
            print(f"Average path length: {total_path_length / paths_found:.1f}")
        print(f"Total time: {end_time - start_time:.4f} seconds")
        print(f"Average time per path: {(end_time - start_time) / len(test_cases) * 1000:.2f} ms")


if __name__ == "__main__":
    # Run performance test
    print("Testing API compatibility and features...")
    pathfinder = test_pathfinding_performance()
    
    # Run benchmark comparison
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK")
    benchmark_comparison()