# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Every arc must have its own background ambience, wired to its skin.

The soundscape is generated live in the browser (static/audio.js): `play(skin)`
routes each arc's skin to a `_<skin>(bus)` builder. These tests guard the wiring
so a new arc cannot silently ship with no BGM (or fall through to the hallway
default). They are static checks (no browser needed), which is what the plain
runner supports; the audible signal per arc is verified separately in a browser.
"""

import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCS_DIR = os.path.join(ROOT, "data", "arcs")
AUDIO_JS = os.path.join(ROOT, "static", "audio.js")


def _arc_skins():
    skins = {}
    for path in sorted(glob.glob(os.path.join(ARCS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("meta", {})
        skins[meta.get("id", os.path.basename(path))] = meta.get("skin")
    return skins


def _audio_js():
    with open(AUDIO_JS, encoding="utf-8") as f:
        return f.read()


def _play_body(js):
    m = re.search(r"\bplay\s*\(\s*skin\s*\)\s*\{", js)
    assert m, "audio.js has no play(skin) method"
    return js[m.start():m.start() + 1200]


def test_every_arc_declares_a_skin():
    for arc, skin in _arc_skins().items():
        assert skin, f"arc {arc} has no meta.skin (needed for audio)"


def test_every_arc_skin_has_its_own_builder():
    # A `_<skin>(bus)` builder must exist for each arc's skin, so no arc is left
    # without its own ambience.
    js = _audio_js()
    for arc, skin in _arc_skins().items():
        assert f"_{skin}(bus)" in js, \
            f"audio.js is missing a _{skin}(bus) builder for arc {arc}"


def test_play_routes_every_skin_to_its_builder():
    # play() must actually invoke each arc's builder (explicitly for non-default
    # skins, or via the hallway default), so every arc's BGM is reachable.
    js = _audio_js()
    play = _play_body(js)
    for arc, skin in _arc_skins().items():
        assert f"this._{skin}(bus)" in play, \
            f"play(skin) never calls this._{skin}(bus) for arc {arc}"
        if skin != "hallway":   # hallway is the else-default branch
            assert f'skin === "{skin}"' in play, \
                f"play(skin) has no explicit branch for skin {skin!r}"


def test_landing_theme_is_wired():
    # The select screen's own theme must exist and be routed too.
    js = _audio_js()
    assert "_landing(bus)" in js, "audio.js is missing the landing theme"
    assert "this._landing(bus)" in _play_body(js), "play(skin) never starts the landing theme"


def test_context_unlock_method_exists():
    # Mobile / the Spaces iframe need a synchronous resume() from a gesture.
    js = _audio_js()
    assert re.search(r"\bunlock\s*\(\s*\)\s*\{", js), \
        "audio.js is missing unlock() (needed to start audio on mobile / in the iframe)"


def test_arcs_are_level_matched_to_landing():
    # play(skin) carries a per-arc bus calibration so every arc sits at the
    # landing theme's loudness (see the RMS-derived BUS map).
    play = _play_body(_audio_js())
    assert ("BUS" in play or "busLevel" in play), \
        "play(skin) has no per-arc level calibration (BGM would not be level-matched)"


def test_rare_events_fire_about_every_30s():
    # Every rare ambience event (flicker, lurch, passing train, wind) should be
    # scheduled to land roughly once every 30s, so a normal climb actually meets
    # it. A window centred well past ~45s would fire too rarely to be heard.
    js = _audio_js()
    windows = re.findall(r"_every\(\s*(\d+)\s*,\s*(\d+)", js)
    assert windows, "no _every(...) rare-event windows found in audio.js"
    for lo, hi in windows:
        lo, hi = int(lo), int(hi)
        mid = (lo + hi) / 2
        assert mid <= 45000, \
            f"_every({lo},{hi}) fires too rarely (midpoint {mid:.0f}ms); want ~30s"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS  {name}")
