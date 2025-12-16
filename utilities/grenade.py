import pygame
from pygame.math import Vector2 as v2
import math
from typing import TYPE_CHECKING
import random
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
from utilities.explosion import Explosion
from enum import Enum
from utilities.textParticle import TextParticle
# Original enums for API compatibility
class GrenadeType(Enum):
    FLASH = 0
    FRAG = 1



class Grenade:
    def __init__(self, app: "Game", fromCell, toCell, image, owner: "Pawn", grenadeType = GrenadeType.FLASH):
        self.app = app
        self.pos = (v2(fromCell) + [0.5,0.5])  * self.app.tileSize
        self.angle = self.app.getAngleFrom(fromCell, toCell)
        diff = v2(toCell) - v2(fromCell)

        
        if not owner.currentlyAliveNade:
            owner.currentlyAliveNade = self


        self.type = grenadeType

        self.owner = owner

        if self.type == GrenadeType.FLASH:
            self.imageKillFeed = self.app.flashKillFeed
            self.name = "Flash Grenade"

            if not self.owner.itemEffects["allyProtection"]:
                self.owner.team.takeCoverFromFlash(toCell)

        elif self.type == GrenadeType.FRAG:
            self.imageKillFeed = self.app.fragKillFeed
            self.name = "Frag Grenade"
        

        self.MAXLIFE = 1.5
        self.lifetime = self.MAXLIFE

        self.vel = diff * self.app.tileSize / self.MAXLIFE

        self.app.visualEntities.append(self)
        self.image = image.copy()
        self.verticalPos = 0
        self.rotation = random.randint(0,360)
        self.rotationVel = 720
        
        self.imageR = pygame.transform.rotate(self.image, self.rotation)

    
    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))
    
    def getOwnCell(self):
        return self.v2ToTuple((self.pos + [0, self.app.tileSize/2]) / self.app.tileSize)
        

    def tick(self):
        self.pos += (self.vel * self.app.deltaTime)
        self.lifetime -= self.app.deltaTime
        self.rotation += self.rotationVel * self.app.deltaTime

        self.imageR = pygame.transform.rotate(self.image, self.rotation)

        self.verticalPos = math.sin(math.pi * (self.lifetime / self.MAXLIFE)) * 300

        if self.lifetime <= 0:
            self.detonate()


    def detonate(self):

        self.app.visualEntities.remove(self)

        if self.type == GrenadeType.FLASH:
            self.flash()
        elif self.type == GrenadeType.FRAG:
            self.explode()

        if self.isNadeFilmed():
            self.app.cameraLinger = 0.5

        if self.owner.currentlyAliveNade == self:
            self.owner.currentlyAliveNade = None

        


    def explode(self):
        Explosion(self.app, self.pos, self, 75 * self.owner.itemEffects["weaponDamage"] * self.owner.itemEffects["utilityUsage"])


    def flash(self):
        
        #
        self.app.playPositionalAudio("audio/flash.wav", self.pos)

        self.app.particle_system.create_flashbang(self.pos.x, self.pos.y)


        cell = self.getOwnCell()

        totalFlashed = 0

        for x in self.app.pawnHelpList:
            if not x.canSeeCell(cell): continue

            if self.owner.itemEffects["allyProtection"] and not self.owner.team.hostile(self.owner, x): continue

            v = self.pos - x.pos
            if v.length_squared() == 0: continue


            dist = self.app.getDistFrom(self.pos, x.pos)
            if dist > 100:
                grenade_angle = math.atan2(-v.y, v.x)
                dtheta = angle_diff(x.aimAt, grenade_angle)
                if abs(dtheta) > math.pi / 3: continue  # outside 90° FOV

            

            flashDur = 5 - 5 * (dist/1500)
            flashDur = min(5, max(flashDur, 0))

            if not self.owner.team.hostile(self.owner, x):
                flashDur /= self.owner.itemEffects["utilityUsage"]
                self.owner.stats["teamFlashes"] += 1
            else:
                self.owner.gainXP(int(flashDur)/2.5)
                self.owner.stats["flashes"] += 1

            x.flashed = flashDur
            if x.flashed > 0:
                totalFlashed += 1
                

                x.target = None
                x.flashedBy = self.owner
                self.app.playPositionalAudio("audio/flashedSound.wav", x.pos)
                x.say(random.choice([
                    "Emminä näe!",
                    "Loppu niiden valojen kanssa!",
                    "Kuka vittu näitä nakkailee",
                    "Makke?",
                    "AI VITTU",
                    "Tapoiksmä sen?",
                    f"Hyvä lineuppi {self.owner.name}",
                    f"Kiitti vitusti {self.owner.name}",
                    
                    ]))
        
        if totalFlashed:
            if self.isNadeFilmed():
                TextParticle(self.app, f"{totalFlashed} flashed!", self.pos)
            else:
                TextParticle(self.app, f"{totalFlashed} flashed!", self.owner.pos)
                

        


    def render(self):
        self.app.DRAWTO.blit(self.imageR, self.pos - self.app.cameraPosDelta - [0, self.verticalPos] - v2(self.imageR.get_size())/2)
        if self.isNadeFilmed() or True:
            i = (self.lifetime % 0.25) * 4
            for x in range(4):
                a = math.radians(x*90 + 45)

                color = (
                    [255,255,255],
                    [255,0,0],
                )[self.type.value]

                pos = self.pos - self.app.cameraPosDelta - [0, self.verticalPos] + v2((math.sin(a), math.cos(a))) * 10
                pos2 = self.pos - self.app.cameraPosDelta - [0, self.verticalPos] + v2((math.sin(a), math.cos(a))) * (10 + 40 * i)
                pygame.draw.line(self.app.DRAWTO, color, pos, pos2, width=5)
                


    def isNadeFilmed(self):
        return self.owner == self.app.cameraLock and not self.owner.target and self == self.owner.currentlyAliveNade
    

def angle_diff(a, b):
    return (b - a + math.pi) % (2 * math.pi) - math.pi