
import random
import pygame
from pygame.math import Vector2 as v2
from typing import TYPE_CHECKING
import math
if TYPE_CHECKING:
    from pawn.pawn import Pawn
    from main import Game
class Enemy:
    def __init__(self, app: "Game"):
        self.app = app
        if random.randint(0, 1) == 0:
            self.pos = v2(random.randint(0, 1920), random.choice([-200, self.app.res[1] + 200]))
        else:
            self.pos = v2(random.choice([-200, self.app.res[0] + 200]), random.randint(0, 1080))
        #self.pos = v2([500,500])
        self.vel = v2([0,0])
        self.acc = 100
        self.rect = pygame.Rect(1,1,50,80)
        self.rect.center = self.pos

        self.target = None
        self.deltaPos = self.pos.copy()
        

    def tick(self):

        if not self.target and self.app.pawnHelpList:
            target = random.choice(self.app.pawnHelpList)

            self.target = target
            

        if self.target:
            angle = math.radians(v2([0,0]).angle_to(self.target.pos - self.pos))
            self.vel.x += math.cos(angle) * self.acc * self.app.deltaTime
            self.vel.y += math.sin(angle) * self.acc * self.app.deltaTime
            self.pos += self.vel * self.app.deltaTime

        friction = 0.99
        self.vel *= friction ** (self.app.deltaTime * 60)
        self.rect.center = self.pos
        pygame.draw.rect(self.app.screen, [255,0,0], self.rect, 1)

        