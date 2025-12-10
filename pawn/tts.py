
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
import io
import soundfile as sf
import time
from audioPlayer.audioMixer import AudioSource
class EspeakTTS:
    def __init__(self, owner: "Pawn", speed=175, pitch=50, voice="fi"):
        self.speed = str(speed)
        self.pitch = str(pitch)
        g = random.choice(["f", "m"])
        i = random.randint(1,5)
        l = random.choice(["fi", "et", "sv", "fr", "en"])
        self.voice = f"{l}+{g}{i}"
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
        if self.owner.textBubble or self.sound:
            return
        
        self.generating = True
        
        #self.stop()

        start_new_thread(self.threaded, (text, ))

    def threaded(self, text):
        self.app.speeches += 1
        self.owner.textBubble = text
        
        try:
            #with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            #    wav_path = tmp.name
            proc = subprocess.run([
                "espeak",
                "-s", self.speed,
                "-p", self.pitch,
                "-v", self.voice,
                "--stdout",
                text
            ], check=True, stdout=subprocess.PIPE)
            wav_bytes = proc.stdout
            data, sample_rate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
            source = AudioSource(data, sample_rate, 44100)

            time.sleep(random.uniform(0.1,0.5))

            self.sound = self.owner.app.playPositionalAudio(source, pos=self.owner.pos)
            self.sound.base_volume = 1
            
            self.generating = False

            while True:
                if not self.sound:
                    break
                if not self.sound.active:
                    break
                time.sleep(0.1)


        finally:
            self.owner.textBubble = None
            self.app.speeches -= 1
            self.sound = None

    def stop(self):
        if self.generating:
            return

        if self.sound:
            self.sound.active = False
            self.owner.textBubble = None
