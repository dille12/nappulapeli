print("Starting")
import pygame
import os, sys
import pygame.gfxdraw
from renderObjects.pawn.pawn import Pawn
from renderObjects.pawn.weapon import Weapon
import random
import threading
from renderObjects.bullet import Bullet
from utilities.enemy import Enemy
import math
from pygame.math import Vector2 as v2
import time
from levelGen.mapGen import ArenaGenerator, CellType, Room
import numpy as np
from levelGen.arenaWithPathfinding import ArenaWithPathfinding
from utilities.item import Item
from core.keypress import key_press_manager
from renderObjects.skull import Skull, Bomb
import colorsys
from utilities.infoBar import infoBar
from utilities.shop import Shop
from renderObjects.particles.particle import ParticleSystem, Particle
from core.console import runConsole, handleConsoleEvent
from gameTicks.gameEnd import gameEndTick
from gameTicks.settingsTick import settingsTick, createSettings
from gameTicks.qrCodesTick import createQRS, qrCodesTick
from gameTicks.pawnGeneration import preGameTick
from gameTicks.tick import battleTick
from gameTicks.millionaire import millionaireTick, initMillionaire
from gameTicks.gameModeTick import GlitchGamemodeDisplay, loadingTick
from core.drawRectPerimeter import draw_rect_perimeter
from core.getCommonRoom import find_farthest_room
from gameTicks.showcaseTick import showcaseTick
import asyncio
from core.qrcodeMaker import make_qr_surface
from renderObjects.pawn.turret import Turret
from renderObjects.pawn.teamLogic import Team
import subprocess, glob
from utilities.extractLyrics import get_subs_for_track
from utilities.camera import Camera
import inspect
from renderObjects.pawn.dialog import babloBreak, onCameraLock
import tkinter
from statistics import stdev
from collections import deque
from renderObjects.pawn.site import Site
from collections import Counter
from utilities.register import register_gun_kill
from gameTicks.intro import intro
from utilities.playMultipleSounds import play_sounds_sequential

print("Imports complete")


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
        self.getCodeSuggestions()
        

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

    def getCodeSuggestions(self):
        self.object_methods = {
            name: str(inspect.signature(member))
            for name, member in inspect.getmembers(self, predicate=inspect.ismethod)
            if member.__self__.__class__ is self.__class__ and not name.startswith("__")
        }
        self.object_variables = {
            name: None
            for name in vars(self).keys()
            if not name.startswith("__") and not callable(getattr(self, name))
        }

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

    def resetPawnParticles(self):

        if not self.PAWNPARTICLES:
            return

        for particle in self.PAWNPARTICLES:
            particle.reset()
        random.choice(self.PAWNPARTICLES).setAsMainPiece()
        # Sort the pawns list by particle xvel by absolute ascending
        self.PAWNPARTICLES.sort(key=lambda p: abs(p.xvel), reverse=True)

    def initiatePawnExplostion(self):
        self.TRANSITION = True
        self.transIndex = 0
        self.RAWR.play()
        self.resetPawnParticles()

    def transition(self, target):
        self.initiatePawnExplostion()
        self.TARGETGAMESTATE = target

    def clearEntities(self):
        print(f"Removing {len(self.visualEntities)} visual entities and {len(self.particle_list)} particles.")
        self.visualEntities.clear()
        self.particle_list.clear()
        print(f"{len(self.FireSystem.cells)} fire cells cleared.")
        self.FireSystem.clearCells()
        print("Total entities before cleanup:", len(self.ENTITIES))
        to_remove = []
        for x in self.ENTITIES:
            if not isinstance(x, Pawn):
                print("Removing entity of type:", str(type(x)))
                to_remove.append(x)
        for x in to_remove:
            self.ENTITIES.remove(x)

        to_remove = []
        print("Total pawnlist before cleanup:", len(self.pawnHelpList))
        for x in self.pawnHelpList:
            if not isinstance(x, Pawn):
                print("Removing entity of type:", str(type(x)))
                to_remove.append(x)
        for x in to_remove:
            self.pawnHelpList.remove(x)
                

    def drawExplosion(self):


        TRANSTIME = 60
        FRAME = int(self.transIndex*TRANSTIME)

        for particle in self.PAWNPARTICLES:
            if FRAME < len(particle.images):
                particle.update(self.screen, FRAME)

        if FRAME > TRANSTIME - len(self.FADEOUT):
            f_i = - TRANSTIME + len(self.FADEOUT) + FRAME
            f = self.FADEOUT[f_i]
            self.screen.blit(f, (0,0))
        self.transIndex += self.deltaTimeR
        if self.transIndex >= 1 or self.AUTOPLAY:
            self.TRANSITION = False
            self.FADEIN = len(self.FADEOUT) - 1
        
    

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


    def highLightCell(self, cell):
        #print("HIGHLIGHTING", cell)
        pos = self.convertPos(v2(cell) * self.tileSize)
        r = pygame.Rect(pos, [self.tileSize*self.RENDER_SCALE, self.tileSize*self.RENDER_SCALE])
        pygame.draw.rect(self.DRAWTO, [255,0,0], r, width=3)
    
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

    def handleKOTH(self):
        if self.GAMEMODE == "KING OF THE HILL":
            r = self.currHill
            
            team_counts = {}
            for pawn in r.pawnsPresent:
                team_counts[pawn] = team_counts.get(pawn, 0) + 1

            # uncontested: exactly one team present

            if len(team_counts) == 1:
                sole_team = next(iter(team_counts))
                if r.turfWarTeam is None:
                    self.notify("HILL CAPTURED", self.getTeamColor(sole_team))
                r.turfWarTeam = sole_team
            else:
                if r.turfWarTeam is not None:
                    self.notify("HILL CONTESTED")
                r.turfWarTeam = None  # contested

            if r.turfWarTeam is not None:
                self.allTeams[r.turfWarTeam].kothTime += self.deltaTime

            self.hillSwitchTime -= self.deltaTime
            if self.hillSwitchTime <= 0:
                self.switchHill()
                self.notify("HILL MOVED")


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
            #teamI = r.turfWarTeam
            originalTeam = self.teamSpawnRooms.index(r)
            team = self.allTeams[originalTeam]
            if originalTeam != majority_team:
                self.notify(f"{team.getName()} was captured!", self.getTeamColor(originalTeam))
                team.slaveTo(self.allTeams[majority_team])
            else:
                self.notify(f"{team.getName()} emancipated!", self.getTeamColor(originalTeam))
                team.emancipate()
        
        r.turfWarTeam = majority_team
        r.occupyI = 5


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
    
    def testEspeak(self):

        g = random.choice(["f", "m"])
        i = random.randint(1,5)
        l = random.choice(["fi", "et", "sv", "fr", "en"])
        voice = f"{l}+{g}{i}"
        self.consoleLog.append(voice)

        proc = subprocess.run([
                "espeak",
                "-s", "175",
                "-p", "50",
                "-v", voice,
                "Makke painaa nappulaa."
            ], check=True)
        
    def quit(self):
        pygame.quit()
        sys.exit()
    
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


    
    def makeDeathHeatmapSurface(
        self,
        tilesize=8,
        blur_sigma=1.5,
        colormap=None,
    ):
        kg = self.killgrid.astype(np.float32)

        # --- 1. smooth heatmap ---
        if blur_sigma > 0:
            r = int(3 * blur_sigma)
            x = np.arange(-r, r + 1)
            g = np.exp(-(x**2) / (2 * blur_sigma**2))
            g /= g.sum()

            kg = np.apply_along_axis(lambda m: np.convolve(m, g, mode="same"), 0, kg)
            kg = np.apply_along_axis(lambda m: np.convolve(m, g, mode="same"), 1, kg)

        # normalize
        maxv = kg.max()
        if maxv > 0:
            kg /= maxv

        # --- 2. wall mask ---
        wall_mask = self.map.grid == CellType.WALL.value

        # --- 3. RGB mapping ---
        if colormap is None:
            r = np.clip(kg * 3, 0, 1)
            g = np.clip(kg * 3 - 1, 0, 1)
            b = np.clip(kg * 3 - 2, 0, 1)
            rgb = np.stack((r, g, b), axis=-1)
        else:
            rgb = colormap(kg)[:, :, :3]

        rgb = (55 + rgb * 200).astype(np.uint8)

        # --- 4. Alpha channel ---
        alpha = np.ones((kg.shape[0], kg.shape[1]), dtype=np.uint8) * 255
        alpha[wall_mask] = 0

        # Walls color irrelevant now, but keep clean
        rgb[wall_mask] = 0

        # --- 5. Create surface with per-pixel alpha ---
        surf = pygame.Surface(
            (rgb.shape[1], rgb.shape[0]),
            flags=pygame.SRCALPHA,
        )

        pygame.surfarray.pixels3d(surf)[:, :, :] = rgb.swapaxes(0, 1)
        pygame.surfarray.pixels_alpha(surf)[:, :] = alpha.swapaxes(0, 1)

        # --- 6. Scale ---
        if tilesize != 1:
            surf = pygame.transform.scale(
                surf,
                (surf.get_width() * tilesize, surf.get_height() * tilesize),
            )

        return surf



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


    def convertPos(self, pos, heightDiff = 1.0):
        return (pos - self.cameraPosDelta - self.res/2) * self.RENDER_SCALE * heightDiff + self.res/2
    

    def inverseConvertPos(self, screenPos, heightDiff=1.0):
        return (
            (screenPos - self.res / 2)
            / (self.RENDER_SCALE * heightDiff)
            + self.cameraPosDelta
            + self.res / 2
        )


    def switchHill(self):
        rooms = [x for x in self.map.rooms if x not in self.teamSpawnRooms and x is not self.currHill]
        self.currHill = random.choice(rooms)
        print("Hill moved")
        self.hillSwitchTime = 45
        self.currHill.turfWarTeam = None

    def genLevel(self):
        if self.GAMEMODE == "1v1":
            self.map = ArenaGenerator(self, 50, 40)
            self.map.generate_arena(room_count=self.teams+2, min_room_size=8, max_room_size=20, corridor_width=4)

        else:
            self.map = ArenaGenerator(self, 120, 80)
            self.map.generate_arena(room_count=27, min_room_size=8, max_room_size=14, corridor_width=4)

        self.arena = ArenaWithPathfinding(self, self.map)

        self.shitGrid = np.zeros(self.map.grid.shape, dtype=np.uint8)

        self.FLOORMATRIX = (self.map.grid == 1)

        self.shitDict = {}

        #connectivity = self.arena.validate_arena_connectivity()
        #print(f"Arena Connectivity: {connectivity}")
        print(self.map.grid.shape)

        print("Rooms", len(self.map.rooms))
        self.loadInfo.text = "Finding spawn points"
        if self.GAMEMODE == "DETONATION":
            self.teamSpawnRooms = self.arena.find_spawn_rooms(2)
        else:
            self.teamSpawnRooms = self.arena.find_spawn_rooms(self.teams)
        if not self.teamSpawnRooms:
            self.teamSpawnRooms = []
            for x in range(self.teams):
                self.teamSpawnRooms.append(self.map.rooms[x]%len(self.map.rooms))
                print(f"Spawn room for team {x} not found, using random room instead.")
        self.spawn_points = []
        for team, x in enumerate(self.teamSpawnRooms):
            self.spawn_points.append(x.randomCell())
            x.turfWarTeam = team

            for y in x.connections:
                y.turfWarTeam = team

            #self.allTeams[team].spawnBase()

        print(f"Spawn points: {self.spawn_points}")

        print("Spawn Rooms")
        if self.GAMEMODE != "FINAL SHOWDOWN":
            self.commonRoom = find_farthest_room(self.map.rooms, self.teamSpawnRooms, mode="min")
        else:
            self.commonRoom = max(self.map.rooms, key=lambda room: room.area)

            for dx in range(self.commonRoom.width):
                for dy in range(self.commonRoom.height):
                    self.map.grid[self.commonRoom.y + dy, self.commonRoom.x + dx] = CellType.FLOOR.value

        self.loadInfo.text = "Making walls"
        self.corners, midpoints = self.findCorners(self.map.grid)
        walls = self.findWalls(self.corners, midpoints)
        self.walls = []
        for p1, p2 in walls:
            self.walls.append([v2(p1)*self.tileSize, v2(p2)*self.tileSize])
        
        

        self.map.get_spawn_points()
        self.loadInfo.text = "Rendering"

        

        

        #for p1, p2 in self.walls:
        #    pygame.draw.line(self.MAP, [255,255,255], p1, p2, 3)

        
        
        self.MAP = self.map.to_pygame_surface_textured2(cell_size=int(self.tileSize * self.RENDER_SCALE)) #

        #mapUntextured = self.map.to_pygame_surface(cell_size=self.tileSize) #
        #pygame.image.save(mapUntextured, "untexturedLevel.png")

        self.MINIMAP = self.map.to_pygame_surface(cell_size=self.MINIMAPCELLSIZE)

        self.killgrid = np.zeros(self.map.grid.shape, dtype=np.uint32)

        
        self.SITES = []


        if self.GAMEMODE == "DETONATION":
            self.loadInfo.text = "Handling detonation"
            self.originalGrid = self.map.grid.copy()

            #self.compute_spawnroom_distances()
            print("Making sites")
            self.makeDetonationSites()
            print(self.SITES)

            self.getSites()

            for x in self.SITES:
                c = x.room.randomCell()
                Turret(self, c, self.allTeams[0])


            #for site in self.SITES:
            #    for x,y in site.visibilityCT:
            #        pygame.draw.rect(self.MINIMAP, [15, 26, 51], (x*self.MINIMAPCELLSIZE, y*self.tileSize, 
            #                                                                          self.MINIMAPCELLSIZE, self.MINIMAPCELLSIZE))
            
            #for r in self.SITES:
            #    pygame.draw.rect(self.MAP, [200,200,200], (r.x*self.tileSize, r.y*self.tileSize, 
            #                                                                          r.width*self.tileSize, r.height*self.tileSize))
            
        #self.MAP = MSurf(self, self.MAP)
        

        for team, r in enumerate(self.teamSpawnRooms):
            print("Drawing", team, "spawn room")

            if self.GAMEMODE == "DETONATION":
                if team == 0:
                    team = self.teams - 1
                else:
                    team = 0

            pygame.draw.rect(self.MAP, self.getTeamColor(team, 0.2), (r.x*self.tileSize*self.RENDER_SCALE, r.y*self.tileSize*self.RENDER_SCALE, 
                                                                                      r.width*self.tileSize*self.RENDER_SCALE, r.height*self.tileSize*self.RENDER_SCALE))
            
            pygame.draw.rect(self.MINIMAP, self.getTeamColor(team, 0.2), (r.x*self.MINIMAPCELLSIZE, r.y*self.MINIMAPCELLSIZE, 
                                                                                      r.width*self.MINIMAPCELLSIZE, r.height*self.MINIMAPCELLSIZE))
            

        self.MINIMAPTEMP = self.MINIMAP.copy()
        #entrance = self.map.get_entrance_position()
        routeBetweenSpawns = self.arena.pathfinder.find_path(self.spawn_points[0], self.spawn_points[1])
        midPoint = routeBetweenSpawns[int(len(routeBetweenSpawns)/2)]
        #if entrance:
        if self.GAMEMODE == "ODDBALL":
            self.skull = Skull(self, midPoint)
            print("SKULL CREATED!")
        elif self.GAMEMODE == "DETONATION":
            self.skull = Bomb(self, self.allTeams[-1].getDetonationSpawnRoom().randomCell())
        self.loadInfo.text = "Map done"
        
        self.mapCreated = True

    
    @staticmethod
    def bfs_dists(start_room):
        dist = {start_room: 0}
        q = deque([start_room])

        while q:
            r = q.popleft()
            for nxt in r.connections:
                if nxt not in dist:
                    dist[nxt] = dist[r] + 1
                    q.append(nxt)
        return dist
    
    def bust(self, pawn, timeBetween):

        #if self.VACPAWN:
        #    return

        self.VACPAWN = pawn
        self.timeBetween = timeBetween

        t = threading.Thread(target=self.bustThread, args=(pawn,))
        t.daemon = True
        t.start()
        

    def bustThread(self, pawn):
        dt = 0.01

        # ramp down: 1 -> 0 in 1s
        t = 0.0
        while t < 1.0:
            self.THREAD_SLOWMO = max(0.0, 1.0 - t)
            time.sleep(dt)
            t += dt

        self.THREAD_SLOWMO = 0.0

        self.DISPLAY_VAC = True
        # idle 3s
        time.sleep(10.0)
        self.DISPLAY_VAC = False

        # ramp up: 0 -> 1 in 1s
        t = 0.0
        while t < 1.0:
            self.THREAD_SLOWMO = min(1.0, t)
            time.sleep(dt)
            t += dt

        self.THREAD_SLOWMO = 1.0
        self.VACPAWN = None
    

    def getSites(self):

        self.map.grid = self.originalGrid.copy()

        self.refreshSites()
        self.allTeams[-1].getViableSites()
        self.allTeams[-1].planTimer = 0
        #self.MAP = self.map.to_pygame_surface_textured(cell_size=self.tileSize, floor_texture=self.concretes) #
        #self.MINIMAP = self.map.to_pygame_surface(cell_size=self.MINIMAPCELLSIZE)
        #for site in self.SITES:
        #    for x,y in site.attackPositionsT:
        #        pygame.draw.rect(self.MINIMAP, [255,0,0], [x*self.MINIMAPCELLSIZE,y*self.MINIMAPCELLSIZE, self.MINIMAPCELLSIZE, self.MINIMAPCELLSIZE])


    def pickDetonationSites(self):
        # identify CT and T spawn
        ct_spawn = self.teamSpawnRooms[1]
        t_spawn  = self.teamSpawnRooms[0]

        dist_ct = self.bfs_dists(ct_spawn)
        dist_t  = self.bfs_dists(t_spawn)

        candidates = []

        for room in self.map.rooms:
            dct = dist_ct.get(room, 9999)
            dt  = dist_t.get(room, 9999)

            if dct >= 2 and dt >= 3:
                # combine distance metrics for fairness
                score = dct + dt
                candidates.append((score, room))

        # sort by "best site" score (largest distances)
        candidates.sort(reverse=True, key=lambda x: x[0])

        # pick top 3
        sites = [room for _, room in candidates[:3]]
        return sites
    
    def makeDetonationSites(self):
        self.SITES.clear()
        sites = self.arena.find_detonation_sites(self.teamSpawnRooms[1], self.teamSpawnRooms[0])
        for x in sites:
            Site(self,x)
            


    def refreshSites(self):
        for x in self.SITES:
            x.processSite()
        for x in self.SITES:
            x.makePositions()



    def cell2Pos(self, cell):
        return v2(cell) * self.tileSize + [self.tileSize/2, self.tileSize/2]
    
    def resetDemo(self):
        self.RECORDDEMO = False
        self.DEMO = {"ticks": {}}
                     
        self.demoTick = 0
        self.demoTickIncrement = 0
        self.demoObjects = []
        self.DEMOFPS = 60
        
    

    def initiationWrapper(self):
        self.loadInfo = infoBar(self, "Starting game")
        try:
            self.initiateGame()
            self.loadInfo.text = "Done!"
            self.loadInfo.killed = True
        except:
            self.loadInfo.text = "ERRORED!!!"
            raise RuntimeError
        

    def load_ct_spawn(self, path="training.cfg"):
        try:
            with open(path, "r") as f:
                return float(f.read().strip())
        except:
            return 15.0
        
    def save_ct_spawn(self, value, path="training.cfg"):
        with open(path, "w") as f:
            f.write(f"{value:.3f}")

        print("NEW VALUE!", value)



    def initiateGame(self):

        self.now = time.time()
        
        if self.DOREALGAMEMODES:
            if self.round < len(self.gameModeLineUp):
                self.GAMEMODE = self.gameModeLineUp[self.round % len(self.gameModeLineUp)]
            else:
                self.GAMEMODE = "SUDDEN DEATH"

        else:

            self.GAMEMODE = self.gameModeLineUp[self.round % len(self.gameModeLineUp)]
        self.gamemode_display.set_gamemode(self.GAMEMODE)

        for x in self.getActualPawns():
            x.sendGamemodeInfo()

        
        if self.TRAINCTSPAWNTIME:
            if self.round == self.TRAIN_TIME:
                self.round = 0
                wins = [0,0]
                for x in self.allTeams:
                    if x.isCT():
                        wins[0] += x.wins
                    else:
                        wins[1] += x.wins
                    x.wins = 0

                diff = (wins[0] - wins[1])/self.TRAIN_TIME

                spawnTime = self.load_ct_spawn()
                self.save_ct_spawn(spawnTime + diff)

        for x in self.allTeams:
            x.allied.clear()


        play_sounds_sequential("audio/örkki", ["kierros", str(self.round+1), self.GAMEMODE, "fight"])
        

        if self.GAMEMODE == "1v1":

            # Pick best and the second best pawn
            self.duelPawns = sorted(self.pawnHelpList.copy(), key=lambda x: x.stats["kills"], reverse=True)[:2]
            #if self.duelPawns[0].team == self.duelPawns[1].team:
                # If they are on the same team, pick the next best pawn
                #self.duelPawns[1].team = (1 + self.duelPawns[0].team) % self.teams

            #self.duelPawns = [max(self.pawnHelpList, key=lambda x: x.stats["kills"]), self.pawnHelpList[1]]

        elif self.GAMEMODE == "DETONATION":
            for x in self.allTeams:
                x.detonationTeam = not bool(x.i % 2)
            
                for y in self.allTeams:
                    if y == x:
                        continue
                    
                    if not bool(y.i%2) == x.detonationTeam:
                        x.allied.append(y)
                        print(x.i, "allied with", y.i)

                x.defaultPlan()

        seed = random.randrange(2**32 - 1)
        if self.SET_SEED == None:
            self.LEVELSEED = seed
        else:
            self.LEVELSEED = self.SET_SEED

        
        if self.GAMEMODE == "DETONATION":
            self.LEVELSEED = 696969

        state = random.getstate()
        np_state = np.random.get_state()

        random.seed(self.LEVELSEED)
        np.random.seed(self.LEVELSEED)

        self.loadInfo.text = f"Generating level. Seed: {self.LEVELSEED}"

        self.genLevel()

        random.setstate(state)
        np.random.set_state(np_state)

        self.resetLevelUpScreen()
    
        
            

        self.endGameI = 15
        self.skullTimes = []
        for x in range(self.teams):
            self.skullTimes.append(0)

        
        self.VICTORY = False
        if self.GAMEMODE == "1v1":
            self.roundTime = 60
        #elif self.GAMEMODE == "DETONATION":
        #    self.roundTime = 180
        else:
            self.roundTime = self.MAXROUNDLENGTH

        if self.GAMEMODE == "KING OF THE HILL":
            self.switchHill()

        

        self.cameraLinger = 0
        for i in range(1):
            for pawn in self.pawnHelpList:
                pawn.reset()
                pawn.kills = 0
                pawn.teamKills = 0
                pawn.suicides = 0
                pawn.deaths = 0

        self.nextMusic = 1
        self.midMusicIndex = 0

        self.AUDIOVOLUME = 0.3
        
        if self.GAMEMODE == "FINAL SHOWDOWN":
            self.loadInfo.text = "Making Bablo"
            self.BLOCKMUSIC = True
            

            babloPath = "boss/bablo2.png"
            with open(babloPath, "rb") as f:
                imageRaw = f.read()

            Pawn(self, "BABLO", imageRaw, None, boss=True)
            self.ENTITIES.append(self.BABLO)
            self.alwaysHostileTeam.add(self.BABLO)

            for x in self.music:
                x.stop()

            self.music = self.babloMusic
            self.loadedMusic = "Bablo >:)"
            self.nextMusic = 0
            for x in self.music:
                x.stop()

            self.handleMusic()
            self.nextMusic = 1
            self.BABLO.respawnI = 1
            P = self.commonRoom.center()
            self.BABLO.pos = v2(P) * self.tileSize + [self.tileSize/2, self.tileSize/2] 
            self.AUDIOVOLUME = 0.2
            self.crackIndex = 0
            self.BLOCKMUSIC = False

        

        self.resetDemo()

        for x in self.allTeams:
            x.refreshColor()
            x.kothTime = 0

        if self.giveWeapons:
            self.giveAllWeapons()

        if self.STRESSTEST and False:
            for x in self.getActualPawns():
                if x.BOSS: continue
                x.reLevelPawn(10)
        
        self.TRUCE = self.GAMEMODE == "FINAL SHOWDOWN"

        if not self.AUTOPLAY:
            time.sleep(max(0, 5 - (time.time() - self.now)))

        self.resetRoundInfo()

        

        for x in self.CAMERAS:
            if x.cameraIndex >= len(self.teamSpawnRooms): continue

            x.pos = v2(self.teamSpawnRooms[x.cameraIndex].center()) * self.tileSize - self.res/2
            x.cameraPos = x.pos.copy() 

        self.transition(lambda: self.exitLoadingScreen())

    def compute_spawnroom_distances(self):
        rooms = self.teamSpawnRooms
        n = len(rooms)

        # distance matrix (Euclidean grid distance)
        D = np.zeros((n, n), dtype=np.float32)

        centers = [r.center() for r in rooms]

        for i in range(n):
            x1, y1 = centers[i]
            for j in range(n):
                if i == j:
                    continue
                x2, y2 = centers[j]
                dx = x2 - x1
                dy = y2 - y1
                D[i, j] = (dx*dx + dy*dy) ** 0.5

        self.spawn_dist_matrix = D
        print(D)


    def exitLoadingScreen(self):
        self.GAMESTATE = "ODDBALL"

    def exitIntro(self):
        self.GAMESTATE = "settings"

    def doBabloCracks(self):
        if not (self.GAMEMODE == "FINAL SHOWDOWN" and self.GAMESTATE == "ODDBALL" and self.currMusic == 0):
            return
        timeIntoMusic = time.time() - self.musicStart

        if self.crackIndex >= len(self.crackAppearTimes):
            return

        if self.crackAppearTimes[self.crackIndex] < timeIntoMusic:
            P = self.commonRoom.center()
            POS = v2(P) * self.tileSize + [random.uniform(-1 * self.tileSize, 1*self.tileSize), random.uniform(-1 * self.tileSize, 1*self.tileSize)]
            BLITPOS = POS * self.RENDER_SCALE
            for i in range(random.randint(1,6)):
                I = self.crackIndex - i
                if I >= 0:
                    C = self.cracks[I]
                    self.MAP.blit(C, BLITPOS - v2(C.get_size())/2)
            self.crackIndex += 1
            #if self.crackIndex == len(self.crackAppearTimes):
            #    self.notify("NEW OBJECTIVE")

            self.particle_system.create_explosion(POS.x, POS.y, count = 100, start_size = random.randint(50,100), speed = 15)

            for i in self.pawnHelpList:
                i.say("Ö", 1)
            #random.choice(self.pawnHelpList).say(babloBreak(), 0.5)

            self.CAMERAS[0].cameraLinger = 2
            self.CAMERAS[0].cameraLock = None
            self.CAMERAS[0].cameraPos = POS.copy() - self.res/2
            self.CAMERAS[0].vibrate(25)


    def resetRoundInfo(self):
        self.roundInfo = {
            "deaths": 0,
            "bulletsFired": 0,
            "explosions": 0,
            "timesTalked": 0,
            "flashes": 0,
            "levelUps": 0,
            "xpGained": 0,
        }
        self.victoryProgress = [[0] for _ in range(len(self.allTeams))]
        self.monitorProgress = 3
        self.endroundInfo = self.roundInfo.copy()
        
        
    def onScreen(self, pos):
        if self.PEACEFUL: return True

        #pos = self.convertPos(pos)

        for camera in self.CAMERAS:

            r = pygame.Rect(camera.pos, self.res)
            r.inflate_ip(self.res.x/self.RENDER_SCALE - self.res.x, self.res.y/self.RENDER_SCALE - self.res.y)
        
            onDualScreen = False

            if camera.DUALVIEWACTIVE:

                r2 = pygame.Rect(camera.posToTargetTo2, self.res)
                r2.inflate_ip(self.res.x/self.RENDER_SCALE - self.res.x, self.res.y/self.RENDER_SCALE - self.res.y)

                onDualScreen = r2.collidepoint(pos)
            #r2.inflate_ip(self.app.res)

            if not r.collidepoint(pos) and not onDualScreen:
                continue
            return True
        return False
        


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
        # clear teams first
        #for t in self.allTeams:
        #    t.clear()

        #self.alwaysHostileTeam.clear()

        players = []
        npcs = []

        for team in self.allTeams:
            team.pawns.clear()

        for pawn in self.getActualPawns():
            if pawn.BOSS:
                self.alwaysHostileTeam.add(pawn)
            elif pawn.NPC:
                npcs.append(pawn)
            else:
                players.append(pawn)

            pawn.team = None

        # --- 1. assign players to player teams ---
        for i, pawn in enumerate(players):
            self.allTeams[i % self.playerTeams].add(pawn)

        # --- 2. fill player teams with NPCs ---
        npc_i = 0
        for t in range(self.playerTeams):
            team = self.allTeams[t]
            while len(team.pawns) < self.fillTeamsTo and npc_i < len(npcs):
                team.add(npcs[npc_i])
                npc_i += 1

        # --- 3. remaining NPCs go to npc teams ---
        if self.npcTeams:
            npc_team_i = 0
            for i in range(npc_i, len(npcs)):
                self.allTeams[self.playerTeams + npc_team_i % self.npcTeams].add(npcs[i])
                npc_team_i += 1
        else:
            npc_team_i = 0
            for i in range(npc_i, len(npcs)):
                self.allTeams[npc_team_i % self.playerTeams].add(npcs[i])
                npc_team_i += 1



    def add_player(self, name, image, client, team = -1):
        self.playerFilesToGen.append((name, image, client, team))

    def assignTeam(self, pawn):
        print("Assigning team for", pawn.name)
        length = len(self.allTeams)
        if not pawn.NPC:
            length -= self.npcTeams

        for t in range(length):
            team = self.allTeams[t]
            if len(team.pawns) < self.fillTeamsTo:
                team.add(pawn)
                return
        print("No team found???")

    def threadedGeneration(self, name, image, client, team = -1, boss = False):
        self.pawnGenI += 1
                
        pawn = Pawn(self, name, image, client, team = team, boss = boss)
        #if client:
        
        #else:
        #    pawn.team = self.playerTeams + self.pawnHelpList.index(pawn)%(self.teams - self.playerTeams)
        #pawn.teamColor = self.getTeamColor(pawn.team.i)
        self.ENTITIES.append(pawn)
        #self.reTeamPawns()

        self.pawnGenI -= 1

    def toggleCam(self):
        self.AUTOCAMERA = not self.AUTOCAMERA

    def getWinningTeam(self):
        teams = self.allTeams
        if not teams:
            return None
        sorted_teams = sorted(teams, key=lambda t: t.wins, reverse=True)
        if len(sorted_teams) == 1:
            self.winningTeam = sorted_teams[0]
            return 
        if sorted_teams[0].wins == sorted_teams[1].wins:
            self.winningTeam = None
            return None  # stalemate
        self.winningTeam = sorted_teams[0]  # clear lead
        self.maxWins = max(self.winningTeam.wins, self.maxWins)

    def killAllPawns(self):
        for x in self.getActualPawns():
            x.die()

    def announceVictory(self: "Game", victoryTeam):
        #print(f"Team {i+1} WON")
        self.victoryTeam = victoryTeam
        self.VICTORY = True 
        self.points = []



        if self.GAMEMODE == "DETONATION":

            if self.victoryTeam == 1:
                register_gun_kill("COUNTERTERRORIST", path="detonationWins.txt")
            elif self.victoryTeam == 0:
                register_gun_kill("TERRORIST", path="detonationWins.txt")
            else:
                register_gun_kill("TIE", path="detonationWins.txt")

            register_gun_kill(f"{len(self.SITES)} LEFT", path="detonationWins.txt")


            for x in self.allTeams:
                if x.detonationTeam == victoryTeam or victoryTeam == -1:
                    x.wins += 1
                else:
                    x.currency += 100
        else:
            self.allTeams[self.victoryTeam].wins += 1
            for x in self.allTeams:
                if x.i == self.victoryTeam:
                    continue
                x.currency += 100


        self.getWinningTeam()
        #print("Winning team", self.winningTeam.i)

        self.nextMusic = -1

        for x in [x for x in self.pawnHelpList if x.isPawn]:
            points, reason_str = x.evaluatePawn()
            self.points.append((x, points, reason_str))

        self.points.sort(key=lambda x: x[1], reverse=True)

        self.MVP = sorted(
            self.getActualPawns(),
            key=lambda x: x.kills / max(1, x.deaths),
            reverse=True
        )[0]
        self.LVP = sorted(
            self.getActualPawns(),
            key=lambda x: x.kills / max(1, x.deaths),
            reverse=False
        )[0]
        self.TEAMKILLER = sorted(
            self.getActualPawns(),
            key=lambda x: x.teamKills,
            reverse=True
        )[0]

        self.HEATMAP = self.makeDeathHeatmapSurface(8, 3).convert_alpha()
        self.HEATMAP = pygame.transform.scale_by(self.HEATMAP, (640*self.RENDER_SCALE)/self.HEATMAP.get_height())
        #self.HEATMAP.set_colorkey((0,0,0))

        if self.GAMEMODE != "DETONATION":
            n_samples = len(self.victoryProgress[0])

            for team in range(len(self.victoryProgress)):
                prog = self.victoryProgress[team]

                for i in range(1, n_samples):
                    alpha = 0.5
                    prog[i] = prog[i-1] * (1 - alpha) + prog[i] * alpha

        self.endroundInfo = self.roundInfo.copy()



    def getActualPawns(self) -> list:
        return [x for x in self.pawnHelpList if x.isPawn]
    
    def logParticleEffect(self, fn, args, kwargs):
        if not self.RECORDDEMO or self.PLAYBACKDEMO:
            return

        tick = self.demoTick
        ticks = self.DEMO.setdefault("ticks", {})

        tick_data = ticks.setdefault(tick, {})
        creates = tick_data.setdefault("create", [])

        creates.append((fn, args, kwargs))

    def logDeletion(self, id):
        if not self.RECORDDEMO or self.PLAYBACKDEMO:
            return

        tick = self.demoTick
        ticks = self.DEMO.setdefault("ticks", {})

        tick_data = ticks.setdefault(tick, {})
        kills = tick_data.setdefault("kill", [])

        kills.append(id)

    def exportDemo(self):
        with open("DEMO.txt", "w") as f:
            f.write(str(self.DEMO))

    def createParticleDemo(self):
        tick_data = self.DEMO.get("ticks", {}).get(self.demoTick)
        if not tick_data:
            return

        for fn, args, kwargs in tick_data.get("create", []):
            #print("Creating:", type(fn))
            fn(*args, **kwargs)

        killIds = tick_data.get("kill", [])
        self.demoObjects = [x for x in self.demoObjects if x.id not in killIds]


    def handleMusic(self):

        if not self.music:
            return
        
        if isinstance(self.music, str):
            return
        try:
            for x in self.music:
                if x.get_num_channels():
                    return False
        except:
            print(self.music)
            return
        self.music[self.currMusic].stop()

        if self.currMusic == -1 and self.loadedMusic == "Bablo >:)":
            self.music = self.loadSound("audio/bar", volume=0.2, asPygame=True)

        nextTrack = self.nextMusic
        if self.nextMusic == 1:
            totalMidTracks = len(self.music) - 2
            nextTrack = 1 + self.midMusicIndex
            self.midMusicIndex = (self.midMusicIndex + 1) % totalMidTracks
            if self.midMusicIndex == 0 and self.loadedMusic == "Bablo >:)" and self.currMusic == 1:
                self.midMusicIndex = 1
                self.babloLyricIndex = 0

        self.music[nextTrack].play()
        self.currMusic = self.nextMusic

        self.musicStart = time.time()
        self.musicLength = self.music[self.nextMusic].get_length()

        

        return True
    
    def handleBabloLyrics(self):
        if not self.babloLyrics:
            return 
        
        current_time = time.time() - self.musicStart + self.musicLength * ((self.midMusicIndex-1)%4)
        lyrics = self.babloLyrics
        n = len(lyrics)
        i = self.babloLyricIndex % n

        t_curr, lyric_curr = lyrics[i]
        t_next = lyrics[(i + 1) % n][0]

        # Handle loop wrap (if timestamps reset after track restart)
        if t_next <= t_curr:
            # estimate total song duration using last timestamp
            song_duration = lyrics[-1][0]
            t_next += song_duration

        # Advance lyric when we pass the next timestamp
        if current_time >= t_next:
            self.babloLyricIndex = (i + 1) % n
            self.babloLyricCurrent = lyrics[self.babloLyricIndex][1]
            

        # Normalized progress between current and next lyric
        span = t_next - t_curr
        norm = (current_time - t_curr) / span
        norm = max(0.0, min(1.0, norm))

        self.babloLyricTime = current_time
        self.babloLyricNorm = norm
        #self.babloLyricCurrent = lyric
        
    
    def debugEnslavement(self):
        r = random.choice(self.teamSpawnRooms)
        t = self.teamSpawnRooms.index(r)
        team = self.allTeams[t]
        for x in team.pawns:
            x.die()
        self.log(f"Killed all pawns of team {t+1}")
        self.switchRoomOwnership(r, random.randint(0, self.teams-1))
    
    def BPM(self):
        if not self.loadedMusic:
            return
        
        tempo = {"HH": 150, "Bablo": 123, "Bablo >:)": 125}[self.loadedMusic]
        #tempo = 150 if self.loadedMusic == "HH" else 123
        musicPlayedFor = time.time() - self.musicStart
        self.beatI = 1-((musicPlayedFor%(60/tempo))/(60/tempo))

    def getTeamColor(self, team, intensity = 1, maxTeams = None):
        if not maxTeams:
            maxTeams = self.teams

        hue = (team * 1/maxTeams) % 1.0  # Cycle hue every ~6 teams
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)

        if hasattr(self, "GAMEMODE") and self.GAMEMODE == "DETONATION":
            if self.allTeams[team].isCT():
                r, g, b = [76/255, 129/255, 255/255]  # CT
            else:
                r, g, b = [255/255, 210/255, 64/255] # T

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

        if self.DISABLEDEBUGTEXT:
            return
        
        t = self.fontSmaller.render(str(text), True, [255,255,255])
        self.screen.blit(t, [self.res[0] - 20 - t.get_size()[0], max(self.res[1] - 700, 0) + self.debugI * 22])
        self.debugI += 1

    def smoothRotationFactor(self, angleVel, gainFactor, diff):
        dir = 1 if diff > 0 else -1
        gainFactor *= min(1, abs(diff) * 3)
        gainFactor = max(0.1, gainFactor)

        # Your original calculation - time needed to decelerate to zero
        if abs(angleVel) < 1e-6:  # Avoid division by zero
            decelarationTicks = 0
        else:
            try:
                decelarationTicks = abs(angleVel / gainFactor)
            except:
                print("VITUN OUTO BUGI")
                print(angleVel, gainFactor)
                decelarationTicks = 0
        # Your original calculation - distance covered while decelerating
        distanceDecelerating = angleVel * decelarationTicks - 0.5 * dir * gainFactor * decelarationTicks**2
        
        acceleratingMod = 1 if distanceDecelerating < diff else -1
        
        return acceleratingMod * gainFactor
    
    def toggleStressTest(self):
        self.STRESSTEST = not self.STRESSTEST
        self.log(f"STRESS: {self.STRESSTEST}")

    
    def getAngleFrom(self, fromPoint, toPoint):
        return math.radians(v2([0,0]).angle_to(v2(toPoint) - v2(fromPoint))) 
    
    def getDistFrom(self, fromPoint, toPoint):
        return math.sqrt((fromPoint[0] - toPoint[0])**2 + (fromPoint[1] - toPoint[1])**2)
    
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
                self.CAMERA.cameraLock = None
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
                    pawn.ULT_TIME = 30
                    self.clicks[1].play()

            self.screen.blit(t, r.topleft)
            yPos += 40

    def getTurretHead(self, rgb):
        key = tuple(rgb)
        if key in self.turretHeadRGB:
            return self.turretHeadRGB[key]

        base = pygame.image.load("texture/turretColorable.png").convert_alpha()
        arr = pygame.surfarray.pixels3d(base).astype(np.float32) / 255.0
        alpha = pygame.surfarray.pixels_alpha(base)

        r, g, b = [c / 255.0 for c in rgb]
        h_target, _, _ = colorsys.rgb_to_hls(r, g, b)
        s_target = 0.4

        r0, g0, b0 = arr[..., 0], arr[..., 1], arr[..., 2]
        l = (np.maximum.reduce([r0, g0, b0]) +
            np.minimum.reduce([r0, g0, b0])) * 0.5

        hls_to_rgb = np.vectorize(colorsys.hls_to_rgb)
        rr, gg, bb = hls_to_rgb(h_target, l, s_target)

        out = np.stack([rr, gg, bb], axis=2)
        out = np.clip(out * 255.0, 0, 255).astype(np.uint8)

        surf = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        pygame.surfarray.blit_array(surf, out)
        pygame.surfarray.pixels_alpha(surf)[:] = alpha

        surf = pygame.transform.scale_by(surf, self.RENDER_SCALE)

        self.turretHeadRGB[key] = surf
        return surf


    def setManualPawn(self, name):

        if not name:
            self.MANUALPAWN = None

        for x in self.pawnHelpList:
            if x.name == name:
                self.MANUALPAWN = x
                return
        

    def handleCameraLock(self):


        if not self.CAMERA.cameraLock and self.CAMERA.cameraLinger <= 0:
            #if self.objectiveCarriedBy:
            #    self.CAMERA.cameraLock = self.objectiveCarriedBy

            if self.BABLO and not self.BABLO.killed:
                self.CAMERA.cameraLock = self.BABLO

            elif self.pawnHelpList:
                
                if self.filmOnly:
                    FILMLIST = [x for x in self.pawnHelpList.copy() if x in self.filmOnly and x.isPawn]
                    e = sorted(FILMLIST, key=lambda p: p.onCameraTime)

                else:
                    FILMLIST = [x for x in self.pawnHelpList.copy() if x.team.i == self.CAMERA.cameraIndex]
                    e = sorted(FILMLIST, key=lambda p: p.onCameraTime)

                    if self.GAMEMODE in "DETONATION":
                        site = self.allTeams[0].getCurrentSite()
                        if site:
                            center = site.room.center()
                            e = sorted(FILMLIST, key=lambda p: self.getDistFrom(p.getOwnCell(), center))
                    #    if self.skull.plantedAt:
                    #        l = [x for x in FILMLIST.copy() if self.skull.plantedAt.room.contains(*x.getOwnCell())]
                    #        e = sorted(l, key=lambda p: p.onCameraTime)
                    #    else:
                    #        l = [x for x in FILMLIST.copy() if not x.team.detonationTeam]
                    #        site = self.allTeams[0].getCurrentSite()
                    #        if site:
                    #            sitePos = self.allTeams[0].getCurrentSite().room.center()
                    #            e = sorted(l, key=lambda p: self.getDistFrom(p.getOwnCell(), sitePos))
                    #        else:
                    #            e = sorted(FILMLIST, key=lambda p: p.onCameraTime)
#
                    #    #e = sorted(l, key=lambda p: p.onCameraTime)
                    #elif self.GAMEMODE == "ODDBALL":
                    #    if self.objectiveCarriedBy:
                    #        l = [x for x in FILMLIST.copy() if x.team.i == self.objectiveCarriedBy.team.i]
                    #    else:
                    #        l = FILMLIST
                    #    e = sorted(l, key=lambda p: p.onCameraTime)
                    #else:
                    #    l = FILMLIST
                    #    e = sorted(l, key=lambda p: p.onCameraTime)

                noNPC = [x for x in e if not x.NPC and not x.killed and x.isPawn]
                if noNPC:
                    e = noNPC

                for x in e:
                    if not x.killed and x.isPawn:
                        self.CAMERA.cameraLock = x
                        if not x.target:
                            x.say(onCameraLock(x.name))
                        break


        elif self.CAMERA.cameraLinger <= 0:
            if self.CAMERA.cameraLock.killed:
                self.CAMERA.cameraLock = None
                self.CAMERA.cameraLinger = 1
                
            else:

                if not self.CAMERA.cameraLock.target and not self.CAMERA.cameraLock.BOSS and self.CAMERA.cameraLock.currentlyAliveNade:
                    self.CAMERA.cameraPos = self.CAMERA.cameraLock.currentlyAliveNade.pos - [0, self.CAMERA.cameraLock.currentlyAliveNade.verticalPos] - self.res/2
                    #self.cameraLinger = 0.4

                else:
                    self.CAMERA.cameraPos = self.CAMERA.cameraLock.pos - self.res/2
                    self.CAMERA.cameraLock.onCameraTime += self.deltaTime


                if self.CAMERA.cameraLock.target:
                    self.CAMERA.cameraIdleTime = 0
                    if not self.pendingLevelUp and not self.VICTORY:
                        self.CREATEDUAL = True
                        self.CAMERA.cameraLockTarget = self.CAMERA.cameraLock.target.pos.copy() * 0.1 + self.CAMERA.cameraLockTarget * 0.9
                        self.CAMERA.cameraLockOrigin = self.CAMERA.cameraLock.pos.copy()
                else:
                    self.CAMERA.cameraIdleTime += self.deltaTimeR

                if self.CAMERA.cameraIdleTime > 5:
                    self.CAMERA.cameraLock = None
                    self.CAMERA.cameraLinger = 0
                    self.CAMERA.cameraIdleTime = 3
                    
        
        else:
            self.CAMERA.cameraLinger -= self.deltaTime
            self.CAMERA.cameraIdleTime = 0



        if self.VICTORY:
            I = max(self.endGameI-8, 0)
            self.SLOWMO = 1 - 0.25*(2-I)
            
            #self.CAMERA.cameraLock = max(
            #    (x for x in self.getActualPawns() if (x.team.i == self.victoryTeam and not x.killed)),
            #    key=lambda x: x.kills,
            #    default=None
            #)

        
        elif self.pendingLevelUp:
            #self.CAMERA.cameraLockOrigin = self.pendingLevelUp.pos.copy() - self.res/2

            I = self.levelUpTimeFreeze()

            self.SLOWMO = 1 - 0.5*(1-I)
            #self.CAMERA.cameraLock = self.pendingLevelUp

    def isCameraLocked(self, pawn: "Pawn"):
        for x in self.CAMERAS:
            if x.cameraLock == pawn:
                return x

    def handleCameraManual(self):
        if not self.MANUALPAWN.killed:
            self.cameraPos = self.MANUALPAWN.pos  - self.res/2
            self.cameraPos += (self.mouse_pos - self.res/2) * 0.35

    def handleCameraSplit(self):
        
        if self.CREATEDUAL and not self.STRESSTEST:

            self.CAMERA.splitI += self.deltaTimeR * 3
            self.CAMERA.splitI = min(1, self.CAMERA.splitI)
        else:
            self.CAMERA.splitI -= self.deltaTimeR * 3
            self.CAMERA.splitI = max(0, self.CAMERA.splitI)

        if self.CAMERA.splitI > 0:

            if self.CAMERA.cameraLock and not self.CAMERA.cameraLock.killed:
                self.CAMERA.cameraLockOrigin = self.CAMERA.cameraLock.pos.copy()

            self.line1, self.line2, self.line3, self.line4 = self.CAMERA.update_split_positions(self.res)

    def splitScreen(self, screen, DS1, DS2):
        #self.screen.fill((0,0,0))
        screen.blit(DS1, (0, 0))

        self.mask.fill((0, 0, 0, 0))
        pygame.draw.polygon(self.mask, [255, 255, 255, 255], (self.line1, self.line2, self.line4, self.line3))

        # Masking step: use mask to zero out non-polygon areas in screenCopy2
        DS2.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # True alpha blending
        screen.blit(DS2, (0, 0))  # This now honors alpha channel

        pygame.draw.line(screen, [255, 255, 255], self.line1, self.line2, 3)

    def bombPlanted(self):
        return self.GAMEMODE == "DETONATION" and self.skull and self.skull.planted
    
    def skip(self):
        self.shopTimer = 0
        self.roundTime = 0
        self.endGameI = 0
    
    def drawAwards(self, endGameI):
        awards = [
            ("MVP", self.MVP),
            ("LVP", self.LVP),
            ("TEAM KILLER", self.TEAMKILLER),
        ]

        w, h = self.res
        n = len(awards)
        spacing = w // (n + 1)
        cy = h // 2 + endGameI**2 * 900 + 100

        for i, (label, pawn) in enumerate(awards):
            cx = spacing * (i + 1)

            img = pawn.levelUpImage
            rect = img.get_rect(center=(cx, cy))
            self.screen.blit(img, rect)
            color = pawn.team.getColor()
            title = self.fontLarge.render(f"{label}: {pawn.name}", True, color)
            trect = title.get_rect(center=(cx, rect.top - 45))
            self.screen.blit(title, trect)

            if label in ["MVP", "LVP"]:
                line = f"K/D: {pawn.kills/max(1, pawn.deaths):.1f}"
            else:
                line = f"Team kills: {pawn.teamKills}"

            txt = self.font.render(line, True, color)
            lrect = txt.get_rect(center=(cx, rect.bottom + 35))
            self.screen.blit(txt, lrect)


    async def killClient(self, client):
        await client.ws.close(code=1000, reason="Server shutdown")


    def kick(self, name: str):
        pawn = self.getPawn(name)
        if not pawn: return
        if pawn in self.pawnHelpList:
            self.pawnHelpList.remove(pawn)
        if pawn in self.ENTITIES:
            self.ENTITIES.remove(pawn)
        if pawn.team and pawn in pawn.team.pawns:
            pawn.team.pawns.remove(pawn)
        if pawn.client:

            client = self.clients[pawn.client]
            asyncio.run_coroutine_threadsafe(self.killClient(client), self.loop)

            del self.clients[pawn.client]
            del self.clientPawns[pawn.client]
        self.log(f"Kicked player {name}")

    def tickEndGame(self):
        self.endGameI -= self.deltaTimeR
        I = max(self.endGameI-13, 0)*0.5

        if self.currMusic == -1:
            self.nextMusic = 0
        else:
            self.nextMusic = -1
        
        d = self.darken[round((1-I)*19)]
        self.screen.blit(d, (0,0))
        t = -1 if not self.victoryTeam else 0
        if self.GAMEMODE == "DETONATION":
            if self.victoryTeam == 1:
                s = "COUNTER TERRORISTS WON"
                c = self.allTeams[t].getColor()
            elif self.victoryTeam == 0:
                s = "TERRORISTS WON"
                c = self.allTeams[t].getColor()
            else:
                s = "TIE"
                c = [255,255,255]
            
            
            text = self.notificationFont.render(f"{s}", True,c)

        else:
            text = self.notificationFont.render(f"{self.allTeams[self.victoryTeam].getName()} WON", True, self.allTeams[self.victoryTeam].getColor())
        text.set_alpha(int(255 * (1-I)))
        self.screen.blit(text, v2([self.res.x/2, 100]) - v2(text.get_size())/2)

        if self.endGameI > 8:
            I = max(I, 9 - self.endGameI)
            self.drawAwards(I)
        else:
            I = max(self.endGameI-7, 0)
            self.screen.blit(self.HEATMAP, self.res/2 - v2(self.HEATMAP.get_size())/2 + [0, I**2 * 900])

            # Base Y aligned with heatmap top
            base_y = self.res.y / 2 - self.HEATMAP.get_height() / 2

            # Slide-in from left (mirrors heatmap easing)
            x_offset = min(10, 10 - I**2 * 400)

            line_h = self.font.get_height() + 6

            ROUND_INFO_LABELS = {
                "deaths":        "Deaths",
                "bulletsFired":  "Bullets Fired",
                "explosions":    "Explosions",
                "timesTalked":   "Times Talked",
                "flashes":       "Times flashed",
                "levelUps":      "Level Ups",
                "xpGained":      "XP Gained",
            }

            for i, (k, v) in enumerate(self.endroundInfo.items()):
                text = f"{ROUND_INFO_LABELS[k]}: {v:.0f}"
                surf = self.font.render(text, True, (255, 255, 255))

                pos = v2(
                    x_offset,
                    base_y + i * line_h
                )

                self.screen.blit(surf, pos)



            if self.GAMEMODE != "DETONATION":
                i2 = 1 - max(min(self.endGameI-2.5, 1), 0)

                
                xWidth = self.HEATMAP.get_width()

                n_samples = max(len(self.victoryProgress[0]), 1)
                draw_samples = int(n_samples * i2)

                perStep = xWidth / n_samples

                height = 140
                maxY = max(max(row) for row in self.victoryProgress if row)
                maxY = max(maxY, 1)
                position = v2(self.originalRes.x/2 - self.HEATMAP.get_width()/2, self.originalRes.y - height - 20)

                for team in range(len(self.victoryProgress)):
                    prog = self.victoryProgress[team]

                    for i in range(1, draw_samples):
                        v0 = prog[i - 1]
                        v1 = prog[i]

                        x0 = (i - 1) * perStep
                        x1 = i * perStep

                        y0 = height * (1 - v0 / maxY)
                        y1 = height * (1 - v1 / maxY)

                        pygame.draw.line(
                            self.screen,
                            self.getTeamColor(team),
                            position + [x0, y0],
                            position + [x1, y1],
                            2
                        )
                    
                    

    def handleNPCWeaponPurchase(self):
        NPCS = [x for x in self.pawnHelpList if x.NPC and x.isPawn]
        maxPrice = (self.round + 1)*75
        for pawn in NPCS:
            w = random.choice(self.weapons)
            if pawn.weapon.price[0] < w.price[0] <= maxPrice:
                w.give(pawn)

            if pawn.gType == None:
                gtype = self.randomWeighted(0.25, 0.25, 0.25, 3/(self.round+1))
                if gtype == 3:
                    continue
                pawn.gType = gtype


    def buildAwards(self):
        pawns = [x for x in self.getActualPawns() if not x.NPC and not x.BOSS]
        if not pawns:
            pawns = [x for x in self.getActualPawns()]

        awards = []

        def add_stat_award(title, pawn, stat):
            val = pawn.stats.get(stat, 0)

            statToDesc = {
                "kills": "Kills",
                "deaths": "Deaths",
                "damageDealt": "Damage Dealt",
                "damageTaken": "Damage Taken",
                "teamkills": "Teammates Killed",
                "suicides": "Suicides",
                "flashes": "Flashes",
                "teamFlashes": "Team Flashes",
                "amountSpended": "Amount Spent",
                "amountDrank": "Amount Drank"
            }

            desc = f"{statToDesc[stat]}: {val:.0f}"
            awards.append((title, pawn, desc))

        add_stat_award("MOST KILLS",
                    max(pawns, key=lambda p: p.stats["kills"]),
                    "kills")

        add_stat_award("MOST DEATHS",
                    max(pawns, key=lambda p: p.stats["deaths"]),
                    "deaths")

        add_stat_award("LEAST DAMAGE DEALT",
                    min(pawns, key=lambda p: p.stats["damageDealt"]),
                    "damageDealt")

        add_stat_award("MOST DAMAGE DEALT",
                    max(pawns, key=lambda p: p.stats["damageDealt"]),
                    "damageDealt")

        add_stat_award("LEAST DAMAGE TAKEN",
                    min(pawns, key=lambda p: p.stats["damageTaken"]),
                    "damageTaken")

        add_stat_award("MOST DAMAGE TAKEN",
                    max(pawns, key=lambda p: p.stats["damageTaken"]),
                    "damageTaken")

        add_stat_award("MOST TEAMMATES KILLED",
                    max(pawns, key=lambda p: p.stats["teamkills"]),
                    "teamkills")

        add_stat_award("MOST SUICIDES",
                    max(pawns, key=lambda p: p.stats["suicides"]),
                    "suicides")

        add_stat_award("MOST FLASHES",
                    max(pawns, key=lambda p: p.stats["flashes"]),
                    "flashes")

        add_stat_award("MOST TEAMFLASHES",
                    max(pawns, key=lambda p: p.stats["teamFlashes"]),
                    "teamFlashes")

        # --- Drink-specific awards ---
        heaviest = max(pawns, key=lambda p: p.stats["amountDrank"])
        awards.append((
            "HEAVIEST DRINKER",
            heaviest,
            self.summarizeDrinks(heaviest)
        ))

        worst = min(pawns, key=lambda p: p.stats["amountDrank"])
        awards.append((
            "WORST DRINKER",
            worst,
            self.summarizeDrinks(worst)
        ))

        add_stat_award("BIGGEST SPENDER",
                    max(pawns, key=lambda p: p.stats["amountSpended"]),
                    "amountSpended")

        add_stat_award("SMALLEST SPENDER",
                    min(pawns, key=lambda p: p.stats["amountSpended"]),
                    "amountSpended")

        self.awards = awards


    

    def summarizeDrinks(self, pawn):
        if not pawn.lastDrinks:
            return "No drinks consumed"

        counts = Counter()
        for _, drinkType in pawn.lastDrinks:
            counts[drinkType] += 1

        parts = []

        if counts.get("shot"):
            parts.append(f"{counts['shot']} shots")

        if counts.get("330ml"):
            parts.append(f"{counts['330ml']} × 330ml")

        if counts.get("500ml"):
            parts.append(f"{counts['500ml']} × 500ml")

        return "Drinks drunk: " + ", ".join(parts)

    def endGame(self):

        t1, t2 = sorted(self.allTeams, key=lambda x: x.wins, reverse=True)[:2]

        if t1.wins > t2.wins and t1.wins >= self.maxWins and self.round >= len(self.gameModeLineUp) - 1 and self.DOREALGAMEMODES:
            self.GAMESTATE = "end"
            print("ending game.")
            self.buildAwards()
        else:
            self.GAMESTATE = "pawnGeneration"
            print("not ending game.")
            print(t1.i, t1.wins)
            print(t2.i, t2.wins)
            print(self.round >= len(self.gameModeLineUp))


        

        self.GAMEMODE = None
        self.PEACEFUL = True
        self.objectiveCarriedBy = None
        self.teamInspectIndex = -1
        self.nextMusic = 0
        self.mapCreated = False
        self.CAMERA.cameraLock = None

        self.FireSystem.clearCells()
        for x in self.allTeams:
            x.utilityPos["aggr"].clear()
            x.utilityPos["defensive"].clear()

        if self.skull:
            self.skull.kill()

        for x in self.allTeams:
            x.emancipate()
            x.refreshColor()
            
        for x in self.pawnHelpList:
            self.allTeams[x.originalTeam].add(x)
            x.enslaved = False
            x.killed = False
            x.reset()
            x.defaultPos()
            x.respawnI = 0

            if not x.isPawn:
                if x in self.ENTITIES:
                    self.ENTITIES.remove(x)
                if x in self.pawnHelpList:
                    self.pawnHelpList.remove(x)
                x.killed = True

        if self.BABLO:
            self.BABLO.die()
            self.BABLO.killed = True
            self.BABLO.respawnI = 1
            if self.BABLO in self.ENTITIES:
                self.ENTITIES.remove(self.BABLO)
            if self.BABLO in self.pawnHelpList:
                self.pawnHelpList.remove(self.BABLO)


        self.refreshShops()
        self.particle_list.clear()
        self.round += 1
        if self.round == 2 and False:
            self.judgePawns()
        self.LAZER.deactivate()

        if self.NPC_WEAPONS_PURCHASE:
            self.handleNPCWeaponPurchase()

        self.clearEntities()


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

    def switchToDemo(self):

        state = self.PLAYBACKDEMO

        self.PLAYBACKDEMO = not state
        self.RECORDDEMO = state
        self.demoTick = 0
        self.demoTickIncrement = 0


    def handleHud(self, CAMERA: Camera, index = 0):
        if CAMERA.currHud == CAMERA.cameraLock and CAMERA.currHud and not self.VICTORY:
            CAMERA.hudChange += self.deltaTimeR * 2
            CAMERA.hudChange = min(1, CAMERA.hudChange)

        else:
            CAMERA.hudChange -= self.deltaTimeR * 2
            CAMERA.hudChange = max(0, CAMERA.hudChange)
            if CAMERA.hudChange == 0:
                CAMERA.currHud = None

                CAMERA.ekg_time = 0.0
                CAMERA.ekg_accum = 0.0
                CAMERA.ekg_points.clear()

                if not CAMERA.currHud and CAMERA.cameraLock:
                    CAMERA.currHud = CAMERA.cameraLock

        if CAMERA.hudChange > 0 and CAMERA.currHud:
            
            currHud: "Pawn" = CAMERA.currHud
            
            health = currHud.health / currHud.getHealthCap()
            health = min(1, max(health, 0))

            if currHud.killed:
                health = 0

            if health != 0:
                CAMERA.heartRateEKG = 1.2 + (5 * (1-health))
            else:
                CAMERA.heartRateEKG = 0

            EKG = CAMERA.updateEKG()

            yPos = self.res[1] - 220*(1-(1-CAMERA.hudChange)**2)
            surf = pygame.Surface((200,200))
            c = self.getTeamColor(currHud.team.i)
            surf.fill((c[0]*0.2, c[1]*0.2, c[2]*0.2))
            surf.blit(currHud.hudImage if index == 1 else currHud.hudImageFlipped, v2(100,100) - v2(currHud.hudImage.get_size())/2)
            surf.blit(random.choice(self.noise), (0,0))
            pygame.draw.rect(surf, c, (0,0,200,200), width=1)

            surf2 = pygame.Surface((180,40))
            surf2.fill((0,0,0))
            color2 = heat_color(1-health)

            
            
            lastPos = (0,39)
            for i,p in enumerate(EKG):
                x = i/len(EKG) * 180
                y = 32 - p*5
                pos = (x,y)
                I = i/len(EKG)
                c = [int(color2[0] * I), int(color2[1] * I), int(color2[2] * I)]
                pygame.draw.line(surf2, c, lastPos, pos, width=2)
                lastPos = pos

            pygame.draw.rect(surf2, color2, (0,0,180,40), width=2)

            if health != 0:
                t = self.font.render(f"+{int(currHud.health)}", True, color2)
            else:
                t = self.font.render(f"DEAD", True, color2)
            surf2.blit(t, (5, 20-t.get_height()/2))

            
            surf.blit(surf2, [10, 155])

            c2 = [255,255,255]

            t1 = self.font.render(currHud.name, True, c2)
            

            if index == 0:
                surf.blit(t1, (5, 5))
                self.screen.blit(surf, [20, yPos])
                hudInfoPos = (240, yPos)
            else:
                surf.blit(t1, (surf.get_width() - t1.get_width() - 5, 5))
                self.screen.blit(surf, [self.originalRes.x - surf.get_width() - 20, yPos])
                hudInfoPos = (self.originalRes.x - surf.get_width() - 25, yPos)

            p = currHud

            p.hudInfo(hudInfoPos, screen=self.screen, reverse = bool(index))

            

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
            
        
            pygame.draw.rect(self.MAP, (0,0,0), (x*self.tileSize*self.RENDER_SCALE,y*self.tileSize*self.RENDER_SCALE, 
                                                 self.tileSize*self.RENDER_SCALE + 1, self.tileSize*self.RENDER_SCALE + 1))
            
    def drawDetonation(self):
        if self.GAMEMODE != "DETONATION":
            return
        
        for site in self.SITES:
            r = site.room
            rect = pygame.Rect(r.x*self.tileSize, r.y*self.tileSize, 
                                r.width*self.tileSize * self.RENDER_SCALE, r.height*self.tileSize * self.RENDER_SCALE)
            rect.topleft = self.convertPos(rect.topleft)
            draw_rect_perimeter(self.DRAWTO, rect, time.time()-self.now, 200, 10, [255,0,0], width=5)
        

    def drawTurfs(self):
        if self.GAMEMODE != "TURF WARS":
            return
        for r in self.map.rooms:
            if r.turfWarTeam is not None:
                rect = pygame.Rect(r.x*self.tileSize, r.y*self.tileSize, 
                                   r.width*self.tileSize * self.RENDER_SCALE, r.height*self.tileSize * self.RENDER_SCALE)
                rect.topleft = self.convertPos(rect.topleft)
                draw_rect_perimeter(self.DRAWTO, rect, time.time()-self.now, 200, 10, self.getTeamColor(r.turfWarTeam), width=5)

    def drawKOTH(self):
        if self.GAMEMODE != "KING OF THE HILL":
            return
        r = self.currHill
        
        rect = pygame.Rect(r.x*self.tileSize, r.y*self.tileSize, 
                            r.width*self.tileSize * self.RENDER_SCALE, r.height*self.tileSize * self.RENDER_SCALE)
        rect.topleft = self.convertPos(rect.topleft)

        if r.turfWarTeam is not None:
            color = self.getTeamColor(r.turfWarTeam)
        else:
            color = [255,255,255]

        draw_rect_perimeter(self.DRAWTO, rect, time.time()-self.now, 200, 10, color, width=5)

    def giveAllWeapons(self):
        for x in self.pawnHelpList:
            if x.BOSS or not x.isPawn:
                continue
            w = random.choice(self.weapons)
            w.give(x)
            x.gType = random.randint(0,3)

    def tickScoreBoard(self):
        y = 20

        if self.GAMEMODE == "ODDBALL":
            for i, x in sorted(enumerate(self.skullTimes), key=lambda pair: pair[1], reverse=True):
                t = combinedText(f"{self.allTeams[i].getName()}: ", self.getTeamColor(i), f"{x:.1f} seconds", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22
        elif self.GAMEMODE in ["TEAM DEATHMATCH", "DETONATION"]:
            kills = [0 for _ in range(self.teams)]
            for p in self.getActualPawns():
                kills[p.team.i] += p.kills

            for i, x in sorted(enumerate(kills), key=lambda pair: pair[1], reverse=True):
                t = combinedText(f"{self.allTeams[i].getName()}: ", self.getTeamColor(i), f"{x} kills", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22

        elif self.GAMEMODE == "SUDDEN DEATH":
            alive = [0 for _ in range(self.teams)]
            for p in [x for x in self.getActualPawns() if not x.killed]:
                alive[p.team.i] += 1

            for i, x in sorted(enumerate(alive), key=lambda pair: pair[1], reverse=True):
                t = combinedText(f"{self.allTeams[i].getName()}: ", self.getTeamColor(i), f"{x} alive", self.getTeamColor(i), font=self.fontSmaller)
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

                all_enslaved = all(x.enslaved for x in self.getActualPawns() if x.originalTeam == i)

                t = combinedText(f"{self.allTeams[i].getName()}: ", self.getTeamColor(i), f"{x} rooms" if not all_enslaved else "ORJUUTETTU", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22

        elif self.GAMEMODE == "FINAL SHOWDOWN" and not self.BABLO.killed:
            damage = [0 for _ in range(self.teams)]

            for i, d in enumerate(self.BABLO.damageTakenPerTeam.values()):
                if i >= len(damage):
                    continue
                damage[i] = self.BABLO.damageTakenPerTeam.get(i, 0)

            for i, x in sorted(enumerate(damage), key=lambda pair: pair[1], reverse=True):

                t = combinedText(f"{self.allTeams[i].getName()}: ", self.getTeamColor(i), f"{x:.1f} damage dealt", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22

        elif self.GAMEMODE == "KING OF THE HILL":
            timeOnTheHill = [x.kothTime for x in self.allTeams]

            for i, x in sorted(enumerate(timeOnTheHill), key=lambda pair: pair[1], reverse=True):

                t = combinedText(f"{self.allTeams[i].getName()}: ", self.getTeamColor(i), f"{x:.1f} seconds", self.getTeamColor(i), font=self.fontSmaller)
                self.screen.blit(t, [10, y])
                y += 22

        else:
            return


        y += 22

        for x in sorted([x for x in self.pawnHelpList if x.isPawn], key = lambda p: p.kills, reverse=True):

            npcAppendix = "(NPC)" if x.NPC else ""
            t = combinedText(f"{x.name} {npcAppendix}: ", x.teamColor, f"LVL {x.level}  {x.kills}/{x.deaths}", [255,255,255], font=self.fontSmallest)
            r = t.get_rect()
            r.topleft = [10,y]
            
            if r.collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, x.teamColor, r, width=2)
                if "mouse0" in self.keypress:
                    if x not in self.filmOnly:
                        self.filmOnly.append(x)
                    else:
                        self.filmOnly.remove(x)

                    self.CAMERA.cameraLock = None
                    self.cameraLinger = 0

            elif x in self.filmOnly:
                pygame.draw.rect(self.screen, x.teamColor, r, width=1)


            self.screen.blit(t, [10,y])
            y += 14


    def toggleRendering(self):
        self.RENDERING = not self.RENDERING

    
    def drawRoundInfo(self):
        t1 = self.fontSmaller.render("Round: " + str(self.round+1), True, [255]*3)
        t2 = self.font.render(self.GAMEMODE, True, [255]*3)
        
        self.screen.blit(t1, [self.res[0]/2 - t1.get_size()[0]/2, 10])
        self.screen.blit(t2, [self.res[0]/2 - t2.get_size()[0]/2, 40])

        minutes = int(self.roundTime / 60)
        seconds = int(self.roundTime % 60)
        t3 = self.font.render(f"{minutes:02}:{seconds:02}", True, [255]*3)
        self.screen.blit(t3, [self.res[0]/2 - t3.get_size()[0]/2, 70])

    def drawRoundInfoDetonation(self):
        t1 = self.fontSmaller.render("Round: " + str(self.round+1), True, [255]*3)
        t2 = self.font.render(self.GAMEMODE, True, [255]*3)
        
        self.screen.blit(t1, [self.res[0]/2 - t1.get_size()[0]/2, 10])
        self.screen.blit(t2, [self.res[0]/2 - t2.get_size()[0]/2, 40])

        minutes = int(self.roundTime / 60)
        seconds = int(self.roundTime % 60)
        t3 = self.font.render(f"{minutes:02}:{seconds:02}", True, [255]*3)

        if self.skull.planted:
            t3.set_alpha(100)

        self.screen.blit(t3, [self.res[0]/2 - t3.get_size()[0]/2, 70])
        
        if self.skull.planted:

            self.bombInfoI = 1 * 0.01 + self.bombInfoI * 0.99

            if not self.skull.defusedBy:
                seconds = self.skull.time
                t3 = self.font.render(f"BOMB EXPLODES IN {seconds:.1f} SECONDS", True, [255, 210, 64])
                self.screen.blit(t3, [self.res[0]/2 - t3.get_size()[0]/2, 100])

            else:
                seconds = self.skull.defuseTimer
                t3 = self.font.render(f"DEFUSED IN {seconds:.1f} SECONDS", True, [76, 129, 255])
                self.screen.blit(t3, [self.res[0]/2 - t3.get_size()[0]/2, 100])

        else:
            self.bombInfoI = self.bombInfoI * 0.99

        for i, site in enumerate(self.SITES):

            planSite = self.allTeams[0].getCurrentSite() == site

            xPos = i - (len(self.SITES) - 1)/2

            c = v2([self.res[0]/2 + 60 * xPos, 130 + 25*self.bombInfoI])
            rect = pygame.Rect(1,1,40,35)
            rect.center = c

            color = [255,0,0] if planSite else [255,255,255]

            pygame.draw.rect(self.screen, color, rect, width=2)
            t = self.font.render(site.name, True, color)
            self.screen.blit(t, v2(rect.center) - v2(t.get_size())/2)
        



    def drawBFGLazers(self):
        currLaser = False
        for startPos, endPos, color in self.BFGLasers:
            s1 = startPos
            e1 = endPos
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

            name, image, client, team = random.choice(self.playerFilesToGen)
            self.playerFiles.append(name)
            self.playerFilesToGen.remove((name, image, client, team))

            #p = "players/" if non_npc else "npcs/"
            if client:
                if client != "DEBUG":
                    client_ip, client_port = client.remote_address
                else:
                    client_ip = "DEBUG"
            else:
                client_ip = None

            t = threading.Thread(target=self.threadedGeneration, args=(name, image, client_ip, team))
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

    def tickTrails(self):
        toremove = []
        for i, trail in enumerate(self.trails):
            trail.pop(0)
            if not trail:
                toremove.append(i)

        for i in reversed(toremove):
            self.trails.pop(i)

    def renderTrails(self):
        for trail in self.trails:
            if len(trail) < 2:
                continue
            Bullet.renderTrail(self, trail)

    def playPositionalAudio(self, audio, pos = None):

        if self.STRESSTEST:
            return

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
        self.playPositionalAudio("audio/flash.wav", v2(random.uniform(-3000, 3000), random.uniform(-3000, 3000)))
        self.log("Audio engine initialized.")

    def notify(self, text, color = [255,255,255]):
        self.notificationTime = pygame.time.get_ticks()
        self.currNotification = [text, color]

    def drawFPS(self):
        lastTime = 0
        m = max(self.frameTimeCache)

        minT = min(self.frameTimeCache)

        tf = self.fontSmaller.render(f"{minT*1000:.2f} / {m*1000:.2f} ms", True, [255,255,255])
        self.screen.blit(tf, (self.res.x - tf.get_width(), 830))

        for i, x in enumerate(self.frameTimeCache):
            t = 50 * ((x-minT)/(m-minT))
            if i:
                pygame.draw.line(self.screen, [0,255,0], (self.res.x - i-1, 850 - lastTime), (self.res.x - i, 850 - t), 1)
            lastTime = t

        
    def raycast_grid(self, pos, direction, max_dist):
        x0, y0 = pos.x / self.tileSize, pos.y / self.tileSize
        dx, dy = direction.x, direction.y

        map_x = int(x0)
        map_y = int(y0)

        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1

        t_delta_x = abs(1 / dx) if dx != 0 else float("inf")
        t_delta_y = abs(1 / dy) if dy != 0 else float("inf")

        next_x = map_x + (1 if dx > 0 else 0)
        next_y = map_y + (1 if dy > 0 else 0)

        t_max_x = (next_x - x0) / dx if dx != 0 else float("inf")
        t_max_y = (next_y - y0) / dy if dy != 0 else float("inf")

        t = 0.0
        hit_axis = None

        while t <= max_dist:
            if 0 <= map_x < self.map.grid.shape[1] and 0 <= map_y < self.map.grid.shape[0]:
                if self.map.grid[map_y, map_x] == CellType.WALL.value:
                    hit_pos = pos + direction * (t * self.tileSize)
                    hit_pos -= direction * 1.0

                    if hit_axis == 'x':
                        normal = pygame.Vector2(-step_x, 0)
                    else:
                        normal = pygame.Vector2(0, -step_y)

                    return hit_pos, normal
            else:
                return None, None

            if t_max_x < t_max_y:
                map_x += step_x
                t = t_max_x
                t_max_x += t_delta_x
                hit_axis = 'x'
            else:
                map_y += step_y
                t = t_max_y
                t_max_y += t_delta_y
                hit_axis = 'y'

        return None, None

    def run(self):
        self.frameTimeCache = []
        timeSum = 0
        while True:
            self.SLOWMO = 1


            self.debugCells.clear()

            if self.SLOWMO_FOR > 0:

                self.SLOWMO = 1 - 0.9 * min(1, self.SLOWMO_FOR * 2)

                self.SLOWMO_FOR -= self.deltaTimeR
                self.SLOWMO_FOR = max(0, self.SLOWMO_FOR)

            #elif self.BABLO and not self.BABLO.killed and self.GAMEMODE == "FINAL SHOWDOWN":
            #    self.SLOWMO = 0.2 + 5*(self.beatI**2)

            self.mankkaDistance = float("inf")
            tickStartTime = time.time()

            key_press_manager(self)
        
            self.debugI = 0

            if self.pawnHelpList:
                self.randomTalkInterval -= self.deltaTimeR
                if self.randomTalkInterval <= 0:
                    self.randomTalkInterval = random.uniform(5, 15)
                    p = random.choice(self.getActualPawns())
                    p.say(random.choice(
                        [
                        "Nyt palo munat!",
                        "Mä oon paras!",
                        "Makke on maailman paskin jätkä",
                        "Piaru.",
                        "Eihän tämä tunnu missään",
                        "Jyri vie roskat roskiin",
                        str(p),
                        p.name + " on Epstein kansioissa",
                        "Mä haluun kotiin",
                        "Onpa paska peli",
                        "Älkää kertoko kenellekään, mutta mä huijaan",
                        "Oon varma että Makella on satiaisia",
                        "Tää peli on ihan paska",
                        "Voittaja! Voittaja!",
                    ]))


            if self.GAMESTATE != "pawnGeneration" or self.pregametick == "judgement":
                self.shopTimer = self.midRoundTime
            else:
                if not self.playerFilesToGen and self.pawnGenI == 0 and self.TRANSITION == False:
                    self.shopTimer -= self.deltaTimeR
                    self.shopTimer = max(0, self.shopTimer)

            if self.GAMESTATE == "settings":
                settingsTick(self)

            elif self.GAMESTATE == "end":
                gameEndTick(self)

            elif self.GAMESTATE == "pawnGeneration":
                preGameTick(self)

            elif self.GAMESTATE == "loadingScreen":
                loadingTick(self)
            
            elif self.GAMESTATE == "millionaire":
                millionaireTick(self)

            elif self.GAMESTATE == "showcase":
                showcaseTick(self)

            elif self.GAMESTATE == "qrs":
                qrCodesTick(self)

            elif self.GAMESTATE == "intro":
                intro(self)

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

            SPAWNBABLO = self.GAMEMODE == "FINAL SHOWDOWN" and self.GAMESTATE == "ODDBALL" and self.currMusic == 0

            if not self.BLOCKMUSIC:
                self.musicSwitch = self.handleMusic()
            else:
                self.musicSwitch = False
            

            if SPAWNBABLO and self.musicSwitch and self.currMusic == 1:
                print("Bablo spawned!")
                self.BABLO.health = self.BABLO.healthCap
                self.BABLO.respawnI = 0
                P = self.commonRoom.center()
                self.BABLO.pos = v2(P) * self.tileSize + [self.tileSize/2, self.tileSize/2] 
                self.BABLO.killed = False
                #self.notify("SURVIVE")
                self.CAMERAS[0].cameraLock = self.BABLO
                self.BABLO.damageTakenPerTeam = {}
                self.SLOWMO_FOR = 3.36
                self.particle_system.create_explosion(self.BABLO.pos.x, self.BABLO.pos.y, count = 100)

            if self.GAMEMODE == "FINAL SHOWDOWN" and self.GAMESTATE == "ODDBALL" and self.currMusic == 1:
                self.handleBabloLyrics()
                self.debugText(f"{self.babloLyricCurrent}")
                self.debugText(f"{self.babloLyricNorm:.2f}")
                self.debugText(f"{self.babloLyricTime:.2f}")

            if self.GAMESTATE in ["millionaire"]:
                pygame.mixer.music.unload()
                pygame.mixer.music.stop()
            else:
                #self.handleMainMusic()
                #self.drawSubs()
                self.BPM()
            #r = pygame.Rect((0,0), self.res)
            #pygame.draw.rect(self.screen, [255,0,0], r, width=1+int(15*(self.beatI**2)))

            #self.screen.fill((0, 0, 0))
            elapsed = time.time() - self.now

            if self.currNotification and self.RENDERING:
                if self.draw_notification(self.currNotification[0], self.res.x/2, self.res.y/4, 
                                          self.notificationTime, color=self.currNotification[1]):
                    self.currNotification = None

            self.manualTransition = False

            self.ATR.tick()

            if self.TRANSITION:
                self.drawExplosion()
            elif self.FADEIN > 0:
                self.screen.blit(self.FADEOUT[self.FADEIN], (0,0))
                self.FADEIN -= 1

            elif self.FADEOUTMANUAL < len(self.FADEOUT):
                self.screen.blit(self.FADEOUT[self.FADEOUTMANUAL], (0,0))
                self.FADEOUTMANUAL += 1
                if self.FADEOUTMANUAL == len(self.FADEOUT):
                    self.FADEIN = len(self.FADEOUT) - 1
                    self.manualTransition = True

            if not self.TRANSITION and self.TARGETGAMESTATE:
                self.TARGETGAMESTATE()
                self.TARGETGAMESTATE = None

           # for x in self.AUDIOMIXER.audio_sources:
           #     p = x.pos - self.cameraPosDelta
           #     pygame.draw.circle(self.screen, [255,0,0], p, 10)

            if "f1" in self.keypress:
               self.consoleOpen = not self.consoleOpen
            
            if self.consoleOpen:
                runConsole(self)

            if self.DISPLAY_VAC:
                self.screen.blit(self.darken[-1], (0,0))
                p = self.VACPAWN
                t = self.fontLarge.render(f"{p.name} REKISTERÖI ÄSKEN KAKS KERTAA {self.timeBetween:.1f} SEKUNNIS :DDD", True, [255, 0, 0])
                self.screen.blit(t, self.originalRes / 2 - v2(t.get_size()) / 2)

                t = self.fontLarge.render(f"JULKINEN TELOITUS VARATTU 30 MIN PÄÄHÄN", True, [255, 0, 0])
                self.screen.blit(t, self.originalRes / 2 - v2(t.get_size()) / 2 + [0,60])

           #if self.STRESSTEST and not self.PEACEFUL:
           #    if self.stressTestFpsClock >= 1/60:
           #        pygame.display.update()
           #        self.stressTestFpsClock = 0
           #else:
            pygame.display.update()
            self.t1 = time.time() - tickStartTime

            #if self.STRESSTEST:
            #    self.stressTestFpsClock += self.t1
            
            if self.STRESSTEST:
                self.clock.tick()
                self.deltaTimeR = 1/self.FIXED_FRAMERATE
            else:
                self.deltaTimeR = self.clock.tick(self.MAXFPS) / 1000
            self.t2 = time.time() - tickStartTime


            self.frameTimeCache.append(self.t2)
            timeSum += self.t2
            if len(self.frameTimeCache) > 144:
                tR = self.frameTimeCache.pop(0)
                timeSum -= tR
            

            self.FPS = len(self.frameTimeCache) / sum(self.frameTimeCache)
            self.MAXFRAMETIME = max(self.frameTimeCache)
            self.STD = stdev(self.frameTimeCache) if len(self.frameTimeCache) > 1 else 0

            self.deltaTimeR = min(self.deltaTimeR, 1/20)
            self.deltaTime = self.deltaTimeR


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

import traceback

def run():
    for i in range(1):
        try:
            game = Game()
            game.run()
            print("Program exited Normally!")
            break  # normal exit → stop restarting
        except KeyboardInterrupt:
            raise
        except Exception:
            with open("crash.log", "a", encoding="utf-8") as f:
                f.write("\n" + "="*60 + "\n")
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                traceback.print_exc(file=f)
                traceback.print_exc()
            #time.sleep(2)

if __name__ == "__main__":
    run()
