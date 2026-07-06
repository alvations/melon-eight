# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Server robustness regressions.

Guards the fixes for:
  * difficulty must be resolved on a *fresh* run (/api/new), because the opening
    room is built at level 0, which is where the per-climb aggro-hold is decided;
  * a malformed JSON body (non-string sid/difficulty, non-numeric confidence)
    must not crash the request with a 500;
  * the in-memory session store must not grow without bound (forged sids).

Runnable two ways:
    python -m pytest tests/test_server_robustness.py -q
    python tests/test_game.py                 # plain runner discovers this file
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402
from hallway import _DIFF  # noqa: E402


def _client():
    return A.app.test_client()


# --- difficulty on a fresh run ---------------------------------------------

def test_new_run_honours_difficulty_header():
    # A Hard player's very first climb must be built as Hard, not the default.
    c = _client()
    r = c.post("/api/new", json={"arc": "hallway-eight"},
               headers={"X-Sid": "robust-hard", "X-Diff": "hard"})
    sid = r.get_json()["sid"]
    assert A.STATE[sid]["difficulty"] == "hard"


def test_new_run_defaults_to_normal_without_header():
    c = _client()
    r = c.post("/api/new", json={"arc": "hallway-eight"},
               headers={"X-Sid": "robust-normal"})
    sid = r.get_json()["sid"]
    assert A.STATE[sid]["difficulty"] == "normal"


# --- malformed input hardening ---------------------------------------------

def test_non_string_sid_body_does_not_crash():
    c = _client()
    r = c.post("/api/new", json={"arc": "hallway-eight", "sid": [1, 2]})
    assert r.status_code == 200
    assert r.get_json().get("sid"), "a fresh sid is minted instead of crashing"


def test_non_string_difficulty_body_does_not_crash():
    c = _client()
    r = c.post("/api/new",
               json={"arc": "hallway-eight", "difficulty": []},
               headers={"X-Sid": "robust-baddiff"})
    assert r.status_code == 200
    assert A.STATE["robust-baddiff"]["difficulty"] in _DIFF


def test_non_numeric_confidence_does_not_crash():
    c = _client()
    c.post("/api/new", json={"arc": "hallway-eight"},
           headers={"X-Sid": "robust-conf"})
    r = c.post("/api/act",
               json={"choice": "continue", "confidence": [1, 2]},
               headers={"X-Sid": "robust-conf"})
    assert r.status_code == 200
    # a string confidence must be ignored too, not summed into the average
    r2 = c.post("/api/act",
                json={"choice": "continue", "confidence": "5"},
                headers={"X-Sid": "robust-conf"})
    assert r2.status_code == 200


# --- session-store cap -----------------------------------------------------

def test_state_store_is_capped():
    saved_cap = A.MAX_SLOTS
    saved_state = dict(A.STATE)
    try:
        A.MAX_SLOTS = 5
        A.STATE.clear()
        c = _client()
        for i in range(20):
            c.post("/api/new", json={"arc": "hallway-eight"},
                   headers={"X-Sid": f"robust-cap-{i}"})
        assert len(A.STATE) <= A.MAX_SLOTS, len(A.STATE)
    finally:
        A.MAX_SLOTS = saved_cap
        A.STATE.clear()
        A.STATE.update(saved_state)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS  {name}")
