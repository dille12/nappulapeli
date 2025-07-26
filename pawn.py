from rembg import remove
from PIL import Image
import io
import pygame
from pygame.math import Vector2 as v2
import random
import os
import math
import numpy as np
from imageProcessing import gaussian_blur, trim_surface, remove_background, generate_corpse_sprite, set_image_hue_rgba, colorize_to_blood
from blood import BloodParticle
from killfeed import KillFeed
from explosion import Explosion
from bloodSplatter import BloodSplatter
from pixelSort import pixel_sort_surface
def combinedText(*args, font):
    if len(args) % 2 != 0:
        raise ValueError("Arguments must be in (string, color) pairs")

    text_surfaces = []
    heights = []
    for i in range(0, len(args), 2):
        text = args[i]
        color = args[i+1]
        surf = font.render(text, True, color)
        text_surfaces.append(surf)
        heights.append(surf.get_height())

    total_width = sum(s.get_width() for s in text_surfaces)
    max_height = max(heights)

    combined_surface = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
    x = 0
    for surf in text_surfaces:
        combined_surface.blit(surf, (x, 0))
        x += surf.get_width()

    return combined_surface


def heat_color(v):
    v = max(0.0, min(1.0, v))
    if v < 0.5:
        # Green (0,255,0) → Yellow (255,255,0)
        t = v / 0.5
        r = round(255 * t)
        g = 255
        b = 0
    else:
        # Yellow (255,255,0) → Red (255,0,0)
        t = (v - 0.5) / 0.5
        r = 255
        g = round(255 * (1 - t))
        b = 0
    return (r, g, b)


class Pawn:
    def __init__(self, app, cardPath):
        self.app = app
        self.cardPath = cardPath
        # extract the name from the path
        self.name = cardPath.split("/")[-1].split(".")[0]
        self.removeBGPath = "player_images_removed/" + self.name + ".png"
        if not os.path.exists(self.removeBGPath):
            print("NEW PAWN INBOUND")
            remove_background(cardPath, self.removeBGPath)
            image = pygame.image.load(self.removeBGPath).convert_alpha()
        else:
            image = pygame.image.load(self.removeBGPath).convert_alpha()
            


        image = trim_surface(image)

        #self.blurredImage = gaussian_blur(self.image, sigma=5)
        if random.randint(0, 1) == 0:
            self.pos = v2(random.randint(0, 1920), random.choice([-200, self.app.res[1] + 200]))
        else:
            self.pos = v2(random.choice([-200, self.app.res[0] + 200]), random.randint(0, 1080))
        #self.pos = v2([1000, 500])
        self.deltaPos = self.pos.copy()

        self.imagePawn = pygame.transform.scale_by(image, 100 / image.get_size()[1]).convert_alpha()
        self.imagePawnR = pygame.transform.flip(self.imagePawn.copy(), True, False).convert_alpha()

        self.hurtPawn = colorize_to_blood(self.imagePawn.copy()).convert_alpha()
        self.hurtPawnR = pygame.transform.flip(self.hurtPawn.copy(), True, False).convert_alpha()

        self.hurtIm = [[], []]
        for x in range(10):
            h1 = self.hurtPawn.copy()
            h2 = self.hurtPawnR.copy()
            h1.set_alpha(int(255*x/10))
            h2.set_alpha(int(255*x/10))
            print("ALPHA:", int(255*x/10))
            self.hurtIm[0].append(h1)
            self.hurtIm[1].append(h2)

        self.hurtI = 0

        self.corpses = []
        for x in range(3):
            corpse = generate_corpse_sprite(self.imagePawn.copy())
            corpse.set_alpha(155)
            corpse = pygame.transform.rotate(corpse, random.randint(0,360))
            self.corpses.append(corpse)

        self.levelUpImage = pygame.transform.scale_by(image, 400 / image.get_size()[1])

        self.levelUpIms = []
        for x in range(4):
            l = self.levelUpImage.copy()
            b = random.randint(25,75)
            l = pixel_sort_surface(l, b, b+random.randint(50,100))
            l.set_alpha(random.randint(175,200))
            self.levelUpIms.append(l)

        self.facingRight = True
        self.team = 0
        self.teamColor = self.app.getTeamColor(self.team) 


        self.breatheI = random.uniform(0, 1)
        self.thinkEvery = 1 # seconds
        self.thinkI = random.uniform(0, self.thinkEvery)
        self.walkTo = None
        self.route = None
        self.speed = random.randint(300, 600)
        self.stepI = 0 
        self.respawnI = 0
        self.healthCap = 100
        self.health = self.healthCap

        self.lastKiller = None

        self.target = None
        self.killed = False
        self.hitBox = pygame.Rect(self.pos[0], self.pos[1], 100, 100)

        self.yComponent = 0
        self.xComponent = 0
        self.rotation = 0

        self.healthRegen = 10
        self.outOfCombat = 0
        self.loseTargetI = 0

        self.getNextItems()

        self.xp = 0
        self.xpI = 15

        self.weapon = None
        
        self.app.skullW.give(self)
        self.skullWeapon = self.weapon

        self.cameraLockI = 0


        weapon = random.choice([self.app.AK, self.app.e1, self.app.e2, self.app.e3, self.app.pistol])

        weapon.give(self)  # Give the AK-47 to this pawn
        self.app.pawnHelpList.append(self)

        self.kills = 0
        self.killsThisLife = 0
        self.level = 1
        self.deaths = 0

        self.itemEffects = {
            "speedMod": 1.0, # Done
            "healthRegenMult": 1.0,
            "thorns": 0.0,
            "healthCapMult": 1.0,
            "berserker" : False,
            "martyrdom" : False,

            "weaponHandling" : 1.0,
            "weaponDamage" : 1.0,
            "weaponReload" : 1.0,
            "weaponFireRate" : 1.0,
            "weaponAmmoCap" : 1.0,
            "weaponRange":1.0,
            "accuracy":1.0,
            "multiShot" : 1,

            "instaHeal" : False,
            "saveChance" : 0.0,
            "fireRateIncrease" : 0,
            "allyProtection" : False,
            "coward" : False,
            "revenge" : False,
            "duplicator" : False,

            "defenceNormal" : 1.0,
            "defenceEnergy" : 1.0,
            "defenceExplosion" : 1.0,

            "dodgeChance": 0.0,
            "xpMult":1.0,
            "healOnKill":0.0,
            "knockbackMult":1.0,
            "healAllies":0.0

        }

    def getSpeed(self):
        s = self.speed * self.itemEffects["speedMod"]
        if self.revengeHunt():
            s *= 2
        return s
    def getRegenRate(self):
        return self.healthRegen * self.itemEffects["healthRegenMult"]
    def thorns(self):
        return self.itemEffects["thorns"]
    def getHealthCap(self):
        return self.healthCap * self.itemEffects["healthCapMult"]
    def getWeaponHandling(self):
        return self.itemEffects["weaponHandling"]
    def getRange(self):
        if self.carryingSkull():
            return self.skullWeapon.range * self.itemEffects["weaponRange"]
        return self.weapon.range * self.itemEffects["weaponRange"]
    
    def revengeHunt(self):
        return self.itemEffects["revenge"] and self.lastKiller and not self.lastKiller.killed
    
    def defenceNormal(self):
        s = self.itemEffects["defenceNormal"]
        if self.revengeHunt():
            s *= 0.05
        return s
    
    def defenceEnergy(self):
        s = self.itemEffects["defenceEnergy"]
        if self.revengeHunt():
            s *= 0.05
        return s
    
    def defenceExplosion(self):
        s = self.itemEffects["defenceExplosion"]
        if self.revengeHunt():
            s *= 0.05
        return s

    def getNextItems(self):
        self.nextItems = []
        for x in range(3):
            self.nextItems.append(random.choice(self.app.items))

    def searchEnemies(self):
        
        x = random.choice(self.app.ENTITIES)
        if x == self or not isinstance(x, Pawn):
            return
        
        if x.team == self.team:
            return
        
        if x.respawnI > 0:
            return
        
        if self.revengeHunt():
            if self.lastKiller != x:
                return
        
        dist = self.pos.distance_to(x.pos)
        if dist > self.getRange():
            return
        if self.target and dist >= self.pos.distance_to(self.target.pos):
            return

        if not self.sees(x):
            return
        
        self.target = x
        self.loseTargetI = 2
        if not self.itemEffects["berserker"] and not self.carryingSkull():
            self.walkTo = v2(self.getOwnCell()) * 70
            self.route = None



    def shoot(self):

        if self.loseTargetI <= 0:
            self.target = None
            self.loseTargetI = 2

        
        if not self.target:
            self.searchEnemies()
        if not self.target:
            return
        
        if self.target.killed:
            self.target = None
            return
        dist = self.pos.distance_to(self.target.pos)
        if dist > self.getRange():
            self.loseTargetI -= self.app.deltaTime
            self.searchEnemies()
            return
        
        if not self.sees(self.target):
            self.loseTargetI -= self.app.deltaTime
            self.searchEnemies()
            return
        
        self.facingRight = self.target.pos[0] <= self.pos[0]
        if dist < 250:
            if self.carryingSkull():
                self.skullWeapon.tryToMelee()
            else:
                self.weapon.tryToMelee()
        elif self.carryingSkull(): # Cannot shoot with the skull!
            pass
        else:
            
            self.weapon.fireFunction(self.weapon)
        self.loseTargetI = 2

    def dropSkull(self):
        if self.app.objectiveCarriedBy != self:
            return
        self.app.objectiveCarriedBy = None
        self.app.skull.cell = self.getOwnCell()
        print("Skull dropped!")

    def die(self):

        if random.uniform(0, 1) < self.itemEffects["saveChance"]:
            self.health = self.healthCap
            return

        for x in self.app.deathSounds:
            x.stop()

        for x in range(random.randint(4,8)):
            self.app.particle_list.append(BloodParticle(self.pos.copy(), 1.2, app = self.app))

        #if self.app.cameraLock == self and self.target:
        #    self.app.cameraLock = self.target
        #    print("Camera quick switch")

        if self.carryingSkull() or (self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team):
            self.respawnI = 15
        else:
            self.respawnI = 5

        if self.app.objectiveCarriedBy == self:
            self.dropSkull()

        self.killed = True
        if self.itemEffects["martyrdom"]:
            Explosion(self.app, self.pos.copy(), self)

        random.choice(self.app.deathSounds).play()

        c = random.choice(self.corpses)
        self.app.MAP.blit(c, self.pos - v2(c.get_size())/2)

        self.pos = v2(self.app.spawn_points[self.team]) * 70 + [35, 35]
        self.deltaPos = self.pos.copy()
        self.health = self.healthCap

        self.hurtI = 0
        
        
        
        self.route = None
        self.walkTo = None
        self.killsThisLife = 0
        self.deaths += 1


    def takeDamage(self, damage, fromActor = None, thornDamage = False, typeD = "normal", bloodAngle = None):

        if self.killed:
            return

        if random.uniform(0, 1) < self.itemEffects["dodgeChance"]:
            return
        
        if fromActor.itemEffects["allyProtection"] and fromActor.team == self.team:
            return
        
        if typeD == "normal":
            damage *= self.defenceNormal()
        elif typeD == "energy":
            damage *= self.defenceEnergy()
        elif typeD == "explosion":
            damage *= self.defenceExplosion()

        self.health -= damage
        self.outOfCombat = 3
        self.hurtI = 0.25

        if bloodAngle:
            for x in range(random.randint(5,20)):
                BloodSplatter(self.app, self.pos.copy(), bloodAngle)

        if self.itemEffects["thorns"] > 0 and not thornDamage and fromActor:
            fromActor.takeDamage(damage * self.itemEffects["thorns"], thornDamage = True, fromActor = self)
        if self.health <= 0:
            if fromActor.team != self.team:
                self.lastKiller = fromActor
            self.die()
            KillFeed(fromActor, self, fromActor.weapon if not self.carryingSkull() else fromActor.skullWeapon)

    def gainXP(self, amount):
        self.xp += amount * self.itemEffects["xpMult"]


    def gainKill(self, killed):
        self.health += self.itemEffects["healOnKill"]
        self.killsThisLife += 1
        self.kills += 1
        self.gainXP(self.killsThisLife)
        if killed == self.lastKiller:
            self.lastKiller = None
            print("Retribution!")
        


    def tick(self):

        if self.respawnI > 0:

            if self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team:
                self.respawnI -= self.app.deltaTime*0.25
            else:
                self.respawnI -= self.app.deltaTime
            self.killsThisLife = 0
            self.dropSkull()
            return
        self.killed = False

        if self.xpI > 0:
            self.xpI -= self.app.deltaTime
        else:
            self.xpI = 15
            self.gainXP(1)

        if self.outOfCombat > 0:
            self.outOfCombat -= self.app.deltaTime
        
        if self.outOfCombat <= 0 or self.itemEffects["instaHeal"]:
            self.health += self.getRegenRate() * self.app.deltaTime
            self.health = min(self.health, self.healthCap)


        if self.xp >= self.app.levelUps[self.level-1] and not self.app.pendingLevelUp:
            self.app.pendingLevelUp = self


        self.think()
        self.walk()
        self.shoot()

        if self.getOwnCell() == self.app.skull.cell and not self.app.objectiveCarriedBy:
            self.app.objectiveCarriedBy = self
            #self.app.cameraLock = self

        
        self.breatheIm = self.imagePawn.copy() if self.facingRight else self.imagePawnR.copy()

        if self.hurtI > 0:
            I = int(9*self.hurtI/0.25)

            hurtIm = self.hurtIm[0 if self.facingRight else 1][I]

            self.breatheIm.blit(hurtIm, (0,0))

        self.breatheI += self.app.deltaTime % 2
        self.breatheIm = pygame.transform.scale_by(self.breatheIm, [1 + 0.05 * math.sin(self.breatheI * 2 * math.pi), 1 + 0.05 * math.cos(self.breatheI * 2 * math.pi)])
        self.breatheY = 2.5*math.sin(self.breatheI * 2 * math.pi)

        #if self.app.cameraLock == self and self.route:
        #    pygame.draw.rect(self.app.screen, [255,0,0], [self.route[0][0] * 70 - self.app.cameraPosDelta[0], self.route[0][1] * 70- self.app.cameraPosDelta[1], 70, 70])
        

        self.yComponent = 0
        self.xComponent = 0
        self.rotation = 0
        if self.walkTo is not None:
            # The player should be swinging from side to side when walking
            self.yComponent = abs(math.sin(self.stepI * 2 * math.pi)) * 30
            # The player should move left and right when walking
            self.xComponent = math.cos(self.stepI * 2 * math.pi) * 20
            self.rotation = math.cos(self.stepI * 2 * math.pi) * 10

            self.breatheIm = pygame.transform.rotate(self.breatheIm, self.rotation)

        newPos = self.pos - [self.xComponent, self.yComponent]
        self.deltaPos = newPos * 0.35 + self.deltaPos * 0.65

        # Draw an arc to resemble a circle around the player

        self.hitBox.center = self.pos.copy()

        

        #pygame.draw.arc(self.app.screen, (255, 255, 255), arcRect, 0, math.pi)

        #self.app.screen.blit(breatheIm, self.deltaPos - v2(breatheIm.get_size()) / 2 + [0, breatheY]  - self.app.cameraPosDelta)

        if self.carryingSkull():
            self.skullWeapon.tick()
            self.tryToTransferSkull()


        elif self.weapon:
            self.weapon.tick()           


        # Draw name

        self.namePlate = combinedText(self.name, self.teamColor, " +" + str(int(self.health)).zfill(3), heat_color(1 - self.health/self.healthCap), f" LVL {self.level}",[255,255,255], font=self.app.font)

        #t = self.app.font.render(f"{self.name}", True, (255, 255, 255))
        #self.app.screen.blit(t, (self.pos.x - t.get_width() / 2, self.pos.y - t.get_height() - 70) - self.app.cameraPosDelta)

        cx, cy = self.getOwnCell()

        self.hurtI -= self.app.deltaTime
        self.hurtI = max(0, self.hurtI)
        self.cameraLockI += self.app.deltaTime
        self.cameraLockI = self.cameraLockI%0.5

        pygame.draw.rect(self.app.MINIMAPTEMP, self.teamColor, [cx*3, cy*3, 3,3])

    def carryingSkull(self):
        return self.app.objectiveCarriedBy == self

    def tryToTransferSkull(self):
        p = random.choice(self.app.pawnHelpList)
        if p.team != self.team:
            return
        if p.killed:
            return
        cx, cy = self.getOwnCell()
        c2x, c2y = p.getOwnCell()
        if abs(cx - c2x) > 2 and abs(cy - c2y) > 2:
            return
        
        if self.level <= p.level:
            return
        
        self.app.objectiveCarriedBy = p
        print("Transferred skull to", p.name)
        

    def render(self):

        if self.killed:
            return

        self.arcRect = pygame.Rect(self.pos.x - self.app.cameraPosDelta[0], self.pos.y + 50 - self.app.cameraPosDelta[1], 0, 0)
        self.arcRect.inflate_ip(120, 60)

        if self.app.cameraLock == self:
            I = self.cameraLockI/0.5

            arcRectI = self.arcRect.copy()
            arcRectI.inflate_ip(120*I, 60*I)

        pygame.draw.arc(self.app.DRAWTO, self.teamColor, self.arcRect, 0, math.pi)

        if self.app.cameraLock == self:
            pygame.draw.arc(self.app.DRAWTO, self.teamColor, arcRectI, 0, 2*math.pi)

        self.app.DRAWTO.blit(self.breatheIm, self.deltaPos - v2(self.breatheIm.get_size()) / 2 + [0, self.breatheY]  - self.app.cameraPosDelta)

        

        if self.app.objectiveCarriedBy == self:
            self.skullWeapon.render()
        elif self.weapon:
            self.weapon.render()      

        pygame.draw.arc(self.app.DRAWTO, self.teamColor, self.arcRect, math.pi, math.pi * 2)


        self.app.DRAWTO.blit(self.namePlate, (self.pos.x - self.namePlate.get_width() / 2, self.pos.y - self.namePlate.get_height() - 70) - self.app.cameraPosDelta)

        if self.revengeHunt():
            t2 = self.app.font.render(f"HUNTING FOR {self.lastKiller.name}!!!", True, [255,255,255])
            self.app.DRAWTO.blit(t2, (self.pos.x - t2.get_width() / 2, self.pos.y - t2.get_height() - 40) - self.app.cameraPosDelta)
        elif self.weapon.isReloading():
            t2 = self.app.fontSmaller.render(f"RELOADING", True, [255,255,255])
            self.app.DRAWTO.blit(t2, (self.pos.x - t2.get_width() / 2, self.pos.y - t2.get_height() - 40) - self.app.cameraPosDelta)


    def think(self):
        self.thinkI += self.app.deltaTime
        if self.thinkI >= self.thinkEvery:
            self.thinkI = 0
            # Do some thinking logic here, e.g., print a message or change state

            c = self.app.randomWeighted(0.2, 0.2)
            if c == 0:
                if not self.target:
                    if not self.weapon.isReloading() and self.weapon.magazine < int(self.weapon.magazineSize * self.itemEffects["weaponAmmoCap"]) and not self.carryingSkull():
                        self.weapon.reload()


            if c == 1:
                if self.walkTo is None:
                    self.pickWalkingTarget()
    
    def distanceToPawn(self, pawn):
        return self.pos.distance_to(pawn.pos)
    
    def skullCarriedByOwnTeam(self):
        return self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team

    def pickWalkingTarget(self):
        if not self.target:
        #self.walkTo = v2(random.randint(0, 1920), random.randint(0, 1080))
            if self.revengeHunt():
                self.getRouteTo(endPosGrid=self.lastKiller.getOwnCell())
            else:
                if self.app.skull:
                    if not self.app.objectiveCarriedBy:
                        self.getRouteTo(endPosGrid=self.app.skull.cell) # RUN TOWARDS DROPPED SKULL
                    else:
                        if self.carryingSkull(): # CARRYING SKULL
                            if not self.route: # Else go to spawn
                                self.getRouteTo(endPosGrid=self.app.spawn_points[self.team])
                                print("Running with skull to spawn")
                            #if len(self.route) > 6:
                            #    self.route = self.route[0:5] # WALKS TOWARDS OWN SPAWN
                        else:
                            c = self.app.randomWeighted(0.5, 0.2)
                            if c == 1 and self.skullCarriedByOwnTeam():
                                self.getRouteTo(endPosGrid=self.app.spawn_points[(self.team+1)%self.app.teams])
                                print("Attacking!")
                            else:
                                
                                cells = self.app.objectiveCarriedBy.getVisibility() # ELSE WALK TOWARDS SKULL CARRIER VICINITY
                                self.getRouteTo(endPosGrid=random.choice(cells))
                else:
                    self.getRouteTo(endPosGrid=self.app.spawn_points[(self.team+1)%self.app.teams])
        else:

            if self.carryingSkull(): # Go melee target
                self.getRouteTo(endPosGrid=self.target.getOwnCell())
                print("Running with skull towards target")

            elif self.itemEffects["coward"] and self.health <= 0.5 * self.getHealthCap():
                self.getRouteTo(endPosGrid=self.app.spawn_points[self.team])
                if len(self.route) > 18:
                    self.route = self.route[0:15]

            else:
                CELLS = self.getVisibility()

                if self.app.skull.cell in CELLS and not self.app.objectiveCarriedBy:
                    self.getRouteTo(endPosGrid=self.app.skull.cell)
                else:
                    self.getRouteTo(endPosGrid=random.choice(CELLS))


    def getRouteTo(self, endPos = None, endPosGrid = None):
        if endPos:
            endPos = (int(endPos[0]/70), int(endPos[1]/70))

        elif endPosGrid:
            endPos = endPosGrid

        startPos = (int(self.pos[0]/70), int(self.pos[1]/70))

        self.route = self.app.arena.pathfinder.find_path(startPos, endPos)

        self.advanceRoute()


    def advanceRoute(self):
        if not self.route:
            return
        self.walkTo = v2(self.route[0]) * 70 + [35, 0]
        self.route.pop(0)


    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))
    
    def getOwnCell(self):
        return self.v2ToTuple((self.pos + [0, 35]) / 70)


    def getVisibility(self):
        cell = self.getOwnCell()
        return self.app.map.get_visible_cells(cell[0], cell[1])
    
    def sees(self, target: "Pawn"):
        c1 = self.getOwnCell()
        c2 = target.getOwnCell()
        return self.app.map.can_see(c1[0], c1[1], c2[0], c2[1])


    def walk(self):
        if self.walkTo is not None:
            
            if not self.target:
                self.facingRight = self.walkTo[0] <= self.pos[0]

            direction = self.walkTo - self.pos
            if direction.length() > self.getSpeed() * 2 / 60:
                direction = direction.normalize()
                self.pos += direction * self.getSpeed() * self.app.deltaTime
                self.stepI += self.app.deltaTime * self.getSpeed() / 300
                
            else:
                if self.route:
                    self.advanceRoute()
                else:
                    self.walkTo = None
                    self.stepI = 0  # Reset step index when reaching the target

            if self.route and len(self.route) > 5:
                c = self.getOwnCell()
                r1x, r1y = self.route[0]
                r2x, r2y = self.route[1]

                if self.app.map.can_see(c[0], c[1], r1x, r1y) and self.app.map.can_see(c[0], c[1], r2x, r2y):
                    self.advanceRoute()

        elif self.route:
            self.advanceRoute()


