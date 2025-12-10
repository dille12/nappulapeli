import pygame
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn

from pygame.math import Vector2 as v2
import random

class TestPawn:
    def __init__(self, im):
        self.levelUpImage = pygame.image.load(im).convert_alpha()
        self.levelUpImage = pygame.transform.scale_by(
            self.levelUpImage, 400 / self.levelUpImage.get_size()[1]
        )


class PawnParticle:
    def __init__(self, pawn: "Pawn"):
        self.image = pawn.levelUpImage.copy()
        self.images = []
        imHeight = self.image.get_height() / self.image.get_width()
        self.rot = random.uniform(0, 360)
        self.rotVel = random.uniform(-1,1)
        pawn.app.PAWNPARTICLES.append(self)

        for i in range(144):
            scale = int(100 + ((i) / 144) ** 1.5 * 1480)
            imtemp = pygame.transform.scale(
                self.image.copy(), (scale, int(scale * imHeight))
            )

            darken_factor = 0.25 + 0.75 * ((144-i) / 144)
            dark_surface = pygame.Surface(imtemp.get_size())
            dark_surface.fill((darken_factor*255, darken_factor*255, darken_factor*255))
            imtemp.blit(dark_surface, (0, 0), special_flags=pygame.BLEND_MULT)

            imtemp = pygame.transform.rotate(imtemp, self.rot)
            self.rot += self.rotVel

            self.images.append(imtemp)

        self.reset()

    def setAsMainPiece(self):
        self.pos.x = 1920/2
        self.xvel = 0
        self.yvel = 12

    def reset(self):
        self.pos = v2(1920/2, 1080)
        self.xvel = random.uniform(1,10) * random.choice((-1,1))
        self.pos.x += self.xvel * 20
        self.yvel = random.uniform(7,14)
        

    def update(self, screen, frame):
        self.pos.x += self.xvel
        self.pos.y -= self.yvel
        self.yvel -= 0.1

        index = int(frame / (1+abs(self.xvel)))

        im = self.images[index]
        
        s = v2(im.get_size())/2
        screen.blit(im, self.pos - s)




def getFade(frames):
    l = []
    surf = pygame.Surface((1920,1080)).convert()
    surf.fill((0,0,0))
    for i in range(frames):
        s = surf.copy()
        s.set_alpha(int(255 * i/frames))
        l.append(s)
    return l
if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    clock = pygame.time.Clock()

    player_dir = "players"
    pawns = []
    for file in os.listdir(player_dir):
        if file.lower().endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(player_dir, file)
            pawn = TestPawn(path)
            particle = PawnParticle(pawn)
            pawns.append((pawn, particle))

    running = True
    frame = 0
    random.choice(pawns)[1].setAsMainPiece()
    fade = getFade(30)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))
        x_offset = 0
        for _, particle in pawns:
            if frame < len(particle.images):
                particle.update(screen, frame)

        if frame > 144 - len(fade):
            f_i = - 144 + len(fade) + frame
            f = fade[f_i]
            screen.blit(f, (0,0))
        pygame.display.flip()
        frame = frame + 1
        
        if frame >= 144:
            for _, particle in pawns:
                particle.reset()
            random.choice(pawns)[1].setAsMainPiece()
            # Sort the pawns list by particle xvel by absolute ascending
            pawns.sort(key=lambda p: abs(p[1].xvel), reverse=True)

            frame = 0
        clock.tick(144)

    pygame.quit()
