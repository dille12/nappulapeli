import pygame
from pygame.math import Vector2 as v2

class Camera:
    def __init__(self, app, pos):
        self.app = app  
        self.pos = v2(pos)
        self.vel = v2(0, 0)

    def update(self, target, delta, smooth_time=0.25):
        """
        Smooth camera follow using critically damped spring.
        target: target position (Vector2)
        delta: frame delta time
        smooth_time: larger = looser follow, smaller = tighter
        """
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
