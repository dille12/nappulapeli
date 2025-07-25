import pygame
import os

import pygame.gfxdraw
from pawn import Pawn
from weapon import Weapon
import random
from _thread import start_new_thread
from enemy import Enemy
import math
from pygame.math import Vector2 as v2
import time
from mapGen import ArenaGenerator, CellType
import numpy as np
from arenaWithPathfinding import ArenaWithPathfinding
from loadAnimation import load_animation
from item import Item
from items import getItems
from keypress import key_press_manager
from skull import Skull
import colorsys
def wait_for_file_ready(filepath, timeout=5, poll_interval=0.1):
    """Wait until the file is stable and readable, or timeout."""
    start_time = time.time()
    last_size = -1
    while time.time() - start_time < timeout:
        try:
            current_size = os.path.getsize(filepath)
            # If size hasn't changed for two polls, assume it's ready
            if current_size == last_size and current_size > 0:
                with open(filepath, "rb") as f:
                    f.read(1)
                return True
            last_size = current_size
        except Exception:
            pass
        time.sleep(poll_interval)
    return False

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



class Game:
    def __init__(self):
        self.res = v2(1920, 1080)
        self.screen = pygame.display.set_mode(self.res, pygame.SRCALPHA)  # Delay screen initialization
        self.darken = pygame.Surface(self.res).convert_alpha()
        self.mask = pygame.Surface(self.res, pygame.SRCALPHA).convert_alpha()
        self.darken.fill((0,0,0))
        self.darken.set_alpha(100)
        pygame.font.init()
        self.ENTITIES = []
        self.pawnHelpList = []
        self.playerFiles = []  # List to hold player objects
        self.particle_list = []
        self.playerFilesToGen = [] 
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font("texture/terminal.ttf", 20)  # Load a default font
        self.fontLarge = pygame.font.Font("texture/terminal.ttf", 50)  # Load a default font
        self.fontLevel = pygame.font.Font("texture/terminal.ttf", 35)  # Load a default font
        # image_path, damage, range, magSize, fireRate, fireFunction, reloadTime
        self.AK = Weapon(self, "AK-47", "texture/ak47.png", 10, 1600, 30, 8, Weapon.AKshoot, 1.5, "normal")
        self.e1 = Weapon(self, "Energy 1", "texture/energy1.png", 100, 3000, 5, 1, Weapon.Energyshoot, 2, "energy")
        self.e2 = Weapon(self, "Energy 2", "texture/energy2.png", 5, 1600, 1, 1.5, Weapon.RocketLauncher, 3, "explosion")
        self.e3 = Weapon(self, "Energy 3", "texture/energy3.png", 8, 1000, 40, 14, Weapon.Energyshoot, 0.8, "energy")
        self.pistol = Weapon(self, "Pistol", "texture/pistol.png", 25, 2000, 12, 3, Weapon.AKshoot, 0.3, "normal")

        self.skullW = Weapon(self, "Skull", "texture/skull.png", 1, 1000, 1, 1, Weapon.skull, 1, "normal")

        #self.timbs = Item("Timbsit", speedMod=["add", 300])


        print("AK created")
        #self.ENTITIES.append(Enemy(self))

        #for x in os.listdir("players"):
        #    self.ENTITIES.append(Pawn(self, "players/" + x))

        print("Game initialized")
        self.deltaTime = 1/60
        self.deltaTimeR = 1/60
        self.debugI = 0
        self.fontSmaller = pygame.font.Font("texture/terminal.ttf", 12)  # Smaller font for debug text
        self.pawnGenI = 0
        self.pawnGenT = 0
        self.map = ArenaGenerator(80, 60)

        # TEAM COUNT
        self.teams = 6

        self.map.generate_arena(room_count=int(self.teams*1.5)+4, min_room_size=8, max_room_size=20, corridor_width=3)
        self.killfeed = []
        self.keypress = []
        self.keypress_held_down = []

        self.cameraLinger = 2

        self.t1 = 1
        self.t2 = 1

        self.splitI = 0
        self.cameraLockTarget = v2(0,0)
        self.cameraLockOrigin = v2(0,0)

        

        self.arena = ArenaWithPathfinding(self.map)
        connectivity = self.arena.validate_arena_connectivity()
        print(f"Arena Connectivity: {connectivity}")

        self.spawn_points = self.arena.find_optimal_spawn_points(self.teams, min_distance=20)
        print(f"Spawn points: {self.spawn_points}")

        self.map.get_spawn_points()

        self.MAP = self.map.to_pygame_surface(cell_size=70)

        #floor_mask = pygame.Surface((80*70, 60*70))
        #self.wall_mask = pygame.Surface((80*70, 60*70), flags=pygame.SRCALPHA).convert_alpha()
        #for y in range(60):
        #    for x in range(80):
        #        if self.map.grid[y,x] != CellType.WALL.value:  # Your tile logic
        #            pygame.draw.rect(floor_mask, (55,55,55), (x*70, y*70, 70, 70))
        #        else:
        #            pygame.draw.rect(self.wall_mask, (0,0,0), (x*70, y*70, 70, 70))

        #self.MAP = floor_mask

        self.MINIMAP = self.map.to_pygame_surface(cell_size=3)
        self.MINIMAPTEMP = self.MINIMAP.copy()
        self.cameraPos = v2(0, 0)
        self.cameraPosDelta = self.cameraPos.copy()
        self.cameraVel = v2(0,0)

        self.dualCameraPos = v2(0, 0)
        self.dualCameraPosDelta = self.cameraPos.copy()
        self.dualCameraVel = v2(0,0)


        self.bulletSprite = pygame.image.load("texture/bullet.png").convert_alpha()
        self.bulletSprite = pygame.transform.scale(self.bulletSprite, [200, 5])

        self.energySprite = pygame.image.load("texture/lazer.png").convert_alpha()
        self.energySprite = pygame.transform.scale(self.energySprite, [220, 8])

        self.visualEntities = []
        self.explosion = load_animation("texture/expl1", 0, 31, size = [500,500])
        self.items = getItems()
        self.cameraLock = None

        self.levelUps = [round(10*(x+1) * (1.2) ** x) for x in range(100)]

        self.pendingLevelUp = None
        self.levelUpI = 5
        self.levelUpBlink = 1

        self.objectiveCarriedBy = None

        self.screenCopy1 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.screenCopy2 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)

        #entrance = self.map.get_entrance_position()
        routeBetweenSpawns = self.arena.pathfinder.find_path(self.spawn_points[0], self.spawn_points[1])
        midPoint = routeBetweenSpawns[int(len(routeBetweenSpawns)/2)]
        #if entrance:
        self.skull = Skull(self, midPoint)
        print("SKULL CREATED!")
        self.skullTimes = []
        for x in range(self.teams):
            self.skullTimes.append(0)

        pygame.mixer.init()
        self.ARSounds = [
            pygame.mixer.Sound("audio/assault1.wav"),
            pygame.mixer.Sound("audio/assault2.wav"),
            pygame.mixer.Sound("audio/assault3.wav"),
        ]

        self.deathSounds = [
            pygame.mixer.Sound("audio/death1.wav"),
            pygame.mixer.Sound("audio/death2.wav"),
            pygame.mixer.Sound("audio/death3.wav"),
        ]

        self.hitSounds = [
            pygame.mixer.Sound("audio/hit1.wav"),
            pygame.mixer.Sound("audio/hit2.wav"),
            pygame.mixer.Sound("audio/hit3.wav"),
            pygame.mixer.Sound("audio/hit4.wav"),
            pygame.mixer.Sound("audio/hit5.wav"),
            pygame.mixer.Sound("audio/hit6.wav"),
        ]

        self.explosionSound = [
            pygame.mixer.Sound("audio/explosion1.wav"),
            pygame.mixer.Sound("audio/explosion2.wav"),
            pygame.mixer.Sound("audio/explosion3.wav"),
        ]

        self.energySound = self.loadSound("audio/nrg_fire")
        self.shotgunSound = self.loadSound("audio/shotgun")
        self.silencedSound = self.loadSound("audio/silenced")
        if len(self.energySound) != 3:
            raise RuntimeError

        

        self.reloadSound = pygame.mixer.Sound("audio/reload.wav")
        self.meleeSound = pygame.mixer.Sound("audio/melee.wav")
        for x in self.ARSounds + [self.reloadSound]:
            x.set_volume(0.3)


    def playSound(self, l):
        for x in l:
            x.stop()
        random.choice(l).play()

    def loadSound(self, fileHint, startIndex = 1, suffix=".wav"):
        l = []
        while True:
            f = fileHint + str(startIndex) + suffix
            if os.path.exists(f):
                l.append(pygame.mixer.Sound(f))
                startIndex += 1

            else:
                return l

        
    def drawWalls(self):
        for x in self.wallRects:
            x2 = x.copy()
            x2.topleft -= self.cameraPos
            pygame.draw.rect(self.screen, [0,0,0], x2)

    def threadedGeneration(self, path):
        self.pawnGenI += 1
        print("Probing if file ready.")
        if wait_for_file_ready(path):
            print("File ready!")
            
            pawn = Pawn(self, path)
            pawn.team = len(self.pawnHelpList)%self.teams
            pawn.teamColor = self.getTeamColor(pawn.team)
            pawn.pos = v2(self.spawn_points[pawn.team]) * 70 + [35, 35]
            self.ENTITIES.append(pawn)
            
        else:
            print("Download was incomplete.")

        self.pawnGenI -= 1

    def getTeamColor(self, team):

        hue = (team * 1/self.teams) % 1.0  # Cycle hue every ~6 teams
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        return [int(r * 255), int(g * 255), int(b * 255)]

        if team == 0:
            return [255,0,0]
        elif team == 1:
            return [0,255,0]
        elif team == 2:
            return [0,0,255]
        elif team == 3:
            return [255,255,0]
        else:
            hue = (team * 0.15) % 1.0  # Cycle hue every ~6 teams
            r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
            return [int(r * 255), int(g * 255), int(b * 255)]
        

    def debugText(self, text):

        t = self.fontSmaller.render(str(text), True, [255,255,255])
        self.screen.blit(t, [self.res[0] - 20 - t.get_size()[0], 200 + self.debugI * 12])
        self.debugI += 1

    def smoothRotationFactor(self, angleVel, gainFactor, diff):
        dir = 1 if diff > 0 else -1
        gainFactor *= min(1, abs(diff) * 3)

        # Your original calculation - time needed to decelerate to zero
        if abs(angleVel) < 1e-6:  # Avoid division by zero
            decelarationTicks = 0
        else:
            decelarationTicks = abs(angleVel / gainFactor)
        # Your original calculation - distance covered while decelerating
        distanceDecelerating = angleVel * decelarationTicks - 0.5 * dir * gainFactor * decelarationTicks**2
        
        acceleratingMod = 1 if distanceDecelerating < diff else -1
        
        return acceleratingMod * gainFactor
    
    def getAngleFrom(self, fromPoint, toPoint):
        return math.radians(v2([0,0]).angle_to(toPoint - fromPoint)) 
    
    def rangeDegree(self, angle):
        return angle % 360
    
    def levelUpScreen(self):

        
       
        if self.levelUpBlink > 0:
            self.levelUpBlink -= self.deltaTimeR
        else:
            self.levelUpBlink = 1

        self.levelUpI -= self.deltaTimeR
        

        self.screen.blit(self.darken, (0,0))

        self.screen.blit(self.pendingLevelUp.levelUpImage, self.res/2 - [0, 300] - v2(self.pendingLevelUp.levelUpImage.get_size())/2)

        t = combinedText(self.pendingLevelUp.name, self.pendingLevelUp.teamColor, f" LEVELED UP (LVL {self.pendingLevelUp.level+1})", [255,255,255], font=self.fontLarge)
        self.screen.blit(t, self.res/2 - [0, 300] - v2(t.get_size())/2)

        r1 = pygame.Rect(self.res[0]/2 - 400, 800, 800, 30)
        pygame.draw.rect(self.screen, [255,255,255], r1, width=1)
        r2 = r1.copy()
        ir2 = max(0, 1-(5-self.levelUpI)/5)
        r2.width = ir2*796
        r2.height = 26
        r2.center = r1.center
        pygame.draw.rect(self.screen, [255,255*ir2,255*ir2], r2)

        for x in range(3):
            xpos = (x-1)*450 + self.res[0]/2
            item = self.pendingLevelUp.nextItems[x]

            t = self.fontLevel.render(item.name, True, [255,255,255])
            rPos = v2(xpos, 600) - v2(t.get_size())/2
            rect = pygame.Rect(rPos, t.get_size())
            
            if self.levelUpBlink > 0.75 and self.levelUpIndex == x:
                rect2 = rect.copy()
                i = ((1-self.levelUpBlink)/0.25)**2
                rect2.inflate_ip(30*i, 30*i)
                pygame.draw.rect(self.screen, [255,0,0], rect2, width=int(i*4))

            self.screen.blit(t, rPos)
            if rect.collidepoint(self.mouse_pos):
                c = [255,0,0]
                w = 2
                a = True
            else:
                c = [255,255,255]
                w = 1
                a = False
            pygame.draw.rect(self.screen, c, rect, width = w)
            if ("mouse0" in self.keypress and a) or (self.levelUpI <= 0 and x == self.levelUpIndex):
                item.apply(self.pendingLevelUp)
                self.pendingLevelUp.getNextItems()
                self.pendingLevelUp.level += 1
                self.pendingLevelUp.healthCap += 10
                self.pendingLevelUp = None
                self.resetLevelUpScreen()
                self.cameraVel = v2([0,0])
                return
                
                


    def tick(self):

        tickStartTime = time.time()
        
        key_press_manager(self)
        
        self.debugI = 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()  # Ensure the program exits cleanly

        
        
        

        # Sort entities by their y position for correct rendering order into a separate list to prevent modifying the list while iterating


        entities_temp = sorted(self.ENTITIES, key=lambda x: x.pos.y)
        CREATEDUAL = False

        if "space" in self.keypress:
            self.cameraLock = None

        if not self.cameraLock:
            #if self.objectiveCarriedBy:
            #    self.cameraLock = self.objectiveCarriedBy

            if self.pawnHelpList:
                e = sorted(self.pawnHelpList.copy(), key=lambda p: p.killsThisLife, reverse=True)
                
                for x in e:
                    if not x.killed:
                        self.cameraLock = x
                        break


        elif self.cameraLinger <= 0:
            if self.cameraLock.killed:
                self.cameraLock = None
                self.cameraLinger = 1
            else:
                self.cameraPos = self.cameraLock.pos - self.res/2
                if self.cameraLock.target:
                    CREATEDUAL = True
                    self.cameraLockTarget = self.cameraLock.target.pos.copy() * 0.1 + self.cameraLockTarget * 0.9
                    self.cameraLockOrigin = self.cameraLock.pos.copy()
        
        else:
            self.cameraLinger -= self.deltaTime
        
        if self.pendingLevelUp:
            #    self.cameraPos = self.pendingLevelUp.pos - self.res/2
            self.deltaTime *= 0.01


        #if self.skull:
        #    self.cameraPos = self.skull.pos - self.res/2
        

        if CREATEDUAL:

            self.splitI += self.deltaTime
            self.splitI = min(1, self.splitI)
        else:
            self.splitI -= self.deltaTime
            self.splitI = max(0, self.splitI)

        if self.splitI > 0:

            shiftI = (1-self.splitI)**2

            maxX = 1000 * shiftI

            if self.cameraLock and not self.cameraLock.killed:
                self.cameraLockOrigin = self.cameraLock.pos.copy()

            angle = self.getAngleFrom(self.cameraLockOrigin, self.cameraLockTarget) + math.pi/2

            shift = v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(-maxX)

            line1 = v2(math.cos(angle), math.sin(angle))*1920 + self.res/2 + shift
            line2 = v2(math.cos(angle+math.pi), math.sin(angle+math.pi))*1920 + self.res/2 + shift
            line3 = v2(math.cos(angle), math.sin(angle))*1920 + self.res/2 - v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*1200 + shift
            line4 = v2(math.cos(angle+math.pi), math.sin(angle+math.pi))*1920 + self.res/2 - v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*1200 + shift
            posToTargetTo = self.cameraLockOrigin + v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(-300 * (1-shiftI)) - self.res/2
            posToTargetTo2 = self.cameraLockTarget + v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(300+0.7*maxX) - self.res/2

        self.MINIMAPTEMP = self.MINIMAP.copy()
        for x in self.particle_list:
            x.tick()

        for x in entities_temp:
            x.tick()

        for x in self.visualEntities:
            x.tick()


        if self.objectiveCarriedBy:
            self.skullTimes[self.objectiveCarriedBy.team] += self.deltaTime

        if self.splitI > 0:
            self.cameraPos = posToTargetTo.copy()
            self.dualCameraPos = posToTargetTo2.copy()
        else:
            self.dualCameraPos = self.cameraPos.copy()

        CAMPANSPEED = 500000 * self.deltaTimeR
        #self.cameraVel[0] += self.smoothRotationFactor(self.cameraVel[0], CAMPANSPEED, self.cameraPos[0] - self.cameraPosDelta[0]) * self.deltaTimeR
        #self.cameraVel[1] += self.smoothRotationFactor(self.cameraVel[1], CAMPANSPEED, self.cameraPos[1] - self.cameraPosDelta[1]) * self.deltaTimeR
        self.cameraPosDelta = self.cameraPosDelta * 0.9 + self.cameraPos * 0.1#* self.deltaTimeR

        DUAL = False
        if self.splitI > 0:
            if self.cameraLockOrigin.distance_to(self.cameraLockTarget) > 600:
                DUAL = True


        for i in range(1 if not DUAL else 2):

            if not DUAL:
                self.DRAWTO = self.screen
                
            elif i == 0:
                self.DRAWTO = self.screenCopy1
            else:
                self.DRAWTO = self.screenCopy2

            self.DRAWTO.fill((0,0,0))

            if i == 1:
                SAVECAMPOS = self.cameraPosDelta.copy()
                self.cameraPosDelta = posToTargetTo2.copy()

            self.DRAWTO.blit(self.MAP, -self.cameraPosDelta)
            #self.DRAWTO.blit(self.wall_mask, -self.cameraPosDelta)

            for x in entities_temp:
                x.render()

            for x in self.visualEntities:
                x.render()

            if DUAL and i == 1:
                self.cameraPosDelta = SAVECAMPOS.copy()

        if DUAL:

            #self.screen.fill((0,0,0))
            self.screen.blit(self.screenCopy1, (0, 0))

            self.mask.fill((0, 0, 0, 0))
            pygame.draw.polygon(self.mask, [255, 255, 255, 255], (line1, line2, line4, line3))

            # Masking step: use mask to zero out non-polygon areas in screenCopy2
            self.screenCopy2.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            # True alpha blending
            self.screen.blit(self.screenCopy2, (0, 0))  # This now honors alpha channel

            pygame.draw.line(self.screen, [255, 255, 255], line1, line2, 3)
                        

        #self.drawWalls()

        self.debugText(f"FPS: {1/self.t2:.0f}")
        self.debugText(f"GEN: {self.pawnGenI:.0f}")
        self.debugText(f"ENT: {len(self.ENTITIES):.0f}")
        self.debugText(f"BENT: {len(self.particle_list):.0f}")
        self.debugText(f"CAM: {self.cameraVel}")
        self.debugText(f"PLU: {self.pendingLevelUp}")
        self.debugText(f"IDLE: {100*(1-self.t1/self.t2):.0f}")
        self.debugText(f"DUAL: {DUAL} {CREATEDUAL}")

        for x in self.killfeed:
            x.tick()


        y = 200

        for i, x in sorted(enumerate(self.skullTimes), key=lambda pair: pair[1], reverse=True):
            t = combinedText(f"TEAM {i + 1}: ", self.getTeamColor(i), f"{x:.1f} seconds", self.getTeamColor(i), font=self.font)
            self.screen.blit(t, [10, y])
            y += 30

        y += 80

        for x in sorted(self.pawnHelpList.copy(), key = lambda p: p.kills, reverse=True):

            t = combinedText(f"{x.name}: ", x.teamColor, f"{x.kills}/{x.deaths}", [255,255,255], font=self.font)
            self.screen.blit(t, [10,y])
            y += 30


        ox, oy = 3*self.cameraPosDelta/(70)
        w, h = 3*self.res/(70)
        
        pygame.draw.rect(self.MINIMAPTEMP, [255,0,0], (ox, oy, w, h), width=1)

        if self.objectiveCarriedBy:
            skullpos = self.objectiveCarriedBy.pos.copy()
        else:
            skullpos = self.skull.pos.copy()

        pygame.draw.circle(self.MINIMAPTEMP, [255,255,255], 3*skullpos/70, 6, width=1)
        
        self.screen.blit(self.MINIMAPTEMP, self.res - self.MINIMAP.get_size() - [10,10])



        if self.pendingLevelUp:
            self.levelUpScreen()
        else:
            self.resetLevelUpScreen()

        pygame.display.update()

        self.t1 = time.time() - tickStartTime

        self.deltaTimeR = self.clock.tick(144) / 1000
        self.t2 = time.time() - tickStartTime
        self.deltaTimeR = min(self.deltaTimeR, 1/30)
        self.deltaTime = self.deltaTimeR

        self.pawnGenT += self.deltaTime
        if self.pawnGenT > 1:
            self.pawnGenT -= 1
            for x in os.listdir("players/"):
                if x not in self.playerFiles and x not in self.playerFilesToGen:
                    print(x, "Not present")
                    self.playerFilesToGen.append(x)

        if self.pawnGenI < 3 and self.playerFilesToGen:

            x = random.choice(self.playerFilesToGen)
            self.playerFiles.append(x)
            self.playerFilesToGen.remove(x)
            start_new_thread(self.threadedGeneration, ("players/" + x, ))

        
    def resetLevelUpScreen(self):
        self.levelUpI = 3
        self.levelUpBlink = 1
        self.levelUpIndex = random.randint(0,2)


    def randomWeighted(self, *args):
        """
        Gets a random choice between a selected amount of arguments. Arguments are weights
        """
        weightSum = sum(args)
        r = random.uniform(0, weightSum)
        l = 0

        for i, x in enumerate(args):
            if l <= r <= l + x:
                return i
            l += x

    def run(self):

        while True:
            self.tick()

if __name__ == "__main__":
    game = Game()
    game.run()
