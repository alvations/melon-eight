# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Localization core: the string-key scheme, the locale registry, and the
compiled-catalog loader shared by the runtime (hallway.py, app.py) and the
tooling (scripts/i18n_*.py).

Design
------
Every translatable string in an arc has a deterministic key derived from its
position in the arc JSON (see ``arc_items``). The English text in the arc files
is the source of truth. Translations live in an audit file
(``data/i18n/lines.json``, keyed by string-key, holding every locale with its
text/score/postedit/postedit_score) and are *compiled* down to a flat runtime
catalog per locale (``data/i18n/compiled/<locale>.json`` = {key: final_text}).

At runtime, hallway.py rebuilds the same key for each line it picks and looks up
the localized text, falling back to the English original when a key is missing.
So partial translations degrade gracefully to English, string by string.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Iterator, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
I18N_DIR = os.path.join(HERE, "data", "i18n")
COMPILED_DIR = os.path.join(I18N_DIR, "compiled")

SOURCE_LOCALE = "en_US"

# Supported locales: code -> display metadata. `native` is what the picker shows.
# All of these are left-to-right.
LOCALES: List[dict] = [
    {"code": "en_US", "name": "English", "native": "English"},
    {"code": "en_GB", "name": "English (UK)", "native": "English (UK)"},
    {"code": "de_DE", "name": "German", "native": "Deutsch"},
    {"code": "es_ES", "name": "Spanish", "native": "Español"},
    {"code": "fr_FR", "name": "French", "native": "Français"},
    {"code": "fr_CA", "name": "French (Canada)", "native": "Français (Canada)"},
    {"code": "it_IT", "name": "Italian", "native": "Italiano"},
    {"code": "pt_PT", "name": "Portuguese", "native": "Português"},
    {"code": "nl_NL", "name": "Dutch", "native": "Nederlands"},
    {"code": "cs_CZ", "name": "Czech", "native": "Čeština"},
    {"code": "ja_JP", "name": "Japanese", "native": "日本語"},
    {"code": "ko_KR", "name": "Korean", "native": "한국어"},
    {"code": "zh_CN", "name": "Chinese (Simplified)", "native": "简体中文"},
    {"code": "zh_TW", "name": "Chinese (Taiwan)", "native": "繁體中文（台灣）"},
    {"code": "yue_HK", "name": "Cantonese", "native": "廣東話"},
    {"code": "vi_VN", "name": "Vietnamese", "native": "Tiếng Việt"},
    {"code": "th_TH", "name": "Thai", "native": "ไทย"},
    {"code": "id_ID", "name": "Indonesian", "native": "Bahasa Indonesia"},
    {"code": "ms_MY", "name": "Malay", "native": "Bahasa Melayu"},
    {"code": "hi_IN", "name": "Hindi", "native": "हिन्दी"},
    {"code": "ta_IN", "name": "Tamil", "native": "தமிழ்"},
]

LOCALE_CODES = [l["code"] for l in LOCALES]

# Locales exposed in the language picker for this phase. Translations for other
# locales may already be complete and compiled, but they stay hidden until we
# deliberately promote them here. Keep this list authoritative for what ships.
EXPOSED_LOCALES = [
    "en_US", "de_DE", "fr_FR", "pt_PT", "ja_JP", "ko_KR", "zh_CN", "vi_VN",
]


def is_locale(code: str) -> bool:
    return code in LOCALE_CODES


# Short codes for the "I18N-XX" unlock promo -> full locale. Two letters each so
# the code "I18N-XX" stays within the promo box.
PROMO_LOCALE = {
    "EN": "en_US", "GB": "en_GB", "DE": "de_DE", "ES": "es_ES", "FR": "fr_FR",
    "CA": "fr_CA", "IT": "it_IT", "PT": "pt_PT", "NL": "nl_NL", "CS": "cs_CZ",
    "JA": "ja_JP", "KO": "ko_KR", "ZH": "zh_CN", "TW": "zh_TW", "HK": "yue_HK",
    "VI": "vi_VN", "TH": "th_TH", "ID": "id_ID", "MS": "ms_MY", "HI": "hi_IN",
    "TA": "ta_IN",
}


# --- the string-key scheme -------------------------------------------------

def arc_items(arc_id: str, data: dict) -> Iterator[Tuple[str, str]]:
    """Yield (key, english_text) for every translatable string in an arc, in a
    stable order. The same keys are recomputed at runtime and by the tooling."""
    meta = data.get("meta", {})
    yield (f"a:{arc_id}|title_main", meta.get("title", ""))
    yield (f"a:{arc_id}|tagline", meta.get("tagline", ""))
    yield (f"a:{arc_id}|go_on", meta.get("go_on", ""))
    yield (f"a:{arc_id}|turn_back", meta.get("turn_back", ""))
    yield (f"a:{arc_id}|progress", meta.get("progress", ""))
    yield (f"a:{arc_id}|share_prompt", meta.get("share_prompt", ""))
    yield (f"a:{arc_id}|attempt", meta.get("attempt", ""))
    yield (f"a:{arc_id}|attempt_first", meta.get("attempt_first", ""))
    for prop, lab in meta.get("labels", {}).items():
        yield (f"a:{arc_id}|label|{prop}", lab)
    for i, t in enumerate(data.get("title_variants", [])):
        yield (f"a:{arc_id}|title|{i}", t)
    for prop, spec in data.get("properties", {}).items():
        for val, pool in spec.get("values", {}).items():
            for i, t in enumerate(pool):
                yield (f"a:{arc_id}|p:{prop}|v:{val}|{i}", t)
        for val, pool in spec.get("anomalies", {}).items():
            for i, t in enumerate(pool):
                yield (f"a:{arc_id}|p:{prop}|x:{val}|{i}", t)
    for kind, pool in data.get("adaptive", {}).items():
        for i, t in enumerate(pool):
            yield (f"a:{arc_id}|adaptive|{kind}|{i}", t)
    for kind, pool in data.get("framing", {}).items():
        for i, t in enumerate(pool):
            yield (f"a:{arc_id}|framing|{kind}|{i}", t)
    # Act 2: the optional "touch the room" interactions (see docs/ACT2.md).
    act2 = data.get("act2", {})
    for i, t in enumerate(act2.get("flashbacks", [])):
        yield (f"a:{arc_id}|act2|flashback|{i}", t)
    ex = act2.get("exit", {})
    if ex.get("tempt"):
        yield (f"a:{arc_id}|act2|exit|tempt", ex.get("tempt", ""))
    if ex.get("action"):
        yield (f"a:{arc_id}|act2|exit|action", ex.get("action", ""))
    if ex.get("utterance"):
        yield (f"a:{arc_id}|act2|exit|utterance", ex.get("utterance", ""))
    for eid, pool in act2.get("endings", {}).items():
        for i, t in enumerate(pool):
            yield (f"a:{arc_id}|act2|end|{eid}|{i}", t)
    for prop, spec in act2.get("touch", {}).items():
        yield (f"a:{arc_id}|act2|t:{prop}|verb", spec.get("verb", ""))
        for kind in ("reaction", "herring", "fold"):
            for i, t in enumerate(spec.get(kind, [])):
                yield (f"a:{arc_id}|act2|t:{prop}|{kind}|{i}", t)


# UI strings that live outside the arcs (source English). Keys are `ui|<name>`.
UI_STRINGS_EN: Dict[str, str] = {
    "select_lead_1": "Somewhere you can't quite leave.",
    "select_lead_2": "Choose a way through.",
    "begin": "Begin",
    "back": "Back",
    "again": "Walk it again",
    "change": "Change scenario",
    "give_up": "Give up · back to start",
    "conf_q": "How certain are you?",
    "conf_1": "Guessing",
    "conf_2": "I think so",
    "conf_3": "Almost sure",
    "conf_4": "Certain",
    "language": "Language",
    # Heading for the first-reset onboarding panel. A neutral "Instructions"
    # label, so the arc's scene title (e.g. a time-of-day framing) never reads
    # as part of the how-to. The panel body reuses the arc's own backstory.
    "instructions": "Instructions",
    # The fleeting "look back" toggle on the win screen. Metaphoric (reflect on
    # the run just finished), NOT a physical "turn around": translators must use
    # the retrospective sense in each language.
    "look_back": "Look back.",
    # Shown when a touch folds the run back to the start, so the player learns it
    # was their own action, not a glitch. The opt-out appears only from the 2nd
    # time (see game.js maybeFoldExplainer).
    "fold_title": "Back to the start.",
    "fold_1": "That was you. You reached for something in the place, and it folded the way back on you.",
    "fold_2": "Touching what you find is never necessary. Look if you like, but a wrong touch can send you here.",
    "fold_hide": "Don't show this again.",
    # The display / accessibility settings panel (gear). Defaults leave the look
    # exactly as it is; these only change things if the player opts in.
    "settings_title": "Display",
    "set_text": "Text size",
    "set_bright": "Brightness",
    "set_motion": "Reduce motion",
    "set_done": "Done",
    # Achievements / collection page.
    "ach_open": "Achievements",
    "ach_save": "Save",
    "ach_load": "Load",
    # Erase: wipe the local memory back to a blank slate (with a warning gate).
    "erase": "Erase",
    "erase_title": "Erase your memory?",
    "erase_body": "Everything this place remembers of you goes: the fragments you have recollected, the marks you have earned, every run. This cannot be undone.",
    "erase_cancel": "Keep it",
    "ach_locked": "Locked",
    "ach_flash": "Flashbacks",
    "ach_progress": "{n} of {total} unlocked",
    "promo_hint": "Code",
    "promo_go": "Redeem",
    "promo_ok": "Unlocked.",
    "promo_bad": "That code does nothing here.",
    "promo_have": "Already redeemed.",
    # The memory overlay: its header, its empty state, and the fragment section.
    "mem_title": "Memory",
    "ach_empty": "Nothing yet. Escape a place to begin.",
    "ach_section": "Achievements",
    "col_section": "Recollections",
    # Recalling a collected fragment from the ledger.
    "col_recall": "Recall this fragment",
    "col_recall_empty": "A fragment you have seen, its words already fading.",
    # Re-view the ending credits from the Memory overlay.
    "view_credits": "View credits",
    # Win-screen button that plays the ending credits (first escape of an arc).
    "end_credits": "End Credits",
    # Win-screen adaptive nudge toward what is left to find ({n} = unseen count).
    "nudge_frags": "There are {n} memories here you have not seen yet.",
    "nudge_arcs": "Two other places are also called 8.",
    "nudge_eight": "Eight escapes from one place is a different kind of remembering.",
    # Records: a quiet ledger of *how* runs were won (self-competition, unscored).
    "rec_section": "Records",
    "rec_steady": "Escaped without a single guess.",
    "rec_cold": "Escaped without a second look.",
    "rec_nerve": "Turned back at the final door, and was right.",
    "rec_streak": "Clean escapes in a row: {n}",
    # The fleeting "how you did" line on the win screen.
    "read_steady": "You never once called it a guess.",
    "read_cold": "You walked it without a second look.",
    "read_nerve": "You turned back at the very last door, and you were right.",
    # Difficulty + reading-register settings (Display panel).
    "set_diff": "Difficulty",
    "set_age": "Reading",
    "diff_easy": "Easy",
    "diff_normal": "Normal",
    "diff_hard": "Hard",
    "diff_insane": "Insane",
    "diff_hint_hard": "Hard adds new kinds of change.",
    "diff_hint_locked": "Escape once to unlock Hard.",
    "diff_hint_insane": "Insane remakes what normal is, every run.",
    "age_simple": "Simple",
    "age_normal": "Normal",
    # The HUD "furthest reached" marker ({n} = best level).
    "furthest": "furthest {n}",
    # Shown when the player admits doubt and is sent back for one more look.
    "hesitate_1": "You hesitate. Look again.",
    "hesitate_2": "You're not sure. You take another look.",
    "hesitate_3": "Doubt stops you. Read it once more.",
    "hesitate_4": "You hold back, and let your eyes travel over it again.",
    # The alternate-ending screen's return button.
    "ending_back": "Back to the start",
    # Accessibility labels for icon-only controls (screen readers).
    "a11y_settings": "Display settings",
    "a11y_close": "Close",
    "a11y_sound_on": "Sound on",
    "a11y_sound_off": "Sound off",
    # Simple (younger-reader) register: a plain, spoiler-free statement of the
    # rule, shown in the onboarding when Reading is set to Simple. Its QE has an
    # extra "explain like I am young" simplicity gate (see docs/LOCALIZATION.md).
    "rules_plain": "Something changed? Go back. Nothing changed? Go on. Eight in a row to get out.",
    # Badge names (ach_n_*) and one-line descriptions (ach_d_*), discovered by
    # playing; no spoilers of the specific detail to watch.
    "ach_n_out_hallway-eight": "Out of Hallway 8",
    "ach_d_out_hallway-eight": "Escape the corridor.",
    "ach_n_out_stairway8": "Out of Stairway 8",
    "ach_d_out_stairway8": "Reach the ground floor.",
    "ach_n_out_coach8": "Out of Coach 8",
    "ach_d_out_coach8": "Step off the train.",
    "ach_n_out_all": "All the way out",
    "ach_d_out_all": "Escape all three places.",
    "ach_n_flawless": "Flawless",
    "ach_d_flawless": "Escape a place without a single reset.",
    "ach_n_eight_times": "Eight times through",
    "ach_d_eight_times": "Escape one place eight times.",
    "ach_n_end_hallway-eight": "The lobby that won't open",
    "ach_d_end_hallway-eight": "Find Hallway 8's other ending.",
    "ach_n_end_stairway8": "The stairs that only climb",
    "ach_d_end_stairway8": "Find Stairway 8's other ending.",
    "ach_n_end_coach8": "The platform that isn't yours",
    "ach_d_end_coach8": "Find Coach 8's other ending.",
    "ach_n_npc_knows": "It knows you",
    "ach_d_npc_knows": "Be acknowledged by the one who is always ahead.",
    "ach_n_shared": "Passed it on",
    "ach_d_shared": "Send the place to someone else.",
    "ach_n_opening_night": "Opening night",
    "ach_d_opening_night": "Play on the day it opened.",
    "ach_n_flash_hallway-eight": "Hallway, remembered",
    "ach_d_flash_hallway-eight": "See every fragment in Hallway 8.",
    "ach_n_flash_stairway8": "Stairway, remembered",
    "ach_d_flash_stairway8": "See every fragment in Stairway 8.",
    "ach_n_flash_coach8": "Coach, remembered",
    "ach_d_flash_coach8": "See every fragment in Coach 8.",
    "ach_n_total_recall": "Total recall",
    "ach_d_total_recall": "See every last fragment, everywhere.",
    "ach_n_steady": "Steady",
    "ach_d_steady": "Escape without a single guess.",
    "ach_n_cold": "Cold read",
    "ach_d_cold": "Escape without a second look.",
    "ach_n_nerve": "Nerve",
    "ach_d_nerve": "Turn back at the final door, and be right.",
    "ach_n_streak": "On a roll",
    "ach_d_streak": "Three clean escapes in a row.",
    "ach_n_hard_hallway-eight": "Hallway, harder",
    "ach_d_hard_hallway-eight": "Escape Hallway 8 on hard.",
    "ach_n_hard_stairway8": "Stairway, harder",
    "ach_d_hard_stairway8": "Escape Stairway 8 on hard.",
    "ach_n_hard_coach8": "Coach, harder",
    "ach_d_hard_coach8": "Escape Coach 8 on hard.",
    "ach_n_hard_all": "Nowhere left soft",
    "ach_d_hard_all": "Escape all three on hard.",
    "ach_n_insane_hallway-eight": "Hallway, unmade",
    "ach_d_insane_hallway-eight": "Escape Hallway 8 on insane.",
    "ach_n_insane_stairway8": "Stairway, unmade",
    "ach_d_insane_stairway8": "Escape Stairway 8 on insane.",
    "ach_n_insane_coach8": "Coach, unmade",
    "ach_d_insane_coach8": "Escape Coach 8 on insane.",
    "ach_n_insane_all": "Trust nothing",
    "ach_d_insane_all": "Escape all three on insane.",
    "ach_n_melon": "Melon Supporter",
    "ach_d_melon": "Thank you for keeping the lights on. From all of us at Melon Labs.",
    # Win-screen sharing. One of share_1..8 is chosen at random when the player
    # gets out, in the "invitation" voice: cryptic, elegant, a challenge held
    # out to a friend. The play link is appended by the client. (The prompt line
    # above them is a per-arc string, keyed a:<arc>|share_prompt, not here.)
    "share_native": "Share",
    "share_copy": "Copy link",
    "share_copied": "Link copied",
    "share_1": "There is a place you can't quite leave. I left. Now it's your turn.",
    "share_2": "Somewhere you can't quite leave, someone found the door. Come find yours.",
    "share_3": "Eight chances to doubt yourself. I trusted the right ones. Now you.",
    "share_4": "I know the way out now. I won't tell you where. Come and see.",
    "share_5": "A quiet place, eight small doubts, one way through. I found it. Can you?",
    "share_6": "I walked it eight times and trusted what I remembered. See if you can.",
    "share_7": "The way out comes down to what you remember. I remembered. Now you try.",
    "share_8": "Eight doors stood between me and the cold air. I opened every one. Your turn.",
}


def ui_items() -> Iterator[Tuple[str, str]]:
    for name, text in UI_STRINGS_EN.items():
        yield (f"ui|{name}", text)


# --- compiled catalog loader (runtime) -------------------------------------

_CACHE: Dict[str, Dict[str, str]] = {}


def load_compiled(locale: str) -> Dict[str, str]:
    """Load (and cache) the compiled {key: text} catalog for a locale.
    Missing files yield an empty catalog, so everything falls back to English."""
    if locale in _CACHE:
        return _CACHE[locale]
    path = os.path.join(COMPILED_DIR, f"{locale}.json")
    data: Dict[str, str] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    _CACHE[locale] = data
    return data


def clear_cache() -> None:
    _CACHE.clear()


def available_locales() -> List[dict]:
    """Locales shown in the picker: the explicit EXPOSED_LOCALES allowlist,
    intersected with locales that actually have a compiled catalog (or are the
    source). This keeps the picker to the phase's chosen set even when other
    locales are fully translated and compiled on disk."""
    return [l for l in LOCALES if l["code"] in EXPOSED_LOCALES
            and (l["code"] == SOURCE_LOCALE or load_compiled(l["code"]))]


def unlock_map() -> Dict[str, dict]:
    """SHORT code -> {code, native} for the I18N-XX unlock promo, limited to
    locales that actually have a compiled catalog (or the source)."""
    by_code = {l["code"]: l for l in LOCALES}
    out: Dict[str, dict] = {}
    for short, code in PROMO_LOCALE.items():
        l = by_code.get(code)
        if l and (code == SOURCE_LOCALE or load_compiled(code)):
            out[short] = {"code": code, "native": l["native"]}
    return out


def localize(locale: str, key: str, fallback: str) -> str:
    """Return the localized string for a key, or the English fallback."""
    if not locale or locale == SOURCE_LOCALE:
        return fallback
    return load_compiled(locale).get(key) or fallback
