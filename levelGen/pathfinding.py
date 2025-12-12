import heapq
import numpy as np
from typing import List, Tuple, Set, Optional, Dict, Callable
from enum import Enum
from dataclasses import dataclass
import time

# Assuming your existing CellType enum
class CellType(Enum):
    WALL = 0
    FLOOR = 1
    CTVIS = 2

@dataclass
class PathNode:
    """Node for pathfinding with cost tracking."""
    x: int
    y: int
    g_cost: float = 0.0  # Distance from start
    h_cost: float = 0.0  # Heuristic to goal
    parent: Optional['PathNode'] = None
    
    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost

class MovementType(Enum):
    """Different movement capabilities."""
    GROUND = "ground"        # Can walk on floor, through doors
    TERRORIST = "terrorist"

class Pathfinder:
    """Highly optimized pathfinding system for 2D arenas."""
    
    def __init__(self, arena_grid: np.ndarray):
        self.grid = arena_grid
        self.height, self.width = arena_grid.shape
        
        # Pre-calculate movement costs for different cell types
        self.movement_costs = {
            CellType.FLOOR.value: 1.0,
            CellType.CTVIS.value: 1.0,
            CellType.WALL.value: float('inf')  # Impassable for ground units
        }
        
        # Different movement type costs
        self.movement_type_costs = {
            MovementType.GROUND: self.movement_costs.copy(),

            MovementType.TERRORIST: {
                CellType.FLOOR.value: 1.0,
                CellType.CTVIS.value: 50.0,
                CellType.WALL.value: float('inf')
            },
        }
        
        # Pre-compute neighbor offsets
        self.directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 4-directional
        self.diagonal_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # Diagonals
        
        # Cache for frequently used paths
        self.path_cache: Dict[Tuple[int, int, int, int, MovementType], List[Tuple[int, int]]] = {}
        self.cache_max_size = 1000
    
    def heuristic(self, pos1: Tuple[int, int], pos2: Tuple[int, int], 
                  heuristic_type: str = "manhattan") -> float:
        """Calculate heuristic distance between two positions."""
        x1, y1 = pos1
        x2, y2 = pos2
        
        if heuristic_type == "manhattan":
            return abs(x1 - x2) + abs(y1 - y2)
        elif heuristic_type == "euclidean":
            return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        elif heuristic_type == "diagonal":
            dx, dy = abs(x1 - x2), abs(y1 - y2)
            return max(dx, dy) + (1.414 - 1) * min(dx, dy)  # Diagonal movement
        else:
            return abs(x1 - x2) + abs(y1 - y2)
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height
    
    def get_movement_cost(self, x: int, y: int, movement_type: MovementType) -> float:
        """Get movement cost for a specific cell and movement type."""
        if not self.is_valid_position(x, y):
            return float('inf')
        
        cell_type = self.grid[y, x]
        costs = self.movement_type_costs[movement_type]
        return costs.get(cell_type, float('inf'))
    
    def get_neighbors(self, pos: Tuple[int, int], allow_diagonal: bool = False) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        x, y = pos
        neighbors = []
        
        # Cardinal directions
        for dx, dy in self.directions:
            nx, ny = x + dx, y + dy
            if self.is_valid_position(nx, ny):
                neighbors.append((nx, ny))
        
        # Diagonal directions (if allowed)
        if allow_diagonal:
            for dx, dy in self.diagonal_directions:
                nx, ny = x + dx, y + dy
                if self.is_valid_position(nx, ny):
                    neighbors.append((nx, ny))
        
        return neighbors
    
    def find_path(self, 
                  start: Tuple[int, int], 
                  goal: Tuple[int, int],
                  movement_type: MovementType = MovementType.GROUND,
                  allow_diagonal: bool = False,
                  heuristic_type: str = "manhattan",
                  use_cache: bool = True) -> Optional[List[Tuple[int, int]]]:
        """
        Find optimal path using A* algorithm.
        
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
        # Check cache first
        cache_key = (*start, *goal, movement_type) if use_cache else None
        if cache_key and cache_key in self.path_cache:
            return self.path_cache[cache_key].copy()
        
        # Validate inputs
        if not (self.is_valid_position(*start) and self.is_valid_position(*goal)):
            return None
        
        if start == goal:
            return [start]
        
        # Check if goal is reachable for this movement type
        goal_cost = self.get_movement_cost(*goal, movement_type)
        if goal_cost == float('inf'):
            return None
        
        # Initialize data structures
        open_heap = []
        open_set = set()
        closed_set = set()
        
        # Create start node
        start_node = PathNode(*start)
        start_node.g_cost = 0
        start_node.h_cost = self.heuristic(start, goal, heuristic_type)
        
        heapq.heappush(open_heap, start_node)
        open_set.add(start)
        
        # For tracking best g_cost to each position
        g_costs = {start: 0.0}
        
        while open_heap:
            current_node = heapq.heappop(open_heap)
            current_pos = (current_node.x, current_node.y)
            
            # Remove from open set
            open_set.discard(current_pos)
            
            # Skip if we've already processed this with better cost
            if current_pos in closed_set:
                continue
            
            # Add to closed set
            closed_set.add(current_pos)
            
            # Check if we reached the goal
            if current_pos == goal:
                path = self._reconstruct_path(current_node)
                
                # Cache the result
                if use_cache and cache_key:
                    if len(self.path_cache) >= self.cache_max_size:
                        # Remove oldest entry (simple FIFO)
                        self.path_cache.pop(next(iter(self.path_cache)))
                    self.path_cache[cache_key] = path.copy()
                
                return path
            
            # Explore neighbors
            for neighbor_pos in self.get_neighbors(current_pos, allow_diagonal):
                if neighbor_pos in closed_set:
                    continue
                
                neighbor_x, neighbor_y = neighbor_pos
                movement_cost = self.get_movement_cost(neighbor_x, neighbor_y, movement_type)
                
                if movement_cost == float('inf'):
                    continue
                
                # Calculate costs
                diagonal_penalty = 1.414 if (allow_diagonal and 
                                           abs(neighbor_x - current_node.x) + 
                                           abs(neighbor_y - current_node.y) == 2) else 1.0
                
                tentative_g_cost = current_node.g_cost + movement_cost * diagonal_penalty
                
                # Skip if we found a worse path
                if neighbor_pos in g_costs and tentative_g_cost >= g_costs[neighbor_pos]:
                    continue
                
                # Create neighbor node
                neighbor_node = PathNode(neighbor_x, neighbor_y)
                neighbor_node.g_cost = tentative_g_cost
                neighbor_node.h_cost = self.heuristic(neighbor_pos, goal, heuristic_type)
                neighbor_node.parent = current_node
                
                # Update best known g_cost
                g_costs[neighbor_pos] = tentative_g_cost
                
                # Add to open set
                if neighbor_pos not in open_set:
                    heapq.heappush(open_heap, neighbor_node)
                    open_set.add(neighbor_pos)
        
        return None  # No path found
    
    def _reconstruct_path(self, node: PathNode) -> List[Tuple[int, int]]:
        """Reconstruct path from goal node back to start."""
        path = []
        current = node
        
        while current:
            path.append((current.x, current.y))
            current = current.parent
        
        return path[::-1]  # Reverse to get start-to-goal path
    
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
        reachable = set()
        queue = [(start, 0)]
        visited = {start}
        
        while queue:
            pos, dist = queue.pop(0)
            reachable.add(pos)
            
            if dist < max_distance:
                for neighbor in self.get_neighbors(pos):
                    if neighbor not in visited:
                        cost = self.get_movement_cost(*neighbor, movement_type)
                        if cost != float('inf'):
                            visited.add(neighbor)
                            queue.append((neighbor, dist + 1))
        
        return reachable
    
    def smooth_path(self, path: List[Tuple[int, int]], 
                   movement_type: MovementType = MovementType.GROUND) -> List[Tuple[int, int]]:
        """Smooth path by removing unnecessary waypoints using line of sight."""
        if len(path) <= 2:
            return path
        
        smoothed = [path[0]]
        current_idx = 0
        
        while current_idx < len(path) - 1:
            farthest_idx = current_idx + 1
            
            # Find the farthest point we can reach directly
            for i in range(current_idx + 2, len(path)):
                if self._has_line_of_sight(path[current_idx], path[i], movement_type):
                    farthest_idx = i
                else:
                    break
            
            smoothed.append(path[farthest_idx])
            current_idx = farthest_idx
        
        return smoothed
    
    def _has_line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int], 
                          movement_type: MovementType) -> bool:
        """Check if there's a clear line of sight between two points."""
        x1, y1 = start
        x2, y2 = end
        
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while True:
            # Check if current position is passable
            cost = self.get_movement_cost(x, y, movement_type)
            if cost == float('inf'):
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
    grid = np.ones((50, 50), dtype=int)  # All floor
    
    # Add some walls
    grid[10:40, 25] = CellType.WALL.value  # Vertical wall
    grid[25, 10:40] = CellType.WALL.value  # Horizontal wall
    grid[25, 25] = CellType.DOOR.value     # Door in the intersection
    
    pathfinder = Pathfinder(grid)
    
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
            print(f"Test {i+1} ({movement_type.value}): Path length = {len(path) if path else 'No path'}")
    
    end_time = time.time()
    print(f"Total time: {end_time - start_time:.3f} seconds")
    
    return pathfinder

if __name__ == "__main__":
    # Run performance test
    pathfinder = test_pathfinding_performance()