from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from pygame.math import Vector2 as v2
import threading


def preGameTick(self: "Game"):
    self.PEACEFUL = True
    self.cameraPosDelta = v2([0,0])
    entities_temp = sorted(self.ENTITIES, key=lambda x: x.pos.y)
    self.DRAWTO = self.screen
    self.DRAWTO.fill((0,0,0))

            

            
    for x in entities_temp:
        x.tick()
        x.render()
    
    
    self.particle_system.update_all()
    self.particle_system.render_all(self.DRAWTO)

    if self.teamInspectIndex != -1:
        t = self.fontLarge.render(f"TIIMI {self.teamInspectIndex + 1}", True, self.getTeamColor(self.teamInspectIndex))
        self.screen.blit(t, v2(self.res[0]/2, 100) - v2(t.get_size())/2)

        if self.shops[self.teamInspectIndex].draw():
            self.advanceShop()
            if self.teamInspectIndex == -1:
                t = threading.Thread(target=self.initiateGame)
                t.daemon = True
                t.start()
                self.GAMESTATE = "loadingScreen"

        underMouse = None
        for x in self.pawnHelpList:
            if x.team != self.teamInspectIndex:
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


    self.debugText(f"FPS: {self.FPS:.0f}")
    self.debugText(f"GEN: {self.pawnGenI:.0f}")
    self.debugText(f"ENT: {len(self.ENTITIES):.0f}")
    self.debugText(f"BENT: {len(self.particle_list):.0f}")
    self.debugText(f"CAM: {self.cameraPosDelta}")
    self.debugText(f"PLU: {self.pendingLevelUp}")
    self.debugText(f"IDLE: {100*(1-self.t1/self.t2):.0f}")
    self.debugText(f"INSP: {self.teamInspectIndex}")
    
    self.genPawns()