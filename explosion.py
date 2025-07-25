
from pygame.math import Vector2 as v2
class Explosion:
    def __init__(self, app, pos, firer = None):
        self.lifetime = 0.5
        self.app = app
        self.pos = v2(pos)
        self.app.playSound(self.app.explosionSound)
        self.app.visualEntities.append(self)
        self.firer = firer
        for x in self.app.pawnHelpList:
            if x.killed:
                continue
            dist = 1 - (self.pos.distance_to(x.pos)/500)
            if dist > 0:

                dam = dist * 125 * firer.itemEffects["weaponDamage"]
                x.takeDamage(dam, fromActor = self.firer, typeD = "explosion")
        
        self.im = self.app.explosion[0]


    def tick(self):
        i = int(2*(0.5 - self.lifetime) * len(self.app.explosion))

        self.im = self.app.explosion[i]
        
        self.lifetime -= self.app.deltaTime
        if self.lifetime <= 0:
            self.app.visualEntities.remove(self)

    def render(self):
        
        self.app.DRAWTO.blit(self.im, self.pos - v2(self.im.get_size())/2 - self.app.cameraPosDelta)