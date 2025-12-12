import pygame
from pygame.math import Vector2 as v2
import math
from levelGen.mapGen import CellType
from utilities.explosion import Explosion


class Objective:
    def __init__(self, app, cell):
        self.app = app
        self.cell = cell
        self.originalCell = cell
        self.pos = v2(self.cell) * self.app.tileSize + [self.app.tileSize/2, self.app.tileSize/2]
        
        self.image = pygame.transform.scale(self.image, [40, 40])
        self.bounce = 0
        self.app.visualEntities.append(self)

    def reset(self):
        self.cell = self.originalCell
        print("Skull out of bounds!!! reset!")

    def defaultTick(self):
        if self.app.objectiveCarriedBy:
            return
        
        if self.app.map.grid[self.cell[1], self.cell[0]] == CellType.WALL.value:
            self.reset()

        self.pos = v2(self.cell) * self.app.tileSize + [self.app.tileSize/2, self.app.tileSize/2]
        self.bounce += self.app.deltaTime 
        self.bounce = self.bounce%0.5

    def kill(self):
        self.app.visualEntities.remove(self)
        self.app.skull = None
        

    def render(self):
        if self.app.objectiveCarriedBy:
            return
        pos = self.pos - v2(self.image.get_size())/2 +[0, 10*math.sin(2*self.bounce*math.pi)] - self.app.cameraPosDelta
        self.app.DRAWTO.blit(self.image, pos)



class Skull(Objective):
    def __init__(self, app, cell):
        self.image = pygame.image.load("texture/skull.png")
        self.name = "SKULL"
        super().__init__(app, cell)

    def tick(self):
        self.defaultTick()


class Bomb(Objective):
    def __init__(self, app, cell):
        self.image = pygame.image.load("texture/bomb.png")
        self.name = "BOMB"
        self.planted = False
        self.plantedAt = None
        self.time = 5
        self.planter = None
        super().__init__(app, cell)

    def tick(self):
        if self.planted:
            self.time -= self.app.deltaTime
            if self.time <= 0:
                self.app.notify("BOMB EXPLODED!", self.planter.team.getColor())
                self.reset()

                self.app.SITES.remove(self.plantedAt)

                self.planted = False
                self.plantedAt = None
                self.time = 5

                Explosion(self.app, self.pos, self.planter, 500, doFire=True)

                

                self.app.getSites()
        
        self.defaultTick()