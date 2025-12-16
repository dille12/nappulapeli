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
def createSettings(self: "Game"):
    self.npcType = Dropdown(self, "Mode:", ["PVE", "PVP", "PVPE"], (300,400))
    self.teamAmount = Dropdown(self, "Player Teams:", ["1", "2", "3", "4", "5", "6", "7", "8"], (100,600), initialValue=3)
    self.npcTeamAmount = Dropdown(self, "NPC Teams:", ["0", "1", "2", "3", "4", "5", "6", "7", "8"], (350,600))
    self.teamFill = Dropdown(self, "Fill teams to:", ["1", "2", "3", "4", "5", "6", "7", "8"], (600,600), initialValue=2)


    self.loadedMusic = None
    self.musicChoice = Dropdown(self, "Music:", ["Bablo", "HH" , "Bablo >:)"], (550,400))
    self.ttsToggle = Dropdown(self, "TTS:", ["On", "Off"], (800,400))

    self.itemToggle = Dropdown(self, "Items:", ["Manual", "Auto"], (1050,400), initialValue=1)
    self.roundLength = Dropdown(self, "Round Length:", ["0:30", "3:00", "5:00", "10:00"], (1550,400), initialValue=2)

    self.playButton = Button(self, (1600,850), (250,120))
    self.giveRandomWeapons = Button(self, (1600,750), (200,40))
    self.toggleServer = Button(self, (200,850), (200,40))
    self.SimpleServerController = SimpleServerController()

    ip = get_local_ip()
    
    self.QR = make_qr_surface(f"http://{ip}:5000", 4)
    threading.Thread(target=startServer, args=(self,), daemon=True).start()


def settingsTick(self: "Game"):
    self.screen.fill((0,0,0))

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


    T = int(self.teamAmount.get_selected()) + int(self.npcTeamAmount.get_selected())
    if T != self.teams:
        self.teams = T
        self.allTeams = []
        for i in range(T):
            self.allTeams.append(Team(self, i))


    self.playerTeams = int(self.teamAmount.get_selected())
    self.fillTeamsTo = int(self.teamFill.get_selected())
    self.teamsSave = self.teams
    self.TTS_ON = self.ttsToggle.get_selected() == "On"
    self.ITEM_AUTO = self.itemToggle.get_selected() == "Auto"
    self.reTeamPawns()
    teamIndices = []
    for i in range(self.teams):
        teamIndices.append(0)


    for i, pawn in enumerate(self.pawnHelpList):
        x = 900 + pawn.team * 100

        y = 550 + 30*teamIndices[pawn.team.i]
        teamIndices[pawn.team.i] += 1

        t = self.fontSmaller.render(pawn.name, True, pawn.team.color)
        self.screen.blit(t, (x,y))

    for team in range(len(teamIndices)):
        for playerI in range(self.fillTeamsTo):
            if teamIndices[team] > playerI:
                continue

            x = 900 + team * 100

            y = 550 + 30*playerI

            t = self.fontSmaller.render("NPC", True, self.getTeamColor(team))

            self.screen.blit(t, (x,y))

    if self.loadedMusic != self.musicChoice.get_selected():

        if self.music:
            for x in self.music:
                x.stop()

        if self.musicChoice.get_selected() == "Bablo":
            self.music = self.loadSound("audio/bar", volume=0.2, asPygame=True)
            print("Loaded")

        elif self.musicChoice.get_selected() == "Bablo >:)":
            self.music = self.loadSound("audio/taikakeinu/bar", volume=0.2, asPygame=True)
            print("Loaded")
            
        elif self.musicChoice.get_selected() == "HH":
            self.music = self.loadSound("audio/hh/bar", volume=0.2, asPygame=True)
            print("Loaded")

    self.loadedMusic = self.musicChoice.get_selected()


    serverOn = self.SimpleServerController.process and self.SimpleServerController.process.poll() is None
    
    if serverOn:
        ip = get_local_ip()

    t = self.font.render(f"Servu päällä ({ip}:5000)" if serverOn else "Servu pois päältä", True, [255,255,255])
    self.screen.blit(t, (200, 900))

    if serverOn:
        self.screen.blit(self.QR, (200,700))

    if self.toggleServer.draw(self.screen, "Käynnistä serveri" if not serverOn else "Lopeta serveri", font = self.font):
        pass
        



    if self.giveRandomWeapons.draw(self.screen, "Anna aseita", font = self.font):
        self.giveWeapons = True
        for pawn in self.pawnHelpList:
            w = random.choice(self.weapons)
            w.give(pawn)

    if not (self.playerFilesToGen or self.pawnGenI) and self.playButton.draw(self.screen, "Peliä", font = self.fontLarge):
        self.GAMESTATE = "pawnGeneration"

        #self.MANUALPAWN = self.pawnHelpList[0]

        #t = threading.Thread(target=self.threadedGeneration, args=("BABLO", imageRaw, None), kwargs={"boss": True})
        #t.daemon = True
        #t.start()

        npcsToAdd =  self.playerTeams * self.fillTeamsTo - len(self.pawnHelpList)
        for _ in range(npcsToAdd):
            for file_name in os.listdir("npcs/"):
                npc_name = os.path.splitext(file_name)[0]  # filename without extension
                if npc_name not in self.playerFiles and not any(t[0] == npc_name for t in self.playerFilesToGen):
                    
                    file_path = os.path.join("npcs", file_name)

                    # Load image as raw bytes (like imageRaw)
                    with open(file_path, "rb") as f:
                        imageRaw = f.read()

                    print(npc_name, "Adding npc")
                    self.playerFilesToGen.append((npc_name, imageRaw, None))
                    break

        self.refreshShops()
        self.reTeamPawns()
        self.SimpleServerController.stop_server()
        
    self.debugText("SUBS: " + str(bool(self.subs)))
    self.genPawns()


# Alternative simpler approach using subprocess
import subprocess
import sys
import asyncio
import websockets
from server.appServer import make_handler
import threading

def startServer(app):
    handler = make_handler(app)
    async def serverMain():
        async with websockets.serve(handler, "0.0.0.0", 8765, max_size=None):
            print("Server listening")
            app.loop = asyncio.get_event_loop() 
            await asyncio.Future()  # run forever

    asyncio.run(serverMain())

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