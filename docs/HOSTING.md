<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Hosting 8 (free alternatives to Hugging Face Spaces)

Hugging Face now requires a **PRO** subscription to run **Docker** Spaces on free
cpu-basic (`create_repo` returns HTTP 402). **8** is a Flask backend, not a static
site: the loop's answer lives on the server and is stripped from every payload, so
the game cannot be made a free *Static* Space without moving that logic into the
browser and losing the anti-cheat property.

Two ways forward:

1. **Stay on HF**: subscribe to PRO (https://huggingface.co/pro), then re-run
   `python scripts/deploy_hf.py` unchanged.
2. **Host the same Docker image free elsewhere.** The `Dockerfile` at the repo
   root is standard and portable, so any host that builds a Dockerfile works. The
   one rule: **run exactly ONE instance/worker**, because game state (and each
   loop's answer) is in memory in a single process. Multiple instances would split
   state and break runs.

The client already targets `location.origin` for its API and share URL, so the
game just works at whatever URL the host gives you (override the share URL with
`window.H8_SHARE_URL` if you want a custom domain).

---

## Fly.io (recommended: Docker-native, one persistent machine)

A single shared-cpu machine comfortably runs this app.

```bash
# one-time
curl -L https://fly.io/install.sh | sh      # or: brew install flyctl
fly auth login

# from the repo root (a fly.toml is already committed)
fly launch --copy-config --no-deploy        # accept the app name / region
fly deploy                                   # builds the Dockerfile and ships it
fly scale count 1                            # IMPORTANT: exactly one machine
fly open                                     # opens the live URL
```

The committed `fly.toml` sets the internal port to **7860** (matching the
`Dockerfile`), keeps at most one machine, and does NOT auto-stop to zero (so a
mid-run player never hits a cold start that drops their in-memory slot).

## Render (free web service from the Dockerfile)

- New > **Web Service** > connect this repo.
- Environment: **Docker** (Render reads the root `Dockerfile`).
- Instance type: **Free**. Set **Instances = 1** (do not scale out).
- No start command needed (the Dockerfile `CMD` runs gunicorn on 7860; Render maps
  it automatically). Health check path: `/healthz`.

Caveat: the free tier sleeps after ~15 min idle, so the first hit after idle is a
slow cold start and any in-progress run resets. Fine for a hobby launch.

## Google Cloud Run (generous free tier, scales to zero)

```bash
gcloud run deploy eight --source . \
    --port 7860 --min-instances 0 --max-instances 1 \
    --allow-unauthenticated --region us-central1
```

`--max-instances 1` is **required** (in-memory state). `--min-instances 1` avoids
cold starts but costs a little; `0` is free but recycles the process (a fresh run
after idle).

---

## itch.io (static HTML5, the same engine run in-browser)

itch.io serves an HTML5 game as static files in a sandboxed iframe: there is **no
server** there. 8's answer lives server-side, so rather than hand-porting the
engine to JavaScript (a second engine that would drift out of sync), the itch
build runs the **exact same Flask engine in the browser via Pyodide**. A tiny
bootstrap (`static/itch-boot.js`) loads Pyodide, `micropip`-installs Flask,
unpacks the real runtime (`app.py` + `hallway.py`/`anomalies.py`/`memory.py`/
`i18n.py` + the arcs + compiled i18n) into Pyodide's filesystem, boots the app,
and dispatches every `/api/*` call through Flask's test client. `game.js` is
byte-for-byte the file the server ships; it just talks to a local Flask. One
engine, both targets, always in sync (guarded by `tests/test_itch.py`).

Build the bundle:

```bash
python scripts/build_itch.py         # -> dist/hallway8-itch.zip
# or build BOTH targets at once (HF preflight + itch bundle):
python scripts/build_all.py
```

Upload:

1. Zip `dist/itch/`'s contents (or use the ready-made `dist/hallway8-itch.zip`);
   `index.html` must be at the zip root.
2. itch.io: **Create/Edit project -> Kind of project: HTML**.
3. Upload the zip and tick **"This file will be played in the browser."**
4. Under **Embed options**, set **Viewport dimensions** (itch errors with "No
   dimensions provided or detected" if these are blank): **Width `1000`,
   Height `760`** (a tall reading column, so height matters; `1120 x 800` also
   works). Enable **Fullscreen button** and **Mobile friendly**.

Notes:
- Pyodide (~a few MB) loads from a CDN on first play, then caches. The landing's
  title/lead paint instantly while the engine settles (a couple of seconds on
  desktop, more on mobile), so it never looks blank.
- Nothing leaves the browser; there is no backend to run or pay for.
- To point the win-screen share link at your itch page instead of the raw iframe
  URL, add near the top of `index.html`'s `<head>`:
  `<script>window.H8_SHARE_URL = "https://YOURNAME.itch.io/eight";</script>`
- The sandbox that builds this has no outbound network, so the Pyodide boot
  itself can only be verified in a real browser; `tests/test_itch.py` proves the
  Python contract (it boots the app from *only* the packed `app.tar` and serves
  every endpoint exactly as the browser shim does), so if the server works, itch
  works. Do a one-time smoke play in a browser after the first upload.

---

## What NOT to do

- Do **not** run more than one instance/worker/replica anywhere. The single-worker
  gunicorn in the `Dockerfile` is deliberate; horizontal scaling splits the game
  state and the per-loop answer across processes and corrupts runs.
- Do **not** convert to a Static Space/site unless you accept moving the game
  logic (and the answer) into the client, which removes the anti-cheat design.
