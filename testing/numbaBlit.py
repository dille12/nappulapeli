import numpy, pygame
import time

screen = pygame.display.set_mode((1920, 1080))
surf = pygame.Surface((1920, 1080))

import time


for x in range(100):
    t = time.time()
    arr = pygame.surfarray.array3d(surf)
    print("array3d time:", time.time() - t)
    t = time.time()
    surf = pygame.surfarray.make_surface(arr)
    print("surfarray time:", time.time() - t)