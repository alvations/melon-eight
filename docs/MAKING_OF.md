# Building Hallway 8 with Claude Code

This is the method behind the game: how it was designed and built end to end
through a conversation with an AI coding agent (Claude Code), how each feature
was verified before it shipped, and the gotchas that cost time so you can skip
them. If you want to reproduce *this* game, read the README. If you want to
reproduce the *process* on a game of your own, read this.

The whole thing was built by talking to the agent in plain language, one change
at a time, and having it write the code, run it, screenshot it, test it, and
commit it. There was no separate design doc up front; the design emerged in the
first few messages and then got refined by playing.

---

## 0. Setup that made it work

A few things were decided once, early, and paid off every turn:

- **A tiny, no-build stack.** Python + Flask backend, vanilla HTML/CSS/JS
  frontend, JSON for content. No bundler, no framework, no npm. The agent can
  edit any file and immediately run the app, which keeps the feedback loop fast.
- **A `CLAUDE.md` at the repo root.** This is the agent's standing memory: the
  stack, the core mechanic, the conventions (see below), and "keep it this way"
  notes next to load-bearing decisions. Every session reads it first, so you
  don't re-explain the project or re-litigate settled choices.
- **Explicit conventions, stated once.** Commit authorship, a no-spoilers rule,
  no em-dashes, colour constraints. Written down, they get honoured for free.
- **A test runner with zero dependencies** (`python tests/test_game.py`) and a
  **headless browser** (Chromium via Playwright) for UI verification. The agent
  can prove a change works instead of guessing.

The single highest-leverage artifact is `CLAUDE.md`. Start it on day one and
update it whenever a decision becomes load-bearing.

---

## 1. The design conversation

The game started as a discussion, not a spec: *how do you make a "spot the
change" loop that is about doubting your memory rather than hunting for a weird
sentence?* That produced a small set of principles that became the mechanic:

- Never describe everything; show only a subset of details each loop.
- Change *meaning*, not wording. Draw each detail from a pool of interchangeable
  sentences so players can't diff two loops literally.
- One quiet mutation per changed loop, never signposted.
- Frame it as a memory test, not "find the anomaly."

Only after the mechanic felt right did any code get written. Lesson: **spend the
first messages on the core loop and its framing, not on architecture.**

---

## 2. The working loop

Every feature, from the MVP to the audio, followed the same rhythm:

1. **Ask in plain language** for one change ("add an arc about taking the
   stairs", "the top bar is hidden on mobile", "make the crackle rarer").
2. **The agent implements it** across whatever files it touches.
3. **It verifies before claiming success:**
   - runs `python tests/test_game.py`,
   - drives the real app in headless Chromium and screenshots the result,
   - for logic, plays the game against the server's own answer to prove
     win/lose paths.
4. **It commits** (authored as the owner) and **pushes**.
5. You look at the screenshot / play it, and the next message is the next
   change. Bugs and polish are just more turns.

This is the important part: **the agent is expected to prove each change, not
assert it.** Screenshots and a passing test suite in the same turn as the edit
are what make it safe to move fast.

---

## 3. Architecture decisions (and why)

- **Server owns the truth.** `correct = (choice == "back") == has_anomaly`. The
  answer lives only in server state and is stripped from every payload (keys
  starting with `_` are dropped). The browser literally cannot be inspected to
  cheat. Decide early what must never reach the client.
- **Content is data, not code.** Each arc is one JSON file of properties,
  sentence pools, and story. New files appear on the menu automatically. This is
  what let "add an arc" be a 20-minute change with no engine edits.
- **Session state keyed by a client-echoed id, not a cookie.** (See lessons.)
- **Single process, in-memory state.** Fine for this game; it dictates
  single-worker deployment. Know this constraint before you scale.

---

## 4. Content model: arcs

An arc is a skin + backstory over the shared mechanic. The schema and the design
rules (every arc needs a strong diegetic hook, an NPC that can become the
anomaly, a loop-aware NPC twist, and a non-physical `sense` layer) live in
`docs/ARCS.md`, along with shared tuning and a queue of planned arcs. Keeping a
living design doc meant new arcs stayed consistent and we never re-derived the
rules.

The difficulty ramp and the doubt-prompt curve are engine-wide and documented
so every arc inherits them.

---

## 5. Procedural audio

There are no audio files in the game. Ambience is synthesised live in the
browser with the Web Audio API (`static/audio.js`): oscillators and filtered
noise per arc (fluorescent buzz, subway roll, stairwell wind), plus a muted
arpeggio for the landing. Rare events (a flicker, a passing train, a gust) are
scheduled sparsely. This kept the repo tiny and every soundscape editable as
code.

For sharing, the same synth is rendered offline (`OfflineAudioContext`) into an
OGG and a 1080p MP4 by `scripts/export_landing_media.py`, so the exported media
is exactly what players hear.

---

## 5b. The win screen: identity, sharing, and a fleeting look back

Late in the build the game got a critical review (kept in `docs/reviews/REVIEW.md`), and
several of its fixes converged on one screen: the exit. Worth copying as a
pattern:

- **Reward the win, keep the punishment.** The reviewer wanted the reset softened
  *and* the win rewarded. We took only the second half: the reset stays hard (it
  is the whole point of a memory game), and the reward is a way to pass the place
  on plus an optional, fleeting "look back" at how many runs it took. Say no to
  the half of a suggestion that would defang the design.
- **Make sharing look intentional, or don't ship it.** A share link with no Open
  Graph tags unfurls as a bare, broken-looking URL. The fix was a generated
  1200x630 "8" card (rendered from the game's own look with the same headless
  Chromium used for screenshots) plus `og:*` / `twitter:*` meta, and a favicon so
  the browser tab is not the "invisible = broken" tell the reviewer flagged. The
  identity is the single number `8`, reused in the card and the icon.
- **Mobile-first sharing.** Instead of five platform buttons, lead with the
  native share sheet where it exists (one tap reaches Instagram, Snapchat, X,
  Messages, everything) and fall back to explicit X / Facebook / LinkedIn only on
  desktops without the API. Less chrome, and it actually reaches the apps that
  have no web-link share.
- **Fleeting by design.** The "look back" line surfaces on tap, lingers a few
  seconds, then fades and reclaims its space so the eye returns to sharing or
  replaying. A thing that is meant to be glanced at should remove itself.
- **Copy is the owner's call; show options.** Voice ("invitation" vs "dare"),
  the exact per-arc share prompts, and the "look back" label were all previewed
  as rendered mockups and chosen by the owner before implementation. Render the
  choice, don't assume it.
- **Localize idioms as meaning.** "Look back" is metaphoric; every language uses
  its own retrospective phrase, not the literal turn-around verb (see
  `docs/LOCALIZATION.md`). The eight share invitations and the per-arc run-count
  lines went through the same i18n pipeline as everything else.

Two small UI fixes rode along, both from the same review: the emoji sound toggle
became a drawn line icon, and the native `<select>` language picker (OS chrome in
the mood board, competing with the arc choice) moved to a quiet top-left corner
with its chrome stripped to a drawn caret.

## 5c. The collection: making curiosity pay off

Later reviews (`docs/reviews/REVIEW3.md`, `docs/reviews/REVIEW_COLD.md`) converged on one gap:
the Act 2 touches, and the flashbacks they surfaced, were inert and
uncollected, so a curious player learned to stop touching. The fix was a
client-side **collection page** (`docs/COLLECTION.md`). Patterns worth copying:

- **Turn the best-written, least-seen content into a habit.** Flashbacks now
  fill a visible ledger and can be recalled; alternate endings and clean runs
  earn badges. The reward shows up in the first few touches, not on a 2% roll,
  which is what the reviews actually asked for.
- **Persistence belongs to the player.** The whole collection is `localStorage`,
  never server-side and never scored, the exact inverse of the answer state,
  which is server-only. Save/Load is an obfuscated file (a keystream XOR, not
  real crypto: enough to stop eyeballing, honest about being no more).
- **Draw the icons in the game's own hand.** Every badge is a thin line glyph in
  the noir palette, locked ones a padlock, one consistent visual language,
  with exactly one deliberate break (the full-colour "Melon Supporter"
  watermelon) so the exception reads as a wink, not a mistake.
- **Let a spec's number be a design lever.** The owner spec'd 16 badges; a 17th
  studio badge is simply hidden until a promo code redeems it, so the board
  shows 16 by default and the extra reads as a bonus rather than something
  withheld. The count question answered itself by choosing when the tile exists.
- **Extensible unlock plumbing, shipped minimal.** Promo codes (`MELONADE`, and
  `I18N-XX` to unlock a language) run through one small redeem function that
  could later gate arcs or features; today it does two things, and the codes
  persist through save/load.

## 6. Verification discipline

What the agent actually did to trust its own work:

- **Logic:** ran the app in-process and played optimally by reading the server's
  hidden answer, asserting the game wins in exactly eight correct calls and that
  a fresh, cookie-less client keeps its arc (the regression test).
- **UI:** launched Chromium, drove the flow, and screenshotted the landing, each
  skin, the win screens, and mobile viewports. A picture caught things a test
  never would (colours too similar, HUD clipped on mobile).
- **Audio:** rendered offline and inspected the node graph / sample peaks.
- **Emulation tests:** later, the ad-hoc browser drives were hardened into a
  committed layer (`tests/emulation.cjs`, run by `tests/test_emulation.py`) that
  boots the app and asserts client-only behaviour: reduced-motion rendering,
  touch verbs, the flavour line's auto-fade, the ending-achievement gate. It is
  opt-in (`H8_EMU=1`) and self-skips without a browser, so the fast suite stays
  fast. Full story in `docs/TESTING.md`.

**Disprove perceived bugs with a deterministic harness.** A report ("the verbs
never show under reduced motion") is a hypothesis, not a fact. Instead of
patching on suspicion, pin the randomness (`Math.random = () => 0` so a
15-45%-of-loops feature fires every loop), measure at *settle* not during a
transition (a sample taken mid-swap reads elements as `0x0` because an ancestor
is briefly hidden, and lies), and compare conditions. Here that method *disproved*
the reduced-motion verb bug (verbs render 18/18 and stay visible) and pointed at
the real defect, the flavour line not fading. The measurement saved a wrong fix
and became the regression test.

If you take one habit from this project: **make the agent show you a screenshot
or a green test in the same message it says "done".**

---

## 7. Deployment

The game ships as a Docker Space on Hugging Face (`Dockerfile`, port 7860,
single worker). `scripts/deploy_hf.py` creates/updates the Space and uploads;
`scripts/make_private_hf.py` toggles visibility for a private-until-release flow.

Deployment is **local-only** here: the sandboxed web session's network policy
blocks `huggingface.co` (a 403 at the egress proxy), so deploys must run from a
machine with normal internet. Know your environment's network policy before you
plan a deploy.

---

## 8. Hard-won lessons (the gotchas)

These cost real time. Skip them:

- **Cross-site iframe drops cookies.** On Spaces the app runs in an iframe, so
  the Flask session cookie was silently dropped and every request span a fresh
  default slot (the arc kept reverting, progress vanished). It reproduced only
  when hosted, never locally. Fix: hand the client a session id and echo it on
  every request via a header; keep the cookie only as a same-origin fallback.
- **`localStorage` throws on opaque origins / private mode.** An unguarded read
  in a constructor broke audio for some users (and for offline rendering). Wrap
  storage access in try/catch.
- **Browser autoplay policy.** Audio can only start after a user gesture. Start
  ambience on entering a loop / first interaction, and always ship a mute
  toggle.
- **Chromium refuses "unsafe" ports** (e.g. 5060, 6000) for page loads. Serve
  test instances on 8070+.
- **Centered flexbox clips tall content.** `align-items:center; min-height:100vh`
  hides the top of anything taller than the viewport, which buried the mobile
  progress bar. Top-align on mobile and let it scroll.
- **A live write token is a secret.** When a token has to be used, treat it as
  exposed the moment it's pasted and rotate it after.
- **A blanket reduced-motion rule can strand a toggling element.** The
  accessibility reset forced `opacity: 1 !important` on a set of "fades in once"
  elements. One of them (the Act 2 flavour line) also fades *out*, so the force
  pinned it visible forever. Exempt anything that toggles; and remember an
  **opacity fade is not motion**, so a text element may keep a gentle fade under
  reduced motion (re-raise its `transition-duration`) instead of snapping.
- **Timers outlive the DOM nodes they were set on.** A hover-to-inspect
  `setTimeout` kept firing after its line was replaced by the next loop, landing
  a stale aside "before" the new prose. Guard async UI callbacks with a
  render-generation counter and a `node.isConnected` check, and cancel on
  re-render.
- **Gate a badge on the server's own confirmation.** An "alternate ending"
  achievement recorded on the client before the server had resolved the exit.
  Record it only when the server returns the actual outcome (`kind == "exit"`),
  so client state can never diverge from what really happened.
- **Measuring during a transition gives false positives.** A UI probe taken
  right after a commit samples the previous loop mid-swap; wait for the settled
  state (controls visible plus a beat) or you will "reproduce" bugs that are not
  real.

---

## 9. Writing rules (the game's voice)

- **Never spoil the game in the instructions.** State the rule generically
  (proceed while it matches your memory, turn back if anything changed). Do not
  name the specific detail or character a player must notice; they discover it.
- **No em-dashes.** Commas, periods, colons instead. (Arrows in sign content are
  fine.)
- **Weave the rule into the story**, per arc, instead of listing it as rules.

These are enforced by writing them into `CLAUDE.md`, so every future edit obeys
them without a reminder.

---

## 10. Conventions worth copying

From this repo's `CLAUDE.md`, the ones that generalise:

- Commits are authored solely by the repo owner. Decide attribution up front.
- No AI model identifier in commits, code, comments, or docs.
- Develop on the branch/flow the owner authorises; commit and push when a change
  is complete and verified.
- After UI changes, verify in a real browser and run the tests before committing.
- Remind the owner when a change needs a manual deploy to reach production.

---

## 11. Replication checklist

To build a similar game with an AI coding agent:

1. **Write the mechanic down** in a few sentences before any code. Nail the
   framing (what the player is really doing).
2. **Create `CLAUDE.md`** with: the stack, the one-line mechanic, what must
   never leak to the client, and your conventions (attribution, tone, colours).
3. **Ask for a thin, runnable MVP** in a no-build stack. Make "run it" trivial.
4. **Add a test runner and browser verification early.** Insist the agent proves
   changes with a screenshot or a passing test in the same turn. Harden the
   repeated browser drives into a committed, self-skipping emulation layer once a
   feature is worth guarding (see `docs/TESTING.md`).
5. **Model content as data** so new content is a file, not an engine change.
6. **Iterate one change per message.** Design by playing: react to screenshots,
   ask for the next tweak.
7. **Write a living design doc** (`docs/ARCS.md`-style) once you have more than
   one variant, so consistency survives.
8. **Keep secrets out of the repo and chat**; when a token is unavoidable,
   rotate it after use.
9. **Update `CLAUDE.md` whenever a decision becomes load-bearing** (the iframe
   fix, the audio design, the tuning curves all live there now).
10. **Deploy from where the network allows it**, and script the deploy so it is
    one command.

---

## 12. Prompt playbook

Real prompts from this build that produced good results, lightly generalised:

- "Think of the mechanic first: how do we make it *feel* like X, not Y?"
- "Build a thin, runnable version I can play."
- "Add an arc about <situation>; keep the mechanic, give it its own NPC and a
  psychological twist."
- "There's a bug: <symptom>. Write a proper test that reproduces it, then fix it,
  and run random walks to be sure."
- "Don't change the mechanism first. Check what's actually happening, with a
  deterministic harness, before you touch anything." (turns a hunch into a
  measurement, and sometimes disproves the reported bug)
- "Show me a preview of <screen>." (invites a screenshot)
- "Make the instructions relate to the backstory, and don't reveal any details."
- "Optimise for mobile; the <element> isn't visible."
- "Have the reviewers look again, but wipe their memory of the last review and
  keep their personas; they should judge it as players, not read the code, except
  the one code reviewer." (independent player perspectives + one adversarial code
  read catch different classes of problem; run them in parallel)
- "Save everything we've learned into `CLAUDE.md`."

The through-line: describe the *goal and the feel*, let the agent choose the
implementation, and make it show you the result.

---

## 13. Where the rest of it is written down

This file is the *method*. The concrete, runnable how-to lives in companion docs,
so anyone (a person or another coding agent) can pick the repo up and re-create
the game and its whole workflow:

- **[`REPRODUCE.md`](REPRODUCE.md)**: run, test, measure audio, localize, run the
  reviewer panel, deploy, and (importantly) **drive this same build loop with a
  local or non-Anthropic model** by pointing Claude Code at a compatible gateway,
  or with a different agent entirely. Nothing here is tied to one vendor.
- **[`TESTING.md`](TESTING.md)**: the two test layers and the deterministic-harness
  diagnostic method.
- **[`AUDIO.md`](AUDIO.md)**: the live-synthesis audio pipeline (no audio files):
  how BGM/SFX are built, how they are level-matched to the landing theme, the
  measurement script, and the mobile/iframe autoplay unlock.
- **[`LOCALIZATION.md`](LOCALIZATION.md)**: the model-translated, self-scored
  localization pipeline and its quality gate.
- **[`ARCS.md`](ARCS.md)** / **[`COLLECTION.md`](COLLECTION.md)**: the design
  rules for arcs and the collection/achievements layer.
- **[`reviews/`](reviews/)**: the reviewer-persona passes (a harsh code-reading
  critic who keeps memory, plus memory-wiped player reviewers for mechanics,
  craft, and cold first impressions). The recipe to re-run them is in REPRODUCE.
- **[`OWNERSHIP.md`](OWNERSHIP.md)**: who owns code built with an AI agent
  (the human developer; the tool vendor does not), with pointers to the governing
  terms.

If you fork the *process* onto your own game, the two artifacts that carry the
most weight are `CLAUDE.md` (the agent's standing brief) and the zero-dependency
verify loop (`python tests/test_game.py`, plus the headless-browser emulation).
