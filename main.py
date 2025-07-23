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
        self.e1 = Weapon(self, "Energy 1", "texture/energy1.png", 100, 3000, 5, 1, Weapon.AKshoot, 2, "energy")
        self.e2 = Weapon(self, "Energy 2", "texture/energy2.png", 5, 1600, 1, 1.5, Weapon.RocketLauncher, 3, "explosion")

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
        self.map.generate_arena(room_count=14, min_room_size=4, max_room_size=10, corridor_width=3)
        self.killfeed = []
        self.keypress = []
        self.keypress_held_down = []

        self.t1 = 1
        self.t2 = 1

        self.arena = ArenaWithPathfinding(self.map)
        connectivity = self.arena.validate_arena_connectivity()
        print(f"Arena Connectivity: {connectivity}")

        self.spawn_points = self.arena.find_optimal_spawn_points(2, min_distance=30)
        print(f"Spawn points: {self.spawn_points}")

        self.map.get_spawn_points()

        self.MAP = self.map.to_pygame_surface(cell_size=70)
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

        self.visualEntities = []
        self.explosion = load_animation("texture/expl1", 0, 31, size = [500,500])
        self.items = getItems()
        self.cameraLock = None

        self.levelUps = [round(10*(x+1) * (1.2) ** x) for x in range(100)]

        self.pendingLevelUp = None
        self.levelUpI = 3
        self.levelUpBlink = 1

        self.screenCopy1 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.screenCopy2 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)


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

        self.reloadSound = pygame.mixer.Sound("audio/reload.wav")
        for x in self.ARSounds + [self.reloadSound]:
            x.set_volume(0.3)


    def playSound(self, l):
        for x in l:
            x.stop()
        random.choice(l).play()

        
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
            pawn.team = len(self.pawnHelpList)%2
            pawn.pos = v2(self.spawn_points[pawn.team]) * 70 + [35, 35]
            self.ENTITIES.append(pawn)
            
        else:
            print("Download was incomplete.")

        self.pawnGenI -= 1


        

    def debugText(self, text):

        t = self.fontSmaller.render(str(text), True, [255,255,255])
        self.screen.blit(t, [self.res[0] - 20 - t.get_size()[0], 200 + self.debugI * 12])
        self.debugI += 1

    def smoothRotationFactor(self, angleVel, gainFactor, diff):
        dir = 1 if diff > 0 else -1
        decelarationTicks = abs(angleVel/gainFactor)
        distanceDecelerating = angleVel*decelarationTicks-0.5*dir*gainFactor*decelarationTicks**2
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
        t = combinedText(self.pendingLevelUp.name, [255,0,0] if self.pendingLevelUp.team else [0,0,255], " LEVELED UP", [255,255,255], font=self.fontLarge)
        self.screen.blit(t, self.res/2 - [0, 300] - v2(t.get_size())/2)

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
                pygame.draw.rect(self.screen, [255,0,0], rect2, width=int(5-i))

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
                self.pendingLevelUp.healthCap += 50
                self.pendingLevelUp = None
                self.resetLevelUpScreen()
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
        if not self.cameraLock:
            if self.pawnHelpList:
                e = sorted(self.pawnHelpList.copy(), key=lambda p: p.killsThisLife, reverse=True)
                
                for x in e:
                    if not x.killed:
                        self.cameraLock = x
                        break


        else:
            if self.cameraLock.killed:
                self.cameraLock = None
            else:
                if self.cameraLock.target:
                    self.cameraPos = self.cameraLock.pos - self.res/2
                    if not self.pendingLevelUp:
                        CREATEDUAL = True
                else:
                    self.cameraPos = self.cameraLock.pos - self.res/2
        
        if self.pendingLevelUp:
            self.cameraPos = self.pendingLevelUp.pos - self.res/2
            self.deltaTime *= 0.01


        if self.cameraLock:
            if self.cameraLock.target:
                angle = self.getAngleFrom(self.cameraLock.pos, self.cameraLock.target.pos) + math.pi/2
            else:
                angle = self.getAngleFrom(self.cameraLock.pos, self.dualCameraPosDelta) + math.pi/2
            line1 = v2(math.cos(angle), math.sin(angle))*1920 + self.res/2
            line2 = v2(math.cos(angle+math.pi), math.sin(angle+math.pi))*1920 + self.res/2
            line3 = v2(math.cos(angle), math.sin(angle))*1920 + self.res/2 - v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*1200
            line4 = v2(math.cos(angle+math.pi), math.sin(angle+math.pi))*1920 + self.res/2 - v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*1200
        else:
            CREATEDUAL = False
        if CREATEDUAL:
            posToTargetTo = self.cameraLock.pos + v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(-300) - self.res/2
            posToTargetTo2 = self.cameraLock.target.pos + v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(300) - self.res/2
        

        self.MINIMAPTEMP = self.MINIMAP.copy()
        for x in self.particle_list:
            x.tick()

        for x in entities_temp:
            x.tick()

        for x in self.visualEntities:
            x.tick()

        if CREATEDUAL:
            self.cameraPos = posToTargetTo.copy()
            self.dualCameraPos = posToTargetTo2.copy()
        else:
            self.dualCameraPos = self.cameraPos.copy()

        CAMPANSPEED = 7000
        self.cameraVel[0] += self.smoothRotationFactor(self.cameraVel[0], CAMPANSPEED, self.cameraPos[0] - self.cameraPosDelta[0]) * self.deltaTimeR
        self.cameraVel[1] += self.smoothRotationFactor(self.cameraVel[1], CAMPANSPEED, self.cameraPos[1] - self.cameraPosDelta[1]) * self.deltaTimeR
        self.cameraPosDelta += self.cameraVel * self.deltaTimeR

        self.dualCameraVel[0] += self.smoothRotationFactor(self.dualCameraVel[0], CAMPANSPEED, self.dualCameraPos[0] - self.dualCameraPosDelta[0]) * self.deltaTimeR
        self.dualCameraVel[1] += self.smoothRotationFactor(self.dualCameraVel[1], CAMPANSPEED, self.dualCameraPos[1] - self.dualCameraPosDelta[1]) * self.deltaTimeR
        self.dualCameraPosDelta += self.dualCameraVel * self.deltaTimeR
        DUAL = False
        if self.dualCameraPosDelta.distance_to(self.cameraPosDelta) > 250:
            DUAL = CREATEDUAL


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
                self.cameraPosDelta = self.dualCameraPosDelta.copy()

            self.DRAWTO.blit(self.MAP, -self.cameraPosDelta)

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
        for x in sorted(self.pawnHelpList.copy(), key = lambda p: p.kills, reverse=True):

            t = combinedText(f"{x.name}: ", [255,0,0] if x.team else [0,0,255], f"{x.kills} KILLS", [255,255,255], font=self.font)
            self.screen.blit(t, [10,y])
            y += 30

        

        
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
        self.levelUpI = 5
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
