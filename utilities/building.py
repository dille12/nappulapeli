from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
    from pawn.teamLogic import Team
from pygame.math import Vector2 as v2
import pygame
import time
from core.drawRectPerimeter import draw_rect_perimeter

class Building:
    def __init__(self, app: "Game", name, team: "Team", texture, tile, size, buildingProgress = 0, progressToComplete = 200):
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
        self.buildingProgress = 0
        self.addProgress(buildingProgress * progressToComplete)

        self.app.ENTITIES.append(self)
        self.VIS = self.getVisibility()

    def getVisibility(self):
        cell = (int(self.tile.x, int(self.tile.y)))
        return self.app.map.get_visible_cells(cell[0], cell[1])

    def setMapGrid(self, val):
        # 0 for wall, 1 for floor
        for x in range(int(self.size.x)):
            for y in range(int(self.size.y)):
                self.app.map.grid[int(self.tile.y + y), int(self.tile.x + x)] = val

    def addProgress(self, amount):
        self.buildingProgress += amount
        if self.built():
            self.setMapGrid(0)

    def built(self):
        return self.buildingProgress >= self.progressToComplete

    def tick(self):
        pass

    def render(self):

        rect = pygame.Rect(self.tile.x*self.app.tileSize, self.tile.y*self.app.tileSize, 
                                   self.size.x * self.app.tileSize, self.size.y * self.app.tileSize)
        rect.topleft -= self.app.cameraPosDelta
        draw_rect_perimeter(self.app.DRAWTO, rect, time.time()-self.app.now, 200, 2, self.team.color)
        self.app.DRAWTO.blit(self.image, self.pos - self.app.cameraPosDelta)
