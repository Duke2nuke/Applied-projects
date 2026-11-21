# Day 26 — Q-Learning Gridworld Agent (Day B: AI/ML Python)

A reinforcement-learning agent that learns, from scratch and with no
human demos, to navigate a 6×6 gridworld: dodge a pit, get around two
walls, and reach the goal in the fewest steps. Tabular Q-learning,
numpy only, no downloads, no GPU.

## The grid

```
S . . # . .
. . . # . .
. . X # . .
. . . . . .
. # # # # .
. . . . . G
```

S = start, G = goal (+10, episode ends), X = pit (−10, episode ends),
`#` = wall (bumping into one leaves you where you are), every step
costs −0.1 so dawdling is punished. The shortest path to the goal is
10 steps: down the left column, across row 3, then down the right
column. The pit at (2, 2) sits right next to the gap in the vertical
wall, so a greedy agent that just heads for the goal falls in.

## What it does

- `gridworld.py` — the environment: `reset()`, `step(action)`,
  rewards, terminal states, and an ASCII renderer that draws a
  learned policy as arrows.
- `agent.py` — the Q-learning agent: a Q-table, epsilon-greedy action
  selection (explore early, exploit late, epsilon decays 1.0 → 0.05),
  and the Bellman update
  `Q(s,a) += α·(r + γ·max Q(s′,·) − Q(s,a))`, with α=0.1, γ=0.95.
- `run.py` — CLI: `train` (trains, saves `q_table.npy` and
  `results.json`), `demo` (trains and prints the learned policy),
  `eval` (loads the saved Q-table and re-evaluates it).

## How to run

```bash
pip install -r requirements.txt   # numpy only
python run.py demo                # train + show the learned policy
python run.py train               # train and save q_table.npy, results.json
python run.py eval                # re-evaluate the saved Q-table
python -m unittest test_qlearning -v
```

## Results (actually run, seed 42, 2000 episodes)

- Greedy policy over 100 eval episodes: **100% success, 10.0 mean
  steps to goal — exactly the optimal 10**, mean reward 9.10
  (10 for the goal minus 10 × 0.1 step cost).
- Learning curve: mean reward per episode −5.55 over the first 100
  episodes (the agent falls in the pit a lot early on) → 9.06 over
  the last 100.
- Learned policy, printed by `python run.py demo`:

```
S v ^ # ^ v
v < < # v v
v v X # v v
v > > > > v
v # # # # v
> > > > > G
```

The optimal route (down column 0, across row 3, down column 5) is
correct; arrows in cells the agent never visits after early training
are arbitrary, because their Q-values were never updated — that is
expected for tabular Q-learning, not a bug.

## Tests

10/10 pass (`python -m unittest test_qlearning -v`): wall and
off-grid bumps, goal/pit rewards and termination, the Q-update
checked against the Bellman formula by hand (including the
no-bootstrap terminal case), training converging to the optimal path,
the greedy policy avoiding the pit from the cell next to it, and
same-seed reproducibility.

## 2-minute explainer

**Problem:** teach an agent to reach a goal in a grid with a trap and
walls, with no labelled data and no human demonstrations — only
rewards. **Approach:** tabular Q-learning. The agent keeps a table of
Q(s, a): "how good is it to take action a in state s". It plays
2,000 episodes, each time updating the table with the Bellman
equation — the value of a move is the reward just received plus the
discounted best value of wherever it lands. Early on it explores
randomly (epsilon = 1.0); epsilon decays so it gradually trusts what
it has learned. **Results:** after training, the greedy policy reaches
the goal in 10 steps — the provable optimum — in 100 out of 100 test
episodes, and never falls in the pit. Mean reward climbs from −5.55
to 9.06. **Limits:** this is a tiny, fully known, deterministic
grid — the table has one entry per state-action pair, so it does not
scale to large or continuous worlds (that is where deep Q-networks
come in). It also learns only from its own trial and error; with a
stochastic or changing environment it would need retraining.
