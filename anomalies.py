# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Anomaly selection and the small "drift" tricks.

Nothing here screams. An anomaly is a single property quietly swapped for a
plausible variant. The drift helpers change wording, punctuation, and the
heading itself so the player can never compare two loops character-for-character
and must fall back on memory of *meaning*.
"""

from __future__ import annotations

import random
from typing import Dict, Iterable, List, Optional, Tuple


def pick_anomaly(properties: Dict[str, dict], rng: random.Random,
                 exclude: Iterable[str] = (),
                 baseline_of: Optional[Dict[str, str]] = None
                 ) -> Optional[Tuple[str, str]]:
    """Choose one property and one changed value.

    Returns (property_name, changed_value), or None if every candidate property
    is excluded. `exclude` holds props that must not be the anomaly this loop,
    which powers two callers:

    - a late-revealed "aggro-item" the player has not yet seen at baseline, so
      it can never be the change on the loop it first appears; and
    - hard mode's second simultaneous change, where passing the already-chosen
      change (plus any held item) as `exclude` yields a distinct second detail,
      so the two changes never collide.

    `baseline_of` (INSANE only): a map of prop -> this run's baseline value. When
    given, the change is any value that DIFFERS from this run's baseline (drawn
    from the property's full value set: baseline pools + anomaly pools), not the
    fixed anomaly set. That is what makes 'insane' a memory test rather than a
    vocabulary test. When None (every other difficulty), the behaviour is
    unchanged: pick from the property's `anomalies`.
    """
    skip = set(exclude)
    if baseline_of is not None:
        candidates = []
        for name, spec in properties.items():
            if name in skip:
                continue
            allv = list(spec.get("values", {})) + list(spec.get("anomalies", {}))
            base = baseline_of.get(name)
            alts = [v for v in allv if v != base]
            if alts:
                candidates.append((name, alts))
        if not candidates:
            return None
        prop, alts = rng.choice(candidates)
        return prop, rng.choice(alts)
    candidates = [name for name, spec in properties.items()
                  if spec.get("anomalies") and name not in skip]
    if not candidates:
        return None
    prop = rng.choice(candidates)
    value = rng.choice(list(properties[prop]["anomalies"].keys()))
    return prop, value


def drift_heading(title_variants: List[str], loops: int, rng: random.Random) -> str:
    """The heading is usually 'Hallway 8', but every so often it slips.

    Early on it is stable. The longer the player survives, the more the
    heading is allowed to wander -- a meta anomaly they can never act on.
    """
    if loops < 4:
        return title_variants[0]
    # a small, growing chance of a slipped heading
    if rng.random() < min(0.05 + loops * 0.01, 0.30):
        return rng.choice(title_variants)
    return title_variants[0]


def drift_sign(sign_variants: List[str], rng: random.Random) -> str:
    """The exit sign's spacing/arrow drifts even when it is *not* the anomaly."""
    return rng.choice(sign_variants)


def render_sentence(template: str, sign_text: str) -> str:
    """Fill the shared placeholders in a sentence template."""
    return template.replace("{SIGN}", sign_text)
