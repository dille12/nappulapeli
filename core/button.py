import pygame
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game

from pygame.math import Vector2 as v2

class Button:
    def __init__(self, app: "Game", pos, size):
        self.app = app
        self.rect = pygame.Rect(pos, size)
        self.a = False
        self.weaponPos = v2(0,0)

    def draw(self, surface, text="", font=None):
        pygame.draw.rect(surface, (100, 100, 100), self.rect)
       
        hitBox = self.rect.copy()

        if hitBox.collidepoint(self.app.mouse_pos):
            w = 3
            if not self.a:
                self.app.clicks[0].stop()
                self.app.clicks[0].play()
            self.a = True
        else:
            w = 1
            self.a = False

        pygame.draw.rect(surface, [255,255,255], self.rect, width=w)

                

        if text and font:
            label = font.render(text, True, (255, 255, 255))
            surface.blit(label, label.get_rect(center=self.rect.center))

        if self.a and "mouse0" in self.app.keypress:
            self.app.clicks[1].stop()
            self.app.clicks[1].play()
            return True
        return False