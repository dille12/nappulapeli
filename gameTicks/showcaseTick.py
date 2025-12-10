import pygame
import math
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
    from pawn.teamLogic import Team


def showcaseTick(self: "Game"):
    SHOWCASE_DURATION = 5.0  # seconds per team
    TOTAL_TEAMS = len(self.allTeams)
    if TOTAL_TEAMS == 0:
        return

    # Determine which team is currently being showcased
    total_cycle_time = SHOWCASE_DURATION * TOTAL_TEAMS
    elapsed = (pygame.time.get_ticks() / 1000.0)
    if elapsed > total_cycle_time:
        self.GAMESTATE = "pawnGeneration"

    showcase_index = int(elapsed // SHOWCASE_DURATION)
    t_in_team = (elapsed % SHOWCASE_DURATION) / SHOWCASE_DURATION
    pulse = (math.sin(t_in_team * math.pi * 2) * 0.5 + 0.5)

    team = self.allTeams[showcase_index]
    screen = self.screen
    w, h = screen.get_size()
    cx, cy = w // 2, h // 2
    self.screen.fill((0,0,0))
    # --- background animation ---
    w, h = screen.get_size()
    pulse = (math.sin(t_in_team * math.pi * 2) * 0.5 + 0.5)
    s = pygame.Surface((w, h), pygame.SRCALPHA)

    num_lines = 180
    tilt_angle = math.radians(5)  # fixed direction
    cos_a, sin_a = math.cos(tilt_angle), math.sin(tilt_angle)
    base_color = team.color

    for i in range(num_lines):
        # random spacing and offset for natural look
        offset = (i * (w / num_lines) + (t_in_team * 800) % (w / num_lines)) % w
        x = offset
        y = 0

        # line extends beyond screen to avoid clipping
        length = h * 2.5
        dx = cos_a * length
        dy = sin_a * length

        # subtle variation per line
        alpha = int(60 + 120 * abs(math.sin(i * 0.3 + pulse * 4)))
        thickness = 1 + int(2 * abs(math.sin(i * 0.7 + pulse * 6)))

        color = (*base_color, alpha)
        start_pos = (x - dy, y + dx)
        end_pos = (x - dy + dx * 1.2, y + dx + dy * 1.2)
        print(start_pos, end_pos)

        pygame.draw.line(s, color, start_pos, end_pos, thickness)

    # fade/pulse overall intensity
    s.set_alpha(int(120 + 60 * pulse))
    screen.blit(s, (0, 0), special_flags=pygame.BLEND_ADD)

    # --- text ---
    font = pygame.font.SysFont("arialblack", int(h * 0.12))
    text_surf = font.render(f"TEAM {showcase_index + 1}", True, team.color)
    text_surf = pygame.transform.rotate(text_surf, -5)
    text_rect = text_surf.get_rect(bottomleft=(int(w * 0.05), int(h * 0.95)))
    screen.blit(text_surf, text_rect)

    # --- pawn showcase animation ---
    pawns = team.pawns
    num = len(pawns)
    if num == 0:
        return

    base_y = cy + 100
    spacing = 120
    entry_progress = min(1.0, t_in_team * 1.5)  # smooth entrance speed factor

    for i, pawn in enumerate(pawns):
        depth = i / num
        brightness = max(0.3, 1.0 - depth * 0.7)
        shade = tuple(int(c * brightness) for c in team.color)
        pawn_img = pygame.transform.smoothscale(pawn.levelUpImage.copy(), (80, 80))

        # offset and timing for staggered entry
        delay = i * 0.1
        local_t = max(0.0, (t_in_team - delay) / (1.0 - delay))
        local_t = min(local_t, 1.0)
        eased = 1 - (1 - local_t) ** 3  # ease-out cubic

        x = w + 200 - eased * (w // 2)
        y = base_y - i * spacing * 0.3
        pawn_img.set_alpha(int(255 * brightness * eased))
        screen.blit(pawn_img, pawn_img.get_rect(center=(x, y)))

    # Optional glow pulse behind pawns
    #glow_radius = 250 + 100 * pulse
    #glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
    #pygame.draw.circle(glow_surf, (*team.color, 60), (glow_radius, glow_radius), int(glow_radius))
    #screen.blit(glow_surf, (cx - glow_radius, cy - glow_radius), special_flags=pygame.BLEND_ADD)
