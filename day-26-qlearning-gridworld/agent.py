"""Tabular Q-learning agent for the gridworld.

Q-learning update (the one line that matters):

    Q(s, a) += alpha * (r + gamma * max_a' Q(s', a') - Q(s, a))

Action selection is epsilon-greedy: with probability epsilon pick a
random action (explore), otherwise pick the best-known action (exploit).
Epsilon decays over training so the agent explores early and exploits
late.
"""

from __future__ import annotations

import numpy as np

from gridworld import GridWorld


class QLearningAgent:
    def __init__(
        self,
        n_states: int,
        n_actions: int,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        seed: int = 42,
    ):
        self.q = np.zeros((n_states, n_actions), dtype=float)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.rng = np.random.default_rng(seed)

    def act(self, state: int) -> int:
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, self.q.shape[1]))
        return int(np.argmax(self.q[state]))

    def greedy_action(self, state: int) -> int:
        return int(np.argmax(self.q[state]))

    def update(self, state: int, action: int, reward: float, next_state: int, done: bool):
        target = reward
        if not done:
            target += self.gamma * float(np.max(self.q[next_state]))
        self.q[state, action] += self.alpha * (target - self.q[state, action])

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def greedy_policy(self) -> np.ndarray:
        return np.argmax(self.q, axis=1)


def train(env: GridWorld, agent: QLearningAgent, episodes: int = 2000, max_steps: int = 100):
    """Train the agent. Returns a list of total reward per episode."""
    rewards = []
    for _ in range(episodes):
        state = env.reset()
        total = 0.0
        for _ in range(max_steps):
            action = agent.act(state)
            next_state, reward, done = env.step(action)
            agent.update(state, action, reward, next_state, done)
            total += reward
            state = next_state
            if done:
                break
        rewards.append(total)
        agent.decay_epsilon()
    return rewards


def evaluate(env: GridWorld, agent: QLearningAgent, episodes: int = 100, max_steps: int = 100):
    """Run the greedy policy. Returns (success_rate, mean_steps, mean_reward)."""
    successes = 0
    steps_list = []
    rewards = []
    for _ in range(episodes):
        state = env.reset()
        total = 0.0
        steps = 0
        for _ in range(max_steps):
            action = agent.greedy_action(state)
            state, reward, done = env.step(action)
            total += reward
            steps += 1
            if done:
                if env.pos_of(state) == env.goal:
                    successes += 1
                break
        steps_list.append(steps)
        rewards.append(total)
    return successes / episodes, float(np.mean(steps_list)), float(np.mean(rewards))
