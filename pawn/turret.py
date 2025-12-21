
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
    from pawn.teamLogic import Team


import pygame
from pygame.math import Vector2 as v2
from pawn.getStat import getStat
from utilities.explosion import Explosion
import random, math
from utilities.bullet import Bullet

def angle_diff(a, b):
    diff = (b - a + 180) % 360 - 180
    return diff

class Turret(getStat):
    def __init__(self, app: "Game", cell, team: "Team", owner=None):
        self.app = app
        self.cell = cell
        self.isPawn = False

        super().__init__()
        self.pos = (v2(cell) + [0.5,0.5]) * self.app.tileSize
        self.team = team
        self.leg_base = self.app.turretLeg.copy()
        self.head_base = self.app.turretHead.copy()
        self.leg = self.leg_base.copy()
        self.head = self.head_base.copy()

        headRGB = self.app.getTurretHead(self.team.getColor())
        self.head.blit(headRGB, (0,0))

        self.rescale()

        team.add(self)
        self.onCameraTime = 0
        self.NPC = True
        self.target = None
        self.grenadePos = None
        self.originalTeam = self.team.i
        self.GENERATING = False
        

        self.name = "TURRET"

        self.BOSS = False
        self.enslaved = False
        self.killed = False
        self.aimAt = 0
        self.respawnI = 0
        self.health = 125
        self.currentlyAliveNade = None
        self.rotation = 0
        self.rotationVel = 0
        self.flashed = 0
        self.loseTargetI = 1
        self.spread = 0.05
        if owner:
            self.owner = owner
        else:
            self.owner = self.team.getPawns()[0]

        self.imageKillFeed = self.app.turretKillIcon
        self.barrelOffset = v2(35,0)

        self.BPS = 5
        self.fireTick = 0

        self.hitBox = pygame.Rect(self.pos[0], self.pos[1], 100, 100)
        self.app.ENTITIES.append(self)
        self.app.pawnHelpList.append(self)

    def getTurretRange(self):
        return 1500
    
    def shoot(self):
        if self.loseTargetI <= 0:
            if self.target:
                self.team.addNadePos(self.target.getOwnCell(), "aggr")  #.marchCells(-self.target.aimAt + math.pi, 5)

            self.target = None
            self.loseTargetI = 1

        if not self.target:
            self.searchEnemies()
        if not self.target:
            return
        
        if self.target.killed:
            self.target = None
            return
        
        dist = self.pos.distance_to(self.target.pos)
        if dist > self.getTurretRange():
            self.loseTargetI -= self.app.deltaTime
            self.searchEnemies()
            return
        
        if not self.sees(self.target):
            self.loseTargetI -= self.app.deltaTime
            self.searchEnemies()
            return
        
        self.facingRight = self.target.pos[0] <= self.pos[0]
        if dist < 250:
            return

        self.turretFire()
        self.loseTargetI = 1

    def pointingAtTarget(self):
        if self.target:
            r = math.degrees(self.app.getAngleFrom(self.pos, self.target.pos))
            if abs(angle_diff(self.rotation, r)) > 20:
                return False

        return True

    def turretFire(self):
        if self.fireTick > 0: return

        if not self.pointingAtTarget(): return

        self.fireTick = 1/self.BPS
        
        r = math.radians(self.rotation)


        Bullet(self, self.getBulletSpawnPoint(), r, spread = self.spread, damage = 20, type="normal", 
               ) 
        self.app.playPositionalAudio(self.app.turretFireSound, self.pos)
        
    def getBulletSpawnPoint(self):
        rotatedOffset = self.barrelOffset.rotate(self.rotation)
        return self.pos + rotatedOffset

    def tick(self):
        self.hitBox.center = self.pos.copy()

        r = 0
        if self.target:
            if self.target.killed:
                self.target = None

        if self.target:
            r = math.degrees(self.app.getAngleFrom(self.pos, self.target.pos))

            
        
        rotation = self.app.rangeDegree(r)

        RGAIN = 3000

        DIFF = angle_diff(self.rotation, rotation)

        rotation_factor = self.app.smoothRotationFactor(
            self.rotationVel,  # Current angular velocity (no deltaTime here)
            RGAIN,               # Gain factor - acceleration rate (no deltaTime here)
            DIFF  # Angle difference
        )

        self.rotationVel += rotation_factor * self.app.deltaTime
        self.rotation += self.rotationVel * self.app.deltaTime
        self.rotation = self.app.rangeDegree(self.rotation)

        if self.fireTick > 0:
            self.fireTick -= self.app.deltaTime

        self.shoot()

    def reset(self):
        if self in self.app.ENTITIES:
            self.app.ENTITIES.remove(self)
        if self in self.app.pawnHelpList:
            self.app.pawnHelpList.remove(self)
        self.killed = True

    def defaultPos(self):
        pass

    def die(self):
        
        Explosion(self.app, self.pos, self, 75)
        self.killed = True
        self.reset()

    def say(self, t, chanceToSay = 0.2):
        return

    def takeDamage(self, damage, fromActor = None, thornDamage = False, typeD = "normal", bloodAngle = None):

        if self.health <= 0:
            return

        self.health -= damage
        self.app.playPositionalAudio(self.app.turretDamageSound, self.pos)
        if self.health <= 0:
            self.die()
            pass

    def render(self):
        pos_leg = self.app.scale_world_pos(self.pos - v2(self.leg.get_size())/2 - self.app.cameraPosDelta)
        self.app.DRAWTO.blit(self.leg, pos_leg)

        im = pygame.transform.rotate(self.head.copy(), -self.rotation)
        pos_head = self.app.scale_world_pos(self.pos - v2(im.get_size())/2 - self.app.cameraPosDelta)
        self.app.DRAWTO.blit(im, pos_head)

    def rescale(self):
        if self.app.RENDER_SCALE != 1:
            self.leg = self.app.scale_surface(self.leg_base)
            self.head = self.app.scale_surface(self.head_base)
        else:
            self.leg = self.leg_base.copy()
            self.head = self.head_base.copy()


    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))
    
    def getOwnCell(self):
        return self.v2ToTuple(self.pos / self.app.tileSize)
    
    def getOwnCellFloat(self):
        p = self.pos / self.app.tileSize
        return (float(p[0]), float(p[1]))

    def getCell(self, pos):
        return self.v2ToTuple((pos + [0, self.app.tileSize/2]) / self.app.tileSize)

    def getVisibility(self, maxDist = 10):
        cell = self.getOwnCell()
        return self.app.map.get_visible_cells(cell[0], cell[1], maxDist)
    
    def sees(self, target: "Pawn"):
        c1 = self.getOwnCell()
        c2 = target.getOwnCell()
        return self.app.map.can_see(c1[0], c1[1], c2[0], c2[1])
    
    def canSeeCell(self, c2):
        c1 = self.getOwnCell()
        return self.app.map.can_see(c1[0], c1[1], c2[0], c2[1])
    
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
    
    def searchEnemies(self):
        if self.app.PEACEFUL:
            return
        
        #if self.flashed > 0:
        #    return
        
        x = random.choice(self.app.pawnHelpList)
        if x == self or not isinstance(x, self.app.SHOOTABLE):
            return
        
        if not self.app.VICTORY and not self.app.GAMEMODE == "1v1":
            if not self.team.hostile(self, x):
                return
        
        if x.respawnI > 0:
            return
        
        
        dist = self.pos.distance_to(x.pos)
        if dist > self.getTurretRange():
            return
        if self.target and dist >= self.pos.distance_to(self.target.pos):
            return

        if not self.sees(x):
            return
        
        if not self.target:
            self.app.playPositionalAudio("audio/turretAlert.wav", self.pos)

        self.target = x
        self.loseTargetI = 1

        self.team.addNadePos(self.target.getOwnCell(), "aggr") #
        

