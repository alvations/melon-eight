#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Per-locale level-composition QE, straight from one locale's src files.

Read-only and self-contained: it does NOT read data/i18n/lines.json and writes
nothing, so it is safe to run concurrently while other locales are still being
authored. It reproduces scripts/i18n_levelqe.py's level score (the mean of the
composing lines' postedit_score, with any missing/untranslated line counted as
0 = a "leak") but sources the scores from data/i18n/src/<loc>.json plus
data/i18n/src/<arc>/<loc>.json instead of the merged audit trail.

Use it to iterate a single locale to the >=95 gate BEFORE the shared
ingest/compile/levelqe run:

    PYTHONPATH=. python scripts/i18n_selfqe.py --loc it_IT --show-weak 12

Exit code 0 iff every requested arc reaches mean >= 95 with 0 leaks.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n  # noqa: E402
from hallway import Hallway  # noqa: E402
from memory import PlayerMemory  # noqa: E402

PASS = 95


def load_src_scores(loc: str) -> dict:
    """key -> postedit_score (falling back to score) from this locale's src
    files: the flat data/i18n/src/<loc>.json and every per-arc
    data/i18n/src/<arc>/<loc>.json."""
    scores = {}
    paths = [os.path.join(i18n.I18N_DIR, "src", f"{loc}.json")]
    paths += sorted(glob.glob(os.path.join(i18n.I18N_DIR, "src", "*", f"{loc}.json")))
    for p in paths:
        if not os.path.exists(p):
            continue
        for k, v in json.load(open(p, encoding="utf-8")).items():
            if isinstance(v, dict):
                s = v.get("postedit_score", v.get("score"))
                if s is not None:
                    scores[k] = s
    return scores


def level_keys(hall: Hallway, n: int):
    """The composing keys of each of the N deterministic levels (same seeds as
    scripts/i18n_levelqe.py)."""
    out = []
    for i in range(n):
        mem = PlayerMemory(level=i % 8)
        room = hall.build(mem, random.Random(1000 + i), "en_US")
        out.append(room["_keys"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loc", required=True)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--arcs", nargs="*",
                    default=["coach8", "hallway-eight", "stairway8"])
    ap.add_argument("--show-weak", type=int, default=0,
                    help="also print the N lowest-scoring keys these levels use")
    args = ap.parse_args()

    scores = load_src_scores(args.loc)
    all_pass = True
    for arc in args.arcs:
        hall = Hallway(arc)
        keysets = level_keys(hall, args.n)
        lvls, leaks, used = [], set(), set()
        for keys in keysets:
            row = []
            for k in keys:
                used.add(k)
                if k in scores:
                    row.append(scores[k])
                else:
                    row.append(0)
                    leaks.add(k)
            lvls.append(round(sum(row) / len(row), 1) if row else 0)
        mean = round(sum(lvls) / len(lvls), 1)
        passes = sum(1 for x in lvls if x >= PASS)
        gate = "PASS" if (mean >= PASS and not leaks) else "REVISE"
        if gate != "PASS":
            all_pass = False
        print(f"{args.loc} {arc}: mean={mean}  min={min(lvls)}  "
              f">=95: {passes}/{len(lvls)}  leaks={len(leaks)}  -> {gate}")
        if leaks:
            print("  LEAK (untranslated/missing) keys:", sorted(leaks)[:20])
        if args.show_weak:
            weak = sorted(((scores.get(k, 0), k) for k in used))[:args.show_weak]
            print(f"  weakest {args.show_weak} lines used by these levels:")
            for s, k in weak:
                print(f"    {s}  {k}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
