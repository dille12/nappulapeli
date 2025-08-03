from rembg import remove
from PIL import Image
import io
import pygame
from pygame.math import Vector2 as v2
import random
import os
import math
import numpy as np
from imageprocessing.imageProcessing import gaussian_blur, trim_surface, remove_background, generate_corpse_sprite, set_image_hue_rgba, colorize_to_blood
from particles.blood import BloodParticle
from killfeed import KillFeed
from utilities.explosion import Explosion
from particles.bloodSplatter import BloodSplatter
from imageprocessing.pixelSort import pixel_sort_surface
from imageprocessing.faceMorph import getFaceLandMarks, processFaceMorph
from _thread import start_new_thread
import json
import subprocess
from utilities.dialog import onKill, onDeath, onTarget, onTakeDamage, onTeamDamage, onTeamKill, onOwnDamage
import re
from utilities.infoBar import infoBar
import time
import subprocess
import re
from _thread import start_new_thread
import subprocess
import tempfile
import pygame
import os
from _thread import start_new_thread
from pawn.weapon import Weapon
from typing import TYPE_CHECKING
from particles.particle import Particle
if TYPE_CHECKING:
    from main import Game


def ult_multiplier(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        return result * 2 if self.ULT else result
    return wrapper

def ult_division(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        return result / 2 if self.ULT else result
    return wrapper

class EspeakTTS:
    def __init__(self, owner: "Pawn", speed=175, pitch=50, voice="fi"):
        self.speed = str(speed)
        self.pitch = str(pitch)
        self.voice = voice
        self.owner = owner
        self.app: "Game" = owner.app
        self.current_path = None
        self.sound = None
        self.generating = False

    def say(self, text):

        if not self.app.TTS_ON:
            return
        if self.generating:
            return
        if self.app.speeches > 1:
            return
        if self.owner.textBubble or self.sound:
            return
        
        self.generating = True
        
        #self.stop()

        start_new_thread(self.threaded, (text, ))

    def threaded(self, text):
        self.app.speeches += 1
        self.owner.textBubble = text
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                wav_path = tmp.name
            subprocess.run([
                "espeak",
                "-s", self.speed,
                "-p", self.pitch,
                "-v", self.voice,
                "-w", wav_path,
                text
            ], check=True)

            self.sound = pygame.mixer.Sound(wav_path)
            self.generating = False
            self.sound.play()
            while True:
                if not self.sound:
                    break
                if self.sound.get_num_channels():
                    pygame.time.wait(100)
                else:
                    break

        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
            self.owner.textBubble = None
            self.app.speeches -= 1
            self.sound = None

    def stop(self):
        if self.generating:
            return

        if self.sound:
            self.sound.stop()
            self.owner.textBubble = None


def load_landmarks_cache(app, cache_path="landmarks_cache.json"):
    with app.cacheLock:
        if os.path.isfile(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

def save_landmarks_cache(app, data, cache_path="landmarks_cache.json"):
    with app.cacheLock:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

def get_or_load_landmarks(app, name, rgb, cache_path="landmarks_cache.json"):
    initial_cache = load_landmarks_cache(app, cache_path)

    if name in initial_cache:
        print(f"Loading landmarks for '{name}' from cache")
        return np.array(initial_cache[name]) if initial_cache[name] is not None else np.array(None)

    print(f"Detecting landmarks for '{name}'")
    try:
        landmarks = getFaceLandMarks(rgb)
        new_data = landmarks.tolist()
    except:
        landmarks = np.array(None)
        new_data = None

    # Reload latest cache just before writing to avoid overwriting updates
    latest_cache = load_landmarks_cache(app, cache_path)
    latest_cache[name] = new_data
    save_landmarks_cache(app, latest_cache, cache_path)
    
    return landmarks

def debug_draw_alpha(surface):
    alpha_arr = pygame.surfarray.array_alpha(surface)
    alpha_rgb = np.stack([alpha_arr]*3, axis=-1)
    debug_surface = pygame.surfarray.make_surface(alpha_rgb)
    return debug_surface

def get_apex_pixel_mean(surface: pygame.Surface, threshold=1, min_pixels=3, max_spread=20):
    arr = pygame.surfarray.array_alpha(surface)

    for y in range(arr.shape[0]):
        row = arr[y]
        visible = row >= threshold
        count = np.count_nonzero(visible)
        
        if count >= min_pixels:
            xs = np.where(visible)[0]
            
            # Check if pixels are reasonably clustered (not too spread out)
            if True:
                x_mean = int(xs.mean())
                print(f"Row {y}: {count} visible pixels, x_mean={x_mean}")
                return x_mean - arr.shape[1]/2, y - arr.shape[0]/2

    print("No valid apex found.")
    return None






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
    def __init__(self, app: "Game", cardPath):
        self.app: "Game" = app
        self.cardPath = cardPath
        # extract the name from the path
        self.name = cardPath.split("/")[-1].split(".")[0]

        info = infoBar(self.app, f"{self.name}: Generating")

        self.removeBGPath = "player_images_removed/" + self.name + ".png"
        if not os.path.exists(self.removeBGPath):
            print("NEW PAWN INBOUND")
            info.text = f"{self.name}: Removing bg"
            remove_background(cardPath, self.removeBGPath)
            
            image = pygame.image.load(self.removeBGPath).convert_alpha()
        else:
            image = pygame.image.load(self.removeBGPath).convert_alpha()
            
        self.textBubble = None

        image = trim_surface(image)


        self.defaultPos()


        self.NPC = random.choice((True, True, False))

        self.left_eye_center = v2(0,0)
        self.right_eye_center = v2(0,0)


        self.imagePawn = pygame.transform.scale_by(image, 100 / image.get_size()[1]).convert_alpha()
        #self.imagePawn = debug_draw_alpha(self.imagePawn).convert_alpha()

        self.imagePawnR = pygame.transform.flip(self.imagePawn.copy(), True, False).convert_alpha()

        self.apexPawn = v2([0, -self.imagePawn.get_height()/2])
        #self.apexPawn = v2(get_apex_pixel_mean(self.imagePawn, threshold=2))
        

        pygame.draw.circle(self.imagePawn, [255,0,0], self.apexPawn, 10)
        
        

        self.hurtPawn = colorize_to_blood(self.imagePawn.copy()).convert_alpha()
        self.hurtPawnR = pygame.transform.flip(self.hurtPawn.copy(), True, False).convert_alpha()
        info.text = f"{self.name}: Hurting"
        self.hurtIm = [[], []]
        for x in range(10):
            h1 = self.hurtPawn.copy()
            h2 = self.hurtPawnR.copy()
            h1.set_alpha(int(255*x/10))
            h2.set_alpha(int(255*x/10))
            self.hurtIm[0].append(h1)
            self.hurtIm[1].append(h2)

        self.hurtI = 0
        info.text = f"{self.name}: Making corpses"
        self.corpses = []
        for x in range(3):
            corpse = generate_corpse_sprite(self.imagePawn.copy())
            corpse.set_alpha(155)
            corpse = pygame.transform.rotate(corpse, random.randint(0,360))
            self.corpses.append(corpse)

        self.levelUpImage = pygame.transform.scale_by(image, 400 / image.get_size()[1])
        info.text = f"{self.name}: Morphing"
        self.levelUpImage = self.morph(self.levelUpImage)



        #pygame.draw.circle(self.imagePawn, [255,0,0], self.left_eye_center*100, 5)
        #pygame.draw.circle(self.imagePawn, [255,0,0], self.right_eye_center*100, 5)

        self.hudImage = pygame.transform.scale_by(self.levelUpImage.copy(), 200 / self.levelUpImage.get_size()[1])

        info.text = f"{self.name}: Pixel sorting"
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
        self.thinkEvery = 0.5 # seconds
        self.thinkI = random.uniform(0, self.thinkEvery)
        self.walkTo = None
        self.route = None
        self.speed = 400
        self.stepI = 0 

        self.takeStepEvery = 0.5
        self.lastStep = -1
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
        self.pastItems = []
        self.getNextItems()

        self.xp = 0
        self.xpI = 15

        self.weapon: Weapon = None
        
        self.app.skullW.give(self)
        self.skullWeapon = self.weapon

        self.cameraLockI = 0
        self.onCameraTime = 0

        info.text = f"{self.name}: Giving a weapon"
        weapon = random.choice(self.app.weapons)
        weapon = self.app.pistol2

        weapon.give(self)  # Give the AK-47 to this pawn
        self.app.pawnHelpList.append(self)

        self.kills = 0
        self.killsThisLife = 0
        self.level = 1
        self.levelUpCreatedFor = 0
        self.deaths = 0
        self.teamKills = 0
        self.suicides = 0

        self.turnCoatI = 0

        self.tts = EspeakTTS(self, random.randint(120,300), random.randint(0,100), voice="fi")
        
        self.ULT = False
        self.ULT_TIME = 0

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
            "meleeDamage": 1.0,
            "recoilMult": 1.0,
            

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
            "healOnKill":0,
            "knockbackMult":1.0,
            "healAllies":0,
            "talking": False,
            "turnCoat" : False,
            "hat": False,
            "noscoping": False,
            "piercing": False,
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
        }


        self.referenceEffects = self.itemEffects.copy()

        info.text = f"{self.name}: Done!"
        info.killed = True

        #for x in range(3):
        #    i = random.choice(self.app.items)
        #    i.apply(self)


    def defaultPos(self):
        if random.randint(0, 1) == 0:
            self.pos = v2(random.randint(0, 1920), random.choice([-200, self.app.res[1] + 200]))
        else:
            self.pos = v2(random.choice([-200, self.app.res[0] + 200]), random.randint(0, 1080))
        self.deltaPos = self.pos.copy()

    def onScreen(self):
        r = pygame.Rect(self.app.cameraPosDelta, self.app.res)
       
        r2 = pygame.Rect(self.app.cameraLockTarget, (0,0))
        r2.inflate_ip(self.app.res)

        DUAL = False
        if self.app.splitI > 0:
            if self.app.cameraLockOrigin.distance_to(self.app.cameraLockTarget) > 600:
                DUAL = True

        if not r.collidepoint(self.pos) and not (r2.collidepoint(self.pos) and DUAL):
            return False
        return True

    def say(self, t, chanceToSay = 0.2):
        if not self.itemEffects["talking"]:
            return
        
        if not self.onScreen():
            return
        
        if random.uniform(0,1) >= chanceToSay:
            return
        self.tts.say(t)


    def morph(self, image):
        rgb = pygame.surfarray.array3d(image).swapaxes(0, 1)
        alpha = pygame.surfarray.array_alpha(image)

        landMarks = get_or_load_landmarks(self.app, self.name, rgb)
        print("LandMarkType:", type(landMarks))
        if landMarks.dtype == object and landMarks.size == 1 and landMarks[()] is None:
            print(self.name, "No morph!!!")
            self.morphed = False
            print(landMarks)
            print("nää ei jostain syystä käyny")
            return image
        
        # Left eye (landmarks 36-41)
        left_eye_points = landMarks[36:42]
        left_eye_center = left_eye_points.mean(axis=0)
        self.left_eye_center = v2(left_eye_center[0], left_eye_center[1]) / 400
        # Right eye (landmarks 42-47)  
        right_eye_points = landMarks[42:48]
        right_eye_center = right_eye_points.mean(axis=0)
        self.right_eye_center = v2(right_eye_center[0], right_eye_center[1]) / 400
        self.eyeMirror = v2(image.get_width()/image.get_height(), 0)

        result = processFaceMorph(rgb, landMarks, smileIntensity=8, eyeScale=2)
        surface_array = result.swapaxes(0, 1).astype(np.uint8)

        # Ensure alpha matches dimensions
        if alpha.shape != surface_array.shape[:2]:
            alpha = np.resize(alpha, surface_array.shape[:2])

        alpha = alpha.astype(np.uint8)

        # Create surface with alpha support
        surface_out = pygame.Surface(surface_array.shape[:2], flags=pygame.SRCALPHA, depth=32)

        # Blit the RGB data first (only 3 channels)
        pygame.surfarray.blit_array(surface_out, surface_array)

        # Then apply the alpha channel separately
        alpha_array = pygame.surfarray.pixels_alpha(surface_out)
        alpha_array[:] = alpha  # Note the transpose - pygame uses (width, height) while numpy uses (height, width)
        del alpha_array  # Release the pixel array lock
        self.morphed = True
        IMAGE = surface_out.convert_alpha()
        return IMAGE
    
    def getEyePositions(self):
        if self.facingRight:
            return self.left_eye_center*100, self.right_eye_center*100
        else:

            LEFT = v2(self.eyeMirror[0] - self.left_eye_center[0], self.left_eye_center[1])*100
            RIGHT = v2(self.eyeMirror[0] - self.right_eye_center[0], self.right_eye_center[1])*100

            return LEFT, RIGHT
        
    


    @ult_multiplier
    def getSpeed(self):
        s = self.speed * self.itemEffects["speedMod"] * (1 + 0.5*self.weapon.runOffset)
        if self.revengeHunt():
            s *= 2
        return s
    

    def getRegenRate(self):
        return self.healthRegen * self.itemEffects["healthRegenMult"]
    
    def thorns(self):
        return self.itemEffects["thorns"]
    
    def getHealthCap(self):
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

    def getNextItems(self):
        self.nextItems = []
        while True:
            item = random.choice(self.app.items)
            if item not in self.nextItems and item.name not in self.pastItems:
                self.nextItems.append(item)
                if len(self.nextItems) == 3:
                    break

    def searchEnemies(self):
        if self.app.PEACEFUL:
            return
        
        x = random.choice(self.app.ENTITIES)
        if x == self or not isinstance(x, Pawn):
            return
        
        if not self.revengeHunt():
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
        
        self.say(onTarget())
        self.target = x
        self.loseTargetI = 1
        
        if not self.itemEffects["berserker"] and not self.carryingSkull():
            self.walkTo = v2(self.getOwnCell()) * 70
            self.route = None



    def shoot(self):

        if self.loseTargetI <= 0:
            if self.target:
                self.say("Karkas saatana", 0.1)
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
        self.loseTargetI = 1

    def dropSkull(self):
        if self.app.objectiveCarriedBy != self:
            return
        self.app.objectiveCarriedBy = None
        self.app.skull.cell = self.getOwnCell()
        print("Skull dropped!")

    def die(self):

        if random.uniform(0, 1) < self.itemEffects["saveChance"]:
            self.health = self.getHealthCap()
            return

        for x in self.app.deathSounds:
            x.stop()

        for x in range(random.randint(4,8)):
            self.app.bloodSplatters.append(BloodParticle(self.pos.copy(), 1.2, app = self.app))

        #if self.app.cameraLock == self and self.target:
        #    self.app.cameraLock = self.target
        #    print("Camera quick switch")

        if self.app.objectiveCarriedBy == self:
            self.dropSkull()

        self.killed = True
        if self.itemEffects["martyrdom"]:
            Explosion(self.app, self.pos.copy(), self)

        random.choice(self.app.deathSounds).play()

        c = random.choice(self.corpses)
        self.app.MAP.blit(c, self.pos - v2(c.get_size())/2)

        self.reset()

        if self.carryingSkull() or (self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team):
            self.respawnI = 15
        else:
            self.respawnI = 5


        self.killsThisLife = 0
        self.deaths += 1


    def getCellInSpawnRoom(self):
        SPAWNROOM = self.app.teamSpawnRooms[self.team]
        if SPAWNROOM:
            P = SPAWNROOM.randomCell()
        else:
            P = self.app.spawn_points[self.team]
        return P

    def reset(self):

        P = self.getCellInSpawnRoom()

        self.pos = v2(P) * 70 + [35, 35]
        self.deltaPos = self.pos.copy()
        self.health = self.getHealthCap()
        self.hurtI = 0
        self.route = None
        self.walkTo = None
        self.target = None
        self.respawnI = 0
        

        self.killsThisLife = 0
        
        self.weapon.magazine = self.getMaxCapacity()
        self.weapon.currReload = 0
        self.tts.stop()

    def takeDamage(self, damage, fromActor = None, thornDamage = False, typeD = "normal", bloodAngle = None):
        if self.killed:
            return

        if fromActor.itemEffects["allyProtection"] and fromActor.team == self.team:
            return
        
        if typeD == "normal":
            damage /= self.defenceNormal()
        elif typeD == "energy":
            damage /= self.defenceEnergy()
        elif typeD == "explosion":
            damage /= self.defenceExplosion()

        self.health -= damage
        self.outOfCombat = 2
        self.hurtI = 0.25

        if bloodAngle:
            for x in range(random.randint(int(damage/2),int(damage))):
                BloodSplatter(self.app, self.pos.copy(), bloodAngle)

        if self.itemEffects["thorns"] > 0 and not thornDamage and fromActor:
            fromActor.takeDamage(damage * self.itemEffects["thorns"], thornDamage = True, fromActor = self)
        if self.health <= 0:
            if fromActor.team != self.team:
                self.lastKiller = fromActor
            else:
                fromActor.say(onTeamKill(self.name), 1)

            fromActor.say(onKill(fromActor.name, self.name), 1)
            #self.say(onDeath())

            self.die()
            KillFeed(fromActor, self, fromActor.weapon if not self.carryingSkull() else fromActor.skullWeapon)
        else:

            if fromActor == self:
                self.say(onOwnDamage(), 0.5)

            elif fromActor.team == self.team:
                self.say(onTeamDamage(fromActor.name), 0.4)
            else:
                self.say(onTakeDamage(), 0.1)

    def gainXP(self, amount):
        if self.app.VICTORY or self.ULT:
            return
        self.xp += amount * self.itemEffects["xpMult"]

    def evaluatePawn(self):

        print(self.name, "Evaluation")
        print(self.kills, self.deaths, self.teamKills, self.suicides)

        sorted_pawns = sorted(self.app.pawnHelpList.copy(), key=lambda x: x.kills)
        total = len(sorted_pawns)
        try:
            rank = sorted_pawns.index(self)
        except ValueError:
            return 0, "Not ranked"

        reasons = []
        points = 0

        # Base points for rank (inverted: worst rank gets most points)
        points += rank
        reasons.append(f"{rank} pts for being rank {rank + 1} of {total} (kills: {self.kills})")

        if self.suicides:
            s_points = self.suicides * 2
            points += s_points
            reasons.append(f"{s_points} pts for {self.suicides} suicides")

        if self.teamKills:
            t_points = self.teamKills * 2
            points += t_points
            reasons.append(f"{t_points} pts for {self.teamKills} team kills")

        reason_str = f"{points} total points: " + ", ".join(reasons)
        return points, reason_str




    def gainKill(self, killed):
        self.health += self.itemEffects["healOnKill"]
        if killed and killed.team == self.team:
            if killed == self:
                self.suicides += 1
            else:
                self.teamKills += 1
        else:
            self.killsThisLife += 1
            self.kills += 1
        self.gainXP(self.killsThisLife + killed.level)
        if killed == self.lastKiller:

            if self.itemEffects["revenge"]:
                self.say(f"Kosto elää {self.lastKiller.name}.", 1)

            self.lastKiller = None
            print("Retribution!")
            

    def handleTurnCoat(self):
        if self.app.PEACEFUL:
            return
        self.turnCoatI += self.app.deltaTime
        if self.turnCoatI >= 60:
            self.team += random.randint(1, self.app.teams-1)
            self.team = self.team%self.app.teams
            self.turnCoatI = 0
            self.say(f"Ähäkutti! Kuulun joukkueeseen {self.team+1}!", 1)
            if self.target and self.target.team == self.team:
                self.target = None

    def fetchInfo(self, addItems = True):
        info_lines = []

        g = [0,255,0]
        r = [255,0,0]

        for key in self.itemEffects:
            ref = self.referenceEffects.get(key, None)
            val = self.itemEffects[key]

            if isinstance(val, bool):
                if val and not ref:
                    if val:
                        label = self.effect_labels_fi.get(key, key)
                        info_lines.append([f"{label}: Aktivoitu", g])
                    else:
                        label = self.effect_labels_fi.get(key, key)
                        info_lines.append([f"{label}: Deaktivoitu", g])
                        
            elif isinstance(val, (int, float)) and isinstance(ref, (int, float)):
                if ref == 0:
                    diff_ratio = val
                else:
                    diff_ratio = (val - ref) / ref
                if diff_ratio != 0:
                    symbol = "+" if diff_ratio > 0 else "-"
                    label = self.effect_labels_fi.get(key, key)
                    if isinstance(ref, (int)):
                        amount = int(abs(diff_ratio))
                        info_lines.append([f"{label}: {symbol}{amount}", g if diff_ratio > 0 else r])
                    else:        
                        amount = int(abs(diff_ratio*100))
                        info_lines.append([f"{label}: {symbol}{amount}%", g if diff_ratio > 0 else r])



        if addItems:
            info_lines.append(["Omistetut esineet:", [255,255,255]])
            for pI in self.pastItems:
                info_lines.append([pI, [255,255,255]])

        return info_lines

    def hudInfo(self, pos, screen = None):
        font = self.app.fontSmaller
        x, y = pos
        line_height = 20
        info_lines = self.fetchInfo(addItems=False)
        if not info_lines:
            return
        surfs = []
        for l in info_lines:
            line, c = l
            text_surf = font.render(line, True, c)
            surfs.append(text_surf)
        separation = max(surf.get_width() for surf in surfs) + 10

        for i, surf in enumerate(surfs):
            yOff = line_height*(i%9)
            xOff = separation*(i//9)
            screen.blit(surf, (x+xOff, y+yOff))


    def renderInfo(self):
        font = self.app.fontSmaller
        x, y = self.pos
        y += 40
        line_height = font.get_height() + 2
        info_lines = self.fetchInfo(addItems=True)

        for i, l in enumerate(info_lines):
            line, c = l
            text_surf = font.render(line, True, c)
            self.app.DRAWTO.blit(text_surf, v2(x-text_surf.get_width()/2, y + i * line_height) - self.app.cameraPosDelta)


    def levelUp(self, item = None):
        if item:
            item.apply(self)
        else:
            random.choice(self.nextItems).apply(self)
        self.getNextItems()
        self.healthCap += 10
        self.say(f"Jipii! Nousin tasolle {self.level}, ja sain uuden esineen!", 0.1)
        print(self.name, "Leveled up")
        self.level += 1


    def eyeGlow(self):

        if not self.morphed:
            return

        pos1, pos2 = self.getEyePositions()

        for x in (pos1, pos2):
            
            eye = x.copy()

            POS = self.deltaPos + eye - v2(self.breatheIm.get_size()) / 2 + [0, self.breatheY]
            endC = self.app.getTeamColor(self.team) + [0]
            Particle(self.app, POS[0], POS[1], 
                     start_color = [255,255,255,255], end_color=endC, 
                    vel_x=random.uniform(-1, 1), vel_y=random.uniform(-1, 1), 
                    start_size=2, end_size= random.randint(10,20),
                    lifetime=10)

            #self.app.particle_system.create_fire(x[0], x[1], 1, start_color = [0, 255,255,255], end_color=[0,0,255,0], 
            #                                     vel_x=random.uniform(-0.01, 0.01), vel_y=random.uniform(0.01, 0.05), lifetime=10)
        
        


    def tick(self):

        if self.ULT_TIME > 0:
            self.ULT_TIME -= self.app.deltaTime
            self.ULT = True
        else:
            self.ULT = False


        if self.itemEffects["turnCoat"]:
            self.handleTurnCoat()

        self.teamColor = self.app.getTeamColor(self.team) 

        if self.respawnI > 0:

            if self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team:
                self.respawnI -= self.app.deltaTime*0.25
            else:
                self.respawnI -= self.app.deltaTime
            self.killsThisLife = 0
            self.dropSkull()
            return
        
        if self.killed:
            self.app.particle_system.create_healing_particles(self.pos[0], self.pos[1])

        self.killed = False

        if not self.app.PEACEFUL:
            if self.xpI > 0:
                self.xpI -= self.app.deltaTime
            else:
                self.xpI = 15
                self.gainXP(1)

        if self.outOfCombat > 0:
            self.outOfCombat -= self.app.deltaTime
        
        if self.health < self.getHealthCap():
            if self.outOfCombat <= 0 or self.itemEffects["instaHeal"]:
                self.health += self.getRegenRate() * self.app.deltaTime
                self.health = min(self.health, self.getHealthCap())


        if self.xp >= self.app.levelUps[self.level-1] and not self.app.pendingLevelUp:

            if self.xp >= self.app.levelUps[self.levelUpCreatedFor]:
                self.levelUpCreatedFor += 1
                self.app.particle_system.create_level_up_indicator(self.pos[0], self.pos[1])
                print("LEVEL UP ANIM CREATED")
                
            if self.NPC:
                self.levelUp()
            else:
                self.app.pendingLevelUp = self

        if self.app.currMusic != 0 or self.app.PEACEFUL:
            self.think()
        self.walk()
        if self.app.currMusic != 0 or self.app.PEACEFUL:
            self.shoot()
        
        

        if self.app.skull and self.getOwnCell() == self.app.skull.cell and not self.app.objectiveCarriedBy and not self.ULT:
            self.app.objectiveCarriedBy = self
            self.say("Meikäläisen kallopallo!", 1)
            self.route = None
            self.walkTo = None
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
        yAdd = 0
        if self.walkTo is not None:
            # The player should be swinging from side to side when walking
            self.yComponent = abs(math.sin(self.stepI * 2 * math.pi)) * 30
            # The player should move left and right when walking
            self.xComponent = math.cos(self.stepI * 2 * math.pi) * 20
            self.rotation = math.cos(self.stepI * 2 * math.pi) * 10
            Addrotation = 0
            if self.facingRight:
                Addrotation -= self.weapon.runOffset * 15
            else:
                Addrotation += self.weapon.runOffset * 15
            
            yAdd += self.weapon.runOffset * 10


            self.breatheIm = pygame.transform.rotate(self.breatheIm, self.rotation + Addrotation)

        newPos = self.pos - [self.xComponent, self.yComponent - yAdd]
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
        if self.NPC:
            self.npcPlate = self.app.fontSmaller.render("NPC", True, self.teamColor)

        self.namePlate = combinedText(self.name, self.teamColor, " +" + str(int(self.health)).zfill(3), heat_color(1 - self.health/self.getHealthCap()), f" LVL {self.level}",[255,255,255], font=self.app.font)

        #t = self.app.font.render(f"{self.name}", True, (255, 255, 255))
        #self.app.screen.blit(t, (self.pos.x - t.get_width() / 2, self.pos.y - t.get_height() - 70) - self.app.cameraPosDelta)

        cx, cy = self.getOwnCell()

        self.hurtI -= self.app.deltaTime
        self.hurtI = max(0, self.hurtI)
        self.cameraLockI += self.app.deltaTimeR
        self.cameraLockI = self.cameraLockI%0.5
        if self.app.MINIMAPTEMP:
            pygame.draw.rect(self.app.MINIMAPTEMP, self.teamColor, [cx*self.app.MINIMAPCELLSIZE, cy*self.app.MINIMAPCELLSIZE, self.app.MINIMAPCELLSIZE,self.app.MINIMAPCELLSIZE])

        if self.itemEffects["hat"]:
            self.topHat = self.app.topHat.copy()
            self.topHat = pygame.transform.rotate(self.topHat, self.rotation)

        if self.ULT:
            self.eyeGlow()

    def carryingSkull(self):
        return self.app.objectiveCarriedBy == self

    def tryToTransferSkull(self):
        p: "Pawn" = random.choice(self.app.pawnHelpList)
        if p.team != self.team:
            return
        if p.killed:
            return
        cx, cy = self.getOwnCell()
        c2x, c2y = p.getOwnCell()
        if abs(cx - c2x) > 2 or abs(cy - c2y) > 2:
            return
        
        if self.level <= p.level:
            return
        
        if p.ULT:
            return
        
        self.app.objectiveCarriedBy = p
        print("Transferred skull to", p.name)
        self.say("Ota sää tää paska!", 1)
        p.route = None
        p.walkTo = None
        self.route = None
        self.walkTo = None
        

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

        if self.itemEffects["hat"]:
            self.app.DRAWTO.blit(self.topHat, self.deltaPos + [-self.xComponent*0.2, self.breatheY - self.yComponent - self.weapon.recoil*20]  - self.app.cameraPosDelta + self.apexPawn - v2(self.topHat.get_size())/2)


        if self.app.objectiveCarriedBy == self:
            self.skullWeapon.render()
        elif self.weapon:
            self.weapon.render()      


        


        pygame.draw.arc(self.app.DRAWTO, self.teamColor, self.arcRect, math.pi, math.pi * 2)

        if self.NPC:
            self.app.DRAWTO.blit(self.npcPlate, (self.pos.x - self.npcPlate.get_width() / 2, self.pos.y - self.npcPlate.get_height() - 45) - self.app.cameraPosDelta)

        self.app.DRAWTO.blit(self.namePlate, (self.pos.x - self.namePlate.get_width() / 2, self.pos.y - self.namePlate.get_height() - 70) - self.app.cameraPosDelta)


        if self.textBubble:
            t2 = self.app.font.render(self.textBubble, True, [255,255,255])
            self.app.DRAWTO.blit(t2, (self.pos.x - t2.get_width() / 2, self.pos.y - t2.get_height() - 40) - self.app.cameraPosDelta)

        elif self.revengeHunt():
            t2 = self.app.font.render(f"HUNTING FOR {self.lastKiller.name}!!!", True, [255,255,255])
            self.app.DRAWTO.blit(t2, (self.pos.x - t2.get_width() / 2, self.pos.y - t2.get_height() - 40) - self.app.cameraPosDelta)
        elif self.weapon.isReloading():
            
            t2 = self.app.fontSmaller.render(f"RELOADING", True, [255,255,255])
            self.app.DRAWTO.blit(t2, (self.pos.x - t2.get_width() / 2, self.pos.y - t2.get_height() - 40) - self.app.cameraPosDelta)

        #if not self.app.PEACEFUL and self.app.cameraLock == self:
        #    self.renderInfo()


    def think(self):
        self.thinkI += self.app.deltaTime
        if self.thinkI >= self.thinkEvery or self.ULT:
            self.thinkI = 0
            # Do some thinking logic here, e.g., print a message or change state

            c = self.app.randomWeighted(0.2, 0.2)
            if c == 0:
                if not self.target:
                    if not self.weapon.isReloading() and self.weapon.magazine < self.getMaxCapacity()/2 and not self.carryingSkull():
                        self.weapon.reload()


            if c == 1:
                if self.walkTo is None:
                    self.pickWalkingTarget()
    
    def distanceToPawn(self, pawn):
        return self.pos.distance_to(pawn.pos)
    
    def skullCarriedByOwnTeam(self):
        return self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team

    def pickWalkingTarget(self):

        if self.app.PEACEFUL:
            
            if self.app.teamInspectIndex != -1:
                inspect_team = [p for p in self.app.pawnHelpList.copy() if p.team == self.app.teamInspectIndex]
                other_team = [p for p in self.app.pawnHelpList.copy() if p.team != self.app.teamInspectIndex]
                inspect_team.sort(key=lambda p: id(p))
                other_team.sort(key=lambda p: id(p))
                spacing = 250
                spacing2 = 100
                base_x = self.app.res[0]/2 + spacing/2
                base_x2 = self.app.res[0]/2 + spacing2/2
                base_y = 300
                offset_y = 600  # vertical gap between top and bottom lines
                if self.team == self.app.teamInspectIndex:
                    index = inspect_team.index(self)
                    total = len(inspect_team)
                    x = base_x + (index - total / 2) * spacing
                    y = base_y
                else:
                    index = other_team.index(self)
                    total = len(other_team)
                    x = base_x2 + (index - total / 2) * spacing2
                    y = base_y + offset_y + 70*(index%2)

                self.walkTo = [x, y]
            else:
                self.walkTo = v2(random.randint(0, 1920), random.randint(0, 1080))
            return


        if not self.target:
        #self.walkTo = v2(random.randint(0, 1920), random.randint(0, 1080))
            if self.revengeHunt():
                self.getRouteTo(endPosGrid=self.lastKiller.getOwnCell())
                self.say(f"Tuu tänne {self.lastKiller.name}!")
            else:
                if self.app.skull:
                    if not self.app.objectiveCarriedBy:
                        self.getRouteTo(endPosGrid=self.app.skull.cell) # RUN TOWARDS DROPPED SKULL
                    else:
                        if self.carryingSkull(): # CARRYING SKULL
                            if not self.route: # Else go to spawn
                                self.getRouteTo(endPosGrid=self.getCellInSpawnRoom())
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

            elif self.itemEffects["coward"] and self.health <= 0.5 * self.getHealthCap():
                self.say("APUA")
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
            if direction.length() > self.getSpeed() * self.app.deltaTime:
                direction = direction.normalize()
                self.pos += direction * self.getSpeed() * self.app.deltaTime
                self.stepI += self.app.deltaTime * self.getSpeed() / 300

                if self.lastStep != self.stepI // self.takeStepEvery:
                    self.lastStep = self.stepI // self.takeStepEvery
                    if self.onScreen():
                        self.app.playSound(self.app.waddle)
                
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


