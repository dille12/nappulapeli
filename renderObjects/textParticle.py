
import pygame
from pygame.math import Vector2 as v2
from typing import TYPE_CHECKING
import random
if TYPE_CHECKING:
    from main import Game
class TextParticle:
    def __init__(self, app: "Game", text, pos):
        self.app = app
        self.text = self.app.font.render(text, True, [255,255,255])
        self.pos = v2(pos) - v2(self.text.get_size())/2
        self.maxLife = 0.5
        self.lifetime = self.maxLife
        self.app.visualEntities.append(self)

    def tick(self):
        self.lifetime -= self.app.deltaTime
        if self.lifetime <= 0:
            self.app.visualEntities.remove(self)
        
        alpha = 255 - int((self.maxLife-self.lifetime)**2)
        self.pos.y -= self.app.deltaTime * 30
        self.text.set_alpha(alpha)

    def render(self):
        self.app.DRAWTO.blit(self.text, self.pos - self.app.cameraPosDelta)