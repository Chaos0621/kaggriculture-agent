"""Run local Kaggriculture matches and print a compact result summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--opponent", default="starter", choices=["pass", "random", "starter"])
    parser.add_argument("--replay", type=Path, help="save the final episode replay JSON")
    return parser.parse_args()


def main() -> None:
    try:
        from kaggle_environments import make
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency. Run: python -m pip install -r requirements.txt"
        ) from exc

    args = parse_args()
    if args.episodes < 1:
        raise SystemExit("--episodes must be at least 1")

    rewards: list[float] = []
    wins = draws = losses = 0
    final_env = None

    for episode in range(args.episodes):
        env = make(
            "kaggriculture",
            configuration={"episodeSteps": 720, "seed": episode},
            debug=True,
        )
        env.run(["main.py", args.opponent])
        final_env = env
        ours, theirs = env.steps[-1]
        our_reward = float(ours.reward or 0)
        their_reward = float(theirs.reward or 0)
        rewards.append(our_reward)
        if our_reward > their_reward:
            wins += 1
        elif our_reward < their_reward:
            losses += 1
        else:
            draws += 1
        print(
            f"episode={episode:02d} reward={our_reward:.1f} "
            f"opponent={their_reward:.1f} status={ours.status}"
        )

    print(
        f"summary episodes={args.episodes} wins={wins} draws={draws} "
        f"losses={losses} mean_reward={mean(rewards):.1f}"
    )

    if args.replay and final_env is not None:
        args.replay.parent.mkdir(parents=True, exist_ok=True)
        args.replay.write_text(json.dumps(final_env.toJSON()), encoding="utf-8")
        print(f"saved replay: {args.replay}")


if __name__ == "__main__":
    main()
