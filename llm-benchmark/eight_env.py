# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""A tiny HTTP client that turns the deployed game into a step-able environment.

The game server is the source of truth for correctness (`correct = (choice ==
"back") == has_anomaly`); this client never sees the answer, exactly like a human
player. It exposes three moves against the public API:

    env = EightEnv("http://127.0.0.1:5000", arc="hallway-eight",
                   difficulty="normal", locale="en_US")
    obs = env.reset()                 # POST /api/new  -> first loop
    res = env.touch("door")           # POST /api/interact (optional, flavour)
    res = env.act("go_on")            # POST /api/act  -> verdict + next loop

`act` returns the server verdict for the loop just committed AND the next loop's
room, so the caller can read `res["correct"]`, `res["won"]`, `res["level"]`, and
`res["room"]`. A wrong call resets the run to level 0 (the server does this); a
win resets progress but reports `res["attempts"]` (how many runs it took).
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, Optional

import requests

# The player-facing verbs the agents speak, mapped to the server's wire values.
DIRECTIONS = ("go_on", "turn_back")
_CHOICE = {"go_on": "continue", "turn_back": "back"}


class EightEnv:
    def __init__(self, base_url: str, arc: str = "hallway-eight",
                 difficulty: str = "normal", locale: str = "en_US",
                 sid: Optional[str] = None, timeout: float = 60.0):
        self.base = base_url.rstrip("/")
        self.arc = arc
        self.difficulty = difficulty      # easy | normal | hard | (insane)
        self.locale = locale              # e.g. en_US, de_DE, ja_JP
        self.timeout = timeout
        self.sid = sid or ("bench-" + secrets.token_hex(8))
        self.goal = 8
        self.last: Dict[str, Any] = {}

    # --- wire helpers ------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        # Difficulty and language travel as headers, exactly like the web client.
        # State is keyed by X-Sid (NOT a cookie), so a fresh client still resolves
        # to the same run across calls.
        return {
            "X-Sid": self.sid,
            "X-Lang": self.locale,
            "X-Diff": self.difficulty,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(self.base + path, json=body,
                          headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # --- moves -------------------------------------------------------------
    def reset(self) -> Dict[str, Any]:
        """Start a fresh climb of the arc; returns the opening loop payload."""
        d = self._post("/api/new", {"arc": self.arc})
        self.sid = d.get("sid", self.sid)
        self.goal = d.get("goal", 8)
        self.last = d
        return d

    def act(self, direction: str, confidence: int = 3) -> Dict[str, Any]:
        """Commit the loop. `direction` is 'go_on' or 'turn_back'.

        Confidence never affects correctness (server truth), so we send a firm
        commit by default. The reply carries the verdict for THIS loop plus the
        NEXT loop's room.
        """
        if direction not in _CHOICE:
            raise ValueError(f"direction must be one of {DIRECTIONS}, got {direction!r}")
        d = self._post("/api/act", {"choice": _CHOICE[direction], "confidence": confidence})
        self.last = d
        return d

    def touch(self, prop: str) -> Dict[str, Any]:
        """Act 2: touch a detail (optional, flavour only). Never decides the
        forward/back call, but a curious touch can rarely FOLD the run back to
        level 0 (`kind == 'fold'`). Returns {kind, line, level, ...}."""
        return self._post("/api/interact", {"prop": prop})

    # --- convenience -------------------------------------------------------
    def room(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """The room dict from a payload (defaults to the last one seen)."""
        return (payload or self.last).get("room", {}) or {}

    def available_actions(self, payload: Optional[Dict[str, Any]] = None):
        """The action strings offered this loop: the two directional calls, plus
        one 'touch:<prop>' for every touchable detail the server exposed."""
        room = self.room(payload)
        actions = list(DIRECTIONS)
        for t in room.get("touch", []) or []:
            actions.append("touch:" + t["prop"])
        return actions
