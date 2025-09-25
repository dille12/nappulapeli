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
        
    
    def hostile(self, other: "Pawn"):
        
        if self.app.PEACEFUL:
            return False
        if self.app.TRUCE:
            return False
        if self.app.FFA:
            return True
        if other.team in self.allied:
            return False
        return self != other.team
        


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

        
