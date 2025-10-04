from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from pygame.math import Vector2 as v2
import pygame
import time


def announceVictory(self: "Game", victoryTeam):
    #print(f"Team {i+1} WON")
    self.victoryTeam = victoryTeam
    self.VICTORY = True 
    self.points = []

    self.nextMusic = -1

    for x in self.pawnHelpList:
        points, reason_str = x.evaluatePawn()
        self.points.append((x, points, reason_str))

    self.points.sort(key=lambda x: x[1], reverse=True)

def battleTick(self: "Game"):

    self.PEACEFUL = False
    self.BFGLasers = []

    # Sort entities by their y position for correct rendering order into a separate list to prevent modifying the list while iterating

    #if self.skull:
    #    self.cameraPos = self.skull.pos - self.res/2
    if not self.VICTORY:

        if self.GAMEMODE == "ODDBALL":

            victoryCondition = self.skullTimes

            for i, x in enumerate(self.skullTimes):
                if x >= self.skullVictoryTime:
                    #print(f"Team {i+1} WON")
                    announceVictory(self, i)
                    break

        elif self.GAMEMODE == "TEAM DEATHMATCH":
            victoryCondition = [0 for _ in range(self.teams)]
            for p in self.pawnHelpList:
                victoryCondition[p.team.i] += p.kills
            
            for i, x in enumerate(victoryCondition):
                if x >= 200:
                    announceVictory(self, i)
                    break
        
        elif self.GAMEMODE == "1v1":
            victoryCondition = [0 for _ in range(len(self.duelPawns))]
            for i, p in enumerate(self.duelPawns):
                victoryCondition[i] = p.kills
            
            for i, x in enumerate(victoryCondition):
                if x >= 10:
                    announceVictory(self, self.duelPawns[i].team.i)
                    break

        elif self.GAMEMODE == "TURF WARS":
            victoryCondition = [0 for _ in range(self.teams)]
            for r in self.map.rooms:
                if r.turfWarTeam is not None:
                    victoryCondition[r.turfWarTeam] += 1
            
            for i, x in enumerate(victoryCondition):
                if x == len(self.map.rooms):
                    announceVictory(self, i)
                    break
                    
                
        
                
    self.roundTime = max(0, self.roundTime)

    entities_temp = sorted(self.ENTITIES, key=lambda x: x.pos.y)
    if self.GAMEMODE == "1v1":
        for x in self.pawnHelpList:
            if x in self.duelPawns:
                continue
            x.respawnI = 5
            x.killed = True


    self.CREATEDUAL = False
    self.handleCameraLock()
    self.handleCameraSplit()
    #self.handleUltingCall()

    self.deltaTime *= self.SLOWMO

    if not self.VICTORY:
        self.roundTime -= self.deltaTime
        if self.roundTime <= 0:
            # Pick out from the victoryCondition the highest index
            max_index = victoryCondition.index(max(victoryCondition))
            announceVictory(self, max_index)

    
    


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

    

    for x in entities_temp:
        x.tick()

    for x in self.visualEntities:
        x.tick()

    for x in self.bloodSplatters:
        x.tick()

    if self.GAMEMODE == "TURF WARS":
        for r in self.map.rooms:
            CONTESTED = False
            if len(r.pawnsPresent) > 0:
                unique_teams = set(r.pawnsPresent)
                if len(unique_teams) == 1:
                    teamOccupied = unique_teams.pop()
                    if r.turfWarTeam != teamOccupied:
                        CONTESTED = True
                        
                    
                    #print("Room occupied by:", r.turfWarTeam)
            
            if not CONTESTED:
                r.occupyI += self.deltaTime
                r.occupyI = min(5, r.occupyI)
            else:
                r.occupyI -= self.deltaTime * min(1, len(r.pawnsPresent))
                if r.occupyI <= 0:
                    #if r in self.teamSpawnRooms:
                    #    spawnTeam = self.teamSpawnRooms.index(r)
                    #    for p in self.pawnHelpList:
                    #        if p.originalTeam == spawnTeam:
                    #            p.team = teamOccupied
                    #            p.enslaved = spawnTeam != teamOccupied
                    #    print("Teams spawn point captured")
                    
                    r.turfWarTeam = teamOccupied


    if self.objectiveCarriedBy:
        self.skullTimes[self.objectiveCarriedBy.team.i] += self.deltaTime

    if self.splitI > 0:
        self.cameraPos = self.posToTargetTo.copy()
        self.dualCameraPos = self.posToTargetTo2.copy()
    else:
        self.dualCameraPos = self.cameraPos.copy()

    CAMPANSPEED = 500000 * self.deltaTimeR
    #self.cameraVel[0] += self.smoothRotationFactor(self.cameraVel[0], CAMPANSPEED, self.cameraPos[0] - self.cameraPosDelta[0]) * self.deltaTimeR
    #self.cameraVel[1] += self.smoothRotationFactor(self.cameraVel[1], CAMPANSPEED, self.cameraPos[1] - self.cameraPosDelta[1]) * self.deltaTimeR
    #self.cameraPosDelta = self.cameraPosDelta * 0.9 + self.cameraPos * 0.1#* self.deltaTimeR
    #self.cameraPosDelta += self.cameraVel * self.deltaTimeR

    self.CAMERA.update(self.cameraPos, self.deltaTimeR, smooth_time=0.25)
    self.cameraPosDelta = self.CAMERA.pos

    self.cleanUpLevel()

    DUAL = False
    if self.splitI > 0:
        if self.cameraLockOrigin.distance_to(self.cameraLockTarget) > 600:
            DUAL = True

    self.DUALVIEWACTIVE = DUAL


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
        #self.renderParallax2()
        #self.DRAWTO.blit(self.wall_mask, -self.cameraPosDelta)
        self.drawTurfs()

        #if self.cameraLock:
        #    self.cameraLock.visualizeVis()

        for x in self.shitDict.values():
            x.render()

        for x in entities_temp:
            x.render()

        for x in self.visualEntities:
            x.render()

        self.drawBFGLazers()

        self.particle_system.render_all(self.DRAWTO)

        

        if DUAL and i == 1:
            self.cameraPosDelta = SAVECAMPOS.copy()

    if DUAL:
        self.splitScreen()
        

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
            self.endGame()
            return
    else:
        pass
        self.tickScoreBoard()

    if not self.VICTORY:
        self.drawRoundInfo()

    ox, oy = self.MINIMAPCELLSIZE*self.cameraPosDelta/(self.tileSize)
    w, h = self.MINIMAPCELLSIZE*self.res/(self.tileSize)
    
    pygame.draw.rect(self.MINIMAPTEMP, [255,0,0], (ox, oy, w, h), width=1)


    if self.skull:
        if self.objectiveCarriedBy:
            skullpos = self.objectiveCarriedBy.pos.copy()
        else:
            skullpos = self.skull.pos.copy()

        pygame.draw.circle(self.MINIMAPTEMP, [255,255,255], self.MINIMAPCELLSIZE*skullpos/self.tileSize, 6, width=1)
    
    self.screen.blit(self.MINIMAPTEMP, self.res - self.MINIMAP.get_size() - [10,10])

    self.handleHud()



    if self.pendingLevelUp and not self.VICTORY:
        self.levelUpScreen()
    else:
        self.resetLevelUpScreen()

    if self.ultFreeze > 0:
        self.handleUlting()

    self.debugText(f"FPS: {self.FPS:.0f}")
    self.debugText(f"MAXFR: {self.MAXFRAMETIME*1000:.1f}ms")
    self.debugText(f"GEN: {self.pawnGenI:.0f}")
    self.debugText(f"SOUNDS: {len(self.AUDIOMIXER.audio_sources):.0f}")
    self.debugText(f"SOUND TIME: {self.AUDIOMIXER.callBackTime*1000:.1f}ms")
    self.debugText(f"ONSCREEN: {onscreen}")
    
    #self.genPawns()
