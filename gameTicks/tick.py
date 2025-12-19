from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
from pygame.math import Vector2 as v2
import pygame
import time
#from core.AI import constructTeamVisibility, drawGridMiniMap
import math
from utilities.bullet import raycast_grid
from core.drawRectPerimeter import draw_rect_perimeter
def battleTick(self: "Game"):

    self.PEACEFUL = False
    self.BFGLasers = []

    self.debugCells = []

    # Sort entities by their y position for correct rendering order into a separate list to prevent modifying the list while iterating

    #if self.skull:
    #    self.cameraPos = self.skull.pos - self.res/2
    if not self.VICTORY:

        if self.GAMEMODE == "ODDBALL":

            victoryCondition = self.skullTimes

            for i, x in enumerate(self.skullTimes):
                if x >= self.skullVictoryTime:
                    #print(f"Team {i+1} WON")
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
        
        elif self.GAMEMODE == "DETONATION":
            victoryCondition = [0 for _ in range(2)]
            if self.SITES:
                if len(self.SITES) == 1:
                    victoryCondition[1] = 1 # TIE
                    victoryCondition[0] = 1
                else:
                    victoryCondition[1] = 1
                
            else:
                victoryCondition[0] = 1
                self.announceVictory(0)

        elif self.GAMEMODE == "SUDDEN DEATH":
            alive = [0] * self.teams

            for p in self.getActualPawns():
                if not p.killed:
                    alive[p.team.i] += 1

            alive_teams = [i for i, n in enumerate(alive) if n > 0]

            if len(alive_teams) == 1:
                self.announceVictory(alive_teams[0])
                
                    
                
        
                
    self.roundTime = max(0, self.roundTime)

    entities_temp = sorted(self.ENTITIES, key=lambda x: x.pos.y)
    if self.GAMEMODE == "1v1":
        for x in self.pawnHelpList:
            if x in self.duelPawns:
                continue
            x.respawnI = 5
            x.killed = True


    self.CREATEDUAL = False

    if not self.MANUALPAWN:
        if self.AUTOCAMERA:
            self.handleCameraLock()
            self.handleCameraSplit()
    else:
        self.handleCameraManual()


    combat = any(
            p.target or p.grenadePos
            for p in self.pawnHelpList
        ) or self.bombPlanted()
    
    if not combat and self.GAMEMODE != "FINAL SHOWDOWN" and not self.VICTORY:
        self.fastForwardI += self.deltaTimeR
        self.fastForwardI = min(3, self.fastForwardI)
    else:
        self.fastForwardI -= self.deltaTimeR * 5
        self.fastForwardI = max(0, self.fastForwardI)

    FF = max(1, self.fastForwardI)
    
    TIMESCALE = self.TIMESCALE * FF


    #self.handleUltingCall()

    self.deltaTime *= self.SLOWMO
    self.deltaTime *= TIMESCALE

    if not self.VICTORY:

        if self.GAMEMODE == "FINAL SHOWDOWN":
            if self.currMusic == 1:
                self.roundTime -= self.deltaTime
            victoryCondition = list(self.BABLO.damageTakenPerTeam.values())

        elif self.GAMEMODE == "DETONATION":
            if not self.skull.planted:
                self.roundTime -= self.deltaTime

        else:

            self.roundTime -= self.deltaTime
        if self.roundTime <= 0:
            # Pick out from the victoryCondition the highest index
            max_index = victoryCondition.index(max(victoryCondition))
            
            if self.GAMEMODE == "DETONATION":
                if victoryCondition[0] == victoryCondition[1]:
                    max_index = -1
            self.announceVictory(max_index)

    
    

    #self.MINIMAP = self.map.to_pygame_surface(cell_size=self.MINIMAPCELLSIZE)
    self.MINIMAPTEMP = self.MINIMAP.copy()

    

    self.particle_system.update_all()


    if self.GAMEMODE == "TURF WARS":
        for r in self.map.rooms:
            r.pawnsPresent = []
            if r.turfWarTeam is not None:
                pygame.draw.rect(self.MINIMAPTEMP, self.getTeamColor(r.turfWarTeam, 0.25), (r.x*self.MINIMAPCELLSIZE, r.y*self.MINIMAPCELLSIZE, 
                                                                                      r.width*self.MINIMAPCELLSIZE, r.height*self.MINIMAPCELLSIZE))
                
            if r in self.teamSpawnRooms:
                i = self.teamSpawnRooms.index(r)
                r2 = self.teamSpawnRooms[i]
                pygame.draw.rect(self.MINIMAPTEMP, self.getTeamColor(i, 1), (r2.x*self.MINIMAPCELLSIZE, r2.y*self.MINIMAPCELLSIZE, 
                                                                                      r2.width*self.MINIMAPCELLSIZE, r2.height*self.MINIMAPCELLSIZE), width=1)
                
    if self.GAMEMODE == "DETONATION":

        

        for site in self.SITES:

            pos = v2(site.room.center())*self.MINIMAPCELLSIZE
            t = self.fontSmaller.render(site.name, True, [155,0,0])
            self.MINIMAPTEMP.blit(t, pos - v2(t.get_size())/2)
            room = site.room
            rect = pygame.Rect(room.x*self.MINIMAPCELLSIZE, room.y*self.MINIMAPCELLSIZE, room.width*self.MINIMAPCELLSIZE, room.height*self.MINIMAPCELLSIZE)
            color = [255,0,0] if site == self.allTeams[0].getCurrentSite() else [255,255,255]
            draw_rect_perimeter(self.MINIMAPTEMP, rect, time.time()-self.now, 20, 2, color, width=1)




        #    color = [51,42,13] if site.controlledByT() else [15, 26, 51]
        #    r = site.room
        #    pygame.draw.rect(self.MINIMAPTEMP, color, (r.x*self.MINIMAPCELLSIZE, r.y*self.MINIMAPCELLSIZE, 
        #                                                                              r.width*self.MINIMAPCELLSIZE, r.height*self.MINIMAPCELLSIZE))
    #constructTeamVisibility(self)
        

    self.FireSystem.update()

    if self.GAMEMODE == "DETONATION":
        for x in self.SITES:
            x.tickSite()

        self.allTeams[0].tickDetonation()
        self.allTeams[-1].tickDetonation()

    for x in self.allTeams:
        x.tickNadePos()

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

    if self.AUTOCAMERA:
        if self.splitI > 0:
            self.cameraPos = self.posToTargetTo.copy()
            self.dualCameraPos = self.posToTargetTo2.copy()
        else:
            self.dualCameraPos = self.cameraPos.copy()
    else:
        if "w" in self.keypress_held_down:
            self.cameraPos.y -= 10
        elif "s" in self.keypress_held_down:
            self.cameraPos.y += 10

        if "a" in self.keypress_held_down:
            self.cameraPos.x -= 10
        elif "d" in self.keypress_held_down:
            self.cameraPos.x += 10

    CAMPANSPEED = 500000 * self.deltaTimeR
    #self.cameraVel[0] += self.smoothRotationFactor(self.cameraVel[0], CAMPANSPEED, self.cameraPos[0] - self.cameraPosDelta[0]) * self.deltaTimeR
    #self.cameraVel[1] += self.smoothRotationFactor(self.cameraVel[1], CAMPANSPEED, self.cameraPos[1] - self.cameraPosDelta[1]) * self.deltaTimeR
    #self.cameraPosDelta = self.cameraPosDelta * 0.9 + self.cameraPos * 0.1#* self.deltaTimeR
    #self.cameraPosDelta += self.cameraVel * self.deltaTimeR

    self.CAMERA.update(self.cameraPos, self.deltaTimeR, smooth_time=0.1)
    self.cameraPosDelta = self.CAMERA.pos.copy()
    self.AUDIOORIGIN = self.cameraPosDelta.copy() + self.res/2

    self.cleanUpLevel()

    DUAL = False
    if self.splitI > 0:
        
        angle = self.getAngleFrom(self.cameraLockOrigin, self.cameraLockTarget) + math.pi/2

        max_dist = 300 + 300 * abs(math.sin(angle))   # ensures 300–600 range

        if self.cameraLockOrigin.distance_to(self.cameraLockTarget) > max_dist and self.cameraLock and not self.cameraLock.BOSS:
            DUAL = True

    self.DUALVIEWACTIVE = DUAL

    if self.RENDERING:
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
                self.cameraPosDelta = self.posToTargetTo2.copy()

            self.DRAWTO.blit(self.MAP, -self.cameraPosDelta)

            if self.SLOWMO_FOR > 0 and not self.BABLO.killed:
                alpha = int(255 * min(max(self.SLOWMO_FOR * 2, 0.5), 1.0))
                self.speedLinesSurf.fill((0, 0, 0, alpha))
                self.speedlines.draw(self.speedLinesSurf, self.BABLO.pos - self.cameraPosDelta)
                self.DRAWTO.blit(self.speedLinesSurf, (0,0))

            #self.renderParallax2()
            #self.DRAWTO.blit(self.wall_mask, -self.cameraPosDelta)
            self.drawTurfs()
            self.drawDetonation()

            #if self.cameraLock:
            #    self.cameraLock.visualizeVis()

            

            for x in self.shitDict.values():
                x.render()

            self.FireSystem.draw(self.DRAWTO)

            for x in entities_temp:
                x.render()

            for x in self.visualEntities:
                x.render()

            self.drawBFGLazers()

            for x in self.bulletImpactPositions:
                pygame.draw.circle(self.DRAWTO, [255,0,0], v2(x) - self.cameraPosDelta, 10, )

            self.particle_system.render_all(self.DRAWTO)

            for x in self.debugCells:
                self.highLightCell(x)

            if DUAL and i == 1:
                self.cameraPosDelta = SAVECAMPOS.copy()

        if DUAL:
            self.splitScreen()
    else:
        self.screen.fill((0,0,0))


    
    
        

    #if self.currMusic == 0:
    #    t = self.fontLarge.render(f"Peli alkaa: {self.musicLength - (time.time()-self.musicStart):.0f}", True, [255,255,255])
    #    self.screen.blit(t, v2(self.res[0]/2, 300) - v2(t.get_size())/2)
                    

    #self.drawWalls()


    
    onscreen = 0
    for x in self.pawnHelpList:
        if x.onScreen():
            onscreen += 1
    

    for x in self.killfeed:
        x.tick()

    
    if self.VICTORY:
        if self.endGameI >= 0:
            self.tickEndGame()
        else:
            if not self.TRANSITION:
                self.transition(lambda: self.endGame())
            #self.endGame()
            
    else:
        if self.RENDERING:
            #if self.GAMEMODE != "FINAL SHOWDOWN":
            self.tickScoreBoard()

    if not self.VICTORY:
        if self.GAMEMODE != "DETONATION":
            self.drawRoundInfo()
        else:
            self.drawRoundInfoDetonation()

    ox, oy = self.MINIMAPCELLSIZE*self.cameraPosDelta/(self.tileSize)
    w, h = self.MINIMAPCELLSIZE*self.res/(self.tileSize)
    
    pygame.draw.rect(self.MINIMAPTEMP, [255,0,0], (ox, oy, w, h), width=1)


    if self.skull:
        if self.objectiveCarriedBy:
            skullpos = self.objectiveCarriedBy.pos.copy()
        else:
            skullpos = self.skull.pos.copy()

        pygame.draw.circle(self.MINIMAPTEMP, [255,255,255], self.MINIMAPCELLSIZE*skullpos/self.tileSize, 6, width=1)

    MINIMAP_POS = self.res - self.MINIMAP.get_size() - [10,10]
    
    self.screen.blit(self.MINIMAPTEMP, MINIMAP_POS)


    #t = self.font.render("Points", True, [255,255,255])
    #self.screen.blit(t, [self.res.x - 10 - t.get_width(), MINIMAP_POS.y - 45 - t.get_height()])

    w = self.MINIMAP.get_width()
    h = 40
    w_r = w / len(self.allTeams)
    x = 0

    for team in self.allTeams:

        rect1 = pygame.Rect(MINIMAP_POS + [x, -h], [w_r, h])

        pygame.draw.rect(self.screen, self.getTeamColor(team.i, 0.2), rect1)

        rect2 = rect1.copy()
        rect2.height = (team.wins/self.maxWins) * h
        rect2.bottom = rect1.bottom
        pygame.draw.rect(self.screen, self.getTeamColor(team.i, 0.5), rect2)

        
        pygame.draw.rect(self.screen, self.getTeamColor(team.i, 1), rect1, width=2)
        
        x += w_r

        center = rect1.center
        t = self.font.render(f"{team.wins}", True, [255,255,255])
        self.screen.blit(t, v2(center) - v2(t.get_size())/2)

        if self.winningTeam != None and team == self.winningTeam:
            # draw a yellow crown on top of the rect
            crown_width = w_r * 0.6
            crown_height = h * 0.6
            crown_top = rect1.top - crown_height * 0.8
            crown_center_x = rect1.centerx

            points = [
                (crown_center_x - crown_width/2, rect1.top),                # bottom-left
                (crown_center_x - crown_width/2 - 5, crown_top),                # left spike
                (crown_center_x - crown_width/5, crown_top + crown_height*0.33),
                (crown_center_x, crown_top - crown_height*0.5),                                # middle spike
                (crown_center_x + crown_width/5, crown_top + crown_height*0.33),
                (crown_center_x + crown_width/2 + 5, crown_top),                # right spike
                (crown_center_x + crown_width/2, rect1.top)                 # bottom-right
            ]
            pygame.draw.polygon(self.screen, (255, 255, 0), points)
            pygame.draw.polygon(self.screen, (200, 200, 0), points, width=2)  # outline


    #debugRay(self)

    if self.RENDERING:
        self.handleHud()


    if self.pendingLevelUp and not self.VICTORY:
        self.levelUpScreen()
    else:
        self.resetLevelUpScreen()

    if self.ultFreeze > 0:
        self.handleUlting()

    if FF > 1:
        t = self.fontLarge.render("FAST FORWARDING", True, [255,255,255])

        alpha = 255*(FF-1)/2
        t.set_alpha(int(alpha))

        self.screen.blit(t, self.res/2 - v2(t.get_size())/2)

    if self.roundTime < 4:
        self.nextMusic = -1

    self.debugText(f"FPS: {self.FPS:.0f} (+/-{self.STD*1000:.1f}ms)")
    self.debugText(f"MAXFR: {self.MAXFRAMETIME*1000:.1f}ms")
    self.debugText(f"GEN: {self.pawnGenI:.0f}")
    self.debugText(f"SOUNDS: {len(self.AUDIOMIXER.audio_sources):.0f}")
    self.debugText(f"SOUND TIME: {self.AUDIOMIXER.callBackTime*1000:.1f}ms, ({self.AUDIOMIXER.callBackTime/(self.AUDIOMIXER.chunk_size/self.AUDIOMIXER.sample_rate)*100:.1f}%)")
    self.debugText(f"ONSCREEN: {onscreen}")
    self.debugText(f"MUSIC: {self.currMusic} -> {self.nextMusic}")
    self.debugText(f"CAM: {self.CAMERA.vibration_amp}")
    self.debugText(f"{self.cameraLinger:.2f}")
    if self.cameraLock:
        self.debugText(f"{self.cameraLock.name}")
    else:
        self.debugText(f"{self.cameraLock}")

    if self.GAMEMODE == "DETONATION":
        self.debugText(f"T: {self.allTeams[-1].plan["currentAction"]}, {self.allTeams[-1].plan["planTimer"]:.1f}")
        self.debugText(f"CT: {self.allTeams[0].plan["currentAction"]}, {self.allTeams[0].plan["planTimer"]:.1f}")
        self.debugText(f"Site controlled: {self.allTeams[0].terroristsHoldPlanSite()}")

    if self.GAMEMODE == "TURF WARS":
        for x in self.allTeams:
            self.debugText(f"TEAM {x.i}: {x.enslavedTo}")

    self.debugText(f"ENT: {len(self.pawnHelpList)}, {len([x for x in self.pawnHelpList if not x.isPawn])}")


    #self.drawFPS()
    
    #self.genPawns()


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
