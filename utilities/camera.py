import pygame
from pygame.math import Vector2 as v2
import random
import math

class Camera:
    def __init__(self, app, pos):
        self.app = app  
        self.pos = v2(pos)
        self.vel = v2(0, 0)
        self.vibration_amp = 0.0
        self.vibration_decay = 4.0  # higher = faster decay
        self.vibration_offset = v2(0, 0)

    def vibrate(self, strength: float):
        strength = min(strength, 40)
        self.vibration_amp = max(self.vibration_amp, strength)

    def update(self, target, delta, smooth_time=0.25):
        if smooth_time <= 1e-6:
            self.pos = v2(target)
            self.vel = v2(0, 0)
            return

        omega = 2.0 / smooth_time
        x = omega * delta
        exp = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)

        change = self.pos - target
        temp = (self.vel + omega * change) * delta
        self.vel = (self.vel - omega * temp) * exp
        self.pos = target + (change + temp) * exp

        if self.vibration_amp > 1e-4:
            angle = random.uniform(0, 2 * math.pi)
            offset = v2(math.cos(angle), math.sin(angle)) * self.vibration_amp
            self.vibration_offset = offset
            self.vibration_amp *= math.exp(-self.vibration_decay * delta)
        else:
            self.vibration_offset = v2(0, 0)

        self.pos = self.pos + self.vibration_offset
