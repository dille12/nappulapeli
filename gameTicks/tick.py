from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from pygame.math import Vector2 as v2
import pygame
import time

def battleTick(self: "Game"):

    self.PEACEFUL = False
    self.BFGLasers = []

    # Sort entities by their y position for correct rendering order into a separate list to prevent modifying the list while iterating

    #if self.skull:
    #    self.cameraPos = self.skull.pos - self.res/2
    if not self.VICTORY:
        for i, x in enumerate(self.skullTimes):
            if x >= self.skullVictoryTime:
                #print(f"Team {i+1} WON")
                self.victoryTeam = i
                self.VICTORY = True 
                self.points = []

                self.nextMusic = -1

                for x in self.pawnHelpList:
                    points, reason_str = x.evaluatePawn()
                    self.points.append((x, points, reason_str))

                self.points.sort(key=lambda x: x[1], reverse=True)

                    
                
    
    

    entities_temp = sorted(self.ENTITIES, key=lambda x: x.pos.y)
    self.CREATEDUAL = False
    self.handleCameraLock()
    self.handleCameraSplit()

    
    


    self.MINIMAPTEMP = self.MINIMAP.copy()
    self.particle_system.update_all()

    for x in entities_temp:
        x.tick()

    for x in self.visualEntities:
        x.tick()

    for x in self.bloodSplatters:
        x.tick()


    if self.objectiveCarriedBy:
        self.skullTimes[self.objectiveCarriedBy.team] += self.deltaTime

    if self.splitI > 0:
        self.cameraPos = self.posToTargetTo.copy()
        self.dualCameraPos = self.posToTargetTo2.copy()
    else:
        self.dualCameraPos = self.cameraPos.copy()

    CAMPANSPEED = 500000 * self.deltaTimeR
    #self.cameraVel[0] += self.smoothRotationFactor(self.cameraVel[0], CAMPANSPEED, self.cameraPos[0] - self.cameraPosDelta[0]) * self.deltaTimeR
    #self.cameraVel[1] += self.smoothRotationFactor(self.cameraVel[1], CAMPANSPEED, self.cameraPos[1] - self.cameraPosDelta[1]) * self.deltaTimeR
    self.cameraPosDelta = self.cameraPosDelta * 0.9 + self.cameraPos * 0.1#* self.deltaTimeR

    self.cleanUpLevel()

    DUAL = False
    if self.splitI > 0:
        if self.cameraLockOrigin.distance_to(self.cameraLockTarget) > 600:
            DUAL = True


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
        #self.DRAWTO.blit(self.wall_mask, -self.cameraPosDelta)

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
        

    if self.currMusic == 0:
        t = self.fontLarge.render(f"Peli alkaa: {self.musicLength - (time.time()-self.musicStart):.0f}", True, [255,255,255])
        self.screen.blit(t, v2(self.res[0]/2, 300) - v2(t.get_size())/2)
                    

    #self.drawWalls()

    self.debugText(f"FPS: {self.FPS:.0f}")
    self.debugText(f"GEN: {self.pawnGenI:.0f}")
    self.debugText(f"ENT: {len(self.ENTITIES):.0f}")
    self.debugText(f"BENT: {len(self.particle_list):.0f}")
    self.debugText(f"CAM: {self.cameraPosDelta}")
    self.debugText(f"PLU: {self.pendingLevelUp}")
    self.debugText(f"IDLE: {100*(1-self.t1/self.t2):.0f}")
    self.debugText(f"DUAL: {DUAL} {self.CREATEDUAL}")
    self.debugText(f"BLOOD: {self.bloodClearI}")
    self.debugText(f"SPE: {self.speeches}")
    
    onscreen = 0
    for x in self.pawnHelpList:
        if x.onScreen():
            onscreen += 1
    self.debugText(f"ONSCREEN: {onscreen}")

    for x in self.killfeed:
        x.tick()

    
    if self.VICTORY:
        if self.currMusic == -1:
            self.tickEndGame()
        if self.endGameI <= 0 and self.currMusic == 0:
            self.endGame()
            return
    else:
        self.tickScoreBoard()


    


    ox, oy = self.MINIMAPCELLSIZE*self.cameraPosDelta/(70)
    w, h = self.MINIMAPCELLSIZE*self.res/(70)
    
    pygame.draw.rect(self.MINIMAPTEMP, [255,0,0], (ox, oy, w, h), width=1)

    if self.objectiveCarriedBy:
        skullpos = self.objectiveCarriedBy.pos.copy()
    else:
        skullpos = self.skull.pos.copy()

    pygame.draw.circle(self.MINIMAPTEMP, [255,255,255], self.MINIMAPCELLSIZE*skullpos/70, 6, width=1)
    
    self.screen.blit(self.MINIMAPTEMP, self.res - self.MINIMAP.get_size() - [10,10])

    self.handleHud()



    if self.pendingLevelUp and not self.VICTORY:
        self.levelUpScreen()
    else:
        self.resetLevelUpScreen()


    
    #self.genPawns()
