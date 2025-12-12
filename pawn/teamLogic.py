from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
    from levelGen.mapGen import Room
from utilities.building import Building
import numpy as np
import random
class Team:
    def __init__(self, app: "Game", i):
        self.pawns = []
        self.i = i
        self.app = app
        self.color = self.getColor()
        self.currency = 0
        self.wins = 0
        self.allied = []
        self.enslavedTo = self.i
        self.buildingsToBuild = 5
        self.bombCarrier = None

        self.planTimer = 30
        self.plan = {"currentAction": "probe",
                     "ctHolding" : True,
                     "viableSites": [], 
                     "site": None}

        

        self.detonationTeam = False

        self.sightGrid = None

    def refreshCarrier(self):
        if not self.bombCarrier or self.bombCarrier.killed:
            self.bombCarrier = random.choice(self.getDetonationPawns())

        if self.app.objectiveCarriedBy and self.plan["site"] and self.app.objectiveCarriedBy.getOwnCell() == self.plan["site"].plantingSite:
            print("BOMB PLANTED")

            
            
            self.app.skull.planted = True
            self.app.skull.plantedAt = self.plan["site"]
            self.app.skull.planter = self.app.objectiveCarriedBy

            self.app.objectiveCarriedBy.dropSkull()

            self.app.notify("THE BOMB HAS BEEN PLANTED!", self.getColor())

    def getDetI(self):
        return 1 if self.detonationTeam else 0

    def refreshColor(self):
        self.color = self.getColor()

    def resetSightGrid(self):
        self.sightGrid = np.zeros(self.app.map.grid.shape, dtype=np.float32)

    def addVisToGrid(self, vis):
        if not isinstance(self.sightGrid, np.ndarray):
            self.sightGrid = np.zeros(self.app.map.grid.shape, dtype=np.float32)
        
        for x,y in vis:
            self.sightGrid[y,x] += 1

    def getDetonationPawns(self):
        p = []
        for x in self.app.allTeams:
            if x.detonationTeam == self.detonationTeam:
                p += x.pawns
        return p


    def getViableSites(self):
        startPos = self.getDetonationSpawnRoom().center()
        viable_sites = []

        for site in self.app.SITES:
            if site.attackPositionsT and site.attackPositionsCT:
                viable_sites.append(site)
        print("Can only attack:", viable_sites)
        self.plan["viableSites"] = viable_sites


    def terroristsInControlOfSite(self):
        return any(x.controlledByT() for x in self.app.SITES)

    def tickDetonation(self):

        SITES = self.app.allTeams[-1].plan["viableSites"]
        if not SITES:
            return

        self.refreshCarrier()

        if self.plan["site"] not in self.app.SITES:
            self.plan["site"] = None

        if self.getDetI(): # CT
            currHolding = not any(x.controlledByT() for x in self.app.SITES)
            if currHolding != self.plan["ctHolding"]:
                print("Switching ct plan!")

                #if not currHolding:
                self.plan["site"] = self.app.allTeams[-1].plan["site"]  

                self.plan["ctHolding"] = currHolding
                if not currHolding:
                    print("Attacking site", self.plan["site"])
                    self.plan["currentAction"] = "prepare"
                    self.planTimer = 45
            if not currHolding:
                self.planTimer -= self.app.deltaTime
                if self.plan["currentAction"] == "probe":
                    self.plan["currentAction"] = "prepare"
                    self.planTimer = 45

                if self.plan["currentAction"] == "prepare":
                    p = self.getDetonationPawns()
                    l = [x.attackInPosition() for x in p]
                    l2 = [x.target for x in p]
                    if all(l) or any(l2):
                        self.planTimer = 0

            else:
                self.plan["currentAction"] = "probe"
                self.planTimer = 30
                          

        else: # T
            currHolding = any(x.controlledByT() for x in self.app.SITES)
            if not currHolding:
                self.planTimer -= self.app.deltaTime

                if self.plan["currentAction"] == "prepare":
                    p = self.getDetonationPawns()
                    l = [x.attackInPosition() for x in p]
                    l2 = [x.target for x in p]
                    if all(l) or any(l2):
                        self.planTimer = 0
                
            else:
                self.plan["currentAction"] = "probe"
                self.planTimer = 5
                for x in self.app.SITES:
                    if x.controlledByT():
                        self.plan["site"] = x
                        break

        
        if self.planTimer <= 0:
            if self.plan["currentAction"] == "probe":
                self.plan["currentAction"] = "prepare"
                self.planTimer = 45
                self.plan["site"] = random.choice(SITES)
            elif self.plan["currentAction"] == "prepare":
                self.plan["currentAction"] = "execute"
                self.planTimer = 30
            elif self.plan["currentAction"] == "execute":
                self.plan["currentAction"] = "probe"
                self.planTimer = 30

            for x in self.app.pawnHelpList:
                if x.team.detonationTeam == self.detonationTeam:
                    x.pickWalkingTarget()

    def getGodTeam(self):
        if self.detonationTeam:
            return self.app.allTeams[0]
        else:
            return self.app.allTeams[-1]
         


    def getDetonationSpawnRoom(self):
        rooms = self.app.teamSpawnRooms
        i = 1 if self.detonationTeam else 0
        return rooms[i]
    
    def getTotalIndex(self, p):
        i = 0
        for x in self.app.allTeams:

            if x.detonationTeam != self.detonationTeam:
                continue

            if x == self:
                i += self.pawns.index(p)
                return i
            else:
                i += len(x.pawns)
    

    def getSite(self, p):
        if not self.detonationTeam:
            index = self.getTotalIndex(p)
            SITES = self.app.allTeams[-1].plan["viableSites"]
            if not SITES:
                return None
            return SITES[index%len(SITES)]
        else:
            index = self.getTotalIndex(p)
            return self.app.SITES[index%len(self.app.SITES)]



    def spawnBase(self):
        r = self.getSpawnRoom()
        x,y = r.center()
        Building(self.app, "BASE", self, "texture/base.png", (x,y), (2,2), 1, 500)
        
    def getSpawnRoom(self) -> "Room":
        if hasattr(self.app, "teamSpawnRooms"):
            return self.app.teamSpawnRooms[self.i]

    def getI(self):
        return self.enslavedTo

    def getColor(self, enslaved = False):
        if self.i == -1:
            return [255,255,255]
        if enslaved:
            return self.app.getTeamColor(self.getI())
        
        if hasattr(self.app, "GAMEMODE") and self.app.GAMEMODE == "DETONATION":
            if self.detonationTeam:
                return [76, 129, 255]
            
            else:
                return [255, 210, 64]
        
        return self.app.getTeamColor(self.i)
        
    
    def hostile(self, P: "Pawn", other: "Pawn"):
        
        if self.app.PEACEFUL:
            return False
        if other.BOSS or P.BOSS:
            return True
        if self.app.TRUCE:
            return False
        if self.app.FFA:
            return True
        
        if P.enslaved and self.enslavedTo == other.team.i:
                return False
        if other.enslaved and other.team.enslavedTo == self.i:
            return False

        if other.team in self.allied:
            return False
        return self != other.team
        
    def slaveTo(self, other: "Team"):
        self.enslavedTo = other.i
    
    def emancipate(self):
        self.enslavedTo = self.i


    def updateCurrency(self):
        for x in self.pawns:
            if not x.client:
                continue

            x.updateStats({"currency": self.currency})

    def add(self, pawn: "Pawn"):

        if pawn.team == self:
            return

        if pawn.team:
            pawn.team.pawns.remove(pawn)
        self.pawns.append(pawn)
        pawn.team = self
        pawn.originalTeam = self.i
        if pawn.client:
            packet = {"type": "teamSwitch", 
                        "newTeamColor": self.color}
            pawn.dumpAndSend(packet)

            pawn.updateStats({"currency": self.currency})

    def __mul__(self, other):
        return int(self) * other

    def __radd__(self, other):
        return other + int(self)

    def __int__(self):
        return int(self.i)

        
