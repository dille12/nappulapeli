from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
import random
import math
from pygame.math import Vector2 as v2

def ult_multiplier(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        return result * 3 if self.ULT else result
    return wrapper

def ult_division(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        return result / 3 if self.ULT else result
    return wrapper

class getStat:
    def __init__(self: "Pawn"):
        pass


    @ult_multiplier
    def getSpeed(self):
        s = self.speed * self.itemEffects["speedMod"] * (1 + 0.5*self.weapon.runOffset)
        if self.revengeHunt():
            s *= 2
        return s
    
    @ult_multiplier
    def getRegenRate(self):
        return self.healthRegen * self.itemEffects["healthRegenMult"]
    
    def thorns(self):
        return self.itemEffects["thorns"]
    
    def getHealthCap(self):
        if self.enslaved:
            return 25
        return self.healthCap * self.itemEffects["healthCapMult"]
    
    @ult_multiplier
    def getWeaponHandling(self):
        return self.itemEffects["weaponHandling"]
    def getRange(self):
        if self.carryingSkull():
            return self.skullWeapon.range * self.itemEffects["weaponRange"]
        return self.weapon.range * self.itemEffects["weaponRange"]
    
    def revengeHunt(self):
        return self.itemEffects["revenge"] and self.lastKiller and not self.lastKiller.killed and not self.app.PEACEFUL
    
    @ult_multiplier
    def defenceNormal(self):
        s = self.itemEffects["defenceNormal"]
        if self.revengeHunt():
            s *= 5
        return s
    
    @ult_multiplier
    def defenceEnergy(self):
        s = self.itemEffects["defenceEnergy"]
        if self.revengeHunt():
            s *= 5
        return s
    
    @ult_multiplier
    def defenceExplosion(self):
        s = self.itemEffects["defenceExplosion"]
        if self.revengeHunt():
            s *= 5
        return s
    
    def getSpread(self):
        return (self.weapon.spread + self.weapon.recoil * 0.5) / self.itemEffects["accuracy"]

    @ult_multiplier
    def getDamage(self):
        return self.weapon.damage * self.itemEffects["weaponDamage"]
    
    @ult_multiplier
    def getMaxCapacity(self):
        return int(self.weapon.magazineSize * self.itemEffects["weaponAmmoCap"])

    @ult_division
    def getRoundsPerSecond(self):
        return 1/((self.weapon.firerate+self.weapon.addedFireRate) * self.itemEffects["weaponFireRate"])
    
    @ult_multiplier
    def getHandling(self):
        return self.itemEffects["weaponHandling"]
    
    @ult_multiplier
    def getReloadAdvance(self):
        return self.app.deltaTime * self.itemEffects["weaponReload"]