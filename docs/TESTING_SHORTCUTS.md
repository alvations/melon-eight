<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Testing shortcuts: reach and visualise every scene fast

The canonical game is eight loops long and gates its late content (Act 2 fold,
the false exit, the ending credits) behind real progress, which is right for
players but slow for testing. These are the built-in shortcuts to jump to any
scene, and the in-repo tools to capture it as an image, audio, or video. Nothing
here changes the real game: the flags are opt-in and the canonical build ignores
them.

## The env flags (server)

| Flag | Effect | Where |
|------|--------|-------|
| `H8_GOAL=N` | Win in **N** loops instead of 8 (clamped 1..8). Reaches the win/credits fast. | `hallway.py` |
| `H8_ACT2_TEST=1` | Boost the Act 2 triggers (the fold and the false exit) so the alternate endings surface quickly. **Off in the real game.** | `hallway.py` |

```bash
H8_GOAL=3 python app.py                 # end screen in 3 correct calls
H8_GOAL=1 H8_ACT2_TEST=1 python app.py  # fastest path to endings for testing
```

There is also a **shortcut deploy** (`scripts/deploy_hf_shortcut.py`) that ships
`H8_GOAL=3` + `H8_ACT2_TEST=1` to a **separate** Space; it refuses to target the
canonical one. Never ship a shortcut build as the real game.

### Testing the hidden Insane difficulty

Insane is server-only and unlocks client-side only after every earnable
achievement is unlocked, so you cannot reach it by normal play in testing. Two
ways in:

- **Server behavior (no unlock needed):** send the header directly. Insane is a
  valid `X-Diff`, honoured per request:
  ```bash
  curl -s -X POST localhost:5000/api/new  -H 'X-Diff: insane' -H 'X-Sid: t' -d '{"arc":"hallway-eight"}'
  curl -s -X POST localhost:5000/api/act  -H 'X-Diff: insane' -H 'X-Sid: t' -d '{"choice":"continue","confidence":3}'
  ```
- **Client unlock (to see the picker button):** in the browser console, seed a
  completed memory so `insaneUnlocked()` is true, then reopen settings:
  ```js
  // earns every gate achievement; opening Settings reveals the Insane button
  localStorage.setItem('h8_mem', JSON.stringify({v:1,shared:true,attempts:20,
    records:{best:9,steady:true,cold:true,nerve:true,flawless:true},
    wins:{}, hardWins:{}, clean:{}, ends:{}, npc:{}, flash:{}, arcStarted:{}, best:{}}));
  // then, for each of hallway-eight/coach8/stairway8, set wins/hardWins/best=8,
  // clean=3, ends=true, npc={figure:true}, flash=[0..7]; reload.
  ```
  The unit/emulation tests cover the mechanic and unlock gate directly
  (`tests/test_game.py::test_insane_*`), so this is only for eyeballing the UI.

## The three acts / scenes, and how to reach + capture each

The client also exposes a few functions (it is a classic script, so they are
callable by bare name in `page.evaluate`) that let a test jump straight to a
scene without grinding: `showWin(payload)`, `openCredits()` / `playCredits()`,
and `buildTouch({level, room:{touch:[...]}})`. The capture tools below use these.

### Act 1: the core loop (reveal, doubt, commit)

The moment-to-moment game: the prose reveals line by line (the closing sense line
lands last), the doubt prompt may ask how sure you are, and you commit continue or
turn-back.

- **Reach it:** pick any arc and press Begin. Every loop is Act 1.
- **Capture:** `node scripts/ux_shots.cjs <url>` grabs the loop screen for every
  arc at desktop + mobile. `node scripts/capture_video.cjs <url> loop <arc>` records
  a reveal-and-commit.

### Act 2: touch the room (verbs, flavour line, fold, false exit)

The optional layer: some shown details can be touched, giving a flashback, a
reaction, a red herring, a rare fold back to the start, or (near the end) the
false way out. Verbs appear from about level 3 onward (see `docs/ACT2.md`).

- **Reach it fast:** `H8_ACT2_TEST=1` makes the fold and false exit common. Or, in
  a test, force a verb regardless of level:
  `buildTouch({ level: 4, room: { touch: [{ prop: "door", verb: "try the door" }] } })`.
- **Capture:** `node scripts/capture_video.cjs <url> act2 <arc>` forces a verb,
  clicks it, and records the flavour line appearing and auto-fading. The emulation
  test (`tests/emulation.cjs`) also asserts the onset and the flavour-line fade.

### The win scene (benediction, look-back, share, credits, nudge)

On escape: the hushed benediction lands first, then the "look back" toggle (with
the earned record beneath it on a clean run), the "leave the door open" share
prompt, and, on a first escape of an arc, the **ending credits** (button, or an
auto-roll after a readable dwell), after which the replay button and the adaptive
nudge appear.

- **Reach it fast:** `H8_GOAL=1 python app.py` and make one correct call. In a
  test, `showWin({win_text, attempts, attempt_text})` renders it directly, and
  `winIsFirst = true` before it puts the credits on the primary button.
- **Capture:** `node scripts/capture_video.cjs <url> win <arc>` records the win and
  expands the look-back; `... credits <arc>` records the credits roll;
  `node scripts/ux_shots.cjs` grabs the settled win frame per arc. Remember the
  `win-hush` holds the look-back/share/nudge at opacity 0 for ~1.6s, so capture a
  win *after* that settles.

## The capture tools (all in `scripts/`)

| Tool | Produces | Notes |
|------|----------|-------|
| `scripts/ux_shots.cjs` | PNG screenshots of select/intro/loop/win/credits, every arc, desktop + mobile | design/layout review |
| `scripts/capture_video.cjs` | WebM video of a scene (`loop`/`act2`/`win`/`credits`) | Playwright video; convert to mp4 with ffmpeg |
| `scripts/render_audio.cjs` | WebM audio of any arc's BGM or the SFX | faithful realtime capture of the live synth |
| `scripts/measure_audio.cjs` | RMS/peak/centroid table | audio level calibration (see `docs/AUDIO.md`) |
| `scripts/probe_render.cjs` | reveal-order report | verifies the sense line lands last |

All the Node tools resolve Chromium/Playwright portably; run `npm install && npx
playwright install chromium` once (see `package.json`). ffmpeg (optional, for
mp4/ogg conversion) is any standard build.
