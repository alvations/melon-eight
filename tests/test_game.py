# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Tests for the memory-loop game.

Runnable two ways:
    python -m pytest tests/test_game.py -q      # if pytest is installed
    python tests/test_game.py                   # plain runner, no deps

Covers the arc-selection regression (state must survive with NO cookies, as in a
cross-site iframe), random-walk invariants, the difficulty ramp, and win paths.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A
from hallway import (
    GOAL, Hallway, anomaly_chance, list_arcs,
    act2_exit_ready, act2_fold_chance,
)
from memory import PlayerMemory

ARC_IDS = [a["id"] for a in list_arcs()]
# heading words that legitimately appear for each arc (accounting for drift)
ARC_WORDS = {
    "hallway-eight": ("Hallway", "Corridor", "HALLWAY"),
    "stairway8": ("Stairway", "Stairwell", "STAIRWAY"),
    "coach8": ("Coach", "Carriage", "COACH"),
}
NPC = {"hallway-eight": "figure", "stairway8": "figure", "coach8": "passenger"}
NPC_TWIST = {"figure": "knows", "passenger": "speaks"}


# --- helpers ---------------------------------------------------------------

def _json(resp):
    return resp.get_json()


def _new(client, arc, sid=None):
    hdrs = {"X-Sid": sid} if sid else {}
    return _json(client.post("/api/new", json={"arc": arc}, headers=hdrs))


def _act(client, sid, choice, confidence=None):
    """Act using a FRESH client each call is the caller's job; here we just send
    the sid header so state resolves without any cookie."""
    return _json(
        client.post(
            "/api/act",
            json={"choice": choice, "confidence": confidence},
            headers={"X-Sid": sid},
        )
    )


def _answer(sid):
    """White-box peek at the current room's truth, to play optimally in tests."""
    return A.STATE[sid]["room"]["_has_anomaly"]


# --- tests -----------------------------------------------------------------

def test_arcs_listed():
    c = A.app.test_client()
    data = _json(c.get("/api/arcs"))
    ids = [a["id"] for a in data["arcs"]]
    assert data["default"] == "hallway-eight"
    assert set(ids) == set(ARC_IDS)
    assert ids[0] == "hallway-eight"  # default first


def test_each_arc_starts_correctly():
    c = A.app.test_client()
    for arc in ARC_IDS:
        p = _new(c, arc)
        assert p["meta"]["id"] == arc, (arc, p["meta"]["id"])
        assert p["sid"], "server must return a session id"
        assert p["level"] == 0 and p["goal"] == GOAL
        assert p["room"]["sentences"], "a room must have text"
        # the answer must never leak to the client
        assert not any(k.startswith("_") for k in p["room"])


def test_arc_persists_without_cookies():
    """Regression: on Spaces the app runs in a cross-site iframe and the session
    cookie is dropped. Using a BRAND-NEW client (empty cookie jar) for every
    request, the arc and progress must still persist via the echoed sid."""
    for arc in ARC_IDS:
        starter = A.app.test_client()
        p = _new(starter, arc)
        sid = p["sid"]
        assert p["meta"]["id"] == arc

        rng = random.Random(1234)
        for step in range(60):
            fresh = A.app.test_client()  # no cookies at all
            fresh.delete_cookie("session")
            ans = _answer(sid)
            choice = "back" if (ans and rng.random() < 0.8) else (
                "continue" if not ans and rng.random() < 0.8 else
                rng.choice(["continue", "back"])
            )
            r = _act(fresh, sid, choice, confidence=rng.choice([None, 1, 4]))
            assert r["sid"] == sid, "sid must be stable across cookieless calls"
            assert r["meta"]["id"] == arc, (
                f"arc flipped to {r['meta']['id']} at step {step} (expected {arc})"
            )
            assert 0 <= r["level"] <= GOAL


def test_switch_arcs_reuses_sid():
    c = A.app.test_client()
    p1 = _new(c, "coach8")
    sid = p1["sid"]
    assert p1["meta"]["id"] == "coach8"
    # start a different arc with the same sid -> must switch, not revert
    p2 = _new(c, "stairway8", sid=sid)
    assert p2["meta"]["id"] == "stairway8"
    # and it stays switched across further cookieless calls
    for _ in range(10):
        fresh = A.app.test_client()
        r = _act(fresh, sid, "continue")
        assert r["meta"]["id"] == "stairway8"


def test_random_walk_invariants():
    c = A.app.test_client()
    for arc in ARC_IDS:
        p = _new(c, arc)
        sid = p["sid"]
        rng = random.Random(99)
        for _ in range(400):
            ans = _answer(sid)
            choice = rng.choice(["continue", "back"])
            r = _act(c, sid, choice)
            expected_correct = (choice == "back") == ans
            assert r["correct"] == expected_correct
            assert r["had_anomaly"] == ans
            if not r["won"]:
                assert 0 <= r["level"] < GOAL
            assert not any(k.startswith("_") for k in r["room"])


def test_optimal_play_wins_in_goal_steps():
    c = A.app.test_client()
    for arc in ARC_IDS:
        p = _new(c, arc)
        sid = p["sid"]
        won = False
        for step in range(GOAL):
            ans = _answer(sid)
            r = _act(c, sid, "back" if ans else "continue", confidence=4)
            assert r["correct"]
            if step < GOAL - 1:
                assert r["level"] == step + 1
        # the GOAL-th correct call wins
        assert r["won"], (arc, "should win after GOAL correct calls")
        assert r["win_text"], "win must carry win text"
        assert r["level"] == 0, "progress resets after a win"
        won = True
        assert won


def test_win_reports_attempts_and_line():
    """The win payload carries the run count and a localized in-world line:
    a clean first run reads '1' with the first-run wording; one forced reset
    makes it the second attempt and the counted wording (with the number)."""
    c = A.app.test_client()

    # clean optimal run -> attempts == 1, first-run line (no {n} left in it)
    p = _new(c, "hallway-eight")
    sid = p["sid"]
    for _ in range(GOAL):
        ans = _answer(sid)
        r = _act(c, sid, "back" if ans else "continue", confidence=4)
    assert r["won"] and r["attempts"] == 1
    assert r["attempt_text"] and "{n}" not in r["attempt_text"]

    # one deliberate wrong call resets the run; the next clean win is attempt 2
    p = _new(c, "hallway-eight")
    sid = p["sid"]
    ans = _answer(sid)
    r = _act(c, sid, "continue" if ans else "back", confidence=4)  # wrong on purpose
    assert not r["correct"]
    for _ in range(GOAL):
        ans = _answer(sid)
        r = _act(c, sid, "back" if ans else "continue", confidence=4)
    assert r["won"] and r["attempts"] == 2
    assert "2" in r["attempt_text"] and "{n}" not in r["attempt_text"]


def test_each_arc_has_its_own_resting_benediction():
    """The last win line is the resting benediction (the client renders it as the
    .lead on the win screen, the last thing the player reads). It must be
    arc-supplied and arc-specific, never a shared, engine-wide line, so each arc
    keeps its own closing note. Guards against a hardcoded/shared benediction
    (and the win_text must actually come from the arc's own framing.win)."""
    last = {}
    for arc in ARC_IDS:
        win = Hallway(arc).win(None)
        assert win, f"{arc} has no framing.win"
        assert win[-1].strip(), f"{arc} resting line is empty"
        last[arc] = win[-1].strip()
    # every arc's resting line is distinct: no single benediction shared across arcs
    vals = list(last.values())
    assert len(set(vals)) == len(vals), f"resting lines must be per-arc: {last}"
    # and each is served as the win payload's last line, per arc
    c = A.app.test_client()
    for arc in ARC_IDS:
        p = _new(c, arc)
        sid = p["sid"]
        for _ in range(GOAL):
            ans = _answer(sid)
            r = _act(c, sid, "back" if ans else "continue", confidence=4)
        assert r["won"], (arc, "should win")
        assert r["win_text"][-1].strip() == last[arc], (
            arc, "win payload must end with the arc's own benediction",
            r["win_text"][-1], last[arc])


def test_difficulty_ramp():
    # monotonic and bounded
    assert anomaly_chance(0) < anomaly_chance(3) < anomaly_chance(7)
    assert anomaly_chance(0) <= 0.25
    assert anomaly_chance(100) <= 0.55 + 1e-9
    # statistical: level 0 yields fewer anomalies than a later level
    for arc in ARC_IDS:
        h = Hallway(arc)
        rng = random.Random(2024)
        def rate(level, n=3000):
            hits = 0
            for _ in range(n):
                mem = PlayerMemory(level=level)
                if h.build(mem, rng)["_has_anomaly"]:
                    hits += 1
            return hits / n
        r0, r6 = rate(0), rate(6)
        # The opening loop is *very* low (no baseline yet), but not zero, and far
        # below the deeper loops. Hard's cross-loop persistence must also not
        # fire on the opening loop (a reset sends you back to level 0).
        assert r0 < 0.06, (arc, "opening loop must be very low", r0)
        assert r0 < r6, (arc, r0, r6)
        assert r6 > 0.30, (arc, "later loops ramp up", r6)
        for diff in ("easy", "normal", "hard"):
            hits = sum(
                h.build(PlayerMemory(level=0, loops=5, prev_anomaly_prop=NPC[arc],
                                     prev_anomaly_val=NPC_TWIST[NPC[arc]]),
                        random.Random(s), None, diff)["_has_anomaly"]
                for s in range(2000))
            assert hits / 2000 < 0.06, (arc, diff, "opening stays low even after a reset")


def test_aggro_item_is_held_then_revealed_fairly():
    """A late-revealed detail (aggro-item) stays out of the early loops, only
    appears mid-run, and can NEVER be the change on the loop it first appears
    (so a late arrival is memory, never pure luck). Hard always holds one;
    normal sometimes; easy never."""
    for arc in ARC_IDS:
        h = Hallway(arc)
        late = h.meta.get("late_props", [])
        assert late, (arc, "each arc names a couple of late props")
        assert all(p in h.properties for p in late), (arc, late)

        hard_held = norm_held = easy_held = 0
        for seed in range(300):
            for diff, tag in (("hard", "h"), ("normal", "n"), ("easy", "e")):
                mem = PlayerMemory()
                rng = random.Random(hash((arc, diff, seed)) & 0xFFFFFFFF)
                seen_first = {}
                for lvl in range(GOAL):
                    mem.level = lvl
                    mem.loops += 1
                    room = h.build(mem, rng, None, diff)
                    held = dict(mem.held)          # prop -> reveal level
                    shown = room["shown"]
                    # a held detail must not show before its reveal loop
                    for p, rv in held.items():
                        if lvl < rv:
                            assert p not in shown, (arc, diff, lvl, p)
                    for p in shown:
                        seen_first.setdefault(p, lvl)
                    # a held detail can never be the change on the loop it is
                    # first seen: its baseline must have been shown earlier, so a
                    # late arrival is memory, never pure luck. (Ordinary details
                    # may still change on first sight, as they always have.)
                    for ap in room["_anomaly_props"]:
                        if ap in held:
                            assert seen_first.get(ap, lvl) < lvl, (
                                arc, diff, lvl, ap, "aggro-item changed on first sight")
                n_held = len(mem.held)
                if tag == "h":
                    hard_held += n_held > 0
                    assert 1 <= n_held <= 2, (arc, "hard holds one or two", n_held)
                elif tag == "n":
                    norm_held += n_held > 0
                    assert n_held <= 1, (arc, "normal holds at most one", n_held)
                else:
                    easy_held += n_held
        assert hard_held == 300, (arc, "hard always holds a late prop", hard_held)
        # normal holds only rarely (a fair chance to meet almost everything)
        assert 0 < norm_held < 120, (arc, "normal rarely holds", norm_held)
        assert easy_held == 0, (arc, "easy never holds", easy_held)


def test_flare_props_only_on_correct_double_turn_back():
    """flare_props (hard mode's post-hoc "two things moved" pulse) must appear
    ONLY on a correct turn-back where two details changed, and never otherwise.
    It rides the server/client answer boundary, so pin its exact shape."""
    c = A.app.test_client()

    def act_with_room(fields, choice):
        # Start a fresh slot, then override the current room's truth so we can
        # drive each decision branch deterministically.
        p = _new(c, "hallway-eight")
        sid = p["sid"]
        A.STATE[sid]["room"].update(fields)
        return _act(c, sid, choice, confidence=4)

    two = {"_has_anomaly": True, "_anomaly_props": ["poster", "sign"],
           "_anomaly_prop": "poster", "_anomaly_val": "gone"}
    one = {"_has_anomaly": True, "_anomaly_props": ["poster"],
           "_anomaly_prop": "poster", "_anomaly_val": "gone"}
    clean = {"_has_anomaly": False, "_anomaly_props": [],
             "_anomaly_prop": None, "_anomaly_val": None}

    # correct two-change turn-back: flare both changed lines, in order
    r = act_with_room(two, "back")
    assert r["correct"] and r.get("flare_props") == ["poster", "sign"]

    # two changed but walked on (wrong call): no flare
    r = act_with_room(two, "continue")
    assert not r["correct"] and "flare_props" not in r

    # only one change, correct turn-back: no flare (needs two)
    r = act_with_room(one, "back")
    assert r["correct"] and "flare_props" not in r

    # nothing changed, turned back (false report): no flare
    r = act_with_room(clean, "back")
    assert not r["correct"] and "flare_props" not in r

    # nothing changed, walked on (correct): correct but no flare
    r = act_with_room(clean, "continue")
    assert r["correct"] and "flare_props" not in r
    # and the room handed back is still stripped of every answer key
    assert not any(k.startswith("_") for k in r["room"])


def test_npc_and_sense_present():
    for arc in ARC_IDS:
        h = Hallway(arc)
        npc = NPC[arc]
        assert npc in h.properties and npc in h.data["anchor_order"]
        assert NPC_TWIST[npc] in h.properties[npc]["anomalies"]
        assert "sense" in h.properties and h.properties["sense"]["anomalies"]


# --- Act 2: touch-the-room interactions ------------------------------------

def test_act2_content_integrity():
    """Every arc's Act 2 touches a real detail and its exit points at a real
    ending (see docs/ACT2.md)."""
    for arc in ARC_IDS:
        h = Hallway(arc)
        a = h.act2
        assert a.get("flashbacks"), arc
        assert a.get("touch"), arc
        for prop, spec in a["touch"].items():
            assert prop in h.properties, (arc, prop, "touch a real detail")
            assert spec.get("verb"), (arc, prop)
            for kind in ("reaction", "herring", "fold"):
                assert spec.get(kind), (arc, prop, kind)
        ex = a.get("exit", {})
        assert ex.get("ending") in a.get("endings", {}), arc
        assert a["endings"][ex["ending"]], arc


def test_act2_interact_is_flavor_and_leakproof():
    """A touch resolves to a flavour outcome only, never reads the answer, and
    an unknown detail is a no-op."""
    for arc in ARC_IDS:
        h = Hallway(arc)
        for prop in h.act2["touch"]:
            kinds = set()
            for s in range(200):
                res = h.interact(prop, PlayerMemory(level=4),
                                 random.Random(s), "en_US", GOAL)
                assert res and res["kind"] in (
                    "flashback", "reaction", "herring", "fold"), (arc, prop)
                assert res["line"], (arc, prop)
                kinds.add(res["kind"])
            assert "flashback" in kinds, (arc, prop)
        assert h.interact("nope", PlayerMemory(level=4),
                          random.Random(1), "en_US", GOAL) is None


def test_act2_touch_only_for_shown_details():
    for arc in ARC_IDS:
        h = Hallway(arc)
        for s in range(40):
            r = h.build(PlayerMemory(level=s % 8), random.Random(s), "en_US")
            shown = set(r["shown"])
            for t in r["touch"]:
                assert t["prop"] in shown and t["prop"] in h.act2["touch"]
            assert not any(k.startswith("_") for k in h.public(r)), arc


def test_false_exit_gated_to_three_quarter_mark():
    """The false exit only surfaces around the 3/4 mark: never early, never on
    the final level, so ignoring it is almost always the only option."""
    for arc in ARC_IDS:
        h = Hallway(arc)
        eligible = [lvl for lvl in range(GOAL)
                    if any(act2_exit_ready(lvl, GOAL, random.Random(s))
                           for s in range(1500))]
        assert eligible, arc
        assert all(4 <= lvl <= GOAL - 2 for lvl in eligible), (arc, eligible)


def test_fold_never_before_onset():
    assert act2_fold_chance(0, 8) == 0.0
    assert act2_fold_chance(2, 8) == 0.0
    assert act2_fold_chance(3, 8) > 0.0
    assert act2_fold_chance(7, 8) >= act2_fold_chance(4, 8)


def test_take_exit_ends_run_not_in_a_win():
    c = A.app.test_client()
    for arc in ARC_IDS:
        p = _new(c, arc)
        sid = p["sid"]
        for _ in range(3):
            ans = _answer(sid)
            _act(c, sid, "back" if ans else "continue", confidence=4)
        res = _json(c.post("/api/interact", json={"action": "exit"},
                           headers={"X-Sid": sid}))
        assert res["kind"] == "exit"
        assert len(res.get("ending", [])) >= 2
        assert res["level"] == 0, "the run resets after a false exit"
        assert not res.get("won"), "a false exit is never a win"
        assert not any(k.startswith("_") for k in res.get("room", {}))


# --- Insane difficulty (hidden, anti-bot) ----------------------------------
# Insane randomizes each run's baseline from a property's FULL value set, so the
# "clean" vocabulary is run-specific and a bot that memorized the global all-clear
# wording cannot tell clean from changed. These guard both that behavior AND that
# the existing modes are completely untouched by it.

from hallway import DIFFICULTIES, EXPOSED_DIFFICULTIES, norm_difficulty  # noqa: E402


def test_insane_is_a_difficulty_but_not_exposed():
    # It exists on the server (so a client that has earned it can send X-Diff),
    # but it is deliberately absent from the exposed set (the picker ships
    # easy/normal/hard only; Insane is unlocked client-side).
    assert "insane" in DIFFICULTIES
    assert "insane" not in EXPOSED_DIFFICULTIES
    assert tuple(EXPOSED_DIFFICULTIES) == ("easy", "normal", "hard")
    # An unknown/garbage difficulty still degrades to normal, never to insane.
    assert norm_difficulty("INSANE!!") == "normal"
    assert norm_difficulty(None) == "normal"


def test_existing_modes_never_touch_the_insane_baseline():
    # The whole insane implementation is gated behind `diff == "insane"`. Prove
    # the other modes never enter it: their run_baseline stays empty across a full
    # climb, and every change they make is drawn from the fixed `anomalies` set
    # (the non-insane path), never an arbitrary value from the full set.
    for arc in ARC_IDS:
        h = Hallway(arc)
        for diff in ("easy", "normal", "hard"):
            for seed in range(12):
                mem = PlayerMemory()
                rng = random.Random(seed)
                for lvl in range(8):
                    mem.level = lvl
                    room = h.build(mem, rng, None, diff)
                    assert mem.run_baseline == {}, (arc, diff, "insane branch fired")
                    p = room["_anomaly_prop"]
                    if p is not None:
                        # A non-insane change is always a declared anomaly value.
                        assert room["_anomaly_val"] in h.properties[p]["anomalies"], \
                            (arc, diff, p)


def _insane_varying_prop(h):
    """A property whose baseline-SAFE pool has >1 value, so insane still
    randomizes its baseline (some properties fairly collapse to their calm
    value; the anti-bot property lives in the ones that don't)."""
    return next(p for p, s in h.properties.items()
                if len(Hallway._insane_baseline_keys(s, p, h.npc_prop)) > 1)


def test_insane_randomizes_baseline_per_run():
    # Across runs, a property's run-baseline actually varies (drawn from its
    # baseline-safe pool), or insane would collapse back into normal.
    for arc in ARC_IDS:
        h = Hallway(arc)
        prop = _insane_varying_prop(h)
        safe = set(Hallway._insane_baseline_keys(h.properties[prop], prop, h.npc_prop))
        seen = set()
        for seed in range(60):
            mem = PlayerMemory(level=0)
            h.build(mem, random.Random(seed), None, "insane")
            assert mem.run_baseline, (arc, "insane set no baseline")
            assert set(mem.run_baseline) == set(h.properties), (arc, "baseline gaps")
            seen.add(mem.run_baseline[prop])
        assert len(seen) > 1, (arc, prop, "run-baseline never varied")
        assert seen <= safe and not (seen - safe)


def test_insane_clean_vocabulary_is_not_the_fixed_baseline_set():
    # The anti-bot core. On CLEAN (no-change) insane loops, the value a property
    # shows spans its full set across runs, INCLUDING values that are anomalies in
    # normal mode. In normal mode a clean loop only ever shows the fixed baseline.
    # So a dictionary of "normal-mode clean wording" cannot classify insane loops.
    for arc in ARC_IDS:
        h = Hallway(arc)
        # a property whose baseline-safe pool includes a value that is an anomaly
        # in normal mode (so insane's clean vocabulary genuinely exceeds normal's).
        prop = next(
            p for p, s in h.properties.items()
            if set(Hallway._insane_baseline_keys(s, p, h.npc_prop))
            & set(s.get("anomalies", {})))
        anomaly_values = set(h.properties[prop]["anomalies"])
        insane_clean_vals = set()
        # Drive many insane runs; on a loop where `prop` is shown and unchanged,
        # record the value used as this run's baseline for it.
        for seed in range(120):
            mem = PlayerMemory(level=0)
            for lvl in range(4):
                mem.level = lvl
                room = h.build(mem, random.Random(seed * 100 + lvl), None, "insane")
                if prop in room["shown"] and prop not in room["_anomaly_props"]:
                    insane_clean_vals.add(mem.run_baseline[prop])
        # In normal mode, the same prop shown-and-clean is ALWAYS the baseline.
        normal_clean_vals = set()
        for seed in range(120):
            mem = PlayerMemory(level=0)
            for lvl in range(4):
                mem.level = lvl
                room = h.build(mem, random.Random(seed * 7 + lvl), None, "normal")
                if prop in room["shown"] and prop not in room["_anomaly_props"]:
                    normal_clean_vals.add(h.properties[prop]["baseline"])
        assert normal_clean_vals <= {h.properties[prop]["baseline"]}, arc
        # Insane's clean vocabulary reaches values that normal treats as changes.
        assert insane_clean_vals & anomaly_values, \
            (arc, prop, "insane clean loops never used a normal-anomaly value")


def test_insane_anomaly_always_differs_from_the_run_baseline():
    # When insane does change a property, the changed value is never equal to this
    # run's baseline for it (else the "change" would be invisible / unfair).
    for arc in ARC_IDS:
        h = Hallway(arc)
        checked = 0
        for seed in range(200):
            mem = PlayerMemory(level=0)
            for lvl in range(8):
                mem.level = lvl
                room = h.build(mem, random.Random(seed * 13 + lvl), None, "insane")
                # _anomaly_val is the PRIMARY change's value, so it is only
                # comparable to the primary prop's baseline. (A double change's
                # second prop can share a value key with the primary, e.g. both
                # "steady" for lighting/sense, which is not a bug.) The second
                # prop's value != its baseline is guaranteed by construction:
                # pick_anomaly(baseline_of=run_baseline) never returns the baseline.
                p = room["_anomaly_prop"]
                if p is not None:
                    assert room["_anomaly_val"] != mem.run_baseline.get(p), \
                        (arc, p, "primary change equals the run baseline")
                    checked += 1
        assert checked > 0, (arc, "no insane anomaly ever fired to check")


def test_insane_anomaly_only_on_a_property_seen_at_baseline_this_run():
    # Fairness: because the baseline is run-specific, a change may only land on a
    # property the player has already met at baseline earlier in THIS run. So the
    # opening loop is a clean baseline and a detail's first appearance is never
    # the trap.
    for arc in ARC_IDS:
        h = Hallway(arc)
        for seed in range(120):
            mem = PlayerMemory(level=0)
            seen_before = set()
            for lvl in range(8):
                mem.level = lvl
                # snapshot what had been seen at baseline BEFORE this loop
                before = set(mem.seen_props)
                room = h.build(mem, random.Random(seed * 17 + lvl), None, "insane")
                for p in room["_anomaly_props"]:
                    if p is None:
                        continue
                    assert p in before, \
                        (arc, seed, lvl, p, "changed a prop not yet seen this run")


def test_insane_is_strictly_harder_than_hard():
    # Insane must be the hardest tier: a higher anomaly ramp than hard at every
    # level past the opening, a higher cap, AND it inherits hard's escalations
    # (aggro holds) on top of its randomized baseline.
    from hallway import anomaly_chance
    for lvl in range(1, 8):
        assert anomaly_chance(lvl, "insane") >= anomaly_chance(lvl, "hard"), lvl
    assert anomaly_chance(7, "insane") > anomaly_chance(7, "hard"), "insane cap must exceed hard"
    # Insane holds aggro items like hard does (memory pressure), across arcs.
    for arc in ARC_IDS:
        h = Hallway(arc)
        if not h.meta.get("late_props"):
            continue
        held_runs = 0
        for seed in range(40):
            mem = PlayerMemory(level=0)
            h.build(mem, random.Random(seed), None, "insane")
            if mem.held:
                held_runs += 1
        assert held_runs > 0, (arc, "insane never held an aggro item")


def test_insane_baseline_never_reads_as_a_change():
    # Option-2 fairness fix: an insane run-baseline must never be a value whose
    # prose announces a change or references the player's memory (which would make
    # a clean loop read as wrong and a fair turn-back reset the player), nor the
    # NPC's acknowledgement. Every property still keeps its calm value as a safe
    # baseline, so the pool is never empty.
    from hallway import _INSANE_BASELINE_UNSAFE, _NPC_ACK_VALUES
    for arc in ARC_IDS:
        h = Hallway(arc)
        for prop, spec in h.properties.items():
            keys = Hallway._insane_baseline_keys(spec, prop, h.npc_prop)
            assert keys, (arc, prop, "insane baseline pool empty")
            # the calm value(s) must always be allowed
            for calm in spec.get("values", {}):
                assert calm in keys, (arc, prop, calm, "calm value dropped")
            for val in keys:
                if val in spec.get("values", {}):
                    continue
                # every allowed anomaly baseline reads as a plain state
                assert not (prop == h.npc_prop and val in _NPC_ACK_VALUES), \
                    (arc, prop, val, "NPC acknowledgement used as baseline")
                pool = spec["anomalies"][val]
                bad = [m for s in pool for m in _INSANE_BASELINE_UNSAFE
                       if m in s.lower()]
                assert not bad, (arc, prop, val, "change/memory prose as baseline", bad[:2])


def test_insane_payload_still_hides_the_answer():
    # Insane must not leak: the public room drops every underscore key, and the
    # run baseline lives only in server memory, never in the payload.
    h = Hallway(ARC_IDS[0])
    mem = PlayerMemory(level=3)
    # seed seen_props so a change is allowed, then build until one fires
    for lvl in range(4):
        mem.level = lvl
        room = h.build(mem, random.Random(99 + lvl), None, "insane")
    pub = h.public(room)
    assert not any(k.startswith("_") for k in pub)
    assert "run_baseline" not in pub


# --- sign drift fairness ----------------------------------------------------

_ARROWS = set("→←⇢⇠↔⟶⟵➜⭢⭠▶◀")  # → ← ⇢ ⇠ ↔ ⟶ ⟵ ➜ ⭢ ⭠ ▶ ◀


def test_sign_drift_never_swaps_the_arrow_glyph():
    # The {SIGN} drift is a RED HERRING: it must vary only spacing/case, never the
    # arrow glyph. Arrow changes are a real anomaly (the sign's "reversed" value),
    # so a clean-loop arrow swap makes a fair turn-back reset the player "wrongly."
    # Regression: "EXIT ⇢" used to sit in hallway's drift pool.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for arc in ARC_IDS:
        data = json.load(open(os.path.join(root, "data", "arcs", f"{arc}.json"),
                              encoding="utf-8"))
        variants = data.get("sign_variants", []) or []
        drift_arrows = {ch for v in variants for ch in v if ch in _ARROWS}
        # The drift may use at most ONE arrow glyph (the stable baseline one).
        assert len(drift_arrows) <= 1, \
            (arc, "sign drift uses more than one arrow glyph", drift_arrows)
        # That drift arrow must never also be an arrow an anomaly uses (the change).
        anomaly_arrows = set()
        for spec in data["properties"].values():
            uses_sign = any("{SIGN}" in s
                            for pool in spec.get("values", {}).values() for s in pool)
            if not uses_sign:
                continue
            for pool in spec.get("anomalies", {}).values():
                for s in pool:
                    anomaly_arrows |= {ch for ch in s if ch in _ARROWS}
        assert not (drift_arrows & anomaly_arrows), \
            (arc, "a drift arrow collides with an anomaly arrow",
             drift_arrows & anomaly_arrows)


# --- plain runner (no pytest needed) ---------------------------------------

if __name__ == "__main__":
    # Discover every tests/test_*.py so this one command runs the whole suite.
    import glob as _glob
    import importlib as _il

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    _here = os.path.dirname(os.path.abspath(__file__))
    for _p in sorted(_glob.glob(os.path.join(_here, "test_*.py"))):
        _mod = os.path.splitext(os.path.basename(_p))[0]
        if _mod == "test_game":
            continue
        _m = _il.import_module(_mod)
        fns += [v for k, v in sorted(vars(_m).items()) if k.startswith("test_")]

    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
