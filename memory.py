# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Tracks how the player behaves across loops.

The point of this module is not scoring. It is to give the game a small
model of the player's habits so the narration can quietly react to them:
the corridor that "remembers you."
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


@dataclass
class PlayerMemory:
    # progress
    level: int = 0            # which hallway you are standing in (0 = the start)
    best_level: int = 0       # furthest you have ever reached
    loops: int = 0            # total corridors walked this run
    attempts: int = 1         # which run this is (1 = first try; +1 on each reset)

    # behaviour
    turn_backs: int = 0
    continues: int = 0
    false_reports: int = 0    # turned back when nothing was wrong
    missed: int = 0           # walked on past a real change
    inspects: Dict[str, int] = field(default_factory=dict)

    # confidence
    confidence_sum: float = 0.0
    confidence_n: int = 0

    # hard-mode continuity: what changed last loop, so an anomaly can persist or
    # revert across loops (a memory test that spans more than one loop).
    prev_anomaly_prop: Optional[str] = None
    prev_anomaly_val: Optional[str] = None

    # coach arc: how many times the passenger (the NPC) and the player have
    # engaged each other. Once it crosses a threshold the passenger delivers its
    # one fixed utterance (npc_triggered), which *arms* the false way out; only
    # then can the false exit surface, near the end (possibly a later loop than
    # the utterance itself).
    seen_by_npc: int = 0
    npc_triggered: bool = False

    # aggro-item (late-revealed detail): one or two small, inconspicuous
    # properties can be held out of the early loops and only start appearing
    # later in the run, so the player meets them for the first time deep in a
    # climb and the stakes rise. `held` maps each held property to the loop level
    # at which it starts showing. seen_props is the fairness guard: it records
    # every property the player has actually been shown in a *prior* loop, and an
    # anomaly is only ever placed on a baseline-seen property, so a late reveal
    # can never be the anomaly on the very loop it first appears (that would be
    # pure luck, not memory).
    seen_props: list = field(default_factory=list)
    held: dict = field(default_factory=dict)   # held prop -> reveal level

    # "Insane" difficulty only: the baseline value chosen for each property THIS
    # climb (maps prop -> value key). Insane randomizes the baseline per run from
    # a property's existing value pools, so a wording that is the norm in one run
    # is the change in another; a bot that memorized the global vocabulary cannot
    # tell clean from changed and must remember *this* run's baseline. Empty for
    # every other difficulty (they use the arc's fixed baseline).
    run_baseline: dict = field(default_factory=dict)

    def record_inspect(self, thing: str) -> None:
        self.inspects[thing] = self.inspects.get(thing, 0) + 1

    def record_confidence(self, value: Optional[int]) -> None:
        # Only count a real number: a malformed body ({"confidence": "5"} or a
        # list) must not reach the arithmetic below and raise a TypeError.
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value:
            self.confidence_sum += value
            self.confidence_n += 1

    @property
    def confidence(self) -> float:
        if not self.confidence_n:
            return 0.0
        return round(self.confidence_sum / self.confidence_n, 2)

    @property
    def favorite(self) -> Optional[str]:
        """The property the player fixates on, once a habit has formed."""
        if not self.inspects:
            return None
        thing, count = max(self.inspects.items(), key=lambda kv: kv[1])
        return thing if count >= 3 else None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerMemory":
        if not data:
            return cls()
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)
