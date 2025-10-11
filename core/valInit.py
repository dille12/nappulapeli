import time, pygame, os, threading
import numpy as np
from particles.particle import ParticleSystem
from pawn.teamLogic import Team
from pygame.math import Vector2 as v2
from utilities.camera import Camera
from pawn.weapon import Weapon
from core.loadAnimation import load_animation
from utilities.items import getItems, getItemsEng
from gameTicks.millionaire import initMillionaire
from gameTicks.settingsTick import createSettings
from gameTicks.qrCodesTick import createQRS
from gameTicks.gameModeTick import GlitchGamemodeDisplay
from particles.laser import ThickLaser
from audioPlayer.audioMixer import AudioMixer, AudioSource
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn

def generate_noise_surface(size):
    width, height = size
    noise_array = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    surface = pygame.Surface(size)
    pygame.surfarray.blit_array(surface, np.stack([noise_array]*3, axis=-1))
    return surface

class valInit:
    def __init__(self: "Game"):
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

        self.SCALE = 1

        self.teams = 2
        self.allTeams: list[Team] = []
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

        self.CAMERA = Camera(self, (0,0))

        self.consoleFont = pygame.font.Font("texture/terminal.ttf", 20)

        self.font = pygame.font.Font(self.fontName, 30)
        self.fontLarge = pygame.font.Font(self.fontName, 60)  # Load a default font
        self.notificationFont = pygame.font.Font(self.fontName, 140)
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
        

        self.hammer = Weapon(self, "Hammer", [0,0], "texture/hammer.png", 1, 1000, 1, 1, Weapon.skull, 1, "normal", sizeMult=0.5)

        self.weapons = [self.AK, self.e1, self.e2, self.e3, self.e4, self.pistol, self.pistol2, self.smg, self.famas, 
                        self.shotgun, self.mg, self.BFG, self.desert]

        self.firstPacket = self.AK.getPacket()
        self.BFGLasers = []

        self.skullW = Weapon(self, "Skull", [0,0], "texture/skull.png", 1, 1000, 1, 1, Weapon.skull, 1, "normal")

        #self.timbs = Item("Timbsit", speedMod=["add", 300])

        self.GAMEMODE = "TURF WARS"
        self.podiumPawn = None
        self.judgementIndex = 0
        self.judgementTime = 0
        self.pregametick = "shop"
        self.judgementPhases = ["nextup", "reveal", "drink"]
        self.judgementPhase = "nextup"
        self.judgementDrinkTime = 0  # Will be randomized between 5–30

        self.consoleOpen = False

        self.cameraIdleTime = 0

        self.DUALVIEWACTIVE = False

        self.shit = pygame.image.load("texture/shit.png").convert_alpha()

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
        
        self.MAXFRAMETIME = 0
        self.deltaTime = 1/60
        self.deltaTimeR = 1/60
        self.debugI = 0
        self.fontSmaller = pygame.font.Font(self.fontName, 18)  # Smaller font for debug text
        self.pawnGenI = 0
        self.pawnGenT = 0
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
        
        self.teamsSave = self.teams
        self.MINIMAPCELLSIZE = 2
        self.round = 0
        self.roundTime = 0
        self.MAXROUNDLENGTH = 60
        self.AUDIOORIGIN = v2(0, 0)

        self.ultCalled = False
        self.ultFreeze = 0

        self.gameModeLineUp = ["TURF WARS"] # "TEAM DEATHMATCH", "ODDBALL", "TURF WARS"

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

        self.levelUps = [round(5*(x+1) * (1.1) ** x) for x in range(100)]

        self.pendingLevelUp = None
        self.levelUpI = 5
        self.levelUpBlink = 1

        self.speeches = 0

        self.GAMESTATE = "qrs"
        initMillionaire(self)

        self.TRUCE = False
        self.FFA = False

        

        self.objectiveCarriedBy = None

        self.screenCopy1 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.screenCopy2 = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.skull = None
        self.skullVictoryTime = 100

        self.particle_system = ParticleSystem(self)

        self.bloodSplatters = []

        self.AUDIOMIXER = AudioMixer(self, chunk_size=1024)
        self.AUDIOMIXER.start_stream()
        
        self.SLOWMO = 1
        self.skullTimes = []
        self.refreshShops()


        self.midRoundTime = 0

        self.subs = None
        self.subI = 0
        self.lastSubTime = 0

        
        self.ARSounds = self.loadSound("audio/assault")

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
        self.consoleLog = []
        self.lastCommands = []

        print("Game initialized")