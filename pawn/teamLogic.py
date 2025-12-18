from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
    from levelGen.mapGen import Room
from utilities.building import Building
import numpy as np
import random
import math
from core.detonation.teamDetonationLogic import tickDetonationLogic
class NadePos:
    def __init__(self, pos):
        self.pos = pos
        self.lifetime = 10

    def equal(self, pos):
        return self.pos[0] == pos[0] and self.pos[1] == pos[1]




def angle_diff(a, b):
    return (b - a + math.pi) % (2 * math.pi) - math.pi

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

        self.utilityPos = {
            "defensive": [],
            "aggr": [],
        }

        self.defaultPlan()

        

        self.detonationTeam = False

        self.sightGrid = None


    def getTerroristTeam(self):
        """
        Terrorists are the latter half of the teams. detonationTeam is False
        """
        return self.app.allTeams[-1]

    def getCounterTeam(self):
        """
        Terrorists are the first half of the teams. detonationTeam is True
        """
        return self.app.allTeams[0]

    def defaultPlan(self):
        self.plan = {"currentAction": "defend",
                     "ctHolding" : True,
                     "viableSites": [], 
                     "site": None,
                     "planTimer": 30}
        self.utilityPos["aggr"].clear()
        self.utilityPos["defensive"].clear()

    def refreshCarrier(self):

        if self.isCT(): return

        if self.app.objectiveCarriedBy:
            self.bombCarrier = self.app.objectiveCarriedBy

        if not self.bombCarrier or self.bombCarrier.killed:
            self.bombCarrier = random.choice(self.getDetonationPawns())

        if self.app.objectiveCarriedBy and self.plan["site"] and self.app.objectiveCarriedBy.getOwnCell() == self.plan["site"].plantingSite:
            print("BOMB PLANTED")

            self.app.skull.planted = True
            self.app.skull.plantedAt = self.plan["site"]
            self.app.skull.planter = self.app.objectiveCarriedBy
            self.app.allTeams[0].plan["site"] = self.plan["site"]
            self.app.allTeams[-1].plan["site"] = self.plan["site"]

            self.app.playPositionalAudio("audio/bombPlant.wav", self.app.skull.planter.pos)

            self.app.objectiveCarriedBy.dropSkull()

            self.app.notify("THE BOMB HAS BEEN PLANTED!", self.getColor())

    def isCT(self):
        return self.detonationTeam
    
    def bombInEnemyTerritory(self):
        skull_x, skull_y = self.app.skull.cell
        return self.app.map.grid[skull_y, skull_x] in (2, 4) and not self.app.objectiveCarriedBy

    def tryToDefuse(self):
        if not self.isCT(): return

        if not self.app.skull.planted: return

        if self.app.skull.defusedBy: return
            
        for x in self.getPawns():
            if x.getOwnCell() == self.app.skull.plantedAt.plantingSite:
                self.app.skull.defusedBy = x
                x.target = None
                return

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
                pawns = x.pawns
                for x in pawns:
                    if x.isPawn:
                        p.append(x)
        return p


    def getViableSites(self):
        startPos = self.getDetonationSpawnRoom().center()
        viable_sites = []

        for site in self.app.SITES:
            if site.attackPositionsT and site.attackPositionsCT:
                viable_sites.append(site)
        print("Can only attack:", viable_sites)
        self.plan["viableSites"] = viable_sites


    def getClosestSite(self):

        if self.isCT(): return

        startPos = self.getDetonationSpawnRoom().center()

        m = [None, float("inf")]

        for x in self.plan["viableSites"]:
            cell = x.room.randomCell()
            route = self.app.arena.pathfinder.find_path(startPos, x.room.randomCell())
            if len(route) < m[1]:
                m = [x, len(route)]

        print("Picking closest site", m[0])
        return m[0]

    def terroristsHoldPlanSite(self):
        if self.app.allTeams[-1].plan["site"]:
            return self.app.allTeams[-1].plan["site"].controlledByT()
        return False

    def terroristsInControlOfSite(self):
        return any(x.controlledByT() for x in self.app.SITES)

    def tickDetonation(self):
        tickDetonationLogic(self)

    def addNadePos(self, pos, nadeType = "aggr"):
        self.utilityPos[nadeType].append(NadePos(pos))

    def getRandomNadePos(self, nadeType = "aggr"):
        if not self.utilityPos[nadeType]:
            return
        return random.choice(self.utilityPos[nadeType]).pos

    def deleteNadePos(self, delPos, nadeType = "aggr"):
        for obj in self.utilityPos[nadeType]:
            if obj.equal(delPos):
                self.utilityPos[nadeType].remove(obj)
                break

    def tickNadePos(self):
        dt = self.app.deltaTime
        to_remove = {"aggr": [], "defensive": []}

        for kind in ("aggr", "defensive"):
            for obj in self.utilityPos[kind]:
                obj.lifetime -= dt
                if obj.lifetime <= 0:
                    to_remove[kind].append(obj)

        for kind in ("aggr", "defensive"):
            for obj in to_remove[kind]:
                self.utilityPos[kind].remove(obj)

            

    def getGodTeam(self):

        if self.app.GAMEMODE != "DETONATION":
            return self

        if self.isCT():
            return self.app.allTeams[0]
        else:
            return self.app.allTeams[-1]
        
    def _getPawns(self):
        return [x for x in self.pawns if x.isPawn]

    def getPawns(self):
        if self.app.GAMEMODE == "DETONATION":
            p = []
            for x in self.app.allTeams:
                if x.detonationTeam == self.detonationTeam:
                    p += x._getPawns()
            return p
        else:
            return self._getPawns()

    
    def takeCoverFromFlash(self, landingCell):
        pawns = self.getPawns()

        vis = None
        get_vis = self.app.map.get_visible_cells

        for x in pawns:
            #c = x.getOwnCell()
            if x.canSeeCell(landingCell):


                v = self.app.cell2Pos(landingCell) - x.pos

                grenade_angle = math.atan2(-v.y, v.x)
                dtheta = angle_diff(x.aimAt, grenade_angle)
                if abs(dtheta) > math.pi / 3: continue  # outside 90° FOV

                if not vis:
                    vis = set(get_vis(landingCell[0], landingCell[1]))
                vis2 = set(x.getVisibility(4))
                safe_cells = list(vis2 - vis)

                if safe_cells:
                    x.getRouteTo(endPosGrid=random.choice(safe_cells))
                    x.say("Äkkiä piiloon!")
                    print(x.name, "Dodges a flash")
                    


    def getDetonationSpawnRoom(self):
        rooms = self.app.teamSpawnRooms
        i = 1 if self.detonationTeam else 0
        return rooms[i]
    
    def getTotalIndex(self, p):
        i = 0
        for x in self.app.allTeams:

            teamPawns = [x for x in x.pawns if x.isPawn]

            if x.detonationTeam != self.detonationTeam:
                continue

            if x == self:
                i += teamPawns.index(p)
                return i
            else:
                i += len(teamPawns)

    def getCurrentSite(self):
        return self.getTerroristTeam().plan["site"]
    

    def getSite(self, p):
        if not self.detonationTeam: # CT
            index = self.getTotalIndex(p)
            SITES = self.app.allTeams[-1].plan["viableSites"]
            if not SITES:
                return None
            return SITES[index%len(SITES)]
        else: # T
            index = self.getTotalIndex(p)
            if not self.app.SITES:
                #print("No sites???")
                return None
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
            if self.isCT():
                return [76, 129, 255]  # CT
            else:
                return [255, 210, 64] # T
        
        return self.app.getTeamColor(self.i)
        
    
    def hostile(self, P: "Pawn", other: "Pawn"):

        #if P.enslaved and self == P.team and self.isEnslaved():
        #    return self.app.allTeams[self.enslavedTo].hostile(P, other)
            
        
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

    def isEnslaved(self):
        return self.enslavedTo != self.i
    
    def emancipate(self):
        self.enslavedTo = self.i
        for x in self.getPawns():
            x.enslaved = False


    def updateCurrency(self):
        for x in self._getPawns():
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

        
