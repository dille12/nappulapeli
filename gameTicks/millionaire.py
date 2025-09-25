from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
from pygame.math import Vector2 as v2
import pygame
import time
import random

def initMillionaire(self: "Game"):
    self.MONEY = 0
    self.camSwitchTimer = 20
    self.currTime = 0
    self.millCam = True
    self.mill_bg_p = pygame.image.load("texture/millionaire/background_pawn.png").convert_alpha()
    self.mill_fg_p = pygame.image.load("texture/millionaire/foreground_pawn.png").convert_alpha()
    self.mill_fg_Jaajo = pygame.image.load("texture/millionaire/foreground_jaajo.png").convert_alpha()

    self.mill_bg_p = pygame.transform.scale(self.mill_bg_p, (self.res.x, self.res.y))
    self.mill_fg_p = pygame.transform.scale(self.mill_fg_p, (self.res.x, self.res.y))
    self.mill_fg_Jaajo = pygame.transform.scale(self.mill_fg_Jaajo, (self.res.x, self.res.y))

    self.suspense = pygame.mixer.Sound("audio/millionaire/suspense.mp3")

    self.prompt = pygame.image.load("texture/millionaire/prompt.png").convert_alpha()

    self.millionairePawn = None
    

def millionaireTick(self: "Game"):

    self.genPawns()

    if self.millionairePawn == None:
        self.millionairePawn = random.choice(self.pawnHelpList)


    if not self.suspense.get_num_channels():
        self.suspense.play(-1)

    self.currTime += self.deltaTime
    if self.currTime >= self.camSwitchTimer:
        self.currTime = 0
        self.millCam = not self.millCam
        self.camSwitchTimer = random.randint(10, 30)

    if self.millCam:
        self.screen.blit(self.mill_bg_p, (0, 0))

        if self.millionairePawn:

            # 183, 233 from 720, 480

            final_x = 183/720*self.res.x
            final_y = 285/480*self.res.y

            im = self.millionairePawn.millionaireImage

            self.screen.blit(im, (final_x - im.get_width()/2, final_y - im.get_height()))

        self.screen.blit(self.mill_fg_p, (0, 0))
    else:
        self.screen.blit(self.mill_fg_Jaajo, (0, 0))

    question = {"q": "Paljonko on 2 + 2?", "a1": "3", "a2": "4", "a3": "5", "a4": "6", "correct": 2}

    self.screen.blit(self.prompt, (0, self.res.y - self.prompt.get_height()))

    offsety = self.res.y - self.prompt.get_height()

    t = self.fontLarge.render(question["q"], True, [255]*3)
    x = self.res.x/2 - t.get_width()/2
    y = offsety + 205 - t.get_height()/2
    self.screen.blit(t, (x, y))

    for i, a in enumerate([question["a1"], question["a2"], question["a3"], question["a4"]]):

        # OFFSETS
        # topleft 525, 415
        # Botleft 525, 570
        # topright 1390, 415
        locs = [(525, 415), (525, 570), (1390, 415), (1390, 570)]

        t = self.font.render(a, True, [255]*3)
        x = locs[i][0] - t.get_width()/2
        y = offsety + locs[i][1] - t.get_height()/2
        self.screen.blit(t, (x, y))
