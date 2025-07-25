import pygame
from pygame.math import Vector2 as v2
import math
from mapGen import CellType
class Skull:
    def __init__(self, app, cell):
        self.app = app
        self.cell = cell
        self.originalCell = cell
        self.pos = v2(self.cell) * 70 + [35, 35]
        self.image = pygame.image.load("texture/skull.png")
        self.image = pygame.transform.scale(self.image, [40, 40])
        self.bounce = 0
        self.app.visualEntities.append(self)

    def tick(self):
        if self.app.objectiveCarriedBy:
            return
        
        if self.app.map.grid[self.cell[1], self.cell[0]] == CellType.WALL.value:
            self.cell = self.originalCell
            print("Skull out of bounds!!! reset!")

        self.pos = v2(self.cell) * 70 + [35, 35]
        self.bounce += self.app.deltaTime 
        self.bounce = self.bounce%0.5
        

    def render(self):
        if self.app.objectiveCarriedBy:
            return
        pos = self.pos - v2(self.image.get_size())/2 +[0, 10*math.sin(2*self.bounce*math.pi)] - self.app.cameraPosDelta
        self.app.DRAWTO.blit(self.image, pos)
