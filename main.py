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
from core.drawRectPerimeter import draw_rect_perimeter
from core.getCommonRoom import find_farthest_room
import asyncio
from core.qrcodeMaker import make_qr_surface
from pawn.teamLogic import Team

# KILL STREAKS
# Flash bang: Ampuu sinne tänne nänni pohjassa
# Payload (Gamemode) Viedään kärry toisen baseen joka mossauttaa sen
# Dessu
# Lisää aseita (tf2 medic gun, vasara jolla voi rakentaa suojia ja turretteja), eri classit (medic engineer soldier scout) jotka valitaan classiin sopivilla itemeillä
# Class specific itemit, logot määrittävät kelle itemi sopii sekä värjätty itemin classin perusteella
# Levelupit ja itemi valinta tehdään apissa
# Hattu tulee kun vaikka 3 itemiä enemmän kuin muita classin itemeitä

# USAS 12 Frag rounds
# Pickup guns
# Block corridors
# Highroller: 10% Megaitem, 90 Eternal orja
# Piilorasismi: Muuttuu mustaksi, mutta näkymätön välillä, 10x damage johonkin joukkueeseen.
# Pislarundi, zeus (klitoriskiihdytin t:teemu) jotenkin sisään, se antaa shottiallokaation jollekin pelaajalle.
# Pyörätuoli: +50% nopeus (animaatio)

# Näkyvä rasismi, 



# Riisifarmari: Pienenee, silmät ohistuu, mutta nopeus kasvaa
# Paskapajeeti: Paskoo alleen, paskoihin liukastuu
# DIY Liekinheitin: Tuplalämä paheeteihin, 
# Juutalainen: Muuttaa kaikki tuhkakasaksi
# Pelin alussa: Valitse etninen ryhmä: (Juutalainen, Riisiviljelijä, Kaaleet, Punanahka, Turaani, Yön timo)
# Juutalainen: Kaikki aseet on kalliimpia mut parempia
# Intiaani värtjätään punaseksi, alkuaseena jousipyssy, buffi jos omia ympärillä, kasino
# Kaaleilla tupla damage melee aseilla
# Tomahawk
# Rättipäät: Tupladamage räjähdyksillä, Masokismi innate
# Turaaneilla alku ase musta makkara
# Riisifarmareilla syömäpuikot alkuaseina
# 
# Musta mies, varastaa parhaan aseen laittaa kissanaamion pelaajaspritelle.

# Teemun oikeet ideat
# Joka roundi uudet ostot
# 


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

        self.now = time.time()

        self.res = v2(1920, 1080)
        self.screen = pygame.display.set_mode(self.res, pygame.SRCALPHA)  # Delay screen initialization
        self.darken = []
        d = pygame.Surface(self.res).convert_alpha()
        for x in range(20):
            d2 = d.copy()
            d2.fill((0,0,0))
            d2.set_alpha((x+1)*10)
            self.darken.append(d2)

        self.mask = pygame.Surface(self.res, pygame.SRCALPHA).convert_alpha()
        self.infobars = []
        
        pygame.font.init()
        self.ENTITIES = []
        self.pawnHelpList = []
        self.playerFiles = []  # List to hold player objects
        self.particle_list = []
        self.playerFilesToGen = [] 

        self.teams = 2
        self.allTeams = []
        for i in range(self.teams):
            self.allTeams.append(Team(self, i))

        if True:
            for x in os.listdir("players"):
                playerName = os.path.splitext(x)[0]
                file_path = os.path.join("players", x)
                with open(file_path, "rb") as f:
                    imageRaw = f.read()
                self.add_player(playerName, imageRaw, "DEBUG")

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

        self.GAMEMODE = "TURF WARS"
        self.podiumPawn = None
        self.judgementIndex = 0
        self.judgementTime = 0
        self.pregametick = "shop"
        self.judgementPhases = ["nextup", "reveal", "drink"]
        self.judgementPhase = "nextup"
        self.judgementDrinkTime = 0  # Will be randomized between 5–30

        self.concrete = pygame.image.load("texture/concrete.png").convert()
        self.concretes = []
        self.tileSize = 100
        tile_w = 70
        w, h = self.concrete.get_width(), self.concrete.get_height()

        for i in range(w//tile_w):
            rect = pygame.Rect(i * tile_w, 0, tile_w, h)
            tile = self.concrete.subsurface(rect).copy()

            tile = pygame.transform.scale(tile, (self.tileSize, self.tileSize))

            self.concretes.append(tile)
        

        self.deltaTime = 1/60
        self.deltaTimeR = 1/60
        self.debugI = 0
        self.fontSmaller = pygame.font.Font(self.fontName, 18)  # Smaller font for debug text
        self.pawnGenI = 0
        self.pawnGenT = 0
        #self.map = ArenaGenerator(80, 60)

        # TEAM COUNT
        
        self.teamsSave = self.teams
        self.MINIMAPCELLSIZE = 2
        self.round = 0
        self.roundTime = 0
        self.MAXROUNDLENGTH = 60

        self.ultCalled = False
        self.ultFreeze = 0

        self.gameModeLineUp = ["TEAM DEATHMATCH"] # , "ODDBALL", "TURF WARS"

        self.teamInspectIndex = 0
        self.safeToUseCache = True
        self.cacheLock = threading.Lock()
        #self.map.generate_arena(room_count=int(self.teams*1.5)+4, min_room_size=8, max_room_size=20, corridor_width=3)
        self.killfeed = []
        self.keypress = []
        self.keypress_held_down = []

        self.cameraLinger = 2
        self.TTS_ON = True
        self.ITEM_AUTO = False

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
        self.LEVELUPTIME = 10

        self.topHat = pygame.image.load("texture/tophat.png").convert_alpha()
        self.topHat = pygame.transform.scale(self.topHat, (70, 70))
        self.noise = []
        for x in range(10):
            y = generate_noise_surface((200,200))
            y.set_alpha(40)
            self.noise.append(y)


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
        self.horn = pygame.mixer.Sound("audio/horn.wav")
        self.tripSound = pygame.mixer.Sound("audio/trip.wav")
        for x in [self.reloadSound, self.meleeSound, self.horn, self.tripSound]:
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


    def findCorners(self, grid):
        h, w = grid.shape
        corners = []
        wallMidPoints = []

        for y in range(h+1):    
            if y in (0, h):
                continue      # vertices go one past grid
            for x in range(w+1):
                if x in (0, w):
                    continue 
                block = []
                if y > 0 and x > 0:
                    block.append(grid[y-1, x-1])
                if y > 0 and x < w:
                    block.append(grid[y-1, x])
                if y < h and x > 0:
                    block.append(grid[y, x-1])
                if y < h and x < w:
                    block.append(grid[y, x])

                if not block: 
                    continue

                wall_count = sum(1 for v in block if v == 0)
                if wall_count in (1, 3):
                    corners.append((x, y))
                elif wall_count == 2:
                    wallMidPoints.append((x,y))

        return corners, wallMidPoints
    
    def findWalls(self, corners, wallMidPoints):
        wallMidSet = set(wallMidPoints)
        cornerSet  = set(corners)
        walls = []

        for c in corners:
            cx, cy = c

            # search four directions: left, right, up, down
            directions = [(-1,0),(1,0),(0,-1),(0,1)]
            for dx, dy in directions:
                nx, ny = cx+dx, cy+dy
                path = []

                # walk until you hit another corner or fail
                while (nx, ny) in wallMidSet:
                    path.append((nx,ny))
                    nx += dx
                    ny += dy

                if (nx, ny) in cornerSet:
                    # found valid wall
                    other = (nx, ny)
                    seg = tuple(sorted([c, other]))
                    if seg not in walls:
                        walls.append(seg)

        return walls
    
    def wall_intersects_screen(self, p1, p2):
        W, H = self.res
        x1, y1 = p1
        x2, y2 = p2

        if x1 == x2:  # vertical
            ymin, ymax = sorted((y1, y2))
            return (0 <= x1 <= W) and not (ymax < 0 or ymin > H)
        else:  # horizontal
            xmin, xmax = sorted((x1, x2))
            return (0 <= y1 <= H) and not (xmax < 0 or xmin > W)

    

    def renderParallax2(self):
        camCenter = v2(self.res[0]*0.5, self.res[1]*0.8)
        for p1, p2 in self.walls:

            polygon = [p1 - self.cameraPosDelta, p2 - self.cameraPosDelta]

            # skip if both endpoints are outside screen
            in_frame = self.wall_intersects_screen(polygon[0], polygon[1])
            if not in_frame:
                continue

            # wall vector + normal
            wall_vec = polygon[1] - polygon[0]
            normal = np.array([-wall_vec[1], wall_vec[0]])
            normal /= np.linalg.norm(normal) + 1e-6

            # extrusion & lighting
            extruded = []
            maxDiff = 0
            for x in range(2):
                o = polygon[1-x]
                dist = np.linalg.norm(o - camCenter) / self.res[0]
                extrude = (150 + 200*dist) * (o - camCenter) / self.res[0]
                extruded.append(o + extrude)
                maxDiff = max(maxDiff, abs(extrude[0]), abs(extrude[1]))

            # light shading based on wall normal vs camera
            mid = (polygon[0] + polygon[1]) / 2
            to_cam = camCenter - mid
            to_cam /= np.linalg.norm(to_cam) + 1e-6
            light = np.clip(np.dot(normal, to_cam), -1, 1)

            # base shade from extrusion + directional light
            shade = 40 + int(maxDiff/6) + int(80*light)
            shade = max(20, min(220, shade))
            color = (shade, shade, shade)
            colorOutline = (shade+25, shade+25, shade+25)

            pygame.draw.polygon(self.DRAWTO, color, polygon + extruded)

            pygame.draw.lines(self.DRAWTO, colorOutline, True, polygon + extruded, width = 2)




    def renderParallax(self):
        camCenter = self.res/2
        for p1, p2 in self.walls:

            polygon = [p1 - self.cameraPosDelta, p2 - self.cameraPosDelta]
            p1InFrame = 0 <= polygon[0][0] <= self.res[0] and 0 <= polygon[0][1] <= self.res[1]
            p2InFrame = 0 <= polygon[1][0] <= self.res[0] and 0 <= polygon[1][1] <= self.res[1]
            if not p1InFrame and not p2InFrame:
                continue
            maxDiff = 0
            for x in range(2):
                o = polygon[1-x]
                diff = 300 * (o - camCenter) / self.res[0]
                maxDiff = max(maxDiff, abs(diff[0]), abs(diff[1]))
                polygon.append(o + diff)

            color = [10 + int(maxDiff/6)] * 3

            pygame.draw.polygon(self.DRAWTO, color, polygon)

    def genLevel(self):

        
        i = infoBar(self, "Generating level")
        if self.GAMEMODE == "1v1":
            self.map = ArenaGenerator(50, 40)
            self.map.generate_arena(room_count=self.teams+2, min_room_size=8, max_room_size=20, corridor_width=3)

        else:
            self.map = ArenaGenerator(120, 80)
            self.map.generate_arena(room_count=22, min_room_size=8, max_room_size=20, corridor_width=3)

        self.arena = ArenaWithPathfinding(self.map)
        connectivity = self.arena.validate_arena_connectivity()
        print(f"Arena Connectivity: {connectivity}")
        print(self.map.grid.shape)

        print("Rooms", len(self.map.rooms))
        i.text ="Finding spawn points"
        self.teamSpawnRooms = self.arena.find_spawn_rooms(self.teams)
        if not self.teamSpawnRooms:
            self.teamSpawnRooms = []
            for x in range(self.teams):
                self.teamSpawnRooms.append(self.map.rooms[x]%len(self.map.rooms))
                print(f"Spawn room for team {x} not found, using random room instead.")
        self.spawn_points = []
        for team, x in enumerate(self.teamSpawnRooms):
            self.spawn_points.append(x.center())
            x.turfWarTeam = team

        print(f"Spawn points: {self.spawn_points}")

        print("Spawn Rooms")
        self.commonRoom = find_farthest_room(self.map.rooms, self.teamSpawnRooms, mode="min")

        self.corners, midpoints = self.findCorners(self.map.grid)
        walls = self.findWalls(self.corners, midpoints)
        self.walls = []
        for p1, p2 in walls:
            self.walls.append([v2(p1)*self.tileSize, v2(p2)*self.tileSize])
        
        

        self.map.get_spawn_points()
        i.text ="Drawing the map"
        self.MAP = self.map.to_pygame_surface_textured(cell_size=self.tileSize, floor_texture=self.concretes)
        #for p1, p2 in self.walls:
        #    pygame.draw.line(self.MAP, [255,255,255], p1, p2, 3)

        
        self.MINIMAP = self.map.to_pygame_surface(cell_size=self.MINIMAPCELLSIZE)
        
        for team, r in enumerate(self.teamSpawnRooms):
            print("Drawing", team, "spawn room")
            pygame.draw.rect(self.MAP, self.getTeamColor(team, 0.2), (r.x*self.tileSize, r.y*self.tileSize, 
                                                                                      r.width*self.tileSize, r.height*self.tileSize))

        self.MINIMAPTEMP = self.MINIMAP.copy()
        #entrance = self.map.get_entrance_position()
        routeBetweenSpawns = self.arena.pathfinder.find_path(self.spawn_points[0], self.spawn_points[1])
        midPoint = routeBetweenSpawns[int(len(routeBetweenSpawns)/2)]
        #if entrance:
        if self.GAMEMODE == "ODDBALL":
            self.skull = Skull(self, midPoint)
        print("SKULL CREATED!")
        i.text ="Map done!"
        i.killed = True
        self.nextMusic = 1
        self.mapCreated = True

    def initiateGame(self):

        self.now = time.time()
        
        self.GAMEMODE = self.gameModeLineUp[self.round % len(self.gameModeLineUp)]
        self.gamemode_display.set_gamemode(self.GAMEMODE)

        if self.GAMEMODE == "1v1":

            # Pick best and the second best pawn
            self.duelPawns = sorted(self.pawnHelpList.copy(), key=lambda x: x.stats["kills"], reverse=True)[:2]
            #if self.duelPawns[0].team == self.duelPawns[1].team:
                # If they are on the same team, pick the next best pawn
                #self.duelPawns[1].team = (1 + self.duelPawns[0].team) % self.teams

            #self.duelPawns = [max(self.pawnHelpList, key=lambda x: x.stats["kills"]), self.pawnHelpList[1]]


        self.genLevel()
        self.resetLevelUpScreen()
        
            

        self.endGameI = 5
        self.skullTimes = []
        for x in range(self.teams):
            self.skullTimes.append(0)

        self.GAMESTATE = "ODDBALL"
        self.VICTORY = False
        if self.GAMEMODE == "1v1":
            self.roundTime = 60
        else:
            self.roundTime = self.MAXROUNDLENGTH

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
            i = self.pawnHelpList.index(pawn)%self.playerTeams
            self.allTeams[i].add(pawn)


    def add_player(self, name, image, client):
        self.playerFilesToGen.append((name, image, client))

    def threadedGeneration(self, name, image, client):
        self.pawnGenI += 1
        
        print("File ready!")
        
        pawn = Pawn(self, name, image, client)
        #if client:
        
        #else:
        #    pawn.team = self.playerTeams + self.pawnHelpList.index(pawn)%(self.teams - self.playerTeams)
        pawn.teamColor = self.getTeamColor(pawn.team.i)
        self.ENTITIES.append(pawn)
            

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

    def getTeamColor(self, team, intensity = 1):

        hue = (team * 1/self.teams) % 1.0  # Cycle hue every ~6 teams
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        return [int(r * 255 * intensity), int(g * 255 * intensity), int(b * 255 * intensity)]

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
        return max(abs(self.levelUpI-(self.LEVELUPTIME/2))-(self.LEVELUPTIME/2 - 1),0)
    
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

        text_t = min(max((self.LEVELUPTIME-self.levelUpI) - 0.8, 0)/0.7, 1.0)
        text = combinedText(self.pendingLevelUp.name, self.pendingLevelUp.teamColor, f" LEVELED UP (LVL {self.pendingLevelUp.level+1})", [255]*3, font=self.fontLarge)
        text.set_alpha(int(255 * (1-I)))
        self.screen.blit(text, self.res/2 - [0, 150] - v2(text.get_size())/2)

        r1 = pygame.Rect(self.res[0]/2 - 400, 800, 800, 30)
        pygame.draw.rect(self.screen, [255,255,255], r1, width=1)
        r2 = r1.copy()
        ir2 = max(0, 1-(self.LEVELUPTIME-self.levelUpI)/self.LEVELUPTIME)
        r2.width = ir2*796
        r2.height = 26
        r2.center = r1.center
        pygame.draw.rect(self.screen, [255,255*ir2,255*ir2], r2)

        t = self.font.render("Omistetut esineet:", True, [255]*3)
        self.screen.blit(t, [40, 400])
        for i, y in enumerate(self.pendingLevelUp.pastItems):
            t = self.font.render(y, True, [255]*3)
            self.screen.blit(t, [40, 430 + 30*i])

        amountOfItems = len(self.pendingLevelUp.nextItems)
        for x in range(amountOfItems):
            xpos = (x-(amountOfItems/2 - 0.5))*450 + self.res[0]/2
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
            

    def handleUltingCall(self):
        if self.ultCalled:
            self.ultFreeze += self.deltaTimeR
            self.ultFreeze = min(1, self.ultFreeze) 
        else:
            if "space" in self.keypress:
                self.ultCalled = True
            self.ultFreeze -= self.deltaTimeR
            self.ultFreeze = max(0, self.ultFreeze) 

        self.deltaTime *= 1 - 0.99 * self.ultFreeze

    def handleUlting(self):
        d = self.darken[round((self.ultFreeze)*19)]
        self.screen.blit(d, (0,0))
        t = self.fontLarge.render("KUKA ULTAA?", True, [255]*3)
        t.set_alpha(int(255 * self.ultFreeze))
        self.screen.blit(t, (self.res[0]/2 - t.get_width()/2, 100 - t.get_height()/2))

        yPos = 200
        for pawn in self.pawnHelpList:
            # Create a button for each pawn
            if pawn.NPC:
                continue
            
            t = self.font.render(pawn.name, True, self.getTeamColor(pawn.team))
            if self.ultFreeze < 1:
                t.set_alpha(int(255 * self.ultFreeze))

            r = t.get_rect()
            r.center = (self.res[0]/2, yPos + 30)
            if r.collidepoint(self.mouse_pos) and self.ultCalled:
                t = self.font.render(pawn.name, True, [255,255,255])
                if "mouse0" in self.keypress:
                    self.ultCalled = False
                    self.cameraLock = pawn
                    pawn.ULT_TIME = 30
                    self.clicks[1].play()


            self.screen.blit(t, r.topleft)
            yPos += 40

    def handleCameraLock(self):


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
        self.GAMEMODE = None
        self.PEACEFUL = True
        self.objectiveCarriedBy = None
        self.teamInspectIndex = 0
        self.mapCreated = False
        self.cameraLock = None
        if self.skull:
            self.skull.kill()

            
        for x in self.pawnHelpList:
            x.team = x.originalTeam
            x.enslaved = False
            x.reset()
            x.defaultPos()
            x.respawnI = 0


        self.refreshShops()
        self.particle_list.clear()
        self.round += 1
        if self.round == 2 and False:
            self.judgePawns()


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
            
        
            pygame.draw.rect(self.MAP, (0,0,0), (x*self.tileSize,y*self.tileSize, 
                                                 self.tileSize, self.tileSize))

    def drawTurfs(self):
        for r in self.map.rooms:
            if r.turfWarTeam is not None:
                rect = pygame.Rect(r.x*self.tileSize, r.y*self.tileSize, 
                                   r.width*self.tileSize, r.height*self.tileSize)
                rect.topleft -= self.cameraPosDelta
                draw_rect_perimeter(self.DRAWTO, rect, time.time()-self.now, 200, 10, self.getTeamColor(r.turfWarTeam), width=5)

    def tickScoreBoard(self):
        y = 200

        if self.GAMEMODE == "ODDBALL":
            for i, x in sorted(enumerate(self.skullTimes), key=lambda pair: pair[1], reverse=True):
                t = combinedText(f"TEAM {i + 1}: ", self.getTeamColor(i), f"{x:.1f} seconds", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22
        elif self.GAMEMODE in "TEAM DEATHMATCH":
            kills = [0 for _ in range(self.teams)]
            for p in self.pawnHelpList:
                kills[p.team.i] += p.kills

            for i, x in sorted(enumerate(kills), key=lambda pair: pair[1], reverse=True):
                t = combinedText(f"TEAM {i + 1}: ", self.getTeamColor(i), f"{x} kills", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22
        
        elif self.GAMEMODE == "1v1":
            kills = [0 for _ in range(len(self.duelPawns))]
            for i, p in enumerate(self.duelPawns):
                kills[i] = p.kills

            for i, x in sorted(enumerate(kills), key=lambda pair: pair[1], reverse=True):
                t = combinedText(f"{self.duelPawns[i].name}: ", self.getTeamColor(self.duelPawns[i].team), f"{x} kills", self.getTeamColor(self.duelPawns[i].team), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22
            
            return


        elif self.GAMEMODE == "TURF WARS":
            rooms = [0 for _ in range(self.teams)]
            for r in self.map.rooms:
                if r.turfWarTeam is not None:
                    rooms[r.turfWarTeam] += 1

            for i, x in sorted(enumerate(rooms), key=lambda pair: pair[1], reverse=True):

                all_enslaved = all(x.enslaved for x in self.pawnHelpList if x.originalTeam == i)

                t = combinedText(f"TEAM {i + 1}: ", self.getTeamColor(i), f"{x} rooms" if not all_enslaved else "ORJUUTETTU", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22


        y += 22

        for x in sorted(self.pawnHelpList.copy(), key = lambda p: p.kills, reverse=True):

            t = combinedText(f"{x.name}: ", x.teamColor, f"LVL {x.level}  {x.kills}/{x.deaths}", [255,255,255], font=self.fontSmaller)
            self.screen.blit(t, [10,y])
            y += 22


    
    def drawRoundInfo(self):
        t1 = self.fontSmaller.render("Round: " + str(self.round+1), True, [255]*3)
        t2 = self.font.render(self.GAMEMODE, True, [255]*3)
        
        self.screen.blit(t1, [self.res[0]/2 - t1.get_size()[0]/2, 10])
        self.screen.blit(t2, [self.res[0]/2 - t2.get_size()[0]/2, 40])

        minutes = int(self.roundTime / 60)
        seconds = int(self.roundTime % 60)
        t3 = self.font.render(f"{minutes:02}:{seconds:02}", True, [255]*3)
        self.screen.blit(t3, [self.res[0]/2 - t3.get_size()[0]/2, 70])
        



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


    def judgePawns(self):
        self.judgementTime = 0
        self.judgementIndex = 0
        self.pregametick = "judgement"
        self.judge = True
        self.judgements = []
        # Most deaths
        self.judgementPhases = ["nextup", "reveal", "drink"]
        self.judgementPhase = "nextup"
        self.judgementDrinkTime = 0  # Will be randomized between 5–30

        tempPawn = max(self.pawnHelpList, key=lambda p: p.stats["deaths"])
        self.judgements.append((tempPawn, "Eniten kuolemia", f" on kuollut eniten ({tempPawn.stats['deaths']})"))
        # Most team kills
        tempPawn = max(self.pawnHelpList, key=lambda p: p.stats["teamkills"])
        self.judgements.append((tempPawn, "Eniten tiimitappoja", f" on tappanut eniten tiimitovereita ({tempPawn.stats['teamkills']})"))
        # Most suicides
        tempPawn = max(self.pawnHelpList, key=lambda p: p.stats["suicides"])
        self.judgements.append((tempPawn, "Eniten itsemurhia", f" on tappanut itseään eniten ({tempPawn.stats['suicides']})"))
        # Most damage taken
        tempPawn = max(self.pawnHelpList, key=lambda p: p.stats["damageTaken"])
        self.judgements.append((tempPawn, "Eniten vahinkoa vastaanotettu", f" on ottanut eniten vahinkoa ({int(tempPawn.stats['damageTaken'])})"))
        # A random pawn
        if self.pawnHelpList:
            randomPawn = random.choice(self.pawnHelpList)
            self.judgements.append((randomPawn, "Tää äijä vaan haisee", " haisi eniten rng generaattorin mielestä!"))
        else:
            print("No pawns to judge!")
            return

    def genPawns(self):
        if self.pawnGenI < 3 and self.playerFilesToGen:

            name, image, client = random.choice(self.playerFilesToGen)
            self.playerFiles.append(name)
            self.playerFilesToGen.remove((name, image, client))

            #p = "players/" if non_npc else "npcs/"
            if client:
                if client != "DEBUG":
                    client_ip, client_port = client.remote_address
                else:
                    client_ip = "DEBUG"
            else:
                client_ip = None

            t = threading.Thread(target=self.threadedGeneration, args=(name, image, client_ip))
            t.daemon = True
            t.start()
        
    def resetLevelUpScreen(self):
        self.levelUpI = self.LEVELUPTIME
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

            #self.screen.fill((0, 0, 0))
            elapsed = time.time() - self.now

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
