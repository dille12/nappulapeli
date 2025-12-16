import pygame
import math
import random
from enum import Enum
from typing import Tuple, List, Callable, Optional, Union


class BlendMode(Enum):
    NORMAL = pygame.BLEND_ALPHA_SDL2
    ADD = pygame.BLEND_ADD
    MULTIPLY = pygame.BLEND_MULT
    SUBTRACT = pygame.BLEND_SUB


class ParticleShape(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    LINE = "line"
    STAR = "star"
    CUSTOM = "custom"


class EasingType(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"


class Particle:
    """
    A comprehensive particle class for pygame with extensive customization options.
    
    Features:
    - Position, velocity, and acceleration
    - Color interpolation over lifetime
    - Size scaling over lifetime
    - Multiple particle shapes
    - Physics simulation (gravity, friction, etc.)
    - Blend modes
    - Custom easing functions
    - Rotation and angular velocity
    - Trail effects
    - Custom update functions
    """
    
    def __init__(self, app, x: float, y: float, **kwargs):
        """
        Initialize a particle.
        
        Args:
            app: Main application controller (must have particle_list attribute)
            x, y: Initial position
            **kwargs: Additional parameters for customization
        """
        self.app = app
        
        # Core properties
        self.x = float(x)
        self.y = float(y)
        self.start_x = self.x
        self.start_y = self.y
        
        # Velocity and acceleration
        self.vel_x = kwargs.get('vel_x', 0.0)
        self.vel_y = kwargs.get('vel_y', 0.0)
        self.accel_x = kwargs.get('accel_x', 0.0)
        self.accel_y = kwargs.get('accel_y', 0.0)
        
        # Physics
        self.gravity = kwargs.get('gravity', 0.0)
        self.friction = kwargs.get('friction', 1.0)  # 1.0 = no friction, 0.0 = full stop
        self.bounce_damping = kwargs.get('bounce_damping', 0.8)
        self.bounds = kwargs.get('bounds', None)  # (x, y, width, height) or None for no bounds
        
        # Lifetime
        self.lifetime = kwargs.get('lifetime', 60)  # frames
        self.max_lifetime = self.lifetime
        self.age = 0
        self.alive = True
        
        # Color properties
        self.start_color = kwargs.get('start_color', (255, 255, 255, 255))
        self.end_color = kwargs.get('end_color', self.start_color)
        self.current_color = list(self.start_color)
        self.color_curve = kwargs.get('color_curve', EasingType.LINEAR)
        
        # Size properties
        self.start_size = kwargs.get('start_size', 5.0)
        self.end_size = kwargs.get('end_size', self.start_size)
        self.current_size = self.start_size
        self.size_curve = kwargs.get('size_curve', EasingType.LINEAR)
        
        # Shape and rendering
        self.shape = kwargs.get('shape', ParticleShape.CIRCLE)
        self.blend_mode = kwargs.get('blend_mode', BlendMode.NORMAL)
        self.custom_surface = kwargs.get('custom_surface', None)
        
        # Rotation
        self.rotation = kwargs.get('rotation', 0.0)
        self.angular_velocity = kwargs.get('angular_velocity', 0.0)
        self.angular_acceleration = kwargs.get('angular_acceleration', 0.0)
        
        # Trail effect
        self.trail_length = kwargs.get('trail_length', 0)
        self.trail_positions = []
        self.trail_alpha_decay = kwargs.get('trail_alpha_decay', 0.8)
        
        # Custom functions
        self.custom_update_func = kwargs.get('custom_update_func', None)
        self.custom_render_func = kwargs.get('custom_render_func', None)
        
        # Oscillation/wave effects
        self.wave_amplitude_x = kwargs.get('wave_amplitude_x', 0.0)
        self.wave_amplitude_y = kwargs.get('wave_amplitude_y', 0.0)
        self.wave_frequency_x = kwargs.get('wave_frequency_x', 1.0)
        self.wave_frequency_y = kwargs.get('wave_frequency_y', 1.0)
        self.wave_phase_x = kwargs.get('wave_phase_x', 0.0)
        self.wave_phase_y = kwargs.get('wave_phase_y', 0.0)
        
        # Texture/sprite support
        self.texture = kwargs.get('texture', None)
        self.texture_scale = kwargs.get('texture_scale', 1.0)
        
        # Performance flags
        self.use_subpixel = kwargs.get('use_subpixel', True)
        
        # Add to particle list
        if hasattr(app, 'particle_list'):
            app.particle_list.append(self)
    
    def _apply_easing(self, t: float, easing_type: EasingType) -> float:
        """Apply easing function to time value (0-1)."""
        if easing_type == EasingType.LINEAR:
            return t
        elif easing_type == EasingType.EASE_IN:
            return t * t
        elif easing_type == EasingType.EASE_OUT:
            return 1 - (1 - t) * (1 - t)
        elif easing_type == EasingType.EASE_IN_OUT:
            return 3 * t * t - 2 * t * t * t
        elif easing_type == EasingType.BOUNCE:
            if t < 0.5:
                return 2 * t * t
            else:
                return 1 - 2 * (1 - t) * (1 - t)
        elif easing_type == EasingType.ELASTIC:
            if t == 0 or t == 1:
                return t
            return -(2 ** (10 * (t - 1))) * math.sin((t - 1.1) * 5 * math.pi)
        return t
    
    def _interpolate_color(self, start_color: Tuple, end_color: Tuple, t: float) -> Tuple:
        """Interpolate between two colors."""
        return tuple(
            int(start + (end - start) * t)
            for start, end in zip(start_color, end_color)
        )
    
    def _update_trail(self):
        """Update trail positions."""
        if self.trail_length > 0:
            self.trail_positions.append((self.x, self.y))
            if len(self.trail_positions) > self.trail_length:
                self.trail_positions.pop(0)
    
    def _apply_bounds(self):
        """Apply boundary constraints with bouncing."""
        if not self.bounds:
            return
        
        x, y, width, height = self.bounds
        
        # Check horizontal bounds
        if self.x < x:
            self.x = x
            self.vel_x = -self.vel_x * self.bounce_damping
        elif self.x > x + width:
            self.x = x + width
            self.vel_x = -self.vel_x * self.bounce_damping
        
        # Check vertical bounds
        if self.y < y:
            self.y = y
            self.vel_y = -self.vel_y * self.bounce_damping
        elif self.y > y + height:
            self.y = y + height
            self.vel_y = -self.vel_y * self.bounce_damping
    
    def tick(self):
        """Update particle physics and properties."""
        if not self.alive:
            return
        

        if not self.app.onScreen((self.x, self.y)):
            self.destroy()
            return

        
        # Age the particle

        MULT = 144 * self.app.deltaTime

        self.age += MULT
        if self.age >= self.lifetime:
            self.destroy()
            return
        
        # Calculate lifetime progress (0 to 1)
        t = self.age / self.max_lifetime if self.max_lifetime > 0 else 1.0
        
        # Update color
        color_t = self._apply_easing(t, self.color_curve)
        self.current_color = self._interpolate_color(self.start_color, self.end_color, color_t)
        
        # Update size
        size_t = self._apply_easing(t, self.size_curve)
        self.current_size = self.start_size + (self.end_size - self.start_size) * size_t
        
        # Apply physics
        # Gravity
        self.vel_y += self.gravity * MULT
        
        # Acceleration
        self.vel_x += self.accel_x * MULT
        self.vel_y += self.accel_y * MULT
        
        # Friction
        self.vel_x *= self.friction
        self.vel_y *= self.friction
        
        # Wave/oscillation effects
        wave_offset_x = self.wave_amplitude_x * math.sin(self.age * self.wave_frequency_x + self.wave_phase_x)
        wave_offset_y = self.wave_amplitude_y * math.sin(self.age * self.wave_frequency_y + self.wave_phase_y)
        
        # Update position
        self.x += self.vel_x + wave_offset_x
        self.y += self.vel_y + wave_offset_y
        
        # Update rotation
        self.angular_velocity += self.angular_acceleration * MULT
        self.rotation += self.angular_velocity * MULT
        
        # Apply bounds
        self._apply_bounds()
        
        # Update trail
        self._update_trail()
        
        # Custom update function
        if self.custom_update_func:
            self.custom_update_func(self)
    
    def _render_circle(self, surface: pygame.Surface):
        """Render particle as a circle."""
        if self.current_size <= 0:
            return
        
        # Apply camera offset
        camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
        screen_x = self.x - camera_offset[0]
        screen_y = self.y - camera_offset[1]
        
        pos = (int(screen_x), int(screen_y)) if not self.use_subpixel else (screen_x, screen_y)
        
        # Create a temporary surface for blending
        temp_surface = pygame.Surface((int(self.current_size * 2 + 2), int(self.current_size * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(temp_surface, self.current_color, 
                         (int(self.current_size + 1), int(self.current_size + 1)), 
                         int(self.current_size))
        
        surface.blit(temp_surface, (pos[0] - self.current_size - 1, pos[1] - self.current_size - 1), 
                    special_flags=self.blend_mode.value)
    
    def _render_square(self, surface: pygame.Surface):
        """Render particle as a square."""
        if self.current_size <= 0:
            return
        
        # Apply camera offset
        camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
        screen_x = self.x - camera_offset[0]
        screen_y = self.y - camera_offset[1]
        
        size = int(self.current_size * 2)
        rect = pygame.Rect(int(screen_x - self.current_size), int(screen_y - self.current_size), size, size)
        
        temp_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        temp_surface.fill(self.current_color)
        
        if self.rotation != 0:
            temp_surface = pygame.transform.rotate(temp_surface, math.degrees(self.rotation))
            new_rect = temp_surface.get_rect(center=(screen_x, screen_y))
            surface.blit(temp_surface, new_rect, special_flags=self.blend_mode.value)
        else:
            surface.blit(temp_surface, rect, special_flags=self.blend_mode.value)
    
    def _render_triangle(self, surface: pygame.Surface):
        """Render particle as a triangle."""
        if self.current_size <= 0:
            return
        
        # Apply camera offset
        camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
        screen_x = self.x - camera_offset[0]
        screen_y = self.y - camera_offset[1]
        
        # Calculate triangle points
        angle1 = self.rotation
        angle2 = self.rotation + 2 * math.pi / 3
        angle3 = self.rotation + 4 * math.pi / 3
        
        points = [
            (screen_x + self.current_size * math.cos(angle1),
             screen_y + self.current_size * math.sin(angle1)),
            (screen_x + self.current_size * math.cos(angle2),
             screen_y + self.current_size * math.sin(angle2)),
            (screen_x + self.current_size * math.cos(angle3),
             screen_y + self.current_size * math.sin(angle3))
        ]
        
        # Create temporary surface
        bounds = [min(p[0] for p in points), min(p[1] for p in points),
                 max(p[0] for p in points), max(p[1] for p in points)]
        size = (int(bounds[2] - bounds[0] + 2), int(bounds[3] - bounds[1] + 2))
        
        temp_surface = pygame.Surface(size, pygame.SRCALPHA)
        offset_points = [(p[0] - bounds[0], p[1] - bounds[1]) for p in points]
        pygame.draw.polygon(temp_surface, self.current_color, offset_points)
        
        surface.blit(temp_surface, (bounds[0], bounds[1]), special_flags=self.blend_mode.value)
    
    def _render_star(self, surface: pygame.Surface):
        """Render particle as a star."""
        if self.current_size <= 0:
            return
        
        # Apply camera offset
        camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
        screen_x = self.x - camera_offset[0]
        screen_y = self.y - camera_offset[1]
        
        # Calculate star points (5-pointed star)
        points = []
        for i in range(10):
            angle = self.rotation + i * math.pi / 5
            radius = self.current_size if i % 2 == 0 else self.current_size * 0.5
            points.append((
                screen_x + radius * math.cos(angle),
                screen_y + radius * math.sin(angle)
            ))
        
        # Create temporary surface
        bounds = [min(p[0] for p in points), min(p[1] for p in points),
                 max(p[0] for p in points), max(p[1] for p in points)]
        size = (int(bounds[2] - bounds[0] + 2), int(bounds[3] - bounds[1] + 2))
        
        temp_surface = pygame.Surface(size, pygame.SRCALPHA)
        offset_points = [(p[0] - bounds[0], p[1] - bounds[1]) for p in points]
        pygame.draw.polygon(temp_surface, self.current_color, offset_points)
        
        surface.blit(temp_surface, (bounds[0], bounds[1]), special_flags=self.blend_mode.value)
    
    def _render_line(self, surface: pygame.Surface):
        """Render particle as a line."""
        if self.current_size <= 0:
            return
        
        # Apply camera offset
        camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
        screen_x = self.x - camera_offset[0]
        screen_y = self.y - camera_offset[1]
        
        end_x = screen_x + self.current_size * math.cos(self.rotation)
        end_y = screen_y + self.current_size * math.sin(self.rotation)
        
        pygame.draw.line(surface, self.current_color[:3], 
                        (int(screen_x), int(screen_y)), (int(end_x), int(end_y)), 
                        max(1, int(self.current_size * 0.1)))
    
    def _render_texture(self, surface: pygame.Surface):
        """Render particle using a texture/sprite."""
        if not self.texture:
            return
        
        # Apply camera offset
        camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
        screen_x = self.x - camera_offset[0]
        screen_y = self.y - camera_offset[1]
        
        # Scale texture
        if self.texture_scale != 1.0 or self.current_size != self.start_size:
            scale_factor = (self.current_size / self.start_size) * self.texture_scale
            scaled_texture = pygame.transform.scale(self.texture, 
                (int(self.texture.get_width() * scale_factor),
                 int(self.texture.get_height() * scale_factor)))
        else:
            scaled_texture = self.texture
        
        # Rotate if needed
        if self.rotation != 0:
            scaled_texture = pygame.transform.rotate(scaled_texture, math.degrees(self.rotation))
        
        # Apply color tint
        if self.current_color != (255, 255, 255, 255):
            tinted_texture = scaled_texture.copy()
            tinted_texture.fill(self.current_color[:3], special_flags=pygame.BLEND_MULT)
            scaled_texture = tinted_texture
        
        # Blit to surface
        rect = scaled_texture.get_rect(center=(int(screen_x), int(screen_y)))
        surface.blit(scaled_texture, rect, special_flags=self.blend_mode.value)
    
    def _render_trail(self, surface: pygame.Surface):
        """Render particle trail."""
        if not self.trail_positions or len(self.trail_positions) < 2:
            return
        
        # Apply camera offset to trail positions
        camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
        
        for i, pos in enumerate(self.trail_positions[:-1]):
            alpha = int(255 * (self.trail_alpha_decay ** (len(self.trail_positions) - i - 1)))
            trail_color = (*self.current_color[:3], alpha)
            
            if i < len(self.trail_positions) - 1:
                next_pos = self.trail_positions[i + 1]
                # Apply camera offset to both positions
                screen_pos = (pos[0] - camera_offset[0], pos[1] - camera_offset[1])
                screen_next_pos = (next_pos[0] - camera_offset[0], next_pos[1] - camera_offset[1])
                pygame.draw.line(surface, trail_color, screen_pos, screen_next_pos, max(1, int(self.current_size * 0.5)))
    
    def render(self, surface: pygame.Surface):
        """Render the particle to the given surface."""
        if not self.alive or self.current_size <= 0:
            return
        
        # Render trail first (behind particle)
        self._render_trail(surface)
        
        # Custom render function takes precedence
        if self.custom_render_func:
            self.custom_render_func(self, surface)
            return
        
        # Texture rendering
        if self.texture:
            self._render_texture(surface)
            return
        
        # Custom surface rendering
        if self.shape == ParticleShape.CUSTOM and self.custom_surface:
            # Apply camera offset
            camera_offset = getattr(self.app, 'cameraPosDelta', (0, 0))
            screen_x = self.x - camera_offset[0]
            screen_y = self.y - camera_offset[1]
            
            rect = self.custom_surface.get_rect(center=(int(screen_x), int(screen_y)))
            surface.blit(self.custom_surface, rect, special_flags=self.blend_mode.value)
            return
        
        # Shape-based rendering
        if self.shape == ParticleShape.CIRCLE:
            self._render_circle(surface)
        elif self.shape == ParticleShape.SQUARE:
            self._render_square(surface)
        elif self.shape == ParticleShape.TRIANGLE:
            self._render_triangle(surface)
        elif self.shape == ParticleShape.STAR:
            self._render_star(surface)
        elif self.shape == ParticleShape.LINE:
            self._render_line(surface)
    
    def destroy(self):
        """Destroy the particle and remove it from the particle list."""
        self.alive = False
        if hasattr(self.app, 'particle_list') and self in self.app.particle_list:
            self.app.particle_list.remove(self)
    
    def set_color_gradient(self, colors: List[Tuple], curve: EasingType = EasingType.LINEAR):
        """Set a multi-color gradient over the particle's lifetime."""
        if len(colors) >= 2:
            self.start_color = colors[0]
            self.end_color = colors[-1]
            self.color_curve = curve
            # For more than 2 colors, you might want to extend this with custom interpolation
    
    def set_velocity_from_angle(self, angle: float, speed: float):
        """Set velocity based on angle and speed."""
        self.vel_x = speed * math.cos(angle)
        self.vel_y = speed * math.sin(angle)
    
    def add_force(self, force_x: float, force_y: float):
        """Add a force to the particle (affects acceleration)."""
        self.accel_x += force_x
        self.accel_y += force_y
    
    def get_distance_to(self, other_particle) -> float:
        """Get distance to another particle."""
        return math.sqrt((self.x - other_particle.x) ** 2 + (self.y - other_particle.y) ** 2)
    
    def get_angle_to(self, other_particle) -> float:
        """Get angle to another particle."""
        return math.atan2(other_particle.y - self.y, other_particle.x - self.x)


# Example usage and helper functions
class ParticleSystem:
    """A helper class to manage multiple particles."""
    
    def __init__(self, app):
        self.app = app
        if not hasattr(app, 'particle_list'):
            app.particle_list = []
    
    def create_explosion(self, x: float, y: float, count: int = 20, **kwargs):
        """Create an explosion effect."""
        particles = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            if "speed" in kwargs:
                speed = kwargs["speed"] * random.uniform(0.9, 1.1)
            else:
                speed = random.uniform(2, 8)
            
            particle_kwargs = {
                'vel_x': speed * math.cos(angle),
                'vel_y': speed * math.sin(angle),
                'lifetime': random.randint(30, 90),
                'start_color': (255, 255, 100, 255),
                'end_color': (255, 0, 0, 0),
                'start_size': random.uniform(3, 8),
                'end_size': 0,
                'gravity': 0.1,
                'friction': 0.98,
                **kwargs
            }
            
            particles.append(Particle(self.app, x, y, **particle_kwargs))
        return particles
    
    def create_fire(self, x: float, y: float, count: int = 5, **kwargs):
        """Create a fire effect."""
        particles = []
        for _ in range(count):
            particle_kwargs = {
                'vel_x': random.uniform(-1, 1),
                'vel_y': random.uniform(-3, -1),
                'lifetime': random.randint(40, 80),
                'start_color': (255, 255, 0, 255),
                'end_color': (255, 0, 0, 0),
                'start_size': random.uniform(2, 6),
                'end_size': random.uniform(8, 12),
                'blend_mode': BlendMode.ADD,
                'wave_amplitude_x': random.uniform(0.5, 2.0),
                'wave_frequency_x': random.uniform(0.1, 0.3),
                **kwargs
            }
            
            particles.append(Particle(self.app, x + random.uniform(-5, 5), y, **particle_kwargs))
        return particles
    
    def update_all(self):
        """Update all particles in the system."""
        for particle in self.app.particle_list[:]:  # Use slice to avoid modification during iteration
            particle.tick()
    
    def render_all(self, surface: pygame.Surface):
        """Render all particles in the system."""
        for particle in self.app.particle_list:
            particle.render(surface)
    
    # PRESET EFFECTS
    
    def create_level_up_indicator(self, x: float, y: float, **kwargs):
        """
        Create a level up particle effect.
        Features: Golden sparkles that rise and fade, with some larger burst particles.
        """
        particles = []

        
        
        # Main burst particles (large golden stars)
        for _ in range(30):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 6)
            
            particle_kwargs = {
                'vel_x': speed * math.cos(angle),
                'vel_y': speed * math.sin(angle) - 1,  # Slight upward bias
                'lifetime': random.randint(120, 150),
                'start_color': (255, 215, 0, 255),  # Gold
                'end_color': (255, 255, 100, 0),    # Fade to bright yellow
                'start_size': random.uniform(70, 100),
                'end_size': random.uniform(1, 3),
                'shape': ParticleShape.STAR,
                'angular_velocity': random.uniform(-0.1, 0.1),
                'gravity': -0.05,  # Slight anti-gravity for magical feel
                'friction': 0.96,
                'blend_mode': BlendMode.ADD,
                'size_curve': EasingType.EASE_OUT,
                **kwargs
            }
            particles.append(Particle(self.app, x, y, **particle_kwargs))
        
        # Sparkle particles (small rising dots)
        for _ in range(15):
            particle_kwargs = {
                'vel_x': random.uniform(-2, 2),
                'vel_y': random.uniform(-4, -1),
                'lifetime': random.randint(40, 80),
                'start_color': (255, 255, 200, 255),  # Bright yellow-white
                'end_color': (255, 215, 0, 0),        # Fade to gold
                'start_size': random.uniform(2, 4),
                'end_size': 0,
                'shape': ParticleShape.CIRCLE,
                'gravity': -0.02,
                'friction': 0.98,
                'blend_mode': BlendMode.ADD,
                'wave_amplitude_x': random.uniform(0.5, 1.5),
                'wave_frequency_x': random.uniform(0.05, 0.15),
                **kwargs
            }
            particles.append(Particle(self.app, 
                           x + random.uniform(-10, 10), 
                           y + random.uniform(-5, 5), 
                           **particle_kwargs))
        
        # Ring expansion effect
        for i in range(12):
            angle = (i / 12) * 2 * math.pi
            speed = 4
            
            particle_kwargs = {
                'vel_x': speed * math.cos(angle),
                'vel_y': speed * math.sin(angle),
                'lifetime': 30,
                'start_color': (255, 215, 0, 200),
                'end_color': (255, 215, 0, 0),
                'start_size': 1,
                'end_size': 3,
                'shape': ParticleShape.CIRCLE,
                'friction': 0.9,
                'blend_mode': BlendMode.ADD,
                **kwargs
            }
            particles.append(Particle(self.app, x, y, **particle_kwargs))
        
        return particles
    
    def create_muzzle_flash(self, x: float, y: float, angle: float = 0, **kwargs):
        """
        Create a weapon muzzle flash effect.
        Args:
            angle: Direction the weapon is facing (in radians)
        Features: Bright flash, smoke, and directional sparks.
        """
        particles = []
        
        # Main muzzle flash (bright core)
        for _ in range(3):
            particle_kwargs = {
                'vel_x': random.uniform(-0.5, 0.5),
                'vel_y': random.uniform(-0.5, 0.5),
                'lifetime': random.randint(8, 15),  # Very short-lived
                'start_color': (255, 255, 255, 255),  # Bright white
                'end_color': (255, 100, 0, 0),        # Fade to orange
                'start_size': random.uniform(8, 15),
                'end_size': random.uniform(15, 25),
                'shape': ParticleShape.CIRCLE,
                'blend_mode': BlendMode.ADD,
                'size_curve': EasingType.EASE_OUT,
                **kwargs
            }
            particles.append(Particle(self.app, x, y, **particle_kwargs))
        
        # Directional flame jets
        for _ in range(5):
            spread = random.uniform(-0.3, 0.3)  # 30 degree spread
            flash_angle = angle + spread
            speed = random.uniform(8, 15)
            
            particle_kwargs = {
                'vel_x': speed * math.cos(flash_angle),
                'vel_y': speed * math.sin(flash_angle),
                'lifetime': random.randint(12, 20),
                'start_color': (255, 200, 50, 255),   # Bright yellow
                'end_color': (200, 50, 0, 0),         # Dark red fade
                'start_size': random.uniform(4, 8),
                'end_size': 0,
                'shape': ParticleShape.CIRCLE,
                'friction': 0.85,
                'blend_mode': BlendMode.ADD,
                **kwargs
            }
            particles.append(Particle(self.app, x, y, **particle_kwargs))
        
        # Hot sparks/debris
        for _ in range(8):
            spark_angle = angle + random.uniform(-0.8, 0.8)
            speed = random.uniform(5, 12)
            
            particle_kwargs = {
                'vel_x': speed * math.cos(spark_angle),
                'vel_y': speed * math.sin(spark_angle),
                'lifetime': random.randint(15, 35),
                'start_color': (255, 255, 100, 255),  # Hot yellow
                'end_color': (100, 0, 0, 0),          # Cool to dark red
                'start_size': random.uniform(1, 3),
                'end_size': 0,
                'shape': ParticleShape.CIRCLE,
                'gravity': 0.1,
                'friction': 0.95,
                'trail_length': 3,
                'trail_alpha_decay': 0.7,
                'blend_mode': BlendMode.ADD,
                **kwargs
            }
            particles.append(Particle(self.app, x, y, **particle_kwargs))
        
        # Smoke particles
        for _ in range(4):
            smoke_angle = angle + random.uniform(-0.5, 0.5)
            speed = random.uniform(2, 5)
            
            particle_kwargs = {
                'vel_x': speed * math.cos(smoke_angle),
                'vel_y': speed * math.sin(smoke_angle),
                'lifetime': random.randint(40, 70),
                'start_color': (100, 100, 100, 150),  # Gray smoke
                'end_color': (50, 50, 50, 0),         # Fade to transparent
                'start_size': random.uniform(3, 6),
                'end_size': random.uniform(12, 20),   # Expands as it cools
                'shape': ParticleShape.CIRCLE,
                'friction': 0.98,
                'wave_amplitude_x': random.uniform(0.3, 0.8),
                'wave_amplitude_y': random.uniform(0.3, 0.8),
                'wave_frequency_x': random.uniform(0.02, 0.05),
                'wave_frequency_y': random.uniform(0.02, 0.05),
                **kwargs
            }
            particles.append(Particle(self.app, 
                           x + random.uniform(-2, 2), 
                           y + random.uniform(-2, 2), 
                           **particle_kwargs))
        
        return particles
    
    def create_healing_particles(self, x: float, y: float, **kwargs):
        """
        Create healing/restoration particle effect.
        Features: Gentle green/blue rising particles with soft glow and cross shapes.
        """
        particles = []
        
        # Main healing orbs (soft green glowing circles)
        for _ in range(10):
            particle_kwargs = {
                'vel_x': random.uniform(-1, 1),
                'vel_y': random.uniform(-3, -1),
                'lifetime': random.randint(60, 100),
                'start_color': (50, 255, 100, 200),   # Soft green
                'end_color': (100, 255, 200, 0),      # Fade to cyan
                'start_size': random.uniform(30, 60),
                'end_size': random.uniform(1, 3),
                'shape': ParticleShape.CIRCLE,
                'gravity': -0.03,  # Gentle upward float
                'friction': 0.99,
                'blend_mode': BlendMode.ADD,
                'wave_amplitude_x': random.uniform(0.8, 1.5),
                'wave_amplitude_y': random.uniform(0.3, 0.8),
                'wave_frequency_x': random.uniform(0.03, 0.08),
                'wave_frequency_y': random.uniform(0.02, 0.06),
                'color_curve': EasingType.EASE_OUT,
                **kwargs
            }
            particles.append(Particle(self.app, 
                           x + random.uniform(-15, 15), 
                           y + random.uniform(-5, 5), 
                           **particle_kwargs))
        
        # Healing crosses/plus signs
        for _ in range(6):
            particle_kwargs = {
                'vel_x': random.uniform(-0.5, 0.5),
                'vel_y': random.uniform(-2, -0.5),
                'lifetime': random.randint(50, 80),
                'start_color': (255, 255, 255, 255),  # Pure white
                'end_color': (50, 255, 100, 0),       # Fade to green
                'start_size': random.uniform(40, 70),
                'end_size': random.uniform(1, 2),
                'shape': ParticleShape.STAR,  # We'll use star as a cross-like shape
                'angular_velocity': random.uniform(-0.05, 0.05),
                'gravity': -0.02,
                'friction': 0.98,
                'blend_mode': BlendMode.ADD,
                **kwargs
            }
            particles.append(Particle(self.app, 
                           x + random.uniform(-8, 8), 
                           y + random.uniform(-3, 3), 
                           **particle_kwargs))
        
        # Sparkle particles (tiny bright dots)
        for _ in range(15):
            particle_kwargs = {
                'vel_x': random.uniform(-1.5, 1.5),
                'vel_y': random.uniform(-4, -1),
                'lifetime': random.randint(30, 60),
                'start_color': (200, 255, 255, 255),  # Bright cyan-white
                'end_color': (50, 255, 150, 0),       # Fade to healing green
                'start_size': random.uniform(10, 15),
                'end_size': 0,
                'shape': ParticleShape.CIRCLE,
                'gravity': -0.04,
                'friction': 0.97,
                'blend_mode': BlendMode.ADD,
                'wave_amplitude_x': random.uniform(0.2, 0.6),
                'wave_frequency_x': random.uniform(0.08, 0.15),
                **kwargs
            }
            particles.append(Particle(self.app, 
                           x + random.uniform(-20, 20), 
                           y + random.uniform(-8, 8), 
                           **particle_kwargs))
        
        # Gentle energy waves (expanding rings)
        for i in range(3):
            delay_offset = i * 10  # Stagger the waves
            particle_kwargs = {
                'vel_x': 0,
                'vel_y': 0,
                'lifetime': 40 + delay_offset,
                'start_color': (100, 255, 150, 100) if i == 0 else (100, 255, 150, 0),
                'end_color': (100, 255, 150, 0),
                'start_size': 5 if i == 0 else 15 + i * 10,
                'end_size': 25 + i * 15,
                'shape': ParticleShape.CIRCLE,
                'blend_mode': BlendMode.ADD,
                'size_curve': EasingType.EASE_OUT,
                **kwargs
            }
            particles.append(Particle(self.app, x, y, **particle_kwargs))
        
        return particles
    
    def create_flashbang(self, x: float, y: float, **kwargs):
        particles = []

        # 1) Core white flash (screen-burn)
        for _ in range(2):
            particles.append(Particle(
                self.app, x, y,
                vel_x=random.uniform(-0.5, 0.5),
                vel_y=random.uniform(-0.5, 0.5),
                lifetime=random.randint(20, 25),
                start_color=(255, 255, 255, 255),
                end_color=(255, 255, 255, 0),
                start_size=random.uniform(20, 30),
                end_size=random.uniform(100, 200),
                shape=ParticleShape.CIRCLE,
                blend_mode=BlendMode.ADD,
                size_curve=EasingType.EASE_OUT,
                **kwargs
            ))

        # 2) Radial shock rays
        for i in range(24):
            angle = (i / 24) * 2 * math.pi
            speed = random.uniform(100, 180)
            particles.append(Particle(
                self.app, x, y,
                vel_x=math.cos(angle) * speed,
                vel_y=math.sin(angle) * speed,
                lifetime=random.randint(30, 40),
                start_color=(255, 255, 255, 220),
                end_color=(255, 255, 255, 0),
                start_size=random.uniform(40, 70),
                end_size=0,
                shape=ParticleShape.LINE,
                rotation=angle,
                blend_mode=BlendMode.ADD,
                friction=0.85,
                **kwargs
            ))

        # 3) Hot sparks
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(6, 14)
            particles.append(Particle(
                self.app, x, y,
                vel_x=math.cos(angle) * speed,
                vel_y=math.sin(angle) * speed,
                lifetime=random.randint(20, 40),
                start_color=(255, 220, 120, 255),
                end_color=(120, 60, 20, 0),
                start_size=random.uniform(2, 4),
                end_size=0,
                shape=ParticleShape.CIRCLE,
                gravity=0.2,
                friction=0.92,
                trail_length=3,
                trail_alpha_decay=0.6,
                blend_mode=BlendMode.ADD,
                **kwargs
            ))



        return particles
    
    def create_wall_sparks(self, x: float, y: float, normal_angle: float = None, count: int = 12, **kwargs):
        particles = []

        if normal_angle is None:
            base_angle = random.uniform(0, 2 * math.pi)
        else:
            base_angle = normal_angle + math.pi  # sparks go away from wall

        for _ in range(count):
            angle = base_angle + random.uniform(-0.1, 0.1)
            speed = random.uniform(10, 20)

            particles.append(Particle(
                self.app,
                x, y,
                vel_x=math.cos(angle) * speed,
                vel_y=math.sin(angle) * speed,
                lifetime=random.randint(80, 120),
                start_color=(255, 200, 120, 255),
                end_color=(80, 40, 20, 0),
                start_size=random.uniform(3, 4),
                end_size=0,
                shape=ParticleShape.CIRCLE,
                gravity=0.1,
                friction=0.88,
                blend_mode=BlendMode.ADD,
                use_subpixel=False,
                **kwargs
            ))

        return particles

