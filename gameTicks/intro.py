from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
import pygame

def intro(self: "Game"):
    self.screen.fill((0,0,0))
        
    if not self.hasFocus: return

    if not self.introSoundPlayed:
        self.introAudio.play()
        self.introSoundPlayed = True

    surf = self.VIDEOPLAYER.update(self.deltaTime, self.originalRes)

    if surf:
        self.introSurf = surf
    if self.introSurf:
        self.screen.blit(self.introSurf, (0, 0))

    if "space" in self.keypress:
        self.VIDEOPLAYER.done = True
        self.introAudio.stop()

    if self.VIDEOPLAYER.done and not self.TRANSITION:
        self.transition(lambda: self.exitIntro())

    