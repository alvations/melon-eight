# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Agents that decide a move from an observation.

An agent takes the loop payload + the list of legal action strings + its running
history, and returns a LIST of actions to execute in order (touches first, then
exactly one of go_on / turn_back to commit the loop).

Two agents ship here:
  - RandomAgent   : a zero-dependency baseline, so you can smoke-test the harness
                    (and see the floor an LLM must beat) with no model download.
  - LLMAgent      : a local Hugging Face `transformers` model. The default is a
                    small, on-device example; swap it with --model.

Write your own by subclassing Agent and implementing `act`.
"""

from __future__ import annotations

import json
import random
import re
from typing import Dict, List

from prompts import build_messages, render_observation

_DIRECTIONAL = {"go_on", "turn_back"}


class Agent:
    name = "agent"

    def reset(self):
        """Called at the start of each fresh climb."""

    def act(self, payload: Dict, actions: List[str], history: List[str]) -> List[str]:
        raise NotImplementedError


class RandomAgent(Agent):
    """Commits a random direction each loop (never touches). A calibration floor:
    on normal it should almost never string eight correct calls together."""

    name = "random"

    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)

    def act(self, payload, actions, history):
        return [self._rng.choice(["go_on", "turn_back"])]


class AlwaysGoOnAgent(Agent):
    """Always proceeds. Another baseline: it wins only when a whole climb happens
    to be anomaly-free, so its score shows how often turning back is even needed."""

    name = "always_go_on"

    def act(self, payload, actions, history):
        return ["go_on"]


def _extract_actions(text: str, legal: List[str]) -> List[str]:
    """Parse the model's reply into a legal action list. Tolerant: finds the first
    JSON object, else falls back to scanning for the verbs. Always returns a list
    ending in exactly one directional action (defaults to go_on if none found)."""
    chosen: List[str] = []
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            raw = obj.get("actions", obj.get("action"))
            if isinstance(raw, str):
                raw = [raw]
            if isinstance(raw, list):
                chosen = [str(a).strip() for a in raw]
        except (ValueError, TypeError):
            chosen = []
    if not chosen:
        # Fallback: scan the raw text for the verbs, in order of appearance.
        for tok in re.findall(r"touch:[a-zA-Z0-9_\-]+|turn_back|go_on", text):
            chosen.append(tok)
    # Keep only legal actions, truncate at the first directional commit.
    out: List[str] = []
    for a in chosen:
        if a not in legal:
            continue
        out.append(a)
        if a in _DIRECTIONAL:
            break
    if not out or out[-1] not in _DIRECTIONAL:
        out.append("go_on")   # safe default: commit rather than stall
    return out


class LLMAgent(Agent):
    """A local `transformers` causal LM. Loaded once, reused across episodes."""

    def __init__(self, model_id: str, register: str = "normal",
                 allow_touch: bool = True, max_new_tokens: int = 160,
                 device: str = "auto", dtype: str = "auto"):
        # Imported lazily so RandomAgent works with no ML deps installed.
        import torch  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.name = model_id.split("/")[-1]
        self.model_id = model_id
        self.register = register
        self.allow_touch = allow_touch
        self.max_new_tokens = max_new_tokens
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=("auto" if dtype == "auto" else getattr(__import__("torch"), dtype)),
            device_map=device,
        )
        self.model.eval()

    def act(self, payload, actions, history):
        obs = render_observation(payload, actions)
        messages = build_messages(self.register, history, obs, actions, self.allow_touch)
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        import torch
        with torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=self.max_new_tokens,
                do_sample=False, temperature=None, top_p=None,
                pad_token_id=(self.tokenizer.pad_token_id
                              or self.tokenizer.eos_token_id))
        text = self.tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return _extract_actions(text, actions)


def make_agent(kind: str, **kw) -> Agent:
    if kind == "random":
        return RandomAgent(seed=kw.get("seed", 0))
    if kind == "always_go_on":
        return AlwaysGoOnAgent()
    if kind == "llm":
        return LLMAgent(
            model_id=kw["model_id"], register=kw.get("register", "normal"),
            allow_touch=kw.get("allow_touch", True),
            max_new_tokens=kw.get("max_new_tokens", 160),
            device=kw.get("device", "auto"), dtype=kw.get("dtype", "auto"))
    raise ValueError(f"unknown agent kind {kind!r}")
