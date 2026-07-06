<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Future plans: designs considered and deferred

A parking lot for mechanics that were designed but deliberately not built, so the
thinking is not lost. Nothing here is committed. Each entry says what it is, what
it would cost, and, crucially, whether it clears or breaks the game's core
principles:

- resolution is server truth: `correct = (choice == "back") == has_anomaly`;
- confidence never enters correctness;
- the skill is remembering the *meaning* of a place, not its wording;
- the reset is hard, with no checkpoint;
- the look stays minimal (no HUD scores, no leaderboards, no tracking).

An idea that *breaks* one of these is not disqualified, but it becomes an
explicit owner decision, not a default.

---

## 1. Recall: connecting the two verbs (deferred)

**Status:** deferred. The owner chose to keep the Act 2 / Act 1 wall as-is; the
touch stays lore/atmosphere, not play. Kept here in full in case that changes.

**Problem it answers:** gameplay review #4 ("the second verb never touches the
first"). Today touching the room (Act 2) is walled off from the go-on/turn-back
call. The collection pays you to touch, so you touch, get a flashback, and make
the same untouched decision. Two verbs sharing a screen, not a system.

**The mechanic:** add one new touch outcome, **Recall.** You touch a detail and
the place tells you how that property *has always been* (its baseline), in-world:
"The light here has always been a steady fluorescent." You have already read this
loop's version, so for that one property you can now tell whether it changed.

**Why it is play, not content:**
- It rewards *partial* memory: the anomaly is one of ~5 shown details, so a blind
  recall is a coin-flip; a recall guided by a hunch ("something's off about the
  light") converts the hunch into knowledge. Fuzzy memory picks the target, the
  recall confirms it.
- It is a real trade (see cost), so the choice to recall sits *inside* the loop,
  next to the actual call. That is the two verbs in tension.
- Experts never need it; strugglers buy certainty at a price. That is a mastery
  gradient, so it also feeds review #7/#8.

**The important nuance:** Recall does **not** change the correctness formula. The
server still owns the truth; the player still does the comparison. What changes
is the *information available before choosing*, not the *result of a choice*. So
it honors the letter of the Act 2 axiom ("the action never changes the progress
result") while bending its spirit ("a touch now influences which choice you
make"). That spirit-bend is the whole decision.

**Cost models (it must not be a free oracle):**

| Model | Feel | Notes |
|---|---|---|
| Fold risk (recommended) | Recalling risks the place folding you to level 0 | Reuses the existing fold, and redeems review #6 by turning the fold into the chosen price of prying. Self-balancing: recalling all ~5 details is >50% chance of a fold, so no brute-forcing. |
| Hard step cost | Each recall drops a level | Deterministic and legible, but blunt and not thematic. |
| Scarcity | N recalls per run, then none | Simple and gentle, but adds a counter to a minimalist screen. |

In every model, recall also forfeits the "Cold" record (a touch means it was not
a clean escape), a soft cost on top of the hard one.

**Scope:** one arc only, behind a per-arc flag (like `axis: vertical`). Keep the
other two arcs pure-memory. This preserves the "trust only yourself" experience,
contains the risk, and fits the design where arcs already differ in mechanics.

**Fairness:** the recall returns a property's baseline value + a localized "as it
always is" sentence. It never returns `_has_anomaly` or `_anomaly_prop`, so the
payload still cannot be inspected to cheat.

**Build outline (small):** a per-arc `recall` block + a `recall` outcome in
`interact()` (return baseline sentence, roll the fold cost); one touch affordance
and reveal line reusing the touch-line plumbing; a Records tweak (recall forfeits
"Cold", maybe a new "trusted no recall" record); localize the recall sentences +
one or two UI strings; verify the payload still hides the answer.

---

## 2. Doubt as a wager (deferred)

**Status:** deferred; **breaks a core principle** ("confidence never enters
correctness").

**Problem it answers:** gameplay review #2 ("the certainty prompt is not a
mechanic"). Today rating yourself *guessing* just buys one more look and *certain*
just commits; the rating never touches the outcome.

**The mechanic:** tie certainty to stakes. A confident + correct call advances
(and is eligible for a "certain" feat); a confident + wrong call falls harder;
guessing still buys the second look but marks the run assisted. Calibration
becomes a skill you master and can be measured on, bridging review #7 and #8 for
almost no new content.

**Why deferred:** it reverses the documented invariant that confidence is
cosmetic. The *partial*, non-breaking version already shipped: the **Steady**
record rewards winning without ever admitting a guess, surfacing calibration
without changing the resolution. Promoting it to a real wager is the owner's call.

---

## 3. Mastery ranks / New Game+ (deferred)

**Status:** deferred; large scope, does not break core principles.

**Problem it answers:** gameplay review #8 (no mastery arc) and the standing
retention gap (no renewable reason to return).

**The mechanic:** after a clean escape, a harder variant of that arc unlocks:
more of the depth-gated anomaly types active from the start, tighter prose, fewer
details shown, shorter look windows. A diegetic frame ("the place remembers you,
and gets harder") fits the loop-aware theme. Expert players climb ranks; the reset
stays hard at every rank.

**Why deferred:** it is a whole progression layer, best built after there is more
mechanical depth (see the anomaly-type work in `reviews/REVIEW_GAMEPLAY.md`) for the
ranks to escalate.

---

## Known issues (post-beta fixes)

**Mobile audio still silent on the live HF Space (open).** On the Hugging Face
Space, sound does not start on mobile Chrome (and was not fixed by requesting the
desktop site). It works on desktop and in local mobile emulation. This is the
top post-beta bug to chase.

- **What is already done (did not fully fix it):** the AudioContext is no longer
  created at page load; it is constructed and resumed synchronously inside the
  first user gesture (`unlockAudio` in `static/game.js`), which is what iOS/Safari
  and mobile Chrome require. The unlock is registered in the capture phase, is not
  `{once}`, and the landing theme starts the instant the context reports running.
  Local emulation confirms "context unlocks from a gesture."
- **Why it likely still fails on the Space specifically:** the game runs in a
  **cross-origin iframe** on Spaces. Mobile Chrome gates audio in cross-origin
  iframes behind the parent frame's `allow="autoplay"` (and sometimes
  `allow="autoplay 'src'"`) permission-policy delegation, which we do not control
  from inside the iframe. A same-origin desktop page has no such gate, which is why
  desktop and local runs work but the embedded mobile case does not.
- **Next things to try (in order):**
  1. Confirm the failure is the iframe by loading the Space's app URL **directly**
     on mobile Chrome (not embedded) versus embedded; if direct works, it is the
     iframe autoplay-policy delegation.
  2. See whether the HF Space wrapper can set `allow="autoplay"` on the game
     iframe (Space card / embedding config). If HF owns that iframe, this may be a
     platform limitation to raise with them or route around.
  3. As a self-contained fallback, host the game at the top level (own the outer
     page) so there is no cross-origin iframe, or add an explicit in-game "tap to
     enable sound" affordance that both creates the context and plays a
     zero-length buffer in the same gesture (belt-and-suspenders for stubborn
     mobile webviews).
  4. Instrument `ctx.state` transitions on mobile (log suspended -> running) to
     see whether `resume()` is being rejected outright or resolving but muted.

## Notes

**Shipped since (no longer deferred):** escalating anomalies **in kind** landed
as **hard mode** (cross-loop persistence/revert, gated by depth and difficulty),
and the coach **false-exit trail** (the passenger's fixed utterance arming the
exit) landed for Coach 8. Both cleared every core principle: the resolution
formula and the memory skill are untouched. See CLAUDE.md ("Difficulty & hard
mode") and gameplay review #3 / #5.

**Tried and removed:** the **double change** (two simultaneous anomalies deep in
hard mode) was built and then pulled: turning back on either change is correct
and ends the loop, so the "keep scanning" skill it wanted to teach can never form
(gameplay review #5). It would only be fair with a post-hoc "two things moved"
tell; until that is designed, hard mode stays one-change-per-loop.

Still open here: the **legal decoy** (a property that legally drifts every loop,
never the anomaly) is a natural next hard-mode kind but needs per-arc decoy
content, so it is not built yet.
