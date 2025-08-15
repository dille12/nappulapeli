from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from core.dropDown import Dropdown
from core.button import Button
from core.ipManager import get_local_ip
import random
import os
def createSettings(self: "Game"):
    self.npcType = Dropdown(self, "Mode:", ["PVE", "PVP", "PVPE"], (300,400))
    self.teamAmount = Dropdown(self, "Player Teams:", ["1", "2", "3", "4", "5", "6", "7", "8"], (100,600))
    self.npcTeamAmount = Dropdown(self, "NPC Teams:", ["0", "1", "2", "3", "4", "5", "6", "7", "8"], (350,600))
    self.teamFill = Dropdown(self, "Fill teams to:", ["1", "2", "3", "4", "5", "6", "7", "8"], (600,600))


    self.loadedMusic = None
    self.musicChoice = Dropdown(self, "Music:", ["Bablo", "HH"], (550,400))
    self.ttsToggle = Dropdown(self, "TTS:", ["On", "Off"], (800,400))

    self.itemToggle = Dropdown(self, "Items:", ["Manual", "Auto"], (1050,400))
    self.roundLength = Dropdown(self, "Round Length:", ["0:30", "3:00", "5:00", "10:00"], (1550,400))

    self.playButton = Button(self, (1600,850), (250,120))
    self.giveRandomWeapons = Button(self, (1600,750), (200,40))
    self.toggleServer = Button(self, (200,850), (200,40))
    self.SimpleServerController = SimpleServerController()

def settingsTick(self: "Game"):
    self.screen.fill((0,0,0))


    self.reTeamPawns()
    teamIndices = []
    for i in range(self.teams):
        teamIndices.append(0)

    for i, pawn in enumerate(self.pawnHelpList):
        x = 900 + pawn.team * 100

        y = 550 + 30*teamIndices[pawn.team]
        teamIndices[pawn.team] += 1

        t = self.fontSmaller.render(pawn.name, True, self.getTeamColor(pawn.team))
        self.screen.blit(t, (x,y))

    

    t = self.fontLarge.render("ASETUKSET", True, [255]*3)
    self.screen.blit(t, [self.res[0]/2-t.get_width()/2, 200])
    
    self.npcType.tick()
    self.teamAmount.tick()
    self.musicChoice.tick()
    self.ttsToggle.tick()
    self.itemToggle.tick()
    self.roundLength.tick()
    self.npcTeamAmount.tick()
    self.teamFill.tick()

    s = self.roundLength.get_selected()
    if s == "0:30":
        self.MAXROUNDLENGTH = 30
    elif s == "3:00":
        self.MAXROUNDLENGTH = 180
    elif s == "5:00":
        self.MAXROUNDLENGTH = 300
    elif s == "10:00":
        self.MAXROUNDLENGTH = 600


    self.teams = int(self.teamAmount.get_selected()) + int(self.npcTeamAmount.get_selected())
    self.playerTeams = int(self.teamAmount.get_selected())
    self.fillTeamsTo = int(self.teamFill.get_selected())
    self.teamsSave = self.teams
    self.TTS_ON = self.ttsToggle.get_selected() == "On"
    self.ITEM_AUTO = self.itemToggle.get_selected() == "Auto"

    if self.loadedMusic != self.musicChoice.get_selected():

        if self.music:
            for x in self.music:
                x.stop()

        if self.musicChoice.get_selected() == "Bablo":
            self.music = self.loadSound("audio/bar", volume=0.5)
            
        elif self.musicChoice.get_selected() == "HH":
            self.music = self.loadSound("audio/hh/bar", volume=0.5)

    self.loadedMusic = self.musicChoice.get_selected()


    serverOn = self.SimpleServerController.process and self.SimpleServerController.process.poll() is None
    
    if serverOn:
        ip = get_local_ip()

    t = self.font.render(f"Servu päällä ({ip}:5000)" if serverOn else "Servu pois päältä", True, [255,255,255])
    self.screen.blit(t, (200, 900))

    if self.toggleServer.draw(self.screen, "Käynnistä serveri" if not serverOn else "Lopeta serveri", font = self.font):
        self.SimpleServerController.toggle_server()

    if self.giveRandomWeapons.draw(self.screen, "Anna aseita", font = self.font):
        for pawn in self.pawnHelpList:
            w = random.choice(self.weapons)
            w.give(pawn)

    if self.playButton.draw(self.screen, "Peliä", font = self.fontLarge):
        self.GAMESTATE = "pawnGeneration"

        npcsToAdd =  (self.teams - self.playerTeams) * self.fillTeamsTo
        for x in range(npcsToAdd):
            for x in os.listdir("npcs/"):
                if x not in self.playerFiles and (x, False) not in self.playerFilesToGen:
                    print(x, "Adding npc")
                    self.playerFilesToGen.append((x, False))
                    break

        self.refreshShops()
        self.reTeamPawns()
        self.SimpleServerController.stop_server()
        

    self.genPawns()


# Alternative simpler approach using subprocess
import subprocess
import sys

class SimpleServerController:
    def __init__(self):
        self.process = None
        
    def start_server(self):
        """Start server as subprocess"""
        if self.process and self.process.poll() is None:
            print("Server already running!")
            return False
            
        self.process = subprocess.Popen([
            sys.executable, '-c', 
            'from hostsite import run; run()'
        ])
        print("Server started!")
        return True
        
    def stop_server(self):
        """Stop the server subprocess"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            print("Server stopped!")
            return True
        else:
            print("Server not running!")
            return False
            
    def toggle_server(self):
        """Toggle server on/off"""
        if self.process and self.process.poll() is None:
            return self.stop_server()
        else:
            return self.start_server()