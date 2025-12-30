from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from renderObjects.pawn.pawn import Pawn

from pygame.math import Vector2 as v2
import pygame
import time
import math
import pickle
from renderObjects.bullet import raycast_grid
from core.drawRectPerimeter import draw_rect_perimeter


# --------------------------
# Public entry
# --------------------------

def battleTick(self: "Game"):
    _battle_pretick(self)

    victoryCondition = _battle_victory_logic(self)

    entities_temp = _battle_prepare_entities(self)

    FF, TIMESCALE = _battle_timescale(self)

    if self.DO_DEMO:
        _demo_logic(self)

    _battle_roundtime_and_timeout(self, victoryCondition)

    if not self.VICTORY and victoryCondition:
        self.monitorProgress -= self.deltaTime
        if self.monitorProgress <= 0:
            self.monitorProgress = 5
            for i, x in enumerate(victoryCondition):
                self.victoryProgress[i].append(x)

    if self.GAMEMODE == "FINAL SHOWDOWN" or self.PLAYBACKDEMO:
        self.amountOfScreens = 1
    elif self.CAMERAS[0].cameraLock and self.CAMERAS[1].cameraLock and (
        self.CAMERAS[0].cameraLock.target == self.CAMERAS[1].cameraLock or
        self.CAMERAS[1].cameraLock.target == self.CAMERAS[0].cameraLock):
        self.amountOfScreens = 1
    else:
        self.amountOfScreens = 2

    self.screenSwitchI = self.amountOfScreens * 0.05 + self.screenSwitchI * 0.95

    self.res = self.originalRes.copy()
    self.res.x /= self.screenSwitchI

    self.camResSave = self.res.copy()


    _battle_minimap_begin(self)

    _battle_particle_and_world_updates(self)

    _battle_mode_specific_world_updates(self)

    _battle_tick_entities(self, entities_temp)

    _battle_post_entity_logic(self)

    x1,y1 = self.CAMERAS[0].pos
    x2,y2 = self.CAMERAS[1].pos
    rect1 = pygame.Rect(x1,y1, self.camRes.x, self.camRes.y) 
    rect2 = pygame.Rect(x2,y2, self.camRes.x, self.camRes.y) 

    CAMERASCOLLIDE = rect1.colliderect(rect2) and False
    VERSUS = self.CAMERAS[0].cameraLock and self.CAMERAS[1].cameraLock and (
        self.CAMERAS[0].cameraLock.target == self.CAMERAS[1].cameraLock or
        self.CAMERAS[1].cameraLock.target == self.CAMERAS[0].cameraLock)
    
    beginTransition = self.TRANSITION_INTO_SINGLE

   #if self.GAMEMODE == "":
   #    self.amountOfScreens = 1

   ##elif self.CAMERAS[0].cameraLock and self.CAMERAS[1].cameraLock:
   #else:
   #    self.amountOfScreens = 2

   #if self.TRANSITION_INTO_SINGLE != beginTransition:
   #    self.FADEOUTMANUAL = 0

   #if self.manualTransition:
   #    self.IN_SINGLE = self.TRANSITION_INTO_SINGLE


    

    for SPLITSCREENI in range(self.amountOfScreens):

        self.CAMERA = self.CAMERAS[SPLITSCREENI]

        _battle_handle_cameras(self)
        _battle_update_camera_and_cleanup(self)

        #print("HANDLING CAMERA", self.CAMERA.cameraIndex)

        #_battle_handle_cameras(self)

        #_battle_update_camera_and_cleanup(self)

        DUAL = _battle_compute_dual_view(self, self.res)

        _battle_render_world(self, entities_temp, DUAL, SPLITSCREENI, self.amountOfScreens)

    self.res = self.originalRes.copy()

    _battle_render_overlays_and_ui(self, FF)

    

    _battle_debug_and_metrics(self)


# --------------------------
# PRE / SETUP
# --------------------------

def _battle_pretick(self: "Game"):
    

    self.PEACEFUL = False
    self.BFGLasers = []
    self.debugCells = []


def _battle_prepare_entities(self: "Game"):
    entities_temp = sorted(self.ENTITIES, key=lambda x: x.pos.y)

    if self.GAMEMODE == "1v1":
        for x in self.pawnHelpList:
            if x in self.duelPawns:
                continue
            x.respawnI = 5
            x.killed = True

    return entities_temp


# --------------------------
# VICTORY LOGIC
# --------------------------

def _demo_logic(self: "Game"):
    self.RECORDDEMO = not self.VICTORY

    self.demoTickIncrement += self.deltaTime
    if self.demoTickIncrement >= 1/self.DEMOFPS:
        self.demoTick += 1
        self.demoTickIncrement -= 1/self.DEMOFPS

def _battle_victory_logic(self: "Game"):
    # ensures victoryCondition exists for later timeout handling
    victoryCondition = None

    if not self.VICTORY:

        if self.GAMEMODE == "ODDBALL":

            victoryCondition = self.skullTimes

            for i, x in enumerate(self.skullTimes):
                if x >= self.skullVictoryTime:
                    self.announceVictory(i)
                    break

        elif self.GAMEMODE == "TEAM DEATHMATCH":
            victoryCondition = [0 for _ in range(self.teams)]
            for p in self.getActualPawns():
                victoryCondition[p.team.i] += p.kills

            for i, x in enumerate(victoryCondition):
                if x >= 100:
                    self.announceVictory(i)
                    break

        elif self.GAMEMODE == "1v1":
            victoryCondition = [0 for _ in range(len(self.duelPawns))]
            for i, p in enumerate(self.duelPawns):
                victoryCondition[i] = p.kills

            for i, x in enumerate(victoryCondition):
                if x >= 10:
                    self.announceVictory(self.duelPawns[i].team.i)
                    break

        elif self.GAMEMODE == "TURF WARS":
            victoryCondition = [0 for _ in range(self.teams)]
            for r in self.map.rooms:
                if r.turfWarTeam is not None:
                    victoryCondition[r.turfWarTeam] += 1

            for i, x in enumerate(victoryCondition):
                if x == len(self.map.rooms):
                    self.announceVictory(i)
                    break

        elif self.GAMEMODE == "FINAL SHOWDOWN":
            victoryCondition = [self.BABLO.damageTakenPerTeam.get(x,0) for x in range(len(self.allTeams))]

        elif self.GAMEMODE == "DETONATION":
            victoryCondition = [0 for _ in range(2)]
            if self.SITES:
                if len(self.SITES) == 1:
                    victoryCondition[1] = 1  # TIE
                    victoryCondition[0] = 1
                else:
                    victoryCondition[1] = 1
            else:
                victoryCondition[0] = 1
                self.announceVictory(0)

        elif self.GAMEMODE == "KING OF THE HILL":
            victoryCondition = [x.kothTime for x in self.allTeams]
            for i, x in enumerate(victoryCondition):
                if x >= 100:
                    self.announceVictory(i)
                    break

        elif self.GAMEMODE == "SUDDEN DEATH":
            alive = [0] * self.teams

            for p in self.getActualPawns():
                if not p.killed:
                    alive[p.team.i] += 1

            alive_teams = [i for i, n in enumerate(alive) if n > 0]

            if len(alive_teams) == 1:
                self.announceVictory(alive_teams[0])
            elif len(alive_teams) == 0:
                kills = [0 for _ in range(self.teams)]
                for p in self.getActualPawns():
                    kills[p.team.i] += p.kills
                teamWithMostKills = max(range(len(kills)), key=lambda i: kills[i])
                self.announceVictory(teamWithMostKills)

    self.roundTime = max(0, self.roundTime)

    return victoryCondition


# --------------------------
# CAMERA & TIMESCALE
# --------------------------

def _battle_handle_cameras(self: "Game"):
    self.CREATEDUAL = False

    if not self.MANUALPAWN:
        if self.AUTOCAMERA:
            self.handleCameraLock()
            self.handleCameraSplit()
    else:
        self.handleCameraManual()


def _battle_timescale(self: "Game"):
    combat = any(
        p.target or p.grenadePos
        for p in self.pawnHelpList
    ) or self.bombPlanted()

    if not self.PLAYBACKDEMO and not combat and self.GAMEMODE != "FINAL SHOWDOWN" and not self.VICTORY:
        self.fastForwardI += self.deltaTimeR
        self.fastForwardI = min(3, self.fastForwardI)
    else:
        self.fastForwardI -= self.deltaTimeR * 5
        self.fastForwardI = max(0, self.fastForwardI)

    FF = max(1, self.fastForwardI)
    TIMESCALE = self.TIMESCALE * FF

    if self.VICTORY:
        I = max(self.endGameI-13, 0)*0.5
        ENDGAME =  0.25 + I*0.75
    else:
        ENDGAME = 1

    self.TOTAL_TIME_ADJUSTMENT = self.SLOWMO * TIMESCALE * ENDGAME * self.THREAD_SLOWMO

    self.deltaTime *= self.TOTAL_TIME_ADJUSTMENT
    return FF, TIMESCALE


def _battle_roundtime_and_timeout(self: "Game", victoryCondition):
    if self.VICTORY:
        return

    if self.GAMEMODE == "FINAL SHOWDOWN":
        if self.currMusic == 1:
            self.roundTime -= self.deltaTime
        

    elif self.GAMEMODE == "DETONATION":
        if not self.skull.planted:
            self.roundTime -= self.deltaTime

    else:
        self.roundTime -= self.deltaTime

    if self.roundTime <= 0:
        print(victoryCondition)
        # Pick out from the victoryCondition the highest index
        max_index = victoryCondition.index(max(victoryCondition))

        if self.GAMEMODE == "DETONATION":
            if victoryCondition[0] == victoryCondition[1]:
                max_index = -1
        self.announceVictory(max_index)


# --------------------------
# MINIMAP PREP
# --------------------------

def _battle_minimap_begin(self: "Game"):
    # self.MINIMAP = self.map.to_pygame_surface(cell_size=self.MINIMAPCELLSIZE)
    self.MINIMAPTEMP = self.MINIMAP.copy()


# --------------------------
# WORLD UPDATES (non-entity)
# --------------------------

def _battle_particle_and_world_updates(self: "Game"):
    self.particle_system.update_all()

    if self.GAMEMODE == "TURF WARS":
        for r in self.map.rooms:
            r.pawnsPresent = []
            if r.turfWarTeam is not None:
                pygame.draw.rect(
                    self.MINIMAPTEMP,
                    self.getTeamColor(r.turfWarTeam, 0.25),
                    (r.x * self.MINIMAPCELLSIZE, r.y * self.MINIMAPCELLSIZE,
                     r.width * self.MINIMAPCELLSIZE, r.height * self.MINIMAPCELLSIZE)
                )

            if r in self.teamSpawnRooms:
                i = self.teamSpawnRooms.index(r)
                r2 = self.teamSpawnRooms[i]
                pygame.draw.rect(
                    self.MINIMAPTEMP,
                    self.getTeamColor(i, 1),
                    (r2.x * self.MINIMAPCELLSIZE, r2.y * self.MINIMAPCELLSIZE,
                     r2.width * self.MINIMAPCELLSIZE, r2.height * self.MINIMAPCELLSIZE),
                    width=1
                )

    if self.GAMEMODE == "DETONATION":
        for site in self.SITES:
            pos = v2(site.room.center()) * self.MINIMAPCELLSIZE
            t = self.fontSmaller.render(site.name, True, [155, 0, 0])
            self.MINIMAPTEMP.blit(t, pos - v2(t.get_size()) / 2)
            room = site.room
            rect = pygame.Rect(
                room.x * self.MINIMAPCELLSIZE,
                room.y * self.MINIMAPCELLSIZE,
                room.width * self.MINIMAPCELLSIZE,
                room.height * self.MINIMAPCELLSIZE
            )
            color = [255, 0, 0] if site == self.allTeams[0].getCurrentSite() else [255, 255, 255]
            draw_rect_perimeter(self.MINIMAPTEMP, rect, time.time() - self.now, 20, 2, color, width=1)


    if self.GAMEMODE == "KING OF THE HILL":
        self.currHill.pawnsPresent = []
        rect = pygame.Rect(
            self.currHill.x * self.MINIMAPCELLSIZE,
            self.currHill.y * self.MINIMAPCELLSIZE,
            self.currHill.width * self.MINIMAPCELLSIZE,
            self.currHill.height * self.MINIMAPCELLSIZE
        )
        if self.currHill.turfWarTeam is not None:
            color = self.getTeamColor(self.currHill.turfWarTeam)
        else:
            color = [255,255,255]
        draw_rect_perimeter(self.MINIMAPTEMP, rect, time.time() - self.now, 20, 4, color, width=2)


    # constructTeamVisibility(self)


def _battle_mode_specific_world_updates(self: "Game"):
    self.FireSystem.update()

    if self.GAMEMODE == "DETONATION":
        for x in self.SITES:
            x.tickSite()

        self.allTeams[0].tickDetonation()
        self.allTeams[-1].tickDetonation()

    for x in self.allTeams:
        x.tickNadePos()


# --------------------------
# ENTITY TICK
# --------------------------


    

def _battle_tick_entities(self: "Game", entities_temp):


    if self.PLAYBACKDEMO:
        self.createParticleDemo()

        tick_data = self.DEMO.get("ticks", {}).get(self.demoTick)
        if tick_data:
            ids = tick_data.keys()
            for id in ids:
                if not isinstance(id, int): continue
                obj = self.demoObjectLookUp[id]
                if obj not in self.demoObjects:
                    self.demoObjects.append(obj)

        for x in self.demoObjects:
            x.handleSprite()
            x._playBackTick()

    else:

        for x in entities_temp:
            if hasattr(x, "itemEffects"):
                self.deltaTime *= x.itemEffects["timeScale"]

            x.tick()

            if hasattr(x, "itemEffects"):
                self.deltaTime /= x.itemEffects["timeScale"]

    for x in self.visualEntities:
        x.tick()

    for x in self.bloodSplatters:
        x.tick()

    self.handleTurfWar()
    self.handleKOTH()
    self.tickTrails()


def _battle_post_entity_logic(self: "Game"):
    if self.GAMEMODE != "FINAL SHOWDOWN":
        self.commonRoomSwitchI += self.deltaTime
        if self.commonRoomSwitchI >= 10:
            self.commonRoomSwitchI = 0
            r2 = self.commonRoom
            self.commonRoom = max(self.map.rooms, key=lambda r: r.kills)
            if self.commonRoom != r2:
                print("COMMON ROOM SWITCHED!", self.commonRoom.kills)

    self.doBabloCracks()

    if self.objectiveCarriedBy and self.GAMEMODE == "ODDBALL":
        self.skullTimes[self.objectiveCarriedBy.team.i] += self.deltaTime


# --------------------------
# CAMERA UPDATE & CLEANUP
# --------------------------

def _battle_update_camera_and_cleanup(self: "Game"):
    if self.AUTOCAMERA:
        if self.CAMERA.splitI > 0:
            self.CAMERA.cameraPos = self.CAMERA.posToTargetTo.copy()

    else:
        if "w" in self.keypress_held_down:
            self.CAMERA.cameraPos.y -= 10
        elif "s" in self.keypress_held_down:
            self.CAMERA.cameraPos.y += 10

        if "a" in self.keypress_held_down:
            self.CAMERA.cameraPos.x -= 10
        elif "d" in self.keypress_held_down:
            self.CAMERA.cameraPos.x += 10

    # self.cameraVel[0] += self.smoothRotationFactor(self.cameraVel[0], CAMPANSPEED, self.cameraPos[0] - self.cameraPosDelta[0]) * self.deltaTimeR
    # self.cameraVel[1] += self.smoothRotationFactor(self.cameraVel[1], CAMPANSPEED, self.cameraPos[1] - self.cameraPosDelta[1]) * self.deltaTimeR
    # self.cameraPosDelta = self.cameraPosDelta * 0.9 + self.cameraPos * 0.1#* self.deltaTimeR
    # self.cameraPosDelta += self.cameraVel * self.deltaTimeR

    self.CAMERA.update(self.CAMERA.cameraPos, self.deltaTimeR, smooth_time=0.2)
    self.cameraPosDelta = self.CAMERA.pos.copy()

    self.AUDIOORIGIN = v2(500,500)

    self.cleanUpLevel()


def _battle_compute_dual_view(self: "Game", res):
    DUAL = False
    if self.CAMERA.splitI > 0:
        if self.CAMERA.requires_dual_view(self.res):
            DUAL = True

    self.CAMERA.DUALVIEWACTIVE = DUAL
    return DUAL


# --------------------------
# RENDER
# --------------------------

def _battle_render_world(self: "Game", entities_temp, DUAL: bool, SPLITSCREENI = 0, amountOfScreens = 2):

    if DUAL:
        if amountOfScreens == 1:
            DS1 = self.screenCopy1FULL
            DS2 = self.screenCopy2FULL
        else:
            DS1 = self.screenCopy1
            DS2 = self.screenCopy2


    if self.RENDERING:
        for i in range(1 if not DUAL else 2):

            if not DUAL:
                if amountOfScreens != 1:
                    self.DRAWTO = self.sp
                else:
                    self.DRAWTO = self.screen
            elif i == 0:
                self.DRAWTO = DS1
            else:
                self.DRAWTO = DS2

            self.DRAWTO.fill((0, 0, 0))

            if i == 1:
                SAVECAMPOS = self.cameraPosDelta.copy()
                self.cameraPosDelta = self.CAMERA.posToTargetTo2.copy()

            self.DRAWTO.blit(self.MAP, self.convertPos(v2(0,0)))

            if self.SLOWMO_FOR > 0 and not self.BABLO.killed:
                alpha = int(255 * min(max(self.SLOWMO_FOR * 2, 0.5), 1.0))
                self.speedLinesSurf.fill((0, 0, 0, alpha))
                self.speedlines.draw(self.speedLinesSurf, self.BABLO.pos - self.cameraPosDelta)
                self.DRAWTO.blit(self.speedLinesSurf, (0, 0))

            # self.renderParallax2()
            # self.DRAWTO.blit(self.wall_mask, -self.cameraPosDelta)
            self.drawTurfs()
            self.drawKOTH()
            self.drawDetonation()

            # if self.cameraLock:
            #     self.cameraLock.visualizeVis()

            for x in self.shitDict.values():
                x.render()

            self.FireSystem.draw(self.DRAWTO)

            for x in entities_temp:
                x.render()

            self.renderTrails()

            for x in self.visualEntities:
                x.render()

            self.drawBFGLazers()

            for x in self.bulletImpactPositions:
                pygame.draw.circle(self.DRAWTO, [255, 0, 0], v2(x) - self.cameraPosDelta, 10, )

            self.particle_system.render_all(self.DRAWTO)

            for x in self.debugCells:
                self.highLightCell(x)

            if DUAL and i == 1:
                self.cameraPosDelta = SAVECAMPOS.copy()

        if DUAL:

            splitScreen = self.screen if amountOfScreens == 1 else self.sp

            self.splitScreen(splitScreen, DS1, DS2)
    else:
        self.screen.fill((0, 0, 0))

    if amountOfScreens != 1:
        self.screen.blit(self.sp, (SPLITSCREENI * self.originalRes.x/amountOfScreens, 0))
        rect = self.sp.get_rect()
        rect.topleft = (SPLITSCREENI * self.originalRes.x/amountOfScreens, 0)
        pygame.draw.rect(self.screen, self.getTeamColor(self.CAMERA.cameraIndex), rect, width = 2)
    


def _battle_render_overlays_and_ui(self: "Game", FF: float):
    # onscreen count
    onscreen = 0
    for x in self.getActualPawns():
        if self.onScreen(x.pos):
            onscreen += 1

    for x in self.killfeed:
        x.tick()

    if self.VICTORY:
        self.tickEndGame()
        if self.endGameI < 0:
            if not self.TRANSITION:
                self.transition(lambda: self.endGame())
            # self.endGame()
    else:
        if self.RENDERING:
            # if self.GAMEMODE != "FINAL SHOWDOWN":
            self.tickScoreBoard()

    if not self.VICTORY:
        if self.GAMEMODE != "DETONATION":
            self.drawRoundInfo()
        else:
            self.drawRoundInfoDetonation()

    for x in self.CAMERAS:

        if x.cameraIndex >= self.amountOfScreens:
            break

        ox, oy = self.MINIMAPCELLSIZE * x.pos / (self.tileSize)
        w, h = self.MINIMAPCELLSIZE * self.camResSave / (self.tileSize)
        r = pygame.Rect(ox, oy, w, h)
        r.inflate_ip(w/self.RENDER_SCALE - w, h/self.RENDER_SCALE - h)
        pygame.draw.rect(self.MINIMAPTEMP, self.getTeamColor(x.cameraIndex), r, width=1)

    if self.skull:
        if self.objectiveCarriedBy:
            skullpos = self.objectiveCarriedBy.pos.copy()
        else:
            skullpos = self.skull.pos.copy()

        pygame.draw.circle(self.MINIMAPTEMP, [255, 255, 255], self.MINIMAPCELLSIZE * skullpos / self.tileSize, 6, width=1)

    if self.GAMEMODE != "FINAL SHOWDOWN":
        MINIMAP_POS = v2(self.originalRes.x/2 - self.MINIMAP.get_width()/2, self.originalRes.y - self.MINIMAP.get_height() - 10)
    else:
        MINIMAP_POS = v2(self.originalRes.x - self.MINIMAP.get_width() - 10, self.originalRes.y - self.MINIMAP.get_height() - 10)
    if not self.VICTORY:
        self.screen.blit(self.MINIMAPTEMP, MINIMAP_POS)

        w = self.MINIMAP.get_width()
        h = 40
        w_r = w / len(self.allTeams)
        x = 0

        for team in self.allTeams:
            rect1 = pygame.Rect(MINIMAP_POS + [x, -h], [w_r, h])

            pygame.draw.rect(self.screen, self.getTeamColor(team.i, 0.2), rect1)

            rect2 = rect1.copy()
            rect2.height = (team.wins / self.maxWins) * h
            rect2.bottom = rect1.bottom
            pygame.draw.rect(self.screen, self.getTeamColor(team.i, 0.5), rect2)

            pygame.draw.rect(self.screen, self.getTeamColor(team.i, 1), rect1, width=2)

            x += w_r

            center = rect1.center
            t = self.font.render(f"{team.wins}", True, [255, 255, 255])
            self.screen.blit(t, v2(center) - v2(t.get_size()) / 2)

            if self.winningTeam != None and team == self.winningTeam:
                crown_width = w_r * 0.6
                crown_height = h * 0.6
                crown_top = rect1.top - crown_height * 0.8
                crown_center_x = rect1.centerx

                points = [
                    (crown_center_x - crown_width / 2, rect1.top),  # bottom-left
                    (crown_center_x - crown_width / 2 - 5, crown_top),  # left spike
                    (crown_center_x - crown_width / 5, crown_top + crown_height * 0.33),
                    (crown_center_x, crown_top - crown_height * 0.5),  # middle spike
                    (crown_center_x + crown_width / 5, crown_top + crown_height * 0.33),
                    (crown_center_x + crown_width / 2 + 5, crown_top),  # right spike
                    (crown_center_x + crown_width / 2, rect1.top)  # bottom-right
                ]
                pygame.draw.polygon(self.screen, (255, 255, 0), points)
                pygame.draw.polygon(self.screen, (200, 200, 0), points, width=2)  # outline

    if self.RENDERING:
        for i in range(2):
            camera = self.CAMERAS[i]
            self.handleHud(camera, i)

    if self.pendingLevelUp and not self.VICTORY:
        self.levelUpScreen()
    else:
        self.resetLevelUpScreen()

    if self.ultFreeze > 0:
        self.handleUlting()

    if FF > 1:
        t = self.fontLarge.render("FAST FORWARDING", True, [255, 255, 255])

        alpha = 255 * (FF - 1) / 2
        t.set_alpha(int(alpha))

        self.screen.blit(t, self.res / 2 - v2(t.get_size()) / 2)

    


    if self.roundTime < 10 and not self.VICTORY:
        self.nextMusic = -1

    # keep onscreen for debug
    self._onscreen_cache = onscreen


# --------------------------
# DEBUG / METRICS
# --------------------------

def _battle_debug_and_metrics(self: "Game"):
    onscreen = getattr(self, "_onscreen_cache", 0)

    self.debugText(f"FPS: {self.FPS:.0f} (+/-{self.STD*1000:.1f}ms)")
    self.debugText(f"MAXFR: {self.MAXFRAMETIME*1000:.1f}ms")
    self.debugText(f"GEN: {self.pawnGenI:.0f}")
    self.debugText(f"SOUNDS: {len(self.AUDIOMIXER.audio_sources):.0f}")
    self.debugText(f"SOUND TIME: {self.AUDIOMIXER.callBackTime*1000:.1f}ms, ({self.AUDIOMIXER.callBackTime/(self.AUDIOMIXER.chunk_size/self.AUDIOMIXER.sample_rate)*100:.1f}%)")
    self.debugText(f"ONSCREEN: {onscreen}")
    self.debugText(f"MUSIC: {self.currMusic} -> {self.nextMusic}")
    self.debugText(f"CAM: {self.CAMERA.vibration_amp}")
    self.debugText(f"{self.cameraLinger:.2f}")

    for camera in self.CAMERAS:

        if camera.cameraLock:
            self.debugText(f"{camera.cameraLock.name}")
        else:
            self.debugText(f"{camera.cameraLock}")

    if self.GAMEMODE == "DETONATION":
        self.debugText(f"T: {self.allTeams[-1].plan['currentAction']}, {self.allTeams[-1].plan['planTimer']:.1f}")
        self.debugText(f"CT: {self.allTeams[0].plan['currentAction']}, {self.allTeams[0].plan['planTimer']:.1f}")
        self.debugText(f"Site controlled: {self.allTeams[0].terroristsHoldPlanSite()}")

    if self.GAMEMODE == "TURF WARS":
        for x in self.allTeams:
            self.debugText(f"TEAM {x.i}: {x.enslavedTo}")

    self.debugText(f"ENT: {len(self.pawnHelpList)}, {len([x for x in self.pawnHelpList if not x.isPawn])}")
    self.debugText(f"DEMO: {len(self.DEMO["ticks"])}")
    self.debugText(f"DEMO OBJS: {len(self.demoObjects)}")
    self.debugText(f"DEMO TOTOBJS: {len(self.demoObjectLookUp)}")
    if self.GAMEMODE == "KING OF THE HILL":
        self.debugText(f"KOTH: {self.currHill.pawnsPresent}")



# --------------------------
# DEBUG RAY (unchanged)
# --------------------------

def debugRay(self):
    ray_origin = self.cameraPosDelta + self.res / 2

    mouse_world = self.cameraPosDelta + self.mouse_pos
    direction = mouse_world - ray_origin
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()

    max_dist_tiles = 2000 / self.tileSize

    hit = raycast_grid(
        ray_origin,
        direction,
        max_dist_tiles,
        self.map.grid,
        self.tileSize
    )

    if hit is not None:
        pygame.draw.circle(
            self.DRAWTO,
            (255, 0, 0),
            hit - self.cameraPosDelta,
            6
        )
    else:
        end = ray_origin + direction * 2000
        pygame.draw.line(
            self.DRAWTO,
            (0, 255, 0),
            ray_origin - self.cameraPosDelta,
            end - self.cameraPosDelta,
            2
        )
