"""A small deterministic gridworld environment.

Layout (6x6, rows top to bottom, cols left to right):

    S . . # . .
    . . . # . .
    . . X # . .
    . . . . . .
    . # # # # .
    . . . . . G

S = start (0, 0)   G = goal (5, 5), reward +10, episode ends
# = wall (bumping into one leaves you where you are)
X = pit (2, 2), reward -10, episode ends
. = empty floor, each step costs -0.1

Actions: 0=up, 1=right, 2=down, 3=left.
"""

from __future__ import annotations

import numpy as np

ACTIONS = ("up", "right", "down", "left")
_DELTAS = ((-1, 0), (0, 1), (1, 0), (0, -1))

STEP_COST = -0.1
GOAL_REWARD = 10.0
PIT_REWARD = -10.0


class GridWorld:
    """Deterministic gridworld with walls, one goal and one pit."""

    def __init__(self, rows: int = 6, cols: int = 6):
        self.rows = rows
        self.cols = cols
        self.start = (0, 0)
        self.goal = (5, 5)
        self.pit = (2, 2)
        self.walls = {
            (0, 3), (1, 3), (2, 3),  # vertical wall, gap at row 3
            (4, 1), (4, 2), (4, 3), (4, 4),  # horizontal wall, gaps at col 0 and 5
        }
        self.state = self.start
        self.n_states = rows * cols
        self.n_actions = 4

    # -- helpers ---------------------------------------------------------
    def state_id(self, pos) -> int:
        return pos[0] * self.cols + pos[1]

    def pos_of(self, state_id: int):
        return (state_id // self.cols, state_id % self.cols)

    def is_wall(self, pos) -> bool:
        return pos in self.walls

    def is_terminal(self, pos) -> bool:
        return pos == self.goal or pos == self.pit

    # -- environment API -------------------------------------------------
    def reset(self) -> int:
        self.state = self.start
        return self.state_id(self.state)

    def step(self, action: int):
        """Take one step. Returns (next_state_id, reward, done)."""
        if self.is_terminal(self.state):
            return self.state_id(self.state), 0.0, True
        dr, dc = _DELTAS[action]
        nxt = (self.state[0] + dr, self.state[1] + dc)
        if (
            nxt[0] < 0 or nxt[0] >= self.rows
            or nxt[1] < 0 or nxt[1] >= self.cols
            or nxt in self.walls
        ):
            nxt = self.state  # bump: stay put, still pay the step cost
        self.state = nxt
        if nxt == self.goal:
            return self.state_id(nxt), GOAL_REWARD, True
        if nxt == self.pit:
            return self.state_id(nxt), PIT_REWARD, True
        return self.state_id(nxt), STEP_COST, False

    def render(self, policy=None) -> str:
        """ASCII picture of the grid. With a policy, floor cells show arrows."""
        arrows = {"up": "^", "right": ">", "down": "v", "left": "<"}
        lines = []
        for r in range(self.rows):
            cells = []
            for c in range(self.cols):
                pos = (r, c)
                if pos == self.start:
                    cells.append("S")
                elif pos == self.goal:
                    cells.append("G")
                elif pos == self.pit:
                    cells.append("X")
                elif pos in self.walls:
                    cells.append("#")
                elif policy is not None:
                    cells.append(arrows[ACTIONS[policy[self.state_id(pos)]]])
                else:
                    cells.append(".")
            lines.append(" ".join(cells))
        return "\n".join(lines)
