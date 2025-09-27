from rembg import remove
from PIL import Image
import io
import pygame
from pygame.math import Vector2 as v2
import random
import os
import math
import numpy as np
from imageprocessing.imageProcessing import gaussian_blur, trim_surface, remove_background, remove_background_bytes, generate_corpse_sprite, set_image_hue_rgba, colorize_to_blood, get_or_remove_background
from particles.blood import BloodParticle
from killfeed import KillFeed
from utilities.explosion import Explosion
from particles.bloodSplatter import BloodSplatter
from imageprocessing.pixelSort import pixel_sort_surface
from imageprocessing.faceMorph import getFaceLandMarks, processFaceMorph, get_or_load_landmarks
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
import asyncio
if TYPE_CHECKING:
    from main import Game

from pawn.behaviour import PawnBehaviour
from pawn.getStat import getStat
from pawn.tts import EspeakTTS
import base64
from pawn.teamLogic import Team


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


class Pawn(PawnBehaviour, getStat):
    def __init__(self, app: "Game", pawnName, pawnAvatarEncoded, client):
        self.app: "Game" = app
        # extract the name from the path
        self.name = pawnName
        self.client = client
        self.GENERATING = True

        super().__init__()
        


        # pawnAvatarEncoded is encoded as base64

        info = infoBar(self.app, f"{self.name}: Removing BG")

        # decode base64
        #image_bytes = base64.b64decode(pawnAvatarEncoded)

        # remove background in memory
        bg_removed_bytes = get_or_remove_background(self.app, pawnAvatarEncoded)

        # convert to pygame.Surface
        img = Image.open(io.BytesIO(bg_removed_bytes)).convert("RGBA")
        mode = img.mode
        size = img.size
        data = img.tobytes()
        image = pygame.image.frombuffer(data, size, mode)
            
        self.textBubble = None

        image = trim_surface(image)


        self.defaultPos()


        self.NPC = not bool(self.client)
        if self.client == "DEBUG":
            self.client = None

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

        self.millionaireImage = pygame.transform.scale_by(self.levelUpImage.copy(), 300 / image.get_size()[1])
        self.millionaireImage = pygame.transform.flip(self.millionaireImage, True, False)

        self.currentRoom = None



        #pygame.draw.circle(self.imagePawn, [255,0,0], self.left_eye_center*100, 5)
        #pygame.draw.circle(self.imagePawn, [255,0,0], self.right_eye_center*100, 5)

        self.hudImage = pygame.transform.scale_by(self.levelUpImage.copy(), 200 / self.levelUpImage.get_size()[1])


        enc = pygame.transform.scale_by(self.hudImage, 40 / self.hudImage.get_size()[1])

        self.encodedImage = surface_to_base64(enc)

        info.text = f"{self.name}: Pixel sorting"
        

        self.facingRight = True
        self.app.pawnHelpList.append(self)
        self.team: Team = None

        I = self.app.pawnHelpList.index(self)%self.app.playerTeams
        self.app.allTeams[I].add(self)

        self.teamColor = self.team.color

        self.reconnectJson = None
        self.pendingAppLU = False


        self.breatheI = random.uniform(0, 1)
        self.thinkEvery = 0.5 # seconds
        self.thinkI = random.uniform(0, self.thinkEvery)
        self.walkTo = None
        self.route = None
        self.speed = 400

        self.vel = v2(0,0)

        self.stepI = 0 
        self.stats = {
            "kills": 0,
            "deaths": 0,
            "damageDealt": 0,
            "damageTaken": 0,
            "teamkills": 0,
            "suicides": 0,
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
        self.hitBox = pygame.Rect(self.pos[0], self.pos[1], 100, 100)

        self.yComponent = 0
        self.xComponent = 0
        self.rotation = 0

        

        self.healthRegen = 10
        self.outOfCombat = 0
        self.loseTargetI = 0
        self.pastItems = []
        

        self.xp = 0
        self.xpI = 15
        self.enslaved = False

        self.weapon: Weapon = None
        
        self.app.skullW.give(self)
        self.skullWeapon = self.weapon

        self.app.hammer.give(self)
        self.hammer = self.weapon

        self.cameraLockI = 0
        self.onCameraTime = 0

        info.text = f"{self.name}: Giving a weapon"
        weapon = random.choice(self.app.weapons)
        weapon = self.app.pistol2

        if self.app.giveWeapons:
            weapon = random.choice(self.app.weapons)

        #weapon = self.app.hammer

        weapon.give(self)  # Give the AK-47 to this pawn
        

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

        self.tripped = False
        self.tripI = 0.0  # [0..1] animation progress
        self.getUpI = 0
        self.tripRot = random.choice([-90, 90])  # fall direction

        self.shopCurrWeapon = random.choice(self.app.weapons)

        self.building = False
        self.buildingTarget = None  # Building object being constructed
        self.buildingI = 0  # Animation timer
        self.hammerWeapon = None  # Hammer weapon instance
        self.buildingJumpOffset = 0
        self.buildingBounceOffset = 0
        self.buildingRotationOffset = 0
        

        self.getNextItems()
        
        self.referenceEffects = self.itemEffects.copy()
        info.text = f"{self.name}: sending"
        # self.client is the WebSocket

        self.app.clientPawns[self.client] = self

        if self.client:
            self.fullSync()

        info.text = f"{self.name}: Done!"
        info.killed = True

        self.app.notify(f"{self.name} joined!", self.teamColor)
        
        self.GENERATING = False

        #for x in range(3):
        #    i = random.choice(self.app.items)
        #    i.apply(self)

        #for x in range(50):
        #    self.getNextItems()
        #    self.levelUp()

    def fullSync(self):
        if not self.client:
            return       
        
        asyncio.run_coroutine_threadsafe(self.completeToApp(), self.app.loop)

        self.updateStats({"xp": int(self.xp), "currency": self.team.currency, "level" : self.level, "xpToNextLevel" : self.app.levelUps[self.level-1]})

        self.sendHudInfo()

        if self.pendingAppLU:
            asyncio.run_coroutine_threadsafe(self.sendPacket(self.reconnectJson), self.app.loop)
        
        self.sendKDStats()
        
        self.sendNemesisInfo(True, True)

        self.sendCurrWeaponShop()

    def pickAnother(self, exclude, pickFrom):
        exclude_set = set(exclude)
        candidates = [x for x in pickFrom if x not in exclude_set]
        if not candidates:
            raise ValueError("No available elements after exclusion")
        return random.choice(candidates)


    def canBuy(self):
        return self.shopCurrWeapon.price[0] <= self.team.currency
    def canReroll(self):
        return self.team.currency >= 25
    
    def rerollWeapon(self):
        self.team.currency -= 25
        self.shopCurrWeapon = self.pickAnother([self.shopCurrWeapon, self.weapon], self.app.weapons)
        self.sendCurrWeaponShop()
    
    def purchaseWeapon(self, weaponName):
        weapon = [weapon for weapon in self.app.weapons if weapon.name == weaponName][0]
        self.team.currency -= weapon.price[0]
        weapon.give(self)

        self.shopCurrWeapon = self.pickAnother([self.shopCurrWeapon, self.weapon], self.app.weapons)
        self.sendCurrWeaponShop()

    def sendCurrWeaponShop(self):
        
        p = self.shopCurrWeapon.getPacket()

        p = {"type": "shopUpdate", "nextWeapon": p}
        self.dumpAndSend(p)

        

        

    def sendKDStats(self):
        if not self.client:
            return
        
        kd = self.stats["kills"] / max(1, self.stats["deaths"])

        self.updateStats({"Kills": self.stats["kills"], "Deaths" : self.stats["deaths"], "KD" : f"{kd:.1f}"})

        

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
            self.pos = v2(random.randint(0, 1920), random.choice([-200, self.app.res[1] + 200]))
        else:
            self.pos = v2(random.choice([-200, self.app.res[0] + 200]), random.randint(0, 1080))
        self.deltaPos = self.pos.copy()

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

        landMarks = get_or_load_landmarks(self.app, rgb)
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
            if item not in self.nextItems and item.name not in self.pastItems:
                self.nextItems.append(item)
                if len(self.nextItems) == (4 if self.itemEffects["extraItem"] else 3):
                    break

    def searchEnemies(self):
        if self.app.PEACEFUL:
            return
        
        x = random.choice(self.app.ENTITIES)
        if x == self or not isinstance(x, Pawn):
            return
        
        if not self.revengeHunt() and not self.app.VICTORY and not self.app.GAMEMODE == "1v1":
            if not self.team.hostile(x):
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
            self.walkTo = v2(self.getOwnCell()) * self.app.tileSize
            self.route = None




    def dropSkull(self):
        if self.app.objectiveCarriedBy != self:
            return
        self.app.objectiveCarriedBy = None
        self.app.skull.cell = self.getOwnCell()

    def die(self):

        if random.uniform(0, 1) < self.itemEffects["saveChance"]:
            self.health = self.getHealthCap()
            return

        

        for x in range(random.randint(4,8)):
            self.app.bloodSplatters.append(BloodParticle(self.pos.copy(), 1.2, app = self.app))

        #if self.app.cameraLock == self and self.target:
        #    self.app.cameraLock = self.target
        #    print("Camera quick switch")

        if self.app.objectiveCarriedBy == self:
            self.dropSkull()

        self.killed = True
        if self.itemEffects["martyrdom"]:
            Explosion(self.app, self.pos.copy(), self, damage = 200 * self.itemEffects["weaponDamage"])

        
        self.app.playPositionalAudio(self.app.deathSounds, self.pos)


        c = random.choice(self.corpses)
        self.app.MAP.blit(c, self.pos - v2(c.get_size())/2)

        self.reset()

        if self.app.GAMEMODE == "1v1":
            self.respawnI = 2

        elif self.app.GAMEMODE == "TEAM DEATHMATCH":
            self.respawnI = 2

        elif self.carryingSkull() or (self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team):
            self.respawnI = 15
        else:
            self.respawnI = 10


        self.killsThisLife = 0
        self.deaths += 1
        self.stats["deaths"] += 1


    def getCellInSpawnRoom(self):
        SPAWNROOM = self.app.teamSpawnRooms[self.team.i]
        if SPAWNROOM:
            P = SPAWNROOM.randomCell()
        else:
            P = self.app.spawn_points[self.team.i]
        return P

    def reset(self):
        
        if self.app.GAMEMODE == "TURF WARS" and not self.app.PEACEFUL:
            self.enslaved = self.app.teamSpawnRooms[self.originalTeam].turfWarTeam != self.originalTeam
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
        

        self.killsThisLife = 0
        
        self.weapon.magazine = self.getMaxCapacity()
        self.weapon.currReload = 0
        self.tts.stop()
        self.sendKDStats()

    def takeDamage(self, damage, fromActor = None, thornDamage = False, typeD = "normal", bloodAngle = None):
        if self.killed:
            return

        if fromActor.itemEffects["allyProtection"] and not fromActor.team.hostile(self):
            return
        
        if typeD == "normal":
            damage /= self.defenceNormal()
        elif typeD == "energy":
            damage /= self.defenceEnergy()
        elif typeD == "explosion":
            damage /= self.defenceExplosion()

        self.stats["damageTaken"] += damage
        if fromActor:
            fromActor.stats["damageDealt"] += damage

        self.health -= damage
        self.outOfCombat = 2
        self.hurtI = 0.25

        if bloodAngle:
            for x in range(random.randint(int(damage/2),int(damage))):
                BloodSplatter(self.app, self.pos.copy(), bloodAngle)

        if self.itemEffects["thorns"] > 0 and not thornDamage and fromActor:
            fromActor.takeDamage(damage * self.itemEffects["thorns"], thornDamage = True, fromActor = self)

        if fromActor and fromActor.itemEffects["lifeSteal"] > 0:
            fromActor.health += damage * fromActor.itemEffects["lifeSteal"]

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
                if self.itemEffects["detonation"]:
                    self.say("Allahu Akbar!", 1)
                else:
                    self.say(onOwnDamage(), 0.5)

            elif fromActor.team == self.team:
                self.say(onTeamDamage(fromActor.name), 0.4)
            else:
                self.say(onTakeDamage(), 0.1)

    def gainXP(self, amount):
        if self.app.VICTORY or self.ULT:
            return
        self.xp += amount * self.itemEffects["xpMult"]

        
        self.updateStats({"xp": self.xp})

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

        xp = int((killed.level ** 0.5) * (max(1, killed.level - self.level)))

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

    def dumpAndSend(self, packet):
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
        self.level += 1

        self.updateStats({"level" : self.level, "xpToNextLevel" : self.app.levelUps[self.level-1]})
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
        
    
    def levelUpClient(self):
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

    def tick(self):

        self.ONSCREEN = self.onScreen()

        if self.ULT_TIME > 0:
            self.ULT_TIME -= self.app.deltaTime
            self.ULT = True
        else:
            self.ULT = False


        if self.itemEffects["turnCoat"]:
            self.handleTurnCoat()

        self.teamColor = self.team.color

        if self.respawnI > 0:

            if self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team:
                self.respawnI -= self.app.deltaTime*0.25
            else:
                self.respawnI -= self.app.deltaTime
            self.killsThisLife = 0
            self.dropSkull()
            return
        
        if self.killed:
            self.reset()
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
                
            if self.NPC or self.app.ITEM_AUTO:
                self.levelUp()
            elif not self.client:
                self.app.pendingLevelUp = self # Old implementation, the screen displays the item choices. 

        if not self.tripped:
            self.think()
            self.walk()
            if not self.app.PEACEFUL:
                self.shoot()

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
        
        

        if self.app.skull and self.getOwnCell() == self.app.skull.cell and not self.app.objectiveCarriedBy and not self.ULT:
            self.app.objectiveCarriedBy = self
            self.say("Meikäläisen kallopallo!", 1)
            self.route = None
            self.walkTo = None
            #self.app.cameraLock = self

        if self.ONSCREEN:
            newPos = self.handleSprite()
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

        if self.carryingSkull():
            self.skullWeapon.tick()
            self.tryToTransferSkull()

        elif self.buildingTarget and not self.target:
            self.hammer.tick()

        elif self.weapon:
            self.weapon.tick()    



        if self.itemEffects["playMusic"]:
            d = (self.pos - self.app.cameraPosDelta - v2(self.app.res)/2).length()
            self.app.mankkaDistance = min(self.app.mankkaDistance, d) 


        # Draw name

        if self.ONSCREEN:
            if self.NPC:
                self.npcPlate = self.app.fontSmaller.render("NPC", True, self.teamColor)

            self.namePlate = combinedText(self.name, self.teamColor, " +" + str(int(self.health)).zfill(3), heat_color(1 - self.health/self.getHealthCap()), f" LVL {self.level}",[255,255,255], font=self.app.font)

        #t = self.app.font.render(f"{self.name}", True, (255, 255, 255))
        #self.app.screen.blit(t, (self.pos.x - t.get_width() / 2, self.pos.y - t.get_height() - 70) - self.app.cameraPosDelta)

        self.handleTurfWar()

        cx, cy = self.getOwnCell()

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
            self.topHat = self.app.topHat.copy()
            self.topHat = pygame.transform.rotate(self.topHat, self.rotation)

        if self.ULT:
            self.eyeGlow()

    def handleSprite(self):
        self.breatheIm = self.imagePawn.copy() if self.facingRight else self.imagePawnR.copy()

        if self.hurtI > 0:
            I = int(9*self.hurtI/0.25)

            hurtIm = self.hurtIm[0 if self.facingRight else 1][I]

            self.breatheIm.blit(hurtIm, (0,0))

        breathingMod = 1 if not self.itemEffects["playMusic"] else 5

        self.breatheI += (self.app.deltaTime * breathingMod) % 2
        self.breatheIm = pygame.transform.scale_by(self.breatheIm, [1 + 0.05 * math.sin(self.breatheI * 2 * math.pi) * breathingMod, 1 + 0.05 * math.cos(self.breatheI * 2 * math.pi) * breathingMod])
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


            

        if self.facingRight:
            self.xComponent += self.buildingBounceOffset
            self.rotation += self.buildingRotationOffset
        else:
            self.xComponent -= self.buildingBounceOffset
            self.rotation -= self.buildingRotationOffset
        self.yComponent += self.buildingJumpOffset

        totalRot = self.rotation + Addrotation

        self.breatheIm = pygame.transform.rotate(self.breatheIm, totalRot)

        newPos = self.pos - [self.xComponent, self.yComponent - yAdd]

        # TRIPPING:
        if self.tripI > 0:
            fall_offset = self.tripI ** 2
    
            # Y movement shaped: fast up, slow linger, hard drop
            shaped = math.sin(self.tripI * math.pi)  # [0..1..0], slow fall
            rotation = math.sin(self.tripI * 0.5 * math.pi)  # [0..1]]
            y_off = -shaped * 150  # peak height = -150 px

            self.breatheIm = pygame.transform.rotate(self.breatheIm, self.tripRot * rotation)
            newPos += [0, y_off]
        
        return newPos


    def carryingSkull(self):
        return self.app.objectiveCarriedBy == self
    
    def handleTurfWar(self):
        if self.app.GAMEMODE != "TURF WARS":
            return
        
        if not hasattr(self.app, "map"):
            return

        x, y = self.getOwnCell()
        for r in self.app.map.rooms:
            if r.contains(x, y):
                r.pawnsPresent.append(self.team.i)
                self.currentRoom = r
                return

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
        p.route = None
        p.walkTo = None
        self.route = None
        self.walkTo = None
        

    def render(self):

        if self.killed:
            return
        
        if not self.ONSCREEN:
            return

        self.arcRect = pygame.Rect(self.pos.x - self.app.cameraPosDelta[0], self.pos.y + 50 - self.app.cameraPosDelta[1], 0, 0)
        self.arcRect.inflate_ip(120, 60)

        if self.app.cameraLock == self:
            I = self.cameraLockI/0.5

            arcRectI = self.arcRect.copy()
            arcRectI.inflate_ip(120*I, 60*I)

        pygame.draw.arc(self.app.DRAWTO, self.teamColor, self.arcRect, 0, 2*math.pi)

        if self.app.cameraLock == self:
            pygame.draw.arc(self.app.DRAWTO, self.teamColor, arcRectI, 0, 2*math.pi)

        self.app.DRAWTO.blit(self.breatheIm, self.deltaPos - v2(self.breatheIm.get_size()) / 2 + [0, self.breatheY]  - self.app.cameraPosDelta)

        if self.itemEffects["hat"]:
            self.app.DRAWTO.blit(self.topHat, self.deltaPos + [-self.xComponent*0.2, self.breatheY - self.yComponent - self.weapon.recoil*20]  - self.app.cameraPosDelta + self.apexPawn - v2(self.topHat.get_size())/2)

        #if not self.tripped:
        if self.app.objectiveCarriedBy == self:
            self.skullWeapon.render()

        elif self.buildingTarget and not self.target:
            self.hammer.render()

        elif self.weapon:
            self.weapon.render()      

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

        elif self.enslaved:
            
            t2 = self.app.fontSmaller.render(f"Orja", True, self.app.getTeamColor(self.originalTeam))
            self.app.DRAWTO.blit(t2, (self.pos.x - t2.get_width() / 2, self.pos.y - t2.get_height() - 40) - self.app.cameraPosDelta)

        #if not self.app.PEACEFUL and self.app.cameraLock == self:
        #    self.renderInfo()


    
    def distanceToPawn(self, pawn):
        return self.pos.distance_to(pawn.pos)

    def skullCarriedByOwnTeam(self):
        return self.app.objectiveCarriedBy and self.app.objectiveCarriedBy.team == self.team


    def getRouteTo(self, endPos = None, endPosGrid = None):
        if endPos:
            endPos = (int(endPos[0]/self.app.tileSize), int(endPos[1]/self.app.tileSize))

        elif endPosGrid:
            endPos = endPosGrid

        startPos = (int(self.pos[0]/self.app.tileSize), int(self.pos[1]/self.app.tileSize))

        self.route = self.app.arena.pathfinder.find_path(startPos, endPos)

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

    def getCell(self, pos):
        return self.v2ToTuple((pos + [0, self.app.tileSize/2]) / self.app.tileSize)

    def getVisibility(self):
        cell = self.getOwnCell()
        return self.app.map.get_visible_cells(cell[0], cell[1])
    
    def sees(self, target: "Pawn"):
        c1 = self.getOwnCell()
        c2 = target.getOwnCell()
        return self.app.map.can_see(c1[0], c1[1], c2[0], c2[1])



