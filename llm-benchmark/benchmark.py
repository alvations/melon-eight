# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Benchmark an LLM against the deployed 8 game.

For every combination of ARC x DIFFICULTY x READING-LEVEL it runs N episodes and
measures how many rounds (committed loops) the agent needs to complete the arc
(eight correct calls in a row), and how many times it was reset trying.

    # zero-dependency smoke test against a local server (no model needed):
    python benchmark.py --base-url http://127.0.0.1:5000 --agent random --episodes 5

    # a local Hugging Face model as the player:
    python benchmark.py --base-url https://alvations-hallway8.hf.space \\
        --agent llm --model google/gemma-3n-e4b-it --episodes 3

Each loop, the agent is shown the room and its legal actions; it returns the
action(s); we call the server API to enact them. The server owns correctness and
never reveals the answer, so this is a genuine memory test.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import make_agent                    # noqa: E402
from eight_env import EightEnv                   # noqa: E402
from prompts import render_observation           # noqa: E402

ARCS = ["hallway-eight", "stairway8", "coach8"]
DIFFICULTIES = ["easy", "normal", "hard"]        # the three exposed "levels of eight"
REGISTERS = ["normal", "simple"]                 # the two reading levels


def _short(s: str, n: int = 100) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def run_episode(env: EightEnv, agent, register: str, allow_touch: bool,
                max_rounds: int) -> Dict:
    """One episode = climb the arc until a win or the round cap. Returns metrics."""
    env.reset()
    agent.reset()
    if hasattr(agent, "register"):
        agent.register = register
    payload = env.last
    history: List[str] = []
    rounds = 0            # committed loops (/api/act calls)
    attempts = 0          # resets (wrong calls or curious folds)
    steps = 0             # hard bound so a touch-only loop cannot spin forever
    step_cap = max_rounds * 4

    while rounds < max_rounds and steps < step_cap:
        steps += 1
        actions = env.available_actions(payload)
        moves = agent.act(payload, actions, history)
        obs = render_observation(payload, actions)
        committed = False

        for mv in moves:
            if mv.startswith("touch:") and allow_touch:
                res = env.touch(mv.split(":", 1)[1])
                if res.get("kind") == "fold":
                    attempts += 1
                    history = []                 # a fold restarts the climb
                    payload = res                # fold payload carries a level-0 room
                    committed = True
                    break
                history.append(f"{obs}\n  -> touched {mv.split(':',1)[1]}: "
                               f"{_short(res.get('line'))}")
                continue
            # directional commit
            res = env.act(mv)
            rounds += 1
            if res.get("won"):
                return {"won": True, "rounds": rounds, "attempts": attempts,
                        "server_attempts": res.get("attempts")}
            verdict = "correct" if res.get("correct") else "WRONG -> back to start"
            if res.get("correct"):
                history.append(f"{obs}\n  -> you chose {mv}: {verdict}")
            else:
                attempts += 1
                history = []                     # baseline is gone; new climb
            payload = res
            committed = True
            break

        if not committed:                        # no legal move taken; force one
            res = env.act("go_on")
            rounds += 1
            if res.get("won"):
                return {"won": True, "rounds": rounds, "attempts": attempts,
                        "server_attempts": res.get("attempts")}
            payload = res

    return {"won": False, "rounds": rounds, "attempts": attempts,
            "server_attempts": None}


def summarize(results: List[Dict]) -> Dict:
    wins = [r for r in results if r["won"]]
    won_rounds = [r["rounds"] for r in wins]
    return {
        "episodes": len(results),
        "wins": len(wins),
        "win_rate": round(len(wins) / len(results), 3) if results else 0.0,
        "mean_rounds_to_win": round(statistics.mean(won_rounds), 1) if won_rounds else None,
        "min_rounds_to_win": min(won_rounds) if won_rounds else None,
        "mean_attempts_to_win": (round(statistics.mean(r["attempts"] for r in wins), 1)
                                 if wins else None),
    }


def main():
    ap = argparse.ArgumentParser(description="Benchmark an LLM against the 8 game.")
    ap.add_argument("--base-url", default="http://127.0.0.1:5000",
                    help="game server (e.g. https://alvations-hallway8.hf.space)")
    ap.add_argument("--agent", default="random",
                    choices=["random", "always_go_on", "llm"])
    ap.add_argument("--model", default="google/gemma-3n-e4b-it",
                    help="HF model id for --agent llm")
    ap.add_argument("--arcs", nargs="+", default=ARCS, choices=ARCS)
    ap.add_argument("--difficulties", nargs="+", default=DIFFICULTIES,
                    choices=DIFFICULTIES)
    ap.add_argument("--registers", nargs="+", default=REGISTERS, choices=REGISTERS)
    ap.add_argument("--locale", default="en_US", help="X-Lang, e.g. de_DE, ja_JP")
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--max-rounds", type=int, default=120,
                    help="give up an episode after this many committed loops")
    ap.add_argument("--no-touch", action="store_true",
                    help="hide the Act 2 touch actions from the agent")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default="auto")
    ap.add_argument("--out", default=None, help="write full JSON results here")
    args = ap.parse_args()

    allow_touch = not args.no_touch
    agent = make_agent(
        args.agent, model_id=args.model, allow_touch=allow_touch,
        device=args.device, dtype=args.dtype)
    label = getattr(agent, "name", args.agent)
    print(f"agent: {label}   server: {args.base_url}   locale: {args.locale}\n")

    grid: Dict[str, Dict] = {}
    header = f"{'arc':<16}{'diff':<8}{'reading':<9}{'win%':>6}{'rounds':>9}{'resets':>8}"
    print(header)
    print("-" * len(header))

    for arc in args.arcs:
        for diff in args.difficulties:
            for reg in args.registers:
                env = EightEnv(args.base_url, arc=arc, difficulty=diff,
                               locale=args.locale)
                results = []
                for _ in range(args.episodes):
                    results.append(run_episode(env, agent, reg, allow_touch,
                                               args.max_rounds))
                s = summarize(results)
                grid[f"{arc}|{diff}|{reg}"] = {"summary": s, "episodes": results}
                rounds_str = "-" if s["mean_rounds_to_win"] is None else str(s["mean_rounds_to_win"])
                resets_str = "-" if s["mean_attempts_to_win"] is None else str(s["mean_attempts_to_win"])
                print(f"{arc:<16}{diff:<8}{reg:<9}"
                      f"{s['win_rate']*100:>5.0f}%"
                      f"{rounds_str:>9}{resets_str:>8}")

    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "results",
        f"{label}-{int(time.time())}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"agent": label, "base_url": args.base_url,
                   "locale": args.locale, "grid": grid}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nfull results -> {out}")


if __name__ == "__main__":
    main()
