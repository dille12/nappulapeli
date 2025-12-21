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

    def _lock_angle(self) -> float:
        """Return the angle from the lock origin to target.

        Falls back to 0 when the points overlap to avoid NaNs.
        """
        delta = self.cameraLockTarget - self.cameraLockOrigin
        if delta.length_squared() == 0:
            return 0.0
        return math.atan2(delta.y, delta.x)

    def max_split_distance(self):
        """Compute angle and maximum distance before a split is required."""
        angle = self._lock_angle() + math.pi / 2
        max_dist = 300 + 300 * abs(math.sin(angle))
        return angle, max_dist

    def requires_dual_view(self) -> bool:
        if not self.cameraLock or getattr(self.cameraLock, "BOSS", False):
            return False

        _, max_dist = self.max_split_distance()
        return self.cameraLockOrigin.distance_to(self.cameraLockTarget) > max_dist

    def update_split_positions(self, res: v2):
        """Update split camera lines and target positions.

        Returns a tuple of (line1, line2, line3, line4) points used for masking
        the split screen. `res` should be the current resolution Vector2.
        """
        angle, max_dist = self.max_split_distance()

        shiftI = (1 - self.splitI) ** 2
        maxX = 1000 * shiftI

        shift = v2(math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2)) * (-maxX)
        raw_dist = self.cameraLockOrigin.distance_to(self.cameraLockTarget)
        shiftAmount = min(max_dist, raw_dist) / 2

        side_dir = v2(math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2))
        forward_dir = v2(math.cos(angle), math.sin(angle))
        backward_dir = v2(math.cos(angle + math.pi), math.sin(angle + math.pi))

        self.posToTargetTo = self.cameraLockOrigin + side_dir * (-shiftAmount * (1 - shiftI)) - res / 2
        self.posToTargetTo2 = self.cameraLockTarget + side_dir * (shiftAmount + 0.7 * maxX) - res / 2

        line1 = forward_dir * res.x + res / 2 + shift
        line2 = backward_dir * res.x + res / 2 + shift
        line3 = forward_dir * res.x + res / 2 - side_dir * 1200 + shift
        line4 = backward_dir * res.x + res / 2 - side_dir * 1200 + shift

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
