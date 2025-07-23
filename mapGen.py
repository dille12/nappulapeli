import numpy as np
import random
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import matplotlib.pyplot as plt
import pygame



class CellType(Enum):
    WALL = 0
    FLOOR = 1
    DOOR = 2
    STAIRS_UP = 3
    STAIRS_DOWN = 4
    ENTRANCE = 5
    EXIT = 6

class Room:
    def __init__(self, x, y, width, height, room_type):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.room_type = room_type
        self.area = self.width * self.height

    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

class ArenaGenerator:
    def __init__(self, width: int = 80, height: int = 60, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=int)
        self.rooms: List[Room] = []
        
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)



    def to_pygame_surface(self, cell_size: int = 16, colors: Optional[Dict[int, Tuple[int, int, int]]] = None) -> pygame.Surface:
        """
        Convert the generated arena to a pygame Surface.
        
        Args:
            cell_size: Size of each cell in pixels (default 16x16)
            colors: Optional custom color mapping for cell types
        
        Returns:
            pygame.Surface: Rendered arena surface
        """
        # Default color scheme
        if colors is None:
            colors = {
                CellType.WALL.value: (40, 40, 40),           # Dark gray
                CellType.FLOOR.value: (200, 200, 200),       # Light gray
                CellType.DOOR.value: (139, 69, 19),          # Brown
                CellType.STAIRS_UP.value: (70, 130, 180),    # Steel blue
                CellType.STAIRS_DOWN.value: (25, 25, 112),   # Midnight blue
                CellType.ENTRANCE.value: (0, 255, 0),        # Green
                CellType.EXIT.value: (255, 0, 0)             # Red
            }
        
        # Create surface
        surface_width = self.width * cell_size
        surface_height = self.height * cell_size
        surface = pygame.Surface((surface_width, surface_height))
        
        # Fill surface
        for y in range(self.height):
            for x in range(self.width):
                cell_type = self.grid[y, x]
                color = colors.get(cell_type, (128, 0, 128))  # Magenta for unknown types
                
                # Calculate pixel coordinates
                pixel_x = x * cell_size
                pixel_y = y * cell_size
                
                # Draw cell
                pygame.draw.rect(surface, color, 
                            (pixel_x, pixel_y, cell_size, cell_size))
        
        return surface

    def to_pygame_surface_textured(self, 
                                wall_texture: Optional[pygame.Surface] = None,
                                floor_texture: Optional[pygame.Surface] = None,
                                cell_size: int = 16) -> pygame.Surface:
        """
        Convert the generated arena to a pygame Surface with optional textures.
        
        Args:
            wall_texture: Optional texture for walls
            floor_texture: Optional texture for floors
            cell_size: Size of each cell in pixels
        
        Returns:
            pygame.Surface: Rendered arena surface with textures
        """
        # Create surface
        surface_width = self.width * cell_size
        surface_height = self.height * cell_size
        surface = pygame.Surface((surface_width, surface_height))
        
        # Scale textures if provided
        if wall_texture:
            wall_texture = pygame.transform.scale(wall_texture, (cell_size, cell_size))
        if floor_texture:
            floor_texture = pygame.transform.scale(floor_texture, (cell_size, cell_size))
        
        # Default colors if no textures
        default_colors = {
            CellType.WALL.value: (40, 40, 40),
            CellType.FLOOR.value: (200, 200, 200),
            CellType.DOOR.value: (139, 69, 19),
            CellType.STAIRS_UP.value: (70, 130, 180),
            CellType.STAIRS_DOWN.value: (25, 25, 112),
            CellType.ENTRANCE.value: (0, 255, 0),
            CellType.EXIT.value: (255, 0, 0)
        }
        
        # Fill surface
        for y in range(self.height):
            for x in range(self.width):
                cell_type = self.grid[y, x]
                pixel_x = x * cell_size
                pixel_y = y * cell_size
                
                # Use texture or color based on cell type
                if cell_type == CellType.WALL.value and wall_texture:
                    surface.blit(wall_texture, (pixel_x, pixel_y))
                elif cell_type == CellType.FLOOR.value and floor_texture:
                    surface.blit(floor_texture, (pixel_x, pixel_y))
                else:
                    # Fall back to solid colors
                    color = default_colors.get(cell_type, (128, 0, 128))
                    pygame.draw.rect(surface, color, 
                                (pixel_x, pixel_y, cell_size, cell_size))
        
        return surface

    def get_spawn_points(self) -> List[Tuple[int, int]]:
        """
        Get potential spawn points (floor cells away from walls).
        
        Returns:
            List of (x, y) coordinates suitable for spawning entities
        """
        spawn_points = []
        
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.grid[y, x] == CellType.FLOOR.value:
                    # Check if it's not adjacent to walls (optional for safer spawning)
                    safe = True
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if self.grid[y + dy, x + dx] == CellType.WALL.value:
                                safe = False
                                break
                        if not safe:
                            break
                    
                    if safe:
                        spawn_points.append((x, y))
        
        return spawn_points

    def get_entrance_position(self) -> Optional[Tuple[int, int]]:
        """Get the entrance position if it exists."""
        entrance_pos = np.where(self.grid == CellType.ENTRANCE.value)
        if len(entrance_pos[0]) > 0:
            return (entrance_pos[1][0], entrance_pos[0][0])  # (x, y)
        return None

    def get_exit_position(self) -> Optional[Tuple[int, int]]:
        """Get the exit position if it exists."""
        exit_pos = np.where(self.grid == CellType.EXIT.value)
        if len(exit_pos[0]) > 0:
            return (exit_pos[1][0], exit_pos[0][0])  # (x, y)
        return None
    
    def generate_arena(self, 
                      room_count: int = 8,
                      min_room_size: int = 4,
                      max_room_size: int = 12,
                      corridor_width: int = 2) -> np.ndarray:
        """Generate a complete arena with rooms and corridors."""
        
        # Step 1: Fill with walls
        self.grid.fill(CellType.WALL.value)
        
        # Step 2: Generate rooms using architectural principles
        self._generate_rooms(room_count, min_room_size, max_room_size)
        
        # Step 3: Create corridors between rooms
        self._create_corridors(corridor_width)
        
        # Step 4: Add doors and special features
        self._add_doors()
        self._add_special_features()
        
        # Step 5: Smooth and refine
        # self._smooth_arena()
        
        return self.grid.copy()
    
    def _generate_rooms(self, count: int, min_size: int, max_size: int):
        """Generate rooms with size and placement constraints."""
        room_types = ['main_hall', 'chamber', 'storage', 'passage', 'alcove']
        attempts = 0
        max_attempts = count * 10
        
        while len(self.rooms) < count and attempts < max_attempts:
            attempts += 1
            
            # Generate room dimensions based on type
            room_type = random.choice(room_types)
            width, height = self._get_room_dimensions(room_type, min_size, max_size)
            
            # Find placement using architectural principles
            x, y = self._find_room_placement(width, height)
            
            if x is not None and y is not None:
                room = Room(x, y, width, height, room_type)
                self.rooms.append(room)
                self._carve_room(room)
    
    def _get_room_dimensions(self, room_type: str, min_size: int, max_size: int) -> Tuple[int, int]:
        """Generate room dimensions based on architectural principles."""
        if room_type == 'main_hall':
            # Large, roughly square rooms
            size = random.randint(max_size - 2, max_size)
            aspect_ratio = random.uniform(0.8, 1.2)
            return int(size), int(size * aspect_ratio)
        elif room_type == 'passage':
            # Long, narrow corridors
            length = random.randint(max_size, max_size + 4)
            width = random.randint(min_size // 2, min_size)
            return (length, width) if random.random() < 0.5 else (width, length)
        elif room_type == 'alcove':
            # Small, square rooms
            size = random.randint(min_size, min_size + 2)
            return size, size
        else:
            # Regular chambers with varied aspect ratios
            width = random.randint(min_size, max_size)
            aspect_ratio = random.uniform(0.6, 1.6)
            height = max(min_size, int(width * aspect_ratio))
            return width, min(height, max_size)
    
    def _find_room_placement(self, width: int, height: int) -> Tuple[Optional[int], Optional[int]]:
        """Find suitable placement for a room using spacing constraints."""
        attempts = 0
        max_attempts = 100
        
        while attempts < max_attempts:
            attempts += 1
            
            # Leave border space
            x = random.randint(2, self.width - width - 2)
            y = random.randint(2, self.height - height - 2)
            
            # Check for overlaps with existing rooms (with minimum spacing)
            valid = True
            for room in self.rooms:
                # Minimum 3-cell spacing between rooms
                if (x < room.x + room.width + 3 and x + width + 3 > room.x and
                    y < room.y + room.height + 3 and y + height + 3 > room.y):
                    valid = False
                    break
            
            if valid:
                return x, y
        
        return None, None
    
    def _carve_room(self, room: Room):
        """Carve out a room in the grid."""
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                if 0 <= y < self.height and 0 <= x < self.width:
                    self.grid[y, x] = CellType.FLOOR.value
    
    def _create_corridors(self, width: int):
        """Create corridors connecting rooms using MST-like approach."""
        if len(self.rooms) < 2:
            return
        
        # Create minimum spanning tree of room connections
        connections = self._generate_room_connections()
        
        for room1, room2 in connections:
            self._carve_corridor(room1, room2, width)
    
    def _generate_room_connections(self) -> List[Tuple[Room, Room]]:
        """Generate connections between rooms using MST algorithm."""
        if len(self.rooms) <= 1:
            return []
        
        # Simple MST using Prim's algorithm
        connected = {self.rooms[0]}
        connections = []
        
        while len(connected) < len(self.rooms):
            min_dist = float('inf')
            best_pair = None
            
            for room1 in connected:
                for room2 in self.rooms:
                    if room2 not in connected:
                        dist = self._room_distance(room1, room2)
                        if dist < min_dist:
                            min_dist = dist
                            best_pair = (room1, room2)
            
            if best_pair:
                connections.append(best_pair)
                connected.add(best_pair[1])
        
        # Add some extra connections for interesting layouts
        extra_connections = min(2, len(self.rooms) // 3)
        for _ in range(extra_connections):
            room1 = random.choice(self.rooms)
            room2 = random.choice(self.rooms)
            if room1 != room2 and (room1, room2) not in connections and (room2, room1) not in connections:
                connections.append((room1, room2))
        
        return connections
    
    def _room_distance(self, room1: Room, room2: Room) -> float:
        """Calculate distance between room centers."""
        x1, y1 = room1.center()
        x2, y2 = room2.center()
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def _carve_corridor(self, room1: Room, room2: Room, width: int):
        """Carve an L-shaped corridor between two rooms."""
        x1, y1 = room1.center()
        x2, y2 = room2.center()
        
        # Create L-shaped path
        if random.random() < 0.5:
            # Horizontal first, then vertical
            self._carve_line(x1, y1, x2, y1, width)
            self._carve_line(x2, y1, x2, y2, width)
        else:
            # Vertical first, then horizontal
            self._carve_line(x1, y1, x1, y2, width)
            self._carve_line(x1, y2, x2, y2, width)
    
    def _carve_line(self, x1: int, y1: int, x2: int, y2: int, width: int):
        """Carve a line of given width between two points."""
        # Bresenham-like line algorithm with width
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while True:
            # Carve with width
            for i in range(-(width//2), width//2 + 1):
                for j in range(-(width//2), width//2 + 1):
                    nx, ny = x + i, y + j
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        self.grid[ny, nx] = CellType.FLOOR.value
            
            if x == x2 and y == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def _add_doors(self):
        """Add doors between rooms and corridors."""
        for room in self.rooms:
            # Find walls adjacent to corridors
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    if self.grid[y, x] == CellType.FLOOR.value:
                        # Check adjacent cells for potential door placement
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = x + dx, y + dy
                            if (0 <= nx < self.width and 0 <= ny < self.height and
                                self.grid[ny, nx] == CellType.WALL.value):
                                # Check if there's a corridor beyond this wall
                                nnx, nny = nx + dx, ny + dy
                                if (0 <= nnx < self.width and 0 <= nny < self.height and
                                    self.grid[nny, nnx] == CellType.FLOOR.value and
                                    not any(r.contains(nnx, nny) for r in self.rooms)):
                                    if random.random() < 0.3:  # 30% chance for door
                                        self.grid[ny, nx] = CellType.DOOR.value
    
    def _add_special_features(self):
        """Add entrance, exit, and other special features."""
        if not self.rooms:
            return
        
        # Add entrance to the largest room
        largest_room = max(self.rooms, key=lambda r: r.area)
        cx, cy = largest_room.center()
        self.grid[cy, cx] = CellType.ENTRANCE.value
        
        # Add exit to a room far from entrance
        max_dist = 0
        exit_room = largest_room
        for room in self.rooms:
            if room != largest_room:
                dist = self._room_distance(largest_room, room)
                if dist > max_dist:
                    max_dist = dist
                    exit_room = room
        
        if exit_room != largest_room:
            cx, cy = exit_room.center()
            self.grid[cy, cx] = CellType.EXIT.value
        
        # Occasionally add stairs
        if len(self.rooms) > 4 and random.random() < 0.4:
            stairs_room = random.choice([r for r in self.rooms if r not in [largest_room, exit_room]])
            cx, cy = stairs_room.center()
            self.grid[cy, cx] = CellType.STAIRS_UP.value if random.random() < 0.5 else CellType.STAIRS_DOWN.value
    
    def _smooth_arena(self):
        """Apply smoothing to make the arena more natural."""
        # Remove isolated walls
        new_grid = self.grid.copy()
        
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.grid[y, x] == CellType.WALL.value:
                    # Count neighboring floors
                    floor_neighbors = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if (self.grid[y + dy, x + dx] in 
                                [CellType.FLOOR.value, CellType.DOOR.value]):
                                floor_neighbors += 1
                    
                    # Remove walls with too many floor neighbors
                    if floor_neighbors >= 5:
                        new_grid[y, x] = CellType.FLOOR.value
        
        self.grid = new_grid


    def get_visible_cells(self, from_x: int, from_y: int, max_range: int = 10) -> List[Tuple[int, int]]:
        """
        Get all cells visible from a given position using raycasting.
        
        Args:
            from_x, from_y: Starting position
            max_range: Maximum vision distance
            
        Returns:
            List of (x, y) coordinates that are visible
        """
        visible = []
        
        # Cast rays in all directions
        for angle in range(0, 360, 2):  # Every 2 degrees for performance
            rad = np.radians(angle)
            dx = np.cos(rad)
            dy = np.sin(rad)
            
            # Cast ray up to max_range
            for step in range(1, max_range + 1):
                x = int(from_x + dx * step)
                y = int(from_y + dy * step)
                
                # Check bounds
                if not (0 <= x < self.width and 0 <= y < self.height):
                    break
                    
                
                
                # Stop if we hit a wall
                if self.grid[y, x] == CellType.WALL.value:
                    break

                # Add to visible list
                if (x, y) not in visible:
                    visible.append((x, y))
        
        return visible

    def can_see(self, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
        """
        Check if there's a clear line of sight between two points using Bresenham's line algorithm.
        
        Args:
            from_x, from_y: Starting position
            to_x, to_y: Target position
            
        Returns:
            True if line of sight is clear, False if blocked
        """
        # Bresenham's line algorithm
        dx = abs(to_x - from_x)
        dy = abs(to_y - from_y)
        sx = 1 if from_x < to_x else -1
        sy = 1 if from_y < to_y else -1
        err = dx - dy
        
        x, y = from_x, from_y
        
        while True:
            # Check if current cell blocks vision (but not the target cell)
            if (x != to_x or y != to_y) and self.grid[y, x] == CellType.WALL.value:
                return False
                
            # Reached target
            if x == to_x and y == to_y:
                return True
                
            # Check bounds
            if not (0 <= x < self.width and 0 <= y < self.height):
                return False
            
            # Move to next cell
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def visualize(self, save_path: Optional[str] = None):
        """Visualize the generated arena."""
        # Color map for different cell types
        colors = {
            CellType.WALL.value: 'black',
            CellType.FLOOR.value: 'lightgray',
            CellType.DOOR.value: 'brown',
            CellType.STAIRS_UP.value: 'blue',
            CellType.STAIRS_DOWN.value: 'darkblue',
            CellType.ENTRANCE.value: 'green',
            CellType.EXIT.value: 'red'
        }
        
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Create colored grid
        colored_grid = np.zeros((self.height, self.width, 3))
        for cell_type, color in colors.items():
            mask = (self.grid == cell_type)
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
        ax.set_title('Generated 2D Arena')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=colors[ct.value], label=ct.name.replace('_', ' ').title()) 
                        for ct in CellType if np.any(self.grid == ct.value)]
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.show()

# Example usage and testing
def generate_sample_arenas():
    """Generate and display sample arenas with different parameters."""
    
    # Small dungeon
    print("Generating small dungeon...")
    gen1 = ArenaGenerator(width=40, height=30, seed=42)
    arena1 = gen1.generate_arena(room_count=5, min_room_size=3, max_room_size=8)
    gen1.visualize()
    
    # Medium complex arena
    print("Generating medium arena...")
    gen2 = ArenaGenerator(width=60, height=45, seed=123)
    arena2 = gen2.generate_arena(room_count=8, min_room_size=4, max_room_size=10)
    gen2.visualize()
    
    # Large complex arena
    print("Generating large arena...")
    gen3 = ArenaGenerator(width=80, height=60, seed=456)
    arena3 = gen3.generate_arena(room_count=20, min_room_size=4, max_room_size=14)
    gen3.visualize()
    
    return arena1, arena2, arena3

if __name__ == "__main__":
    # Generate sample arenas
    arenas = generate_sample_arenas()
    
    # Print statistics
    for i, arena in enumerate(arenas, 1):
        floor_cells = np.sum(arena == CellType.FLOOR.value)
        total_cells = arena.size
        density = floor_cells / total_cells
        print(f"Arena {i}: {floor_cells}/{total_cells} floor cells ({density:.2%} density)")