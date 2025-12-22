import pygame
from pygame.math import Vector2 as v2
import random
class Explosion:
    def __init__(self, app, pos, firer = None, damage = 125, doFire = False):
        self.lifetime = 0.5
        self.app = app
        self.im = self.app.explosion[0]
        self.pos = v2(pos)
        if self.app.onScreen(self.pos):
            self.app.CAMERA.vibrate(damage/10)
        self.app.playPositionalAudio(self.app.explosionSound, self.pos)
        self.app.visualEntities.append(self)
        self.weapon = firer

        self.app.roundInfo["explosions"] += 1

        s = random.choice(self.app.stains)
        pos = self.pos * self.app.RENDER_SCALE - v2(s.get_size())/2
        self.app.MAP.blit(s, pos)

        maxDist = (1 + (damage/125)*0.05) * 500

        if doFire:
            cx, cy = self.getOwnCell()
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx*dx + dy*dy <= 3*3:    # inside circle
                        nx = cx + dx
                        ny = cy + dy

                        if 0 <= ny < self.app.map.grid.shape[0] and 0 <= nx < self.app.map.grid.shape[1]:
                            if self.app.map.grid[ny, nx] == 0:
                                continue
                        else:
                            continue

                        self.app.FireSystem.addCell(nx, ny, random.uniform(3,10), self.weapon)


        self.damage = damage
        for x in self.app.pawnHelpList:
            if x.killed:
                continue
            dist = 1 - (self.pos.distance_to(x.pos)/maxDist)
            if dist > 0:
                dam = dist * self.damage
                x.takeDamage(dam, fromActor = self.weapon, typeD = "explosion")
        
        

    def getOwnCell(self):
        return self.v2ToTuple((self.pos + [0, self.app.tileSize/2]) / self.app.tileSize)

    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))



    def tick(self):

        if self.lifetime <= 0:
            self.app.visualEntities.remove(self)
            return

        i = int(2*(0.5 - self.lifetime) * (len(self.app.explosion)-1))

        i = min(i, len(self.app.explosion)-1)

        self.im = self.app.explosion[i]
        
        self.lifetime -= self.app.deltaTime
        

    def render(self):
        
        self.app.DRAWTO.blit(self.im, self.app.convertPos(self.pos, heightDiff = 1.1) - v2(self.im.get_size())/2)