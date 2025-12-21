import numpy as np
import random
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import matplotlib.pyplot as plt
import pygame
import numba as nb
from collections import deque
@nb.njit
def get_visible_mask(grid, from_x, from_y, max_range, cos_table, sin_table):
    height, width = grid.shape
    visible = np.zeros((height, width), dtype=np.uint8)

    for i in range(len(cos_table)):
        dx = cos_table[i]
        dy = sin_table[i]

        for step in range(1, max_range + 1):
            x = int(from_x + dx * step)
            y = int(from_y + dy * step)

            if x < 0 or x >= width or y < 0 or y >= height:
                break

            if grid[y, x] == 0:  # assume WALL=1
                break

            visible[y, x] = 1

    return visible

@nb.njit
def march_ray_all_cells(grid, from_x, from_y, max_range, dx, dy):
    height, width = grid.shape
    visited = np.zeros((max_range, 2), dtype=np.int32)
    count = 0

    for step in range(1, max_range + 1):
        x = int(from_x + dx * step)
        y = int(from_y + dy * step)

        if x < 0 or x >= width or y < 0 or y >= height:
            break

        if grid[y, x] == 0:  # WALL=0
            break

        visited[count, 0] = x
        visited[count, 1] = y
        count += 1

    return visited[:count]  # slice to only return the visited cells

@nb.njit
def march_ray(grid, from_x, from_y, max_range, dx, dy):
    height, width = grid.shape
    last_y = from_y
    last_x = from_x

    for step in range(1, max_range + 1):
        x = int(from_x + dx * step)
        y = int(from_y + dy * step)

        if x < 0 or x >= width or y < 0 or y >= height:
            break

        if grid[y, x] == 0:  # WALL=0
            break

        last_x = x
        last_y = y

    return last_y, last_x



class CellType(Enum):
    WALL = 0
    FLOOR = 1
    CTVIS = 2
    TVIS = 3
    VIS = 4


OBSTACLE_SHAPES = [
    np.array([[1,0],
              [1,0],
              [1,1]], dtype=np.uint8),

    np.array([[0,1,0],
              [1,1,1],
              [0,1,0]], dtype=np.uint8),

    np.array([[1,1]], dtype=np.uint8),

]
def rotate_shape(shape, k):
    return np.rot90(shape, k)

def can_place(grid, shape, ox, oy):
    h, w = shape.shape
    H, W = grid.shape

    for sy in range(h):
        for sx in range(w):
            if shape[sy, sx] == 0:
                continue

            gx, gy = ox + sx, oy + sy

            # Bounds
            if not (0 <= gx < W and 0 <= gy < H):
                return False

            # Overlap with wall
            if grid[gy, gx] == 0:
                return False

            # Touch check
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ng_x = gx + dx
                    ng_y = gy + dy
                    if 0 <= ng_x < W and 0 <= ng_y < H:
                        if grid[ng_y, ng_x] == 0:
                            return False

    return True


def place_obstacle(room, max_tries=5):
    grid = room.arena.grid

    # choose shape + rotation
    shape = random.choice(OBSTACLE_SHAPES)
    shape = rotate_shape(shape, random.randint(0, 3))

    h, w = shape.shape
    x0, y0 = room.x, room.y
    x1, y1 = x0 + room.width, y0 + room.height

    for _ in range(max_tries):
        ox = random.randint(x0, x1 - w)
        oy = random.randint(y0, y1 - h)

        if can_place(grid, shape, ox, oy):
            # apply: write 0 into shape positions
            for sy in range(h):
                for sx in range(w):
                    if shape[sy, sx] == 1:
                        grid[oy + sy, ox + sx] = 0
            return True

    return False



class Room:
    def __init__(self, arena: "ArenaGenerator", x, y, width, height, room_type):
        self.x = x
        self.y = y
        self.arena = arena
        self.width = width
        self.height = height
        self.room_type = room_type
        self.area = self.width * self.height
        self.turfWarTeam = None
        self.pawnsPresent = []
        self.connections = []
        self.occupyI = 5
        self.kills = 0
        self.CENTER = (self.x + self.width // 2, self.y + self.height // 2)
        self.texture = random.choice(self.arena.app.roomTextures)
        self.defensivePositions = []
        
        
    def getCenter(self):
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        grid = self.arena.grid
        H, W = grid.shape

        # starting point may be non-walkable
        q = deque([(cx, cy)])
        seen = {(cx, cy)}

        # 8 directions to avoid missing diagonally adjacent free cells
        dirs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]

        # room bounds
        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.width, y0 + self.height

        while q:
            x, y = q.popleft()

            if x0 <= x < x1 and y0 <= y < y1:
                if 0 <= x < W and 0 <= y < H and grid[y, x] > 0:
                    return (x, y)

            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))

        # fallback (should never happen in valid rooms)
        return (cx, cy)

    def center(self):
        if self.arena.grid[self.CENTER[1], self.CENTER[0]] == CellType.WALL:
            self.CENTER = self.getCenter()
        return self.CENTER
        

    
    def randomCell(self) -> Tuple[int, int]:
        while True:
            x,y = (random.randint(self.x, self.x + self.width - 1), random.randint(self.y, self.y + self.height - 1))
            if self.arena.grid[y,x]:
                return (x,y)
    
    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height
    
    def addConnection(self, room):
        if room not in self.connections:
            self.connections.append(room)
        if self not in room.connections:
            room.connections.append(self)

    def allCells(self):
        cells = []
        gx = self.arena.grid
        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.width, y0 + self.height

        for y in range(y0, y1):
            for x in range(x0, x1):
                if gx[y, x]:    # walkable cell
                    cells.append((x, y))

        return cells

class ArenaGenerator:
    def __init__(self, app, width: int = 80, height: int = 60, seed: Optional[int] = None):
        self.app = app
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=int)
        self.rooms: List[Room] = []
        


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
                CellType.WALL.value: (0,0,0),           # Dark gray
                CellType.FLOOR.value: (55,55,55),       # Light gray
                CellType.CTVIS.value: [15, 26, 51],          # Brown
                CellType.TVIS.value: [51,42,13],    # Steel blue
                CellType.VIS.value: (100,100,100),   # Midnight blue

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
    

    def to_pygame_surface_textured2(self, cell_size=16):
        # Create surface
        surface_width = self.width * cell_size
        surface_height = self.height * cell_size
        surface = pygame.Surface((surface_width, surface_height))

        for y in range(self.height):
            for x in range(self.width):
                cell_type = self.grid[y, x]
                if cell_type == CellType.WALL.value:
                    continue


                pixel_x = x * cell_size
                pixel_y = y * cell_size

                drawn = False
                for r in self.rooms:
                    if r.contains(x,y):
                        surface.blit(r.texture, (pixel_x, pixel_y))
                        drawn = True
                        break
                
                if not drawn:
                    surface.blit(random.choice(self.app.concretes), (pixel_x, pixel_y))

        
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
        #if wall_texture:
        #    wall_texture = pygame.transform.scale(wall_texture, (cell_size, cell_size))
        #if floor_texture:
        #    floor_texture = pygame.transform.scale(floor_texture, (cell_size, cell_size))
        
        # Default colors if no textures
        default_colors = {
                CellType.WALL.value: (0,0,0),           # Dark gray
                CellType.FLOOR.value: (55,55,55),       # Light gray
                CellType.CTVIS.value: [15, 26, 51],          # Brown
                CellType.TVIS.value: [51,42,13],    # Steel blue
                CellType.VIS.value: (100,100,100),   # Midnight blue

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
                elif cell_type != CellType.WALL.value and floor_texture:
                    surface.blit(random.choice(floor_texture), (pixel_x, pixel_y))
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
    
    def get_room(self, cell):
        for x in self.rooms:
            if x.contains(cell[0], cell[1]):
                return x
        return None


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

        for x in self.rooms:
            for i in range(random.randint(0,5)):
                place_obstacle(x, max_tries=3)

        self._get_room_defensive_positions()

        
        # Step 4: Add doors and special features
        #self._add_doors()
        #self._add_special_features()
        
        # Step 5: Smooth and refine
        # self._smooth_arena()
        
        return self.grid.copy()
    
    def _get_room_defensive_positions(self):
        grid = self.grid
        H, W = grid.shape

        for room in self.rooms:
            positions = set()

            x0, y0 = room.x, room.y
            x1, y1 = x0 + room.width, y0 + room.height

            for y in range(y0, y1):
                for x in range(x0, x1):
                    if grid[y, x] == CellType.WALL:
                        continue

                    for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
                        nx, ny = x + dx, y + dy

                        if not (0 <= nx < W and 0 <= ny < H):
                            continue

                        if room.contains(nx, ny):
                            continue

                        if grid[ny, nx] > 0:
                            positions.add((nx, ny))

            room.defensivePositions = list(positions)

    
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
                room = Room(self, x, y, width, height, room_type)
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
        
        for r1, r2 in connections:
            r1.addConnection(r2)
        
        for room1, room2 in connections:
            self._carve_corridor(room1, room2, random.randint(1, width))
    
    def _generate_room_connections(self) -> List[Tuple[Room, Room]]:
        """Generate connections between rooms using MST algorithm with minimum 2 connections per room."""
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
        
        # Count connections per room
        connection_count = {room: 0 for room in self.rooms}
        for room1, room2 in connections:
            connection_count[room1] += 1
            connection_count[room2] += 1
        
        # Ensure each room has at least 2 connections
        rooms_needing_connections = [room for room, count in connection_count.items() if count < 2]
        
        for room in rooms_needing_connections:
            # Find potential connections (rooms not already connected to this room)
            already_connected = set()
            for r1, r2 in connections:
                if r1 == room:
                    already_connected.add(r2)
                elif r2 == room:
                    already_connected.add(r1)
            
            # Get available rooms to connect to, sorted by distance
            available_rooms = [r for r in self.rooms if r != room and r not in already_connected]
            if available_rooms:
                # Sort by distance and connect to closest available room
                available_rooms.sort(key=lambda r: self._room_distance(room, r))
                
                # Add connections until this room has at least 2
                connections_needed = 2 - connection_count[room]
                for i in range(min(connections_needed, len(available_rooms))):
                    new_connection = (room, available_rooms[i])
                    # Check if this connection already exists in reverse
                    if (available_rooms[i], room) not in connections:
                        connections.append(new_connection)
                        connection_count[room] += 1
                        connection_count[available_rooms[i]] += 1
        
        # Add some extra connections for interesting layouts (optional)
        extra_connections = min(0, len(self.rooms) // 4)
        for _ in range(extra_connections):
            room1 = random.choice(self.rooms)
            room2 = random.choice(self.rooms)
            if (room1 != room2 and 
                (room1, room2) not in connections and 
                (room2, room1) not in connections):
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


    def marchRay(self, from_x: int, from_y: int, angle: float, max_range: int = 20):
        dx = np.cos(angle)
        dy = np.sin(angle)

        y, x = march_ray(self.grid, from_x, from_y, max_range, dx, dy)
        return x, y
    
    def marchRayAll(self, from_x: int, from_y: int, angle: float, max_range: int = 20):
        dx = np.cos(np.radians(angle))
        dy = np.sin(np.radians(angle))

        cells = march_ray_all_cells(self.grid, from_x, from_y, max_range, dx, dy)
        return cells

    def get_visible_cells(self, from_x: int, from_y: int, max_range: int = 10):
        angles = np.arange(0, 360, 2)
        cos_table = np.cos(np.radians(angles))
        sin_table = np.sin(np.radians(angles))

        mask = get_visible_mask(self.grid, from_x, from_y, max_range, cos_table, sin_table)
        return [(xy[1], xy[0]) for xy in np.argwhere(mask == 1)]

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
    
    return gen1

if __name__ == "__main__":
    # Generate sample arenas
    arena = generate_sample_arenas()
    

    import time
    t = time.time()
    for i in range(5000):
        p = (random.randint(0,40), random.randint(0,30))
        #print(arena.get_visible_cells(p[0], p[1]))
    print(time.time()- t)
