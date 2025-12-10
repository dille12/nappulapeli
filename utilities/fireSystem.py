import pygame
import random
import math

class FireSystem:
    def __init__(self, app):
        self.app = app
        self.CELL = self.app.tileSize      # expect 70
        self.cells = {}                    # (cx,cy) → particle container

    # ==============================================
    # UTILITY
    # ==============================================

    def fire_color(self, v):
        v = max(0.0, min(1.0, v))
        if v < 0.3:
            return (int(255*v/0.3), 0, 0)
        elif v < 0.6:
            t = (v-0.3)/0.3
            return (255, int(160*t), 0)
        else:
            t = (v-0.6)/0.4
            return (255, 160, int(120*t))

    def smoke_color(self, a):
        a = max(0.0, min(1.0, a))
        return (40, 40, 40, int(a*180))
    
    def to_screen(self, x, y):
        return int(x - self.app.cameraPosDelta.x), int(y - self.app.cameraPosDelta.y)

    # ==============================================
    # PARTICLES
    # ==============================================

    class FlameBlob:
        def __init__(self, parent, cx, cy):
            self.parent = parent
            CELL = parent.CELL
            x0, y0 = cx*CELL, cy*CELL

            self.x = x0 + random.uniform(0, CELL)
            self.y = y0 + CELL + random.uniform(-10, CELL / 2)

            self.vy = random.uniform(-2.5, -5.0)
            self.vx = random.uniform(-0.5, 0.5)

            self.radius = random.uniform(8, 20)
            self.life = random.uniform(0.25, 0.5)
            self.age = 0.0

            self.noise_phase = random.uniform(0, 1000)
            self.cx = cx
            self.cy = cy

        def update(self, dt):
            self.age += dt
            n = math.sin(self.noise_phase + self.age * 10) * 0.8
            self.x += self.vx + n
            self.y += self.vy

        def alive(self):
            return self.age < self.life

        def draw(self, surf):

            if not self.parent.app.onScreen((self.x, self.y)):
                return

            a = 1 - self.age/self.life
            col = self.parent.fire_color(min(1.0, a*1.3))
            pygame.draw.circle(surf, col, self.parent.to_screen(int(self.x), int(self.y)), int(self.radius))

    class Spark:
        def __init__(self, parent, cx, cy):
            self.parent = parent
            CELL = parent.CELL
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

            if not self.parent.app.onScreen((self.x, self.y)):
                return

            a = 1 - self.age/self.life
            col = self.parent.fire_color(a*0.8 + 0.2)
            pygame.draw.circle(surf, col, self.parent.to_screen(int(self.x), int(self.y)), 3)

    class Smoke:
        def __init__(self, parent, cx, cy):
            self.parent = parent
            CELL = parent.CELL
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

            if not self.parent.app.onScreen((self.x, self.y)):
                return

            a = 1 - self.age/self.life
            col = self.parent.smoke_color(a)
            pygame.draw.circle(surf, col, self.parent.to_screen(int(self.x), int(self.y)), 8)

    # ==============================================
    # CELL MANAGEMENT
    # ==============================================


    def removeCell(self, cell):
        if cell in self.cells:
            del self.cells[cell]

    def addCell(self, cx, cy, lifetime, firer):
        if (cx, cy) not in self.cells:
            self.cells[(cx, cy)] = {
                "lifetime": lifetime,
                "firer": firer,
                "time": 0.0,
                "flames": [],
                "sparks": [],
                "smoke": []
            }
        else:
            # refresh lifetime & optionally update firer
            self.cells[(cx, cy)]["lifetime"] = lifetime
            self.cells[(cx, cy)]["firer"] = firer


    # ==============================================
    # UPDATE & DRAW
    # ==============================================

    def update(self):
        dt = self.app.deltaTime

        for (cx, cy), data in list(self.cells.items()):
            data["lifetime"] -= dt
            data["time"] += dt

            if data["lifetime"] <= 0:
                self.removeCell((cx, cy))
                continue


        # particle simulation
        for (cx, cy), data in self.cells.items():
            data["time"] += dt

            flames = data["flames"]
            sparks = data["sparks"]
            smoke = data["smoke"]

            # update existing
            flames[:] = [p for p in flames if p.alive()]
            sparks[:] = [p for p in sparks if p.alive()]
            smoke[:] = [p for p in smoke if p.alive()]

            for p in flames: p.update(dt)
            for p in sparks: p.update(dt)
            for p in smoke: p.update(dt)

            # spawn new (per frame)
            if random.random() < 0.5:
                flames.append(self.FlameBlob(self, cx, cy))

            if random.random() < 0.06:
                sparks.append(self.Spark(self, cx, cy))

            if random.random() < 0.04:
                smoke.append(self.Smoke(self, cx, cy))

    def draw(self, surf):
        # draw in order
        for data in self.cells.values():
            for p in data["flames"]:
                p.draw(surf)
            for p in data["sparks"]:
                p.draw(surf)
            for p in data["smoke"]:
                p.draw(surf)
