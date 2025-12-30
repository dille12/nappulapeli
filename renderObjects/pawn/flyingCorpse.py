import random
from pygame.math import Vector2 as v2
import math
import pygame
from renderObjects.particles.blood import BloodParticle


class FlyingCorpse:
    def __init__(self, pos, pawn):
        self.pos = pos.copy()
        self.app = pawn.app
        self.pawn = pawn
        self.xvel = random.choice((-1,1)) * random.uniform(90, 270)
        self.yvel = random.choice((-1,1)) * random.uniform(40, 140)
        self.yPos = 0
        self.maxLife = random.uniform(0.5,1)
        self.lifeTime = self.maxLife

        self.targetRotation = random.choice((-1,1)) * random.randint(90, 270)

        self.rotation = 0

        self.I = 0 if self.pawn.facingRight else 1

        self.im = self.pawn.imagePawn.copy() if self.pawn.facingRight else self.pawn.imagePawnR.copy()
        self.blitIm = self.im.copy()

        self.SOUND = self.app.playPositionalAudio("audio/screams/" + random.choice(self.app.deathScreams), self.pos)

        self.app.ENTITIES.append(self)
        
        

    def tick(self):
        self.lifeTime -= self.app.deltaTime
        self.pos.x += self.xvel * self.app.deltaTime
        self.pos.y += self.yvel * self.app.deltaTime

        life = (1-(self.lifeTime/self.maxLife))

        life = max(0, min(1, life))

        self.yPos = -math.sin(life * math.pi) * (self.maxLife - 0.4)*300

        self.rotation = life * self.targetRotation
        hurtI = int(life*(len(self.pawn.hurtIm[self.I])-1))
        bloodIm = self.pawn.hurtIm[self.I][hurtI].copy()
        im = self.im.copy()
        im.blit(bloodIm, (0,0))
        self.blitIm = pygame.transform.rotate(im, self.rotation)

        if self.lifeTime <= 0:
            c = random.choice(self.pawn.corpses)
            self.app.MAP.blit(c, self.pos * self.app.RENDER_SCALE - v2(c.get_size())/2)

            self.app.playPositionalAudio(self.app.deathSounds, self.pos)

            if self.SOUND:
                self.SOUND.active = False

            for x in range(random.randint(4,8)):
                self.app.bloodSplatters.append(BloodParticle(self.pos.copy() * self.app.RENDER_SCALE, 1.2, app = self.app))

            self.app.ENTITIES.remove(self)

    def render(self):
        POS = self.app.convertPos(self.pos + [0, self.yPos]) - v2(self.blitIm.get_size())/2
        self.app.DRAWTO.blit(self.blitIm, POS)
