from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from pygame.math import Vector2 as v2
import pygame
import time
import random


def gameEndTick(self: "Game"):
    winnerTeam = sorted(self.allTeams, key=lambda x: x.wins, reverse=True)[0]
    t = self.notificationFont.render(f"TEAM {winnerTeam.i+1} WON!!", True, winnerTeam.getColor())
    self.screen.blit(t, self.res/2 - v2(t.get_size())/2)
