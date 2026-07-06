<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Testing: how this game is verified, and how to reproduce it

Two layers, one command each. The first proves the **server's math and payloads**
without a browser. The second drives the **real client** in headless Chromium to
prove the rendering, which unit tests cannot reach. Both are designed to run
anywhere: the browser layer skips cleanly when Chromium is absent, so the fast
suite and browserless CI stay green.

```bash
python tests/test_game.py            # fast: server + i18n unit/regression tests
H8_EMU=1 python tests/test_game.py   # also runs the headless-browser emulation checks
```

## The zero-dependency runner

`tests/test_game.py` is both a test module and the runner. Run directly it
**auto-discovers every `tests/test_*.py`**, collects each module's top-level
`test_*` **functions**, calls them, and reports `PASS`/`FAIL` (a function that
does not raise passed). No pytest required (though `pytest tests/` also works).
Consequences worth knowing:

- Tests are plain functions, not `unittest.TestCase` methods (methods are not
  discovered). Assert with bare `assert`.
- A test that wants to **skip** just prints a note and returns (it counts as a
  pass). This is how the browser layer degrades gracefully.

## Layer 1: server tests (`tests/test_game.py`, `test_i18n.py`, `test_audio.py`)

These exercise `app.py` / `hallway.py` / `anomalies.py` / `memory.py` in-process
via Flask's `test_client()`, and read the server's hidden answer to play
optimally (`A.STATE[sid]["room"]["_has_anomaly"]`). They guard the invariants
that must never regress:

- **The core loop is honest.** A perfect player wins in exactly `GOAL` correct
  calls; a fresh, cookie-less client keeps its arc (the `sid`-header regression).
- **The answer never leaks.** Every payload is stripped of `_`-prefixed keys
  (`test_compiled_catalogs_carry_no_answer_keys`, and the `public()` check).
- **Fairness.** The mutated property is always among the shown details; the
  aggro-item is held out then revealed and can never be the change on the loop it
  first appears (`test_aggro_item_is_held_then_revealed_fairly`, 300 seeds/arc).
- **Difficulty ramp** is monotonic and bounded, and level 0 leans clean
  (`test_difficulty_ramp`).
- **Flare gate.** `flare_props` appears only on a correct turn-back where two
  details changed, never otherwise (`test_flare_props_only_on_correct_double_turn_back`).
- **Act 2** touches are flavour-only and leak-proof; every exit points at a real
  ending.
- **i18n** completeness/exposure gates (see `docs/LOCALIZATION.md` for the full
  pipeline): every UI string compiled for every exposed locale, exactly the
  chosen locales exposed, no answer keys in catalogs, no em-dashes.

Add a server test by writing a `test_*` function in the relevant file. To drive
a specific decision branch, start a slot with `_new(c, arc)` and overwrite
`A.STATE[sid]["room"]` with the fields you want (this is how the flare test forces
each branch deterministically).

## Layer 2: browser emulation (`tests/emulation.cjs` + `tests/test_emulation.py`)

`tests/test_emulation.py` boots the app on a free port and runs
`tests/emulation.cjs` (Playwright) against it, asserting the client rendering
that only a browser exercises:

- reduced-motion prose renders in canonical order and is fully visible at settle;
- Act 2 touch verbs render **and stay visible** under reduced motion;
- the flavour line appears on a touch, then **auto-fades** after a readable dwell,
  and keeps a real opacity fade even under reduced motion;
- the alternate-ending achievement (`end_<arc>`) never unlocks through ordinary
  play, and its predicate reflects `mem.ends` exactly.

**Opt-in and self-skipping.** It runs only when `H8_EMU=1` and Node + Playwright +
Chromium are present; otherwise `test_emulation` prints a skip and returns.
Overridable env: `H8_CHROMIUM` (browser path), `NODE_PATH` (where `playwright`
resolves), `H8_EMU` (enable).

How the harness reaches the client: `static/game.js` is a **classic script**, so
its top-level `let`/`function` bindings (`current`, `mem`, `computeAch`, ...) are
addressable by bare name inside `page.evaluate`. That lets a check read
`current.room.shown`, mutate `mem`, or call `computeAch()` directly. To make a
probabilistic feature deterministic, override `Math.random` before load with
`addInitScript(() => { Math.random = () => 0; })` so, e.g., every touch roll
fires. Seed `localStorage.h8_mem` with `arcStarted` for each arc to skip the
first-run Act 2 suppression, and set `h8_motion` for reduced motion. Add a check
by pushing to `results` via the `check(name, ok, detail)` helper.

## Diagnostic workflow: disprove or confirm a perceived rendering bug

The most useful lesson of this project's QA. When a UI bug is reported ("the
verbs never show under reduced motion"), do **not** patch on suspicion. Build a
**deterministic emulation harness** that isolates the variable:

1. **Force the probabilistic thing on** (`Math.random = () => 0`) so a feature
   that normally appears 15-45% of the time appears every eligible loop. Now
   absence is signal, not noise.
2. **Measure at settle, never during a transition.** Wait for
   `#controls:not(.hidden)` and a short beat; a sample taken right after a commit
   catches the *previous* loop mid-swap and lies (elements read as `0x0` because
   an ancestor is briefly `display:none`).
3. **When a box is `0x0`, walk the ancestor chain** and print each parent's
   `display`/`getBoundingClientRect`; a zero-size box almost always means a
   hidden ancestor, not a hidden element.
4. **Emulate the real trigger both ways.** Reduced motion via the in-app toggle
   (`localStorage.h8_motion`) *and* via the OS (`newContext({ reducedMotion:
   'reduce' })`) can differ.
5. **Compare deterministically.** With randomness pinned, any difference between
   two conditions is caused by the variable under test, not variance.

In this repo that method **disproved** the reported "verbs vanish under reduced
motion" (they render 18/18 and stay visible) and pointed at the real defect: the
flavour *line* was not fading. Turning a hunch into a measurement saved a wrong
fix and produced the regression test that now guards it.

## Browser-test gotchas (baked into the harness)

- Advance the intro with the `#begin` button, not the Enter key; dismiss any
  cutscene/onboarding overlay before the loop.
- With `Math.random = 0` the doubt prompt always fires; handle it (click
  `[data-conf="4"]`) or commits silently stall.
- After a commit there is a ~1.5s pause (flare + dwell) before the next render;
  wait it out before sampling.
- Serve test instances on **8070+**; Chromium refuses "unsafe" ports (5060, 6000).
- Chromium lives at `/opt/pw-browsers/chromium-*/chrome-linux/chrome`; launch with
  `--autoplay-policy=no-user-gesture-required` so audio-gated paths run.
