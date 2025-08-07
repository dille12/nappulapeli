
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
import random
import math
from pygame.math import Vector2 as v2
import subprocess
import tempfile
from _thread import start_new_thread
import os
import pygame
class EspeakTTS:
    def __init__(self, owner: "Pawn", speed=175, pitch=50, voice="fi"):
        self.speed = str(speed)
        self.pitch = str(pitch)
        self.voice = voice
        self.owner = owner
        self.app: "Game" = owner.app
        self.current_path = None
        self.sound = None
        self.generating = False

    def say(self, text):

        if not self.app.TTS_ON:
            return
        if self.generating:
            return
        if self.app.speeches > 1:
            return
        if self.owner.textBubble or self.sound:
            return
        
        self.generating = True
        
        #self.stop()

        start_new_thread(self.threaded, (text, ))

    def threaded(self, text):
        self.app.speeches += 1
        self.owner.textBubble = text
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                wav_path = tmp.name
            subprocess.run([
                "espeak",
                "-s", self.speed,
                "-p", self.pitch,
                "-v", self.voice,
                "-w", wav_path,
                text
            ], check=True)

            self.sound = pygame.mixer.Sound(wav_path)
            self.generating = False
            self.sound.play()
            while True:
                if not self.sound:
                    break
                if self.sound.get_num_channels():
                    pygame.time.wait(100)
                else:
                    break

        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
            self.owner.textBubble = None
            self.app.speeches -= 1
            self.sound = None

    def stop(self):
        if self.generating:
            return

        if self.sound:
            self.sound.stop()
            self.owner.textBubble = None
