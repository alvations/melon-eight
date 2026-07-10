# CLAUDE.md, project memory for Hallway 8

Guidance for Claude Code working in this repo. Read this first.

## What this is

A browser game about memory and doubt. You move through a place that should be
identical each loop; **turn back** if something changed, **go on** if nothing
did. Eight correct calls in a row wins; one wrong call resets to the start. The
place is described from rotating sentence pools with only a subset of details
shown per loop, so the player must remember *meaning*, not wording.

It ships several **arcs** (skins/backstories) that share one mechanic. Live on a
Hugging Face Docker Space at `alvations/hallway8`.

## Stack & layout

Python + Flask backend, vanilla HTML/CSS/JS frontend. No build step.

```
app.py             Flask server; owns all game state, arc selection, answers
hallway.py         loads an arc, builds & describes a loop; difficulty ramp
anomalies.py       anomaly selection + wording/heading drift
memory.py          per-player habit tracking (PlayerMemory)
data/arcs/*.json   one file per arc: meta/skin, properties, sentence pools, story
templates/index.html
static/style.css   skins (body[data-skin=...]) + layout
static/game.js     client: arc select, rendering, pacing, drift, sid, controls
scripts/deploy_hf.py       deploy/update the HF Space (run locally)
scripts/make_private_hf.py toggle Space visibility (--public to release)
scripts/export_landing_media.py  render landing theme -> ogg + 1080p youtube mp4 (local)
tests/test_game.py         test suite (no pytest needed)
docs/ARCS.md               design rules, shared tuning, built + planned arcs
```

## Run / test / deploy

```bash
pip install -r requirements.txt
python app.py                      # http://127.0.0.1:5000  (HOST/PORT/SECRET_KEY env)
python tests/test_game.py          # runs the whole tests/ suite (auto-discovers
                                   # tests/test_*.py); plain runner or pytest
H8_EMU=1 python tests/test_game.py # also runs the headless-Chromium emulation
                                   # checks (tests/emulation.cjs); opt-in, skips
                                   # cleanly when node/Playwright/Chromium absent
```

**Emulation tests** (`tests/emulation.cjs`, driven by `tests/test_emulation.py`)
cover client rendering that unit tests cannot reach: reduced-motion prose order +
visibility, Act 2 touch verbs render and stay visible under reduced motion, the
flavour line auto-fades after a readable dwell (its opacity fade is kept alive
under reduced motion, since opacity is not motion), and the alternate-ending
achievement never unlocks without a server-confirmed exit. Off by default so the
fast suite stays fast; enable with `H8_EMU=1`.

Deploy is **local-only**: the sandboxed web session's network policy blocks
`huggingface.co` (403 at the proxy), so deployment must run from a machine with
normal internet:

```bash
export HF_TOKEN=hf_...             # or `hf auth login`; a WRITE token
python scripts/deploy_hf.py        # creates/updates alvations/hallway8, uploads
python scripts/make_private_hf.py            # private (default)
python scripts/make_private_hf.py --public   # public on release day
```

The `Dockerfile` targets HF Spaces (port 7860, **single gunicorn worker**: game
state is in-memory per process; do not scale workers). README front matter is the
Space card (`sdk: docker`, `app_port: 7860`). `deploy_hf.py` runs a **preflight**
first: it boots the game from ONLY the lean upload set and hits its endpoints, so
a broken build never ships (`tests/test_deploy.py` runs the same check in the
suite). App startup prints `[8-boot]` diagnostics to stderr (visible in the Space
logs), and `GET /healthz` returns `ok`.

**Two deploy targets, one engine (keep it this way).** 8 ships to the Flask
server (HF/Docker/Fly) AND to **itch.io** as a static HTML5 bundle. itch has no
backend, so the itch build runs the *same* Flask engine in the browser via
**Pyodide**: `scripts/build_itch.py` packs the runtime Python (`app.py` + engine
modules + arcs + compiled i18n) into `app.tar`, and `static/itch-boot.js` loads
Pyodide, `micropip`-installs Flask, unpacks it, and routes `/api/*` through
Flask's `test_client`. There is **no second, hand-maintained JS engine** to drift
out of sync; `game.js` is byte-identical to the server's. Build one or both:
`python scripts/build_itch.py` (-> `dist/hallway8-itch.zip`) or
`python scripts/build_all.py` (HF preflight + itch bundle, so *every build*
produces both). `itch-boot.js` and `dist/` are excluded from the HF upload
(`deploy_hf.IGNORE_PATTERNS`), so the server path is untouched. Guarded by
`tests/test_itch.py` (boots from only `app.tar` and serves every endpoint like
the browser shim). Full itch upload steps are in **docs/HOSTING.md**. The Pyodide
boot itself can only be verified in a real browser (the sandbox has no outbound
network for the CDN), so smoke-play once after the first itch upload.

**Heads-up (HF pricing):** Hugging Face now requires **PRO** to run **Docker**
Spaces on free cpu-basic (`create_repo` returns HTTP 402). `deploy_hf.py` catches
that and prints the options. Since 8 is a Flask backend (the answer lives
server-side), it cannot be a free *Static* Space. Free alternatives that run the
same portable `Dockerfile` (Fly.io with the committed `fly.toml`, Render, Cloud
Run) are in **docs/HOSTING.md**: always pin **one** instance (in-memory state).

**Shortcut test build (non-canonical).** `GOAL` (in `hallway.py`) reads `H8_GOAL`
(clamped 1..8), so `H8_GOAL=3 python app.py` reaches the end screen in 3 calls for
quick testing. `scripts/deploy_hf_shortcut.py` deploys that to a **separate**
Space (`alvations/hallway8-shortcut`) with `H8_GOAL=3` and `H8_ACT2_TEST=1` set;
it refuses to target the canonical `.../hallway8`. `H8_ACT2_TEST` boosts the Act 2
triggers (fold + false exit) so the endings are reachable for testing; it is OFF
in the real game. Canonical is always 8; never ship a shortcut build as the real
game.

## Core mechanic (server truth)

`correct = (choice == "back") == has_anomaly`. Confidence never enters this.
The answer (`_has_anomaly`, etc.) lives only in server state and is stripped from
every payload (`Hallway.public` drops keys starting with `_`), never leak it to
the client.

## Session state, important

State is keyed by a client-echoed **`sid`** (the `X-Sid` header), NOT the session
cookie. Reason: on Spaces the app runs in a cross-site iframe where the cookie is
dropped, which otherwise spawned a fresh default-arc slot on every request (arc
kept reverting to `hallway-eight`, progress lost). `/api/new` returns `sid`; the
client stores it and sends it on every call. The cookie remains only as a
same-origin fallback. Keep it this way.

## Arcs

Each arc is a self-contained `data/arcs/<id>.json`; new files appear on the
opening screen automatically. Every arc MUST have: a strong diegetic hook, an
NPC that can become the anomaly, a loop-aware NPC twist that acknowledges the
player (`knows` for silent figures, `speaks` for talkers), and a psychological
`sense` property (non-physical wrongness). Full schema, design rules, shared
tuning, and the queue of planned arcs are in **`docs/ARCS.md`**: read it before
adding or changing arcs, and keep it updated.

Every arc's `meta` also carries three win-screen strings: `share_prompt` (the
arc-flavoured share invitation), `attempt` (the run-count "look back" line, must
contain `{n}`), and `attempt_first` (the clean-first-run line). See docs/ARCS.md.

Built: `hallway-eight` (blue), `stairway8` (green, `axis: vertical`), `coach8`
(amber). Intros weave the turn-back/go-on rule into the story rather than stating
it as rules, keep that style.

## Win screen: sharing + look back

The exit screen is engine-wide; arcs only supply the three `meta` strings above.

- **Look back** (`#look`): a quiet toggle under "You're out." reveals the arc's
  `attempt`/`attempt_first` line (localized server-side; `{n}` = run count from
  `PlayerMemory.attempts`, resets + 1), then **fades after ~4.5s and hides**, so
  the eye returns to sharing/replaying. Deliberately fleeting; keep it that way.
- **Sharing** (`#share`): **progressive disclosure** keeps the reward moment
  calm. By default only the arc's `share_prompt` shows, as a quiet trigger
  (`#share-open`); tapping it reveals `#share-panel` (the invitation line + the
  share targets). One of eight cryptic invitation lines (`ui|share_1..8`) is
  chosen at random. Mobile-first: if
  `navigator.share` exists, show one **Share** button (native sheet reaches
  Instagram/Snapchat/etc.) and hide the explicit platform row; else X / Facebook
  / LinkedIn + Copy link. Shared URL = `location.origin + pathname` (override with
  `window.H8_SHARE_URL`). No stats are shared or tracked.
- **Identity / social card:** the tab favicon and the Open Graph / Twitter share
  image are the game's `8` (`static/img/{og.png,icon-512.png,icon-180.png}`, meta
  tags in `templates/index.html` with absolute `_external` URLs). 8 is the whole
  visual identity; do not add animated motifs.
- **First-reset onboarding** (`#learn`): shown once (localStorage `h8_onboarded`),
  heading is the localized `ui|instructions`, body reuses the arc's own intro.
- **Ending credits** (`#credits`): on a **first escape of an arc** (`winIsFirst`
  in `commit`) the win button reads **End Credits** (`setAgainMode`) and the nudge
  is held back; tapping it rolls the credits, and only after they close do the
  nudge + **Walk it again** appear. Player-initiated (not auto), so the look-back
  and share get their beat first. Re-viewable any time via **View credits** at the
  bottom of the Memory overlay (`#credits-row`, gated on any `mem.wins`). Content
  is the `CREDITS` array in `game.js`, styled like the landing text: a **Marvel-
  style opening studio splash** (`MELON LAB` + `© 2026 alvations`), then EIGHT,
  cast (AI collaborators one size smaller via `{n, sm}`), and the dedication as
  the final beat. **Authored English-only on purpose** (a personal dedication;
  only `view_credits`/`end_credits` are localized). Every line is our own; it
  never references the game that inspired it. Under reduced motion it does **not**
  scroll (`html.motion-reduce .credits-roll { animation: none }`): it reads
  statically. Tap anywhere or the `×` to skip.
- **Adaptive nudge** (`#nudge`): one quiet line above "Walk it again" that shifts
  with progress, unseen fragments here (`nudge_frags`, `{n}`) -> the other places
  (`nudge_arcs`) -> eight escapes from one (`nudge_eight`). It nudges breadth and
  depth only, never naming secret content (alternate endings, `npc_knows`).
  Hushed with `#look`/`#share` for the benediction's first beat.

## Collection: achievements + collectibles

Client-side persistence/replayability layer (full design in
**`docs/COLLECTION.md`**: read before touching it). Opened from a quiet corner
button (`#ach-open`, top-right cluster with sound/settings, select screen only)
so it lives off the landing; the overlay is titled **Memory** (`mem_title`). All
state is `localStorage` `h8_mem` (never sent to the server, never scored). Layout
top to bottom: Save/Load, then the achievements grid, then the **Recollections**
fragment ledger (`col_section`).

- **Only earned achievements appear**, populated as they unlock, no wall of
  padlocks, and no `{n} of {total}` count (it would spoil how many exist). `ACHS`
  in `static/game.js` holds `{id, test()}`; each earns a **drawn line glyph**
  (noir, chrome/accent tier). The `melon` "Melon Supporter" badge is the ONE
  colour break (a full-colour watermelon). Names/descriptions are localized
  `ach_n_*`/`ach_d_*` (English fallback `ACH_TEXT`); descriptions never spoil the
  detail to watch.
- **Records are achievements.** How a run was won is folded into `ACHS`, not a
  separate ledger: `steady` (never guessed), `cold` (no touches), `nerve` (final
  call a correct turn-back on a real change), `streak` (>=3 clean escapes). Still
  tracked in `mem.records` via a live `run` object (reset on every fresh climb;
  observes the win logic, never changes it). The strongest mark still also
  surfaces as a fleeting win-screen "read record" (`read_*`) under the look-back.
- **Fragment recall.** `recordFlashback(arc, idx, line)` stores the fragment text
  in `mem.flashText`; a filled ledger dot is a button that recalls its words
  (`col_recall` / `col_recall_empty`). Only collected fragments are quoted.
- **Save/Load** exports `eight-save.json`: two blobs (memory + achievements) run
  through a keystream XOR seeded `melon8`: **obfuscation, not crypto** (keeps a
  save unreadable, hides the achievement count). Wrong file ignored silently.
- **Erase** (`#ach-erase`): wipes the local memory back to a blank slate (runs,
  achievements, recollections, records), gated behind a deliberate
  confirm dialog (`#erase-confirm`, "This cannot be undone"). Display/language
  settings are preferences, not run-memory, so they are kept. Memory is
  `localStorage` only and per-browser, so this is a true reset for that device.
- **Promo codes / redeem: removed for now.** The Code + Redeem UI, the
  `redeemPromo` engine, and the `I18N-XX` locale-unlock path are gone; the
  language picker exposes only the 8 core locales (the other 13 stay translated
  and compiled on disk, just hidden). The `melon` "Melon Supporter" badge is
  **kept** (glyph + `mem.melon`), currently unearnable, held for a future use;
  the `mem.promos`/`mem.melon`/`mem.langs` fields stay in the save for
  compatibility. Dead `promo_*` UI strings remain in the catalog, unreferenced.

## Audio

Ambience is **generated live in the browser** (`static/audio.js`, Web Audio API)
per arc, no audio files, no external assets. It is room tone, not music and not
eerie stings: hallway = fluorescent buzz + ventilation hum (soft flicker); coach
= almost-empty-subway roll with steady soft rail-joint clacks (its identity, not
chuggy), plus a lurch and a passing train; stairway = near silence, low room tone
+ reverb space + a soft distant extractor-fan drone (so it does not sound like the
coach), with a wind gust. Occasional events (flicker, wind) use
`_every(22000, 40000, fn)` so a normal climb meets them about **once every 30s**;
the **coach** bed is deliberately quieter and calmer, so its lurch and passing
train are spaced wider (`_every(30000, 54000)`, ~once every 42s), still met in a
normal climb but interrupting the quiet less. The cadence test caps every
window's midpoint at 45s so events stay audible.

**Level-matching (keep it this way):** each arc's room tone is set via a per-arc
`BUS` map in `play()` (originally derived from RMS measurement against the
**landing theme**). Hallway and stairway sit near the landing theme's loudness;
**coach is deliberately the quietest bed** (owner tuning, well below landing,
`BUS.coach = 0.8`, an almost-empty-subway hush). The movement SFX (footsteps) play
at their natural level, a hair above the room tone, by owner preference; only the
beds are calibrated. Retuning a bed means re-measuring; keep hallway/stairway near
landing and coach the quiet outlier. `tests/test_audio.py`
guards the level-match, the ~30s cadence, and `unlock()`. **Mobile / iframe audio:** `ambience.unlock()` resumes a suspended
AudioContext, and `game.js` calls it **synchronously on the first gesture**
(capture phase, not `{once}`), before any `await`: iOS/Safari and the cross-site
Spaces iframe only start audio from a synchronous in-gesture `resume()`.
The **landing** screen has its own quiet theme (`_landing`): a soft, slow vi-IV-I-V
arpeggio, wistful fantasy, deliberately muted and background, never epic or eerie.
`window.ambience.play(skin)` starts on entering a loop (or `"landing"` on the
select screen); it stops/rebuilds on transitions. Landing audio starts on the
first user gesture (autoplay policy). An exported render of the landing theme is
saved at `static/audio/landing.ogg` (mono OGG Vorbis, ~42s, normalized; rendered
offline from the same synth via OfflineAudioContext). An always-visible mute toggle (`#sound-toggle`) persists to
`localStorage` (`h8_muted`); it is a **drawn SVG line icon** (speaker + waves, or
speaker + x when muted), not an emoji, and inherits the chrome-tier colour.
Audio only starts from a user gesture (browser autoplay policy).

**Movement SFX:** committing a choice plays
`window.ambience.step(dir, dwellMs, confidence)`, synthesised (footstep thud +
scuff, plus a directional scene-change swish). A confidence score (0..1) is
derived from `dwellMs` (`performance.now() - decideStart`, set when controls
appear) and raised by an explicit certainty rating (only 3/4 ever reach a
commit): confident -> 3-5 firm steps + swish; hesitant -> 2-4 tiptoe; long and
unsure -> a single near-silent shuffle. **Running SFX:** after the act response,
`ambience.run(dir)` plays a hurried 5-7 step flurry, used sparingly and mostly
when the player turned **back** on a real anomaly (`had_anomaly`, ~22%; ~5% on a
false alarm). All routed through the master gain, so the mute toggle covers it. To add a soundscape for a new arc, add a `_<skin>(bus)` builder
and branch to it in `play()`.

## Rendering & reduced motion (keep it this way)

Reduced motion (`html.motion-reduce`) suppresses animation/transition. The
`h8_motion` toggle is **tri-state and authoritative over the OS**: unset follows
`prefers-reduced-motion` (respects the accessibility default), `"1"` forces
reduced, and `"0"` forces full motion **overriding the OS** (so a phone in Low
Power / Reduce Motion can still run full motion when the player clears the
toggle). The checkbox reflects the effective state. Three load-bearing rules,
each covered by an emulation test (see below):

- **Do not force-`opacity:1` on anything that toggles off.** The motion-reduce
  reset pins "fade-in-once" elements visible; the Act 2 flavour line (`.touch-line`)
  toggles on AND off, so it is deliberately excluded from that list and instead
  keeps a real `transition-duration` under reduced motion (an opacity fade is not
  motion). It shows on a touch, holds ~4.5s, then **auto-fades** (`touchLineTimer`
  in `showTouchLine`, cleared in `clearTouch`). Never let it linger to the next
  commit or snap without a fade.
- **Guard async UI callbacks against loop changes.** The hover-to-inspect aside
  uses a `renderGen` counter (bumped every `renderRoom`) plus `node.isConnected`,
  so a stale `setTimeout` from a past loop can never land an aside before the new
  loop's prose has rendered.
- **Gate the alternate-ending badge on the server.** `takeExit` records the
  ending (unlocking `end_<arc>`) only when the server returns `kind == "exit"`, so
  the badge can never appear without the ending truly being reached.

Verify client rendering with the **browser emulation tests**: `H8_EMU=1 python
tests/test_game.py`. Full testing story (both layers, the deterministic-harness
diagnostic method, browser gotchas) is in **`docs/TESTING.md`**. Read it before
touching reduced-motion rendering or adding a UI-timing feature.

## Localization (i18n)

Full reproducible playbook (process, audit, per-line + level-composition QE,
post-edit QE, revision loop, the >=95 gate, adding a language/arc, and porting
the whole rigor to another game) lives in **`docs/LOCALIZATION.md`**: read it
before doing any translation work; the summary below is the map, that doc is the
territory.

Every translatable string has a deterministic key (`i18n.arc_items` / `ui_items`).
English in the arc JSON is the source of truth; `hallway.build(mem, rng, locale)`
rebuilds the same key per line and looks up the localized text, falling back to
English key by key (so partial translations degrade gracefully). The client
sends `X-Lang`; `app.py` resolves the locale and localizes meta/intro/win/arcs;
a language picker (top-left corner of the landing) persists to `localStorage`
(`h8_lang`). New UI keys since the first phase: `instructions`, `look_back`,
`share_1..8`, `share_native/copy/copied`, the collection strings (`ach_section`,
`col_section`, `ach_n_*`/`ach_d_*` badge names+descriptions, `col_recall`,
`col_recall_empty`), and the settings/fold strings (`set_*`, `fold_*`, `promo_*`).
New per-arc `meta` keys: `share_prompt`,
`attempt`, `attempt_first`. Metaphoric strings (e.g. `look_back`) must be
translated by *meaning*, not literally, see docs/LOCALIZATION.md.

Pipeline (translations are model-generated + self-scored; no external MT):
- `data/i18n/lines.json` = audit trail, `{key: {en_US:{text}, de_DE:{text,score,
  postedit,postedit_score,revisions[]}, ...}}` (exact shape the owner asked for).
- Author `data/i18n/src/<locale>.json` (UI + shared) or
  `data/i18n/src/<arc>/<locale>.json` (per-arc) -> `scripts/i18n_extract.py`
  (seed en) -> `scripts/i18n_ingest.py` (merge; globs both flat and per-arc
  files) -> `scripts/i18n_compile.py` (emit `data/i18n/compiled/<locale>.json`
  for the server + `static/i18n/<locale>.json` for the client UI).
- `scripts/i18n_levelqe.py --arc <arc>` composes N levels and scores each as the
  mean of its lines' postedit_scores (`data/i18n/levels.json`); gate is mean
  >= 95 over 120 levels. Below that, revise the weakest lines and re-run
  ingest/compile/levelqe.
- English (`en_US`) is the fixed reference and is never scored.

The picker exposes only the locales in `i18n.EXPOSED_LOCALES` (the phase's
chosen set), intersected with locales that actually have a compiled catalog.
Other locales can be fully translated + compiled on disk and still stay hidden
until promoted into that list. `available_locales()` (served by `/api/langs`)
enforces this; keep `EXPOSED_LOCALES` authoritative for what ships.

Status: engine + language toggle live. **All 21 locales are FULLY translated**,
every key: the three arcs' loop prose (which cleared the level gate 120/120 >= 95,
0 leaks; means ~95.2-95.6) AND all peripheral content (Act 2 touch reactions,
flashbacks, alternate endings, the exit trail, and every UI string, including the
difficulty + achievement labels for hard and the hidden Insane). Every locale
reports 0 missing content keys against en_US, 0 em-dashes, 0 answer-key leaks.
Eight are EXPOSED in the picker (English, German, French, Portuguese, Japanese,
Korean, Simplified Chinese, Vietnamese); the other 13 (en_GB, es_ES, fr_CA, it_IT,
nl_NL, cs_CZ, zh_TW, yue_HK, th_TH, id_ID, ms_MY, hi_IN, ta_IN) are complete +
compiled on disk but hidden until promoted into `i18n.EXPOSED_LOCALES`. (Earlier
the 13 hidden locales carried only the core loop prose and fell back to English
for Act 2 flavour + newer UI; that gap is now closed, so all 21 are peers.)
Per-locale iteration to the gate is easiest via `scripts/i18n_selfqe.py --loc
<code>` (read-only, reads a locale straight from its src files; safe alongside
others).

## UI conventions

- **Controls:** back is always on the LEFT, forward on the RIGHT. The UI adds the
  arrow; arc labels (`go_on`/`turn_back`) are plain text with no arrows. Default
  arrows are horizontal `←`/`→`; set `"axis": "vertical"` in an arc's meta for
  ↑ (back) / ↓ (forward), as stairway does.
- **Arc colours must stay visually distinct** (currently blue / amber / green)
  and must **carry into the loop**, not just the landing: the choice buttons
  (`.choice`), the HUD progress word (`.progress`), and the ambient background
  temperature all take a whisper of the arc's `--accent`/`--hue`, so the place
  keeps its identity all the way in. Keep these subtle (a hair, not a wash).
- **Chrome follows the last-played arc.** `applyMeta` records the arc's skin in
  `localStorage` `h8_last_skin`; the landing (and the settings panel opened from
  it) uses `lastSkin()` instead of snapping back to the default, so the settings
  accent matches the arc you were just in, not a fixed blue.
- **Language picker** is a quiet fixed control in the **top-left** corner
  (`#lang-corner`, a globe + native `<select>` with OS chrome stripped to a drawn
  caret), mirroring the sound toggle top-right. Shown only on the select screen
  (`show()` toggles it). Do not move it back into the arc column.
- **Doubt prompt** ("How certain are you?") appears randomly, more often near the
  exit. Certain (≥3) commits; guessing (≤2) returns for exactly one re-decide.
- A "give up · back to start" link returns to the arc-selection landing.
- **Mobile** (`@media max-width:640px`): the layout top-aligns (`align-items:
  flex-start`) instead of centering, because centered flex clips the top HUD when
  content is taller than the viewport. `#screen` gets `padding-top` to clear the
  fixed sound toggle. Keep the progress HUD visible; don't reintroduce centering.
  Load-bearing mobile rules to keep: overlays (`.learn-panel`, settings, fold)
  cap at `calc(100dvh - 2rem)` and scroll inside, so the action button is always
  reachable on a short phone; the Memory action row (Save/Load/Erase) uses
  `flex:1`/`min-width:0` so it fits a 375px width; the HUD carries `padding-right`
  and the fixed toggles use `env(safe-area-inset-top)` so "Furthest" never runs
  under the gear/speaker on Safari notched phones; a `<=380px` tier tightens type
  for the 12/13 mini. The achievements empty-state line spans the full grid row
  (`grid-column: 1 / -1`) so longer translations stay one line.
- **Mobile audio (HF):** the AudioContext is created **inside the first gesture**
  (`unlockAudio`), never at load, because a context constructed pre-gesture can
  stick suspended on mobile Chrome / the Spaces iframe. Known still-open bug on
  the live Space (cross-origin iframe autoplay policy); see `docs/FUTURE.md`.

## Shared tuning (engine-wide; see docs/ARCS.md for detail)

- Anomaly chance ramps with level *and difficulty* (`anomaly_chance(level, diff)`
  in `hallway.py`). Normal is `min(0.55, 0.02 + 0.076*level)`; easy ramps gentler
  to a lower cap, hard stiffer to a higher one. The **opening loop (level 0) is
  very low** on purpose (~2% normal, 1% easy, 3% hard): with no baseline yet,
  turning back would be an unwinnable coin flip, so a fresh run is almost always
  a clean baseline. It is not zero (a rare early jolt keeps it honest), and there
  is no level-0 floor. It ramps steeply to the cap by ~level 7.
- Doubt-prompt chance: `min(0.85, 0.12 + level*(0.7/goal))`.

## Difficulty & hard mode

Four difficulties exist on the server (`easy`/`normal`/`hard`/`insane`), sent from
the client via an `X-Diff` header like the locale and honoured per-request (client
owns unlock/selection). Only three are **exposed** (`EXPOSED_DIFFICULTIES` in
`hallway.py`); **Insane is hidden and unlockable** (see below).

- **Easy** leans toward "go on" with fewer changes but keeps a floor (never no
  anomaly), for younger players. **Normal** is the canonical ramp. **Hard**
  escalates *in kind* via **cross-loop continuity**: `build()` can make an anomaly
  **persist** across loops (you caught it, is it still there?) or cleanly
  **revert** (a clean loop right after a change), so memory must span more than
  one loop. Deep in a hard run a **second simultaneous** change can also appear;
  it is made fair by a **silent post-hoc flare** (`flare_props`): on a *correct*
  turn-back where two details moved, the client pulses both lines *after* the
  call is committed, so it never helps the decision, only teaches "keep
  scanning." No text tell, and the two changes never collide on one detail.
- **Aggro-item (late reveal):** each arc names a couple of small, inconspicuous
  `meta.late_props`. Once per climb `build()` may **hold some out** of the early
  loops so they first appear partway in (`mem.held` maps each to its reveal level,
  paced ~level 2-6, never the last), raising the stakes when a detail you never
  had to track starts to matter. **Hard always holds one or two of them (the
  "not everything up front" pressure lives here); normal only *rarely* holds a
  single one (~15%), so a normal player gets a fair chance to meet almost every
  encounter and the everyday run-to-run rotation of shown details is the replay
  hook; easy never holds.** Fairness guard: an anomaly can never land on a held
  item until the player has seen it at baseline on an *earlier* loop
  (`mem.seen_props`), so its first appearance is always a calm baseline, never
  the trap, and a late arrival is memory, not luck.
- **Hard is open to all:** the client offers all three difficulties from the
  start (default **Normal**); no escape is required to unlock Hard. Four badges
  (`hard_<arc>` ×3, `hard_all`) reward hard escapes; hard escapes are tracked in
  `mem.hardWins`.
- **Insane (hidden, anti-bot).** A fourth difficulty that ships **not exposed** in
  the picker and **unlocks only for a true completionist**: every earnable
  achievement unlocked, except the held studio badge, the date-locked
  opening-night badge, and the four Insane badges themselves (`INSANE_GATE_EXCLUDE`
  in `game.js`; `insaneUnlocked()`). Nobody is expected to reach it for weeks, so
  it does not affect the launch experience. **Strictly the hardest tier:** insane
  has a higher anomaly ramp than hard (step 0.092 vs 0.081, cap 0.66 vs 0.60) AND
  it inherits every hard escalation, the aggro-item holds, cross-loop
  persist/revert, and the deep double-change (each hard-only branch is now
  `diff in ("hard","insane")`, so hard's own path is untouched), on top of its
  randomized baseline. **What it changes:** every other mode
  shows a *fixed* global baseline vocabulary on clean loops, so a bot could
  memorize the all-clear wording and flag anything outside it. Insane randomizes
  **this run's baseline** for every property (`mem.run_baseline`, chosen at level
  0), so "normal" is run-specific and the change is any value that differs from
  *this run's* baseline (`anomalies.pick_anomaly(baseline_of=...)`). A memorized
  dictionary cannot tell clean from changed; you must remember what THIS run
  established. **Fairness (two guards):** (1) a change may only land on a property
  already seen at baseline earlier in the run (the aggro-item guard extended to
  every property), so level 0 and every detail's first appearance are calm
  baselines, never the trap. (2) The run baseline is drawn only from a property's
  **baseline-safe** pool (`_insane_baseline_keys`): its calm `values` plus only
  anomaly values whose prose reads as a plain *state*, never one that *announces a
  change* ("the arrow has reversed", "you don't remember") nor the NPC twist, so a
  clean loop never reads as wrong. Properties whose anomalies all announce a change
  (e.g. the sign) simply keep their calm baseline; enough others still randomize
  to keep it anti-bot. **No new content or i18n
  for the prose:** a value renders through its existing `v`/`x` line via
  `_pool_and_kind`, so Insane reuses every translated line. Four badges
  (`insane_<arc>` ×3, `insane_all`, tracked in `mem.insaneWins`) reward Insane
  escapes; they are earnable only after Insane is unlocked, so they are excluded
  from the unlock gate (no chicken-and-egg). All of it is isolated behind
  `diff == "insane"`, so easy/normal/hard are byte-for-byte unchanged (regression
  test: `test_existing_modes_never_touch_the_insane_baseline`). The 10 Insane UI
  strings (label, hint, four escape badges) are translated for all 21 locales.
- **Reading register** (`simple`/`normal`, an age-match toggle, default normal):
  simple surfaces a plain-language rule (`rules_plain`) on the intro/onboarding
  for younger readers, and can overlay a `<lang>.simple.json` UI catalog. It does
  not change any mechanic. The QE has an added "explain like I am young"
  simplicity gate (see docs/LOCALIZATION.md).
- **Coach false-exit trail** (coach only): the passenger must *interact* enough
  (be the change, or be touched back, `mem.seen_by_npc`); crossing the threshold
  fires one fixed **utterance** (`act2|exit|utterance`) that *arms* the exit
  (`mem.npc_triggered`). Only then can the false exit surface near the end,
  possibly a later loop than the utterance. Both stay ignorable: the player can
  read the line and still make the normal call. Louder in easy. Other arcs keep
  the flat gated roll.
- **Settings travel with the save:** difficulty, register, display settings, and
  language ride in the exported `eight-save.json` (see docs/COLLECTION.md).

## Working conventions (IMPORTANT)

- **Commits/PRs are authored solely by the repo owner.** Use the owner's git
  identity already recorded in the repo: read it with
  `git log -1 --format='%an <%ae>'`. Never add Claude as author or co-author, and
  never add Claude/Co-Authored-By/session trailers to commits or PR bodies.
  Commit with
  `git -c user.name="<owner>" -c user.email="<owner-email>" commit --author="<owner> <owner-email>"`.
- **Do not put any AI model identifier** in commits, code, comments, or docs.
- **License/attribution.** Apache-2.0. Copyright holder: `alvations (Melon Lab)`.
  New source files carry an SPDX header (`SPDX-License-Identifier: Apache-2.0`)
  plus the copyright line; never remove `LICENSE`, `NOTICE`, or existing headers.
- **Do not reference the source film or any external IP** anywhere in the repo
  (docs, code, comments, or commit messages). Keep the game's own naming.
- **Never spoil the game in the instructions/intros.** State the rule generically
  (proceed while it matches your memory, turn back if anything changed). Do NOT
  name the specific details/objects/NPC a player must watch, they discover those
  themselves.
- **No em-dashes** in game-facing prose (or anywhere). Use commas, periods, or
  colons instead. (Arrows like → ← in sign content are fine.)
- Develop on `main` for this project (owner has authorized pushing to main).
- After UI changes, verify in a real browser (Chromium at
  `/opt/pw-browsers/chromium-*/chrome-linux/chrome`, driven via Playwright) and
  run the test suite before committing. Avoid Chromium "unsafe" ports (e.g. 5060)
  when serving for tests; use 8070+.
- Deploy changes don't reach the live Space until someone runs
  `scripts/deploy_hf.py` locally, remind the owner after shipping.
