from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from core.dropDown import Dropdown
from core.button import Button
def createSettings(self: "Game"):
    self.npcType = Dropdown(self, "Mode:", ["PVE", "PVP", "PVPE"], (300,400))
    self.teamAmount = Dropdown(self, "Teams:", ["2", "3", "4", "5", "6", "7", "8"], (550,400))
    self.loadedMusic = None
    self.musicChoice = Dropdown(self, "Music:", ["Bablo", "HH"], (800,400))

    self.playButton = Button(self, (1600,850), (250,120))

def settingsTick(self: "Game"):
    self.screen.fill((0,0,0))
    t = self.fontLarge.render("ASETUKSET", True, [255]*3)
    self.screen.blit(t, [self.res[0]/2-t.get_width()/2, 200])
    
    self.npcType.tick()
    self.teamAmount.tick()
    self.musicChoice.tick()

    self.teams = int(self.teamAmount.get_selected())

    if self.loadedMusic != self.musicChoice.get_selected():

        if self.music:
            for x in self.music:
                x.stop()

        if self.musicChoice.get_selected() == "Bablo":
            self.music = self.loadSound("audio/bar")
            
        elif self.musicChoice.get_selected() == "HH":
            self.music = self.loadSound("audio/hh/bar")
    
    self.loadedMusic = self.musicChoice.get_selected()

    if self.playButton.draw(self.screen, "Peliä", font = self.fontLarge):
        self.GAMESTATE = "pawnGeneration"
        self.refreshShops()
        self.reTeamPawns()

    self.genPawns()