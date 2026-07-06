---
title: "8"
emoji: 🎱
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Somewhere you can't quite leave. Choose a way through.
---

# Eight

[![Deploy to Hugging Face Spaces](https://huggingface.co/datasets/huggingface/badges/resolve/main/deploy-to-spaces-md.svg)](https://huggingface.co/new-space?sdk=docker)

**8** is a small browser game about memory and doubt. Its whole identity is the
number: eight loops to escape, several places that are all called *something 8*,
and a title screen that is just a single "8". (The repo and the live Space are
named `hallway8` after the first arc that was built, but the game itself is
**8**.)

You move through a place that should be identical every time. If anything
differs from what you remember, **turn back**. If nothing has changed, **go
on**. Reach the eighth loop without contradicting your own memory. Get it wrong
and you start over.

The trick is that the place is never described the same way twice. Only a
handful of its details are mentioned each loop, and each is phrased from a pool
of interchangeable sentences, so you can't compare two loops word-for-word.
You're forced to remember *meaning*, not wording. Somewhere in that fog, one
detail occasionally changes for real.

## The places (arcs)

**8** is not one setting but a set of **arcs**: self-contained places that each
have their own backstory, vocabulary, and visual skin, all sharing the one
mechanic. You pick one from the opening screen. Three ship today, and the queue
of planned places (Platform 8, Aisle 8, Ward 8, and more) lives in
[`docs/ARCS.md`](docs/ARCS.md).

- **Hallway 8**: locked in after hours, you follow a sign to the fire exit and
  walk corridor after identical corridor toward the eighth fire door.
- **Stairway 8**: the elevator is out of order, so you descend eight flights on
  foot, checking each landing before you keep going down to the ground floor.
- **Coach 8**: the conductor sent you forward to coach 8, but the night train
  never seems to reach it; you walk carriage after identical carriage.

Every arc carries more than physical changes: each has an **NPC** who is usually
passive but can become the anomaly (turning to face you, moving, vanishing),
including a loop-aware twist where they *acknowledge you*, and a psychological
`sense` layer where the wrongness is in perception, not objects (a corridor that
feels too long, a calm that shouldn't be there).

Arcs live as self-contained JSON files in `data/arcs/`. Adding a new one is just
dropping in another file (see *Adding an arc* below), no code changes needed.
The design rules and the queue of future arcs are kept in
[`docs/ARCS.md`](docs/ARCS.md). For how this game was built end to end with an AI
coding agent (the method, the verify-loop, the gotchas, and a replication
checklist), see [`docs/MAKING_OF.md`](docs/MAKING_OF.md).

## Languages

**8** ships in **eight languages** (English, German, French, Portuguese,
Japanese, Korean, Simplified Chinese, Vietnamese), chosen from a picker in the
quiet top-left corner of the opening screen. Thirteen more locales are fully
translated on disk and can be promoted into the picker at any time. English is
the source of truth; every other language is model-translated and self-scored
against a strict, reproducible quality gate. The full playbook is in
[`docs/LOCALIZATION.md`](docs/LOCALIZATION.md).

## Getting out, and passing it on

Escape and the eighth door gives. The win screen is quiet: it offers to let you
**look back** at how many runs it took (a single in-world line that surfaces,
then fades), and to **leave the door open** for someone else, sharing a cryptic
one-line invitation to X, Facebook, LinkedIn, or straight to a phone's share
sheet. A shared link unfurls as the game's own "8" card. Nothing about your play
is tracked or published; the share is just a line and a link.

## Keeping what you find

Behind a quiet **Achievements** link on the opening screen is a collection page
that turns what you do across runs into a record you can keep. It has two halves:
**Achievements**, a board of badges drawn as small line glyphs (escape each
place, escape all three, a clean run, an arc eight times, the loop-aware NPC
noticing you, each arc's rare alternate ending); and **Collectibles**, a ledger
of the backstory **fragments** you uncover by touching the room, one dot per
fragment, filling in as you find them. Tap a fragment you've collected and its
words surface again for a moment. Every badge is earned by playing (one studio
badge is held aside for the future).

Your progress lives in your browser, never on a server and never scored. You can
**save** it to a file and **load** it on another device, and **erase** it back to
a blank slate whenever you like. The full design is in
[`docs/COLLECTION.md`](docs/COLLECTION.md).

## What makes it unsettling

- **Partial description.** Each corridor has eight properties (lighting, sound,
  the man down the hall, the exit sign, a door, a camera, the floor, a poster),
  but only four to six are ever mentioned per loop.
- **Rotating prose.** Every detail is drawn from several equivalent sentences,
  so the wording drifts even when nothing has actually changed.
- **A single quiet mutation.** When a corridor *is* different, exactly one
  property has shifted to a plausible variant, nothing screams "look here."
- **A gentle start.** The first stage after you enter leans toward "nothing
  changed," so you learn the baseline by walking forward; the chance of a real
  change ramps up the deeper you get.
- **Doubt as a mechanic.** Now and then, more often as you near the exit, the
  game stops to ask how certain you are. Answer *certain* and your call locks in;
  admit you're *guessing* and it sends you back for one more look instead of
  committing. Honesty about doubt buys a second glance, nothing more.
- **A corridor that notices you.** Linger on one detail across loops and the
  narration begins to react to your habits.
- **Presentation drift.** Heading, pacing, font weight, letter spacing, and the
  background shift a fraction each loop, felt more than seen.

## Running the tests

```bash
python tests/test_game.py          # plain runner, no dependencies
H8_EMU=1 python tests/test_game.py # also runs the headless-browser emulation
# or, if you have it:  python -m pytest tests/test_game.py -q
```

The unit and API suite covers arc selection (including a regression test that the
chosen arc survives with cookies disabled, as in a cross-site iframe),
random-walk invariants, the difficulty ramp, aggro-item fairness, localization
coverage, server robustness, and the audio wiring. The opt-in **browser
emulation** (`H8_EMU=1`) covers client rendering unit tests cannot reach:
reduced-motion prose, the Act 2 verbs and flavour line, the credits roll, the
erase flow, every arc being playable, the audio graph, and network-failure
recovery. It skips cleanly when Node/Playwright/Chromium are absent.

**Reproduce anything, or build it with your own agent (local or non-Anthropic
model included):** [`docs/REPRODUCE.md`](docs/REPRODUCE.md). Audio pipeline:
[`docs/AUDIO.md`](docs/AUDIO.md). Reviewer panel and its reviews:
[`docs/reviews/`](docs/reviews/).

## Benchmark an LLM against it

Can a language model *remember a place*? [`llm-benchmark/`](llm-benchmark/) points a
local Hugging Face `transformers` model at the deployed game and measures how many
rounds it needs to escape each arc, across all **3 arcs × 3 difficulties × 2
reading levels**. The model plays exactly like a human (the server owns
correctness; the answer is never in the payload), so it is a genuine memory test.

```bash
cd llm-benchmark && pip install -r requirements.txt
python benchmark.py --base-url http://127.0.0.1:5000 --agent random     # baseline, no model
python benchmark.py --base-url http://127.0.0.1:5000 \
    --agent llm --model google/gemma-3n-e4b-it                          # a local model plays
```

See [`llm-benchmark/README.md`](llm-benchmark/README.md) for the agent protocol,
the sample prompt, and how to plug in your own model.

---

## Run it locally

You need **Python 3.9+** (any recent Python 3 works).

**1. Get the code**

```bash
git clone https://github.com/alvations/hallway8.git
cd hallway8
```

**2. (Optional but recommended) create a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

**3. Install the dependencies**

```bash
pip install -r requirements.txt
```

**4. Start the server**

```bash
python app.py
```

You'll see something like `Running on http://127.0.0.1:5000`.

**5. Open the game in your browser**

Go to **<http://127.0.0.1:5000>** and press **Begin**.

To stop the server, press `Ctrl+C` in the terminal.

### Options

| Variable     | Default     | What it does                                            |
|--------------|-------------|---------------------------------------------------------|
| `PORT`       | `5000`      | Port the server listens on.                             |
| `HOST`       | `127.0.0.1` | Interface to bind. Use `0.0.0.0` to expose on a network.|
| `SECRET_KEY` | random      | Set a fixed value to keep sessions stable across restarts. |

Example: `PORT=8000 python app.py` then open <http://127.0.0.1:8000>.

---

## Host it on Hugging Face Spaces

This repo is ready to run as a **Docker Space**. The included `Dockerfile`
serves the app on port `7860`, and the metadata block at the very top of this
README is the Space card Hugging Face reads, so there's nothing extra to
configure.

**Prerequisites:** a free Hugging Face account (<https://huggingface.co/join>).
For the git and CLI methods you'll also need a **write access token** from
<https://huggingface.co/settings/tokens>.

### Step 1, create the Space

Click the **Deploy to Spaces** badge at the top of this README, or go to
<https://huggingface.co/new-space> and:

1. **Owner / Space name**: e.g. `hallway8`.
2. **SDK**: choose **Docker**, then the **Blank** template.
3. **Hardware**: the free **CPU basic** tier is plenty.
4. **Visibility**: Public or Private, your call. Create the Space.

You now have an empty Space at
`https://huggingface.co/spaces/<your-username>/hallway8`.

### Step 2, get the code into the Space

Pick whichever is easiest. All three upload the same files; the Space rebuilds
on every change.

**Option A, drag and drop (no tools needed)**

In the Space's **Files** tab, click **Add file → Upload files** and upload the
whole project. Make sure these are all present at the Space root: `Dockerfile`,
`app.py`, `hallway.py`, `anomalies.py`, `memory.py`, `requirements.txt`,
`README.md`, and the `data/`, `templates/`, and `static/` folders.

**Option B, push with git**

A Space is a git repo. Add it as a remote and push:

```bash
git remote add space https://huggingface.co/spaces/<your-username>/hallway8
git push space main
```

When prompted, enter your **Hugging Face username** and paste your **access
token** as the password. (To avoid the prompt, run `pip install -U huggingface_hub`
then `hf auth login` once, it installs a git credential helper.)

> If the Space was created with its own starter `README.md`, your first push may
> be rejected as out of date. Either `git pull space main --rebase` first, or
> `git push space main --force` to overwrite the starter files with this repo.

**Option C, upload with the Hugging Face CLI**

```bash
pip install -U huggingface_hub
hf auth login                       # paste your write token once
hf upload <your-username>/hallway8 . . --repo-type=space
```

### Step 3, watch it build and play

Open the Space's **Logs** (or **App**) tab. Hugging Face builds the Docker
image and starts the container; the first build takes a couple of minutes. Once
the status turns **Running**, the game plays right there in the browser at
`https://huggingface.co/spaces/<your-username>/hallway8`.

### Recommended settings

- In **Settings → Variables and secrets**, add a secret named `SECRET_KEY` with
  any long random string. This keeps player sessions valid across Space
  restarts. (Without it a fresh key is generated on each boot, which simply
  resets any in-progress runs.)
- The free tier **sleeps after a period of inactivity** and wakes on the next
  visit, normal, and fine for a game like this.

> **Why the Dockerfile pins a single worker:** the game keeps each corridor's
> answer in server memory so the page can't be inspected to cheat. That state
> lives in one process, so the app must run with a single worker (the Dockerfile
> already does this). Don't scale it to multiple workers/replicas.

### Add your own "Open in Spaces" badge

Once your Space is live, you can point people straight at it by adding this near
the top of the README (swap in your username):

```markdown
[![Open in Spaces](https://huggingface.co/datasets/huggingface/badges/resolve/main/open-in-hf-spaces-md.svg)](https://huggingface.co/spaces/<your-username>/hallway8)
```

### Other hosts

The same `Dockerfile` runs anywhere that takes a container, Fly.io, Render,
Railway, Google Cloud Run, etc. Point the platform at the image (or use
`gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT app:app`) and keep it to a single
worker for the reason above.

---

## Layout

```
app.py             Flask server; owns all game state, arc selection, and answers
hallway.py         loads an arc, builds and describes a loop; localizes it
anomalies.py       anomaly selection + wording/heading drift
memory.py          tracks the player's habits across loops (incl. run count)
i18n.py            the localization key scheme, locale registry, catalog loader
data/arcs/*.json   one file per arc: meta/skin, properties, sentence pools, story
data/i18n/         translation source, audit trail, and compiled catalogs
templates/         the page
static/            style (skins), client logic, live audio, the "8" share art
scripts/           i18n pipeline, deploy, audio measure/render, screenshot + video
tests/             unit/API tests + the headless-browser emulation harness
llm-benchmark/     drive a local LLM against the deployed game as a memory benchmark
docs/              design, testing, audio, localization, reviews, ownership
package.json       the Node dev tool-chain (Playwright) for the test/capture tools
Dockerfile         container image for Hugging Face Spaces and other hosts
```

The game itself has **no build step and needs no Node**. The `package.json` and
the `scripts/*.cjs` tools (emulation, audio measurement/rendering, screenshots,
video) are only for reproducible testing and are documented in
[`docs/REPRODUCE.md`](docs/REPRODUCE.md); install them with `npm install && npx
playwright install chromium`.

The browser only ever receives a description, never whether a place has
changed, so you can't read the page source to cheat.

### Adding an arc

Copy an existing file in `data/arcs/` and edit it. Each arc is fully
self-contained:

- **`meta`**: `id`, `title`, `tagline`, a `skin` name, the two action labels
  (`go_on` / `turn_back`, plain text, no arrows; the UI always puts *back* on
  the left and *forward* on the right, and adds the arrow itself). Set
  `"axis": "vertical"` for stairs-like arcs so the arrows read ↑ (back) / ↓
  (forward) instead of the default ← / →. Also a `progress` HUD template
  (placeholders `{level}`, `{goal}`, `{floor}`, `{remaining}`), and friendly
  `labels` per property.
- **Win-screen strings (in `meta`)**: three short, arc-flavoured lines the exit
  screen uses: `share_prompt` (the invitation above the share row, e.g. *Leave
  the door open.* / *Hold the doors.*), `attempt` (the "look back" line for a run
  that took more than one try; must contain the `{n}` placeholder for the run
  count), and `attempt_first` (the line for a clean first run, no placeholder).
- **`properties`**: each with a `baseline` value, a pool of interchangeable
  `values` sentences, and `anomalies` (each an alternate value with its own
  sentence pool). Only these ever change between loops.
- **`title_variants`**, **`anchor_order`**, **`adaptive`**, and **`framing`**
  (the intro and win text).

To give the arc its own colours, add a `body[data-skin="<name>"]` block in
`static/style.css`. The new arc appears automatically on the opening screen, 
no code changes required.

---

## License and attribution

**8** is licensed under the **Apache License, Version 2.0**. See
[`LICENSE`](LICENSE) for the full text.

Copyright 2026 **alvations** (Melon Lab).

Author: alvations. Affiliation: Melon Lab. Attribution notices are in the
[`NOTICE`](NOTICE) file; per the license, redistributions and derivative works
must retain that `NOTICE`. Each source file also carries an SPDX header
(`SPDX-License-Identifier: Apache-2.0`) and the copyright line.

When contributing, keep your commit author identity as the copyright holder and
do not remove the license headers or the `NOTICE`.

### AI authorship and ownership

This game was written by a human developer working with **Claude Code**,
Anthropic's coding agent. **The code and content belong to alvations (Melon Lab);
Anthropic does not claim ownership of what the tool produces for you.** Under
Anthropic's terms, as between the parties, Anthropic assigns its interest in the
outputs to the customer and asserts no ownership over them. The full explanation,
the honest caveats, and pointers to the governing Commercial / Consumer Terms,
Usage Policy, and Claude Code docs are in
[`docs/OWNERSHIP.md`](docs/OWNERSHIP.md). This project references **no external
intellectual property**: all names, prose, art, and audio are its own.
