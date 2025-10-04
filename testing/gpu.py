import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

class GLSurface:
    def __init__(self, size):
        self.size = size
        self.w, self.h = size
        
        # Create FBO and texture
        self.fbo = glGenFramebuffers(1)
        self.texture = glGenTextures(1)
        
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.w, self.h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.texture, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
    
    def fill(self, color):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.w, self.h)
        r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
        glClearColor(r, g, b, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
    
    def blit(self, source, dest_pos, area=None):
        # Bind target FBO
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.w, self.h)
        
        # Setup orthographic projection for this surface
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.w, self.h, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Enable blending
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        
        # Bind source texture
        glBindTexture(GL_TEXTURE_2D, source.texture)
        
        # Calculate coordinates
        x, y = dest_pos
        if area:
            sx, sy, sw, sh = area
            tx0, ty0 = sx / source.w, sy / source.h
            tx1, ty1 = (sx + sw) / source.w, (sy + sh) / source.h
            w, h = sw, sh
        else:
            tx0, ty0, tx1, ty1 = 0, 0, 1, 1
            w, h = source.w, source.h
        
        # Draw quad
        glBegin(GL_QUADS)
        glTexCoord2f(tx0, ty0); glVertex2f(x, y)
        glTexCoord2f(tx1, ty0); glVertex2f(x + w, y)
        glTexCoord2f(tx1, ty1); glVertex2f(x + w, y + h)
        glTexCoord2f(tx0, ty1); glVertex2f(x, y + h)
        glEnd()
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
    
    def get_size(self):
        return self.size


class GLScreen:
    def __init__(self, size):
        self.size = size
        self.w, self.h = size
        pygame.display.set_mode(size, pygame.DOUBLEBUF | pygame.OPENGL)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.w, self.h, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    def fill(self, color):
        r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
        glClearColor(r, g, b, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
    
    def blit(self, source, dest_pos, area=None):
        glBindTexture(GL_TEXTURE_2D, source.texture)
        
        x, y = dest_pos
        if area:
            sx, sy, sw, sh = area
            tx0, ty0 = sx / source.w, sy / source.h
            tx1, ty1 = (sx + sw) / source.w, (sy + sh) / source.h
            w, h = sw, sh
        else:
            tx0, ty0, tx1, ty1 = 0, 0, 1, 1
            w, h = source.w, source.h
        
        glBegin(GL_QUADS)
        glTexCoord2f(tx0, ty0); glVertex2f(x, y)
        glTexCoord2f(tx1, ty0); glVertex2f(x + w, y)
        glTexCoord2f(tx1, ty1); glVertex2f(x + w, y + h)
        glTexCoord2f(tx0, ty1); glVertex2f(x, y + h)
        glEnd()
    
    def get_size(self):
        return self.size


class GLDraw:
    @staticmethod
    def circle(surface, color, center, radius):
        glBindFramebuffer(GL_FRAMEBUFFER, surface.fbo)
        glViewport(0, 0, surface.w, surface.h)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, surface.w, surface.h, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_TEXTURE_2D)
        r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
        glColor3f(r, g, b)
        
        segments = 32
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(center[0], center[1])
        for i in range(segments + 1):
            angle = 2.0 * 3.14159 * i / segments
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            glVertex2f(x, y)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
    
    @staticmethod
    def line(surface, color, start, end, width=1):
        glBindFramebuffer(GL_FRAMEBUFFER, surface.fbo)
        glViewport(0, 0, surface.w, surface.h)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, surface.w, surface.h, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_TEXTURE_2D)
        r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
        glColor3f(r, g, b)
        glLineWidth(width)
        
        glBegin(GL_LINES)
        glVertex2f(start[0], start[1])
        glVertex2f(end[0], end[1])
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glBindFramebuffer(GL_FRAMEBUFFER, 0)


# Test
def main():
    pygame.init()
    res = (1920, 1080)
    clock = pygame.time.Clock()
    
    screen = GLScreen(res)
    surface1 = GLSurface(res)
    surface2 = GLSurface(res)
    
    angle = 0
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        
        # Render to surfaces
        surface1.fill((255, 0, 0))
        GLDraw.circle(surface1, (255, 255, 255), (200, 200), 50)
        
        surface2.fill((0, 0, 255))
        GLDraw.circle(surface2, (255, 255, 255), (res[0]-200, res[1]-200), 50)
        
        # Split screen composite
        angle += 0.02
        center = pygame.math.Vector2(res) / 2
        perp = pygame.math.Vector2(np.cos(angle), np.sin(angle))
        extend = max(res) * 2
        line1 = center + perp * extend
        line2 = center - perp * extend
        
        screen.fill((0, 0, 0))
        
        # Stencil-based split
        glEnable(GL_STENCIL_TEST)
        glClear(GL_STENCIL_BUFFER_BIT)
        glStencilFunc(GL_ALWAYS, 1, 0xFF)
        glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
        glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
        
        glDisable(GL_TEXTURE_2D)
        glBegin(GL_POLYGON)
        glVertex2f(line1.x, line1.y)
        glVertex2f(line2.x, line2.y)
        glVertex2f(res[0], res[1])
        glVertex2f(0, res[1])
        glEnd()
        glEnable(GL_TEXTURE_2D)
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
        
        glStencilFunc(GL_EQUAL, 1, 0xFF)
        screen.blit(surface1, (0, 0))
        
        glStencilFunc(GL_EQUAL, 0, 0xFF)
        screen.blit(surface2, (0, 0))
        
        glDisable(GL_STENCIL_TEST)
        
        # Draw divider
        glDisable(GL_TEXTURE_2D)
        glColor3f(1, 1, 1)
        glLineWidth(3)
        glBegin(GL_LINES)
        glVertex2f(line1.x, line1.y)
        glVertex2f(line2.x, line2.y)
        glEnd()
        glEnable(GL_TEXTURE_2D)
        
        pygame.display.flip()
        clock.tick(1000)
        
        print(f"FPS: {clock.get_fps():.1f}")
    
    pygame.quit()

if __name__ == "__main__":
    main()