import heapq
import numpy as np
from typing import List, Tuple, Set, Optional, Dict, Callable
from enum import Enum
from dataclasses import dataclass
import time
from levelGen.numbaPathFinding import Pathfinder, MovementType
#from levelGen.numbaPathFinding import NumbaPathfinder
from levelGen.mapGen import ArenaGenerator, CellType
import math
from itertools import combinations

class ArenaWithPathfinding:
    """Extended arena generator with integrated pathfinding capabilities."""
    
    def __init__(self, app, arena_generator: ArenaGenerator):
        """Initialize with an existing ArenaGenerator instance."""
        self.app = app
        self.arena_gen = arena_generator
        self.pathfinder = None
        
        # Initialize pathfinder if arena exists
        if hasattr(arena_generator, 'grid') and arena_generator.grid is not None:
            self.pathfinder = Pathfinder(app)
    
    def generate_arena_with_pathfinding(self, **kwargs):
        """Generate arena and initialize pathfinding system."""
        # Generate the arena
        grid = self.arena_gen.generate_arena(**kwargs)
        
        # Initialize pathfinder with the new grid
        self.pathfinder = Pathfinder(grid)
        
        return grid
    
    def validate_arena_connectivity(self) -> Dict[str, any]:
        """Validate that all important areas in the arena are connected."""
        if not self.pathfinder:
            return {"valid": False, "error": "No pathfinder initialized"}
        
        results = {
            "valid": True,
            "entrance_to_exit": False,
            "all_rooms_connected": True,
            "isolated_areas": [],
            "connectivity_score": 0.0
        }
        
        # Get entrance and exit positions
        entrance = self.arena_gen.get_entrance_position()
        exit_pos = self.arena_gen.get_exit_position()
        
        # Test entrance to exit connectivity
        if entrance and exit_pos:
            path = self.pathfinder.find_path(entrance, exit_pos)
            results["entrance_to_exit"] = path is not None
            if path:
                results["entrance_to_exit_distance"] = len(path)
        
        # Test room connectivity
        room_centers = [(room.center()) for room in self.arena_gen.rooms]
        
        if len(room_centers) > 1:
            disconnected_rooms = 0
            total_connections = 0
            
            for i, room1_center in enumerate(room_centers):
                for j, room2_center in enumerate(room_centers[i+1:], i+1):
                    path = self.pathfinder.find_path(room1_center, room2_center)
                    if path:
                        total_connections += 1
                    else:
                        disconnected_rooms += 1
            
            max_possible = len(room_centers) * (len(room_centers) - 1) // 2
            results["connectivity_score"] = total_connections / max_possible if max_possible > 0 else 1.0
            results["all_rooms_connected"] = disconnected_rooms == 0
        
        # Overall validation
        results["valid"] = (results["entrance_to_exit"] and 
                          results["all_rooms_connected"] and 
                          results["connectivity_score"] > 0.8)
        
        return results
    

    def find_spawn_rooms(self, num_spawns: int):
        best_combo = None
        best_min_dist = -1
        iters = 0

        for combo in combinations(self.arena_gen.rooms, num_spawns):
            min_dist = min(
                math.dist(r1.center(), r2.center())
                for i, r1 in enumerate(combo)
                for r2 in combo[i+1:]
            )
            iters += 1
            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_combo = combo

        print("Combo found", best_combo, "iterations", iters)
        return best_combo
    
    

    def find_detonation_sites(self, ct_spawn, t_spawn):
        rooms = self.arena_gen.rooms

        # Precompute centers for speed
        room_centers = {r: r.center() for r in rooms}
        ct_center = ct_spawn.center()
        t_center = t_spawn.center()

        # Pre-filter by distance to both spawns
        # (Tune these thresholds as needed)
        MIN_CT_DIST = 30    # example
        MIN_T_DIST  = 70    # example

        candidate_rooms = []
        for r in rooms:
            rc = room_centers[r]
            if (math.dist(rc, ct_center) >= MIN_CT_DIST and
                math.dist(rc, t_center)  >= MIN_T_DIST):
                candidate_rooms.append(r)

        # If not enough, fallback to all rooms
        if len(candidate_rooms) < 3:
            candidate_rooms = rooms

        best_combo = None
        best_min_dist = -1
        iters = 0

        for combo in combinations(candidate_rooms, 3):
            # Compute the minimum important distance:
            # - between the sites themselves
            # - from each site to each spawn
            dists = []

            # site–site distances
            for i in range(3):
                for j in range(i+1, 3):
                    d = math.dist(room_centers[combo[i]], room_centers[combo[j]])
                    dists.append(d)

            # site–spawn distances
            for r in combo:
                rc = room_centers[r]
                d_ct = math.dist(rc, ct_center)
                d_t  = math.dist(rc, t_center)
                dists.append(d_ct)
                dists.append(d_t)

            min_dist = min(dists)
            iters += 1

            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_combo = combo

        print("Site combo found:", best_combo, "iterations:", iters)
        return best_combo


    
    def find_optimal_spawn_points(self, 
                                num_spawns: int, 
                                min_distance: int = 10,
                                movement_type: MovementType = MovementType.GROUND) -> List[Tuple[int, int]]:
        """Find optimal spawn points using fast euclidean distance with connectivity validation."""
        if not self.pathfinder:
            return []
        
        candidates = self.arena_gen.get_spawn_points()
        if len(candidates) < num_spawns:
            return candidates
        
        # Pre-filter candidates for connectivity (do this once)
        connected_candidates = []
        entrance = self.arena_gen.get_entrance_position()
        
        if entrance and entrance in candidates:
            connected_candidates.append(entrance)
            reference_point = entrance
        else:
            reference_point = candidates[0] if candidates else None
            connected_candidates.append(reference_point)
        
        # Batch connectivity check - only check if each candidate can reach the reference point
        for candidate in candidates:
            if candidate != reference_point:
                path = self.pathfinder.find_path(candidate, reference_point, movement_type)
                if path:  # If it can reach reference, assume it's in the connected component
                    connected_candidates.append(candidate)
        
        if len(connected_candidates) < num_spawns:
            return connected_candidates
        
        # Use euclidean distance for fast selection (much faster than pathfinding)
        selected = [connected_candidates[0]]  # Start with entrance or first candidate
        remaining = connected_candidates[1:]
        
        while len(selected) < num_spawns and remaining:
            best_candidate = None
            best_min_distance = -1
            
            for candidate in remaining:
                # Calculate minimum euclidean distance to selected points
                min_euclidean_dist = min(
                    math.sqrt((candidate[0] - sel[0])**2 + (candidate[1] - sel[1])**2)
                    for sel in selected
                )
                
                if min_euclidean_dist > best_min_distance:
                    best_min_distance = min_euclidean_dist
                    best_candidate = candidate
            
            if best_candidate and best_min_distance >= min_distance:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                # If no candidate meets distance requirement, pick the best available
                if best_candidate:
                    selected.append(best_candidate)
                    remaining.remove(best_candidate)
                else:
                    break
        
        return selected
    
    def create_patrol_routes(self, 
                           spawn_points: List[Tuple[int, int]],
                           route_length: int = 5) -> Dict[Tuple[int, int], List[Tuple[int, int]]]:
        """Create patrol routes for each spawn point."""
        if not self.pathfinder:
            return {}
        
        patrol_routes = {}
        
        for spawn in spawn_points:
            # Find interesting points to patrol to
            room_centers = [room.center() for room in self.arena_gen.rooms]
            
            # Find reachable points
            reachable = []
            for center in room_centers:
                path = self.pathfinder.find_path(spawn, center)
                if path and len(path) <= route_length * 5:  # Reasonable distance
                    reachable.append(center)
            
            if reachable:
                # Select diverse patrol points
                patrol_points = [spawn]
                
                while len(patrol_points) < route_length and len(reachable) > 0:
                    # Find point farthest from current patrol route
                    best_point = None
                    best_distance = -1
                    
                    for candidate in reachable:
                        min_dist = min(
                            len(self.pathfinder.find_path(candidate, p) or []) 
                            for p in patrol_points
                        )
                        if min_dist > best_distance:
                            best_distance = min_dist
                            best_point = candidate
                    
                    if best_point:
                        patrol_points.append(best_point)
                        reachable.remove(best_point)
                
                # Create circular route
                if len(patrol_points) > 1:
                    patrol_points.append(patrol_points[0])  # Return to start
                
                patrol_routes[spawn] = patrol_points
        
        return patrol_routes
    
    def analyze_chokepoints(self) -> List[Tuple[int, int]]:
        """Identify strategic chokepoints in the arena."""
        if not self.pathfinder:
            return []
        
        chokepoints = []
        entrance = self.arena_gen.get_entrance_position()
        exit_pos = self.arena_gen.get_exit_position()
        
        if not entrance or not exit_pos:
            return chokepoints
        
        # Find the main path from entrance to exit
        main_path = self.pathfinder.find_path(entrance, exit_pos)
        if not main_path:
            return chokepoints
        
        # For each point on the main path, temporarily block it and see how much
        # the path increases
        for i, point in enumerate(main_path[1:-1], 1):  # Skip start and end
            x, y = point
            original_cell = self.pathfinder.grid[y, x]
            
            # Temporarily block this cell
            self.pathfinder.grid[y, x] = CellType.WALL.value
            
            # Try to find alternative path
            alt_path = self.pathfinder.find_path(entrance, exit_pos)
            
            # Restore original cell
            self.pathfinder.grid[y, x] = original_cell
            
            if not alt_path:
                # Critical chokepoint - no alternative path
                chokepoints.append((point, "critical"))
            elif len(alt_path) > len(main_path) * 1.5:
                # Important chokepoint - significantly longer alternative
                chokepoints.append((point, "important"))
        
        return chokepoints
    
    def get_escape_routes(self, 
                         position: Tuple[int, int], 
                         threat_positions: List[Tuple[int, int]],
                         max_distance: int = 20) -> List[List[Tuple[int, int]]]:
        """Find escape routes from a position avoiding threats."""
        if not self.pathfinder:
            return []
        
        # Get all reachable positions within max_distance
        reachable = self.pathfinder.get_reachable_area(position, max_distance)
        
        # Score positions based on distance from threats
        scored_positions = []
        for pos in reachable:
            min_threat_distance = float('inf')
            for threat in threat_positions:
                path = self.pathfinder.find_path(threat, pos)
                if path:
                    min_threat_distance = min(min_threat_distance, len(path))
            
            if min_threat_distance != float('inf'):
                scored_positions.append((pos, min_threat_distance))
        
        # Sort by distance from threats (farther is better)
        scored_positions.sort(key=lambda x: x[1], reverse=True)
        
        # Generate escape routes to best positions
        escape_routes = []
        for pos, score in scored_positions[:3]:  # Top 3 escape positions
            route = self.pathfinder.find_path(position, pos)
            if route:
                # Smooth the route for better movement
                smooth_route = self.pathfinder.smooth_path(route)
                escape_routes.append(smooth_route)
        
        return escape_routes
    
    def visualize_pathfinding(self, 
                            paths: List[List[Tuple[int, int]]] = None,
                            spawn_points: List[Tuple[int, int]] = None,
                            chokepoints: List[Tuple[int, int]] = None):
        """Visualize the arena with pathfinding information."""
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        
        # Draw base arena
        colors = {
            CellType.WALL.value: 'black',
            CellType.FLOOR.value: 'lightgray',
            CellType.DOOR.value: 'brown',
            CellType.STAIRS_UP.value: 'blue',
            CellType.STAIRS_DOWN.value: 'darkblue',
            CellType.ENTRANCE.value: 'green',
            CellType.EXIT.value: 'red'
        }
        
        colored_grid = np.zeros((self.arena_gen.height, self.arena_gen.width, 3))
        for cell_type, color in colors.items():
            mask = (self.arena_gen.grid == cell_type)
            if color == 'black':
                colored_grid[mask] = [0, 0, 0]
            elif color == 'lightgray':
                colored_grid[mask] = [0.8, 0.8, 0.8]
            elif color == 'brown':
                colored_grid[mask] = [0.6, 0.3, 0.1]
            elif color == 'blue':
                colored_grid[mask] = [0, 0, 1]
            elif color == 'darkblue':
                colored_grid[mask] = [0, 0, 0.5]
            elif color == 'green':
                colored_grid[mask] = [0, 1, 0]
            elif color == 'red':
                colored_grid[mask] = [1, 0, 0]
        
        ax.imshow(colored_grid, origin='upper')
        
        # Draw paths
        if paths:
            path_colors = ['yellow', 'orange', 'purple', 'cyan', 'magenta']
            for i, path in enumerate(paths):
                if path:
                    path_color = path_colors[i % len(path_colors)]
                    path_x = [p[0] for p in path]
                    path_y = [p[1] for p in path]
                    ax.plot(path_x, path_y, color=path_color, linewidth=3, 
                           alpha=0.7, label=f'Path {i+1}')
        
        # Draw spawn points
        if spawn_points:
            for spawn in spawn_points:
                circle = patches.Circle(spawn, 1, color='lime', alpha=0.8)
                ax.add_patch(circle)
                ax.text(spawn[0], spawn[1]-2, 'SPAWN', ha='center', 
                       fontsize=8, fontweight='bold')
        
        # Draw chokepoints
        if chokepoints:
            for point_info in chokepoints:
                if isinstance(point_info, tuple) and len(point_info) == 2:
                    point, importance = point_info
                    color = 'red' if importance == 'critical' else 'orange'
                    square = patches.Rectangle((point[0]-0.5, point[1]-0.5), 1, 1, 
                                             color=color, alpha=0.8)
                    ax.add_patch(square)
        
        ax.set_title('Arena with Pathfinding Analysis')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.legend()
        plt.tight_layout()
        plt.show()

# Usage example and testing
def comprehensive_pathfinding_demo():
    """Comprehensive demonstration of the pathfinding system."""
    
    # Create arena
    arena_gen = ArenaGenerator(width=60, height=45)
    arena_gen.generate_arena(room_count=10, min_room_size=4, max_room_size=10)
    
    # Create pathfinding-enabled arena
    arena_pf = ArenaWithPathfinding(arena_gen)
    
    print("=== Arena Pathfinding Analysis ===")
    
    # Validate connectivity
    connectivity = arena_pf.validate_arena_connectivity()
    print(f"Arena Connectivity: {connectivity}")
    
    # Find optimal spawn points
    spawn_points = arena_pf.find_optimal_spawn_points(2, min_distance=25)
    print(f"Spawn points: {spawn_points}")
    
    # Create patrol routes
    patrol_routes = arena_pf.create_patrol_routes(spawn_points[:3])
    print(f"Patrol routes created for {len(patrol_routes)} spawn points")
    
    # Analyze chokepoints
    chokepoints = arena_pf.analyze_chokepoints()
    print(f"Found {len(chokepoints)} strategic chokepoints")
    
    # Test different movement types
    entrance = arena_gen.get_entrance_position()
    exit_pos = arena_gen.get_exit_position()
    
    if entrance and exit_pos:
        print("\n=== Movement Type Comparison ===")
        for movement_type in [MovementType.GROUND, MovementType.FLYING, MovementType.CLIMBING]:
            path = arena_pf.pathfinder.find_path(entrance, exit_pos, movement_type)
            if path:
                smooth_path = arena_pf.pathfinder.smooth_path(path, movement_type)
                print(f"{movement_type.value}: {len(path)} -> {len(smooth_path)} (smoothed)")
            else:
                print(f"{movement_type.value}: No path found")
    
    # Test escape routes
    if spawn_points:
        test_pos = spawn_points[0]
        threats = spawn_points[1:3] if len(spawn_points) > 2 else []
        escape_routes = arena_pf.get_escape_routes(test_pos, threats)
        print(f"\nFound {len(escape_routes)} escape routes from {test_pos}")
    
    # Visualize everything
    paths = []
    t = time.time()
    main_path = arena_pf.pathfinder.find_multiple_paths(spawn_points[0], spawn_points[1])
    for x in main_path:
        paths.append(main_path[x])



    print("Spawn to spawn time:", time.time()- t)
    print(main_path)

    
    arena_pf.visualize_pathfinding(paths, spawn_points, chokepoints)
    
    return arena_pf

# Performance optimization utilities
class PathfindingCache:
    """Advanced caching system for pathfinding results."""
    
    def __init__(self, max_size: int = 10000):
        self.cache = {}
        self.access_count = {}
        self.max_size = max_size
    
    def get(self, key) -> Optional[List[Tuple[int, int]]]:
        if key in self.cache:
            self.access_count[key] = self.access_count.get(key, 0) + 1
            return self.cache[key].copy()
        return None
    
    def put(self, key, path: List[Tuple[int, int]]):
        if len(self.cache) >= self.max_size:
            # Remove least frequently used items
            sorted_items = sorted(self.access_count.items(), key=lambda x: x[1])
            for k, _ in sorted_items[:self.max_size // 4]:
                self.cache.pop(k, None)
                self.access_count.pop(k, None)
        
        self.cache[key] = path.copy()
        self.access_count[key] = 1

class HierarchicalPathfinder:
    """Hierarchical pathfinding for very large arenas."""
    
    def __init__(self, arena_grid: np.ndarray, cluster_size: int = 10):
        self.grid = arena_grid
        self.height, self.width = arena_grid.shape
        self.cluster_size = cluster_size
        
        # Create cluster grid
        self.cluster_height = (self.height + cluster_size - 1) // cluster_size
        self.cluster_width = (self.width + cluster_size - 1) // cluster_size
        self.cluster_grid = np.zeros((self.cluster_height, self.cluster_width), dtype=bool)
        
        # Build cluster connectivity
        self._build_clusters()
        
        # Create high-level pathfinder
        self.high_level_pathfinder = Pathfinder(self.cluster_grid.astype(int))
        self.low_level_pathfinder = Pathfinder(arena_grid)
    
    def _build_clusters(self):
        """Build cluster-level connectivity graph."""
        for cy in range(self.cluster_height):
            for cx in range(self.cluster_width):
                # Check if cluster has any passable cells
                start_x = cx * self.cluster_size
                start_y = cy * self.cluster_size
                end_x = min(start_x + self.cluster_size, self.width)
                end_y = min(start_y + self.cluster_size, self.height)
                
                cluster_region = self.grid[start_y:end_y, start_x:end_x]
                passable_cells = np.sum(cluster_region != CellType.WALL.value)
                
                # Mark cluster as passable if it has enough passable cells
                if passable_cells > self.cluster_size * self.cluster_size * 0.3:
                    self.cluster_grid[cy, cx] = 1
    
    def find_hierarchical_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Find path using hierarchical approach."""
        # Convert to cluster coordinates
        start_cluster = (start[0] // self.cluster_size, start[1] // self.cluster_size)
        goal_cluster = (goal[0] // self.cluster_size, goal[1] // self.cluster_size)
        
        # If in same cluster, use direct pathfinding
        if start_cluster == goal_cluster:
            return self.low_level_pathfinder.find_path(start, goal)
        
        # Find high-level path between clusters
        high_path = self.high_level_pathfinder.find_path(start_cluster, goal_cluster)
        if not high_path:
            return None
        
        # Convert cluster path to actual waypoints and find detailed paths
        detailed_path = []
        current_pos = start
        
        for i, cluster_pos in enumerate(high_path[1:], 1):
            # Find a good waypoint in the target cluster
            cluster_x, cluster_y = cluster_pos
            center_x = cluster_x * self.cluster_size + self.cluster_size // 2
            center_y = cluster_y * self.cluster_size + self.cluster_size // 2
            
            # Clamp to grid bounds
            center_x = min(center_x, self.width - 1)
            center_y = min(center_y, self.height - 1)
            
            target_pos = (center_x, center_y) if i < len(high_path) - 1 else goal
            
            # Find detailed path to this waypoint
            segment = self.low_level_pathfinder.find_path(current_pos, target_pos)
            if not segment:
                return None
            
            detailed_path.extend(segment[:-1] if i < len(high_path) - 1 else segment)
            current_pos = target_pos
        
        return detailed_path

if __name__ == "__main__":
    # Run comprehensive demo
    try:
        arena_pf = comprehensive_pathfinding_demo()
        print("Pathfinding demo completed successfully!")
    except ImportError:
        print("Note: To run the demo, make sure your ArenaGenerator module is importable")
        print("The pathfinding system is ready to integrate with your existing code.")