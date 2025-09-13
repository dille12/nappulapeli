from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from pygame.math import Vector2 as v2
import threading
import random

def tickShops(self: "Game"):
    if self.teamInspectIndex != -1:
        t = self.fontLarge.render(f"TIIMI {self.teamInspectIndex + 1}", True, self.getTeamColor(self.teamInspectIndex))
        self.screen.blit(t, v2(self.res[0]/2, 100) - v2(t.get_size())/2)

        FULL_NPC_TEAM = True
        for x in self.pawnHelpList:
            if x.team.i == self.teamInspectIndex:
                if not x.NPC:
                    FULL_NPC_TEAM = False
                    break
        if FULL_NPC_TEAM:
            self.shops[self.teamInspectIndex].autoBuyForTeam()
            self.advanceShop()


        if self.shops[self.teamInspectIndex].draw():
            self.advanceShop()

        underMouse = None
        for x in self.pawnHelpList:
            if x.GENERATING:
                continue
            if x.team.i != self.teamInspectIndex:
                continue
            
            x.renderInfo()

            if x.hitBox.collidepoint(self.mouse_pos):
                underMouse = x

        if self.weaponButtonClicked:
            w = self.weaponButtonClicked
            self.screen.blit(w.weapon.shopIcon, w.weaponPos - [w.weapon.shopIcon.get_width()/2, w.weapon.shopIcon.get_height()/2])

            if "mouse0" in self.keypress and underMouse:
                w.weapon.give(underMouse)
                self.weaponButtonClicked.outOfStock = True
                self.weaponButtonClicked = None

                self.shops[self.teamInspectIndex].totalPrice[0] += w.weapon.price[0]
                self.shops[self.teamInspectIndex].totalPrice[1] += w.weapon.price[1]
    
    if self.teamInspectIndex == -1:
        t = threading.Thread(target=self.initiateGame)
        t.daemon = True
        t.start()
        self.GAMESTATE = "loadingScreen"

def judgementTick(self: "Game"):
    self.judgementTime += self.deltaTime
    t1 = None
    t2 = None

    if self.judgementIndex >= len(self.judgements):
        self.pregametick = "shop"
        self.judgementIndex = 0
        self.judgementTime = 0
        self.teamInspectIndex = 0
        self.judgementPhase = "nextup"
        return

    if self.judgementPhase == "nextup":
        pawn, title, message = self.judgements[self.judgementIndex]
        t1 = self.fontLarge.render(f"Seuraavana: {title}", True, [255]*3)
        self.screen.blit(t1, v2(self.res[0]/2, 200) - v2(t1.get_size())/2)

        if self.judgementTime > 5:
            self.judgementPhase = "reveal"
            self.judgementTime = 0
            self.podiumPawn = pawn
            for x in self.pawnHelpList:
                x.pickWalkingTarget()
            self.horn.play()
            self.judgementDrinkTime = random.uniform(5, 30)

    elif self.judgementPhase == "reveal":
        pawn, title, message = self.judgements[self.judgementIndex]
        t1 = self.fontLarge.render(title, True, [255]*3)
        t2 = self.font.render(f"{pawn.name}{message}", True, [255]*3)
        t3 = self.font.render(f"Rangaistus: {self.judgementDrinkTime:.0f} sekuntia", True, [255]*3)
        self.screen.blit(t1, v2(self.res[0]/2, 200) - v2(t1.get_size())/2)
        self.screen.blit(t2, v2(self.res[0]/2, 300) - v2(t2.get_size())/2)
        self.screen.blit(t3, v2(self.res[0]/2, 350) - v2(t3.get_size())/2)
        if self.judgementTime > 5:
            self.judgementPhase = "drink"
            self.judgementTime = 0
            
            

    elif self.judgementPhase == "drink":
        pawn, title, message = self.judgements[self.judgementIndex]
        t1 = self.fontLarge.render("JUO!", True, [255,0,0])
        t2 = self.fontLarge.render(f"{pawn.name} juo ({int(self.judgementDrinkTime - self.judgementTime)}s)", True, [255]*3)
        self.screen.blit(t1, v2(self.res[0]/2, 200) - v2(t1.get_size())/2)
        self.screen.blit(t2, v2(self.res[0]/2, 300) - v2(t2.get_size())/2)

        if self.judgementTime > self.judgementDrinkTime:
            self.judgementIndex += 1
            self.judgementTime = 0
            self.judgementPhase = "nextup"
            self.podiumPawn = None
            for x in self.pawnHelpList:
                x.pickWalkingTarget()



def preGameTick(self: "Game"):
    self.PEACEFUL = True
    self.cameraPosDelta = v2([0,0])
    entities_temp = sorted(self.ENTITIES, key=lambda x: x.pos.y)
    self.DRAWTO = self.screen
    self.DRAWTO.fill((0,0,0))

            
    for x in entities_temp:
        x.tick()
        x.render()


    if self.pregametick == "judgement":
        judgementTick(self)

    
    if self.pregametick == "shop":
        tickShops(self)
    
    self.particle_system.update_all()
    self.particle_system.render_all(self.DRAWTO)

    
    self.debugText(f"FPS: {self.FPS:.0f}")
    self.debugText(f"GEN: {self.pawnGenI:.0f}")
    self.debugText(f"ENT: {len(self.ENTITIES):.0f}")
    self.debugText(f"BENT: {len(self.particle_list):.0f}")
    self.debugText(f"CAM: {self.cameraPosDelta}")
    self.debugText(f"PLU: {self.pendingLevelUp}")
    self.debugText(f"IDLE: {100*(1-self.t1/self.t2):.0f}")
    self.debugText(f"INSP: {self.teamInspectIndex}")
    
    self.genPawns()