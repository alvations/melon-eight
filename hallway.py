# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""The corridor: building a loop and describing it.

A "room" is not a paragraph. It is a set of properties, each currently at its
baseline value or (at most one of them) at an anomalous value. The describer
turns that into a handful of sentences drawn from rotating pools, so the same
place reads differently every time while still being the same place.

Content is organised into *arcs* (skins/backstories) under data/arcs/. Each arc
file shares the same schema; only the theme, story, and vocabulary change.
"""

from __future__ import annotations

import glob
import json
import os
import random
from typing import Dict, List, Optional

import anomalies
import i18n
from memory import PlayerMemory

ARCS_DIR = os.path.join(os.path.dirname(__file__), "data", "arcs")

DEFAULT_ARC = "hallway-eight"

# How many hallways/landings you must clear. Reaching this level wins.
# Canonically 8 (the game's whole identity). H8_GOAL overrides it only for a
# non-canonical *shortcut* test build (e.g. 3 stages) so the end screen can be
# reached quickly; clamped to 1..8. Do not use a shortcut build as canonical.
GOAL = max(1, min(8, int(os.environ.get("H8_GOAL", "8"))))

# How many details are described each loop. Enough to overload memory a little,
# few enough to keep it readable.
MIN_DETAILS = 4
MAX_DETAILS = 6

# Chance a loop contains an anomaly, as a function of how far along you are.
# The opening loop (level 0) is deliberately *very* low: on your first loop you
# have no baseline yet, so being turned back is close to a coin flip you cannot
# win. It is not zero (a rare early jolt keeps the place honest), just ~2% on
# normal, and it ramps up steeply from there to a near coin-flip near the exit.
ANOMALY_BASE = 0.02   # at level 0 (the opening loop, no baseline yet)
ANOMALY_STEP = 0.076  # added per level cleared (steep, to reach the cap by ~L7)
ANOMALY_MAX = 0.55    # never so high that "always turn back" wins

# Three difficulties scale the same ramp, all sharing the very-low opening. Easy
# ramps gentler to a lower cap; normal is the canonical ramp above; hard ramps
# stiffer to a higher cap AND adds new *kinds* of change (see build(): double
# changes and cross-loop persistence). No level-0 floor: the low opening is the
# point, and levels 1+ ramp well clear of zero so "always continue" still loses.
# "insane" is a server-only, UNEXPOSED difficulty (the client offers only
# easy/normal/hard, like the hidden locales). Its defining feature is not the
# ramp but a per-run randomized baseline (see build()), which defeats a bot that
# memorizes the fixed all-clear vocabulary. It reuses existing translated content,
# so it needs no new i18n. Keep it out of the client picker until deliberately
# released.
DIFFICULTIES = ("easy", "normal", "hard", "insane")
EXPOSED_DIFFICULTIES = ("easy", "normal", "hard")
DEFAULT_DIFFICULTY = "normal"

# The NPC's loop-aware acknowledgement values (the twist): a narrative climax, not
# a resting state, so never an insane baseline.
_NPC_ACK_VALUES = ("knows", "speaks")
# Prose markers that make an anomaly value unfit as an insane BASELINE: it would
# announce a change (or reference the player's memory / a prior state) while being
# shown as this run's calm normal. Matched case-insensitively against every
# sentence of the value's pool. Lean toward over-excluding: a borderline value
# just falls back to the calm baseline, which is always safe.
_INSANE_BASELINE_UNSAFE = (
    "remember", " now", "now,", "no longer", "used to", "a moment ago", "moment ago",
    "than you", "than it", "than they", "than he", "than before", "than the", "never",
    " was ", " were ", "has stopped", "has gone", "has moved", "has reversed",
    "has turned", "has appeared", "has spilled", "have gone", "have been",
    "have moved", "been prised", "not the", "not a ", "not 8", "not one",
    "where there", "wrong way", "unannounced", "behind you", "again?", "don't belong",
    "don't remember", "climbing now", "coming up", "should ", "should be",
    "different colour", "wasn't there", "gone cold", "gone silent", "gone black",
    "gone out", "stopped", "moved to", "awake now", "empty now", "much closer",
    "prised off", "up full", "faster than", "slowing", "raised a hand",
    "lifts a hand", "looks up", "waiting for you", "turned", "is gone", "is missing",
    "half-second",
)
_DIFF = {
    "easy":   {"base": 0.01, "step": 0.042, "max": 0.30, "floor": 0.0},
    "normal": {"base": ANOMALY_BASE, "step": ANOMALY_STEP, "max": ANOMALY_MAX, "floor": 0.0},
    "hard":   {"base": 0.03, "step": 0.081, "max": 0.60, "floor": 0.0},
    # Insane is strictly the hardest: a clearly higher anomaly ramp than hard, AND
    # it inherits every hard escalation (aggro holds, cross-loop persist/revert,
    # the deep double-change) on top of its per-run randomized baseline.
    "insane": {"base": 0.03, "step": 0.092, "max": 0.66, "floor": 0.0},
}


def norm_difficulty(d: Optional[str]) -> str:
    # Guard against a non-string (e.g. a malformed JSON body {"difficulty": []}):
    # `x in _DIFF` would raise on an unhashable value.
    return d if isinstance(d, str) and d in _DIFF else DEFAULT_DIFFICULTY


def anomaly_chance(level: int, difficulty: str = DEFAULT_DIFFICULTY) -> float:
    p = _DIFF[norm_difficulty(difficulty)]
    c = min(p["max"], p["base"] + p["step"] * max(0, level))
    return max(p["floor"], c)


def _arc_path(arc_id: str) -> str:
    return os.path.join(ARCS_DIR, f"{arc_id}.json")


def list_arcs() -> List[dict]:
    """Return the selectable arcs, described by their meta block.

    The default arc is listed first; the rest follow alphabetically.
    """
    arcs = []
    for path in sorted(glob.glob(os.path.join(ARCS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            meta = json.load(f).get("meta", {})
        if meta.get("id"):
            arcs.append({
                "id": meta["id"],
                "title": meta.get("title", meta["id"]),
                "tagline": meta.get("tagline", ""),
                "skin": meta.get("skin", "hallway"),
            })
    arcs.sort(key=lambda a: (a["id"] != DEFAULT_ARC, a["id"]))
    return arcs


# --- Act 2 (touch-the-room) trigger tuning ------------------------------------
# See docs/ACT2.md. Weights scale with GOAL so they hold on a shortcut build.
# H8_ACT2_TEST boosts the fold and surfaces the false exit far more often, so the
# endings can be reached quickly for testing; it must stay OFF for the real game.
ACT2_TEST = os.environ.get("H8_ACT2_TEST", "").strip().lower() not in (
    "", "0", "false", "no",
)


def act2_fold_chance(level: int, goal: int) -> float:
    """Chance a touch folds the run back to level 0. None before the onset."""
    if ACT2_TEST:
        return 0.30 if level >= 1 else 0.0
    onset = max(2, round(goal * 0.35))          # ~level 3 at goal 8
    if level < onset:
        return 0.0
    return 0.15 if level >= round(goal * 0.75) else 0.10


def act2_exit_ready(level: int, goal: int, rng: random.Random,
                    difficulty: str = DEFAULT_DIFFICULTY) -> bool:
    """Whether the rare 'false way out' surfaces this loop. Gated to the
    three-quarter mark (not the finish), or boosted under test. Easy mode makes
    it much rarer, so a younger player does not fall into the wrong ending."""
    if ACT2_TEST:
        return level >= 1 and rng.random() < 0.6
    lo = max(1, round(goal * 0.6))              # ~level 5 at goal 8
    hi = goal - 2                               # ~level 6 at goal 8 (not the last)
    # Easy: about a 1-in-100 chance to even be offered, so a younger player
    # almost never trips into the wrong ending.
    chance = 0.01 if difficulty == "easy" else 0.07
    return lo <= level <= hi and rng.random() < chance


class Hallway:
    def __init__(self, arc_id: str = DEFAULT_ARC):
        path = _arc_path(arc_id)
        if not os.path.exists(path):
            path = _arc_path(DEFAULT_ARC)
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.properties: Dict[str, dict] = self.data["properties"]
        self.meta: dict = self.data.get("meta", {})
        self.labels: Dict[str, str] = self.meta.get("labels", {})
        self.arc_id: str = self.meta.get("id", "")
        self.act2: dict = self.data.get("act2", {})
        # The property that carries this arc's NPC (used for the loop-aware
        # acknowledgement and, on the coach, the "seen enough" exit trail).
        self.npc_prop: Optional[str] = self.meta.get("npc_prop")

    def _loc(self, locale: Optional[str], key: str, fallback: str) -> str:
        return i18n.localize(locale, f"a:{self.arc_id}|{key}", fallback)

    def _exit_ready(self, mem: PlayerMemory, rng: random.Random,
                    difficulty: str) -> bool:
        """Whether the false way out surfaces this loop.

        The coach is special: rather than a flat late-game roll, its passenger
        has to have *clocked the player enough* first, and the offer only comes
        near the very end. The accumulating sightings are the faint trail that
        makes the alternate ending discoverable instead of lottery-rare. The
        other arcs keep the plain gated roll.
        """
        if self.arc_id == "coach8":
            # Armed only after the passenger's fixed utterance has fired, and
            # only near the end. The utterance may have landed several loops ago.
            if not mem.npc_triggered:
                return False
            if ACT2_TEST:
                return mem.level >= 1 and rng.random() < 0.6
            near_end = mem.level >= GOAL - 2      # levels 6-7 at goal 8
            # About 1-in-100 in easy (on top of the trigger + near-end gates), so
            # a younger player almost never reaches the wrong ending, even though
            # the passenger's trail is still visible to them.
            roll = 0.03 if difficulty == "easy" else 0.5
            return near_end and rng.random() < roll
        return act2_exit_ready(mem.level, GOAL, rng, difficulty)

    @staticmethod
    def _value_keys(spec: dict) -> List[str]:
        """Every value a property can take: its baseline value pools plus its
        anomaly value pools. Used to enumerate the full value set."""
        return list(spec.get("values", {})) + list(spec.get("anomalies", {}))

    @staticmethod
    def _insane_baseline_keys(spec: dict, prop: str, npc_prop: Optional[str]) -> List[str]:
        """The values 'insane' may use as this run's baseline for a property.

        Insane randomizes the baseline from the full value set, but an anomaly
        value whose prose ANNOUNCES a change (or the NPC's acknowledgement) reads
        as wrong when shown as a calm baseline: "the arrow has reversed" on a clean
        loop, then a fair turn-back gets reset. So the baseline pool is the calm
        `values` (always safe) plus only those anomaly values whose every sentence
        reads as a plain state (no memory/change/comparison marker), and never the
        NPC twist. Each property keeps at least its calm value, so the pool is
        never empty; enough properties still randomize to keep insane anti-bot.
        The CHANGE is still drawn from the full set (a change SHOULD announce one).
        """
        keys = list(spec.get("values", {}))
        for val, pool in spec.get("anomalies", {}).items():
            if prop == npc_prop and val in _NPC_ACK_VALUES:
                continue
            if any(m in s.lower() for s in pool for m in _INSANE_BASELINE_UNSAFE):
                continue
            keys.append(val)
        return keys

    @staticmethod
    def _pool_and_kind(spec: dict, val: str):
        """The sentence pool and i18n kind for ANY value of a property. A value
        in `values` is a calm baseline line (kind 'v'); one in `anomalies` is a
        wrongness line (kind 'x'). This lets a value serve as a run-baseline OR a
        change depending on the difficulty, while always keying to the SAME
        already-translated line, so 'insane' needs no new i18n."""
        if val in spec.get("values", {}):
            return spec["values"][val], "v"
        return spec["anomalies"][val], "x"

    def build(self, mem: PlayerMemory, rng: random.Random,
              locale: Optional[str] = None,
              difficulty: str = DEFAULT_DIFFICULTY) -> dict:
        """Generate the next place for the player's current level.

        The probability of an anomaly ramps with the player's level: gentle at
        the first stage (so they can learn the baseline by proceeding), rising
        toward a coin-flip so that neither "always continue" nor "always turn
        back" becomes a winning strategy.

        `locale` picks which language the prose is rendered in; each line falls
        back to its English original when a translation is missing.
        """
        diff = norm_difficulty(difficulty)

        # --- Aggro-item: hold small details out of the early loops ------------
        # A short list of inconspicuous "late" properties can be held back so
        # they only start appearing later in the run, meeting the player for the
        # first time deep in a climb (the stakes rise once a detail you never had
        # to track suddenly matters). Decided once per climb (at level 0).
        #   - HARD: always holds 1 or 2 of them, revealing from ~level 2 onward.
        #     This is where the "not everything is shown up front" pressure lives.
        #   - NORMAL: only *rarely* holds a single one, so a normal player gets a
        #     fair chance to meet almost every encounter; the run-to-run rotation
        #     of which details show (never all of them at once) is the everyday
        #     replay hook, not a deliberate hold.
        #   - EASY: never holds.
        # Each held item is paced to reveal before the last level, and can never
        # be the change on the loop it first appears (see the exclusion below),
        # so a late arrival never turns the finish into pure luck.
        late_props = [p for p in self.meta.get("late_props", [])
                      if p in self.properties]
        if mem.level == 0:
            mem.seen_props = []
            mem.held = {}
            mem.run_baseline = {}
            if diff in ("hard", "insane") and late_props:
                hold_k = 1 if len(late_props) < 2 else rng.randint(1, 2)
            elif diff == "normal" and late_props and rng.random() < 0.15:
                hold_k = 1
            else:
                hold_k = 0
            if hold_k:
                lo = min(2, GOAL - 2)            # from ~level 2 onward
                hi = max(lo, GOAL - 2)           # up to ~level 6 (never the last)
                for p in rng.sample(late_props, hold_k):
                    mem.held[p] = rng.randint(lo, hi)
            # INSANE only: randomize this climb's baseline value for every
            # property (from its full set of value pools). The "normal" state is
            # then run-specific, so a bot that memorized the global all-clear
            # vocabulary cannot tell clean from changed and must remember THIS
            # run's baseline. Reuses existing lines, so no new content or i18n.
            if diff == "insane":
                for p, spec in self.properties.items():
                    # Draw from the baseline-SAFE pool (calm value + descriptive
                    # anomalies), never a value whose prose announces a change, so a
                    # clean loop never reads as wrong. See _insane_baseline_keys.
                    keys = self._insane_baseline_keys(spec, p, self.npc_prop)
                    if keys:
                        mem.run_baseline[p] = rng.choice(keys)
        # Props still held out of this loop (they reveal on a later loop).
        held_now = {p for p, rv in mem.held.items() if mem.level < rv}
        # An anomaly may not land on a held item until the player has seen it at
        # baseline on an earlier loop (recorded in seen_props). That covers both
        # "still held" and "revealed this very loop", so a held item's first
        # appearance is always a calm baseline, never the trap.
        excluded_anomaly = {p for p in mem.held if p not in mem.seen_props}
        # INSANE fairness: because the baseline is randomized per run, a property's
        # "normal" is only knowable once the player has seen it this run. So an
        # anomaly may only land on a property already shown at baseline on an
        # earlier loop (exactly the aggro-item guard, extended to every property).
        # This makes the opening loop always a clean baseline and every property's
        # first appearance a calm baseline, never the trap.
        if diff == "insane":
            excluded_anomaly = excluded_anomaly | {
                p for p in self.properties if p not in mem.seen_props}

        # The opening loop (level 0) uses the very-low base above, so a fresh run
        # is almost always a clean baseline before anything is allowed to move.
        has_anomaly = rng.random() < anomaly_chance(mem.level, diff)

        # Every property that has changed this loop -> its anomalous value.
        # Normally 0 or 1. Hard mode escalates in *kind*: cross-loop persistence
        # or revert (below), and, deep in a run, a *second* simultaneous change.
        # The double is made fair by a post-hoc "flare" on a correct turn-back
        # (the two changed lines pulse), so the "keep scanning" lesson can form.
        changed: Dict[str, str] = {}

        # Hard mode, cross-loop continuity: after a change, the same anomaly can
        # PERSIST (you caught it, but is it still there?) or the loop can be a
        # deliberate clean REVERT (back to baseline right after a change). Both
        # break the "each loop is independent" assumption and test memory across
        # more than one loop. This is the whole of hard mode's escalation.
        if mem.level > 0 and diff in ("hard", "insane") and mem.prev_anomaly_prop:
            r = rng.random()
            spec = self.properties.get(mem.prev_anomaly_prop, {})
            if diff == "insane":
                # In insane a change is any value != this run's baseline (it may be
                # a calm value too), so validate against the full value set.
                valid = (mem.prev_anomaly_val in self._value_keys(spec)
                         and mem.prev_anomaly_val
                         != mem.run_baseline.get(mem.prev_anomaly_prop))
            else:
                valid = mem.prev_anomaly_val in spec.get("anomalies", {})
            if r < 0.22 and valid:
                has_anomaly = True
                changed[mem.prev_anomaly_prop] = mem.prev_anomaly_val
            elif r < 0.34:
                has_anomaly = False   # revert: a clean loop right after a change

        if has_anomaly and not changed:
            picked = anomalies.pick_anomaly(
                self.properties, rng, excluded_anomaly,
                baseline_of=(mem.run_baseline if diff == "insane" else None))
            if picked:
                changed[picked[0]] = picked[1]

        # Hard mode, double change: deep in the run, a second (distinct) detail
        # can move at the same time. Excluding the already-chosen change (and any
        # held item) makes the second detail distinct, so the two never collide.
        # The fairness guard shows both, and a correct turn-back flares both lines
        # afterward so the player learns to scan.
        if (diff in ("hard", "insane") and changed and len(changed) == 1
                and mem.level >= round(GOAL * 0.5) and rng.random() < 0.30):
            second = anomalies.pick_anomaly(
                self.properties, rng, excluded_anomaly | set(changed),
                baseline_of=(mem.run_baseline if diff == "insane" else None))
            if second:
                changed[second[0]] = second[1]

        has_anomaly = bool(changed)
        anomaly_props = list(changed.keys())
        # The primary change (for the NPC acknowledgement and continuity): prefer
        # the NPC property if it is one of the changed ones.
        primary = None
        if self.npc_prop and self.npc_prop in changed:
            primary = self.npc_prop
        elif anomaly_props:
            primary = anomaly_props[0]

        # Decide which properties get described this loop.
        order = list(self.data["anchor_order"])
        if held_now:
            # Held aggro-items stay out of the running until their reveal loop.
            order = [p for p in order if p not in held_now]
        rng.shuffle(order)
        n = rng.randint(MIN_DETAILS, MAX_DETAILS)
        shown = order[:n]
        # Every changed property must be visible this loop -- otherwise the
        # player is asked to notice something they were never shown.
        for ap in anomaly_props:
            if ap not in shown:
                spare = [s for s in shown if s not in anomaly_props]
                if spare:
                    shown[shown.index(rng.choice(spare))] = ap
                else:
                    shown.append(ap)
        # On its reveal loop, make sure a just-revealed held item actually
        # appears (at baseline, since it is still excluded from the anomaly), so
        # the player registers it before it can ever be the change on a later loop.
        for hp in [p for p in mem.held
                   if p not in held_now and p not in mem.seen_props]:
            if hp not in shown:
                spare = [s for s in shown if s not in anomaly_props]
                if spare:
                    shown[shown.index(rng.choice(spare))] = hp
                else:
                    shown.append(hp)
        # Re-sort shown into the canonical order so the "camera" of the prose
        # feels consistent even as content rotates.
        shown = [p for p in self.data["anchor_order"] if p in shown]
        # Record every property shown this loop, so the anomaly can only ever
        # land on a detail the player has already seen at baseline (the fairness
        # guard the aggro-item reveal depends on).
        for p in shown:
            if p not in mem.seen_props:
                mem.seen_props.append(p)

        # The coach's passenger clocks the player when it actually *interacts* --
        # i.e. it is the change this loop (it turns, it acknowledges you), not
        # merely present. Enough such interactions (plus the player engaging it
        # back, see /api/interact) eventually make it deliver its one fixed
        # utterance, which arms the false way out (see _exit_ready).
        if self.npc_prop and primary == self.npc_prop:
            mem.seen_by_npc += 1
        # The arming utterance: fires once, on the first loop after enough
        # acquaintance. It may land well before the loop the false exit finally
        # surfaces on, or on the same one.
        npc_utterance = None
        _utter_at = 1 if ACT2_TEST else 3
        if (self.arc_id == "coach8" and not mem.npc_triggered
                and mem.seen_by_npc >= _utter_at):
            mem.npc_triggered = True
            npc_utterance = self._loc(locale, "act2|exit|utterance",
                                      self.act2.get("exit", {}).get("utterance", ""))

        sign_text = anomalies.drift_sign(self.data["sign_variants"], rng)

        sentences: List[str] = []
        keys: List[str] = []
        for prop in shown:
            spec = self.properties[prop]
            if prop in changed:
                val = changed[prop]
                pool, kind = self._pool_and_kind(spec, val)
            elif diff == "insane":
                # This run's randomized baseline for the property (a calm 'v' line
                # or, when the run-baseline happens to be a wrongness value, its
                # 'x' line, keyed to the same existing translation).
                val = mem.run_baseline.get(prop, spec["baseline"])
                pool, kind = self._pool_and_kind(spec, val)
            else:
                val, kind = spec["baseline"], "v"
                pool = spec["values"][val]
            idx = rng.randrange(len(pool))
            skey = f"p:{prop}|{kind}:{val}|{idx}"
            text = self._loc(locale, skey, pool[idx])
            sentences.append(anomalies.render_sentence(text, sign_text))
            keys.append(f"a:{self.arc_id}|{skey}")

        # Remember this loop's primary change so hard mode can persist/revert it.
        mem.prev_anomaly_prop = primary
        mem.prev_anomaly_val = changed.get(primary) if primary else None
        anomaly_prop = primary
        anomaly_val = changed.get(primary) if primary else None

        # Adaptive touch: if the player keeps inspecting one thing, and it is
        # on show this loop, let the place notice.
        fav = mem.favorite
        adaptive_line = None
        if fav and fav in shown and rng.random() < 0.5:
            pool = self.data["adaptive"]["repeat_inspect"]
            idx = rng.randrange(len(pool))
            tmpl = self._loc(locale, f"adaptive|repeat_inspect|{idx}", pool[idx])
            thing = self._loc(locale, f"label|{fav}", self.labels.get(fav, fav))
            adaptive_line = tmpl.replace("{THING}", thing)

        heading = anomalies.drift_heading(
            self.data["title_variants"], mem.loops, rng
        )
        head_key = None
        try:
            hidx = self.data["title_variants"].index(heading)
            head_key = f"a:{self.arc_id}|title|{hidx}"
            heading = self._loc(locale, f"title|{hidx}", heading)
        except ValueError:
            pass

        # Act 2: which shown details can be touched this loop, and (rarely) the
        # false way out. Rolled last so it never perturbs the loop's own prose.
        touch = []
        for prop in shown:
            spec = self.act2.get("touch", {}).get(prop)
            if spec:
                touch.append({
                    "prop": prop,
                    "verb": self._loc(locale, f"act2|t:{prop}|verb",
                                      spec.get("verb", "")),
                })
        exit_offer = None
        ex = self.act2.get("exit")
        if ex and self._exit_ready(mem, rng, diff):
            exit_offer = {
                "tempt": self._loc(locale, "act2|exit|tempt", ex.get("tempt", "")),
                "action": self._loc(locale, "act2|exit|action", ex.get("action", "")),
            }

        return {
            "heading": heading,
            "sentences": sentences,
            "adaptive": adaptive_line,
            "sign_text": sign_text,
            "shown": shown,
            "touch": touch,
            "exit_offer": exit_offer,
            "npc_utterance": npc_utterance,   # coach: the one fixed arming line
            # the audit keys that compose this level (for level-QE); stripped
            # from the public payload like any other underscore field.
            "_keys": ([head_key] if head_key else []) + keys,
            # server-authoritative truth, never sent to the client:
            "_has_anomaly": has_anomaly,
            "_anomaly_prop": anomaly_prop,
            "_anomaly_val": anomaly_val,
            "_anomaly_props": anomaly_props,
        }

    def public(self, room: dict) -> dict:
        """Strip the answer before sending a room to the browser."""
        return {k: v for k, v in room.items() if not k.startswith("_")}

    def meta_for(self, locale: Optional[str] = None) -> dict:
        """The arc meta with its display strings localized for the payload."""
        m = dict(self.meta)
        m["title"] = self._loc(locale, "title_main", m.get("title", ""))
        m["tagline"] = self._loc(locale, "tagline", m.get("tagline", ""))
        m["go_on"] = self._loc(locale, "go_on", m.get("go_on", ""))
        m["turn_back"] = self._loc(locale, "turn_back", m.get("turn_back", ""))
        m["progress"] = self._loc(locale, "progress", m.get("progress", ""))
        m["share_prompt"] = self._loc(locale, "share_prompt", m.get("share_prompt", ""))
        return m

    def interact(self, prop: str, mem: PlayerMemory, rng: random.Random,
                 locale: Optional[str], goal: int) -> Optional[dict]:
        """Resolve a touch on a shown detail into one flavour outcome. Returns
        {kind, line} for flashback / reaction / herring / fold, or None if the
        detail is not touchable. NEVER reads the anomaly, so it cannot be a
        detector, and never changes the go-on/turn-back judgement."""
        spec = self.act2.get("touch", {}).get(prop)
        if not spec:
            return None
        if spec.get("fold") and rng.random() < act2_fold_chance(mem.level, goal):
            kind = "fold"
        else:
            choices = []
            if self.act2.get("flashbacks"):
                choices.append("flashback")
            if spec.get("reaction"):
                choices.append("reaction")
            if spec.get("herring"):
                choices.append("herring")
            if not choices:
                return None
            kind = rng.choice(choices)
        if kind == "flashback":
            pool = self.act2.get("flashbacks", [])
            idx = rng.randrange(len(pool))
            line = self._loc(locale, f"act2|flashback|{idx}", pool[idx])
        else:
            pool = spec.get(kind, [])
            idx = rng.randrange(len(pool))
            line = self._loc(locale, f"act2|t:{prop}|{kind}|{idx}", pool[idx])
        # idx lets the client collect flashbacks (which fragment was seen).
        return {"kind": kind, "line": line, "idx": idx}

    def take_exit(self, locale: Optional[str] = None) -> List[str]:
        """The alternate-ending text for taking the arc's false way out."""
        ex = self.act2.get("exit", {})
        eid = ex.get("ending", "")
        pool = self.act2.get("endings", {}).get(eid, [])
        return [self._loc(locale, f"act2|end|{eid}|{i}", t)
                for i, t in enumerate(pool)]

    def _framing(self, locale: Optional[str], kind: str) -> List[str]:
        pool = self.data["framing"][kind]
        return [self._loc(locale, f"framing|{kind}|{i}", t) for i, t in enumerate(pool)]

    def intro(self, locale: Optional[str] = None) -> List[str]:
        return self._framing(locale, "intro")

    def cutscene(self, locale: Optional[str] = None) -> List[str]:
        """A short, arc-specific restatement of the rule, shown the first time
        the player is reset, before the instructions. Empty if the arc has none."""
        if "cutscene" not in self.data.get("framing", {}):
            return []
        return self._framing(locale, "cutscene")

    def win(self, locale: Optional[str] = None) -> List[str]:
        return self._framing(locale, "win")

    def attempt_line(self, locale: Optional[str], n: int) -> str:
        """A one-line, in-world 'solved in N runs' note for the win screen.
        A clean first run gets its own line; otherwise {n} is spliced in."""
        if n <= 1:
            return self._loc(locale, "attempt_first",
                             self.meta.get("attempt_first", ""))
        tmpl = self._loc(locale, "attempt", self.meta.get("attempt", ""))
        return tmpl.replace("{n}", str(n))

    def long_look(self, locale: Optional[str], rng: random.Random) -> str:
        pool = self.data["adaptive"]["long_look"]
        idx = rng.randrange(len(pool))
        return self._loc(locale, f"adaptive|long_look|{idx}", pool[idx])
