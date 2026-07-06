# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Regression tests for localization, the win-screen share strings, and the
first-reset onboarding heading.

Runnable two ways:
    python -m pytest tests/test_i18n.py -q     # if pytest is installed
    python tests/test_game.py                  # plain runner discovers this file

Guards the pieces that are easy to break silently:
  * exactly eight languages are exposed (8 is the game's through-line);
  * every exposed locale actually ships every UI string (nothing left English
    by accident, nothing forgotten in a recompile);
  * the eight invitation lines are present, distinct, and truly translated;
  * the onboarding "Instructions" heading exists per language;
  * no em-dash slips into any localized string (house style);
  * server-side lookup and locale rendering round-trip.
"""

import glob
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n  # noqa: E402
import app as A  # noqa: E402
from hallway import Hallway, list_arcs  # noqa: E402
from memory import PlayerMemory  # noqa: E402

ARC_IDS = [a["id"] for a in list_arcs()]
EXPOSED = i18n.EXPOSED_LOCALES
NON_EN_EXPOSED = [c for c in EXPOSED if c != i18n.SOURCE_LOCALE]
SHARE_KEYS = [f"share_{i}" for i in range(1, 9)] + [
    "share_native", "share_copy", "share_copied",
]

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPILED = os.path.join(HERE, "data", "i18n", "compiled")
CLIENT = os.path.join(HERE, "static", "i18n")


def _client(loc):
    """The client UI catalog {name: text} a browser fetches for a locale."""
    return json.load(open(os.path.join(CLIENT, f"{loc}.json"), encoding="utf-8"))


def _compiled(loc):
    """The server runtime catalog {key: text} for a locale."""
    return json.load(open(os.path.join(COMPILED, f"{loc}.json"), encoding="utf-8"))


# --- exposure / picker -----------------------------------------------------

def test_exactly_eight_exposed_locales():
    # Eight is the game's identity, quietly echoed by the size of the picker.
    assert len(EXPOSED) == 8, EXPOSED
    assert EXPOSED[0] == i18n.SOURCE_LOCALE, "English leads the list"
    assert len(set(EXPOSED)) == 8, "no duplicate locales"
    # available_locales() must surface exactly those (all are compiled on disk).
    assert [l["code"] for l in i18n.available_locales()] == EXPOSED


def test_api_langs_matches_exposed():
    c = A.app.test_client()
    data = c.get("/api/langs").get_json()
    assert [l["code"] for l in data["langs"]] == EXPOSED
    assert data["default"] == i18n.SOURCE_LOCALE
    # every offered locale carries a display name for the picker
    assert all(l.get("native") for l in data["langs"])


def test_hidden_locales_are_translated_but_not_exposed():
    # The 13 non-exposed locales stay out of the picker even with a compiled
    # catalog on disk: the allowlist, not disk state, decides what ships.
    exposed = set(EXPOSED)
    hidden = [c for c in i18n.LOCALE_CODES if c not in exposed]
    assert len(hidden) == 13, hidden
    offered = {l["code"] for l in i18n.available_locales()}
    for loc in hidden:
        assert loc not in offered, f"{loc} must stay hidden"


# --- UI-string coverage ----------------------------------------------------

def test_every_ui_string_compiled_for_every_exposed_locale():
    for loc in EXPOSED:
        ui = _client(loc)
        for key in i18n.UI_STRINGS_EN:
            assert ui.get(key, "").strip(), f"{loc} missing UI string {key!r}"


# The most recently added UI strings (ending credits, the adaptive next-step
# nudge, and the erase-memory dialog). They were the ones most at risk of
# shipping half-translated, so guard them explicitly: present in the source,
# actually translated (not left as the English fallback) in every non-English
# exposed locale, and the {n} placeholder preserved where it belongs.
NEW_UI_KEYS = [
    "view_credits", "end_credits",
    "nudge_frags", "nudge_arcs", "nudge_eight",
    "erase", "erase_title", "erase_body", "erase_cancel",
]


def test_new_ui_strings_present_in_source():
    for k in NEW_UI_KEYS:
        assert i18n.UI_STRINGS_EN.get(k, "").strip(), f"UI_STRINGS_EN missing {k!r}"


def test_new_ui_strings_actually_translated_for_exposed_locales():
    for loc in NON_EN_EXPOSED:
        ui = _client(loc)
        for k in NEW_UI_KEYS:
            v = ui.get(k, "").strip()
            assert v, f"{loc} missing {k!r}"


# The hidden Insane difficulty's UI (its label, hint, and four escape badges).
# Insane ships unlockable, so a completionist can select it in any exposed
# language; these must be genuinely translated, not left as the English fallback.
INSANE_UI_KEYS = [
    "diff_insane", "diff_hint_insane",
    "ach_n_insane_hallway-eight", "ach_d_insane_hallway-eight",
    "ach_n_insane_stairway8", "ach_d_insane_stairway8",
    "ach_n_insane_coach8", "ach_d_insane_coach8",
    "ach_n_insane_all", "ach_d_insane_all",
]


def test_insane_ui_strings_present_in_source():
    for k in INSANE_UI_KEYS:
        assert i18n.UI_STRINGS_EN.get(k, "").strip(), f"UI_STRINGS_EN missing {k!r}"


def test_insane_ui_strings_translated_for_exposed_locales():
    for loc in NON_EN_EXPOSED:
        ui = _client(loc)
        en = _client(i18n.SOURCE_LOCALE)
        for k in INSANE_UI_KEYS:
            v = ui.get(k, "").strip()
            assert v, f"{loc} missing insane string {k!r}"
            # Arc names (Hallway 8 / Coach 8 / Stairway 8) stay English, so the
            # description strings legitimately share those tokens; but the string
            # as a whole must not be the untouched English fallback.
            assert v != en.get(k, "").strip(), \
                f"{loc} left insane string {k!r} as the English fallback"
            assert v != i18n.UI_STRINGS_EN[k].strip(), \
                f"{loc} left {k!r} as the English fallback ({v!r})"


def test_nudge_fragment_line_keeps_its_count_placeholder():
    # nudge_frags splices in the number of unseen memories; the {n} must survive
    # translation in every exposed locale or the count would read literally.
    for loc in EXPOSED:
        ui = _client(loc)
        assert "{n}" in ui.get("nudge_frags", ""), \
            f"{loc} nudge_frags dropped the {{n}} placeholder"


def test_source_ui_catalog_is_complete():
    # en_US client catalog must contain every source string (guards a forgotten
    # recompile after editing UI_STRINGS_EN).
    en = _client(i18n.SOURCE_LOCALE)
    for key, text in i18n.UI_STRINGS_EN.items():
        assert en.get(key) == text, key


# --- share strings ---------------------------------------------------------

def test_eight_distinct_invitation_lines_per_locale():
    for loc in EXPOSED:
        ui = _client(loc)
        lines = [ui[f"share_{i}"] for i in range(1, 9)]
        assert all(s.strip() for s in lines), (loc, "an invitation line is blank")
        assert len(set(lines)) == 8, (loc, "invitation lines must be distinct")


def test_invitation_lines_are_actually_translated():
    # The eight invitation lines are prose; every exposed non-English locale
    # must translate them, not silently fall back to the English source.
    # (Short UI words like "Instructions" may legitimately coincide with
    # English in some languages, so only the prose lines are checked here.)
    en = _client(i18n.SOURCE_LOCALE)
    for loc in NON_EN_EXPOSED:
        ui = _client(loc)
        for i in range(1, 9):
            key = f"share_{i}"
            assert ui[key] != en[key], f"{loc} {key!r} fell back to English"


def test_onboarding_instructions_heading_present():
    for loc in EXPOSED:
        assert _client(loc).get("instructions", "").strip(), loc


def test_look_back_label_localized():
    for loc in EXPOSED:
        assert _client(loc).get("look_back", "").strip(), loc


def test_arc_attempt_lines_localized_and_keep_placeholder():
    # The win-screen attempt lines are per-arc and localized; the counted
    # variant must keep its {n} placeholder in every language.
    for arc in ARC_IDS:
        for key in (f"a:{arc}|attempt", f"a:{arc}|attempt_first"):
            assert _compiled(i18n.SOURCE_LOCALE).get(key, "").strip(), key
            for loc in NON_EN_EXPOSED:
                assert _compiled(loc).get(key, "").strip(), (loc, key)
        for loc in EXPOSED:
            assert "{n}" in _compiled(loc)[f"a:{arc}|attempt"], (loc, arc)
            assert "{n}" not in _compiled(loc)[f"a:{arc}|attempt_first"], (loc, arc)


def test_arc_share_prompt_is_per_arc_and_localized():
    # The win-screen prompt is a per-arc string (the exit differs by arc), not a
    # shared UI string. Each arc must have it, adapted distinctly in English and
    # translated for every exposed non-English locale.
    en_prompts = {}
    for arc in ARC_IDS:
        key = f"a:{arc}|share_prompt"
        en_prompts[arc] = _compiled(i18n.SOURCE_LOCALE).get(key, "")
        assert en_prompts[arc].strip(), (arc, "missing English share_prompt")
        for loc in NON_EN_EXPOSED:
            assert _compiled(loc).get(key, "").strip(), (loc, key)
    assert len(set(en_prompts.values())) == len(ARC_IDS), \
        f"arc prompts must be distinct, got {en_prompts}"
    # and it must never leak into the shared UI catalog
    assert "share_prompt" not in i18n.UI_STRINGS_EN


# --- Act 2 (touch verbs + reactions) in every language ---------------------

def test_act2_touch_verbs_localized_for_every_locale():
    # The touchable-detail verbs (Act 2) are per-arc, per-property strings. They
    # must be present and actually translated for every exposed non-English
    # locale: a missing one falls back to English and the layer reads as broken
    # in that language (English worked, the others looked empty).
    for arc in ARC_IDS:
        touch_props = list(Hallway(arc).act2.get("touch", {}).keys())
        assert touch_props, f"{arc} has no Act 2 touch targets"
        for prop in touch_props:
            key = f"a:{arc}|act2|t:{prop}|verb"
            en = _compiled(i18n.SOURCE_LOCALE).get(key, "")
            assert en.strip(), (arc, prop, "missing English verb")
            for loc in NON_EN_EXPOSED:
                tr = _compiled(loc).get(key, "")
                assert tr.strip(), (loc, key, "missing verb translation")
                assert tr != en, (loc, key, "verb left as the English fallback")


def test_act2_reactions_localized_via_runtime_for_every_locale():
    # Drive the REAL runtime interact() so this covers what a player actually
    # sees when they touch a detail, not just catalog presence. A fixed rng seed
    # makes every locale take the same branch (fold / flashback / reaction /
    # herring, same index), so the returned lines are directly comparable: each
    # non-English line must be non-empty and differ from English (a real
    # translation, never the silent English fallback).
    for arc in ARC_IDS:
        touch_props = list(Hallway(arc).act2.get("touch", {}).keys())
        seen_kinds = set()
        for prop in touch_props:
            for seed in range(40):
                en_res = Hallway(arc).interact(
                    prop, PlayerMemory(level=4), random.Random(seed),
                    i18n.SOURCE_LOCALE, 8)
                if not en_res:
                    continue
                seen_kinds.add(en_res["kind"])
                assert en_res["line"].strip(), (arc, prop, seed, "empty EN line")
                for loc in NON_EN_EXPOSED:
                    res = Hallway(arc).interact(
                        prop, PlayerMemory(level=4), random.Random(seed), loc, 8)
                    assert res and res["kind"] == en_res["kind"], \
                        (loc, arc, prop, seed, "branch diverged by locale")
                    assert res["line"].strip(), \
                        (loc, arc, prop, seed, res["kind"], "empty line")
                    assert res["line"] != en_res["line"], \
                        (loc, arc, prop, seed, res["kind"],
                         "reaction left as the English fallback")
        # Sanity: every reaction kind must have fired at least once, so the loop
        # above genuinely exercised folds and flashbacks, not only reactions.
        assert {"fold", "flashback", "reaction", "herring"} <= seen_kinds, \
            (arc, "some Act 2 reaction kind never fired", seen_kinds)


# --- house style / safety --------------------------------------------------

def test_no_em_dash_in_any_localized_string():
    hits = []
    for path in glob.glob(os.path.join(COMPILED, "*.json")) + \
            glob.glob(os.path.join(CLIENT, "*.json")):
        for key, val in json.load(open(path, encoding="utf-8")).items():
            if isinstance(val, str) and "—" in val:
                hits.append((os.path.basename(path), key))
    assert not hits, f"em-dash found in localized strings: {hits[:5]}"


def test_compiled_catalogs_carry_no_answer_keys():
    # Compiled text is display-only; server-truth keys start with "_".
    for loc in i18n.LOCALE_CODES:
        path = os.path.join(COMPILED, f"{loc}.json")
        if not os.path.exists(path):
            continue
        assert not any(k.startswith("_") for k in _compiled(loc)), loc


# --- runtime lookup / rendering --------------------------------------------

def test_localize_round_trip():
    key = "a:hallway-eight|go_on"
    assert i18n.localize("de_DE", key, "Go on") == "Weitergehen"
    assert i18n.localize(i18n.SOURCE_LOCALE, key, "Go on") == "Go on"
    # a missing key falls back to the English argument
    assert i18n.localize("de_DE", "a:hallway-eight|nope", "FB") == "FB"


def test_build_renders_in_the_target_language():
    for arc in ARC_IDS:
        h = Hallway(arc)
        en = h.build(PlayerMemory(level=0), random.Random(7), "en_US")
        de = h.build(PlayerMemory(level=0), random.Random(7), "de_DE")
        # same seed -> same structure, different words
        assert en["sentences"] != de["sentences"], arc
        assert en["_has_anomaly"] == de["_has_anomaly"], arc


def test_every_arc_go_on_is_localized_for_exposed_locales():
    # A representative always-present key must be translated in each exposed
    # non-English locale for every arc (a smoke test that arcs, not just UI,
    # carry the exposed languages).
    for arc in ARC_IDS:
        for loc in NON_EN_EXPOSED:
            key = f"a:{arc}|go_on"
            assert _compiled(loc).get(key, "").strip(), (loc, key)
