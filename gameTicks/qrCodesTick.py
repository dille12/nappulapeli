from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from core.dropDown import Dropdown
from core.button import Button
from core.ipManager import get_local_ip
import random
import os
from core.qrcodeMaker import make_qr_surface
from pawn.teamLogic import Team

def createQRS(self: "Game"):
    ip = get_local_ip()
    t = "IP: " + ip
    t = self.font.render(t, True, [255]*3)

    self.QRtoAPP = make_qr_surface(f"https://github.com/dille12/nappulapeli-app/releases", 4)

    self.WIFIQR = make_qr_surface(f"WIFI:S:nappulapeli;T:WPA;P:nappulapeli1234;;", 4)

    self.goToSettingsButton = Button(self, (1600,850), (250,120))

def qrCodesTick(self: "Game"):
    self.screen.fill((0,0,0))

    t = self.fontLarge.render("CONNECT TO THE SERVER", True, [255]*3)
    self.screen.blit(t, [self.res[0]/2-t.get_width()/2, 100])


    x = self.res.x/3

    t = "APP DOWNLOAD"
    t = self.font.render(t, True, [255]*3)
    self.screen.blit(t, (x-t.get_width()/2, 400))
    self.screen.blit(self.QRtoAPP, (x-self.QRtoAPP.get_width()/2, 500))

    x = 2*self.res.x/3

    t = "CONNECT TO WIFI"
    t = self.font.render(t, True, [255]*3)
    self.screen.blit(t, (x-t.get_width()/2, 400))

    SSID = "TP-LINK_58B1_5G"
    PASSWORD = "90073946"

    t = self.font.render(SSID, True, [255]*3)
    self.screen.blit(t, (x-t.get_width()/2, 500))

    t = self.font.render(PASSWORD, True, [255]*3)
    self.screen.blit(t, (x-t.get_width()/2, 550))

    #self.screen.blit(t, (x-t.get_width()/2, 400))
    #self.screen.blit(self.WIFIQR, (x-self.WIFIQR.get_width()/2, 500))
    #self.genPawns()
    if self.goToSettingsButton.draw(self.screen, "Settings", font = self.fontLarge):
        self.GAMESTATE = "settings"