import pygame
import numpy as np
import time

pygame.init()

W, H = 1200, 800           # screen size
WORLD_W, WORLD_H = 12000, 8000
TILE_W, TILE_H = 1200, 800

screen = pygame.display.set_mode((W, H))
clock = pygame.time.Clock()

# --- generate big noise array
print("Generating noise...")
noise = (np.random.rand(WORLD_H, WORLD_W) * 255).astype(np.uint8)

# --- slice into tiles
tiles = []
for y in range(0, WORLD_H, TILE_H):
    row = []
    for x in range(0, WORLD_W, TILE_W):
        sub = noise[y:y+TILE_H, x:x+TILE_W].transpose()
        surf = pygame.surfarray.make_surface(np.stack([sub]*3, axis=-1))
        row.append(surf)
    tiles.append(row)

fullMap = pygame.surfarray.make_surface(np.stack([noise.transpose()]*3, axis=-1))

ROWS = len(tiles)
COLS = len(tiles[0])
print(f"Tiled into {ROWS}x{COLS} = {ROWS*COLS} surfaces")

# --- camera
cam_x, cam_y = 0, 0
speed = 10
frames = 0
blit_time_total = 0.0

running = True
while running:
    

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
    keys = pygame.key.get_pressed()
    if keys[pygame.K_RIGHT]:
        cam_x = min(cam_x + speed, WORLD_W - W)
    if keys[pygame.K_LEFT]:
        cam_x = max(cam_x - speed, 0)
    if keys[pygame.K_DOWN]:
        cam_y = min(cam_y + speed, WORLD_H - H)
    if keys[pygame.K_UP]:
        cam_y = max(cam_y - speed, 0)

    MODE = 1

    screen.fill((0,0,0))

    t0 = time.perf_counter()

    if MODE:

        # determine visible tile range
        x0 = cam_x // TILE_W
        y0 = cam_y // TILE_H
        x1 = (cam_x + W) // TILE_W
        y1 = (cam_y + H) // TILE_H

        for ty in range(y0, y1+1):
            for tx in range(x0, x1+1):
                tile = tiles[ty][tx]
                dest_x = tx*TILE_W - cam_x
                dest_y = ty*TILE_H - cam_y
                screen.blit(tile, (dest_x, dest_y))
    else:
        screen.blit(fullMap, (-cam_x, -cam_y))

    t1 = time.perf_counter()
    blit_time_total += (t1 - t0)
    frames += 1

    pygame.display.flip()
    clock.tick(60)

print(f"Average blit+loop time: {1000*blit_time_total/frames:.2f} ms per frame")
pygame.quit()
