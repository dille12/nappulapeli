import cv2
import pygame
import numpy as np
import sys
class VideoPlayer:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise IOError("Could not open video file")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.dt = 1.0 / self.fps
        self.acc = 0.0
        self.done = False

    def update(self, delta_time, size):
        if self.done:
            return None

        self.acc += delta_time
        if self.acc < self.dt:
            return None

        self.acc -= self.dt

        ret, frame = self.cap.read()


        if not ret:
            self.done = True
            self.cap.release()
            return None

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        target_w, target_h = size
        frame = cv2.resize(
            frame,
            (int(target_w), int(target_h)),
            interpolation=cv2.INTER_AREA
        )

        frame = frame.swapaxes(0, 1)
        return pygame.surfarray.make_surface(frame)


if __name__ == "__main__":


    video = VideoPlayer("utilities/1228.mp4")
    running = True
    screen = pygame.display.set_mode((1920, 1080))
    clock = pygame.time.Clock()
    while running:
        dt = clock.tick(60) / 1000.0

        surf = video.update(dt)
        if surf:
            surf = pygame.transform.scale_by(surf, 1366 / surf.get_width())
            screen.blit(surf, (0, 0))

        if video.done:
            sys.exit()


        pygame.display.flip()
