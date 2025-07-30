import subprocess
import pygame
import tempfile
import time
import os


class EspeakTTS:
    def __init__(self, speed=175, pitch=50, voice="en"):
        self.speed = str(speed)
        self.pitch = str(pitch)
        self.voice = voice

    def speak_to_wav(self, text, wav_path):
        subprocess.run([
            "espeak",
            "-s", self.speed,
            "-p", self.pitch,
            "-v", self.voice,
            "-w", wav_path,
            text
        ], check=True)


# Setup
pygame.mixer.init()
tts = EspeakTTS(speed=100, pitch=2, voice="fi")



with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
    wav_path = tmp.name

try:
    # Timing test
    for x in range(10):
        start = time.perf_counter()
        tts.speak_to_wav("Nimeni on mikko. Ja aioin tappaa sinut!", wav_path)
        sound = pygame.mixer.Sound(wav_path)
        end = time.perf_counter()
        print(f"Total time: {end - start:.3f} s")
    sound.play()
    
    print("Sound started")
    while pygame.mixer.get_busy():
        pygame.time.wait(10)
finally:
    os.remove(wav_path)



