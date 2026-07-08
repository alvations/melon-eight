# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""End-to-end game-logic audit: drive full runs through the real Flask app and
check the load-bearing invariants on every outcome, for EVERY arc and difficulty.

Runs headless against the app test client (X-Sid / X-Diff headers, no cookies,
exactly as the web client talks to it). The server owns correctness and never
sends the answer, so the omniscient checks peek server-side state to know the
truth, the same trick the rest of the suite uses.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402
from hallway import list_arcs, GOAL, DIFFICULTIES  # noqa: E402
from memory import PlayerMemory  # noqa: E402
from hallway import Hallway  # noqa: E402

ARCS = [a["id"] for a in list_arcs()]
DIFFS = list(DIFFICULTIES)          # easy, normal, hard, insane
_client = A.app.test_client()


def _new(arc, diff, sid):
    return _client.post("/api/new", json={"arc": arc},
                        headers={"X-Sid": sid, "X-Diff": diff}).get_json()


def _act(sid, diff, choice):
    return _client.post("/api/act", json={"choice": choice, "confidence": 3},
                        headers={"X-Sid": sid, "X-Diff": diff}).get_json()


def _truth(sid):
    return A.STATE[sid]["room"]["_has_anomaly"]


def _leaks(payload):
    return [k for k in (payload.get("room", {}) or {}) if k.startswith("_")]


def test_omniscient_correct_play_always_wins_in_goal_calls():
    # The whole loop, end to end: a player who always makes the correct call must
    # win in EXACTLY GOAL correct calls, on every arc and difficulty, never resets,
    # never leaks. This exercises new/act, the ramp, held items, hard continuity,
    # and the insane run-baseline all at once.
    for arc in ARCS:
        for diff in DIFFS:
            for t in range(20):
                sid = f"omni-{arc}-{diff}-{t}"
                p = _new(arc, diff, sid)
                assert not _leaks(p), (sid, "leak on /new", _leaks(p))
                calls = 0
                for _ in range(GOAL + 5):
                    choice = "back" if _truth(sid) else "continue"
                    r = _act(sid, diff, choice)
                    assert r.get("correct") is True, (sid, "omniscient call marked wrong")
                    assert not _leaks(r), (sid, "leak on /act", _leaks(r))
                    calls += 1
                    if r.get("won"):
                        break
                assert r.get("won"), (sid, "omniscient play never won")
                assert calls == GOAL, (sid, f"won in {calls} calls, expected {GOAL}")


def test_correctness_formula_and_reset_hold_under_random_play():
    # For arbitrary play, correct == ((choice=='back') == has_anomaly); a wrong
    # call resets to level 0, a correct non-final call advances. On every arc,
    # difficulty, and step.
    for arc in ARCS:
        for diff in DIFFS:
            for t in range(15):
                sid = f"rand-{arc}-{diff}-{t}"
                _new(arc, diff, sid)
                rng = random.Random(t)
                for _ in range(24):
                    ha = _truth(sid)
                    choice = rng.choice(["back", "continue"])
                    r = _act(sid, diff, choice)
                    expect = ((choice == "back") == ha)
                    assert r.get("correct") == expect, (sid, "formula broke")
                    assert not _leaks(r), (sid, "leak", _leaks(r))
                    if not r.get("won") and not expect:
                        assert r.get("level") == 0, (sid, "wrong call did not reset")


def test_anomaly_always_lands_on_a_shown_detail():
    # A player can never be asked to notice a change to a detail that was not
    # shown this loop; and has_anomaly matches whether any property actually moved.
    for arc in ARCS:
        for diff in DIFFS:
            for seed in range(40):
                mem = PlayerMemory(level=0)
                for lvl in range(GOAL):
                    mem.level = lvl
                    pub = Hallway(arc).build(mem, random.Random(seed * 97 + lvl),
                                             "en_US", diff)
                    props = [p for p in pub["_anomaly_props"] if p]
                    for ap in props:
                        assert ap in pub["shown"], (arc, diff, seed, lvl, ap, "not shown")
                    assert pub["_has_anomaly"] == bool(props), \
                        (arc, diff, seed, lvl, "has_anomaly/props mismatch")
