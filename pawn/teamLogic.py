from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn

class Team:
    def __init__(self, app: "Game", i):
        self.pawns = []
        self.i = i
        self.app = app
        self.color = self.app.getTeamColor(self.i)
        self.currency = 0
        self.wins = 0
        self.allied = []
        self.enslavedTo = self.i

    def getI(self):
        return self.enslavedTo

    def getColor(self, enslaved = False):
        if enslaved:
            return self.app.getTeamColor(self.getI())
        
        return self.app.getTeamColor(self.i)
        
    
    def hostile(self, P: "Pawn", other: "Pawn"):
        
        if self.app.PEACEFUL:
            return False
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

        
