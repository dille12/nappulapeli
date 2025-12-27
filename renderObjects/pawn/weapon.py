import pygame
from imageprocessing.imageProcessing import gaussian_blur, trim_surface, remove_background
from pygame.math import Vector2 as v2
import math
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from renderObjects.pawn.pawn import Pawn
import random
from renderObjects.bullet import Bullet, line_intersects_rect
from renderObjects.particles.laser import ThickLaser
from renderObjects.explosion import Explosion
import io, base64
from renderObjects.grenade import Grenade, GrenadeType
from renderObjects.demoObject import DemoObject
def surface_to_base64(surface: pygame.Surface) -> str:
    buf = io.BytesIO()
    pygame.image.save(surface, buf, "PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return b64  # Just the base64, no prefix

def apply_light_bounce(mask_surf, rot_norm):
    w, h = mask_surf.get_size()

    temp = mask_surf.copy().convert_alpha()

    rot_norm = rot_norm*2-0.5

    y = int(h * rot_norm)

    angle = math.radians(30)
    dx = math.cos(angle)
    dy = math.sin(angle)

    length = max(w, h) * 2

    x0 = -length
    y0 = y - dy * length
    x1 = length
    y1 = y + dy * length

    line_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.line(
        line_surf,
        (255, 255, 255, 255),
        (x0, y0),
        (x1, y1),
        40
    )

    # Multiply keeps line only where mask is opaque
    temp.blit(line_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    return temp


def angle_diff(a, b):
    diff = (b - a + 180) % 360 - 180
    return diff

def angle_diff_radians(a,b):
    diff = (b - a + math.pi) % (2*math.pi) - math.pi
    return diff

def ease_in_out(t):
    return 3 * t**2 - 2 * t**3

def reload_rotation(t):
    if t < 0.2:
        return ease_in_out(t / 0.2) * 90
    elif t < 0.35:
        return 90 - ease_in_out((t - 0.2) / 0.15) * (90 - 65)
    elif t < 0.5:
        return 65 + ease_in_out((t - 0.35) / 0.15) * (90 - 65)
    else:
        return 90 * (1 - ease_in_out((t - 0.5) / 0.5))
    

def melee_animation(t):
    if t < 0.15:
        k = ease_in_out(t / 0.15)
        x = -15 * k            # deeper wind-up
        y = 7 * k
        angle = -30 * k        # more backward rotation

    elif t < 0.5:
        k = ease_in_out((t - 0.15) / 0.35)
        x = -15 + 75 * k       # total +60 x from base
        y = 7 - 12 * k
        angle = -30 + 160 * k  # total +130° swing

    else:
        k = ease_in_out((t - 0.5) / 0.5)
        x = 60 * (1 - k)
        y = -5 * (1 - k)
        angle = 130 * (1 - k)

    return x, y, angle

def hammer_animation(t):
    if t < 0.2:
        # Wind up - raise hammer high
        k = ease_in_out(t / 0.2)
        x = -10 * k
        y = -30 * k  # Higher than normal melee
        angle = -60 * k + 90
    elif t < 0.7:
        # Hold position
        x = -10
        y = -30
        angle = -60 + 90
    else:
        # Strike down hard
        k = ease_in_out((t - 0.7) / 0.3)
        x = -10 + 40 * k
        y = -30 + 80 * k  # Slam down
        angle = -60 - 60 * k  + 90
    
    return x, y, angle

def hammer_animation_with_jump(t):
    # Parabolic jump physics
    # Jump peaks at t=0.5, lands at t=1.0
    jump_height = -80 * (4 * t * (1 - t))  # Parabola: peaks at t=0.5
    
    # Hammer swing animation
    if t < 0.3:
        # Wind up while jumping
        k = ease_in_out(t / 0.3)
        x = -15 * k
        y = -40 * k  # High windup
        angle = 70 * k
    elif t < 0.6:
        # Hold hammer high at peak of jump
        x = -15
        y = -40
        angle = 70
    else:
        # Slam down as landing
        k = ease_in_out((t - 0.6) / 0.4)
        x = -15 + 80 * k
        y = -40 + 90 * k  # Big slam
        angle = 70 - 70 * k
    
    return x, y + jump_height, angle


class Weapon(DemoObject):
    def __init__(self, app: "Game", name: str, price: list, *args, owner: "Pawn" = None, precomputedImage=None, sizeMult = 1, burstBullets=3, burstTime=0.1):
        """
        Initialize the Weapon object.
        :param args: Arguments for the weapon, including app, name, image_path, damage, and range.
        :param owner: The Pawn object that owns this weapon.
        :param precomputedImage: Optional precomputed image to avoid loading it again.
        """
        self.args = args
        image_path, damage, range, magSize, fireRate, fireFunction, reloadTime, typeD = args
        self.app = app
        self.name = name
        self.owner = owner
        self.typeD = typeD
        self.price = price

        super().__init__(demo_keys=("ROTATION", "FINALROTATION", "recoil", "owner", "BLITPOS", "rA"))


        self.weaponIsGrenade = fireFunction == Weapon.grenade
        self.weaponIsObjective = fireFunction == Weapon.skull

        WEAPONSCALE = 1.1
        if not precomputedImage:
            self.image = pygame.image.load(image_path).convert_alpha()
            if image_path == "texture/ak47.png":
                self.image = trim_surface(self.image)

            if self.image.get_width() == 16 and self.image.get_height() == 16:
                self.image = pygame.transform.scale_by(self.image, 36 / self.image.get_width())
            else:
                self.image = pygame.transform.scale_by(self.image, (150*sizeMult) / self.image.get_width())  # Scale the image to a suitable size


            
            self.image = pygame.transform.scale_by(self.image, self.app.RENDER_SCALE * WEAPONSCALE)  # Scale the image to a suitable size

        else:
            self.image = precomputedImage

        

        


        self.masked = False
        if self.name == "BABLON AK-47":
            self.tintMask = pygame.transform.scale(pygame.image.load("texture/goldenAkMASK.png"), self.image.get_size()).convert_alpha()
            self.tintMaskR = pygame.transform.flip(self.tintMask.copy(), True, False)
            self.masked = True

        self.shopIcon = pygame.transform.scale_by(self.image.copy(), 100 / self.image.get_height()) 
        self.shopIcon = trim_surface(self.shopIcon)

        self.imageR = pygame.transform.flip(self.image.copy(), True, False)

        self.imageKillFeed = pygame.transform.scale_by(self.image, 20 / self.image.get_height())
        self.imageKillFeed = trim_surface(self.imageKillFeed)

        self.encodedImage = surface_to_base64(self.imageKillFeed)

        self.damage = damage
        self.range = range
        self.magazineSize = magSize
        self.magazine = self.magazineSize
        self.reloadTime = reloadTime
        self.currReload = 0
        self.meleeI = 0
        self.firerate = fireRate # PER SECOND
        self.secondsPerRound = 1/self.firerate
        self.fireTick = 0
        self.spread = 0.05

        self.addedFireRate = 0

        self.recoil = 0
        self.runOffset = 0

        self.fireFunction = fireFunction

        self.wobbleRotation = 0
        self.wobbleVel = 0

        self.burstRounds = burstBullets
        self.burstI = burstTime
        self.currBurstRounds = 0
        self.currBurstI = 0

        self.struck = False

        self.FINALROTATION = 0
        self.ROTATION = 0
        self.ROTATIONVEL = 0
        self.barrelOffset = v2(self.image.get_width()/2, 0)


        self.grenadeThrowI = 0
        self.TARGETROTATION = 0

        self.lazerActive = False
        self.lazerTimer = 0
        self.lazerSound = None
        if self.owner:
            self.defaultPos = self.owner.pos
        else:
            self.defaultPos = v2(0,0)

    def getPacket(self):
        p = {"name": self.name,
             "price": self.price[0],
             "image": self.encodedImage, 
             "description": "Bitch.",
             "backgroundColor": self.get_rarity_color()
        }
        return p
    

    def isReloading(self):
        return self.currReload > 0
    
    def getBulletSpawnPoint(self):
        """
        Calculate the world position where bullets should spawn from.
        Returns a Vector2 representing the bullet spawn point in world coordinates.
        """
        # Get the weapon's world position (same calculation as in tick method)
        ownerBreathe2 = math.sin(self.owner.breatheI * math.pi)
        
        weaponWorldPos = (self.defaultPos + 
                         v2(0.5*self.owner.xComponent, -0.25*self.owner.yComponent + ownerBreathe2*5) + 
                         v2(0, 40) + 
                         self.getSwiwel())
                
        # Rotate the barrel offset by the current weapon rotation
        rotatedOffset = self.barrelOffset.rotate(-self.FINALROTATION)
        
        # Add the rotated offset to the weapon's world position
        bulletSpawnPoint = weaponWorldPos + rotatedOffset
        
        return bulletSpawnPoint
    
    def getSwiwel(self):
        dr = math.radians(self.ROTATION)

        return v2(math.cos(-dr) * 30, -abs(math.sin(-dr) * 5))

    def give(self, pawn: "Pawn"):
        """
        Give this weapon to a pawn.
        :param pawn: The Pawn object to give the weapon to.
        """

        # This creates a memory leak if the weapon is given to multiple pawns?
        pawn.weapon = self.duplicate(pawn)
        
    def duplicate(self, pawn):
        return Weapon(self.app, self.name, self.price, *self.args, owner=pawn, precomputedImage=self.image.copy(),
                             sizeMult=1, burstBullets=self.burstRounds, burstTime=self.burstI)  # Pass the image as a precomputed image
    
    def copy(self):
        return Weapon(self.app, self.name, self.price, *self.args, owner=self.owner, precomputedImage=self.image.copy(),
                             sizeMult=1, burstBullets=self.burstRounds, burstTime=self.burstI)  # Pass the image as a precomputed image


    def reload(self):
        self.currReload = self.getReloadTime()
        self.magazine = self.owner.getMaxCapacity(self)

        self.app.playPositionalAudio("audio/reload.wav", self.owner.pos)

        #if self.owner.onScreen():
        #    self.app.reloadSound.stop()
        #    self.app.reloadSound.play()


    def addRecoil(self, amount):
        self.recoil += amount / self.owner.itemEffects["recoilMult"]

    
    def skull(self):
        self.magazine = self.owner.getMaxCapacity(self)
        return
    
    

    def getMeleeTime(self):
        return 0.5 / max(self.owner.getHandling(), 0.1)
    

    def tryToMelee(self):
        if self.meleeing(): return

        self.meleeI = self.getMeleeTime()
        t = self.owner.target.pos.copy()

        self.owner.target.takeDamage(50*self.owner.itemEffects["meleeDamage"], fromActor = self)

        if self.owner.itemEffects["detonation"]:
            Explosion(self.app, t, self, 100*self.owner.itemEffects["meleeDamage"])


        self.app.playPositionalAudio(self.app.meleeSound, self.owner.pos)
        #if self.owner.onScreen():
        #    self.app.meleeSound.stop()
        #    self.app.meleeSound.play()

    def tryToBuild(self):
        if self.meleeing(): return
        if not self.owner.buildingTarget: return
        if self.owner.pos.distance_to(self.owner.buildingTarget.pos) > 150: return
        if self.owner.buildingTarget.built(): return
        self.owner.walkTo = None
        self.meleeI = self.getMeleeTime()
        self.struck = False

    def hammerStrike(self):
        if not self.canStrike(): return
        
        self.tryToBuild()
        
        # Calculate jump progress
        jump_progress = (self.getMeleeTime() - self.meleeI) / self.getMeleeTime()
        
        # Parabolic jump: y = -4h*x*(x-1) where h is max height
        max_jump_height = 100
        self.owner.buildingJumpOffset = -max_jump_height * 4 * jump_progress * (jump_progress - 1)
        
        # Horizontal bounce for extra comedy
        bounce_amplitude = 15
        self.owner.buildingBounceOffset = bounce_amplitude * math.sin(jump_progress * math.pi * 2)

        rotation_amplitude = 30
        self.owner.buildingRotationOffset = rotation_amplitude * 4 * jump_progress * (jump_progress - 1)
        
        # Strike timing at landing (t ≈ 0.85)
        if 0.8 < jump_progress < 0.9 and not self.struck:
            self.struck = True
            
            # Impact effect with screen shake
            if self.owner.buildingTarget:
                self.owner.buildingTarget.addProgress(10)

            if self.owner.buildingTarget.built():
                self.owner.buildingTarget = None
                
            # Extra impact effects
            #if self.owner.onScreen():
            self.app.playPositionalAudio(self.app.hammerSound, self.owner.pos)

    def canStrike(self):
        #if self.meleeing(): return False
        #if not self.owner.building: return False
        #if not self.owner.buildingTarget: return False
        return True
    

    def Energyshoot(self):
        if not self.canShoot(): return

        #if self.owner.onScreen():
        self.app.playPositionalAudio(self.app.energySound, self.owner.pos)
        self.magazine -= 1
        self.fireTick = self.owner.getRoundsPerSecond(self)

        r = math.radians(-self.ROTATION)
        gun_x, gun_y = self.getBulletSpawnPoint()
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        for x in range(self.owner.itemEffects["multiShot"]):
            self.createBullet(0.2)


    def BFGshoot(self):

        if self.lazerActive:

            if not self.canShoot():
                self.lazerActive = False
                return

            startPos = self.getBulletSpawnPoint()

            r = math.radians(-self.ROTATION)
            r = self.adjustToAccuracy(r)

            endPos = [
                startPos[0] + math.cos(r) * self.owner.getRange(self),
                startPos[1] + math.sin(r) * self.owner.getRange(self)
            ]
            
            self.app.BFGLasers.append([startPos, endPos, self.owner.teamColor])
            
            self.lazerTimer -= self.app.deltaTime
            if self.lazerTimer <= 0:
                self.lazerTimer += self.owner.getRoundsPerSecond(self)

                

                self.magazine -= 1
                
                self.app.particle_system.create_muzzle_flash(startPos[0], startPos[1], math.radians(-self.ROTATION))

                for x in self.app.pawnHelpList:
                    if x == self.owner:
                        continue
                    if self.owner.itemEffects.get("allyProtection") and self.owner.team == x.team:
                        continue
                    if x.killed:
                        continue

                    collides = line_intersects_rect(
                        startPos[0], startPos[1],
                        endPos[0], endPos[1],
                        x.hitBox.x, x.hitBox.y, x.hitBox.width, x.hitBox.height
                    )
                    if collides:
                        x.takeDamage(
                            self.owner.getDamage(self) * self.owner.getRoundsPerSecond(self),  # fixed time step damage
                            fromActor=self,
                            typeD="energy",
                            bloodAngle=-math.radians(self.ROTATION)
                        )

        else:

            if not self.canShoot():
                return
            if self.magazine <= 0:
                self.reload()
                return
            
            self.lazerActive = True
            self.lazerTimer = 0.04
            self.lazerSound = self.app.playPositionalAudio("audio/minigun1.wav", self.owner.pos)
            
    
    

    def RocketLauncher(self):
        if not self.canShoot(): return

        self.magazine -= 1

        #if self.owner.onScreen():
        self.app.playPositionalAudio(self.app.rocketSound, self.owner.pos)

        self.fireTick = self.owner.getRoundsPerSecond(self)
        r = math.radians(-self.ROTATION)

        gun_x, gun_y = self.getBulletSpawnPoint()
        pierce = self.owner.itemEffects["piercing"]
        homing = self.owner.itemEffects["homing"]
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        r = self.adjustToAccuracy(r)

        for x in range(self.owner.itemEffects["multiShot"]):
            Bullet(self, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.25, damage = self.owner.getDamage(self), rocket=True, type=self.typeD, piercing=pierce, homing=homing) #-math.radians(self.FINALROTATION)
            self.addRecoil(0.4)
        self.addRecoil(3)


    def suppressedShoot(self):
        self.AKshoot(sounds = self.app.silencedSound)

    def smgShoot(self):
        self.AKshoot(sounds = self.app.smgSound)

    def pistolShoot(self):
        self.AKshoot(sounds = self.app.pistolSound, recoil = 0.5)

    def desertShoot(self):
        self.AKshoot(sounds = "audio/deserteagle.wav", critChance = 0.25, recoil = 1)



    def burstShoot(self):
        if self.meleeing(): return 
     
        if self.isReloading(): return 
                    
        if self.magazine == 0:
            self.reload()
            self.currBurstRounds = 0
            return False
        
        if self.currBurstRounds == 0:
            if not self.canShoot(): return

            self.currBurstRounds = min(self.burstRounds, self.magazine)
            self.currBurstI = 0

        if self.currBurstRounds > 0:
            
            if self.currBurstI <= 0:
                self.currBurstI += self.burstI #* self.owner.getFireRateMod()
                self.currBurstRounds -= 1
                self.currBurstRounds = max(0, self.currBurstRounds)

                r = math.radians(-self.ROTATION)
                gun_x, gun_y = self.getBulletSpawnPoint()
                self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

                for x in range(self.owner.itemEffects["multiShot"]):
                    self.createBullet(0.25)
                self.magazine -= 1
                self.fireTick += self.owner.getRoundsPerSecond(self)
                #if self.owner.onScreen():
                if self.typeD == "energy":
                    self.app.playPositionalAudio(self.app.energySound, self.owner.pos)
                else:
                    self.app.playPositionalAudio(self.app.ARSounds, self.owner.pos)
            
            self.currBurstI -= self.app.deltaTime

    def shotgunShoot(self):
        

        if not self.canShoot(): return

        #if self.owner.onScreen():
        self.app.playPositionalAudio(self.app.shotgunSound, self.owner.pos)

        

        self.magazine -= 1
        self.fireTick = self.owner.getRoundsPerSecond(self)
        r = math.radians(-self.ROTATION)
        gun_x, gun_y = self.getBulletSpawnPoint()
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        pierce = self.owner.itemEffects["piercing"]
        homing = self.owner.itemEffects["homing"]

        r = self.adjustToAccuracy(r)

        for x in range(10*self.owner.itemEffects["multiShot"]):
            Bullet(self, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.25, damage = self.owner.getDamage(self), type=self.typeD, piercing=pierce, homing=homing) #-math.radians(self.FINALROTATION)
            self.addRecoil(0.15)


    def grenade(self):
        self.grenadeThrowI += self.app.deltaTime * self.owner.itemEffects["utilityUsage"]
        if self.grenadeThrowI >= 1:

            if self.name == "Flashbang":
                gType = GrenadeType.FLASH
            elif self.name == "Frag Grenade":
                gType = GrenadeType.FRAG
            elif self.name == "Turret Grenade":
                gType = GrenadeType.TURRET
            if self.owner.grenadePos:
                Grenade(self.app, self.owner.getOwnCell(), self.owner.grenadePos, self.image, self.owner, grenadeType=gType)
                self.owner.grenadeAmount -= 1
            self.grenadeThrowI = 0
            self.owner.grenadePos = None
            self.app.playPositionalAudio("audio/nadeThrow.wav", self.owner.pos)
        pass

    def AKshoot(self, sounds = None, critChance = 0, recoil = 0.25):
        
        if not self.canShoot(): return
        
        if not sounds:
            sounds = self.app.ARSounds

        #if self.owner.onScreen():
        self.app.playPositionalAudio(sounds, self.owner.pos)

        self.magazine -= 1
        self.fireTick = self.owner.getRoundsPerSecond(self)


        r = math.radians(-self.ROTATION)
        gun_x, gun_y = self.getBulletSpawnPoint()
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        for x in range(self.owner.itemEffects["multiShot"]):
            self.createBullet(recoil, critChance = critChance)

    def adjustToAccuracy(self, r):
        if not self.owner.target:
            return r
        accuracy = self.owner.itemEffects["accuracy"] - 1
        accuracy = min(max(accuracy, -1), 1)
        actualR = self.app.getAngleFrom(self.defaultPos, self.owner.target.pos)

        diff = angle_diff_radians(actualR, r)
        r = r - accuracy * diff

        return r

    def createBullet(self, recoil, critChance = 0):
        r = math.radians(-self.ROTATION)
        pierce = self.owner.itemEffects["piercing"]
        homing = self.owner.itemEffects["homing"]

        r = self.adjustToAccuracy(r)

        Bullet(self, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.25, damage = self.owner.getDamage(self), type=self.typeD, 
               piercing=pierce, homing=homing, critChance = critChance * self.owner.itemEffects["accuracy"]) #-math.radians(self.FINALROTATION)
        self.addRecoil(recoil)

    import math

    def get_rarity_color(self, max_price=300):
        p = max(float(self.price[0]), 1.0)
        m = max(float(max_price), 1.0)

        x = p/m
        x = max(0.0, min(x, 1.0))

        if x < 0.2:
            t = x / 0.2
            c0, c1 = (120,120,120), (50,200,50)
        elif x < 0.4:
            t = (x-0.2) / 0.2
            c0, c1 = (50,200,50), (80,120,255)
        elif x < 0.6:
            t = (x-0.4) / 0.2
            c0, c1 = (80,120,255), (180,80,220)
        elif x < 0.8:
            t = (x-0.6) / 0.2
            c0, c1 = (180,80,220), (255,140,40)
        else:
            t = (x-0.8) / 0.2
            c0, c1 = (255,140,40), (255,215,80)

        return [
            int(c0[i] + (c1[i] - c0[i]) * t * 0.25)
            for i in range(3)
        ]



    def checkIfCanAddFireRate(self):
        if not self.owner.target: return False
        if not self.owner.sees(self.owner.target): return False
        if self.meleeing(): return False
        if self.isReloading(): return False
        if not self.pointingAtTarget(): return False
        if self.magazine <= 0: return False
        return True

    def canShoot(self):
        if self.meleeing(): return False
     
        if self.isReloading(): return False
                    
        if self.magazine <= 0:
            self.reload()
            return False
        
        if self.fireTick > 0:
            return False
        
        if self.owner.isManual():
            return "mouse0" in self.app.keypress_held_down and not self.app.PEACEFUL
        
        if self.owner.flashed > 0: return True

        if not self.pointingAtTarget(): return False

        x,y = self.owner.getOwnCellFloat()
        if self.owner.target:
            dist = self.app.getDistFrom((x,y), self.owner.target.getOwnCellFloat())
        else:
            dist = 10

        allCells = self.app.map.marchRayAll(x,y, -math.degrees(self.owner.aimAt), int(dist)+1)
        allCells_set = set(map(tuple, allCells))

        #if self.owner == self.app.cameraLock:
        #    self.app.debugCells += list(allCells)

        #teamPawns = self.owner.team.getPawns()
        for p in self.app.pawnHelpList:
            if self.owner.team.hostile(self.owner, p):
                continue
            
            if p == self.owner or p.killed:
                continue

            if p.getOwnCell() in allCells_set:
                #self.owner.say("VÄISTÄ NII MÄ VOIN AMPUA", 0.1)
                self.app.debugCells.append(p.getOwnCell())
                self.owner.STATUS = f"CANNOT SHOOT! own in the way: {p.name}" 
                return False
        #self.app.TIMESCALE = 1
        self.owner.STATUS = "CAN SHOOT" 
        return True


    

    def pointingAtTarget(self):
        if self.owner.target:
            r = -math.degrees(self.app.getAngleFrom(self.defaultPos, self.owner.target.pos))
            if abs(angle_diff(self.ROTATION, r)) > 20:
                return False

        return True
    
    def meleeing(self):
        return self.meleeI > 0
    
    def getReloadTime(self):
        return self.reloadTime
    
    
    
    def raiseWeaponWhileRunning(self):

        if not self.owner.walkTo:
            return False
        if self.owner.target:
            return False

        if self.name != "SKULL" and (self.isReloading() or self.meleeing()):
            return False
        
        if self.owner.pos.distance_to(self.owner.walkTo) < 500 and not self.owner.route:
            return False
        
        #if self.owner.route and len(self.owner.route) < 5:
        #    return False

        return True
    

    def addFireRate(self):
        if self.checkIfCanAddFireRate(): 
            self.addedFireRate += self.owner.itemEffects["fireRateIncrease"] * self.app.deltaTime
        else:
            self.addedFireRate -= self.owner.itemEffects["fireRateIncrease"] * self.app.deltaTime

        self.addedFireRate = max(0, self.addedFireRate)

    def tryToDisableLazer(self):
        if not self.lazerActive:
            if self.lazerSound:
                self.lazerSound.active = False
                self.lazerSound = None
                self.app.playPositionalAudio("audio/minigun2.wav", self.owner.pos)



    def tick(self):

        self.defaultPos = self.owner.deltaPos.copy()
        if self.owner.dualwield:
            if self != self.owner.dualWieldWeapon:
                self.defaultPos = self.owner.deltaPos.copy() + [-self.owner.height*0.3, -self.owner.height*0.13]
            else:
                self.defaultPos = self.owner.deltaPos.copy() + [self.owner.height*0.3, -self.owner.height*0.13]

        if self.meleeing():
            self.meleeI -= self.app.deltaTime

        elif self.isReloading():
            self.currReload -= self.owner.getReloadAdvance()

        self.addFireRate()

        # image is rotated 45 degrees to resemble lowering a weapon

        ownerBreathe = math.cos(self.owner.breatheI * math.pi)
        ownerBreathe2 = math.sin(self.owner.breatheI * math.pi)

        rotationMod = ownerBreathe*5 - self.owner.rotation*0.5

        if self.owner.isManual():
            #mouse = self.app.mouse_pos + self.app.cameraPosDelta
            mouse_world = self.app.cameraPosDelta + self.app.mouse_pos
            r = math.degrees(self.app.getAngleFrom(self.defaultPos, v2(mouse_world)))
            if "shift" in self.app.keypress_held_down:
                self.runOffset += (self.app.deltaTime * self.owner.getHandling()*2)
            else:
                self.runOffset -= (self.app.deltaTime * self.owner.getHandling()*2)

        elif self.owner.target and not self.isReloading():
            r = math.degrees(self.app.getAngleFrom(self.defaultPos, self.owner.target.pos))
            self.runOffset -= (self.app.deltaTime * self.owner.getHandling()*2)

        elif self.weaponIsGrenade and self.owner.grenadePos:
            r = math.degrees(self.app.getAngleFrom(self.defaultPos, v2(self.owner.grenadePos) * self.app.tileSize))
            self.runOffset -= (self.app.deltaTime * self.owner.getHandling()*2)

        else:
            if self.raiseWeaponWhileRunning():
                r = -110 if self.owner.facingRight else -70

                self.runOffset += (self.app.deltaTime * self.owner.getHandling()*2)
            else:
                r = 135 if self.owner.facingRight else 45
                self.runOffset -= (self.app.deltaTime * self.owner.getHandling()*2)
        self.runOffset = min(max(self.runOffset, 0), 1)
        #m = v2(pygame.mouse.get_pos()) + self.app.cameraPosDelta
        #
        #r = math.degrees(self.app.getAngleFrom(self.owner.pos, m))
        #if "mouse0" in self.app.keypress:
        #    self.meleeI = 0.5

        xA, yA, self.rA = 0,0,0

        if self.name == "Hammer":
            self.hammerStrike()
            xA, yA, self.rA = hammer_animation_with_jump((self.getMeleeTime()-self.meleeI)/self.getMeleeTime())

        elif self.meleeing():
            xA, yA, self.rA = melee_animation((self.getMeleeTime()-self.meleeI)/self.getMeleeTime())

            #r += rA #if self.owner.facingRight else -rA

        elif self.isReloading():
            r2 = reload_rotation((self.getReloadTime() - self.currReload)/self.getReloadTime()) * 1.4

            r += r2 if self.owner.facingRight else -r2

        

        rotation = -r + rotationMod

        self.recoil *= 0.97 ** (self.app.deltaTime*144)

        
        rotation = self.app.rangeDegree(rotation)

        

        RGAIN = 1000 * self.owner.getHandling()
        RGAIN = max(1, RGAIN)

        DIFF = angle_diff(self.ROTATION, rotation)
        if self.owner.itemEffects["noscoping"] and DIFF < -20:
            DIFF += 360

        # Calculate the rotation factor using proper units
        rotation_factor = self.app.smoothRotationFactor(
            self.ROTATIONVEL,  # Current angular velocity (no deltaTime here)
            RGAIN,               # Gain factor - acceleration rate (no deltaTime here)
            DIFF  # Angle difference
        )
        if self.owner.flashed <= 0:
            self.ROTATIONVEL += rotation_factor * self.app.deltaTime

        # Apply velocity to position
        self.ROTATION += self.ROTATIONVEL * self.app.deltaTime
        self.ROTATION = self.app.rangeDegree(self.ROTATION)

        yA -= self.runOffset*50
        runOffset = self.runOffset*30

        if 90 <= self.ROTATION <= 270:
            self.FINALROTATION = self.ROTATION - self.recoil * 30 - self.rA
            meleeOffset = v2(-xA + runOffset, yA)
        else:
            self.FINALROTATION = self.ROTATION + self.recoil * 30 + self.rA
            meleeOffset = v2(xA - runOffset, yA)

        
        self.handleSprite()
        

        # Update the weapon's image

        # Backward movement (opposite to weapon direction)
        recoilBackwardOffset = v2(-self.recoil * 30, 0).rotate(-self.ROTATION)

        # Upward movement (perpendicular to weapon, always "up" relative to weapon)
        recoilUpwardOffset = v2(0, -self.recoil * 10)

        # Combined recoil offset
        recoilOffset = recoilBackwardOffset + recoilUpwardOffset

        



        
        
        swiwelOffset = self.getSwiwel()

        DUALWIELDOFFSET = self.defaultPos - self.owner.deltaPos.copy()

        TOTALOFFSET = DUALWIELDOFFSET + v2([0.5*self.owner.xComponent, -0.25*self.owner.yComponent + ownerBreathe2*5]) + v2([0, 40]) + recoilOffset + swiwelOffset + meleeOffset
        
        TOTALOFFSET = TOTALOFFSET.rotate(-self.owner.rotation)


        self.BLITPOS = (TOTALOFFSET * self.app.RENDER_SCALE) + self.owner.deltaPos

        self.saveState()

    def handleSprite(self):
        if 90 <= self.ROTATION <= 270:
            self.rotatedImage = pygame.transform.rotate(self.imageR, self.FINALROTATION + 180)

            if self.masked:
                self.rotatedMask = pygame.transform.rotate(self.tintMaskR, self.FINALROTATION + 180)

        else:
            self.rotatedImage = pygame.transform.rotate(self.image, self.FINALROTATION)
            if self.masked:
                self.rotatedMask = pygame.transform.rotate(self.tintMask, self.FINALROTATION)

        if self.masked:
            rot_norm = ((self.FINALROTATION+65) % 45) / 45.0
            temp = apply_light_bounce(self.rotatedMask, rot_norm)
            self.rotatedImage.blit(temp, (0,0))

        
    def render(self):
        if not hasattr(self, "rotatedImage"):
            return
        self.app.DRAWTO.blit(self.rotatedImage, self.app.convertPos(self.BLITPOS) - v2(self.rotatedImage.get_size()) / 2)


        #p = self.getBulletSpawnPoint()
        #pygame.draw.circle(self.app.screen, [255,0,0], p, 10)