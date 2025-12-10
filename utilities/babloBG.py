import pygame, math, random

class SpeedLines:
    def __init__(self, num_lines=80, length=800, width=8, speed=0.6):
        self.num_lines = num_lines
        self.length = length
        self.width = width
        self.speed = speed
        self.lines = [
            (random.uniform(0, 2*math.pi), random.random())
            for _ in range(num_lines)
        ]

    def draw(self, surface, origin):
        t = pygame.time.get_ticks() * 0.001 * self.speed
        cx, cy = origin

        for angle, phase in self.lines:
            offset = (t + phase) % 1.0
            fade = 1.0 - offset
            if fade <= 0:
                continue

            dx, dy = math.cos(angle), math.sin(angle)
            nx, ny = -dy, dx

            inner = offset * self.length * 0.2
            outer = offset * self.length * 1.0
            half_w = self.width * fade

            p1 = (cx + dx * inner + nx * half_w, cy + dy * inner + ny * half_w)
            p2 = (cx + dx * outer, cy + dy * outer)
            p3 = (cx + dx * inner - nx * half_w, cy + dy * inner - ny * half_w)
            p4 = (cx, cy)

            color = (255, 255, 255, int(255 * fade))
            pygame.draw.polygon(surface, color, (p1, p2, p3, p4))


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    clock = pygame.time.Clock()
    origin = (1920/2, 1080/2)
    speedlines = SpeedLines(num_lines=120, length=2000, width=10, speed=3)

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))
        speedlines.draw(screen, origin)
        pygame.display.flip()
        clock.tick(60)