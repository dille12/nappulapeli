import pygame
import os
import pygame.gfxdraw
from pawn.pawn import Pawn
from pawn.weapon import Weapon
import random
import threading
from utilities.enemy import Enemy
import math
from pygame.math import Vector2 as v2
import time
from levelGen.mapGen import ArenaGenerator, CellType
import numpy as np
from levelGen.arenaWithPathfinding import ArenaWithPathfinding
from core.loadAnimation import load_animation
from utilities.item import Item
from utilities.items import getItems
from keypress import key_press_manager
from utilities.skull import Skull
import colorsys
from utilities.infoBar import infoBar
from utilities.shop import Shop
from particles.particle import ParticleSystem, Particle
from particles.laser import ThickLaser
from gameTicks.settingsTick import settingsTick, createSettings
from gameTicks.pawnGeneration import preGameTick
from gameTicks.tick import battleTick
from gameTicks.gameModeTick import GlitchGamemodeDisplay, loadingTick
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

def generate_noise_surface(size):
    width, height = size
    noise_array = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    surface = pygame.Surface(size)
    pygame.surfarray.blit_array(surface, np.stack([noise_array]*3, axis=-1))
    return surface

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
        self.darken = []
        d = pygame.Surface(self.res).convert_alpha()
        for x in range(20):
            d2 = d.copy()
            d2.fill((0,0,0))
            d2.set_alpha((x+1)*5)
            self.darken.append(d2)

        self.mask = pygame.Surface(self.res, pygame.SRCALPHA).convert_alpha()
        self.infobars = []
        
        pygame.font.init()
        self.ENTITIES = []
        self.pawnHelpList = []
        self.playerFiles = []  # List to hold player objects
        self.particle_list = []
        self.playerFilesToGen = [] 
        self.clock = pygame.time.Clock()

        self.fontName = "texture/agencyb.ttf"

        self.font = pygame.font.Font(self.fontName, 30)
        self.fontLarge = pygame.font.Font(self.fontName, 60)  # Load a default font
        self.fontLevel = pygame.font.Font(self.fontName, 40)  # Load a default font
        # image_path, damage, range, magSize, fireRate, fireFunction, reloadTime
        pygame.mixer.init()
        self.weapons = []
        self.AK = Weapon(self, "AK-47", [1, 0], "texture/ak47.png", 12, 1600, 30, 8, Weapon.AKshoot, 1.5, "normal")
        self.e1 = Weapon(self, "Sniper", [2, 0], "texture/energy1.png", 75, 3000, 5, 1, Weapon.Energyshoot, 2, "energy")
        self.e2 = Weapon(self, "Rocket Launcher", [3, 0], "texture/energy2.png", 125, 1600, 1, 0.5, Weapon.RocketLauncher, 3, "explosion")
        self.e3 = Weapon(self, "EMG", [1, 0], "texture/energy3.png", 14, 1000, 40, 14, Weapon.Energyshoot, 0.8, "energy")
        self.pistol = Weapon(self, "USP-S", [0.5, 0], "texture/pistol.png", 25, 2000, 12, 3, Weapon.suppressedShoot, 0.3, "normal", sizeMult=0.7)
        self.pistol2 = Weapon(self, "Glock", [0, 0], "texture/pistol2.png", 8, 1500, 20, 5, Weapon.pistolShoot, 0.5, "normal", sizeMult=0.7)
        self.smg = Weapon(self, "SMG", [1, 0], "texture/ump.png", 10, 1800, 45, 20, Weapon.smgShoot, 1, "normal", sizeMult=0.7)

        self.famas = Weapon(self, "FAMAS", [1.5, 0], "texture/famas.png", 23, 2300, 25, 6, Weapon.burstShoot, 1.4, "normal")

        self.shotgun = Weapon(self, "Shotgun", [2, 0], "texture/shotgun.png", 7, 1300, 6, 1.5, Weapon.shotgunShoot, 0.8, "normal")

        self.mg = Weapon(self, "Machine Gun", [0, 1], "texture/mg.png", 15, 2500, 300, 16, Weapon.AKshoot, 4, "normal")
        self.BFG = Weapon(self, "BFG", [2, 1], "texture/bfg.png", 20, 2300, 50, 5, Weapon.BFGshoot, 2.5, "energy", sizeMult=1.2)

        self.weapons = [self.AK, self.e1, self.e2, self.e3, self.pistol, self.pistol2, self.smg, self.famas, self.shotgun, self.mg, self.BFG]

        self.BFGLasers = []

        self.skullW = Weapon(self, "Skull", [0,0], "texture/skull.png", 1, 1000, 1, 1, Weapon.skull, 1, "normal")

        #self.timbs = Item("Timbsit", speedMod=["add", 300])


        print("AK created")
        #self.ENTITIES.append(Enemy(self))

        #for x in os.listdir("players"):
        #    self.ENTITIES.append(Pawn(self, "players/" + x))

        print("Game initialized")
        self.deltaTime = 1/60
        self.deltaTimeR = 1/60
        self.debugI = 0
        self.fontSmaller = pygame.font.Font(self.fontName, 18)  # Smaller font for debug text
        self.pawnGenI = 0
        self.pawnGenT = 0
        #self.map = ArenaGenerator(80, 60)

        # TEAM COUNT
        self.teams = 2
        self.MINIMAPCELLSIZE = 2

        self.teamInspectIndex = 0
        self.safeToUseCache = True
        self.cacheLock = threading.Lock()
        #self.map.generate_arena(room_count=int(self.teams*1.5)+4, min_room_size=8, max_room_size=20, corridor_width=3)
        self.killfeed = []
        self.keypress = []
        self.keypress_held_down = []

        self.cameraLinger = 2
        self.TTS_ON = True

        self.t1 = 1
        self.t2 = 1

        self.FPS = 0

        self.splitI = 0
        self.cameraLockTarget = v2(0,0)
        self.cameraLockOrigin = v2(0,0)
        self.endGameI = 5
        self.victoryTeam = -1
        self.musicSwitch = False
        self.mapCreated = False

        self.topHat = pygame.image.load("texture/tophat.png").convert_alpha()
        self.topHat = pygame.transform.scale(self.topHat, (70, 70))
        self.noise = []
        for x in range(10):
            y = generate_noise_surface((200,200))
            y.set_alpha(40)
            self.noise.append(y)

        

        #self.arena = ArenaWithPathfinding(self.map)
        #connectivity = self.arena.validate_arena_connectivity()
        #print(f"Arena Connectivity: {connectivity}")

        #self.spawn_points = self.arena.find_optimal_spawn_points(self.teams, min_distance=20)
        #print(f"Spawn points: {self.spawn_points}")

        #self.map.get_spawn_points()

        #self.MAP = self.map.to_pygame_surface(cell_size=70)

        #floor_mask = pygame.Surface((80*70, 60*70))
        #self.wall_mask = pygame.Surface((80*70, 60*70), flags=pygame.SRCALPHA).convert_alpha()
        #for y in range(60):
        #    for x in range(80):
        #        if self.map.grid[y,x] != CellType.WALL.value:  # Your tile logic
        #            pygame.draw.rect(floor_mask, (55,55,55), (x*70, y*70, 70, 70))
        #        else:
        #            pygame.draw.rect(self.wall_mask, (0,0,0), (x*70, y*70, 70, 70))

        #self.MAP = floor_mask

        #self.MINIMAP = self.map.to_pygame_surface(cell_size=3)
        self.MINIMAPTEMP = None
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

        self.speeches = 0

        self.GAMESTATE = "settings"

        self.objectiveCarriedBy = None

        self.screenCopy1 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.screenCopy2 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.skull = None
        self.skullVictoryTime = 100

        self.particle_system = ParticleSystem(self)

        self.bloodSplatters = []
        
        
        self.skullTimes = []
        self.refreshShops()

        
        self.ARSounds = self.loadSound("audio/assault")

        self.deathSounds = self.loadSound("audio/death")

        self.hitSounds = self.loadSound("audio/hit")

        self.explosionSound = self.loadSound("audio/explosion")

        self.clicks = self.loadSound("audio/menu_click")

        self.music = None
        self.currMusic = 0
        self.nextMusic = 0
        self.midMusicIndex = 0

        self.weaponButtonClicked = None
        self.hudChange = 1
        self.currHud = 0


        self.bloodClearI = 0
        self.beatI = 0

        self.energySound = self.loadSound("audio/nrg_fire")
        self.shotgunSound = self.loadSound("audio/shotgun")
        self.silencedSound = self.loadSound("audio/silenced")

        self.waddle = self.loadSound("audio/waddle")

        self.rocketSound = self.loadSound("audio/rocket_launch")

        self.smgSound = self.loadSound("audio/smg")

        self.pistolSound = self.loadSound("audio/weapon_fire")

        if len(self.energySound) != 3:
            raise RuntimeError
        
        self.LAZER = ThickLaser(self, width=20)
        self.lastTickLaser = False
        

        self.reloadSound = pygame.mixer.Sound("audio/reload.wav")
        self.meleeSound = pygame.mixer.Sound("audio/melee.wav")
        for x in [self.reloadSound, self.meleeSound]:
            x.set_volume(0.3)

        createSettings(self)

        self.gamemode_display = GlitchGamemodeDisplay(self)
            

    def refreshShops(self):
        self.shops = []
        for x in range(self.teams):
            self.skullTimes.append(0)
            shop = Shop(self, x)
            shop.totalPrice = [0, 0]
            self.shops.append(shop)


    def genLevel(self):

        
        i = infoBar(self, "Generating level")
        self.map = ArenaGenerator(120, 80)
        self.map.generate_arena(room_count=22, min_room_size=8, max_room_size=20, corridor_width=3)
        self.arena = ArenaWithPathfinding(self.map)
        connectivity = self.arena.validate_arena_connectivity()
        print(f"Arena Connectivity: {connectivity}")
        i.text ="Finding spawn points"
        self.teamSpawnRooms = self.arena.find_spawn_rooms(self.teams)
        
        self.spawn_points = []
        for x in self.teamSpawnRooms:
            self.spawn_points.append(x.center())

        print(f"Spawn points: {self.spawn_points}")

        print("Spawn Rooms")

        self.map.get_spawn_points()
        i.text ="Drawing the map"
        self.MAP = self.map.to_pygame_surface(cell_size=70)
        
        self.MINIMAP = self.map.to_pygame_surface(cell_size=self.MINIMAPCELLSIZE)
        self.MINIMAPTEMP = self.MINIMAP.copy()
        #entrance = self.map.get_entrance_position()
        routeBetweenSpawns = self.arena.pathfinder.find_path(self.spawn_points[0], self.spawn_points[1])
        midPoint = routeBetweenSpawns[int(len(routeBetweenSpawns)/2)]
        #if entrance:
        self.skull = Skull(self, midPoint)
        print("SKULL CREATED!")
        i.text ="Map done!"
        i.killed = True
        self.nextMusic = 1
        self.mapCreated = True

    def initiateGame(self):
        
        self.gamemode_display.set_gamemode("ODDBALL")
        self.genLevel()
        self.resetLevelUpScreen()
       
        self.endGameI = 5
        self.skullTimes = []
        for x in range(self.teams):
            self.skullTimes.append(0)

        self.GAMESTATE = "ODDBALL"
        self.VICTORY = False

        for i in range(2):
            for pawn in self.pawnHelpList:
                pawn.reset()
                pawn.kills = 0
                pawn.teamKills = 0
                pawn.suicides = 0
                pawn.deaths = 0

            time.sleep(0.5)

        


    def playSound(self, l):
        for x in l:
            x.stop()
        random.choice(l).play()

    def loadSound(self, fileHint, startIndex = 1, suffix=".wav", volume = 0.3):
        l = []
        while True:
            f = fileHint + str(startIndex) + suffix
            if os.path.exists(f):
                l.append(pygame.mixer.Sound(f))
                l[-1].set_volume(volume)
                startIndex += 1

            else:
                return l

        
    def drawWalls(self):
        for x in self.wallRects:
            x2 = x.copy()
            x2.topleft -= self.cameraPos
            pygame.draw.rect(self.screen, [0,0,0], x2)

    def reTeamPawns(self):
        for pawn in self.pawnHelpList:
            pawn.team = self.pawnHelpList.index(pawn)%self.teams

    def threadedGeneration(self, path):
        self.pawnGenI += 1
        
        print("Probing if file ready.")
        if wait_for_file_ready(path):
            print("File ready!")
            
            pawn = Pawn(self, path)
            pawn.team = self.pawnHelpList.index(pawn)%self.teams
            pawn.teamColor = self.getTeamColor(pawn.team)
            pawn.NPC = pawn.name != "Micco"
            self.ENTITIES.append(pawn)
            
        else:
            print("Download was incomplete.")

        self.reTeamPawns()

        self.pawnGenI -= 1


    def handleMusic(self):

        if not self.music:
            return

        for x in self.music:
            if x.get_num_channels():
                return False
        self.music[self.currMusic].stop()

        nextTrack = self.nextMusic
        if self.nextMusic == 1:
            totalMidTracks = len(self.music) - 2
            nextTrack = 1 + self.midMusicIndex
            self.midMusicIndex = (self.midMusicIndex + 1) % totalMidTracks

        self.music[nextTrack].play()
        self.currMusic = self.nextMusic

        self.musicStart = time.time()
        self.musicLength = self.music[self.nextMusic].get_length()
        return True
    
    def BPM(self):
        tempo = 150 if self.loadedMusic == "HH" else 123
        musicPlayedFor = time.time() - self.musicStart
        self.beatI = 1-((musicPlayedFor%(60/tempo))/(60/tempo))

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
        self.screen.blit(t, [self.res[0] - 20 - t.get_size()[0], 200 + self.debugI * 22])
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
    
    def levelUpTimeFreeze(self):
        return max(abs(self.levelUpI-2.5)-1.5,0)
    
    def levelUpScreen(self):
        if self.levelUpBlink > 0:
            self.levelUpBlink -= self.deltaTimeR
        else:
            self.levelUpBlink = 1

        self.levelUpI -= self.deltaTimeR
        
        I = self.levelUpTimeFreeze()

        d = self.darken[round((1-I)*19)]

        self.screen.blit(d, (0,0))
        lowering = I**2
        IMS = self.pendingLevelUp.levelUpIms
        #I = 1 - self.levelUpI/5
        IM = random.choice(IMS)



        self.screen.blit(IM, self.res/2 - [random.randint(-2, 2), 300+random.randint(-2, 2)] - v2(IM.get_size())/2 - [0, 800*lowering])

        text_t = min(max((5-self.levelUpI) - 0.8, 0)/0.7, 1.0)
        text = combinedText(self.pendingLevelUp.name, self.pendingLevelUp.teamColor, f" LEVELED UP (LVL {self.pendingLevelUp.level+1})", [255]*3, font=self.fontLarge)
        text.set_alpha(int(255 * (1-I)))
        self.screen.blit(text, self.res/2 - [0, 150] - v2(text.get_size())/2)

        r1 = pygame.Rect(self.res[0]/2 - 400, 800, 800, 30)
        pygame.draw.rect(self.screen, [255,255,255], r1, width=1)
        r2 = r1.copy()
        ir2 = max(0, 1-(5-self.levelUpI)/5)
        r2.width = ir2*796
        r2.height = 26
        r2.center = r1.center
        pygame.draw.rect(self.screen, [255,255*ir2,255*ir2], r2)

        t = self.font.render("Omistetut esineet:", True, [255]*3)
        self.screen.blit(t, [40, 400])
        for i, y in enumerate(self.pendingLevelUp.pastItems):
            t = self.font.render(y, True, [255]*3)
            self.screen.blit(t, [40, 430 + 30*i])

        for x in range(3):
            xpos = (x-1)*450 + self.res[0]/2
            item = self.pendingLevelUp.nextItems[x]

            pulse = 1 + 0.05 * math.sin(pygame.time.get_ticks()/200 + x)
            floatY = 10 * math.sin(pygame.time.get_ticks()/400 + x)
            t_surf = self.fontLevel.render(item.name, True, [255]*3)
            t_surf = pygame.transform.rotozoom(t_surf, 0, pulse)
            pos = v2(xpos, 600 + floatY) - v2(t_surf.get_size())/2
            self.screen.blit(t_surf, pos)

            t_surf2 = self.font.render(item.desc, True, [255]*3)
            t_surf2 = pygame.transform.rotozoom(t_surf2, 0, pulse)
            pos2 = v2(xpos, 650 + floatY) - v2(t_surf2.get_size())/2
            self.screen.blit(t_surf2, pos2)




            rect = pygame.Rect(pos, t_surf.get_size())
            
            if self.levelUpBlink > 0.75 and self.levelUpIndex == x:
                rect2 = rect.copy()
                i = ((1-self.levelUpBlink)/0.25)**2
                rect2.inflate_ip(30*i, 30*i)
                pygame.draw.rect(self.screen, [255,0,0], rect2, width=int(i*4))

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
                self.pendingLevelUp.levelUp(item)
                self.pendingLevelUp = None
                self.resetLevelUpScreen()
                self.cameraVel = v2([0,0])
                self.cameraLock = None
                return
                
                
    def handleCameraLock(self):

        if "space" in self.keypress:
            self.cameraLock = random.choice(self.pawnHelpList)

        if not self.cameraLock and self.cameraLinger <= 0:
            #if self.objectiveCarriedBy:
            #    self.cameraLock = self.objectiveCarriedBy

            if self.pawnHelpList:
                e = sorted(self.pawnHelpList.copy(), key=lambda p: p.onCameraTime)
                
                for x in e:
                    if not x.killed and not x.NPC:
                        self.cameraLock = x
                        break


        elif self.cameraLinger <= 0:
            if self.cameraLock.killed:
                self.cameraLock = None
                self.cameraLinger = 1
            else:
                self.cameraPos = self.cameraLock.pos - self.res/2
                self.cameraLock.onCameraTime += self.deltaTime
                if self.cameraLock.target and not self.pendingLevelUp and not self.VICTORY:
                    self.CREATEDUAL = True
                    self.cameraLockTarget = self.cameraLock.target.pos.copy() * 0.1 + self.cameraLockTarget * 0.9
                    self.cameraLockOrigin = self.cameraLock.pos.copy()
        
        else:
            self.cameraLinger -= self.deltaTime


        if self.VICTORY:
            I = max(self.endGameI-4, 0)
            self.deltaTime *= 1 - 0.5*(1-I)
            self.cameraLock = max(
                (x for x in self.pawnHelpList if (x.team == self.victoryTeam and not x.killed)),
                key=lambda x: x.kills,
                default=None
            )

        
        elif self.pendingLevelUp:
            #self.cameraLockOrigin = self.pendingLevelUp.pos.copy() - self.res/2

            I = self.levelUpTimeFreeze()

            self.deltaTime *= 1 - 0.99*(1-I)
            self.cameraLock = self.pendingLevelUp

    def handleCameraSplit(self):
        
        if self.CREATEDUAL:

            self.splitI += self.deltaTimeR
            self.splitI = min(1, self.splitI)
        else:
            self.splitI -= self.deltaTimeR
            self.splitI = max(0, self.splitI)

        if self.splitI > 0:

            shiftI = (1-self.splitI)**2

            maxX = 1000 * shiftI


            if self.cameraLock and not self.cameraLock.killed:
                self.cameraLockOrigin = self.cameraLock.pos.copy()

            angle = self.getAngleFrom(self.cameraLockOrigin, self.cameraLockTarget) + math.pi/2

            shift = v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(-maxX)

            shiftAmount = min(600, self.cameraLockOrigin.distance_to(self.cameraLockTarget))/2

            self.line1 = v2(math.cos(angle), math.sin(angle))*1920 + self.res/2 + shift
            self.line2 = v2(math.cos(angle+math.pi), math.sin(angle+math.pi))*1920 + self.res/2 + shift
            self.line3 = v2(math.cos(angle), math.sin(angle))*1920 + self.res/2 - v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*1200 + shift
            self.line4 = v2(math.cos(angle+math.pi), math.sin(angle+math.pi))*1920 + self.res/2 - v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*1200 + shift
            self.posToTargetTo = self.cameraLockOrigin + v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(-shiftAmount * (1-shiftI)) - self.res/2
            self.posToTargetTo2 = self.cameraLockTarget + v2(math.cos(angle+math.pi/2), math.sin(angle+math.pi/2))*(shiftAmount+0.7*maxX) - self.res/2

    def splitScreen(self):
        #self.screen.fill((0,0,0))
        self.screen.blit(self.screenCopy1, (0, 0))

        self.mask.fill((0, 0, 0, 0))
        pygame.draw.polygon(self.mask, [255, 255, 255, 255], (self.line1, self.line2, self.line4, self.line3))

        # Masking step: use mask to zero out non-polygon areas in screenCopy2
        self.screenCopy2.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # True alpha blending
        self.screen.blit(self.screenCopy2, (0, 0))  # This now honors alpha channel

        pygame.draw.line(self.screen, [255, 255, 255], self.line1, self.line2, 3)


    def tickEndGame(self):
        self.endGameI -= self.deltaTimeR
        I = max(self.endGameI-4, 0)
        self.deltaTime *= 0.01 + I*0.99

            
        if self.currMusic == -1:
            self.nextMusic = 0
        
        d = self.darken[round((1-I)*19)]
        self.screen.blit(d, (0,0))
        text = self.fontLarge.render(f"TEAM {self.victoryTeam+1} WON", True, self.getTeamColor(self.victoryTeam))
        text.set_alpha(int(255 * (1-I)))
        self.screen.blit(text, self.res/2 - [0, 300] - v2(text.get_size())/2)

        for i, y in enumerate(self.points):
            pawn, points, reason_str = y
            text = self.font.render(f"{pawn.name}: {reason_str}", True, self.getTeamColor(pawn.team))
            text.set_alpha(int(255 * (1-I)))
            self.screen.blit(text, v2(300,500 + i*40))


    def endGame(self):
        self.GAMESTATE = "pawnGeneration"
        self.objectiveCarriedBy = None
        self.teamInspectIndex = 0
        self.mapCreated = False
        self.cameraLock = None
        self.skull.kill()
        for x in self.pawnHelpList:
            x.reset()
            x.defaultPos()
        self.refreshShops()
        self.particle_list.clear()


    def mapTime(self, curr, maximum, inverse = False):
        if not inverse:
            return curr/maximum
        else:
            return (maximum-curr)/maximum
        

    def advanceShop(self):
        self.teamInspectIndex += 1
        self.teamInspectIndex = ((self.teamInspectIndex+1)%(self.teams+1))-1
        for x in self.pawnHelpList:
            x.walkTo = None
            x.pickWalkingTarget()

        for x in self.shops:
            x.hideI = 0.5



    def handleHud(self):
        if self.currHud == self.cameraLock and self.currHud and not self.VICTORY:
            self.hudChange += self.deltaTimeR
            self.hudChange = min(1, self.hudChange)

        else:
            self.hudChange -= self.deltaTimeR
            self.hudChange = max(0, self.hudChange)
            if self.hudChange == 0:
                self.currHud = None
                if not self.currHud and self.cameraLock:
                    self.currHud = self.cameraLock

        if self.hudChange > 0 and self.currHud:
            yPos = self.res[1] - 220*(1-(1-self.hudChange)**2)
            surf = pygame.Surface((200,200))
            c = self.getTeamColor(self.currHud.team)
            surf.fill((c[0]*0.2, c[1]*0.2, c[2]*0.2))
            surf.blit(self.currHud.hudImage, v2(100,100) - v2(self.currHud.hudImage.get_size())/2)
            surf.blit(random.choice(self.noise), (0,0))
            pygame.draw.rect(surf, c, (0,0,200,200), width=1)
            self.screen.blit(surf, [20, yPos])

            c2 = [255,255,255]

            t1 = self.font.render(self.currHud.name, True, c2)
            self.screen.blit(t1, (230, yPos))
            p = self.currHud
            if p.weapon.isReloading():
                i1 = p.weapon.currReload
                i2 = p.weapon.getReloadTime()
                procent = int(100*(1 - i1/i2))
                t1 = self.font.render(f"Lataa: {procent}%", True, c2)
                self.screen.blit(t1, (230, yPos+35))
            else:
                t1 = self.font.render(f"Luodit: {p.weapon.magazine}/{p.getMaxCapacity()}", True, c2)
                self.screen.blit(t1, (230, yPos+35))

            t1 = self.font.render(f"Tapot: {p.kills} Kuolemat: {p.deaths} (KD:{p.kills/max(1, p.deaths):.1f})", True, c2)
            self.screen.blit(t1, (230, yPos+70))


            xpTillnextLevel = self.levelUps[p.level-1] - p.xp

            t1 = self.font.render(f"XP: {p.xp} Jäljellä: {xpTillnextLevel}", True, c2)
            self.screen.blit(t1, (230, yPos+105))

            #t1 = self.font.render(f"{p.weapon.addedFireRate}", True, c2)
            #self.screen.blit(t1, (230, yPos+140))

            p.hudInfo((600, yPos), screen=self.screen)

    def cleanUpLevel(self):

        for i in range(5):
            self.bloodClearI += 1

            x = self.bloodClearI % self.map.width
            y = self.bloodClearI // self.map.width

            if y >= self.map.height:
                self.bloodClearI = 0
                continue
            
            if self.map.grid[y, x] != CellType.WALL.value:
                continue
            
        
            pygame.draw.rect(self.MAP, (0,0,0), (x*70,y*70, 70, 70))


    def tickScoreBoard(self):
        y = 200

        for i, x in sorted(enumerate(self.skullTimes), key=lambda pair: pair[1], reverse=True):
            t = combinedText(f"TEAM {i + 1}: ", self.getTeamColor(i), f"{x:.1f} seconds", self.getTeamColor(i), font=self.fontSmaller)
            self.screen.blit(t, [10, y])
            y += 22

        y += 22

        for x in sorted(self.pawnHelpList.copy(), key = lambda p: p.kills, reverse=True):

            t = combinedText(f"{x.name}: ", x.teamColor, f"LVL {x.level}  {x.kills}/{x.deaths}", [255,255,255], font=self.fontSmaller)
            self.screen.blit(t, [10,y])
            y += 22
        
        



    def drawBFGLazers(self):
        currLaser = False
        for startPos, endPos in self.BFGLasers:
            s1 = startPos - self.cameraPosDelta
            e1 = endPos - self.cameraPosDelta
            #if (0 <= s1[0] <= self.res[0] and 0 <= s1[1] <= self.res[1]) or (0 <= e1[0] <= self.res[0] and 0 <= e1[1] <= self.res[1]):
            self.LAZER.draw(self.DRAWTO, s1, e1)
            currLaser = True

        if currLaser != self.lastTickLaser:
            if currLaser:
                self.LAZER.activate()
            else:
                self.LAZER.deactivate()
        self.lastTickLaser = currLaser
        

    def genPawns(self):
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
            t = threading.Thread(target=self.threadedGeneration, args=("players/" + x,))
            t.daemon = True
            t.start()
        
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
            
            tickStartTime = time.time()

            key_press_manager(self)
        
            self.debugI = 0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()  # Ensure the program exits cleanly

            if self.GAMESTATE == "settings":
                settingsTick(self)

            elif self.GAMESTATE == "pawnGeneration":
                preGameTick(self)

            elif self.GAMESTATE == "loadingScreen":
                loadingTick(self)

            else:
                battleTick(self)

            for x in self.infobars:
                x.tick()
            self.musicSwitch = self.handleMusic()
            self.BPM()
            r = pygame.Rect((0,0), self.res)
            pygame.draw.rect(self.screen, [255,0,0], r, width=1+int(5*(self.beatI**2)))

            pygame.display.update()
            self.t1 = time.time() - tickStartTime
            

            self.deltaTimeR = self.clock.tick(144) / 1000
            self.t2 = time.time() - tickStartTime

            self.FPS = 0.05 * (1/self.t2) + 0.95 * self.FPS

            self.deltaTimeR = min(self.deltaTimeR, 1/30)
            self.deltaTime = self.deltaTimeR

if __name__ == "__main__":
    game = Game()
    game.run()
