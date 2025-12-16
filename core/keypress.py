import pygame
import sys
from numpy import array as v2
import numpy
from core.console import handleConsoleEvent

def key_press_manager(obj):

    obj.mouse_pos = pygame.mouse.get_pos()
    obj.events = pygame.event.get()
    for event in obj.events:
        handleConsoleEvent(obj, event)
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()  # Ensure the program exits cleanly

    keys = pygame.key.get_pressed()

    for key, sign in [
        [pygame.K_w, "w"],
        [pygame.K_a, "a"],
        [pygame.K_s, "s"],
        [pygame.K_d, "d"],
        [pygame.K_x, "x"],
        [pygame.K_c, "c"],
        [pygame.K_z, "z"],
        [pygame.K_r, "r"],
        [pygame.K_1, "1"],
        [pygame.K_2, "2"],
        [pygame.K_3, "3"],
        [pygame.K_4, "4"],
        [pygame.K_TAB, "tab"],
        [pygame.K_LSHIFT, "shift"],
        [pygame.K_RETURN, "enter"],
        [pygame.K_SPACE, "space"],
        [pygame.K_BACKSPACE, "backspace"],
        [pygame.K_ESCAPE, "esc"],
        [pygame.K_DELETE, "del"],
        [pygame.K_LCTRL, "ctrl"],
        [pygame.K_t, "t"],
        [pygame.K_LEFT, "left"],
        [pygame.K_RIGHT, "right"],
        [pygame.K_UP, "up"],
        [pygame.K_DOWN, "down"],
        [pygame.K_F1, "f1"],
    ]:
        if keys[key]:
            if sign in obj.keypress:
                obj.keypress.remove(sign)
            elif sign not in obj.keypress_held_down:
                obj.keypress.append(sign)

            if sign not in obj.keypress_held_down:
                obj.keypress_held_down.append(sign)
        else:
            if sign in obj.keypress:
                obj.keypress.remove(sign)
            if sign in obj.keypress_held_down:
                obj.keypress_held_down.remove(sign)

    for x in range(3):
        sign = "mouse" + str(x)
        if pygame.mouse.get_pressed()[x]:
            if sign in obj.keypress:
                obj.keypress.remove(sign)
            elif sign not in obj.keypress_held_down:
                obj.keypress.append(sign)

            if sign not in obj.keypress_held_down:
                obj.keypress_held_down.append(sign)
        else:
            if sign in obj.keypress:
                obj.keypress.remove(sign)
            if sign in obj.keypress_held_down:
                obj.keypress_held_down.remove(sign)

