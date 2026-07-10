<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# itch.io page art

Store assets for https://alvations.itch.io/eight. Every image here is captured
from the **real game** (not mock-ups), so the page shows exactly what a player
gets. Regenerate any time with the script below.

| File | itch slot | What it is |
|------|-----------|------------|
| `cover.png` | **Cover image** (Edit game → Cover image) | The real landing, framed to itch's 630×500 ratio (corner chrome hidden): the 8, the tagline, the three arcs. |
| `01-landing.png` | Screenshot | Arc-select landing. |
| `02-hallway.png` | Screenshot | A Hallway 8 loop (blue) with the Turn back / Walk on call. |
| `03-stairway.png` | Screenshot | A Stairway 8 loop (green). |
| `04-coach.png` | Screenshot | A Coach 8 loop (amber). |
| `05-win.png` | Screenshot | The "You are out." escape screen. |
| `06-credits.png` | Screenshot | The end-credits roll. |

Covers are shown at 630×500; screenshots have no fixed size (these are 2× for
crispness). Upload the cover in the **Cover image** box and the rest under
**Screenshots**.

## Regenerate

Needs a local server and headless Chromium (the repo's vendored Playwright).

```bash
# main set: cover, landing, the three arc loops, credits
HOST=127.0.0.1 PORT=8071 python app.py &
node scripts/make_itch_assets.cjs http://127.0.0.1:8071/ press/itch main

# the win screen needs a one-call win, so run the server with H8_GOAL=1
H8_GOAL=1 HOST=127.0.0.1 PORT=8071 python app.py &
node scripts/make_itch_assets.cjs http://127.0.0.1:8071/ press/itch win

# re-shoot just the credits (deterministic EIGHT-centred frame)
node scripts/make_itch_assets.cjs http://127.0.0.1:8071/ press/itch credits
```

These are page art only: `scripts/deploy_hf.py` excludes `press/**` from the HF
upload, and the itch bundle (`scripts/build_itch.py`) never includes it either.
