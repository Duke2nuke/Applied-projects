"""Tests for the Q-learning gridworld (run: python -m unittest test_qlearning -v)."""

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import QLearningAgent, evaluate, train
from gridworld import GridWorld


class TestGridWorld(unittest.TestCase):
    def setUp(self):
        self.env = GridWorld()

    def test_reset_starts_at_start(self):
        self.assertEqual(self.env.reset(), self.env.state_id((0, 0)))

    def test_wall_bump_stays_put_and_costs_a_step(self):
        self.env.reset()
        # move right twice to (0, 2), then right into the wall at (0, 3)
        for _ in range(2):
            self.env.step(1)
        state, reward, done = self.env.step(1)
        self.assertEqual(self.env.pos_of(state), (0, 2))
        self.assertEqual(reward, -0.1)
        self.assertFalse(done)

    def test_off_grid_bump_stays_put(self):
        self.env.reset()
        state, _, _ = self.env.step(0)  # up from (0, 0)
        self.assertEqual(self.env.pos_of(state), (0, 0))

    def test_goal_gives_plus_10_and_ends(self):
        self.env.state = (5, 4)
        state, reward, done = self.env.step(1)
        self.assertEqual(reward, 10.0)
        self.assertTrue(done)

    def test_pit_gives_minus_10_and_ends(self):
        self.env.state = (2, 1)
        state, reward, done = self.env.step(1)
        self.assertEqual(reward, -10.0)
        self.assertTrue(done)


class TestQLearning(unittest.TestCase):
    def test_q_update_matches_bellman_formula(self):
        agent = QLearningAgent(36, 4, alpha=0.5, gamma=0.9, epsilon=0.0)
        agent.q[0, 1] = 1.0
        agent.q[1] = [0.0, 2.0, 0.0, 0.0]
        agent.update(state=0, action=1, reward=1.0, next_state=1, done=False)
        # target = 1.0 + 0.9 * 2.0 = 2.8; new Q = 1.0 + 0.5 * (2.8 - 1.0) = 1.9
        self.assertAlmostEqual(agent.q[0, 1], 1.9)

    def test_terminal_update_has_no_bootstrap(self):
        agent = QLearningAgent(36, 4, alpha=1.0, gamma=0.9, epsilon=0.0)
        agent.q[1] = [5.0, 5.0, 5.0, 5.0]
        agent.update(state=0, action=1, reward=10.0, next_state=35, done=True)
        self.assertAlmostEqual(agent.q[0, 1], 10.0)

    def test_training_converges_to_optimal_path(self):
        env = GridWorld()
        agent = QLearningAgent(env.n_states, env.n_actions, seed=42)
        train(env, agent, episodes=2000)
        success, mean_steps, _ = evaluate(env, agent, episodes=100)
        self.assertEqual(success, 1.0)  # reaches the goal every time
        self.assertLessEqual(mean_steps, 10.5)  # optimal is 10 steps

    def test_greedy_policy_avoids_the_pit(self):
        env = GridWorld()
        agent = QLearningAgent(env.n_states, env.n_actions, seed=42)
        train(env, agent, episodes=2000)
        # from (2, 1), the greedy move must NOT be right (into the pit)
        self.assertNotEqual(agent.greedy_action(env.state_id((2, 1))), 1)

    def test_training_is_reproducible_with_same_seed(self):
        def run_once():
            env = GridWorld()
            agent = QLearningAgent(env.n_states, env.n_actions, seed=7)
            train(env, agent, episodes=500)
            return agent.q.copy()

        np.testing.assert_array_equal(run_once(), run_once())


if __name__ == "__main__":
    unittest.main()
