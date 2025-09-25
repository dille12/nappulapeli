import pygame
from pygame.math import Vector2 as v2
class Explosion:
    def __init__(self, app, pos, firer = None, damage = 125):
        self.lifetime = 0.5
        self.app = app
        self.pos = v2(pos)
        if self.onScreen():
            self.app.playPositionalAudio(self.app.explosionSound, self.pos)
        self.app.visualEntities.append(self)
        self.firer = firer

        maxDist = (1 + (damage/125)*0.05) * 500


        self.damage = damage
        for x in self.app.pawnHelpList:
            if x.killed:
                continue
            dist = 1 - (self.pos.distance_to(x.pos)/maxDist)
            if dist > 0:

                dam = dist * self.damage
                
                x.takeDamage(dam, fromActor = self.firer, typeD = "explosion")
        
        self.im = self.app.explosion[0]


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
        i = int(2*(0.5 - self.lifetime) * len(self.app.explosion))

        self.im = self.app.explosion[i]
        
        self.lifetime -= self.app.deltaTime
        if self.lifetime <= 0:
            self.app.visualEntities.remove(self)

    def render(self):
        
        self.app.DRAWTO.blit(self.im, self.pos - v2(self.im.get_size())/2 - self.app.cameraPosDelta)