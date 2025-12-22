import time, pygame, os, threading
import numpy as np
from particles.particle import ParticleSystem
from pawn.teamLogic import Team
from pygame.math import Vector2 as v2
from utilities.camera import Camera
from pawn.weapon import Weapon
from core.loadAnimation import load_animation
from utilities.items import getItems
from gameTicks.millionaire import initMillionaire
from gameTicks.settingsTick import createSettings
from gameTicks.qrCodesTick import createQRS
from gameTicks.gameModeTick import GlitchGamemodeDisplay
from particles.laser import ThickLaser
from audioPlayer.audioMixer import AudioMixer, AudioSource
import random
from utilities.babloBG import SpeedLines
from utilities.bosslyrics import getLyricTimes
from typing import TYPE_CHECKING
from utilities.fireSystem import FireSystem
from collections import deque
from pawn.turret import Turret
from imageprocessing.imageProcessing import trim_surface
if TYPE_CHECKING:
    from main import Game
from pawn.pawn import Pawn
from gameTicks.pawnExplosion import getFade
def generate_noise_surface(size):
    width, height = size
    noise_array = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    surface = pygame.Surface(size)
    pygame.surfarray.blit_array(surface, np.stack([noise_array]*3, axis=-1))
    return surface

import json
import os
from core.ipManager import get_local_ip

CONFIG_DIR = "configs"
MAIN_CONFIG_PATH = os.path.join(CONFIG_DIR, "main.json")

DEBUG_VARS = [
    "AUTOPLAY",
    "TRAINCTSPAWNTIME",
    "STRESSTEST",
    "RENDERING",
    "FIXED_FRAMERATE",
    "midRoundTime",
    "gameModeLineUp",
    "maxWins",
    "DOREALGAMEMODES",
    "XPBASE",
    "MAKEDEBUGPAWNS",
    "DISABLEDEBUGTEXT",
    "NPC_WEAPONS_PURCHASE",
    "REGISTER_WEAPON_KILLS",
    "SET_SEED",
    "TRAIN_TIME",
    "ENABLEGRENADES",
    "RENDER_SCALE",
    "QUALITY_PRESET",
    
]




class valInit:
    def __init__(self: "Game"):
        self.now = time.time()

        self.consoleLog = []

        self.DOREALGAMEMODES = True
        self.AUTOPLAY = True
        self.TRAINCTSPAWNTIME = False
        self.STRESSTEST = False
        self.RENDERING = True

        self.FIXED_FRAMERATE = 20
        self.midRoundTime = 10
        self.stressTestFpsClock = 0
        self.PEACEFUL = True
        self.XPBASE = 5
        self.MAKEDEBUGPAWNS = True
        self.DISABLEDEBUGTEXT = True
        self.NPC_WEAPONS_PURCHASE = True
        self.REGISTER_WEAPON_KILLS = True
        self.SET_SEED = None
        self.TRAIN_TIME = 100
        self.RENDER_SCALE = 0.5
        self.QUALITY_PRESET = 1

        self.ENABLEGRENADES = True

        self.maxWins = 5

        self.gameModeLineUp = ["TEAM DEATHMATCH", "ODDBALL", "DETONATION", "FINAL SHOWDOWN"] #["TEAM DEATHMATCH", "ODDBALL", "DETONATION", "FINAL SHOWDOWN"] # , ,  "FINAL SHOWDOWN",  #,  "TEAM DEATHMATCH", 

        print("Loading config...")
        self.autoloadConfig()
        print("Done")

        self.LEVELSEED = 1

        self.local_ip = get_local_ip()

        if self.STRESSTEST:
            self.res = v2(854, 480)
            self.screen = pygame.display.set_mode(self.res, pygame.SRCALPHA)  # Delay screen initialization
        else:
            if self.QUALITY_PRESET == 3:
                self.res = v2(2560, 1440)
            elif self.QUALITY_PRESET == 2:
                self.res = v2(1920, 1080)
            elif self.QUALITY_PRESET == 1:
                self.res = v2(1366, 768)
            else:
                self.res = v2(854, 480)
            self.screen = pygame.display.set_mode(self.res, pygame.SRCALPHA | pygame.SCALED | pygame.FULLSCREEN)  # Delay screen initialization
        self.originalRes = self.res.copy()
        self.camRes = self.res.copy()
        self.camRes.x /= 2
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


        self.TOTAL_TIME_ADJUSTMENT = 1


        self.preConfiguredTeamNames = []

        self.gameModeDescriptions = {
            "TEAM DEATHMATCH": "Tiimit taistelevat toisiaan vastaan. Ensimmäinen 100 tappoa kerännyt joukkue, tai eniten tappoja saanut joukkue kierrosajan kuluessa voittaa. Tiimitappoja ei lasketa.",
            "ODDBALL": "Tiimit taistelevat pääkallon omistajuudesta. Pääkallon kantaja ei saa käyttää asettansa kalloa kantaessaan, mutta saa väliaikaisen pistoolin. Joukkue joka kantaa kalloa pisimpään voittaa kierroksen.",
            "TURF WARS": "Joukkueiden tulee vallata eniten kartan huoneista. Jos toisen joukkueen kotihuone vallataan, tämän joukkueen pelaajat orjuutetaan valtaajajoukkueen puolelle. Pelaaja muuttuu orjaksi kuollessaan, jos ja vain kun kotihuone on vallattu. Jos joukkueen pelaajat onnistuvat valtaamaan huoneensa takaisin, orjuutetut pelaajat vapautetaan. Eniten huoneita vallannut joukkue voittaa.",
            "DETONATION": "Joukkueet jaetaan kahteen joukkueeseen, terroristeihin ja vastaterroristeihin. Pelin alussa kolme huonetta merkitään pommikohteiksi. Terroristit ottavat yhden kohteista hyökkäyskohteekseen, ja yrittävät vallata sen puolustavilta vastaterroristeilta. Pommi asetetaan kohteeseen jos kohde vallataan, ja se räjähtää 40 sekunnissa. Vastaterroristit yrittävät vallata kohteen takaisin ja purkaa pommin, joka vie 10 sekuntia. Pommi ei voi räjähtää purun aikana. Jos terroristit räjäyttävät kaksi kohdetta, peli päättyy tasapeliin, kaikki joukkueet saavat pisteen. Jos terroristit saavat räjäytettyä kaikki kohteet, vain terroristit ansaitsevat pisteen. Jos terroristit räjäyttävät yhden tai alle kohdetta, vastaterroristit saavat yhden pisteen.",
            "FINAL SHOWDOWN": "error",
            "SUDDEN DEATH": "Pelaajilla on kaksinkertaiset HP:t ja vain yksi elämä. Viimeinen joukkue eloonjääneenä voittaa."
        }

        self.SCALE = 1

        self.teams = 2
        self.allTeams: list[Team] = []
        for i in range(self.teams):
            self.allTeams.append(Team(self, i))

        if self.MAKEDEBUGPAWNS:
            for x in os.listdir("players"):
                playerName = os.path.splitext(x)[0]
                file_path = os.path.join("players", x)
                with open(file_path, "rb") as f:
                    imageRaw = f.read()
                self.add_player(playerName, imageRaw, "DEBUG")

        self.clock = pygame.time.Clock()

        self.fontName = "texture/agencyb.ttf"

        self.CAMERAS = [Camera(self, (0,0)), Camera(self, (0,0)), Camera(self, (0,0)), Camera(self, (0,0))]
        self.CAMERAS[0].mainCamera = True

        for x in self.CAMERAS:
            x.cameraIndex = self.CAMERAS.index(x)

        self.CAMERA = self.CAMERAS[0]
        self.amountOfScreens = 1

        

        self.turretLeg = pygame.image.load("texture/turret_leg.png").convert_alpha()
        self.turretHead = pygame.image.load("texture/turret.png").convert_alpha()

        self.turretLeg = pygame.transform.scale_by(self.turretLeg, self.RENDER_SCALE)
        self.turretHead = pygame.transform.scale_by(self.turretHead, self.RENDER_SCALE)


        self.consoleFont = pygame.font.Font("texture/terminal.ttf", 20)

        self.font = pygame.font.Font(self.fontName, 30)
        self.fontLarge = pygame.font.Font(self.fontName, 60)  # Load a default font
        self.notificationFont = pygame.font.Font(self.fontName, int(140*self.RENDER_SCALE))
        self.fontLevel = pygame.font.Font(self.fontName, 40)  # Load a default font
        # image_path, damage, range, magSize, fireRate, fireFunction, reloadTime
        pygame.mixer.init()
        self.weapons = []
        self.AK = Weapon(self, "AK-47", [150, 0], "texture/ak47.png", 12, 1600, 30, 8, Weapon.AKshoot, 1.5, "normal")
        self.e1 = Weapon(self, "Sniper", [120, 0], "texture/energy1.png", 100, 5000, 5, 1, Weapon.Energyshoot, 2, "energy")
        self.e2 = Weapon(self, "Rocket Launcher", [200, 0], "texture/energy2.png", 125, 1600, 1, 0.5, Weapon.RocketLauncher, 3, "explosion")
        self.e3 = Weapon(self, "EMG", [100, 0], "texture/energy3.png", 14, 1000, 40, 14, Weapon.Energyshoot, 0.8, "energy")
        self.pistol = Weapon(self, "USP-S", [50, 0], "texture/pistol.png", 25, 2000, 12, 3, Weapon.suppressedShoot, 0.3, "normal", sizeMult=0.7)
        self.pistol2 = Weapon(self, "Glock", [30, 0], "texture/pistol2.png", 8, 1500, 20, 5, Weapon.pistolShoot, 0.5, "normal", sizeMult=0.7)
        self.smg = Weapon(self, "SMG", [80, 0], "texture/ump.png", 10, 1800, 45, 20, Weapon.smgShoot, 1, "normal", sizeMult=0.7)
        self.famas = Weapon(self, "FAMAS", [200, 0], "texture/famas.png", 23, 2300, 25, 6, Weapon.burstShoot, 1.4, "normal", burstTime=0.1, burstBullets=3)
        self.shotgun = Weapon(self, "Shotgun", [175, 0], "texture/shotgun.png", 7, 1300, 6, 1.5, Weapon.shotgunShoot, 0.8, "normal")
        self.mg = Weapon(self, "Machine Gun", [300, 1], "texture/mg.png", 15, 2500, 50, 16, Weapon.AKshoot, 4, "normal")
        self.BFG = Weapon(self, "BFG", [500, 1], "texture/bfg.png", 200, 2300, 50, 25, Weapon.BFGshoot, 2.5, "energy", sizeMult=1.2)
        self.e4 = Weapon(self, "E-BR", [150, 0], "texture/energy4.png", 15, 2700, 35, 10, Weapon.burstShoot, 1, "energy", burstBullets=2, burstTime=0.03)
        self.desert = Weapon(self, "Desert Eagle", [100, 0], "texture/desert.png", 45, 3000, 7, 2, Weapon.desertShoot, 0.75, "normal", sizeMult=0.85)


        self.BIGASSAK = Weapon(self, "BABLON AK-47", [150, 0], "texture/goldenAk.png", 12, 1600, 30, 8, Weapon.AKshoot, 1.5, "normal", sizeMult=2.2)
        

        self.hammer = Weapon(self, "Hammer", [0,0], "texture/hammer.png", 1, 1000, 1, 1, Weapon.skull, 1, "normal", sizeMult=0.5)

        self.flash = Weapon(self, "Flashbang", [0,0], "texture/flash.png", 1, 1000, 1, 1, Weapon.grenade, 1, "normal", sizeMult=1)
        self.frag = Weapon(self, "Frag Grenade", [0,0], "texture/frag.png", 1, 1000, 1, 1, Weapon.grenade, 1, "normal", sizeMult=1)
        self.turretNade = Weapon(self, "Turret Grenade", [0,0], "texture/turretNade.png", 1, 1000, 1, 1, Weapon.grenade, 1, "normal", sizeMult=1)

        self.weapons = [self.AK, self.e1, self.e2, self.e3, self.e4, self.pistol, self.pistol2, self.smg, self.famas, 
                        self.shotgun, self.mg, self.BFG, self.desert]

        self.firstPacket = self.AK.getPacket()
        self.BFGLasers = []

        self.skullW = Weapon(self, "Skull", [0,0], "texture/skull.png", 1, 1000, 1, 1, Weapon.skull, 1, "normal")
        self.bombW = Weapon(self, "Skull", [0,0], "texture/bomb.png", 1, 1000, 1, 1, Weapon.skull, 1, "normal")


        self.shopTimer = self.midRoundTime


        #self.timbs = Item("Timbsit", speedMod=["add", 300])

        self.GAMEMODE = None
        self.podiumPawn = None
        self.judgementIndex = 0
        self.judgementTime = 0
        self.pregametick = "shop"
        self.judgementPhases = ["nextup", "reveal", "drink"]
        self.judgementPhase = "nextup"
        self.judgementDrinkTime = 0  # Will be randomized between 5–30

        self.TRANSITION_INTO_SINGLE = False
        self.IN_SINGLE = False
        self.FADEOUTMANUAL = 0

        self.consoleOpen = False

        self.cameraIdleTime = 0

        self.DUALVIEWACTIVE = False

        self.shit = pygame.image.load("texture/shit.png").convert_alpha()
        self.shit = pygame.transform.scale_by(self.shit, self.RENDER_SCALE)


        self.babloLyricIndex = 0
        self.babloLyrics = getLyricTimes()
        self.babloLyricNorm = 0
        self.babloLyricCurrent = ""

        self.BLOCKMUSIC = False

        self.concrete = pygame.image.load("texture/concrete.png").convert()
        self.concretes = []
        self.tileSize = 75
        tile_w = 70
        w, h = self.concrete.get_width(), self.concrete.get_height()



        for i in range(w//tile_w):
            rect = pygame.Rect(i * tile_w, 0, tile_w, h)
            tile = self.concrete.subsurface(rect).copy()

            tile = pygame.transform.scale(tile, (self.tileSize*self.RENDER_SCALE, self.tileSize*self.RENDER_SCALE))

            self.concretes.append(tile)
        
        self.MAXFRAMETIME = 0
        self.deltaTime = 1/60
        self.deltaTimeR = 1/60
        self.debugI = 0
        self.fontSmaller = pygame.font.Font(self.fontName, 18)  # Smaller font for debug text
        self.fontSmallest= pygame.font.Font(self.fontName, 12) 
        self.pawnGenI = 0
        self.pawnGenT = 0
        self.fastForwardI = 0
        #self.map = ArenaGenerator(80, 60)

        self.killstreaks = [
            pygame.mixer.Sound("audio/quake/killingSpree.wav"),
            pygame.mixer.Sound("audio/quake/dominating.wav"),
            pygame.mixer.Sound("audio/quake/unstoppable.wav"),
            pygame.mixer.Sound("audio/quake/godlike.wav"),
            pygame.mixer.Sound("audio/quake/holyshit.wav"),
        ]
        for x in self.killstreaks:
            x.set_volume(0.4)
        
        self.killStreakText = [
            "is on a KILLING SPREE!",
            "is DOMINATING!",
            "is UNSTOPPABLE!",
            "is GODLIKE!",
            "HOLY SHIT!"
        ]

        
        # TEAM COUNT

        self.filmOnly = []
        self.winningTeam = None
        
        

        self.debugCells = []
        
        self.teamsSave = self.teams
        self.MINIMAPCELLSIZE = 2
        self.round = 0
        self.roundTime = 0
        self.MAXROUNDLENGTH = 60
        self.AUDIOORIGIN = v2(0, 0)
        self.AUDIOVOLUME = 0.3


        
        self.MANUALPAWN = None

        self.ultCalled = False
        self.ultFreeze = 0
        self.commonRoomSwitchI = 0

        self.bombInfoI = 0

        

        self.babloMusic = self.loadSound("audio/taikakeinu/bar", volume=0.75, asPygame=True)
        self.BABLO = None

        self.bulletImpactPositions = []

        self.roomTextures = []
        for x in os.listdir("texture/floorTiles"):
            im = pygame.image.load(f"texture/floorTiles/{x}").convert()
            im = pygame.transform.scale(im, [self.tileSize*self.RENDER_SCALE, self.tileSize*self.RENDER_SCALE])
            self.roomTextures.append(im)

        self.grass = pygame.image.load(f"texture/Asphalt3_img.jpg").convert()
        self.grass = pygame.transform.scale(self.grass, [self.tileSize, self.tileSize])



        self.speedlines = SpeedLines(num_lines=120, length=2000, width=10, speed=3)
        self.speedLinesSurf = pygame.Surface(self.res, pygame.SRCALPHA)

        self.teamInspectIndex = -1
        self.safeToUseCache = True
        self.cacheLock = threading.Lock()
        #self.map.generate_arena(room_count=int(self.teams*1.5)+4, min_room_size=8, max_room_size=20, corridor_width=3)
        self.killfeed = []
        self.keypress = []
        self.keypress_held_down = []

        self.crack = pygame.image.load("texture/crack.png").convert_alpha()
        self.crack = pygame.transform.scale_by(self.crack, 400 * self.RENDER_SCALE / self.crack.get_width())


        self.stains = []
        for x in ["texture/stain1.png", "texture/stain2.png"]:
            stain = pygame.image.load(x).convert_alpha()
            for x in range(5):
                s = stain.copy()
                s = pygame.transform.scale_by(s, random.randint(300,400) / stain.get_width() * self.RENDER_SCALE)
                s = pygame.transform.rotate(s, random.randint(0,360))
                s.set_alpha(random.randint(155,255))
                self.stains.append(s)


        self.killFeedMeleeIcon = pygame.image.load("texture/melee.png").convert_alpha()
        self.killFeedMeleeIcon = pygame.transform.scale_by(self.killFeedMeleeIcon, 20 / self.killFeedMeleeIcon.get_width())

        self.flashKillFeed = pygame.image.load("texture/flash.png").convert_alpha()
        self.flashKillFeed = pygame.transform.scale_by(self.flashKillFeed, 20 / self.flashKillFeed.get_width())

        self.fragKillFeed = pygame.image.load("texture/frag.png").convert_alpha()
        self.fragKillFeed = pygame.transform.scale_by(self.fragKillFeed, 20 / self.fragKillFeed.get_width())

        self.skullKillFeed = pygame.image.load("texture/death.png").convert_alpha()
        self.skullKillFeed = pygame.transform.scale_by(self.skullKillFeed, 30 / self.skullKillFeed.get_width())

        self.turretGrenadeKillFeed = pygame.image.load("texture/turretNade.png").convert_alpha()
        self.turretGrenadeKillFeed = pygame.transform.scale_by(self.turretGrenadeKillFeed, 20 / self.turretGrenadeKillFeed.get_width())
        
        
        self.crackAppearTimes = []
        beatsPerSec = 60/125
        start = 8 * 4 * beatsPerSec
        for bar in range(4):
            at = [0, 3.5, 4]
            for a in at:
                self.crackAppearTimes.append(start + (bar*8 + a)*beatsPerSec) 
        self.crackAppearTimes.append(start + (8*4)*beatsPerSec) 
        print(self.crackAppearTimes)
        self.crackIndex = 0

        self.SLOWMO_FOR = 0

        self.cracks = []
        for i in range(len(self.crackAppearTimes)):
            c = self.crack.copy()
            s = 0.5 + i/len(self.crackAppearTimes) * 4
            r = random.uniform(0, 360)
            c = pygame.transform.rotozoom(c, r, s)
            self.cracks.append(c)


        self.TTS_ON = True
        self.ITEM_AUTO = False

        self.t1 = 1
        self.t2 = 1

        self.FPS = 0

        
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
        
        self.cameraPosDelta = v2(0,0)
        self.cameraVel = v2(0,0)

        self.dualCameraPos = v2(0, 0)
        self.dualCameraPosDelta = v2(0,0)
        self.dualCameraVel = v2(0,0)


        self.bulletSprite = pygame.image.load("texture/bullet.png").convert_alpha()
        self.bulletSprite = pygame.transform.scale(self.bulletSprite, [200, 5])

        self.bulletSprite = pygame.transform.scale_by(self.bulletSprite, self.RENDER_SCALE)

        self.energySprite = pygame.image.load("texture/lazer.png").convert_alpha()
        self.energySprite = pygame.transform.scale(self.energySprite, [220, 8])

        self.energySprite = pygame.transform.scale_by(self.energySprite, self.RENDER_SCALE)


        self.resetRoundInfo()
        self.monitorProgress = 3

        self.visualEntities = []
        self.explosion = load_animation("texture/expl1", 0, 31, size = [int(700*self.RENDER_SCALE),700*self.RENDER_SCALE])
        self.items = getItems()
        print("ITEMS:", len(self.items))

        self.levelUps = [round(self.XPBASE*(x+1) * (1.1) ** x) for x in range(100)]

        self.pendingLevelUp = None
        self.levelUpI = 5
        self.levelUpBlink = 1

        self.speeches = 0
        
        self.GAMESTATE = "qrs"
        initMillionaire(self)

        self.onFireCells = []
        self.FireSystem = FireSystem(self)

        self.TRUCE = False
        self.FFA = False

        self.objectiveCarriedBy = None


        self.splitViews = []

        self.sp = pygame.Surface([self.res.x/2, self.res.y], pygame.SRCALPHA)
        self.splitViews.append(self.sp.copy())
        self.splitViews.append(self.sp.copy())

        self.screenCopy1 = pygame.Surface(self.sp.get_size(), pygame.SRCALPHA)
        self.screenCopy2 = pygame.Surface(self.sp.get_size(), pygame.SRCALPHA)

        self.screenCopy1FULL = pygame.Surface(self.originalRes, pygame.SRCALPHA)
        self.screenCopy2FULL = pygame.Surface(self.originalRes, pygame.SRCALPHA)
        

        self.skull = None
        self.skullVictoryTime = 100

        self.particle_system = ParticleSystem(self)

        self.bloodSplatters = []

        self.AUDIOMIXER = AudioMixer(self, chunk_size=1024)
        self.AUDIOMIXER.start_stream()
        
        self.SLOWMO = 1
        self.skullTimes = []
        self.refreshShops()

        self.FADEOUT = getFade(30)
        self.FADEIN = 0

        self.RAWR = pygame.mixer.Sound("audio/rawr.wav")
        self.RAWR.set_volume(0.2)

        self.TARGETGAMESTATE = None
        self.TRANSITION = False
        self.transIndex = 0

        

        


        self.USE_AI = False
        if self.USE_AI:
            #from core.rl_agent import LocalGoalAgent
            #self.AGENT = LocalGoalAgent(80, 120)
            pass

        self.AUTOCAMERA = True

        self.alwaysHostileTeam = Team(self, -1)

        self.subs = None
        self.subI = 0
        self.lastSubTime = 0

        self.SHOOTABLE = (Pawn, Turret)

        
        self.ARSounds = self.loadSound("audio/assault")

        self.turretHeadRGB = {}
        self.turretDamageSound = self.loadSound("audio/turretDamage/turretDamage")
        self.turretFireSound = self.loadSound("audio/turret_fire")

        self.turretKillIcon = pygame.image.load("texture/turretIcon.png").convert_alpha()
        self.turretKillIcon = trim_surface(self.turretKillIcon)
        self.turretKillIcon = pygame.transform.scale_by(self.turretKillIcon, 20 / self.turretKillIcon.get_height())

        self.deathScreams = os.listdir("audio/screams")

        self.deathSounds = self.loadSound("audio/death")

        self.hitSounds = self.loadSound("audio/hit")

        self.explosionSound = self.loadSound("audio/explosion")

        self.clicks = self.loadSound("audio/menu_click", asPygame = True)

        self.music = None
        self.currMusic = 0
        self.nextMusic = 0
        self.midMusicIndex = 0

        self.weaponButtonClicked = None
        self.hudChange = 1
        self.currHud = 0

        self.PAWNPARTICLES = []

        self.giveWeapons = False

        self.MAXFPS = 144
        self.TIMESCALE = 1

        


        self.bloodClearI = 0
        self.beatI = 0

        self.energySound = self.loadSound("audio/nrg_fire")
        self.shotgunSound = self.loadSound("audio/shotgun")
        self.silencedSound = self.loadSound("audio/silenced")

        self.waddle = self.loadSound("audio/waddle")

        self.rocketSound = self.loadSound("audio/rocket_launch")

        self.smgSound = self.loadSound("audio/smg")

        self.pistolSound = self.loadSound("audio/weapon_fire")

        self.hammerSound = self.loadSound("audio/hammer")

        if len(self.energySound) != 3:
            raise RuntimeError
        
        self.LAZER = ThickLaser(self, width=20)
        self.lastTickLaser = False


        self.mankkaDistance = float("inf")

        self.mankkaSound = pygame.mixer.Sound("audio/mankkamusic.wav")
        

        self.reloadSound = pygame.mixer.Sound("audio/reload.wav")
        self.meleeSound = self.loadSound("audio/melee") #pygame.mixer.Sound("audio/melee.wav")
        self.horn = pygame.mixer.Sound("audio/horn.wav")
        self.tripSound = pygame.mixer.Sound("audio/trip.wav")
        self.shitSound = pygame.mixer.Sound("audio/shit.wav")
        for x in [self.reloadSound, self.horn, self.tripSound, self.shitSound]:
            x.set_volume(0.3)

        createSettings(self)
        createQRS(self)
        
        self.notification_start_time = None
        self.currNotification = None

        self.gamemode_display = GlitchGamemodeDisplay(self)

        self.musicQueue = []

        self.console_input = ""
        self.consoleOpen = False
        self.consoleSuggestionI = 0
        self.lastCommands = []
        self.consoleIndicatorI = 0
        self.consoleIndicator = False

        self.initAudioEngine()

        print("Game initialized")

    def getConfigs(self):
        for x in os.listdir("configs"):
            self.log(str(x))

    def saveConfig(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {k: getattr(self, k) for k in DEBUG_VARS}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self.log(f"Config {path} created")


    def loadConfig(self, path):
        with open(path, "r") as f:
            data = json.load(f)
        for k, v in data.items():
            setattr(self, k, v)
        
        self.log(f"Config {path} loaded")

    def saveMainConfig(self, autoload_path):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(MAIN_CONFIG_PATH, "w") as f:
            json.dump({"autoload": autoload_path}, f, indent=2)
        self.log(f"Config {autoload_path} set to load on startup")


    def autoloadConfig(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)

        # create default config if main config is missing
        if not os.path.exists(MAIN_CONFIG_PATH):
            default_cfg_path = os.path.join(CONFIG_DIR, "default")
            self.saveConfig(default_cfg_path)
            self.saveMainConfig(default_cfg_path)
            return

        with open(MAIN_CONFIG_PATH, "r") as f:
            main = json.load(f)

        path = main.get("autoload")
        if not path:
            return

        # create default autoload target if missing
        if not os.path.exists(path):
            self.saveConfig(path)
            return

        self.loadConfig(path)
        self.saveConfig(path)
