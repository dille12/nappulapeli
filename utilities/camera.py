import pygame
from pygame.math import Vector2 as v2
import random
import math
from collections import deque

class Camera:
    def __init__(self, app, pos):
        self.app = app  
        self.pos = v2(pos)
        self.vel = v2(0, 0)
        self.vibration_amp = 0.0
        self.vibration_decay = 4.0  # higher = faster decay
        self.vibration_offset = v2(0, 0)
        self.mainCamera = False
        self.cameraIndex = 0

        self.cameraLinger = 2
        self.cameraIdleTime = 0
        self.cameraLock = None

        self.splitI = 0
        self.cameraLockTarget = v2(0,0)
        self.cameraLockOrigin = v2(0,0)
        self.posToTargetTo = v2(0,0)
        self.posToTargetTo2 = v2(0,0)
        self.cameraPos = v2(0, 0)
        
        self.DUALVIEWACTIVE = False
        self.currHud = None
        self.hudChange = 0

        self.ekg_time = 0.0
        self.ekg_accum = 0.0
        self.ekg_points = deque(maxlen=100)
        self.heartRateEKG = 1.2

    def updateEKG(self):
        self.ekg_time += self.app.deltaTime
        self.ekg_accum += self.app.deltaTime
        # Sampling interval = 0.00625
        while self.ekg_accum >= 0.005:
            self.ekg_accum -= 0.005

            t = self.ekg_time
            if self.heartRateEKG == 0:
                phase = 0.5
            else:
                phase = (t * self.heartRateEKG) % 1.0

            if phase < 0.03:
                y = 5.0 * phase / 0.03
            elif phase < 0.06:
                y = 5.0 * (1.0 - (phase - 0.03) / 0.03)
            elif phase < 0.2:
                y = -0.15 * math.sin((phase - 0.06) * math.pi / 0.14)
            else:
                y = 0.02 * math.sin((phase - 0.2) * 2.0 * math.pi / 0.8)

            self.ekg_points.append(y)

        return list(self.ekg_points)

    def _lock_angle(self) -> float:
        """Return the angle from the lock origin to target.

        Falls back to 0 when the points overlap to avoid NaNs.
        """
        delta = self.cameraLockTarget - self.cameraLockOrigin
        if delta.length_squared() == 0:
            return 0.0
        return math.atan2(delta.y, delta.x)

    def max_split_distance(self, res):
        """Compute angle and maximum distance before a split is required."""
        angle = self._lock_angle() + math.pi

        diff = v2(math.sin(angle) * res.x/2, math.cos(angle) * res.y/2)

        max_dist = diff.magnitude() / self.app.RENDER_SCALE
        return angle, max_dist

    def requires_dual_view(self, res) -> bool:
        if not self.cameraLock or getattr(self.cameraLock, "BOSS", False):
            return False

        _, max_dist = self.max_split_distance(res)
        return self.cameraLockOrigin.distance_to(self.cameraLockTarget) > max_dist

    def update_split_positions(self, res: v2):
        angle, max_dist = self.max_split_distance(res)

        splitI = (1 - self.splitI) ** 2

        hx = res.x * 0.5
        hy = res.y * 0.5

        # Directions
        side_dir = v2(math.cos(angle), math.sin(angle))          # split normal
        forward_dir = v2(-side_dir.y, side_dir.x)               # split direction
        backward_dir = -forward_dir

        # Resolution-dependent lateral shift
        shift = -v2(
            math.cos(angle) * hx,
            math.sin(angle) * hy
        ) * splitI

        # Target separation
        raw_dist = self.cameraLockOrigin.distance_to(self.cameraLockTarget)
        shiftAmount = min(max_dist, raw_dist) * 0.5

        self.posToTargetTo = (
            self.cameraLockOrigin
            - side_dir * (shiftAmount * (1 - splitI))
            - res / 2
        )

        self.posToTargetTo2 = (
            self.cameraLockTarget
            + side_dir * (shiftAmount * (1 - splitI))
            - res / 2
        )

        # Mask thickness (guaranteed to cover screen)
        thickness = max(res.x, res.y) * 1.1
        mask_offset = side_dir * thickness

        center = res / 2

        line1 = forward_dir * res.x + center + shift
        line2 = backward_dir * res.x + center + shift
        line3 = forward_dir * res.x + center + shift - mask_offset
        line4 = backward_dir * res.x + center + shift - mask_offset

        return line1, line2, line3, line4


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
