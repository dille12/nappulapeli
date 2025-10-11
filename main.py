import pygame
import os, sys
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
from utilities.item import Item
from keypress import key_press_manager
from utilities.skull import Skull
import colorsys
from utilities.infoBar import infoBar
from utilities.shop import Shop
from particles.particle import ParticleSystem, Particle
from core.console import runConsole, getCodeSuggestions, handleConsoleEvent
from gameTicks.settingsTick import settingsTick, createSettings
from gameTicks.qrCodesTick import createQRS, qrCodesTick
from gameTicks.pawnGeneration import preGameTick
from gameTicks.tick import battleTick
from gameTicks.millionaire import millionaireTick, initMillionaire
from gameTicks.gameModeTick import GlitchGamemodeDisplay, loadingTick
from core.drawRectPerimeter import draw_rect_perimeter
from core.getCommonRoom import find_farthest_room
import asyncio
from core.qrcodeMaker import make_qr_surface
from pawn.teamLogic import Team
import subprocess, glob
from extractLyrics import get_subs_for_track
from utilities.camera import Camera
from core.modularSurface import modularSurface as MSurf
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

from core.valInit import valInit  # --- IGNORE ---

class Game(valInit):
    def __init__(self):
        super().__init__()
        getCodeSuggestions(self)
        

    def addToPlaylist(self, trackLink):

        i = infoBar(self, f"Adding a song")

        out_dir = "tracks"
        os.makedirs(out_dir, exist_ok=True)

        # Run yt-dlp
        subprocess.run([
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "-o", f"{out_dir}/%(title)s.%(ext)s",
            trackLink
        ], check=True)

        # Find the most recent file in tracks/
        files = glob.glob(os.path.join(out_dir, "*.mp3"))
        if not files:
            raise RuntimeError("No mp3 downloaded.")
        latest = max(files, key=os.path.getctime)
        
        i.killed = True
        # Queue in pygame

        self.musicQueue.append(latest)
        print("QUEUE")
        print(self.musicQueue)

    def draw_notification(self, text, x, y, start_time, color=(255, 255, 255)):
        current_time = pygame.time.get_ticks() - start_time
        duration = 2500
        
        if current_time > duration:
            return True
        
        # Phase timing
        drop_time = 400
        hold_time = 1500
        rise_time = 600

        riseAmount = 1000
        
        # Position calculation
        if current_time < drop_time:
            # Dropping phase
            progress = current_time / drop_time
            ease_progress = progress * progress * (3 - 2 * progress)  # Smoothstep
            pos_y = y - riseAmount + riseAmount * ease_progress
        elif current_time < drop_time + hold_time:
            # Holding phase
            pos_y = y
        else:
            # Rising phase
            rise_progress = (current_time - drop_time - hold_time) / rise_time
            ease_progress = rise_progress * rise_progress
            pos_y = y - riseAmount * ease_progress
        
        # Violent vibration
        shake_intensity = 5 if drop_time <= current_time <= drop_time + hold_time else 5
        shake_x = random.randint(-shake_intensity, shake_intensity)
        shake_y = random.randint(-shake_intensity, shake_intensity)
        final_x = x + shake_x
        final_y = pos_y + shake_y
        
        # Glitch effects
        glitch_chance = 0.3 if drop_time <= current_time <= drop_time + hold_time else 0.1
        
        if random.random() < glitch_chance:
            # Color corruption
            r, g, b = color
            glitch_color = (
                max(0, min(255, r + random.randint(-100, 100))),
                max(0, min(255, g + random.randint(-100, 100))),
                max(0, min(255, b + random.randint(-100, 100)))
            )
        else:
            glitch_color = color
        
        # Render text
        text_surface = self.notificationFont.render(text, True, glitch_color)
        
        # Digital corruption effect
        if random.random() < glitch_chance:
            # Horizontal line displacement
            for line in range(0, text_surface.get_height(), 2):
                if random.random() < 0.4:
                    line_rect = pygame.Rect(0, line, text_surface.get_width(), 1)
                    line_surface = text_surface.subsurface(line_rect).copy()
                    offset = random.randint(-10, 10)
                    text_surface.blit(line_surface, (offset, line))
        
        # Chromatic aberration
        if random.random() < 0.2:
            red_surface = text_surface.copy()
            blue_surface = text_surface.copy()
            red_surface.fill((255, 0, 0), special_flags=pygame.BLEND_MULT)
            blue_surface.fill((0, 0, 255), special_flags=pygame.BLEND_MULT)
            
            text_rect = red_surface.get_rect(center=(final_x - 2, final_y))
            self.screen.blit(red_surface, text_rect)
            text_rect = blue_surface.get_rect(center=(final_x + 2, final_y))
            self.screen.blit(blue_surface, text_rect)
        
        # Main text
        text_rect = text_surface.get_rect(center=(final_x, final_y))
        self.screen.blit(text_surface, text_rect)
        

        
        return False
                    

    def refreshShops(self):
        self.shops = []
        for x in range(self.teams):
            self.skullTimes.append(0)
            shop = Shop(self, x)
            shop.totalPrice = [0, 0]
            self.shops.append(shop)

    def handleMainMusic(self):
        if pygame.mixer.music.get_busy():
            return
        if self.musicQueue:
            next_track = self.musicQueue.pop(0)
 
            self.subs = get_subs_for_track(next_track)
            
            print("Playing from queue:", next_track)
            pygame.mixer.music.load(next_track)
            pygame.mixer.music.play()
            pygame.mixer.music.set_volume(0.4)
            self.musicStartTime = time.time()
            self.subI = 0
        else:
            self.musicQueue = os.listdir("tracks")
            self.musicQueue = ["tracks/" + track for track in self.musicQueue if track.endswith(".mp3")]
            random.shuffle(self.musicQueue)
    
    def drawSubs(self):
        if not self.subs:
            return
        if self.subI >= len(self.subs):
            return
        currentTime = time.time() - self.musicStartTime
        start, text = self.subs[self.subI]
        if self.subI + 1 >= len(self.subs):
            end = start + 2
        else:
            end, _ = self.subs[self.subI + 1]
        if currentTime >= start:
            if currentTime <= end:
                self.lastSubTime += self.deltaTimeR

                if self.lastSubTime <= 0.1:
                    y_offset = 200 - 200 * (self.lastSubTime / 0.1)  # ease in first 0.1s
                elif self.lastSubTime <= 1.0:
                    y_offset = 0  # fully visible
                else:
                    # Quadratic falloff after 1 second
                    t = self.lastSubTime - 1.0
                    falloff = max(0.0, 1.0 - t)  # linear decay 1 → 0
                    y_offset = (1 - falloff ** 2) * 200  # quadratic easing for smooth drop
                subSurf = self.fontLarge.render(text, True, (255,255,255))
                subRect = subSurf.get_rect(center=(self.res[0]//2, self.res[1]-100 + y_offset))
                self.screen.blit(subSurf, subRect)
            else:
                self.subI += 1
                self.lastSubTime = 0


    def handleTurfWar(self):
        if self.GAMEMODE == "TURF WARS":
            for r in self.map.rooms:
                if len(r.pawnsPresent) == 0:
                    r.occupyI += self.deltaTime
                    r.occupyI = min(5, r.occupyI)
                    continue
                
                team_counts = {}
                for pawn in r.pawnsPresent:
                    team_counts[pawn] = team_counts.get(pawn, 0) + 1
                
                max_count = max(team_counts.values())
                teams_with_max = [team for team, count in team_counts.items() if count == max_count]
                
                if len(teams_with_max) == 1:
                    majority_team = teams_with_max[0]
                    
                    if r.turfWarTeam != majority_team:
                        r.occupyI -= self.deltaTime * max_count
                        if r.occupyI <= 0:
                            self.switchRoomOwnership(r, majority_team)
                    else:
                        r.occupyI += self.deltaTime
                        r.occupyI = min(5, r.occupyI)
                else:
                    r.occupyI = max(0, r.occupyI - self.deltaTime * 0.5)

    def switchRoomOwnership(self, r, majority_team):
        if r in self.teamSpawnRooms:
            teamI = r.turfWarTeam
            originalTeam = self.teamSpawnRooms.index(r)
            team = self.allTeams[teamI]
            if originalTeam != majority_team:
                self.notify(f"Team {originalTeam+1} was captured!", self.getTeamColor(originalTeam))
                team.slaveTo(self.allTeams[majority_team])
            else:
                self.notify(f"Team {originalTeam+1} emancipated!", self.getTeamColor(originalTeam))
                team.emancipate()
        
        r.turfWarTeam = majority_team
        r.occupyI = 0


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
    
    def resetApp(self):
        os.execv(sys.executable, ['python'] + sys.argv)
    
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

        self.shitGrid = np.zeros(self.map.grid.shape, dtype=np.uint8)
        self.shitDict = {}

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

            for y in x.connections:
                y.turfWarTeam = team

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
            
        #self.MAP = MSurf(self, self.MAP)

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


    def cell2Pos(self, cell):
        return v2(cell) * self.tileSize + [self.tileSize/2, self.tileSize/2]

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

        
        self.VICTORY = False
        if self.GAMEMODE == "1v1":
            self.roundTime = 60
        else:
            self.roundTime = self.MAXROUNDLENGTH


        self.cameraLinger = 0
        for i in range(1):
            for pawn in self.pawnHelpList:
                pawn.reset()
                pawn.kills = 0
                pawn.teamKills = 0
                pawn.suicides = 0
                pawn.deaths = 0

        self.GAMESTATE = "ODDBALL"

            
        
        
        
    def onScreen(self, pos):
        r = pygame.Rect(self.cameraPosDelta, self.res)
       
        onDualScreen = False

        if self.DUALVIEWACTIVE:
            r2 = pygame.Rect(self.posToTargetTo2, self.res)
            onDualScreen = r2.collidepoint(pos)
        #r2.inflate_ip(self.app.res)

        

        if not r.collidepoint(pos) and not onDualScreen:
            return False
        return True
        


    def playSound(self, l):
        for x in l:
            x.stop()
        random.choice(l).play()

    def loadSound(self, fileHint, startIndex = 1, suffix=".wav", volume = 0.3, asPygame = False):
        l = []
        while True:
            f = fileHint + str(startIndex) + suffix
            if os.path.exists(f):
                if asPygame:
                    l.append(pygame.mixer.Sound(f))
                    l[-1].set_volume(volume)
                else:
                    l.append(f)
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
        #pawn.teamColor = self.getTeamColor(pawn.team.i)
        self.ENTITIES.append(pawn)
        #self.reTeamPawns()

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
    
    def debugEnslavement(self):
        r = random.choice(self.teamSpawnRooms)
        t = self.teamSpawnRooms.index(r)
        team = self.allTeams[t]
        #for x in team.pawns:
        #    x.die()
        self.log(f"Killed all pawns of team {t+1}")
        self.switchRoomOwnership(r, random.randint(0, self.teams-1))
    
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
        self.screen.blit(t, [self.res[0] - 20 - t.get_size()[0], 500 + self.debugI * 22])
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

        IM = self.pendingLevelUp.levelUpImage



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
                if self.cameraLock.target:
                    self.cameraIdleTime = 0
                    if not self.pendingLevelUp and not self.VICTORY:
                        self.CREATEDUAL = True
                        self.cameraLockTarget = self.cameraLock.target.pos.copy() * 0.1 + self.cameraLockTarget * 0.9
                        self.cameraLockOrigin = self.cameraLock.pos.copy()
                else:
                    self.cameraIdleTime += self.deltaTimeR

                if self.cameraIdleTime > 5:
                    self.cameraLock = None
                    self.cameraLinger = 0
                    self.cameraIdleTime = 3
                    
        
        else:
            self.cameraLinger -= self.deltaTime
            self.cameraIdleTime = 0


        if self.VICTORY:
            I = max(self.endGameI-4, 0)
            self.SLOWMO = 1 - 0.5*(1-I)
            
            self.cameraLock = max(
                (x for x in self.pawnHelpList if (x.team == self.victoryTeam and not x.killed)),
                key=lambda x: x.kills,
                default=None
            )

        
        elif self.pendingLevelUp:
            #self.cameraLockOrigin = self.pendingLevelUp.pos.copy() - self.res/2

            I = self.levelUpTimeFreeze()

            self.SLOWMO = 1 - 0.5*(1-I)
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

        for x in self.allTeams:
            x.emancipate()
            
        for x in self.pawnHelpList:
            self.allTeams[x.originalTeam].add(x)
            x.enslaved = False
            x.killed = False
            x.reset()
            x.defaultPos()
            x.respawnI = 0


        self.refreshShops()
        self.particle_list.clear()
        self.round += 1
        if self.round == 2:
            self.judgePawns()
        self.LAZER.deactivate()


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
                t1 = self.font.render(f"RELOADING: {procent}%", True, c2)
                self.screen.blit(t1, (230, yPos+35))
            else:
                t1 = self.font.render(f"Bullets: {p.weapon.magazine}/{p.getMaxCapacity()}", True, c2)
                self.screen.blit(t1, (230, yPos+35))

            t1 = self.font.render(f"KILLS: {p.kills} DEATHS: {p.deaths} (KD:{p.kills/max(1, p.deaths):.1f})", True, c2)
            self.screen.blit(t1, (230, yPos+70))


            xpTillnextLevel = self.levelUps[p.level-1] - p.xp

            t1 = self.font.render(f"XP: {p.xp} Remaining: {xpTillnextLevel}", True, c2)
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
        for startPos, endPos, color in self.BFGLasers:
            s1 = startPos - self.cameraPosDelta
            e1 = endPos - self.cameraPosDelta
            #if (0 <= s1[0] <= self.res[0] and 0 <= s1[1] <= self.res[1]) or (0 <= e1[0] <= self.res[0] and 0 <= e1[1] <= self.res[1]):
            self.LAZER.draw(self.DRAWTO, s1, e1, color)
            currLaser = True

        #if currLaser != self.lastTickLaser:
        #    if currLaser:
        #        self.LAZER.activate()
        #    else:
        #        self.LAZER.deactivate()
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

        judges = []

        nonNpcList = [x for x in self.pawnHelpList if not x.NPC]

        tempPawn = max(nonNpcList, key=lambda p: p.stats["deaths"])
        judges.append(tempPawn)
        self.judgements.append((tempPawn, "Eniten kuolemia", f" on kuollut eniten ({tempPawn.stats['deaths']})"))
        # Most team kills
        tempPawn = max(nonNpcList, key=lambda p: p.stats["teamkills"])
        if tempPawn not in judges:
            judges.append(tempPawn)
            self.judgements.append((tempPawn, "Eniten tiimitappoja", f" on tappanut eniten tiimitovereita ({tempPawn.stats['teamkills']})"))
        # Most suicides
        tempPawn = max(nonNpcList, key=lambda p: p.stats["suicides"])
        if tempPawn not in judges:
            judges.append(tempPawn)
            self.judgements.append((tempPawn, "Eniten itsemurhia", f" on tappanut itseään eniten ({tempPawn.stats['suicides']})"))
        # Most damage taken
        tempPawn = max(nonNpcList, key=lambda p: p.stats["damageTaken"])
        if tempPawn not in judges:
            judges.append(tempPawn)
            self.judgements.append((tempPawn, "Eniten vahinkoa vastaanotettu", f" on ottanut eniten vahinkoa ({int(tempPawn.stats['damageTaken'])})"))
        # A random pawn
        if nonNpcList:
            randomPawn = random.choice(nonNpcList)
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

    def playPositionalAudio(self, audio, pos = None):

        if isinstance(audio, list):
            audio = random.choice(audio)

        center = self.AUDIOORIGIN.copy()

        return self.AUDIOMIXER.playPositionalAudio(audio, pos, center)
    

    def setValue(self, varName, value):
        if varName in self.__dict__:
            self.__dict__[varName] = value
            return True
        return False
    
    def getPawn(self, name):
        for x in self.pawnHelpList:
            if x.name == name:
                return x
        return None
    
    def log(self, text):
        self.consoleLog.append(str(text))

    def changeChunkSize(self, newSize):
        self.AUDIOMIXER.changeChunkSize(newSize)

    def initAudioEngine(self):
        self.log("Initializing audio engine...")
        self.playPositionalAudio("audio/shit.wav", v2(random.uniform(-3000, 3000), random.uniform(-3000, 3000)))
        self.log("Audio engine initialized.")

    def notify(self, text, color = [255,255,255]):
        self.notificationTime = pygame.time.get_ticks()
        self.currNotification = [text, color]

    def run(self):
        self.frameTimeCache = []
        timeSum = 0
        while True:
            self.SLOWMO = 1
            self.mankkaDistance = float("inf")
            tickStartTime = time.time()

            key_press_manager(self)
        
            self.debugI = 0



            if self.GAMESTATE != "pawnGeneration" or self.pregametick == "judgement":
                self.shopTimer = self.midRoundTime
            else:
                self.shopTimer -= self.deltaTimeR
                self.shopTimer = max(0, self.shopTimer)

            if self.GAMESTATE == "settings":
                settingsTick(self)

            elif self.GAMESTATE == "pawnGeneration":
                preGameTick(self)

            elif self.GAMESTATE == "loadingScreen":
                loadingTick(self)
            
            elif self.GAMESTATE == "millionaire":
                millionaireTick(self)

            elif self.GAMESTATE == "qrs":
                qrCodesTick(self)

            else:
                battleTick(self)


            if self.mankkaDistance < 2000:
                vol = max(0, min(1, (2000 - self.mankkaDistance) / 2000))
                self.mankkaSound.set_volume(vol)
                if not self.mankkaSound.get_num_channels():
                    self.mankkaSound.play()
            else:
                self.mankkaSound.set_volume(0)
                self.mankkaSound.stop()

            for x in self.infobars:
                x.tick()
            #self.musicSwitch = self.handleMusic()
            if self.GAMESTATE in ["millionaire"]:
                pygame.mixer.music.unload()
                pygame.mixer.music.stop()
            else:
                #self.handleMainMusic()
                #self.drawSubs()
                pass
                #self.BPM()
            #r = pygame.Rect((0,0), self.res)
            #pygame.draw.rect(self.screen, [255,0,0], r, width=1+int(5*(self.beatI**2)))

            #self.screen.fill((0, 0, 0))
            elapsed = time.time() - self.now

            if self.currNotification:
                if self.draw_notification(self.currNotification[0], self.res.x/2, self.res.y/4, 
                                          self.notificationTime, color=self.currNotification[1]):
                    self.currNotification = None


           # for x in self.AUDIOMIXER.audio_sources:
           #     p = x.pos - self.cameraPosDelta
           #     pygame.draw.circle(self.screen, [255,0,0], p, 10)

            if "f1" in self.keypress:
               self.consoleOpen = not self.consoleOpen
            
            if self.consoleOpen:
                runConsole(self)

            pygame.display.update()
            self.t1 = time.time() - tickStartTime
            

            self.deltaTimeR = self.clock.tick(self.MAXFPS) / 1000
            self.t2 = time.time() - tickStartTime


            self.frameTimeCache.append(self.t2)
            timeSum += self.t2
            if len(self.frameTimeCache) > 144:
                tR = self.frameTimeCache.pop(0)
                timeSum -= tR
            

            self.FPS = len(self.frameTimeCache) / sum(self.frameTimeCache)
            self.MAXFRAMETIME = max(self.frameTimeCache)

            self.deltaTimeR = min(self.deltaTimeR, 1/30)
            self.deltaTime = self.deltaTimeR

def run():
    game = Game()
    #time.sleep(1)
    #getCodeSuggestions(game)
    game.run()

if __name__ == "__main__":
    run()
