import pygame
from pygame.math import Vector2 as v2
import random
class Explosion:
    def __init__(self, app, pos, firer = None, damage = 125, doFire = False):
        self.lifetime = 0.5
        self.app = app
        self.im = self.app.explosion[0]
        self.pos = v2(pos)
        if self.onScreen():
            self.app.CAMERA.vibrate(10)
        self.app.playPositionalAudio(self.app.explosionSound, self.pos)
        self.app.visualEntities.append(self)
        self.firer = firer

        maxDist = (1 + (damage/125)*0.05) * 500

        if doFire:
            cx, cy = self.getOwnCell()
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx*dx + dy*dy <= 3*3:    # inside circle
                        nx = cx + dx
                        ny = cy + dy

                        if self.app.map.grid[ny, nx] == 0:
                            continue

                        self.app.FireSystem.addCell(nx, ny, random.uniform(10,20), firer)


        self.damage = damage
        for x in self.app.pawnHelpList:
            if x.killed:
                continue
            dist = 1 - (self.pos.distance_to(x.pos)/maxDist)
            if dist > 0:
                dam = dist * self.damage
                x.takeDamage(dam, fromActor = self.firer, typeD = "explosion")
        
        

    def getOwnCell(self):
        return self.v2ToTuple((self.pos + [0, self.app.tileSize/2]) / self.app.tileSize)

    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))


    def onScreen(self):
        r = pygame.Rect(self.app.cameraPosDelta, self.app.res)
       
        onDualScreen = False

        if self.app.DUALVIEWACTIVE:
            r2 = pygame.Rect(self.app.posToTargetTo2, self.app.res)
            onDualScreen = r2.collidepoint(self.pos)
        #r2.inflate_ip(self.app.res)

        

        if not r.collidepoint(self.pos) and not onDualScreen:
            return False
        return True


    def tick(self):

        if self.lifetime <= 0:
            self.app.visualEntities.remove(self)
            return

        i = int(2*(0.5 - self.lifetime) * (len(self.app.explosion)-1))

        i = min(i, len(self.app.explosion)-1)

        self.im = self.app.explosion[i]
        
        self.lifetime -= self.app.deltaTime
        

    def render(self):
        
        self.app.DRAWTO.blit(self.im, self.pos - v2(self.im.get_size())/2 - self.app.cameraPosDelta)