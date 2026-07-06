# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""A tiny Flask server for the memory-loop game.

Run:  python app.py   then open  http://127.0.0.1:5000

The game ships several *arcs* (skins/backstories) that share one mechanic.
Game state -- and, crucially, the answer to each loop -- lives on the server.
The browser only ever receives the description, never whether a place is
anomalous, so the page cannot be inspected to cheat.
"""

from __future__ import annotations

import os
import random
import secrets
from typing import Dict

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    session,
)

import i18n
from hallway import (
    Hallway, GOAL, DEFAULT_ARC, DEFAULT_DIFFICULTY, norm_difficulty, list_arcs,
)
from memory import PlayerMemory

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Available arcs, and a cache of one Hallway per arc (each just holds parsed
# JSON, so sharing them across requests is safe).
ARCS = {a["id"]: a for a in list_arcs()}
_HALLWAYS: Dict[str, Hallway] = {}


def get_hallway(arc_id: str) -> Hallway:
    if arc_id not in ARCS:
        arc_id = DEFAULT_ARC
    if arc_id not in _HALLWAYS:
        _HALLWAYS[arc_id] = Hallway(arc_id)
    return _HALLWAYS[arc_id]


# Server-side session store, keyed by a token the client echoes back on every
# request (via the X-Sid header). We do NOT rely on the session cookie: when the
# game is embedded in a cross-site iframe (e.g. Hugging Face Spaces) the cookie
# is dropped, which would otherwise spawn a fresh default-arc slot on every call.
# The cookie is kept only as a same-origin fallback. In-memory is fine for one
# process (the app runs single-worker).
STATE: Dict[str, dict] = {}

# Cap the in-memory store so a stream of unknown/forged sids cannot grow it
# without bound (each slot holds a PlayerMemory + RNG). When full, evict the
# oldest slots (insertion order); a returning player whose slot was evicted just
# gets a fresh one, the same as any first visit. Generous, since one real player
# holds exactly one slot.
MAX_SLOTS = 20000


def _evict_if_full() -> None:
    while len(STATE) >= MAX_SLOTS:
        try:
            oldest = next(iter(STATE))
        except StopIteration:
            break
        STATE.pop(oldest, None)


def _resolve_sid() -> str | None:
    """Find the caller's session id: X-Sid header, then JSON body, then query,
    then the cookie fallback."""
    sid = request.headers.get("X-Sid")
    if not sid:
        body = request.get_json(silent=True) or {}
        sid = body.get("sid")
    if not sid:
        sid = request.args.get("sid")
    if not sid:
        sid = session.get("token")
    # Only a string is a usable key. A malformed body (e.g. {"sid": [1,2]}) must
    # not reach `sid in STATE`, which would raise on an unhashable value.
    return sid if isinstance(sid, str) else None


def _resolve_locale() -> str:
    """Language for this request: X-Lang header, then body, then query."""
    lang = request.headers.get("X-Lang")
    if not lang:
        lang = (request.get_json(silent=True) or {}).get("lang")
    if not lang:
        lang = request.args.get("lang")
    return lang if i18n.is_locale(lang) else i18n.SOURCE_LOCALE


def _resolve_difficulty() -> str:
    """Difficulty for this request: X-Diff header, then body, then query. The
    client owns unlock/selection; the server just honours what it is told (like
    the locale), and clamps anything unknown to normal."""
    d = request.headers.get("X-Diff")
    if not d:
        d = (request.get_json(silent=True) or {}).get("difficulty")
    if not d:
        d = request.args.get("difficulty")
    return norm_difficulty(d)


def _slot() -> dict:
    """Return the caller's server-side state, creating it if the sid is unknown."""
    sid = _resolve_sid()
    if not sid or sid not in STATE:
        _evict_if_full()
        sid = secrets.token_hex(16)
        STATE[sid] = _fresh(DEFAULT_ARC)
    session["token"] = sid          # same-origin fallback
    STATE[sid]["sid"] = sid
    # keep the slot's locale + difficulty current with what the client last asked
    STATE[sid]["locale"] = _resolve_locale()
    STATE[sid]["difficulty"] = _resolve_difficulty()
    return STATE[sid]


def _fresh(arc_id: str) -> dict:
    return {
        "mem": PlayerMemory(),
        "room": None,
        "rng": random.Random(secrets.randbits(64)),
        "arc": arc_id if arc_id in ARCS else DEFAULT_ARC,
        "sid": None,
        "locale": i18n.SOURCE_LOCALE,
        "difficulty": DEFAULT_DIFFICULTY,
    }


def _hall(slot: dict) -> Hallway:
    return get_hallway(slot["arc"])


def _next_room(slot: dict) -> dict:
    mem: PlayerMemory = slot["mem"]
    mem.loops += 1
    room = _hall(slot).build(mem, slot["rng"], slot.get("locale"),
                             slot.get("difficulty", DEFAULT_DIFFICULTY))
    slot["room"] = room
    return room


def _payload(slot: dict, room: dict, extra: dict | None = None) -> dict:
    mem: PlayerMemory = slot["mem"]
    hall = _hall(slot)
    locale = slot.get("locale")
    data = {
        "sid": slot.get("sid"),
        "locale": locale,
        "room": hall.public(room),
        "meta": hall.meta_for(locale),
        "level": mem.level,
        "goal": GOAL,
        "best": mem.best_level,
        "loops": mem.loops,
    }
    if extra:
        data.update(extra)
    return jsonify(data)


def _localized_arcs(locale: str) -> list:
    """The arc list with card title/tagline localized for the picker."""
    out = []
    for a in ARCS.values():
        hall = get_hallway(a["id"])
        flashbacks = hall.act2.get("flashbacks", [])
        # The flashback fragments, localized to the *current* locale, so the
        # Recollections ledger recalls them in the session language, not the
        # language they happened to be collected in.
        flash_texts = [hall._loc(locale, f"act2|flashback|{i}", t)
                       for i, t in enumerate(flashbacks)]
        out.append({
            "id": a["id"],
            "skin": a["skin"],
            "title": i18n.localize(locale, f"a:{a['id']}|title_main", a["title"]),
            "tagline": i18n.localize(locale, f"a:{a['id']}|tagline", a["tagline"]),
            "flashbacks": len(flashbacks),
            "flash_texts": flash_texts,
        })
    return out


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/langs", methods=["GET"])
def api_langs():
    return jsonify({"langs": i18n.available_locales(),
                    "default": i18n.SOURCE_LOCALE,
                    "unlock": i18n.unlock_map()})


@app.route("/api/arcs", methods=["GET"])
def api_arcs():
    return jsonify({
        "arcs": _localized_arcs(_resolve_locale()),
        "default": DEFAULT_ARC,
    })


@app.route("/api/new", methods=["POST"])
def api_new():
    body = request.get_json(silent=True) or {}
    arc_id = body.get("arc", DEFAULT_ARC)
    if arc_id not in ARCS:
        arc_id = DEFAULT_ARC

    # Reuse the caller's sid if it has one (starting a new arc), else mint one.
    sid = _resolve_sid() or secrets.token_hex(16)
    if sid not in STATE:
        _evict_if_full()
    session["token"] = sid
    STATE[sid] = _fresh(arc_id)
    STATE[sid]["sid"] = sid
    STATE[sid]["locale"] = _resolve_locale()
    # Resolve difficulty here too: the opening room is built at level 0, which is
    # exactly where the per-climb aggro-hold is decided, so a Hard/Easy player's
    # first climb must be built under their chosen difficulty, not the default.
    STATE[sid]["difficulty"] = _resolve_difficulty()
    slot = STATE[sid]

    room = _next_room(slot)
    return _payload(slot, room, {
        "intro": _hall(slot).intro(slot["locale"]),
        "cutscene": _hall(slot).cutscene(slot["locale"]),
    })


@app.route("/api/room", methods=["GET"])
def api_room():
    slot = _slot()
    room = slot["room"] or _next_room(slot)
    return _payload(slot, room)


@app.route("/api/inspect", methods=["POST"])
def api_inspect():
    """The player lingers on one detail. The place may notice."""
    slot = _slot()
    mem: PlayerMemory = slot["mem"]
    prop = (request.get_json(silent=True) or {}).get("prop", "")
    line = None
    if prop:
        mem.record_inspect(prop)
        # Occasionally, staring too long earns an unsettling aside.
        if slot["rng"].random() < 0.35:
            line = _hall(slot).long_look(slot.get("locale"), slot["rng"])
    return jsonify({"line": line})


@app.route("/api/interact", methods=["POST"])
def api_interact():
    """Act 2: the player touches a detail (optional). This never decides the
    forward/back call. Most touches are pure flavour; rarely a touch folds the
    run to level 0, and the gated false exit ends it in an alternate ending.
    The answer (`_has_anomaly`) is never read or returned."""
    slot = _slot()
    mem: PlayerMemory = slot["mem"]
    body = request.get_json(silent=True) or {}
    hall = _hall(slot)
    locale = slot.get("locale")

    # The rare false way out: ends the run in a wrong ending, never a win.
    if body.get("action") == "exit":
        ending = hall.take_exit(locale)
        best = mem.best_level
        slot["mem"] = PlayerMemory(best_level=best)   # fresh run, keep record
        room = _next_room(slot)
        return _payload(slot, room, {"kind": "exit", "ending": ending})

    prop = body.get("prop", "")
    # Coach: engaging the passenger yourself also builds toward its fixed
    # utterance and the false way out (the trail is a two-way acquaintance).
    if prop and prop == hall.npc_prop:
        mem.seen_by_npc += 1
    res = hall.interact(prop, mem, slot["rng"], locale, GOAL)
    if not res:
        return jsonify({"sid": slot.get("sid"), "kind": "none"})

    if res["kind"] == "fold":
        mem.level = 0
        mem.attempts += 1                              # curiosity restarted the run
        room = _next_room(slot)
        return _payload(slot, room, {"kind": "fold", "line": res["line"]})

    # flashback / neutral reaction / red herring: flavour only, no state change.
    return jsonify({"sid": slot.get("sid"), "kind": res["kind"],
                    "line": res["line"], "idx": res.get("idx"), "prop": prop,
                    "level": mem.level, "goal": GOAL})


@app.route("/api/act", methods=["POST"])
def api_act():
    """The player commits: 'continue' goes on, 'back' turns around."""
    slot = _slot()
    mem: PlayerMemory = slot["mem"]
    room = slot["room"]
    if room is None:
        room = _next_room(slot)

    body = request.get_json(silent=True) or {}
    choice = body.get("choice")
    confidence = body.get("confidence")
    mem.record_confidence(confidence)

    has_anomaly = room["_has_anomaly"]
    # Correct play: turn back on a changed place, go on when nothing changed.
    correct = (choice == "back") == has_anomaly

    if choice == "back":
        mem.turn_backs += 1
    else:
        mem.continues += 1

    won = False
    if correct:
        mem.level += 1
        mem.best_level = max(mem.best_level, mem.level)
        if mem.level >= GOAL:
            won = True
    else:
        if not has_anomaly and choice == "back":
            mem.false_reports += 1
        elif has_anomaly and choice == "continue":
            mem.missed += 1
        mem.level = 0
        mem.attempts += 1   # the place sent you back to the start: a new run

    result = {
        "correct": correct,
        "had_anomaly": has_anomaly,
        "won": won,
        "confidence": confidence,
    }
    # Post-decision only (safe to reveal now): which detail was the anomaly, so
    # the client can note a loop-aware NPC acknowledgement in its collection.
    if has_anomaly:
        result["anomaly"] = {"prop": room.get("_anomaly_prop"),
                             "val": room.get("_anomaly_val")}
    # Hard mode's double change: on a CORRECT turn-back where two details had
    # moved, hand back both props so the client can flare those two lines. This
    # is the "keep scanning" lesson, delivered after the call is already made
    # (so it never helps the decision), and only when two really did change.
    props = room.get("_anomaly_props", [])
    if correct and choice == "back" and len(props) >= 2:
        result["flare_props"] = list(props)

    if won:
        result["win_text"] = _hall(slot).win(slot.get("locale"))
        result["attempts"] = mem.attempts
        # A quiet, in-world "solved in N runs" line, localized like the rest.
        result["attempt_text"] = _hall(slot).attempt_line(
            slot.get("locale"), mem.attempts)
        result["stats"] = mem.to_dict()
        # Reset progress so a fresh run starts clean, but keep the record.
        best = mem.best_level
        slot["mem"] = PlayerMemory(best_level=best)
        room = _next_room(slot)
        return _payload(slot, room, result)

    room = _next_room(slot)
    return _payload(slot, room, result)


if __name__ == "__main__":
    # HOST/PORT are env-driven so the same file runs locally (127.0.0.1:5000)
    # and on a host like Hugging Face Spaces (0.0.0.0:7860).
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
