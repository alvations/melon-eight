<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Reproduce everything: run, test, measure, review, and build with any agent

This is the operational companion to [`MAKING_OF.md`](MAKING_OF.md). MAKING_OF is
the *method* (how the game was designed with an AI coding agent); this file is the
concrete *how-to* so anyone (a person, or another coding agent reading the repo)
can pick it up and re-create the whole thing, including with a **local or
non-Anthropic model** driving Claude Code instead of Anthropic's hosted Claude.

Everything below is in the repo. Nothing here needs a paid service to run the game
or its tests; the only network-dependent step is deploying to Hugging Face.

## 1. Run it

```bash
pip install -r requirements.txt
python app.py                      # http://127.0.0.1:5000
```

Env knobs: `HOST`, `PORT`, `SECRET_KEY`. A non-canonical **shortcut** build for
fast testing reaches the end in fewer loops: `H8_GOAL=3 python app.py` (clamped
1..8; canonical is always 8).

## 2. Test it

```bash
python tests/test_game.py          # whole tests/ suite, no pytest needed
H8_EMU=1 python tests/test_game.py # also runs the headless-browser emulation
```

- **Unit + API tests** (`tests/test_*.py`): game logic, the no-cookie iframe
  regression, the difficulty ramp, aggro-item fairness, i18n coverage and the new
  UI-string regressions, server robustness (difficulty on a fresh run, malformed
  input, the session-store cap), and the audio wiring/level-match guards.
- **Browser emulation** (`tests/emulation.cjs`, driven by `tests/test_emulation.py`):
  client rendering that unit tests cannot reach: reduced-motion prose order and
  visibility, Act 2 verbs + the auto-fading flavour line, the credits roll and the
  after-credits return, the erase flow (including forgetting onboarding), the Act 2
  onset, every arc being playable, the audio graph building + `unlock()`, and the
  network-failure mid-commit recovery. Off by default (opt in with `H8_EMU=1`),
  and it skips cleanly when Node/Playwright/Chromium are absent.

Full testing story and the deterministic-harness method: [`TESTING.md`](TESTING.md).

## 3. The browser tool-chain (emulation, audio, screenshots, video)

The tests and the measurement/capture tools drive a headless browser. Install the
open-source tool-chain once; it is declared in `package.json` and resolved
portably (see `scripts/browser.cjs`), so a plain checkout works with no
sandbox-specific paths:

```bash
npm install                      # installs Playwright (dev dependency only)
npx playwright install chromium  # the headless browser
# optional, for converting captured media: any ffmpeg build
```

The game itself needs none of this (no build step, no Node). This is only for the
reproducible test/measurement/capture tools:

| Command | What it does |
|---------|--------------|
| `npm run emu` (or `H8_EMU=1 python tests/test_game.py`) | the browser emulation tests |
| `npm run measure-audio` | RMS/peak/centroid, to keep arcs level-matched to landing |
| `npm run measure-sfx-vs-bgm` | peak/RMS/crest of the action SFX vs the beds (why footsteps sit above the BGM) |
| `npm run render-audio -- coach 30` | capture an arc's BGM (or `sfx`) to a WebM |
| `npm run shots -- <url>` | screenshots of every screen, desktop + mobile |
| `npm run video -- <url> credits <arc>` | record a scene (loop/act2/win/credits) |
| `npm run probe-render -- <url> <arc>` | verify the sense line reveals last |

## 4. Measure / render the audio

The soundscape is synthesised live (no audio files). `static/audio.js` is the
generator; `scripts/measure_audio.cjs` keeps the arcs level-matched to the landing
theme, and `scripts/render_audio.cjs` exports any bed or the SFX to a file to
actually hear it. Full pipeline (synth, BGM/SFX, calibration, mobile autoplay,
adding an arc): [`AUDIO.md`](AUDIO.md).

**A lesson worth keeping (SFX vs BGM):** the action SFX (footsteps) are
deliberately louder than the room tone and must stay that way. BGM is steady-state
ambience; an action sound is a transient event, and the ear registers events by
their PEAK, not their average energy. `scripts/measure_sfx_vs_bgm.cjs` shows the
numbers: the footstep's RMS is about the same as a bed's, but its peak is ~2-4x
higher (crest ~11 vs a bed's ~3). Level-match the beds to each other (steady vs
steady, by RMS, the BUS map); do NOT fold the SFX into that match, or you trim away
the crest that makes an action feel tactile. Judge SFX by ear and player testing,
not by matching a number to the bed. The full reasoning is in the header of that
script and in [`AUDIO.md`](AUDIO.md).

## 4b. Jump to any scene fast

The env flags (`H8_GOAL`, `H8_ACT2_TEST`) and the client hooks that let a test
reach Act 1, Act 2, or the win/credits scene directly, plus which tool captures
each, are in [`TESTING_SHORTCUTS.md`](TESTING_SHORTCUTS.md).

## 4. Localize

The whole model-translated + self-scored pipeline (extract, ingest, compile,
level-QE to the >=95 gate) is reproducible from `scripts/i18n_*.py` and documented
in [`LOCALIZATION.md`](LOCALIZATION.md). English is the source of truth; every
other language degrades gracefully to English key by key.

## 5. Review it (the persona panel)

Reviews live in [`reviews/`](reviews/). They are produced by running a small panel
of **reviewer personas**, each a fresh agent with a fixed brief. This is
reproducible with any capable agent; the recipe:

- **Harsh-impartial critic** (`REVIEW*.md`): *keeps* memory of prior reviews and
  *reads the code and tests*. Numbered passes, a verdict out of 10, unsparing but
  fair, quotes file:line.
- **Mechanics reviewer** (`REVIEW_GAMEPLAY*.md`): memory wiped, reviews as a
  *player*, does **not** read source. Cares only whether the eight-times binary
  call is honest, interesting, and fair.
- **Craft / atmosphere reviewer** (`REVIEW_AESTHETIC*.md`): memory wiped, as a
  player. Judges mood, writing, typography, pacing, sound, restraint.
- **Cold reviewer** (`REVIEW_COLD*.md`): memory wiped, a stranger sent a link
  with no explanation. Narrates the first-time experience and where a newcomer
  bounces.

Run them in parallel; have each write to its numbered file in `reviews/`. The
memory-wiped reviewers must not read prior reviews (so first impressions stay
honest); only the harsh critic carries continuity and reads code. To experience
the game without reading source, a player-reviewer boots `H8_GOAL=3 python app.py`
and drives it with headless Chromium (see `tests/emulation.cjs` for the launch
recipe) or reads the player-facing content in `data/arcs/*.json`.

## 6. Deploy (local only)

Deploying to the Hugging Face Space needs normal internet (the sandboxed web
session's network policy blocks `huggingface.co`). From a machine with a write
token:

```bash
export HF_TOKEN=hf_...              # or `hf auth login`
python scripts/deploy_hf.py         # create/update the Space, upload
python scripts/make_private_hf.py   # private (default); --public to release
```

## 7. Build it with any agent (local or non-Anthropic model)

The whole game was built by talking to **Claude Code** in plain language, one
change at a time, letting the agent edit, run, screenshot, test, and commit. None
of that is specific to Anthropic's hosted model. To drive the same loop with a
**local or third-party model**:

- **Point Claude Code at a different backend.** Claude Code reads standard
  environment variables for its endpoint and credentials. Set
  `ANTHROPIC_BASE_URL` to an Anthropic-API-compatible gateway and provide the
  matching auth (`ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY`). Any gateway that
  speaks the Messages API works: a local server that exposes an Anthropic-shaped
  endpoint, or a translating proxy in front of an OpenAI-compatible or local model
  (for example an LLM gateway such as LiteLLM, or a community router like
  `claude-code-router`). This repo's own sandbox runs behind exactly such a proxy.
- **Or use a different agent entirely.** Nothing in the project depends on a
  specific tool. The two artifacts that make *any* agent effective here are:
  1. **`CLAUDE.md`** at the repo root: the standing brief (stack, the core
     mechanic, conventions, and "keep it this way" notes). An equivalent
     agent-memory file gives another tool the same footing.
  2. **The verify loop**: a zero-dependency test runner (`python tests/test_game.py`)
     and a headless browser for UI proof (`H8_EMU=1`). An agent that can run these
     can prove a change instead of guessing.
- **Keep the conventions.** Commit authorship stays the human copyright holder, no
  AI model identifier goes into committed artifacts, no em-dashes in game-facing
  prose, and the answer never leaks to the client. These are stated once in
  `CLAUDE.md` and honoured for free.

### Every kind of content is agent-authored and tool-checked (so any model works)

This is the reason nothing is tied to one provider: **every kind of content in
the game is authored by the agent in plain files, and validated by deterministic,
API-free tools.** The model supplies the creativity; the scripts supply the proof.
So a local model driving Claude Code can produce all of it, the same way.

| Content | The model authors | The deterministic tools check |
|---------|-------------------|-------------------------------|
| Game code / mechanic | Python + vanilla JS | `python tests/test_game.py`, `H8_EMU=1` browser tests |
| Arc content + writing | `data/arcs/<arc>.json` (properties, rotating prose pools, intro/win text, NPC, `sense`), per the schema in [`ARCS.md`](ARCS.md) | the suite loads/validates every arc; a new file appears on the menu automatically |
| BGM + SFX | `_<skin>(bus)` builders + effects in `static/audio.js` | `scripts/measure_audio.cjs` (calibrate), `render_audio.cjs` (audition), `tests/test_audio.py`; authoring guide + runnable examples in [`AUDIO.md`](AUDIO.md) |
| Translations | `data/i18n/src/<locale>.json` (text + honest self-scores) | `scripts/i18n_*.py` (extract/ingest/compile/QE) enforce the >=95 gate, **no MT/API**; see [`LOCALIZATION.md`](LOCALIZATION.md) |
| Reviews | the persona briefs write to `docs/reviews/` | house rules + the numbered series; see [`reviews/PERSONAS.md`](reviews/PERSONAS.md) |

None of the tools in that right column call a model or a network service; they are
pure Python/JS. The "intelligence" lives in the conversation with whatever model is
driving Claude Code, which is exactly what makes the whole project reproducible
with a local model.

On ownership when building with any of these tools, see [`OWNERSHIP.md`](OWNERSHIP.md):
the outputs belong to the human developer; the tool vendor does not own them.

## Repository map (what each piece is for)

```
app.py hallway.py anomalies.py memory.py i18n.py   the game + server
data/arcs/*.json                                   one self-contained arc each
data/i18n/                                          translation source + compiled
templates/ static/                                 page, styles, client, live audio
tests/                                              unit/API + browser emulation
scripts/                                            i18n pipeline, deploy, audio + media
docs/                                               design, testing, audio, i18n, reviews, ownership
Dockerfile                                          single-worker container for Spaces
CLAUDE.md                                           the agent's standing brief
```
