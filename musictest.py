from utilities.musicMixer import MixInfo
import sys
import pygame

class SaveData:
    def __init__(self, beats, drops, INTENSEBEATS, tempo = 100):
        self.beats = beats
        self.drops = drops
        self.intensebeats = INTENSEBEATS
        self.tempo = tempo

if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()
    MInfo = MixInfo(initalSpeed=1.2)
    
    MInfo.startPlaying(firstTrack=False)
    
    clock = pygame.time.Clock()
    while 1:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        MInfo.handleLoop()
