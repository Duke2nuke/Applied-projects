"""CLI for the Q-learning gridworld agent.

Usage:
    python run.py train [--episodes N] [--seed N]
        Train the agent, print the learned policy and eval numbers,
        save q_table.npy and results.json next to this file.

    python run.py demo
        Train with defaults, then print the grid with the learned
        policy drawn as arrows.

    python run.py eval
        Load the saved q_table.npy and evaluate the greedy policy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import QLearningAgent, evaluate, train
from gridworld import GridWorld

HERE = os.path.dirname(os.path.abspath(__file__))
Q_PATH = os.path.join(HERE, "q_table.npy")
RESULTS_PATH = os.path.join(HERE, "results.json")


def cmd_train(episodes: int, seed: int, show_demo: bool):
    env = GridWorld()
    agent = QLearningAgent(env.n_states, env.n_actions, seed=seed)
    rewards = train(env, agent, episodes=episodes)

    success, mean_steps, mean_reward = evaluate(env, agent)
    first100 = float(np.mean(rewards[:100]))
    last100 = float(np.mean(rewards[-100:]))

    results = {
        "episodes": episodes,
        "seed": seed,
        "eval_episodes": 100,
        "success_rate": success,
        "mean_steps_to_goal": mean_steps,
        "mean_eval_reward": mean_reward,
        "mean_reward_first_100_episodes": first100,
        "mean_reward_last_100_episodes": last100,
        "optimal_steps": 10,
    }
    np.save(Q_PATH, agent.q)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Trained {episodes} episodes (seed {seed}).")
    print(f"Mean reward, first 100 episodes: {first100:.2f}")
    print(f"Mean reward, last 100 episodes:  {last100:.2f}")
    print(f"Greedy policy over 100 eval episodes:")
    print(f"  success rate: {success:.0%}")
    print(f"  mean steps to goal: {mean_steps:.1f} (optimal is 10)")
    print(f"  mean reward: {mean_reward:.2f}")
    print(f"Saved {Q_PATH} and {RESULTS_PATH}.")
    if show_demo:
        print()
        print("Learned policy (arrows), S=start, G=goal, X=pit, #=wall:")
        print(env.render(policy=agent.greedy_policy()))


def cmd_eval():
    if not os.path.exists(Q_PATH):
        print("No saved q_table.npy — run `python run.py train` first.")
        raise SystemExit(1)
    env = GridWorld()
    agent = QLearningAgent(env.n_states, env.n_actions)
    agent.q = np.load(Q_PATH)
    success, mean_steps, mean_reward = evaluate(env, agent)
    print(f"Greedy policy over 100 eval episodes:")
    print(f"  success rate: {success:.0%}")
    print(f"  mean steps to goal: {mean_steps:.1f} (optimal is 10)")
    print(f"  mean reward: {mean_reward:.2f}")
    print()
    print(env.render(policy=agent.greedy_policy()))


def main():
    parser = argparse.ArgumentParser(description="Q-learning gridworld agent")
    sub = parser.add_subparsers(dest="command", required=True)
    p_train = sub.add_parser("train", help="train and save the Q-table")
    p_train.add_argument("--episodes", type=int, default=2000)
    p_train.add_argument("--seed", type=int, default=42)
    p_train.add_argument("--demo", action="store_true", help="print the learned policy")
    sub.add_parser("demo", help="train, then print the grid with the learned policy")
    sub.add_parser("eval", help="evaluate the saved Q-table")
    args = parser.parse_args()

    if args.command == "train":
        cmd_train(args.episodes, args.seed, show_demo=False)
    elif args.command == "demo":
        cmd_train(2000, 42, show_demo=True)
    elif args.command == "eval":
        cmd_eval()


if __name__ == "__main__":
    main()
