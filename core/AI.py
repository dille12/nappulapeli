from typing import TYPE_CHECKING
import numpy as np
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
    from pawn.teamLogic import Team

import tensorflow as tf
from tensorflow.keras import layers, models

def constructTeamVisibility(self: "Game"):
    n_teams = len(self.allTeams)
    H, W = self.map.grid.shape

    # shape: (n_teams, H, W)
    team_vis = np.zeros((n_teams, H, W), dtype=np.float32)

    for pawn in self.pawnHelpList:
        team_i = pawn.team.i
        for (x, y) in pawn.getVisibility():
            if 0 <= y < H and 0 <= x < W:
                team_vis[team_i, y, x] = 1.0  # visible tile

    # Alternative: precompute all at once
    hostile_per_team = np.empty_like(team_vis)
    for i in range(n_teams):
        if n_teams > 1:
            hostile_per_team[i] = np.max(np.delete(team_vis, i, axis=0), axis=0)
        else:
            hostile_per_team[i].fill(0.0)

    self.teamVisibility = team_vis
    self.teamHostileVisibility = hostile_per_team

import pygame
import numpy as np


def runAI(pawn: "Pawn"):
    app = pawn.app
    H, W = app.AGENT.map_h, app.AGENT.map_w

    inputTensor = np.zeros((H, W, 4), dtype=np.float32)

    x,y = pawn.getOwnCell()  # assuming getOwnCell returns (y, x)
    if 0 <= y < H and 0 <= x < W:
        inputTensor[y, x, 0] = 1.0

    inputTensor[:, :, 1] = app.FLOORMATRIX.astype(np.float32)
    inputTensor[:, :, 2] = app.teamVisibility[pawn.team.i].astype(np.float32)
    inputTensor[:, :, 3] = app.teamHostileVisibility[pawn.team.i].astype(np.float32)
    probs2d = app.AGENT.predict_goal_tile(inputTensor)
    flat_probs = probs2d.flatten()
    choice_index = np.random.choice(len(flat_probs), p=flat_probs)
    return np.unravel_index(choice_index, probs2d.shape)

def drawGridMiniMap(self, grid: np.ndarray, pos="topleft", scale=4, alpha=200):
    """
    Visualize a 2D grid (e.g., visibility map) on the screen.
    Each cell -> one pixel, scaled by 'scale'.
    grid: np.ndarray (H, W), values 0–1
    pos: corner placement ('topleft', 'topright', 'bottomleft', 'bottomright')
    """
    H, W = grid.shape
    surf = pygame.Surface((H, W)).convert_alpha()
    arr = (grid * 255).astype(np.uint8)
    rgb = np.stack([arr]*3, axis=-1)
    
    pygame.surfarray.blit_array(surf, rgb)
    surf = pygame.transform.scale(surf, (W*scale, H*scale))
    surf.set_alpha(alpha)

    sw, sh = self.screen.get_size()
    rect = surf.get_rect()
    if pos == "topleft":
        rect.topleft = (10, 10)
    elif pos == "topright":
        rect.topright = (sw - 10, 10)
    elif pos == "bottomleft":
        rect.bottomleft = (10, sh - 10)
    elif pos == "bottomright":
        rect.bottomright = (sw - 10, sh - 10)

    self.screen.blit(surf, rect)

