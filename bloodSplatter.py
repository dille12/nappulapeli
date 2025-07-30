from pygame.math import Vector2 as v2
import math
import random
import pygame
class BloodSplatter:
    def __init__(self, app, pos ,angle):
        self.app = app
        self.pos = pos
        self.a = angle + random.uniform(-0.25, 0.25)
        self.color = [125 + random.randint(-25,25), 0, 4]
        self.vel = v2(math.cos(self.a), math.sin(self.a)) * random.uniform(3,7) * 144
        self.lifetime = random.uniform(0.3, 0.7)
        self.lastTicks = 2
        self.lastPos = None
        self.size = random.uniform(3,7)
        self.app.visualEntities.append(self)

    def tick(self):
        
        if self.lifetime < 0:
            self.lastTicks -= 1
            self.lastPos = self.pos.copy()
            if self.lastTicks <= 0:
                self.app.visualEntities.remove(self)
        else:
            self.lifetime -= self.app.deltaTime

        self.pos += self.vel * self.app.deltaTime


    def render(self):
        if self.lifetime >= 0:
            r = pygame.Rect(self.pos[0]-1 - self.app.cameraPosDelta[0], self.pos[1]-1 - self.app.cameraPosDelta[1], self.size,self.size)
            pygame.draw.rect(self.app.DRAWTO, self.color, r)

        elif self.lastPos:
            pygame.draw.line(self.app.MAP, self.color, self.pos, self.lastPos, width=int(self.size/2))