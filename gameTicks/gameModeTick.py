import pygame
from pygame.math import Vector2 as v2
import random
import math
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game

class GlitchGamemodeDisplay:
    def __init__(self, app):
        self.app = app
        self.screen = app.screen
        self.font = app.font
        self.font_large = app.fontLarge
        
        # Screen dimensions
        self.width = self.screen.get_width()
        self.height = self.screen.get_height()
        
        # Animation state
        self.start_time = time.time()
        self.current_gamemode = "BATTLE ROYALE"
        self.subtitle = "Preparing Battle Arena"
        
        # Colors
        self.bg_color = (10, 10, 10)
        self.cyan = (255, 165, 0)
        self.magenta = (255, 0, 64)
        self.white = (255, 255, 255)
        self.gray = (136, 136, 136)
        
        # Grid animation
        self.grid_offset = 0
        self.grid_size = 50
        
        # Scan line
        self.scan_y = 0
        self.scan_speed = 2
        
        # Particles
        self.particles = []
        self.create_particles()
        
        # Glitch effects
        self.glitch_offset_x = 0
        self.glitch_offset_y = 0
        self.glitch_timer = 0
        
        # Progress bar
        self.progress = 0
        self.progress_speed = 0.5
        
        # Animation phases
        self.phase_timers = {
            'label': 0.5,
            'title': 1.0,
            'subtitle': 2.5,
            'progress': 3.0
        }
        
    def create_particles(self):
        """Create floating particles"""
        for _ in range(20):
            particle = {
                'x': random.randint(0, self.width),
                'y': random.randint(self.height, self.height + 200),
                'speed': random.uniform(1, 3),
                'size': random.randint(1, 3),
                'opacity': random.randint(100, 255)
            }
            self.particles.append(particle)
    
    def update_particles(self):
        """Update particle positions"""
        for particle in self.particles:
            particle['y'] -= particle['speed']
            if particle['y'] < -50:
                particle['y'] = self.height + 50
                particle['x'] = random.randint(0, self.width)
    
    def draw_grid_background(self):
        """Draw animated grid background"""
        # Update grid offset
        self.grid_offset += 1
        if self.grid_offset >= self.grid_size:
            self.grid_offset = 0
        
        # Draw vertical lines
        for x in range(-self.grid_size + self.grid_offset, self.width + self.grid_size, self.grid_size):
            pygame.draw.line(self.screen, (*self.cyan, 25), (x, 0), (x, self.height), 1)
        
        # Draw horizontal lines
        for y in range(-self.grid_size + self.grid_offset, self.height + self.grid_size, self.grid_size):
            pygame.draw.line(self.screen, (*self.cyan, 25), (0, y), (self.width, y), 1)
    
    def draw_scan_line(self):
        """Draw animated scan line"""
        self.scan_y += self.scan_speed
        if self.scan_y > self.height + 20:
            self.scan_y = -20
        
        # Create gradient effect for scan line
        for i in range(5):
            alpha = max(0, 180 - i * 40)
            color = (*self.cyan, alpha)
            y_pos = self.scan_y + i
            if 0 <= y_pos <= self.height:
                pygame.draw.line(self.screen, color, (0, y_pos), (self.width, y_pos), 1)
    
    def draw_particles(self):
        """Draw floating particles"""
        self.update_particles()
        for particle in self.particles:
            # Create surface with per-pixel alpha
            particle_surf = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, (*self.cyan, particle['opacity']), 
                             (particle['size'], particle['size']), particle['size'])
            self.screen.blit(particle_surf, (particle['x'], particle['y']))
    
    def get_glitch_offset(self):
        """Calculate random glitch offset"""
        current_time = time.time()
        self.glitch_timer += 1
        
        if self.glitch_timer % 60 < 5:  # Glitch for 5 frames every 60 frames
            self.glitch_offset_x = random.randint(-3, 3)
            self.glitch_offset_y = random.randint(-2, 2)
        else:
            self.glitch_offset_x = 0
            self.glitch_offset_y = 0
        
        return self.glitch_offset_x, self.glitch_offset_y
    
    def draw_glitch_text(self, text, x, y, font, base_color):
        """Draw text with glitch effect"""
        glitch_x, glitch_y = self.get_glitch_offset()
        
        # Draw glitch layers (background)
        if glitch_x != 0 or glitch_y != 0:
            # Red/magenta layer
            magenta_surface = font.render(text, True, self.magenta)
            magenta_rect = magenta_surface.get_rect(center=(x + glitch_x - 2, y + glitch_y + 1))
            self.screen.blit(magenta_surface, magenta_rect)
            
            # Cyan layer
            cyan_surface = font.render(text, True, self.cyan)
            cyan_rect = cyan_surface.get_rect(center=(x + glitch_x + 2, y + glitch_y - 1))
            self.screen.blit(cyan_surface, cyan_rect)
        
        # Draw main text
        main_surface = font.render(text, True, base_color)
        main_rect = main_surface.get_rect(center=(x, y))
        self.screen.blit(main_surface, main_rect)
    
    def draw_corner_brackets(self):
        """Draw corner UI brackets"""
        current_time = time.time() - self.start_time
        if current_time < self.phase_timers['title']:
            return
        
        bracket_size = 60
        bracket_thickness = 3
        margin = 50
        
        # Top-left bracket
        pygame.draw.line(self.screen, self.cyan, 
                        (margin, margin), (margin + bracket_size, margin), bracket_thickness)
        pygame.draw.line(self.screen, self.cyan, 
                        (margin, margin), (margin, margin + bracket_size), bracket_thickness)
        
        # Bottom-right bracket
        pygame.draw.line(self.screen, self.cyan, 
                        (self.width - margin, self.height - margin), 
                        (self.width - margin - bracket_size, self.height - margin), bracket_thickness)
        pygame.draw.line(self.screen, self.cyan, 
                        (self.width - margin, self.height - margin), 
                        (self.width - margin, self.height - margin - bracket_size), bracket_thickness)
    
    def draw_progress_bar(self):
        """Draw animated progress bar"""
        current_time = time.time() - self.start_time
        if current_time < self.phase_timers['progress']:
            return
        
        # Update progress
        if self.progress < 100:
            self.progress += self.progress_speed
        
        bar_width = 300
        bar_height = 4
        bar_x = self.width // 2 - bar_width // 2
        bar_y = self.height // 2 + 120
        
        # Background
        pygame.draw.rect(self.screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))
        
        # Progress fill
        fill_width = int((self.progress / 100) * bar_width)
        if fill_width > 0:
            # Create gradient effect
            for i in range(fill_width):
                ratio = i / bar_width
                r = int(255 * (1 - ratio) + 0 * ratio)
                g = int(0 * (1 - ratio) + 255 * ratio)
                b = int(64 * (1 - ratio) + 255 * ratio)
                pygame.draw.line(self.screen, (r, g, b), 
                               (bar_x + i, bar_y), (bar_x + i, bar_y + bar_height))
    
    def draw_fade_in_text(self, text, x, y, font, color, delay):
        """Draw text that fades in after delay"""
        current_time = time.time() - self.start_time
        if current_time < delay:
            return
        
        # Calculate fade-in alpha
        fade_time = current_time - delay
        alpha = min(255, int(fade_time * 255))
        
        # Create surface with alpha
        text_surface = font.render(text, True, color)
        fade_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
        fade_surface.set_alpha(alpha)
        fade_surface.blit(text_surface, (0, 0))
        
        text_rect = fade_surface.get_rect(center=(x, y))
        self.screen.blit(fade_surface, text_rect)
    
    def set_gamemode(self, gamemode):
        """Change the current gamemode"""
        self.current_gamemode = gamemode.upper()
        
        # Update subtitle based on gamemode
        subtitles = {
            'ODDBALL': 'Pidä kalloa 100 sekuntia ja voita',
            'TEAM DEATHMATCH': 'Tapa sata vihua ja voita',
            'TURF WARS': 'Valtaa huoneet ja voita',
            'FINAL SHOWDOWN': "Tapa ilkeä bossi ja voita",
            "KING OF THE HILL": "Valtaa huone ja voita",
            "DETONATION": "Pelaa ceeässää ja voita"
        }
        
        self.subtitle = subtitles.get(self.current_gamemode, 'Initializing Game')
        
        # Reset animations
        self.start_time = time.time()
        self.progress = 0
    
    def draw(self):
        """Main draw function"""
        current_time = time.time() - self.start_time
        
        # Fill background
        #self.screen.fill(self.bg_color)
        
        # Draw background elements
        #self.draw_grid_background()
        self.draw_particles()
        self.draw_scan_line()
        self.draw_corner_brackets()
        
        # Draw text elements with timing
        center_x = self.width // 2
        center_y = self.height // 2
        
        # "Initialize Gamemode" label
        self.draw_fade_in_text(f"ROUND: {self.app.round + 1}", center_x, center_y - 100, 
                              self.font_large, self.cyan, self.phase_timers['label'])
        
        # Main gamemode title with glitch effect
        if current_time >= self.phase_timers['title']:
            self.draw_glitch_text(self.current_gamemode, center_x, center_y, 
                                 self.font_large, self.white)
        
        # Subtitle
        self.draw_fade_in_text(self.subtitle, center_x, center_y + 80, 
                              self.font, self.gray, self.phase_timers['subtitle'])
        
        # Progress bar
        self.draw_progress_bar()

# Example usage:
# In your main game loop, you would create and use the display like this:
"""
# Initialize the display
gamemode_display = GlitchGamemodeDisplay(app)

# In your game loop:
gamemode_display.draw()

# To change gamemode:
gamemode_display.set_gamemode("TEAM DEATHMATCH")
"""

def loadingTick(self: "Game"):
    self.screen.fill((0,0,0))
    self.screen.blit(self.loadingSplash, self.originalRes/2 - v2(self.loadingSplash.get_size())/2)
    self.gamemode_display.draw()