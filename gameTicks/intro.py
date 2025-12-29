from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
import pygame

def intro(self: "Game"):
    self.screen.fill((0,0,0))

    if not self.introSoundPlayed:
        self.introAudio.play()
        self.introSoundPlayed = True

    surf = self.VIDEOPLAYER.update(self.deltaTime, self.originalRes)

    if surf:
        self.introSurf = surf
    if self.introSurf:
        self.screen.blit(self.introSurf, (0, 0))

    if self.VIDEOPLAYER.done and not self.TRANSITION:
        self.transition(lambda: self.exitIntro())

    