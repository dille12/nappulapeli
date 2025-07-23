import pygame
import math
from pygame.math import Vector2 as v2
import random
from numba import njit
from blood import BloodParticle
from mapGen import CellType
from explosion import Explosion
@njit
def line_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return False
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        return 0 <= ua <= 1 and 0 <= ub <= 1

@njit
def line_intersects_rect(x1, y1, x2, y2, rx, ry, rw, rh):
    # rectangle edges
    left   = (rx, ry, rx, ry + rh)
    right  = (rx + rw, ry, rx + rw, ry + rh)
    top    = (rx, ry, rx + rw, ry)
    bottom = (rx, ry + rh, rx + rw, ry + rh)

    return (
        line_intersect(x1, y1, x2, y2, *left) or
        line_intersect(x1, y1, x2, y2, *right) or
        line_intersect(x1, y1, x2, y2, *top) or
        line_intersect(x1, y1, x2, y2, *bottom)
    )


class Bullet:
    def __init__(self, owner, pos, angle, spread = 0.1, damage = 10, rocket = False, type = "normal"):
        self.owner = owner
        self.app = owner.app
        self.pos = pos
        self.angle = angle + random.uniform(-spread, spread)
        self.speed = 4000
        self.damage = damage
        self.vel = v2(math.cos(self.angle), math.sin(self.angle))
        self.pastPos = []
        self.app.ENTITIES.append(self)
        self.lifetime = 2
        self.b = self.app.bulletSprite.copy()
        self.b = pygame.transform.rotate(self.b, -math.degrees(self.angle))
        self.rocket = rocket
        self.type = type
        self.pos += self.vel * 20

    def getOwnCell(self):
        return self.v2ToTuple((self.pos + [0, 35]) / 70)
    
    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))

    def tick(self):
        self.pastPos.append(self.pos.copy())
        if len(self.pastPos) > 3:
            self.pastPos.pop(0)
        self.pos += self.vel * self.app.deltaTime * self.speed
        nextPos = self.pos + self.vel * self.app.deltaTime * self.speed
        
        line = [list(self.pos), list(nextPos)]
        x,y = self.getOwnCell()

        try:

            if self.app.map.grid[y, x] == CellType.WALL.value:
                self.app.ENTITIES.remove(self)

                if self.rocket:
                    Explosion(self.app, self.pos, firer = self.owner)

                return
        except:
            if self in self.app.ENTITIES:
                self.app.ENTITIES.remove(self)
            return
        
        for x in self.app.pawnHelpList:
            if x == self:
                continue
            if x.team == self.owner.team:
                continue

            if x.killed:
                continue

            collides = line_intersects_rect(
                line[0][0], line[0][1],
                line[1][0], line[1][1],
                x.hitBox.x, x.hitBox.y, x.hitBox.width, x.hitBox.height
            )
            if collides:
                if self in self.app.ENTITIES:
                    self.app.ENTITIES.remove(self)

                self.app.particle_list.append(BloodParticle(x.pos.copy(), 0.7, app = self.app))


                damage = self.damage 

                

                if self.rocket:
                    Explosion(self.app, self.pos, firer = self.owner)
                else:
                    x.takeDamage(damage, fromActor = self.owner, typeD = self.type)

                for x in self.app.hitSounds:
                    x.stop()
                random.choice(self.app.hitSounds).play()
                return




        

        self.lifetime -= self.app.deltaTime
        if self.lifetime < 0:
            if self in self.app.ENTITIES:
                self.app.ENTITIES.remove(self)


    def render(self):
        self.app.DRAWTO.blit(self.b, self.pos - v2(self.b.get_size())/2 - self.app.cameraPosDelta)