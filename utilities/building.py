from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
from pygame.math import Vector2 as v2
import pygame
class Building:
    def __init__(self, app: "Game", name, team, texture, tile, size, buildingProgress = 0, progressToComplete = 200):
        self.app = app
        self.name = name
        self.team = team
        #self.texture = texture
        self.tile = v2(tile)
        self.pos = self.app.tileSize * self.tile
        self.size = v2(size)
        self.pSize = self.app.tileSize * self.size

        self.image = pygame.image.load(texture).convert_alpha()
        self.image = pygame.transform.scale(self.image, self.pSize)

        self.progressToComplete = progressToComplete
        self.buildingProgress = buildingProgress * progressToComplete

        self.app.ENTITIES.append(self)

    def addProgress(self, amount):
        self.buildingProgress += amount

    def built(self):
        return self.buildingProgress >= self.progressToComplete

    def tick(self):
        pass

    def render(self):
        self.app.DRAWTO.blit(self.image, self.pos - self.app.cameraPosDelta)
