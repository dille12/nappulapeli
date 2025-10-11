from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
import pygame

class modularSurface:
    def __init__(self, app: "Game", surface: pygame.Surface):
        self.app = app
        self.surface = surface.convert_alpha()
        self.imDict = {1: self.surface.copy()}

    def _scale(self, scale: float):
        if scale not in self.imDict:
            self.imDict[scale] = pygame.transform.scale_by(
                self.surface.copy(),
                scale,
            )
        return self.imDict[scale]
    
    def __call__(self):
        return self._scale(self.app.SCALE)
    
    def get(self):
        return self._scale(self.app.SCALE).copy()

