import pygame
import numpy as np
import random
import math

CELL = 70
GRID_W, GRID_H = 13, 13
SCR_W, SCR_H = GRID_W * CELL, GRID_H * CELL

pygame.init()
screen = pygame.display.set_mode((SCR_W, SCR_H))
clock = pygame.time.Clock()

onFireCells = {(10,11), (11,10), (12,11)}

# =====================================
# COLOR FUNCTIONS
# =====================================

def fire_color(v):

    v = min(max(v, 0), 1)

    if v < 0.3:
        return (int(255*v/0.3), 0, 0)
    elif v < 0.6:
        t = (v-0.3)/0.3
        return (255, int(160*t), 0)
    else:
        t = (v-0.6)/0.4
        return (255, 160, int(120*t))

def smoke_color(a):
    return (40, 40, 40, int(max(a, 0)*180))


# =====================================
# PARTICLE CLASSES
# =====================================

class Spark:
    def __init__(self, cx, cy):
        x0, y0 = cx*CELL, cy*CELL
        self.x = x0 + random.uniform(0, CELL)
        self.y = y0 + CELL
        self.vy = random.uniform(-1.5, -3.0)
        self.vx = random.uniform(-0.3, 0.3)
        self.life = random.uniform(0.4, 0.9)
        self.age = 0.0

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.age += dt

    def alive(self):
        return self.age < self.life

    def draw(self, surf):
        a = 1 - self.age/self.life
        a = max(0, a)
        a = min(a, 1)
        col = fire_color(a*0.8 + 0.2)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), 3)


class Smoke:
    def __init__(self, cx, cy):
        x0, y0 = cx*CELL, cy*CELL
        self.x = x0 + random.uniform(0, CELL)
        self.y = y0 + CELL*0.3
        self.vy = random.uniform(-0.5, -1.2)
        self.vx = random.uniform(-0.2, 0.2)
        self.life = random.uniform(0.8, 1.5)
        self.age = 0.0

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.age += dt
        self.vx *= 0.99

    def alive(self):
        return self.age < self.life

    def draw(self, surf):
        a = 1 - self.age/self.life
        col = smoke_color(a)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), 8)


# =====================================
# NEW FLAME BLOB CLASS
# =====================================

class FlameBlob:
    def __init__(self, cx, cy):
        x0, y0 = cx*CELL, cy*CELL
        self.cx = cx
        self.cy = cy
        self.x = x0 + random.uniform(0, CELL)
        self.y = y0 + CELL + random.uniform(-10, 10)

        # strong upward rise
        self.vy = random.uniform(-2.5, -5.0)
        self.vx = random.uniform(-0.5, 0.5)

        self.radius = random.uniform(8, 20)
        self.life = random.uniform(0.25, 0.5)
        self.age = 0.0

        # noise warp
        self.noise_phase = random.uniform(0, 1000)

    def update(self, dt):
        self.age += dt

        # horizontal warping (strong)
        n = math.sin(self.noise_phase + self.age * 10) * 0.8
        self.x += self.vx + n
        self.y += self.vy

    def alive(self):
        return self.age < self.life

    def draw(self, surf):
        a = 1 - self.age/self.life
        col = fire_color(min(1.0, a*1.3))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), int(self.radius))


# =====================================
# MAIN LOOP
# =====================================

sparks = []
smokes = []
flames = []

running = True
while running:
    dt = clock.tick(180)/1000.0

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    screen.fill((0,0,0))

    # update all particles
    sparks = [p for p in sparks if p.alive()]
    smokes = [p for p in smokes if p.alive()]
    flames = [p for p in flames if p.alive()]

    for p in sparks: p.update(dt)
    for p in smokes: p.update(dt)
    for p in flames: p.update(dt)

    # spawn new particles for each fire cell
    for cx, cy in onFireCells:
        # many flame blobs
        for _ in range(3):
            flames.append(FlameBlob(cx, cy))

        # sparks
        if random.random() < 0.06:
            sparks.append(Spark(cx, cy))

        # smoke
        if random.random() < 0.04:
            smokes.append(Smoke(cx, cy))

    # draw order: flames → sparks → smoke
    for p in flames: p.draw(screen)
    for p in sparks: p.draw(screen)
    for p in smokes: p.draw(screen)

    pygame.display.set_caption(str(clock.get_fps()))

    pygame.display.flip()

pygame.quit()
