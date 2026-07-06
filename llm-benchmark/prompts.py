# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Prompt templates for the LLM benchmark.

The system prompt states the rule in one of two **reading registers** (the game's
own accessibility toggle): `normal` and `simple`. Neither spoils the specific
details a player must watch, matching the game's design: it teaches the RULE, not
the answer. The agent must work out for itself which detail moved.

The observation renders a loop as the player sees it: a heading, a few rotating
sentences (wording drifts on purpose, so compare MEANING not words), and the list
of actions available this turn.
"""

from __future__ import annotations

from typing import Dict, List

# The rule, in two reading registers. Both are answer-free: they never name the
# details, the NPC, or the anomaly, only how to play.
SYSTEM = {
    "normal": (
        "You are playing a memory game called 8. You move through a place that "
        "should look the same on every loop. Each loop you read a short "
        "description and make one call:\n"
        "  - go_on   : proceed, because nothing has changed from what you remember.\n"
        "  - turn_back: turn around, because something is different from the "
        "baseline you established.\n"
        "The wording is rephrased and only a subset of details is shown each loop, "
        "so you must remember the MEANING of the place, not the exact sentences. "
        "Eight correct calls in a row and the door opens. One wrong call sends you "
        "back to the very start. The first loop is your clean baseline: nothing has "
        "changed yet, so go_on and commit it to memory."
    ),
    "simple": (
        "You are playing a memory game. You walk through a place. It should look "
        "the same each time.\n"
        "Each turn you read a few lines and pick one:\n"
        "  - go_on   : keep going, because it looks the same as before.\n"
        "  - turn_back: turn around, because something changed.\n"
        "The words are switched around and you only see some of the things each "
        "time. So remember what the place MEANS, not the exact words. Get eight in "
        "a row and you win. One wrong pick sends you back to the start. The first "
        "turn is safe: nothing has changed yet, so go_on and remember it."
    ),
}

# Optional Act 2 note, only added when touch actions are offered. It is honest
# about the risk (a touch can, rarely, fold the run back to the start).
TOUCH_NOTE = (
    "Some loops also let you touch a detail (touch:<name>). Touching is optional "
    "and never decides the go_on/turn_back call; it only adds flavour, and a "
    "curious touch can rarely send you back to the start. Touch only if it helps "
    "you remember."
)

ACTION_INSTRUCTION = (
    "Reply with ONLY a JSON object of the form {{\"reason\": \"<one short "
    "sentence>\", \"actions\": [<action>, ...]}} where each <action> is one of: "
    "{actions}. List touch actions first if you use any; end with exactly one of "
    "go_on or turn_back (that commits the loop). Example: "
    "{{\"reason\": \"the sign wording matches my baseline\", \"actions\": "
    "[\"go_on\"]}}."
)


def render_observation(payload: Dict, actions: List[str]) -> str:
    """One loop, as text for the model."""
    room = payload.get("room", {}) or {}
    level = payload.get("level", 0)
    goal = payload.get("goal", 8)
    lines = "\n".join("  " + s for s in room.get("sentences", []))
    head = room.get("heading", "")
    out = [f"Loop {level + 1} of {goal}.", f"[{head}]", lines]
    return "\n".join(x for x in out if x)


def build_messages(system_register: str, history: List[str],
                   observation: str, actions: List[str],
                   allow_touch: bool) -> List[Dict[str, str]]:
    """A chat-format message list for `tokenizer.apply_chat_template`.

    `history` is a compact log of prior loops this run (what was seen, what was
    chosen, the outcome) so the model can compare the current loop against its own
    established baseline.
    """
    sys = SYSTEM.get(system_register, SYSTEM["normal"])
    if allow_touch and any(a.startswith("touch:") for a in actions):
        sys = sys + "\n" + TOUCH_NOTE
    user_parts = []
    if history:
        user_parts.append("Your run so far (oldest first):\n" + "\n".join(history))
    user_parts.append(observation)
    user_parts.append(ACTION_INSTRUCTION.format(actions=", ".join(actions)))
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
