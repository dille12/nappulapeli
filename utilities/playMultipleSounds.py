import threading
import time
import pygame

def play_sounds_sequential(base, sounds, volume=1.0):
    def worker():
        for s in sounds:

            s = pygame.mixer.Sound(base + "/" + s + ".mp3")
            if s is None:
                continue
            s.set_volume(volume)
            s.play()
            length = s.get_length() + 0.3   
            if length > 0:
                time.sleep(length)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
