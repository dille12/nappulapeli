import pygame
from imageprocessing.imageProcessing import gaussian_blur, trim_surface, remove_background
from pygame.math import Vector2 as v2
import math
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
import random
from utilities.bullet import Bullet, line_intersects_rect
from particles.laser import ThickLaser
from utilities.explosion import Explosion
import io, base64
def surface_to_base64(surface: pygame.Surface) -> str:
    buf = io.BytesIO()
    pygame.image.save(surface, buf, "PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return b64  # Just the base64, no prefix

def angle_diff(a, b):
    diff = (b - a + 180) % 360 - 180
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


class Weapon:
    def __init__(self, app: "Game", name: str, price: list, *args, owner: "Pawn" = None, precomputedImage=None, sizeMult = 1):
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

        

        if not precomputedImage:
            print("Recomputing image for weapon:", name)
            self.image = pygame.image.load(image_path).convert_alpha()
            if image_path == "texture/ak47.png":
                self.image = trim_surface(self.image)
            self.image = pygame.transform.scale_by(self.image, (150*sizeMult) / self.image.get_width())  # Scale the image to a suitable size
        else:
            self.image = precomputedImage


        self.shopIcon = pygame.transform.scale_by(self.image.copy(), 100 / self.image.get_height()) 
        self.shopIcon = trim_surface(self.shopIcon)


        if image_path == "texture/skull.png":
            self.image = pygame.transform.scale_by(self.image, 36 / self.image.get_width())

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

        self.burstRounds = 3
        self.burstI = 0.3/3
        self.currBurstRounds = 0
        self.currBurstI = 0

        self.FINALROTATION = 0
        self.ROTATION = 0
        self.ROTATIONVEL = 0
        self.barrelOffset = v2(75, 0) * sizeMult

        self.lazerActive = False
        self.lazerTimer = 0

    def getPacket(self):
        p = {"name": self.name,
             "price": self.price[0],
             "image": self.encodedImage}
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
        
        weaponWorldPos = (self.owner.deltaPos + 
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
        pawn.weapon = Weapon(self.app, self.name, self.price, *self.args, owner=pawn, precomputedImage=self.image.copy())  # Pass the image as a precomputed image


    def reload(self):
        self.currReload = self.getReloadTime()
        self.magazine = self.owner.getMaxCapacity()
        self.app.reloadSound.stop()
        self.app.reloadSound.play()


    
    

    def RocketLauncher(self):
        if not self.canShoot(): return

        self.magazine -= 1

        self.app.playSound(self.app.rocketSound)
        

        self.fireTick = self.owner.getRoundsPerSecond()
        r = math.radians(-self.ROTATION)

        gun_x, gun_y = self.getBulletSpawnPoint()
        pierce = self.owner.itemEffects["piercing"]
        homing = self.owner.itemEffects["homing"]
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        for x in range(self.owner.itemEffects["multiShot"]):
            Bullet(self.owner, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.25, damage = self.owner.getDamage(), rocket=True, type=self.typeD, piercing=pierce, homing=homing) #-math.radians(self.FINALROTATION)
            self.addRecoil(0.4)
        self.addRecoil(3)


    def addRecoil(self, amount):
        self.recoil += amount / self.owner.itemEffects["recoilMult"]

    
    def skull(self):
        self.magazine = self.getMaxCapacity()
        return
    
    def Energyshoot(self):
        if not self.canShoot(): return

        self.app.playSound(self.app.energySound)
        self.magazine -= 1
        self.fireTick = self.owner.getRoundsPerSecond()

        r = math.radians(-self.ROTATION)
        gun_x, gun_y = self.getBulletSpawnPoint()
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        for x in range(self.owner.itemEffects["multiShot"]):
            self.createBullet(0.2)


    def BFGshoot(self):

        if self.lazerActive:

            if self.isReloading() or self.meleeing():
                self.lazerActive = False
                return

            startPos = self.getBulletSpawnPoint()
            endPos = [
                startPos[0] + math.cos(math.radians(-self.ROTATION)) * self.range,
                startPos[1] + math.sin(math.radians(-self.ROTATION)) * self.range
            ]
            
            self.app.BFGLasers.append([startPos, endPos])
            
            self.lazerTimer -= self.app.deltaTime
            if self.lazerTimer <= 0:
                self.lazerTimer += 0.04  # Reset timer

                self.magazine -= 1
                if self.magazine <= 0:
                    self.lazerActive = False
                    self.reload()
                    return
                
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
                            self.owner.getDamage(),  # fixed time step damage
                            fromActor=self.owner,
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

    def getMeleeTime(self):
        return 0.5 / max(self.owner.getHandling(), 0.1)
    
    

    def tryToMelee(self):
        if self.meleeing(): return

        self.meleeI = self.getMeleeTime()
        t = self.owner.target.pos.copy()

        self.owner.target.takeDamage(50*self.owner.itemEffects["meleeDamage"], fromActor = self.owner)

        if self.owner.itemEffects["detonation"]:
            Explosion(self.app, t, self.owner, 100)


        if self.owner.onScreen():
            self.app.meleeSound.stop()
            self.app.meleeSound.play()


    def suppressedShoot(self):
        self.AKshoot(sounds = self.app.silencedSound)

    def smgShoot(self):
        self.AKshoot(sounds = self.app.smgSound)

    def pistolShoot(self):
        self.AKshoot(sounds = self.app.pistolSound)


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
                self.currBurstI += self.burstI * self.owner.getFireRateMod()
                self.currBurstRounds -= 1
                self.currBurstRounds = max(0, self.currBurstRounds)

                r = math.radians(-self.ROTATION)
                gun_x, gun_y = self.getBulletSpawnPoint()
                self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

                for x in range(self.owner.itemEffects["multiShot"]):
                    self.createBullet(0.25)
                self.magazine -= 1
                self.fireTick += self.owner.getRoundsPerSecond()
                self.app.playSound(self.app.ARSounds)
            
            self.currBurstI -= self.app.deltaTime
            


    def createBullet(self, recoil):
        r = math.radians(-self.ROTATION)
        pierce = self.owner.itemEffects["piercing"]
        homing = self.owner.itemEffects["homing"]
        Bullet(self.owner, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.25, damage = self.owner.getDamage(), type=self.typeD, piercing=pierce, homing=homing) #-math.radians(self.FINALROTATION)
        self.addRecoil(recoil)



    def shotgunShoot(self):
        

        if not self.canShoot(): return

        self.app.playSound(self.app.shotgunSound)

        

        self.magazine -= 1
        self.fireTick = self.owner.getRoundsPerSecond()
        r = math.radians(-self.ROTATION)
        gun_x, gun_y = self.getBulletSpawnPoint()
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        pierce = self.owner.itemEffects["piercing"]
        homing = self.owner.itemEffects["homing"]
        for x in range(10*self.owner.itemEffects["multiShot"]):
            Bullet(self.owner, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.25, damage = self.owner.getDamage(), type=self.typeD, piercing=pierce, homing=homing) #-math.radians(self.FINALROTATION)
            self.addRecoil(0.15)


    def checkIfCanAddFireRate(self):
        if not self.owner.target: return False
        if not self.owner.sees(self.owner.target): return False
        if self.meleeing(): return False
        if self.isReloading(): return False
        if not self.pointingAtTarget(): return False
        if self.magazine == 0: return False
        return True

    def canShoot(self):
        if self.meleeing(): return False
     
        if self.isReloading(): return False
                    
        if self.magazine == 0:
            self.reload()
            return False
        
        if self.fireTick > 0:
            self.fireTick -= self.app.deltaTime
            return False

        if not self.pointingAtTarget(): return False

        return True


    def AKshoot(self, sounds = None):
        
        if not self.canShoot(): return
        
        if not sounds:
            sounds = self.app.ARSounds

        self.app.playSound(sounds)

        self.magazine -= 1
        self.fireTick = self.owner.getRoundsPerSecond()


        r = math.radians(-self.ROTATION)
        gun_x, gun_y = self.getBulletSpawnPoint()
        self.app.particle_system.create_muzzle_flash(gun_x, gun_y, r)

        for x in range(self.owner.itemEffects["multiShot"]):
            self.createBullet(0.25)

    def pointingAtTarget(self):
        if self.owner.target:
            r = -math.degrees(self.app.getAngleFrom(self.owner.pos, self.owner.target.pos))
            if abs(angle_diff(self.ROTATION, r)) > 30:
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

        if self.isReloading() or self.meleeing():
            return False
        
        if self.owner.pos.distance_to(self.owner.walkTo) < 500 and not self.owner.route:
            return False
        
        if self.owner.route and len(self.owner.route) < 5:
            return False

        return True
    

    def addFireRate(self):
        if self.checkIfCanAddFireRate(): 
            self.addedFireRate += self.owner.itemEffects["fireRateIncrease"] * self.app.deltaTime
        else:
            self.addedFireRate -= self.owner.itemEffects["fireRateIncrease"] * self.app.deltaTime

        self.addedFireRate = max(0, self.addedFireRate)


    def tick(self):

        if self.meleeing():
            self.meleeI -= self.app.deltaTime

        elif self.isReloading():
            self.currReload -= self.owner.getReloadAdvance()

        self.addFireRate()

        # image is rotated 45 degrees to resemble lowering a weapon

        ownerBreathe = math.cos(self.owner.breatheI * math.pi)
        ownerBreathe2 = math.sin(self.owner.breatheI * math.pi)

        rotationMod = ownerBreathe*5 - self.owner.rotation*0.5

        if self.owner.target and not self.isReloading():
            r = math.degrees(self.app.getAngleFrom(self.owner.pos, self.owner.target.pos))
            self.runOffset -= (self.app.deltaTime * self.owner.getHandling()*2)
        else:
            if self.raiseWeaponWhileRunning():
                if self.name not in ["Skull", "Glock", "USP-S"]:
                    r = -110 if self.owner.facingRight else -70
                else:
                    r = 135 if self.owner.facingRight else 45
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

        xA, yA, rA = 0,0,0
        if self.meleeing():
            xA, yA, rA = melee_animation((self.getMeleeTime()-self.meleeI)/self.getMeleeTime())

            #r += rA #if self.owner.facingRight else -rA

        elif self.isReloading():
            r2 = reload_rotation((self.getReloadTime() - self.currReload)/self.getReloadTime()) * 1.4

            r += r2 if self.owner.facingRight else -r2

        

        rotation = -r + rotationMod

        self.recoil *= 0.97 ** (self.app.deltaTime*144)

        
        rotation = self.app.rangeDegree(rotation)

        RGAIN = 1000 * self.owner.getHandling()

        DIFF = angle_diff(self.ROTATION, rotation)
        if self.owner.itemEffects["noscoping"] and DIFF < -20:
            DIFF += 360

        # Calculate the rotation factor using proper units
        rotation_factor = self.app.smoothRotationFactor(
            self.ROTATIONVEL,  # Current angular velocity (no deltaTime here)
            RGAIN,               # Gain factor - acceleration rate (no deltaTime here)
            DIFF  # Angle difference
        )

        # Apply the acceleration to velocity
        self.ROTATIONVEL += rotation_factor * self.app.deltaTime

        # Apply velocity to position
        self.ROTATION += self.ROTATIONVEL * self.app.deltaTime
        self.ROTATION = self.app.rangeDegree(self.ROTATION)

        if 90 <= self.ROTATION <= 270:
            self.FINALROTATION = self.ROTATION - self.recoil * 30 - rA
            self.rotatedImage = pygame.transform.rotate(self.imageR, self.FINALROTATION + 180)
            right = True
        else:
            self.FINALROTATION = self.ROTATION + self.recoil * 30 + rA
            self.rotatedImage = pygame.transform.rotate(self.image, self.FINALROTATION)
            right = False

        

        # Update the weapon's image

        # Backward movement (opposite to weapon direction)
        recoilBackwardOffset = v2(-self.recoil * 30, 0).rotate(-self.ROTATION)

        # Upward movement (perpendicular to weapon, always "up" relative to weapon)
        recoilUpwardOffset = v2(0, -self.recoil * 10)

        # Combined recoil offset
        recoilOffset = recoilBackwardOffset + recoilUpwardOffset

        if self.name not in ["Glock", "USP-S", "Skull"]:
            yA -= self.runOffset*50
            runOffset = self.runOffset*30
        else:
            runOffset = 0


        if right:
            meleeOffset = v2(-xA + runOffset, yA)
        else:
            meleeOffset = v2(xA - runOffset, yA)
        
        swiwelOffset = self.getSwiwel()

        self.BLITPOS = self.owner.deltaPos - v2(self.rotatedImage.get_size()) / 2 + [0.5*self.owner.xComponent, -0.25*self.owner.yComponent + ownerBreathe2*5] + [0, 40] + recoilOffset + swiwelOffset + meleeOffset
        
    def render(self):
        if not hasattr(self, "rotatedImage"):
            return
        self.app.DRAWTO.blit(self.rotatedImage, self.BLITPOS - self.app.cameraPosDelta)


        #p = self.getBulletSpawnPoint()
        #pygame.draw.circle(self.app.screen, [255,0,0], p, 10)