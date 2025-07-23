import pygame
from imageProcessing import gaussian_blur, trim_surface, remove_background
from pygame.math import Vector2 as v2
import math
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn import Pawn
import random
from bullet import Bullet

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


class Weapon:
    def __init__(self, app: "Game", name: str, *args, owner=None, precomputedImage=None):
        """
        Initialize the Weapon object.
        :param args: Arguments for the weapon, including app, name, image_path, damage, and range.
        :param owner: The Pawn object that owns this weapon.
        :param precomputedImage: Optional precomputed image to avoid loading it again.
        """
        print("Initializing weapon with args:", args)
        self.args = args
        image_path, damage, range, magSize, fireRate, fireFunction, reloadTime, typeD = args
        self.app = app
        self.name = name
        self.owner = owner
        self.typeD = typeD
        if not precomputedImage:
            print("Recomputing image for weapon:", name)
            self.image = pygame.image.load(image_path).convert_alpha()
            self.image = trim_surface(self.image)
            self.image = pygame.transform.scale_by(self.image, 150 / self.image.get_width())  # Scale the image to a suitable size
        else:
            self.image = precomputedImage

        self.imageR = pygame.transform.flip(self.image.copy(), True, False)

        self.imageKillFeed = pygame.transform.scale_by(self.image, 20 / self.image.get_height())

        self.damage = damage
        self.range = range
        self.magazineSize = magSize
        self.magazine = self.magazineSize
        self.reloadTime = reloadTime
        self.currReload = 0
        self.firerate = fireRate # PER SECOND
        self.secondsPerRound = 1/self.firerate
        self.fireTick = 0
        self.spread = 0.05

        self.recoil = 0

        self.fireFunction = fireFunction

        self.wobbleRotation = 0
        self.wobbleVel = 0

        self.FINALROTATION = 0
        self.ROTATION = 0
        self.ROTATIONVEL = 0
        self.barrelOffset = v2(75, 0)

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
        print("Giving weapon:", self.name, "to", pawn.name)

        # This creates a memory leak if the weapon is given to multiple pawns?
        pawn.weapon = Weapon(self.app, self.name, *self.args, owner=pawn, precomputedImage=self.image.copy())  # Pass the image as a precomputed image

        print(f"{self.name} given to {pawn.name}")

    def reload(self):
        self.currReload = self.reloadTime * self.owner.itemEffects["weaponReload"]
        self.magazine = int(self.magazineSize * self.owner.itemEffects["weaponAmmoCap"])
        self.app.reloadSound.play()


    def RocketLauncher(self):
        if self.isReloading(): return
                    
        if self.magazine == 0:
            self.reload()
            return
        
        if self.fireTick > 0:
            self.fireTick -= self.app.deltaTime
            return
        if not self.pointingAtTarget(): return
        self.magazine -= 1

        secondsPerRound = 1/(self.firerate * self.owner.itemEffects["weaponFireRate"])

        self.fireTick = secondsPerRound
        r = self.app.getAngleFrom(self.owner.pos, self.owner.target.pos)
        Bullet(self.owner, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.5, damage = self.getDamage(), rocket=True, type=self.typeD) #-math.radians(self.FINALROTATION)
        self.recoil += 0.25


    def getSpread(self):
        return (self.spread + self.recoil * 0.5) * self.owner.itemEffects["accuracy"]

    def getDamage(self):
        return self.damage * self.owner.itemEffects["weaponDamage"]

    def AKshoot(self):
        if self.isReloading(): return
                    
        if self.magazine == 0:
            self.reload()
            return
        
        if self.fireTick > 0:
            self.fireTick -= self.app.deltaTime
            return

        if not self.pointingAtTarget(): return

        for x in self.app.ARSounds:
            x.stop()

        random.choice(self.app.ARSounds).play()
        self.magazine -= 1
        self.fireTick = self.secondsPerRound
        r = self.app.getAngleFrom(self.owner.pos, self.owner.target.pos)
        Bullet(self.owner, self.getBulletSpawnPoint(), r, spread = self.spread + self.recoil * 0.5, damage = self.getDamage(), type=self.typeD) #-math.radians(self.FINALROTATION)
        self.recoil += 0.25

    def pointingAtTarget(self):
        if self.owner.target:
            r = -math.degrees(self.app.getAngleFrom(self.owner.pos, self.owner.target.pos))
            if abs(angle_diff(self.ROTATION, r)) > 30:
                return False

        return True


    def tick(self):

        if self.isReloading():
            self.currReload -= self.app.deltaTime

        # image is rotated 45 degrees to resemble lowering a weapon

        ownerBreathe = math.cos(self.owner.breatheI * math.pi)
        ownerBreathe2 = math.sin(self.owner.breatheI * math.pi)

        rotationMod = ownerBreathe*5 - self.owner.rotation*0.5


        if self.owner.target and not self.isReloading():
            r = math.degrees(self.app.getAngleFrom(self.owner.pos, self.owner.target.pos))
        else:
            r = 135 if self.owner.facingRight else 45

        if self.isReloading():
            r2 = reload_rotation((self.reloadTime - self.currReload)/self.reloadTime) * 1.4

            r += r2 if self.owner.facingRight else -r2

        #m = v2(pygame.mouse.get_pos())
        
        #r = math.degrees(self.app.getAngleFrom(self.owner.pos, m))
        

        rotation = -r + rotationMod

        self.recoil *= 0.97
        
        rotation = self.app.rangeDegree(rotation)

        RGAIN = 1000 * self.owner.itemEffects["weaponHandling"]

        # Calculate the rotation factor using proper units
        rotation_factor = self.app.smoothRotationFactor(
            self.ROTATIONVEL,  # Current angular velocity (no deltaTime here)
            RGAIN,               # Gain factor - acceleration rate (no deltaTime here)
            angle_diff(self.ROTATION, rotation)  # Angle difference
        )

        # Apply the acceleration to velocity
        self.ROTATIONVEL += rotation_factor * self.app.deltaTime

        # Apply velocity to position
        self.ROTATION += self.ROTATIONVEL * self.app.deltaTime
        self.ROTATION = self.app.rangeDegree(self.ROTATION)

        if 90 <= self.ROTATION <= 270:
            self.FINALROTATION = self.ROTATION - self.recoil * 30
            self.rotatedImage = pygame.transform.rotate(self.imageR, self.FINALROTATION + 180)
            r = True
        else:
            self.FINALROTATION = self.ROTATION + self.recoil * 30
            self.rotatedImage = pygame.transform.rotate(self.image, self.FINALROTATION)
            r = False

        

        # Update the weapon's image

        # Backward movement (opposite to weapon direction)
        recoilBackwardOffset = v2(-self.recoil * 30, 0).rotate(-self.ROTATION)

        # Upward movement (perpendicular to weapon, always "up" relative to weapon)
        recoilUpwardOffset = v2(0, -self.recoil * 10)

        # Combined recoil offset
        recoilOffset = recoilBackwardOffset + recoilUpwardOffset
        
        swiwelOffset = self.getSwiwel()

        self.BLITPOS = self.owner.deltaPos - v2(self.rotatedImage.get_size()) / 2 + [0.5*self.owner.xComponent, -0.25*self.owner.yComponent + ownerBreathe2*5] + [0, 40] + recoilOffset + swiwelOffset
        
    def render(self):
        self.app.DRAWTO.blit(self.rotatedImage, self.BLITPOS - self.app.cameraPosDelta)


        #p = self.getBulletSpawnPoint()
        #pygame.draw.circle(self.app.screen, [255,0,0], p, 10)