import pygame
from pygame.math import Vector2 as v2
import math
from levelGen.mapGen import CellType
from renderObjects.explosion import Explosion


class Objective:
    def __init__(self, app, cell):
        self.app = app
        self.cell = cell
        self.originalCell = cell
        self.pos = v2(self.cell) * self.app.tileSize + [self.app.tileSize/2, self.app.tileSize/2]
        
        self.image = pygame.transform.scale(self.image, [40, 40])

        self.image = pygame.transform.scale_by(self.image, self.app.RENDER_SCALE)

        self.bounce = 0
        self.app.visualEntities.append(self)

    def reset(self):
        self.cell = self.originalCell
        print("Skull out of bounds!!! reset!")

    def getPos(self):
        return v2(self.cell) * self.app.tileSize + [self.app.tileSize/2, self.app.tileSize/2]

    def defaultTick(self):
        if self.app.objectiveCarriedBy:
            return
        
        if self.app.map.grid[self.cell[1], self.cell[0]] == CellType.WALL.value:
            self.reset()

        self.pos = self.getPos()
        self.bounce += self.app.deltaTime 
        self.bounce = self.bounce%0.5

    def kill(self):
        self.app.visualEntities.remove(self)
        self.app.skull = None

    def getCurrentCell(self):
        if self.app.objectiveCarriedBy:
            return self.app.objectiveCarriedBy.getOwnCell()
        else:
            return self.cell
        

    def render(self):
        if self.app.objectiveCarriedBy:
            return
        pos = self.app.convertPos(self.pos + [0, 10*math.sin(2*self.bounce*math.pi)]) - v2(self.image.get_size())/2
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
        self.time = 40
        self.planter = None
        self.defusedBy = None
        

        self.defuseMaxTime = 7.5
        self.defuseTimer = self.defuseMaxTime

        self.bombTickI = 0

        super().__init__(app, cell)

    def tick(self):

        if not self.defusedBy:
            self.defuseTimer = self.defuseMaxTime

        if self.planted:
            self.time -= self.app.deltaTime

            self.bombTickI += self.app.deltaTime
            interval = 0.05 + 0.95 * self.time/40
            interval = max(0.05, interval)
            if self.bombTickI >= interval:
                self.bombTickI = 0
                self.app.playPositionalAudio("audio/bombTick.wav", self.getPos())

            if self.defusedBy:
                self.defuseTimer -= self.app.deltaTime
                if self.defuseTimer <= 0:
                    self.app.notify("BOMB DEFUSED!", self.defusedBy.team.getColor())
                    self.planted = False
                    self.plantedAt = None
                    self.time = 40
                    self.defusedBy = None
                    self.defuseTimer = self.defuseMaxTime
                    self.reset()
                

            if self.time <= 0 and not self.defusedBy:
                self.app.notify("BOMB EXPLODED!", self.planter.team.getColor())

                self.app.playPositionalAudio("audio/bombExplode.wav", self.getPos())

                self.reset()

                self.app.SITES.remove(self.plantedAt)

                self.planted = False
                self.plantedAt = None
                self.time = 40

                self.defusedBy = None
                self.defuseTimer = self.defuseMaxTime

                Explosion(self.app, self.pos, None, 500, doFire=True)                

                self.app.getSites()

                for x in self.app.getActualPawns():
                    x.pickWalkingTarget()
        
        self.defaultTick()