from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
    from pawn.weapon import Weapon
import random
import math
from pygame.math import Vector2 as v2

def ult_multiplier(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)

        if self.NPC and not self.BOSS:
            result *= 0.75

        return result * 3 if self.ULT else result
    return wrapper

def ult_division(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)

        if self.NPC and not self.BOSS:
            result *= 1.25

        return result / 3 if self.ULT else result
    return wrapper

class getStat:
    def __init__(self: "Pawn"):
        self.itemEffects = {
            "speedMod": 1.0, # Done
            "healthRegenMult": 1.0,
            "thorns": 0.0,
            "healthCapMult": 1.0,
            
            "weaponHandling" : 1.0,
            "weaponDamage" : 1.0,
            "weaponReload" : 1.0,
            "weaponFireRate" : 1.0,
            "weaponAmmoCap" : 1.0,
            "weaponRange": 1.0,
            "accuracy": 1.0,
            "multiShot" : 1,
            "recoilMult": 1.0,
            "meleeDamage": 1.0,
            
            "saveChance" : 0.0,
            "fireRateIncrease" : 0,
            "lifeSteal": 0.0,
            "tacticalSprintSpeed": 1.0,
            "defenceNormal" : 1.0,
            "defenceEnergy" : 1.0,
            "defenceExplosion" : 1.0,
            "tripChance": 0.0,
            "shitChance": 0.0,
            "dodgeChance": 0.0,
            "xpMult":1.0,
            "healOnKill":0,
            "knockbackMult":1.0,
            "healAllies":0,
            "timeScale": 1.0,
            "utilityUsage": 1.0,

            "berserker" : False,
            "martyrdom" : False,
            
            "instaHeal" : False,
            "talking": False,
            "turnCoat" : False,
            "hat": False,
            "noscoping": False,
            "piercing": False,
            "detonation": False,
            
            "extraItem": False,  
            "homing": False,
            "playMusic": False,
            "magDump": False,
            "allyProtection" : False,
            "coward" : False,
            "revenge" : False,
            "duplicator" : False,
            "bossKiller" : False,
            "dualWield" : False,
        }

        self.effect_labels_fi = {
            "speedMod": "Nopeus",
            "healthRegenMult": "Elpymisnopeus",
            "thorns": "Piikit",
            "healthCapMult": "Maksimi HP",
            "berserker": "Berserkki",
            "martyrdom": "Marttyyri",

            "weaponHandling": "Aseen käsittely",
            "weaponDamage": "Aseen vahinko",
            "weaponReload": "Latausnopeus",
            "weaponFireRate": "Tulinopeus",
            "weaponAmmoCap": "Lipas",
            "weaponRange": "Kantama",
            "accuracy": "Tarkkuus",
            "multiShot": "Monilaukaus",
            "meleeDamage": "Lyöntivahinko",

            "instaHeal": "Pika-parannus",
            "saveChance": "Pelastumis-%",
            "fireRateIncrease": "Ajan myötä lisääntynyt tuli",
            "allyProtection": "Liittolaisten suoja",
            "coward": "Pelkuri",
            "revenge": "Kosto",
            "duplicator": "Kaksoiskappale",

            "defenceNormal": "Normaali puolustus",
            "defenceEnergy": "Energiapuolustus",
            "defenceExplosion": "Räjähdyssuoja",

            "timeScale": "Kellonopeus",
            "utilityUsage": "Kalusteiden käyttö",

            "dodgeChance": "Väistön todennäköisyys",
            "xpMult": "XP-kerroin",
            "healOnKill": "Parannus tapon yhteydessä",
            "knockbackMult": "Takaisku",
            "healAllies": "Liittolaisten parannus",
            "talking": "Puhuva",
            "turnCoat": "Petturi",
            "hat": "Hattu",
            "noscoping": "360",
            "recoilMult": "Rekyyli",
            "piercing": "Lävistävät luodit",
            "detonation": "Detonaatio",
            "tripChance": "Kaatumisen todennäköisyys",
            "extraItem": "Extraesine", 
            "homing": "Itseohjautuva",
            "shitChance": "Paskantamisen todennäköisyys",
            "playMusic": "Jytä",
            "magDump": "Lipas tyhjäksi",
            "lifeSteal": "Elämänimeminen",
            "tacticalSprintSpeed": "Taktinen juoksu",
            "bossKiller" : "Koodarikilleri",
            "dualWield" : "Dual wield",
        }

        self.effect_labels_en = {
            "speedMod": "Speed",
            "healthRegenMult": "Health Regeneration",
            "thorns": "Thorns",
            "healthCapMult": "Max HP",
            "berserker": "Berserker",
            "martyrdom": "Martyrdom",

            "weaponHandling": "Weapon Handling",
            "weaponDamage": "Weapon Damage",
            "weaponReload": "Reload Speed",
            "weaponFireRate": "Fire Rate",
            "weaponAmmoCap": "Magazine",
            "weaponRange": "Range",
            "accuracy": "Accuracy",
            "multiShot": "Multishot",
            "meleeDamage": "Melee Damage",

            "instaHeal": "Instant Heal",
            "saveChance": "Survival Chance",
            "fireRateIncrease": "Increasing Fire Rate",
            "allyProtection": "Ally Protection",
            "coward": "Coward",
            "revenge": "Revenge",
            "duplicator": "Duplicator",

            "defenceNormal": "Normal Defence",
            "defenceEnergy": "Energy Defence",
            "defenceExplosion": "Explosion Defence",

            "dodgeChance": "Dodge Chance",
            "xpMult": "XP Multiplier",
            "healOnKill": "Heal on Kill",
            "knockbackMult": "Knockback",
            "healAllies": "Heal Allies",
            "talking": "Talking",
            "turnCoat": "Turncoat",
            "hat": "Hat",
            "noscoping": "360",
            "recoilMult": "Recoil",
            "piercing": "Piercing Bullets",
            "detonation": "Detonation",
            "tripChance": "Trip Chance",
            "extraItem": "Extra Item",
            "homing": "Homing",
            "shitChance": "Shitting Chance",
            "playMusic": "Boombox",
        }

        super().__init__()


    @ult_multiplier
    def getSpeed(self, WEAPON: "Weapon"):
        s = self.speed * self.itemEffects["speedMod"] * (1 + 1.0 * WEAPON.runOffset * self.itemEffects["tacticalSprintSpeed"])  # 
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
            return self.healthCap * 0.5 * self.itemEffects["healthCapMult"]
        elif self.app.GAMEMODE == "SUDDEN DEATH":
            return self.healthCap * self.itemEffects["healthCapMult"] * 2
        return self.healthCap * self.itemEffects["healthCapMult"]
    
    @ult_multiplier
    def getWeaponHandling(self):
        return self.itemEffects["weaponHandling"]
    
    def getRange(self, WEAPON):

        return WEAPON.range * self.itemEffects["weaponRange"]
    
    def revengeHunt(self):

        if self.lastKiller and not self.team.hostile(self, self.lastKiller) and "allyProtection" in self.itemEffects:
            self.lastKiller = None
            
        return self.itemEffects["revenge"] and self.lastKiller and not self.lastKiller.killed and not self.app.PEACEFUL and self.flashed <= 0
    
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
    
    def getSpread(self, WEAPON):
        return (WEAPON.spread + WEAPON.recoil * 0.5) / self.itemEffects["accuracy"] # self.weapon.spread

    @ult_multiplier
    def getDamage(self, WEAPON):
        return WEAPON.damage * self.itemEffects["weaponDamage"] # self.weapon.damage
    
    @ult_multiplier
    def getMaxCapacity(self, WEAPON):
        return int(WEAPON.magazineSize * self.itemEffects["weaponAmmoCap"]) #self.weapon.magazineSize
    
    @ult_multiplier
    def getFireRateMod(self):
        return 1 / self.itemEffects["weaponFireRate"]

    @ult_division
    def getRoundsPerSecond(self, WEAPON):
        return 1/((WEAPON.firerate + WEAPON.addedFireRate) * self.itemEffects["weaponFireRate"]) # Added firerate self.weapon.firerate+self.weapon.addedFireRate
    
    @ult_multiplier
    def getHandling(self):
        return self.itemEffects["weaponHandling"]
    
    @ult_multiplier
    def getReloadAdvance(self):
        return self.app.deltaTime * self.itemEffects["weaponReload"]