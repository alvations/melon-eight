#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Level-composition QE: generate levels in English, piece together the
translated parts, and score each composed level.

Per the localization spec, the real test isn't a single line, it's whether the
lines *assembled into a level* still read fluently as a whole. This harness:

  1. Generates N levels for an arc with English (deterministic seeds).
  2. Re-renders each level in each target locale (same seed -> same lines).
  3. Scores each composed level as the mean of the audited postedit_score of the
     lines that compose it (so the level score is grounded in, and auditable
     against, the per-line audit trail in lines.json), and flags any line that
     fell back to English ("leak").
  4. Writes data/i18n/levels.json in the requested shape and prints, per locale,
     the mean/min level score and how many of the N levels reach >= PASS (95).

If a locale does not reach the >=95 gate over the sample, revise the weakest
lines in data/i18n/src/<locale>.json (raise their postedit_score by genuinely
improving the postedit), re-run i18n_ingest + i18n_compile, and re-run this.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n  # noqa: E402
from hallway import Hallway  # noqa: E402
from memory import PlayerMemory  # noqa: E402

LINES = os.path.join(i18n.I18N_DIR, "lines.json")
LEVELS = os.path.join(i18n.I18N_DIR, "levels.json")
PASS = 95


def line_score(lines: dict, key: str, loc: str):
    """Audited score for a line: postedit_score if present, else score."""
    e = (lines.get(key) or {}).get(loc)
    if not isinstance(e, dict):
        return None
    return e.get("postedit_score", e.get("score"))


def compose(room: dict) -> str:
    return room["heading"] + "\n" + "\n".join(room["sentences"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arc", default="coach8")
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--locales", nargs="*", default=["de_DE", "ja_JP"])
    args = ap.parse_args()

    i18n.clear_cache()
    lines = json.load(open(LINES, encoding="utf-8"))
    hall = Hallway(args.arc)

    out = json.load(open(LEVELS, encoding="utf-8")) if os.path.exists(LEVELS) else {}
    arc_out = out.setdefault(args.arc, {})
    summary = {loc: {"scores": [], "leaks": 0} for loc in args.locales}

    for i in range(args.n):
        # same seed + same (reset) memory -> identical line selection per locale
        seed = 1000 + i
        mem = PlayerMemory(level=i % 8)
        en_room = hall.build(mem, random.Random(seed), "en_US")
        keys = en_room["_keys"]
        entry = arc_out.setdefault(str(i), {})
        entry["en_US"] = {"level_text": compose(en_room)}

        for loc in args.locales:
            mem2 = PlayerMemory(level=i % 8)
            room = hall.build(mem2, random.Random(seed), loc)
            scores, leaks = [], []
            for k in keys:
                s = line_score(lines, k, loc)
                if s is None:
                    leaks.append(k)
                else:
                    scores.append(s)
            # a leaked (untranslated) line counts as 0 for the level
            all_scores = scores + [0] * len(leaks)
            lvl = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
            entry[loc] = {"level_text": compose(room), "score": lvl,
                          "leaks": len(leaks)}
            summary[loc]["scores"].append(lvl)
            summary[loc]["leaks"] += len(leaks)

    with open(LEVELS, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"arc={args.arc}  levels={args.n}")
    for loc in args.locales:
        sc = summary[loc]["scores"]
        mean = round(sum(sc) / len(sc), 1)
        passes = sum(1 for x in sc if x >= PASS)
        gate = "PASS" if mean >= PASS else "REVISE"
        print(f"  {loc}: mean={mean}  min={min(sc)}  >=95: {passes}/{len(sc)}  "
              f"leaks={summary[loc]['leaks']}  -> {gate}")


if __name__ == "__main__":
    main()
