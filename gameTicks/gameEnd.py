from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from pygame.math import Vector2 as v2
import pygame
import time
import random

def gameEndTick(self: "Game"):
    self.PEACEFUL = True
    
    self.DRAWTO = self.screen
    self.DRAWTO.fill((0,0,0))
    #self.DRAWTO.blit(self.loadingSplash, self.originalRes/2 - v2(self.loadingSplash.get_size())/2)
    self.cameraPosDelta = v2([0,0])
    self.gameEndTimer += self.deltaTime

    winnerTeam = max(self.allTeams, key=lambda x: x.wins)

    winnerTeamPawns = [pawn for pawn in self.getActualPawns() if pawn.team.i == winnerTeam.i]
    entities_temp = sorted(winnerTeamPawns, key=lambda x: x.pos.y)
    self.TOTAL_TIME_ADJUSTMENT = 1.0
    for x in entities_temp:
        x.tick()
        x.render()


    # Winner banner
    
    t = self.notificationFont.render(
        f"{winnerTeam.getName()} WON!!",
        True,
        winnerTeam.getColor()
    )
    self.screen.blit(t, (self.res.x / 2 - t.get_width() / 2, 10))

    if not hasattr(self, "awards"):
        return

    # --- scrolling awards ---
    W = 420
    base_y = self.res.y * 0.55
    speed = 180

    total_width = len(self.awards) * W
    offset = (self.gameEndTimer * speed) % total_width

    for i, (title, pawn, desc) in enumerate(self.awards):
        x = (self.res.x - offset + i * W) % total_width - W

        if x < -W or x > self.res.x + W:
            continue  # skip offscreen

        drawAward(self, pawn, title, desc, x, base_y)


def drawAward(self, pawn, title, desc, x, y):
    img = pawn.hudImage
    color = pawn.team.getColor()
    #img = pygame.transform.scale_by(img, 120 / img.get_height())

    self.screen.blit(img, (x - img.get_width() / 2, y))

    t1 = self.font.render(title, True, color)
    t2 = self.fontSmaller.render(pawn.name, True, color)
    t3 = self.fontSmaller.render(desc, True, color)

    self.screen.blit(t1, (x - t1.get_width() / 2, y - 40))
    self.screen.blit(t2, (x - t2.get_width() / 2, y + img.get_height() + 5))
    self.screen.blit(t3, (x - t3.get_width() / 2, y + img.get_height() + 40))