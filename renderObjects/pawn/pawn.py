from rembg import remove
from PIL import Image
import io
import pygame
from pygame.math import Vector2 as v2
import random
import os
import math
import numpy as np
from imageprocessing.imageProcessing import gaussian_blur, trim_surface, remove_background, remove_background_bytes, generate_corpse_sprite, set_image_hue_rgba, colorize_to_blood, get_or_remove_background, brighten_surface, outline_surface
from renderObjects.particles.blood import BloodParticle
from renderObjects.killfeed import KillFeed
from renderObjects.explosion import Explosion
from renderObjects.particles.bloodSplatter import BloodSplatter
from imageprocessing.pixelSort import pixel_sort_surface
from imageprocessing.faceMorph import getFaceLandMarks, processFaceMorph, get_or_load_landmarks
from _thread import start_new_thread
import json
import subprocess
from renderObjects.pawn.dialog import onKill, onDeath, onTarget, onTakeDamage, onTeamDamage, onTeamKill, onOwnDamage
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
from renderObjects.pawn.weapon import Weapon
from typing import TYPE_CHECKING
from renderObjects.particles.particle import Particle
import asyncio
if TYPE_CHECKING:
    from main import Game
from levelGen.numbaPathFinding import MovementType
from renderObjects.pawn.behaviour import PawnBehaviour
from renderObjects.pawn.getStat import getStat
from renderObjects.pawn.tts import EspeakTTS
import base64
from renderObjects.pawn.teamLogic import Team
from renderObjects.grenade import GrenadeType
from gameTicks.pawnExplosion import PawnParticle
from renderObjects.textParticle import TextParticle
from renderObjects.pawn.flyingCorpse import FlyingCorpse
from renderObjects.pawn.turret import Turret
from renderObjects.demoObject import DemoObject

def debug_draw_alpha(surface):
    alpha_arr = pygame.surfarray.array_alpha(surface)
    alpha_rgb = np.stack([alpha_arr]*3, axis=-1)
    debug_surface = pygame.surfarray.make_surface(alpha_rgb)
    return debug_surface


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


def surface_to_base64(surface: pygame.Surface) -> str:
    buf = io.BytesIO()
    pygame.image.save(surface, buf, "PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return b64  # Just the base64, no prefix


class Pawn(PawnBehaviour, getStat, DemoObject):
    def __init__(self, app: "Game", pawnName, pawnAvatarEncoded, client, team = -1, boss = False):
        self.app: "Game" = app
        # extract the name from the path
        self.name = pawnName
        self.client = client

        self.NPC = not bool(self.client)
        if self.client == "DEBUG":
            self.client = None

        if self.client:
            self.app.clientPawns[self.client] = self
            print(self.app.clientPawns)

        self.GENERATING = True
        self.itemsInStock = []
        self.shopItems = []

        self.BOSS = boss
        self.isPawn = True

        self.xp = 0

        super().__init__(demo_keys=("pos", "deltaPos", "aimAt", "killed", "flashed", "hurtI", "tripI", "respawnI", "health", "facingRight"))

        
        self.drinkTimer = 0
        self.drinks = {}
        self.lastDrinks = []

        # pawnAvatarEncoded is encoded as base64

        info = infoBar(self.app, f"{self.name}: Removing BG")

        # decode base64
        #image_bytes = base64.b64decode(pawnAvatarEncoded)

        # remove background in memory
        bg_removed_bytes = get_or_remove_background(self.app, pawnAvatarEncoded, "cache/background_cache.json")

        # convert to pygame.Surface
        img = Image.open(io.BytesIO(bg_removed_bytes)).convert("RGBA")
        mode = img.mode
        size = img.size
        data = img.tobytes()
        image = pygame.image.frombuffer(data, size, mode)
            
        self.textBubble = None

        image = trim_surface(image)

        self.levelUpImage = pygame.transform.scale_by(image, 400 / image.get_size()[1])
        info.text = f"{self.name}: Morphing"
        self.levelUpImage = self.morph(self.levelUpImage)


        self.defaultPos()


        

        self.left_eye_center = v2(0,0)
        self.right_eye_center = v2(0,0)

        self.height = 100 if not self.BOSS else 300

        self.hitBox = pygame.Rect(self.pos[0], self.pos[1], self.height, self.height)

        pawnImage = pygame.transform.scale_by(self.levelUpImage, self.height / self.levelUpImage.get_size()[1]).convert_alpha()
        pawnImage = outline_surface(pawnImage, 5)

        self.imagePawn = pawnImage.copy()

        self.imagePawn = pygame.transform.scale_by(self.imagePawn, self.app.RENDER_SCALE)
        
        #self.imagePawn = debug_draw_alpha(self.imagePawn).convert_alpha()

        self.imagePawnR = pygame.transform.flip(self.imagePawn.copy(), True, False).convert_alpha()

        self.cheater = False
        self.cheatPlate = None

        #self.topHat = self.app.topHat.copy()

        

        if not self.BOSS:
            self.apexPawn = v2([0, -75])
        else:
            self.apexPawn = v2([0, -300])
        #self.apexPawn = v2(get_apex_pixel_mean(self.imagePawn, threshold=2))
        

        #pygame.draw.circle(self.imagePawn, [255,0,0], self.apexPawn, 10)

        self.shopSuccessPackets = []
        
        

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

        self.flashPawn = brighten_surface(self.imagePawn.copy(), gain=4, offset=70).convert_alpha()
        self.flashPawnR = pygame.transform.flip(self.flashPawn.copy(), True, False).convert_alpha()
        info.text = f"{self.name}: Flashing"
        self.flashIm = [[], []]
        for x in range(10):
            h1 = self.flashPawn.copy()
            h2 = self.flashPawnR.copy()
            h1.set_alpha(int(255*x/10))
            h2.set_alpha(int(255*x/10))
            self.flashIm[0].append(h1)
            self.flashIm[1].append(h2)

        self.hurtI = 0
        info.text = f"{self.name}: Making corpses"
        self.corpses = []
        for x in range(3):
            corpse = generate_corpse_sprite(self.imagePawn.copy())
            corpse.set_alpha(155)
            corpse = pygame.transform.rotate(corpse, random.randint(0,360))
            self.corpses.append(corpse)

        

        self.millionaireImage = pygame.transform.scale_by(self.levelUpImage.copy(), 300 / self.levelUpImage.get_size()[1])
        self.millionaireImage = pygame.transform.flip(self.millionaireImage, True, False)

        self.currentRoom = None

        self.aimAt = 0

        self.damageTakenPerTeam = {}


        #pygame.draw.circle(self.imagePawn, [255,0,0], self.left_eye_center*100, 5)
        #pygame.draw.circle(self.imagePawn, [255,0,0], self.right_eye_center*100, 5)

        self.hudImage = pygame.transform.scale_by(self.levelUpImage.copy(), 200 / self.levelUpImage.get_size()[1])
        self.hudImageFlipped = pygame.transform.flip(self.hudImage, True, False)



        enc = pygame.transform.scale_by(self.hudImage, 40 / self.hudImage.get_size()[1])

        self.encodedImage = surface_to_base64(enc)

        info.text = f"{self.name}: Pixel sorting"
        

        self.facingRight = True
        self.app.pawnHelpList.append(self)
        self.team: Team = None
        if not self.BOSS:
            if team == -1:
                self.app.assignTeam(self)
            else:
                print("Preassigned team for", self.name)
                self.app.allTeams[team].add(self)
        else:
            self.app.alwaysHostileTeam.add(self)

        

        self.teamColor = self.team.color

        self.reconnectJson = None
        self.pendingAppLU = False


        self.breatheI = random.uniform(0, 1)
        self.thinkEvery = 0.5 # seconds
        self.thinkI = random.uniform(0, self.thinkEvery)
        self.walkTo = None
        self.route = None
        self.speed = 300

        self.gType = None
        #self.gType = random.randint(0,2)
        #if self.team.i == 0:
        #    self.gType = 1
        self.grenadeAmount = 0
        self.grenadeReloadI = 0

        self.vel = v2(0,0)

        self.immune = 0

        self.stepI = 0 
        self.stats = {
            "kills": 0,
            "deaths": 0,
            "damageDealt": 0,
            "damageTaken": 0,
            "teamkills": 0,
            "suicides": 0,
            "assists": 0,
            "flashes": 0,
            "teamFlashes": 0,
            "amountDrank": 0,
            "amountSpended": 0,
        }
        self.playerSpecificStats = {}
        self.mostKilled = None
        self.mostKilledBy = None

        self.takeStepEvery = 0.5
        self.lastStep = -1
        self.respawnI = 0
        self.healthCap = 100
        self.health = self.healthCap

        self.lastKiller = None

        self.target = None
        self.killed = False
        

        self.yComponent = 0
        self.xComponent = 0
        self.rotation = 0

        self.walkingSpeedMult = 0
        

        self.healthRegen = 10
        self.outOfCombat = 0
        self.loseTargetI = 0
        self.pastItems = []
        

        
        self.xpI = 15
        self.enslaved = False

        self.weapon: Weapon = None
        
        self.bombWeapon = self.app.bombW.duplicate(self)
        self.skullWeapon = self.app.skullW.duplicate(self) 
        self.hammer = self.app.hammer.duplicate(self) 

        self.dualwield = False
        self.dualWieldWeapon = self.app.pistol2.duplicate(self)

        self.cameraLockI = 0
        self.onCameraTime = 0

        info.text = f"{self.name}: Giving a weapon"
        weapon = random.choice(self.app.weapons)
        weapon = self.app.pistol2

        if self.app.giveWeapons:
            weapon = random.choice(self.app.weapons)
            

        self.flash = self.app.flash.duplicate(self)
        self.frag = self.app.frag.duplicate(self)
        self.turr = self.app.turretNade.duplicate(self)
        self.tele = self.app.teleNade.duplicate(self)


        self.grenades = [self.flash, self.frag, self.turr, self.tele]

        #weapon = self.app.desert

        #weapon = self.app.hammer

        weapon.give(self)  # Give the AK-47 to this pawn

        self.currWeapon = self.weapon
        

        self.grenadePos = None
        self.currentlyAliveNade = None

        self.kills = 0
        self.killsThisLife = 0
        self.level = 1
        self.levelUpCreatedFor = 0
        self.deaths = 0
        self.teamKills = 0
        self.suicides = 0

        self.flashed = 0

        self.turnCoatI = 0

        self.tts = EspeakTTS(self, random.randint(120,300), random.randint(0,100), voice="fi")
        
        self.ULT = False
        self.ULT_TIME = 0

        self.tripped = False
        self.tripI = 0.0  # [0..1] animation progress
        self.getUpI = 0
        self.tripRot = random.choice([-90, 90])  # fall direction

        self.nextItems = []

        self.shopCurrWeapon = random.choice(self.app.weapons)
        self.rerollWeapon(price=0)

        self.building = False
        self.buildingTarget = None  # Building object being constructed
        self.buildingI = 0  # Animation timer
        self.hammerWeapon = None  # Hammer weapon instance
        self.buildingJumpOffset = 0
        self.buildingBounceOffset = 0
        self.buildingRotationOffset = 0
        
        self.STATUS = "Idling"

        self.getNextItems()
        
        self.referenceEffects = self.itemEffects.copy()
        info.text = f"{self.name}: sending"
        # self.client is the WebSocket

        
        if not self.BOSS and False:
            PawnParticle(self)
            
        if self.client:
            self.fullSync()

        info.text = f"{self.name}: Done!"
        info.killed = True
        if not self.NPC:
            self.app.notify(f"{self.name} joined!", self.teamColor)
        
        

        #for x in range(3):
        #    i = random.choice(self.app.items)
        #    i.apply(self)

        
        if self.BOSS:
            for i in range(39):
                self.getNextItems()
                self.levelUp()
            #for x in self.itemEffects:
            #    if isinstance(self.itemEffects[x], float):
            #        self.itemEffects[x] = float(self.itemEffects[x] * 2)
            #    elif isinstance(self.itemEffects[x], int):
            #        self.itemEffects[x] = int(self.itemEffects[x] * 2)
            #    elif isinstance(self.itemEffects[x], bool):
            #        self.itemEffects[x] = True
            
            self.itemEffects["healthRegenMult"] = 0.0
            self.app.BABLO = self
            self.killed = True
            self.itemEffects["healthCapMult"] = 1.0
            self.healthCap = 100000
            self.itemEffects["healOnKill"] = 0
            self.itemEffects["lifeSteal"] = 0.0
            self.itemEffects["recoilMult"] = 2.0
            self.itemEffects["noscoping"] = False
            self.itemEffects["weaponReload"] = 1.0
            self.itemEffects["playMusic"] = False
            self.itemEffects["talking"] = False
            self.health = self.healthCap

            #self.itemEffects["defenceNormal"] = 2.0
            #self.itemEffects["defenceEnergy"] = 2.0
            #self.itemEffects["defenceExplosion"] = 5.0

            self.weapon = self.app.BIGASSAK.duplicate(self)

            self.dualWieldWeapon = self.weapon.duplicate(self)
            self.dualwield = True

        
            w, h = self.imagePawn.get_size()
            mouth = 145 * self.app.RENDER_SCALE
            self.head_rect = pygame.Rect(0, 0, w, mouth)
            self.body_rect = pygame.Rect(0, mouth, w, h - mouth)

            # HEAD (same size as full image, transparent elsewhere)
            self.imagePawnHead = pygame.Surface((w, h), pygame.SRCALPHA)
            self.imagePawnHead.blit(self.imagePawn, (0, 0), self.head_rect)

            self.imagePawnHeadR = pygame.Surface((w, h), pygame.SRCALPHA)
            self.imagePawnHeadR.blit(self.imagePawnR, (0, 0), self.head_rect)

            # BODY (original with transparent head area)
            self.imagePawn.fill((0, 0, 0, 0), self.head_rect)

            self.imagePawnR.fill((0, 0, 0, 0), self.head_rect)

        



        #else:
        #    for x in range(4):
        #        self.getNextItems()
        #        self.levelUp()
       #
        self.GENERATING = False

    def updateEquipment(self):
        if not self.client:
            return
        
        equipment = [self.weapon]
        if self.itemEffects["dualWield"]:
            equipment.append(self.dualWieldWeapon)
        
        if self.gType != None:
            equipment.append(self.grenades[self.gType])

        packet = {"type": "equipmentImages",
                  "images": [x.encodedImage for x in equipment],}
        
        self.dumpAndSend(packet)

    def getPosInTime(self, timeSeconds):
        cell = self.getOwnCell()
        speed = self.getSpeed(self.currWeapon) / self.app.tileSize

        if self.walkTo is not None:
            w = self.walkTo / self.app.tileSize
            r = ([w] if not self.route or self.route[0] != w else []) + (self.route or [])
        else:
            r = self.route or []

        if not r:
            return self.intCell(cell)

        distanceAmount = speed * timeSeconds
        lastCell = cell

        for c in r:
            dist = self.app.getDistFrom(lastCell, c)
            if dist <= 0:
                continue

            if dist > distanceAmount:
                direction = (v2(c) - v2(lastCell)) / dist
                pos = lastCell + direction * distanceAmount
                return self.intCell(pos)

            distanceAmount -= dist
            lastCell = c

        return self.intCell(lastCell)

    def intCell(self, pos):
        return (int(pos[0]), int(pos[1]))

    def fullSync(self):
        if not self.client:
            return       
        
        asyncio.run_coroutine_threadsafe(self.completeToApp(), self.app.loop)

        self.updateStats({"XP": int(self.xp), "Currency": self.team.currency, "Level" : self.level, "XP to next level" : self.app.levelUps[self.level-1]})

        self.sendHudInfo()

        if self.pendingAppLU:
            asyncio.run_coroutine_threadsafe(self.sendPacket(self.reconnectJson), self.app.loop)
        
        self.sendKDStats()
        
        self.sendNemesisInfo(True, True)

        self.sendCurrWeaponShop()

        self.sendGamemodeInfo()

        self.updateEquipment()

        #for x in self.shopSuccessPackets:
        #    print(x)
        #    self.dumpAndSend(x)

    def reLevelPawn(self, to = 10):
        self.level = 0
        self.xp = 0
        self.healthCap = 100
        self.health = self.healthCap
        self.pastItems.clear()
        self.itemEffects = self.referenceEffects.copy()
        while self.level < to:
            self.getNextItems()
            self.levelUp()



    def pickAnother(self, exclude, pickFrom):
        exclude_set = set(exclude)
        candidates = [x for x in pickFrom if x not in exclude_set]
        if not candidates:
            raise ValueError("No available elements after exclusion")
        return random.choice(candidates)


    def canBuy(self, price):
        return price <= self.team.currency
    def canReroll(self):
        return self.team.currency >= 25
    
    def rerollWeapon(self, price = 25):
        self.team.currency -= price
        self.stats["amountSpended"] += price
        self.shopCurrWeapon = self.pickAnother([self.shopCurrWeapon, self.weapon], self.app.weapons)
        self.shopSuccessPackets = []
        self.shopItems = []
        self.itemsInStock = []
        while len(self.shopItems) < 2:
            self.getRandomItem()

        self.sendCurrWeaponShop()

    def getRandomItem(self):
        
        i = self.app.randomWeighted(0.1, 0.3, 0.6)

        addToStock = False

        if i == 0: # ULT

            ITEM = {"name": "ULT",
                               "price": 100,
                               "image": None,
                               "description": "Ultaa 30 sekunniksi.",
                               "backgroundColor": [155,0,0],
                               "owned": False}


        elif i == 1: # GRENADE
            gtype = self.app.randomWeighted(0.4, 0.4, 0.2, 0.1)
            grenade = self.grenades[gtype]
            color = grenade.get_rarity_color(200)
            ITEM = {"name": grenade.name,
                               "price": grenade.price[0],
                               "image": grenade.encodedImage,
                               "description": "Kranaatti.",
                               "backgroundColor": color,
                               "owned": False}
            

        else: # RANDOM ITEM
            items = [item for item in self.app.items if item not in self.nextItems and item not in self.itemsInStock and item.name not in self.pastItems]
            if not items: return
            item = random.choice(items)
            ITEM = {"name": item.name,
                               "price": int(random.randint(2,8)*25),
                               "image": None,
                               "description": item.desc,
                               "backgroundColor": [20,20,120],
                               "owned": False}
            addToStock = True

        if ITEM["name"] in [x["name"] for x in self.shopItems]:
            return

        if addToStock: 
            self.itemsInStock.append(item)
        self.shopItems.append(ITEM)

    def purchaseItem(self, name, price):
        gnames = [x.name for x in self.grenades]
        if name in gnames:
            self.gType = gnames.index(name)

        elif name == "ULT":
            self.ULT_TIME = 30
            self.app.notify(f"{self.name} IS ULTING", self.team.getColor())

        else:
            item = [item for item in self.app.items if item.name == name]
            item[0].apply(self)

        for itemPacket in self.shopItems:
            if itemPacket["name"] == name:
                itemPacket["owned"] = True
                
                break
        self.sendHudInfo()
        
        self.stats["amountSpended"] += price
        self.team.currency -= price

        self.sendCurrWeaponShop()




    
    def purchaseWeapon(self, weaponName, price):
        weapon = [weapon for weapon in self.app.weapons if weapon.name == weaponName][0]
        self.team.currency -= price
        self.stats["amountSpended"] += price
        weapon.give(self)

        #self.shopCurrWeapon = self.pickAnother([self.shopCurrWeapon, self.weapon], self.app.weapons)
        self.sendCurrWeaponShop()

    def sendCurrWeaponShop(self):
        
        pWeapon = self.shopCurrWeapon.getPacket()
        pWeapon["owned"] = self.shopCurrWeapon.name == self.weapon.name
       
        p = {"type": "shopUpdate", "nextWeapon": pWeapon, "items" : self.shopItems}

        self.dumpAndSend(p)

        

        

    def sendKDStats(self):
        if not self.client:
            return
        
        kd = self.stats["kills"] / max(1, self.stats["deaths"])

        self.updateStats({"Kills": self.stats["kills"], "Deaths" : self.stats["deaths"], "KD" : f"{kd:.1f}",
                          "Amount drank": self.stats["amountDrank"], "Amount spent": self.stats["amountSpended"]})

        

    async def completeToApp(self):
        # Convert pygame.Surface to PNG bytes
        img = self.hudImage  # pygame.Surface
        buf = io.BytesIO()
        pil_img = Image.frombytes("RGBA", img.get_size(), pygame.image.tostring(img, "RGBA"))
        pil_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        # Encode to base64
        b64_image = base64.b64encode(png_bytes).decode("ascii")
        teamColor = self.team.color

        # Build JSON
        message = {
            "type": "completePawn",
            "name": self.name,
            "image": b64_image,
            "teamColor" : teamColor
        }
        # Send JSON to client
        #import json

        c = self.app.clients[self.client]

        await c.send(json.dumps(message))

    def defaultPos(self):
        if random.randint(0, 1) == 0:
            self.pos = v2(random.randint(0, 1920), random.choice([-200, self.app.originalRes[1] + 200]))
        else:
            self.pos = v2(random.choice([-200, self.app.originalRes[0] + 200]), random.randint(0, 1080))
        self.deltaPos = self.pos.copy()



    def say(self, t, chanceToSay = 0.2):
        if not self.itemEffects["talking"]:
            return
        
        #if not self.onScreen():
        #    return
        
        if random.uniform(0,1) >= chanceToSay:
            return
        self.tts.say(t)


    def morph(self, image):
        rgb = pygame.surfarray.array3d(image).swapaxes(0, 1)
        alpha = pygame.surfarray.array_alpha(image)

        landMarks = get_or_load_landmarks(self.app, rgb, "cache/landmarks_cache.json")
        if landMarks.dtype == object and landMarks.size == 1 and landMarks[()] is None:
            self.morphed = False
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
        
    



    def getNextItems(self):
        self.nextItems = []
        while True:
            item = random.choice(self.app.items)
            if item not in self.nextItems and item.name not in self.pastItems and item not in self.itemsInStock:
                self.nextItems.append(item)
                if len(self.nextItems) == (4 if self.itemEffects["extraItem"] else 3):
                    break

    def searchEnemies(self, WEAPON):
        if self.app.PEACEFUL:
            return
        
        if self.flashed > 0:
            return
        
        x = random.choice(self.app.pawnHelpList)
        if x == self or not isinstance(x, (Pawn, Turret)):
            return
        
        if not self.revengeHunt() and not self.app.VICTORY and not self.app.GAMEMODE == "1v1":
            if not self.team.hostile(self, x):
                return
        
        if x.respawnI > 0:
            return
        
        if self.revengeHunt():
            if self.lastKiller != x:
                return
        
        dist = self.pos.distance_to(x.pos)
        if dist > self.getRange(WEAPON):
            return
        if self.target and dist >= self.pos.distance_to(self.target.pos):
            return

        if not self.sees(x):
            return
        
        self.say(onTarget())
        self.target = x
        self.loseTargetI = 1
        self.buildingTarget = None

        self.team.addNadePos(self.target.getPosInTime(2.0), "aggr") #
        
        if not self.itemEffects["berserker"] and not self.carryingSkull():
            self.walkTo = v2(self.getOwnCell()) * self.app.tileSize
            self.route = None




    def dropSkull(self):
        if self.app.objectiveCarriedBy != self:
            return
        self.app.objectiveCarriedBy = None
        self.app.skull.cell = self.getOwnCell()

    def gainCurrency(self, amount):
        self.team.currency += int(amount*self.itemEffects["currencyGain"])
        self.team.updateCurrency()

    def die(self):

        if random.uniform(0, 1) < self.itemEffects["saveChance"]:
            self.health = self.getHealthCap()
            return

        self.gainCurrency(5)
        self.app.roundInfo["deaths"] += 1

        #if self.app.cameraLock == self and self.target:
        #    self.app.cameraLock = self.target
        #    print("Camera quick switch")

        if self.app.objectiveCarriedBy == self:
            self.dropSkull()

        self.killed = True
        if self.itemEffects["martyrdom"]:
            Explosion(self.app, self.pos.copy(), self.currWeapon, damage = 200 * self.itemEffects["weaponDamage"])

        
        

        x, y = self.getOwnCell()
        self.app.killgrid[y,x] += 1
        for r in self.app.map.rooms:
            if r.contains(x, y):
                r.kills += 1
                break


        FlyingCorpse(self.pos, self)

        self.reset()

        if self.app.GAMEMODE == "1v1":
            self.respawnI = 2

        elif self.app.GAMEMODE == "TEAM DEATHMATCH":
            self.respawnI = 2

        elif self.app.GAMEMODE == "KING OF THE HILL":
            self.respawnI = 2

        elif self.app.GAMEMODE == "FINAL SHOWDOWN":
            self.respawnI = 1
            self.xp = self.app.levelUps[self.level-1]

        elif self.app.GAMEMODE == "ODDBALL" and self.carryingSkull() or (self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team):
            self.respawnI = 15
        elif self.app.GAMEMODE == "DETONATION":
            if self.team.isCT():
                self.respawnI = self.app.load_ct_spawn()
            else:
                self.respawnI = 2
        else:
            self.respawnI = 10

        if self.BOSS and self.app.GAMEMODE == "FINAL SHOWDOWN":
            top_team = max(self.damageTakenPerTeam, key=self.damageTakenPerTeam.get)
            print(self.damageTakenPerTeam)
            print(top_team)
            self.app.announceVictory(top_team)

            self.app.ENTITIES.remove(self)
            self.app.pawnHelpList.remove(self)


        self.killsThisLife = 0
        self.deaths += 1
        self.stats["deaths"] += 1


    def getCellInSpawnRoom(self):

        if self.app.GAMEMODE == "TURF WARS":
            if self.team.isEnslaved() and self.enslaved:
                SPAWNROOM = self.app.teamSpawnRooms[self.team.enslavedTo]
            else:
                SPAWNROOM = self.app.teamSpawnRooms[self.team.i]

        elif self.app.GAMEMODE == "DETONATION":
            SPAWNROOM = self.team.getDetonationSpawnRoom()
        else:
            if self.team.i < len(self.app.teamSpawnRooms):
                SPAWNROOM = self.app.teamSpawnRooms[self.team.i]
            else:
                SPAWNROOM = self.app.teamSpawnRooms[0]
        if SPAWNROOM:
            P = SPAWNROOM.randomCell()
        else:
            P = self.app.spawn_points[self.team.i]
        return P

    def reset(self):
        
        if self.app.GAMEMODE == "TURF WARS" and not self.app.PEACEFUL:
            self.enslaved = self.team.isEnslaved()
        else:
            self.enslaved = False

        P = self.getCellInSpawnRoom()

        self.pos = v2(P) * self.app.tileSize + [self.app.tileSize/2, self.app.tileSize/2]
        self.deltaPos = self.pos.copy()
        self.health = self.getHealthCap()
            
        self.hurtI = 0
        self.route = None
        self.walkTo = None
        self.target = None
        self.respawnI = 0
        self.tripped = False
        self.grenadePos = None
        self.flashed = 0
        self.grenadeAmount = 0

        if self.defusing():
            self.app.skull.defusedBy = None

        self.teamColor = self.team.getColor(self.enslaved)

        self.weapon.lazerActive = False
        

        self.killsThisLife = 0
        
        self.weapon.magazine = self.getMaxCapacity(self.weapon)
        self.weapon.currReload = 0
        self.dualWieldWeapon.magazine = self. getMaxCapacity(self.dualWieldWeapon)
        self.dualWieldWeapon.currReload = 0
        self.tts.stop()
        self.sendKDStats()
        if self.killed:
            self.dumpAndSend({"type": "teamSwitch", "newTeamColor": [30,30,30]})
        else:
            self.dumpAndSend({"type": "teamSwitch", "newTeamColor": self.teamColor})

    def takeDamage(self, damage, fromActor = None, thornDamage = False, typeD = "normal", bloodAngle = None):

        if self.immune > 0:
            damage = 0

        if fromActor:
            if thornDamage:
                weapon = "melee"
                fromActor = fromActor
            elif typeD == "melee":
                typeD = "normal"
                weapon = "melee"
                fromActor = fromActor.owner
            else:
                weapon = fromActor
                fromActor = fromActor.owner
        
        else:
            weapon = None

        if self.killed:
            return

        if fromActor and fromActor.itemEffects["allyProtection"] and not fromActor.team.hostile(fromActor, self):
            return
        
        if typeD == "normal":
            damage /= self.defenceNormal()
        elif typeD == "energy":
            damage /= self.defenceEnergy()
        elif typeD == "explosion":
            damage /= self.defenceExplosion()

        if self.app.SILENT_DAMAGE_ADJUST and self.app.winningTeam and fromActor and fromActor.team.i == self.app.winningTeam.i: # Silent damage reduction from the winning team
            damage *= 0.5

        if fromActor and fromActor.itemEffects["bossKiller"]:
            damage *= max(1, self.level - fromActor.level)

        if self.flashed > 1:
            if self.flashedBy:
                mult = (1 + self.flashed/5 * self.flashedBy.itemEffects["utilityUsage"])
                damage *= mult
            else:
                damage *= 2

        self.stats["damageTaken"] += damage
        if fromActor:
            fromActor.stats["damageDealt"] += damage

        if self.BOSS and fromActor and fromActor.team.i != -1:
            if fromActor.team.i not in self.damageTakenPerTeam:
                self.damageTakenPerTeam[fromActor.team.i] = damage
            else:
                self.damageTakenPerTeam[fromActor.team.i] += damage

        self.health -= damage
        self.outOfCombat = 2
        self.hurtI = 0.25

        if bloodAngle:
            for x in range(random.randint(int(damage/2),int(damage))):
                BloodSplatter(self.app, self.pos.copy() + [random.uniform(-50,50), random.uniform(-50,50)], bloodAngle)

        if self.itemEffects["thorns"] > 0 and not thornDamage and fromActor:
            fromActor.takeDamage(damage * self.itemEffects["thorns"], thornDamage = True, fromActor = self)

        if fromActor and fromActor.itemEffects["lifeSteal"] > 0:
            fromActor.health += damage * fromActor.itemEffects["lifeSteal"]

        if self.health <= 0:
            if fromActor:
                if fromActor.team != self.team:
                    self.lastKiller = fromActor
                else:
                    fromActor.say(onTeamKill(self.name), 1)

                fromActor.say(onKill(fromActor.name, self.name), 1)
                #self.say(onDeath())

            self.die()
            KillFeed(fromActor, self, weapon)
        else:

            if fromActor == self:
                if self.itemEffects["detonation"]:
                    self.say("Allahu Akbar!", 1)
                else:
                    self.say(onOwnDamage(), 0.5)

            elif fromActor and fromActor.team == self.team:
                self.say(onTeamDamage(fromActor.name), 0.4)
            else:
                self.say(onTakeDamage(), 0.1)

    def isManual(self):
        return self == self.app.MANUALPAWN

    def gainXP(self, amount):
        if self.app.VICTORY or self.ULT or self.BOSS or self.level >= 49:
            return
        
        if self.level == 49:
            return

        am = amount * self.itemEffects["xpMult"]
        TextParticle(self.app, f"+{am:.1f}XP", self.pos)

        self.xp += am

        self.app.roundInfo["xpGained"] += am

        self.updateStats({"XP": int(self.xp)})

    def updateStats(self, stats: dict):
        if not self.client:
            return
        packet = {
            "type": "statUpdate",
            "stats": stats  # e.g., {"xp": 5, "level": 2, "health": 50}
        }
        json_packet = json.dumps(packet)
        asyncio.run_coroutine_threadsafe(self.sendPacket(json_packet), self.app.loop)


    def createPacket(self, packet):
        if not self.client:
            return
        json_packet = json.dumps(packet)
        asyncio.run_coroutine_threadsafe(self.sendPacket(json_packet), self.app.loop)

    async def sendPacket(self, packet):
        c = self.app.clients[self.client]
        await c.send(packet)
        


    def evaluatePawn(self):

        sorted_pawns = sorted(self.app.getActualPawns(), key=lambda x: x.kills)
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

    def getKillXP(self, killed: "Pawn"):
        return int((killed.level ** 0.5) * (max(1, killed.level - self.level)))

    def gainKill(self, killed: "Pawn"):
        self.health += self.itemEffects["healOnKill"]
        if killed and killed.team == self.team:
            if killed == self:
                self.suicides += 1
                self.stats["suicides"] += 1
            elif self.app.GAMEMODE == "1v1":
                self.killsThisLife += 1
                self.kills += 1
                self.stats["kills"] += 1
            elif not self.app.VICTORY:
                self.teamKills += 1
                self.stats["teamkills"] += 1
        else:
            self.killsThisLife += 1
            self.kills += 1
            self.stats["kills"] += 1

        xp = self.getKillXP(killed)

        self.gainXP(xp)

        self.killStreak()


        if killed == self.lastKiller:

            if self.itemEffects["revenge"]:
                self.say(f"Kosto elää {self.lastKiller.name}.", 1)

            self.lastKiller = None
            

        self.handleNemesisStats(killed)
        self.handleNemesis()
        killed.handleNemesis()
        
        self.sendKDStats()

    def killStreak(self):
        if self.killsThisLife % 5 != 0 or self.killsThisLife > 25 or self.killsThisLife == 0:
            return
        
        i = int(self.killsThisLife / 5 - 1)

        s = self.app.killstreaks[i]
        s.stop()
        s.play()
        self.app.notify(f"{self.name} {self.app.killStreakText[i]}", self.teamColor)

    def handleNemesisStats(self, killed):
        if killed.name not in self.playerSpecificStats:
            self.playerSpecificStats[killed.name] = [killed, 0, 0]
        self.playerSpecificStats[killed.name][1] += 1

        if self.name not in killed.playerSpecificStats:
            killed.playerSpecificStats[self.name] = [self, 0, 0]
        killed.playerSpecificStats[self.name][2] += 1

        

    def handleNemesis(self):
        mostKilledSend = mostKilledBySend = True

        if self.playerSpecificStats:
            MK_entry = max(self.playerSpecificStats.items(), key=lambda kv: kv[1][1])[1]
            MK = MK_entry[0]  # pawn object
            if MK != self.mostKilled:
                mostKilledSend = True
            self.mostKilled = MK

            MKB_entry = max(self.playerSpecificStats.items(), key=lambda kv: kv[1][2])[1]
            MKB = MKB_entry[0]  # pawn object
            if MKB != self.mostKilledBy:
                mostKilledBySend = True
            self.mostKilledBy = MKB

        self.sendNemesisInfo(mostKilledSend, mostKilledBySend)

    def sendNemesisInfo(self, mostKilledSend=False, mostKilledBySend=False):

        if not self.client:
            return
        
        if not mostKilledBySend and not mostKilledSend:
            return

        d = {"type": "rivalryInfo", "mostKilled": None, "mostKilledBy": None}

        if mostKilledSend and self.mostKilled:
            d["mostKilled"] = {
                "name": self.mostKilled.name,
                "image": self.mostKilled.encodedImage,
                "kills": self.playerSpecificStats[self.mostKilled.name][1]
            }

        if mostKilledBySend and self.mostKilledBy:
            d["mostKilledBy"] = {
                "name": self.mostKilledBy.name,
                "image": self.mostKilledBy.encodedImage,
                "kills": self.playerSpecificStats[self.mostKilledBy.name][2]
            }

        self.dumpAndSend(d)



            

    def handleTurnCoat(self):
        if self.app.PEACEFUL:
            return
        self.turnCoatI += self.app.deltaTime
        if self.turnCoatI >= 60:
            T = random.choice(self.app.allTeams)
            T.add(self)
            self.turnCoatI = 0
            self.say(f"Ähäkutti! Kuulun joukkueeseen {self.team.i+1}!", 1)
            if self.target and self.target.team == self.team:
                self.target = None
            self.enslaved = False

    def sendHudInfo(self):
        hud_data = []
        for line, color in self.fetchInfo(addItems=False):
            hud_data.append({
                "text": line,
                "color": {"r": int(color[0]), "g": int(color[1]), "b": int(color[2])}  # [R, G, B]
            })
        packet = {"type": "hudInfo", "lines": hud_data}
        self.dumpAndSend(packet)

    def sendGamemodeInfo(self):
        if not self.client: return
        if self.app.GAMEMODE not in self.app.gameModeDescriptions:
            packet = {"type":"gamemodeInfo", "text": "Kyllä viinnaa pittääpi juua."}
            self.dumpAndSend(packet)
        else:
            packet = {"type":"gamemodeInfo", "text": self.app.GAMEMODE + "\n" + self.app.gameModeDescriptions[self.app.GAMEMODE]}
            self.dumpAndSend(packet)

    def dumpAndSend(self, packet):
        if not self.client:
            return    
        json_packet = json.dumps(packet)
        asyncio.run_coroutine_threadsafe(self.sendPacket(json_packet), self.app.loop)

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
            info_lines.append(["Owned items:", [255,255,255]])
            for pI in self.pastItems:
                info_lines.append([pI, [255,255,255]])

        return info_lines

    def hudInfo(self, pos, screen=None, reverse=False):
        font = self.app.fontSmallest
        x, y = pos
        line_height = 14
        info_lines = self.fetchInfo(addItems=False)
        if not info_lines:
            return

        surfs = []
        for line, c in info_lines:
            surfs.append(font.render(line, True, c))

        separation = max(s.get_width() for s in surfs) + 5

        for i, surf in enumerate(surfs):
            row = i % 14
            col = i // 14

            yOff = line_height * row

            if not reverse:
                xOff = separation * col
                draw_x = x + xOff
            else:
                xOff = separation * col
                draw_x = x - xOff - surf.get_width()

            screen.blit(surf, (draw_x, y + yOff))


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
        self.healthCap += 25
        self.say(f"Jipii! Nousin tasolle {self.level}, ja sain uuden esineen!", 0.1)
        self.level += 1
        self.app.roundInfo["levelUps"] += 1
        self.updateStats({"Level" : self.level, "XP to next level" : self.app.levelUps[self.level-1]})
        self.sendHudInfo()
        self.reconnectJson = None
        self.pendingAppLU = False



    def eyeGlow(self):

        if not self.morphed:
            return

        pos1, pos2 = self.getEyePositions()

        for x in (pos1, pos2):
            
            eye = x.copy()

            POS = self.deltaPos + eye - v2(self.breatheIm.get_size()) / 2 + [0, self.breatheY]
            endC = self.team.color + [0]
            Particle(self.app, POS[0], POS[1], 
                     start_color = [255,255,255,255], end_color=endC, 
                    vel_x=random.uniform(-1, 1), vel_y=random.uniform(-1, 1), 
                    start_size=2, end_size= random.randint(10,20),
                    lifetime=10)

            #self.app.particle_system.create_fire(x[0], x[1], 1, start_color = [0, 255,255,255], end_color=[0,0,255,0], 
            #                                     vel_x=random.uniform(-0.01, 0.01), vel_y=random.uniform(0.01, 0.05), lifetime=10)
        
    def isBombCarrier(self):
        return self.team.getGodTeam().bombCarrier == self and not self.team.isCT()
    
    def levelUpClient(self):

        if not self.client:
            return    

        # Select 3 items (or 4 if a special item is present)
        choices = self.nextItems  # returns list of Item instances

        # Build minimal JSON info
        items_info = [{"name": item.name, "desc": item.desc} for item in choices]

        packet = {
            "type": "levelUpChoices",
            "items": items_info,
            "pawn": self.name,   # optional, to identify which pawn leveled up
        }
        json_packet = json.dumps(packet)
        self.reconnectJson = json_packet
        self.pendingAppLU = True
        # Send to client
        asyncio.run_coroutine_threadsafe(self.sendPacket(json_packet), self.app.loop)

    def tryToNade(self):

        if self.isManual(): return

        if self.gType == None: return

        if self.grenadeAmount <= 0: return

        if self.grenadePos:
            return
        if self.target:
            return
        
        if self.gType in [GrenadeType.FLASH.value, GrenadeType.FRAG.value, GrenadeType.TELE.value]:
            nadeType = "aggr"
        else:
            nadeType = "defensive"

        if not self.team.utilityPos[nadeType]:
            if self.app.GAMEMODE in ["SUDDEN DEATH", "TEAM DEATHMATCH", "ODDBALL", "TURF WARS"]:
                c = self.app.commonRoom.randomCell()
                self.team.addNadePos(c, nadeType)
                return
            elif self.app.GAMEMODE == "KING OF THE HILL":
                c = self.app.currHill.randomCell()
                self.team.addNadePos(c, nadeType)
                return
        
        pos = self.team.getGodTeam().getRandomNadePos(nadeType)
        if not isinstance(pos, (list, tuple)):
            return
        
        dist = self.app.getDistFrom(self.getOwnCell(), pos)
        if dist > 20 + 10*self.itemEffects["utilityUsage"]: return
        
        if nadeType == "aggr":
        
            if self.canSeeCell(pos):
                return
            
            if 10 > dist:
                return
            
            teamPawns = self.team.getPawns()
            for pawn in teamPawns:
                dist = self.app.getDistFrom(pawn.getOwnCell(), pos)
                if 8 > dist:
                    return

        self.grenadePos = pos
        self.team.deleteNadePos(pos, nadeType)
        #self.gType = random.randint(0,1)

        self.say(random.choice([
            "Lentää!",
            "Instanade",
            "Älkää huoliko tiimitoverit! Pelastan teidät!",
            "Maken valo",
            "Täältä pesee",
            "Jumpthrowi",
            "Tätä lineuppia on jyynätty",
            "Inshallah",
            "Allah ohjaa kättäni",
            "Kuolema vihulle!"
            ]))

    def tick(self):

        self.ONSCREEN = False

        if self.drinkTimer > 0:
            self.drinkTimer -= self.app.deltaTimeR

        if self.immune > 0:
            self.immune -= self.app.deltaTime

        #self.teamColor = self.team.color

        if self.BOSS:
            if self.app.GAMEMODE != "FINAL SHOWDOWN":
                self.respawnI = 2


        if self.weapon:
            self.weapon.tryToDisableLazer()


        #########
        if self.respawnI > 0:

            if self.app.GAMEMODE == "SUDDEN DEATH":
                return

            if not self.BOSS:
                if self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team and self.app.GAMEMODE == "ODDBALL":
                    self.respawnI -= self.app.deltaTime*0.25
                else:
                    self.respawnI -= self.app.deltaTime

            self.killsThisLife = 0
            self.dropSkull()
            return
        
        if self.killed:
            self.killed = False
            self.reset()
            self.app.particle_system.create_healing_particles(self.pos[0], self.pos[1])

        self.killed = False

        #########
        if self.gType != None:
            if self.grenadeAmount <= 1 * self.itemEffects["utilityUsage"]:
                self.grenadeReloadI += self.app.deltaTime * self.itemEffects["utilityUsage"]
                if self.grenadeReloadI >= 20:
                    self.grenadeAmount += 1
                    self.grenadeReloadI = 0

            if not self.app.PEACEFUL and self.app.ENABLEGRENADES:
                self.tryToNade()

        #########
        if self.grenadePos:
            self.currWeapon = self.grenades[self.gType]

        elif self.carryingSkull():
            if self.app.skull.name == "SKULL":
                self.currWeapon = self.skullWeapon
            else:
                self.currWeapon = self.bombWeapon

        elif self.buildingTarget and not self.target:
            self.currWeapon = self.hammer

        else:           
            self.currWeapon = self.weapon
        
        #########

        #DELTATIMESAVE = self.app.deltaTime
        #self.app.deltaTime *= self.itemEffects["timeScale"]

        self.ONSCREEN = self.app.onScreen(self.pos)

        if self.ULT_TIME > 0:
            self.ULT_TIME -= self.app.deltaTime
            self.ULT = True
        else:
            self.ULT = False


        if self.itemEffects["turnCoat"]:
            self.handleTurnCoat()

        if self.flashed > 0:
            self.flashed -= self.app.deltaTime
            self.flashed = max(0, self.flashed)
        else:
            self.flashedBy = None

        if self.walkTo:
            if not self.route:
                stopMod = min(1.0, 0.25 + 0.75*(self.app.getDistFrom(self.pos, self.walkTo)/(2*self.app.tileSize)))
            else:
                stopMod = 2.0
            if self.walkingSpeedMult < stopMod:
                self.walkingSpeedMult += self.app.deltaTime * 2
            else:
                self.walkingSpeedMult -= self.app.deltaTime * 2
            
        else:
            self.walkingSpeedMult -= self.app.deltaTime * 2

        self.walkingSpeedMult = max(0.0, min(1.0, self.walkingSpeedMult))

        if not self.app.PEACEFUL:
            if self.xpI > 0:
                self.xpI -= self.app.deltaTime
            else:
                self.xpI = 15
                self.gainXP(1)

        if self.outOfCombat > 0:
            self.outOfCombat -= self.app.deltaTime
        
        if self.health < self.getHealthCap():
            if self.outOfCombat <= 0 or self.itemEffects["instaHeal"] or self.ULT:
                self.health += self.getRegenRate() * self.app.deltaTime
                self.health = min(self.health, self.getHealthCap())
        
        if self.enslaved:
            self.health = min(self.health, self.getHealthCap())


        if self.xp >= self.app.levelUps[self.level-1] and not self.app.pendingLevelUp:

            if self.xp >= self.app.levelUps[self.levelUpCreatedFor] and self.levelUpCreatedFor == self.level - 1:
                self.levelUpCreatedFor += 1
                self.app.particle_system.create_level_up_indicator(self.pos[0], self.pos[1])
                if self.client:
                    self.levelUpClient()

            if not self.client: 
                if self.NPC or self.app.ITEM_AUTO:
                    self.levelUp()
                else:
                    self.app.pendingLevelUp = self # Old implementation, the screen displays the item choices. 

        if not self.tripped and not self.defusing():
            if not self.isManual():
                self.think()
                self.walk()
                if not self.app.PEACEFUL:
                    self.shoot()
            else:
                self.walkManual()
                self.weapon.fireFunction(self.weapon)

        if self.tripped:
            self.tripI = min(self.tripI + self.app.deltaTime, 1.0)
            if self.tripI >= 1.0:
                self.getUpI += self.app.deltaTime
            if self.getUpI >= 0.5:
                self.getUpI = 0
                if random.uniform(0, 1) < 0.25:
                    self.tripped = False
                    self.say("Päätä särkee!", 0.2)
        else:
            self.tripI = max(self.tripI - self.app.deltaTime * 3, 0.0)
        
        

        if self.app.skull and self.getOwnCell() == self.app.skull.cell and not self.app.objectiveCarriedBy and not self.ULT: # Pick up skull

            if self.app.GAMEMODE == "ODDBALL" or (self.app.GAMEMODE == "DETONATION" and not self.team.detonationTeam and not self.app.skull.planted):

                self.app.objectiveCarriedBy = self
                self.say("Meikäläisen kallopallo!", 1)
                if self.app.GAMEMODE == "ODDBALL":
                    self.app.notify(f"{self.team.getName()} PICKED UP SKULL", self.team.getColor())
                    #self.app.cameraLinger = 0
                    #self.app.cameraLock = self
                else:
                    self.team.getGodTeam().bombCarrier = self
                self.route = None
                self.walkTo = None
                #self.app.cameraLock = self
        
        if self.ONSCREEN:
            newPos = self.handleSprite()
            if self.BOSS:
                self.handleSprite(head=True)
        else:
            newPos = self.pos.copy()
        
        
        self.deltaPos = newPos * 0.35 + self.deltaPos * 0.65

        # Draw an arc to resemble a circle around the player

        self.hitBox.center = self.pos.copy()

        #pygame.draw.arc(self.app.screen, (255, 255, 255), arcRect, 0, math.pi)

        #self.app.screen.blit(breatheIm, self.deltaPos - v2(breatheIm.get_size()) / 2 + [0, breatheY]  - self.app.cameraPosDelta)
        #if not self.tripped:

        self.buildingJumpOffset = 0
        self.buildingBounceOffset = 0
        self.buildingRotationOffset = 0

        if not self.BOSS:
            self.dualwield = self.carryingSkull() or self.itemEffects["dualWield"]

        self.currWeapon.tick()

        if self.dualwield and self.dualWieldWeapon:
            self.dualWieldWeapon.tick() 

        if self.carryingSkull():
            self.tryToTransferSkull()

            



        if self.itemEffects["playMusic"]:
            d = (self.pos - self.app.cameraPosDelta - v2(self.app.res)/2).length()
            self.app.mankkaDistance = min(self.app.mankkaDistance, d) 


        # Draw name

            

        #t = self.app.font.render(f"{self.name}", True, (255, 255, 255))
        #self.app.screen.blit(t, (self.pos.x - t.get_width() / 2, self.pos.y - t.get_height() - 70) - self.app.cameraPosDelta)

        self.handleTurfWar()
        self.handleKOTH()

        cx, cy = self.getOwnCell()

        cell_pos = (int(cx), int(cy))  # ensure integer keys

        if cell_pos in self.app.FireSystem.cells:
            cell_data = self.app.FireSystem.cells[cell_pos]
            firer = cell_data["firer"]    # extract the firer for this fire
            self.takeDamage(30 * self.app.deltaTime, firer, False, "fire")
        

        if not self.app.PEACEFUL and cx*200 + cy in self.app.shitDict:
            s = self.app.shitDict[cx*200 + cy]
            if s.owner.team != self.team and not self.tripped:
                self.trip()
                s.kill()

        self.hurtI -= self.app.deltaTime
        self.hurtI = max(0, self.hurtI)
        self.cameraLockI += self.app.deltaTimeR
        self.cameraLockI = self.cameraLockI%0.5
        if self.app.MINIMAPTEMP:
            pygame.draw.rect(self.app.MINIMAPTEMP, self.teamColor, [cx*self.app.MINIMAPCELLSIZE, cy*self.app.MINIMAPCELLSIZE, self.app.MINIMAPCELLSIZE,self.app.MINIMAPCELLSIZE])

        if self.itemEffects["hat"]:
            self.topHat = pygame.transform.rotate(self.app.topHat, self.rotation)

        if self.ULT:
            self.eyeGlow()

        self.handlePawnAngle()

        self.saveState()

        #pos = self.getPosInTime(1.0)
        #self.app.debugCells.append(pos)

        #x,y = self.getOwnCellFloat()
        #dist = 10
        #if not self.app.PEACEFUL and self is self.app.cameraLock:
        #    allCells = self.app.map.marchRayAll(x,y, -math.degrees(self.aimAt), int(dist)+1)
        #    self.app.debugCells += list(allCells)

        #self.app.deltaTime = DELTATIMESAVE

    def handleSprite(self, head = False):
        if not head:
            tempIm = self.imagePawn.copy() if self.facingRight else self.imagePawnR.copy()
        else:
            tempIm = self.imagePawnHead.copy() if self.facingRight else self.imagePawnHeadR.copy()

        if self.hurtI > 0:
            I = int(9*self.hurtI/0.25)

            hurtIm = self.hurtIm[0 if self.facingRight else 1][I]
            if self.BOSS:
                if head:
                    tempIm.blit(hurtIm, self.head_rect.topleft, self.head_rect)
                else:
                    tempIm.blit(hurtIm, self.body_rect.topleft, self.body_rect)
            else:
                tempIm.blit(hurtIm, (0,0))

        if self.flashed > 0:
            I = int(9*min(1, self.flashed))

            flashIm = self.flashIm[0 if self.facingRight else 1][I]
            if self.BOSS:
                if head:
                    tempIm.blit(flashIm, self.head_rect.topleft, self.head_rect)
                else:
                    tempIm.blit(flashIm, self.body_rect.topleft, self.body_rect)
            else:
                tempIm.blit(flashIm, (0,0))
        
        breathingMod = 1 if not self.itemEffects["playMusic"] else 5
        if not head:
            self.breatheI += (self.app.deltaTime * breathingMod) % 2

        
        tempIm = pygame.transform.scale_by(tempIm, [1 + 0.05 * math.sin(self.breatheI * 2 * math.pi) * breathingMod, 1 + 0.05 * math.cos(self.breatheI * 2 * math.pi) * breathingMod])
        self.breatheY = 2.5*math.sin(self.breatheI * 2 * math.pi) * breathingMod

        #if self.app.cameraLock == self and self.route:
        #    pygame.draw.rect(self.app.screen, [255,0,0], [self.route[0][0] * 70 - self.app.cameraPosDelta[0], self.route[0][1] * 70- self.app.cameraPosDelta[1], 70, 70])
        

        self.yComponent = 0
        self.xComponent = 0
        self.rotation = 0
        yAdd = 0
        Addrotation = 0
        if self.walkTo is not None:
            # The player should be swinging from side to side when walking
            self.yComponent = abs(math.sin(self.stepI * 2 * math.pi)) * 30 * self.walkingSpeedMult
            # The player should move left and right when walking
            self.xComponent = math.cos(self.stepI * 2 * math.pi) * 30 * self.walkingSpeedMult
            self.rotation = math.cos(self.stepI * 2 * math.pi) * 15 * self.walkingSpeedMult
            Addrotation = 0
            if self.facingRight:
                Addrotation -= self.currWeapon.runOffset * 22 * self.walkingSpeedMult
            else:
                Addrotation += self.currWeapon.runOffset * 22 * self.walkingSpeedMult
            
            yAdd += self.currWeapon.runOffset * 15 * self.walkingSpeedMult


        if self.facingRight:
            self.xComponent += self.buildingBounceOffset
            self.rotation += self.buildingRotationOffset
        else:
            self.xComponent -= self.buildingBounceOffset
            self.rotation -= self.buildingRotationOffset
        self.yComponent += self.buildingJumpOffset

        totalRot = self.rotation + Addrotation

        #self.breatheIm = pygame.transform.rotate(self.breatheIm, totalRot)

        newPos = self.pos - [self.xComponent, self.yComponent - yAdd]
        tripRotation = 0
        # TRIPPING:
        if self.tripI > 0:
            fall_offset = self.tripI ** 2
    
            # Y movement shaped: fast up, slow linger, hard drop
            shaped = math.sin(self.tripI * math.pi)  # [0..1..0], slow fall
            rotation = math.sin(self.tripI * 0.5 * math.pi)  # [0..1]]
            y_off = -shaped * 150  # peak height = -150 px

            
            tripRotation = self.tripRot * rotation
            newPos += [0, y_off]

        self.rotation = totalRot + tripRotation
        
        if not head:
            self.breatheIm = pygame.transform.rotate(tempIm, self.rotation)
        else:
            self.headIm = pygame.transform.rotate(tempIm, self.rotation)

        if self.BOSS:
            self.npcPlate = self.app.fontSmaller.render("GOD", True, self.teamColor)

        elif self.NPC:
            self.npcPlate = self.app.fontSmaller.render("NPC", True, self.teamColor)

        if self.immune > 0:
            healthText = "INF"
            healthColor = self.app.ATR.getRainBowColor(speed=500)
        else:
            healthText = str(int(self.health)).zfill(3)
            healthColor = heat_color(1 - self.health/self.getHealthCap())

        self.namePlate = combinedText(self.name, self.teamColor, " +" + healthText, healthColor, f" LVL {self.level}",[255,255,255], font=self.app.font)

        if self.cheater:
            self.cheatPlate = self.app.ATR.render(self.app.font, "CHEATER", [255,255,255], wave_amp=3, rainbow=True, rainbow_speed=300)

        
        return newPos
    
    def defusing(self):
        return self.app.GAMEMODE == "DETONATION" and self.app.skull.defusedBy == self


    def carryingSkull(self):
        return self.app.objectiveCarriedBy == self
    
    def handleKOTH(self):
        if self.app.GAMEMODE != "KING OF THE HILL":
            return
        if not hasattr(self.app, "map"):
            return
        x, y = self.getOwnCell()
        if self.app.currHill.contains(x, y):
            self.app.currHill.pawnsPresent.append(self.team.i)
            
    
    def handleTurfWar(self):
        if self.app.GAMEMODE != "TURF WARS":
            return
        
        if not hasattr(self.app, "map"):
            return

        x, y = self.getOwnCell()
        for r in self.app.map.rooms:
            if r.contains(x, y):
                r.pawnsPresent.append(self.team.i if not self.enslaved else self.team.enslavedTo)
                self.currentRoom = r
                return

    def tryToTransferSkull(self):
        p: "Pawn" = random.choice(self.app.pawnHelpList)
        if p.team != self.team:
            return
        if p.killed:
            return
        if not p.isPawn: return
        cx, cy = self.getOwnCell()
        c2x, c2y = p.getOwnCell()
        if abs(cx - c2x) > 2 or abs(cy - c2y) > 2:
            return
        
        if self.level <= p.level:
            return
        
        if p.ULT:
            return
        
        self.app.objectiveCarriedBy = p
        p.route = None
        p.walkTo = None
        self.route = None
        self.walkTo = None
        if self.app.skull.name == "BOMB":
            self.team.getTerroristTeam().bombCarrier = p

    def handlePawnAngle(self):
        aimAt = None
        if self.target:
            aimAt = math.radians(self.currWeapon.ROTATION)
        elif self.walkTo:
            direction = self.walkTo - self.pos
            if direction.length_squared() > 0:
                aimAt = math.atan2(-direction.y, direction.x)
        if aimAt != None:
            self.aimAt = lerp_angle(self.aimAt, aimAt, 0.1)

        
    def marchCells(self, angle, dist = 3):
        x,y = self.getOwnCell()
        cell = self.app.map.marchRay(x,y, angle, dist)
        return cell

        

    def render(self):

        #self.ONSCREEN = self.app.onScreen(self.pos)

        if self.killed:
            return
        
        if not self.ONSCREEN and not self.app.PLAYBACKDEMO:
            return
        
        #if not hasattr(self, "breathIm"):
        #    return
        

        #L = 200
        #dx = math.cos(self.aimAt) * L
        #dy = -math.sin(self.aimAt) * L
#
        #end = self.pos + pygame.Vector2(dx, dy) - self.app.cameraPosDelta
#
        #pygame.draw.line(
        #    self.app.DRAWTO,
        #    self.teamColor,
        #    self.pos - self.app.cameraPosDelta,
        #    end,
        #    width=2
        #)

        BASEPOS = self.app.convertPos(self.deltaPos)
        RS = self.app.RENDER_SCALE

        self.arcRect = pygame.Rect(BASEPOS.x, BASEPOS.y + 50*RS, 0, 0)

        imwidth = max(100 * self.app.RENDER_SCALE, self.breatheIm.get_width())

        self.arcRect.inflate_ip(imwidth, imwidth/2)

        camera = self.app.isCameraLocked(self)

        if camera:
            I = self.cameraLockI*2

            arcRectI = self.arcRect.copy()
            arcRectI.inflate_ip(imwidth*I, imwidth/2*I)

        pygame.draw.arc(self.app.DRAWTO, self.teamColor, self.arcRect, 0, 2*math.pi, width=4)

        for aPlus in [-math.pi/3, math.pi/3]:
            dx = self.arcRect.center[0] + math.cos(self.aimAt + aPlus) * self.arcRect.width/2
            dy = self.arcRect.center[1] - math.sin(self.aimAt + aPlus) * self.arcRect.height/2
            pygame.draw.line(self.app.DRAWTO, self.teamColor, self.arcRect.center, (dx,dy), width=2)
            #pygame.draw.arc(self.app.DRAWTO, self.teamColor, self.arcRect, self.aimAt + aPlus, self.aimAt - aPlus, 5)
            

        if camera:
            pygame.draw.arc(self.app.DRAWTO, self.teamColor, arcRectI, 0, 2*math.pi, width=2)

            #cell = self.marchCells(-self.aimAt, 5)
            #self.app.highLightCell(cell)

        heightOffset = v2(0, - self.height/2 + 30) * RS

        switchSides = math.pi/2 <= self.aimAt <= 3*math.pi/2

        
        self.app.DRAWTO.blit(self.breatheIm, BASEPOS - v2(self.breatheIm.get_size()) / 2 + [0, self.breatheY] + heightOffset)
        if self.BOSS:
            if self.app.babloLyricCurrent:
                heightOffsetHead = v2(0, -((1 - self.app.babloLyricNorm)**2) * 100)
                tripRotation = self.tripRot * math.sin(self.tripI * 0.5 * math.pi)
                heightOffsetHead.rotate(tripRotation)
            else:
                heightOffsetHead = v2(0,0)
            self.app.DRAWTO.blit(self.headIm, BASEPOS - v2(self.headIm.get_size()) / 2 + [0, self.breatheY] + heightOffset + heightOffsetHead)

        if self.itemEffects["hat"]:
            self.app.DRAWTO.blit(self.topHat, BASEPOS + [-self.xComponent*0.2, self.breatheY - self.yComponent - self.weapon.recoil*20] + self.apexPawn - v2(self.topHat.get_size())/2)

        #if not self.tripped:
        
        if self.dualwield and self.dualWieldWeapon:
            if not switchSides:
                self.dualWieldWeapon.render() 
                self.currWeapon.render()
            else:
                self.currWeapon.render()
                self.dualWieldWeapon.render() 
        else:
            self.currWeapon.render()

        if self.BOSS:
            self.app.DRAWTO.blit(self.npcPlate, (BASEPOS.x - self.npcPlate.get_width() / 2, BASEPOS.y - self.npcPlate.get_height() - self.height))

        elif self.NPC:
            self.app.DRAWTO.blit(self.npcPlate, (BASEPOS.x - self.npcPlate.get_width() / 2, BASEPOS.y - self.npcPlate.get_height() - self.height + 55))

        self.app.DRAWTO.blit(self.namePlate, (BASEPOS.x - self.namePlate.get_width() / 2, BASEPOS.y - self.namePlate.get_height() - self.height + 30))
        if self.cheater and self.cheatPlate:
            self.app.DRAWTO.blit(self.cheatPlate, (BASEPOS.x - self.cheatPlate.get_width() / 2, BASEPOS.y - self.cheatPlate.get_height() - self.height - 5))


        if self.BOSS:
            t2 = self.app.fontLarge.render(self.app.babloLyricCurrent, True, [255,255,255])
            t2.set_alpha(int((1-self.app.babloLyricNorm**2)*255))
            self.app.DRAWTO.blit(t2, (BASEPOS.x - t2.get_width() / 2, BASEPOS.y - t2.get_height() - self.height + 140))


        elif self.textBubble:
            t2 = self.app.font.render(self.textBubble, True, [255,255,255])
            self.app.DRAWTO.blit(t2, (BASEPOS.x - t2.get_width() / 2, BASEPOS.y - t2.get_height() - self.height + 60))
        
        elif self.flashed > 0:
            t2 = self.app.font.render("FLASHED", True, [255,255,255])

            i = int(min(1, self.flashed) * 255)
            t2.set_alpha(i)

            self.app.DRAWTO.blit(t2, (BASEPOS.x - t2.get_width() / 2, BASEPOS.y - t2.get_height() - self.height + 60))

        elif self.revengeHunt():
            t2 = self.app.font.render(f"HUNTING FOR {self.lastKiller.name}!!!", True, [255,255,255])
            self.app.DRAWTO.blit(t2, (BASEPOS.x - t2.get_width() / 2, BASEPOS.y - t2.get_height() - self.height + 60))

        elif self.currWeapon.isReloading():
            t2 = self.app.fontSmaller.render(f"RELOADING", True, [255,255,255])
            self.app.DRAWTO.blit(t2, (BASEPOS.x - t2.get_width() / 2, BASEPOS.y - t2.get_height() - self.height + 60))

        elif self.enslaved:
            t2 = self.app.fontSmaller.render(f"Orja", True, self.app.getTeamColor(self.team.i))
            self.app.DRAWTO.blit(t2, (BASEPOS.x - t2.get_width() / 2, BASEPOS.y - t2.get_height() - 40))

        #if not self.app.PEACEFUL and self.app.cameraLock == self:
        #    self.renderInfo()

        


    
    def distanceToPawn(self, pawn):
        return self.pos.distance_to(pawn.pos)

    def skullCarriedByOwnTeam(self):
        return self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team


    def getRouteTo(self, endPos = None, endPosGrid = None, movement_type = MovementType.GROUND):
        if endPos:
            endPos = (int(endPos[0]/self.app.tileSize), int(endPos[1]/self.app.tileSize))

        elif endPosGrid:
            endPos = tuple((int(endPosGrid[0]), int(endPosGrid[1])))

        startPos = (int(self.pos[0]/self.app.tileSize), int(self.pos[1]/self.app.tileSize))

        if startPos == endPos:
            return
        if not endPos:
            return

        self.route = self.app.arena.pathfinder.find_path(startPos, endPos, movement_type=movement_type)

        self.advanceRoute()

    


    def advanceRoute(self):
        if not self.route:
            return
        self.walkTo = v2(self.route[0]) * self.app.tileSize + [self.app.tileSize/2, 0]
        self.route.pop(0)


    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))
    
    def getOwnCell(self):
        return self.v2ToTuple((self.pos + [0, self.app.tileSize/2]) / self.app.tileSize)
    
    def getOwnCellFloat(self):
        p = (self.pos + [0, self.app.tileSize/2]) / self.app.tileSize
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
    
    def canSeeCell(self, c2, c1=None):
        if not c1:
            c1 = self.getOwnCell()
        return self.app.map.can_see(c1[0], c1[1], c2[0], c2[1])



def lerp_angle(a, b, t):
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * t