import pygame
import math
import random

class AnimatedTextRenderer:
    def __init__(self, app):
        self.app = app
        self.time = 0.0

    def tick(self):
        self.time += self.app.deltaTime

    def getRainBowColor(self, speed = 60, i = 0):
        t = self.time
        hue = (t * speed - i * 25) % 360
        c = pygame.Color(0)
        c.hsva = (hue, 100, 100, 100)
        return c

    def render(
        self,
        font,
        text,
        color=(255, 255, 255),
        wave_amp=0.0,
        wave_freq=4.0,
        wave_speed=4.0,
        jitter_amp=0.0,
        jitter_freq=30.0,
        shake_amp=0.0,
        fade_in=0.0,
        fade_out=0.0,
        typewriter_speed=0.0,
        rainbow=False,
        outline=0,
        outline_color=(0, 0, 0),
        glow=0,
        glow_color=(255, 255, 255),
    ):
        t = self.time

        if typewriter_speed > 0:
            visible_chars = int(t * typewriter_speed)
            text = text[:visible_chars]

        glyphs = []
        max_up = 0
        max_down = 0
        x = 0

        for i, ch in enumerate(text):
            base_surf = font.render(ch, True, color)
            y_off = 0

            if wave_amp > 0:
                phase = (x * 0.05 * wave_freq) + t * wave_speed
                y_off += math.sin(phase) * wave_amp

            if jitter_amp > 0:
                y_off += math.sin(t * jitter_freq + i * 13.37) * jitter_amp

            max_up = max(max_up, -y_off)
            max_down = max(max_down, y_off)

            glyphs.append((base_surf, x, y_off, i))
            x += base_surf.get_width()

        height = font.get_height() + int(max_up + max_down)
        surface = pygame.Surface((x, height), pygame.SRCALPHA)

        for surf, gx, gy, i in glyphs:
            draw_surf = surf

            if rainbow:
                c = self.getRainBowColor(i = i)
                draw_surf = font.render(text[i], True, c)

            if outline > 0:
                for ox in range(-outline, outline + 1):
                    for oy in range(-outline, outline + 1):
                        if ox * ox + oy * oy <= outline * outline:
                            o = font.render(text[i], True, outline_color)
                            surface.blit(o, (gx + ox, gy + oy + max_up))

            if glow > 0:
                for g in range(glow, 0, -1):
                    alpha = int(255 * (g / glow) * 0.25)
                    glow_surf = font.render(text[i], True, glow_color)
                    glow_surf.set_alpha(alpha)
                    surface.blit(glow_surf, (gx, gy + max_up))

            surface.blit(draw_surf, (gx, gy + max_up))

        if shake_amp > 0:
            dx = random.uniform(-shake_amp, shake_amp)
            dy = random.uniform(-shake_amp, shake_amp)
            shaken = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            shaken.blit(surface, (dx, dy))
            surface = shaken

        if fade_in > 0:
            a = min(1.0, t / fade_in)
            surface.set_alpha(int(a * 255))

        if fade_out > 0:
            a = max(0.0, 1.0 - t / fade_out)
            surface.set_alpha(int(a * 255))

        return surface
