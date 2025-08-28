from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game


class Team:
    def __init__(self, app: "Game", i):
        self.pawns = []
        self.i = i
        self.app = app
        self.color = self.app.getTeamColor(self.i)
        self.gold = 0

    def add(self, pawn):
        if pawn.team:
            pawn.team.pawns.remove(pawn)
        self.pawns.append(pawn)
        pawn.team = self
        pawn.originalTeam = self.i

    def __mul__(self, other):
        return int(self) * other

    def __radd__(self, other):
        return other + int(self)

    def __int__(self):
        return int(self.i)

        
