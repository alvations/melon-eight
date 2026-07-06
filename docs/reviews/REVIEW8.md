<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Critical review, eighth pass: beta-final, the hardening pass that quietly fixed a hole in my last verdict

Same reviewer, eighth visit. The record stands: `REVIEW.md` (6), `REVIEW2`
(7), `REVIEW3` (7.5), `REVIEW4` (8), `REVIEW5` (8.5), `REVIEW6` (8.5, beta-1
sign-off), `REVIEW7` (9/10, beta-2). Last time I moved the number to 9 for two
felt improvements (hard mode out from behind its win, the double-change flare)
and said flatly that the missing point was "a fourth place you still have not
built." I came into beta-final expecting either that fourth place or a coat of
lacquer. I got neither. What I got instead is a hardening pass, and I have to be
honest about it in both directions: it is mostly plumbing, but one piece of that
plumbing silently repairs a hole in the thing I praised in REVIEW7, and another
fixes audio being stone dead on the actual platform you ship to. So this is not
the mounting-polish pass I braced for. It is a correctness pass, and the
corrections are real.

Tests are 51/51 unit and 33/33 browser emulation, both green on this machine
(`H8_EMU=1 python tests/test_game.py`), and I ran them, I did not take the commit
message's word for it.

## The catch of the patch: `/api/new` was building the first Hard climb as Normal

This is the finding that matters, and it is the one the commit line undersells as
a generic "resolve difficulty on a fresh run." Read what it actually fixes.

The aggro-hold, beta-2's headline mechanic, is decided exactly once per climb, at
level 0, and its behaviour forks on difficulty (`hallway.py:210-223`): hard
*always* holds one or two `late_props`, normal holds a single one only ~15% of
the time. The opening room is built inside `/api/new`, before the first
`/api/act`. And before this patch, `/api/new` never resolved the client's
`X-Diff` header; it left the fresh slot at `DEFAULT_DIFFICULTY`. So a curious
first-timer who read the hint and picked **Hard** had their opening loop, and
therefore their per-climb hold decision, built as **Normal**. The signature
pressure of hard mode, "not everything is up front," was rolled on the normal
15% path for the entire first climb of every hard player.

That is precisely the audience REVIEW7 celebrated opening hard mode to: the
person trying Hard on day one. I stood here three months ago and wrote that a
first-timer who picks Hard "now meets cross-loop persistence, revert, and double
changes on day one." Half of that headline (the aggro-hold) was quietly not
firing on the climb that first-timer actually plays. The one-line fix at
`app.py:230-233` (`STATE[sid]["difficulty"] = _resolve_difficulty()` in
`api_new`) closes it, and the guard is now tested both ways
(`test_server_robustness.py:32-46`). I am crediting this specifically because it
is the rare case of a hardening commit reaching back and making a *previous
review's praise actually true*. Good catch, and an uncomfortable one to have
needed.

The sibling change, gating persist/revert on `mem.level > 0`
(`hallway.py:248`), is belt-and-suspenders (a fresh mem at level 0 has no
`prev_anomaly_prop` anyway), but it is correct and costs nothing.

## The mobile audio unlock is the other non-cosmetic fix

Everything in `static/audio.js` is generated live, which has always been the
show-off feature. It was also, on the platform you actually ship to, frequently
silent. iOS/Safari and mobile Chrome inside a cross-origin iframe (which is
exactly the Spaces embed) will only start an `AudioContext` if `resume()` is
called *synchronously* inside the gesture, before any `await`. The old boot flow
called `play("landing")` after the arc fetch had already resolved, i.e. after an
await, so on a phone the whole synthesised soundscape never started. The new
`unlock()` (`audio.js:539-546`) resumes the context first-thing, and the boot
handler registers it in the **capture** phase and, deliberately, *not*
`{once:true}` (`game.js:1861-1889`), so an early tap that is also choosing an arc
still gets its unlock in before the fetch. This is the difference between "the
audio system works in dev" and "the audio system works for the players." It is
not polish; it is the feature being turned on where it was off.

Coverage here is honest but thin: `test_context_unlock_method_exists` only
asserts the method is present. The synchronous-resume behaviour that is the
entire point is verifiable only in a real mobile browser, which the suite cannot
reach. Fair, but say it plainly: the load-bearing claim is not under test.

## The level-matching is the least-substantiated thing in the patch, and it cites a file that does not exist

The per-arc `BUS = { landing: 1, hallway: 2.2, coach: 4.2, stairway: 1.48 }`
(`audio.js:481`) is sold as RMS-derived, "each arc is calibrated so its measured
loudness (RMS) matches the landing theme," and the comment tells the reader:
"See `scripts/measure_audio.cjs` for how these were derived." **That script does
not exist.** `find . -name "*measure*"` returns nothing; the only reference to it
in the entire repo is the comment pointing at it. This codebase's single best
trait, the one I have praised in five reviews, is that its claims are
reproducible and its comments are load-bearing. Here a comment cites a
reproducibility artifact that was never committed, in the one module that just
made a numeric loudness claim. Either commit the script or drop the citation and
call the numbers hand-tuned by ear, which is no sin. Right now it reads as
rigour it cannot show.

And the test that guards this (`test_arcs_are_level_matched_to_landing`) only
checks that the string `BUS` appears in `play()`. Nothing verifies the numbers
match any measured RMS. So "level-matched to the landing" is, at the value level,
a trust-me. That is acceptable given there is no offline audio-render harness,
but combined with the phantom script it means the headline audio claim of this
patch is the one claim in the whole pass with no evidence behind it. The rare-
event cadence, by contrast, *is* tested (`test_rare_events_fire_about_every_30s`
pins every `_every()` window's midpoint under 45s), and the window did move from
50-90s to 22-40s, so "you now actually meet a flicker/lurch/train/wind on a
normal climb" is real and enforced.

## Act 2 onset: a genuine reach fix, and this one is tested properly

REVIEW-era Act 2 could be seen by *nobody*: a whole-first-climb suppression, then
a 15%/45% roll. The replacement is a clean onset gate, `firstArcRun ? 4 : 3`,
with the chance lifted to 0.55 (0.72 from level 5), `game.js:589-591`. At GOAL 8
that means a first climb offers touch across levels 4-7 at better-than-even odds,
so the layer is met instead of missed. And unlike the audio claims, this one has
real emulation coverage that asserts the behaviour on both sides of the onset
(`emulation.cjs:235-253`: verbs hold back below level 3, appear from it). This is
the model the audio changes should have followed.

## The mid-commit recovery trades a hard soft-lock for a rare silent desync

The soft-lock fix (`game.js:1263-1277`) is the right instinct: a network blip
mid-`/api/act` used to strand the player with the controls hidden until reload,
and now it restores them so the call can be made again. But look at what "made
again" means. `/api/act` is not idempotent: it mutates `mem.level` and consumes
`slot["room"]` (`app.py:330-341, 375`). The recovery is optimistic; it assumes
the request never reached the server. If the request *did* land and only the
**response** was lost, the server has already advanced to room N+1 while the
client still shows room N's prose and re-decides against it. The retry then
evaluates the player's call for room N against room N+1's hidden truth, which can
hand out an undeserved reset or an undeserved advance, silently. This is a rarer
failure than a dropped request, and the old behaviour (hard soft-lock) was
strictly worse, so I am not calling it a regression. I am naming it because the
comment says "the same call can simply be made again" as if that were safe, and
it is only safe on the assumption the write never happened. There is no request
id or idempotency token to distinguish "never processed" from "processed,
response lost." For a memory game where a single wrong-feeling reset is
maximally infuriating, that edge deserves at least a comment that admits it, if
not a nonce.

## Smaller notes

- **The store cap is FIFO, not LRU.** `_evict_if_full` evicts `next(iter(STATE))`,
  the oldest *inserted* slot (`app.py:64-71`). Reassigning an existing key does
  not move it in dict order, and `_slot()` mutates in place, so a genuine
  long-running session sits near the front and would be evicted first under a
  flood of forged sids, while the transient forgeries churn behind it. At a
  20000 cap on a single-worker low-traffic Space this is theoretical, and the
  fix correctly prevents unbounded growth, which was the actual goal. But it is
  eviction-by-age-of-arrival, not by-idleness, and the comment calling it "the
  oldest slots" glosses that the oldest slot can be the most active player.
- **The prose end beat is motion-only.** The closing sense line's deliberate
  longer pause (`game.js:531-543`) is a real, nice touch under normal motion, but
  under reduced motion every line shows at once, so the "lands last, on its own"
  effect simply does not exist for reduced-motion readers. That is a defensible
  call (you cannot stagger without motion), but the CLAUDE.md phrasing "the
  closing sense line now gets a deliberate end beat so it lands last" is true for
  some players and silently false for others.
- **Erase forgetting the onboarding flag is a correct little fix.**
  `eraseMemory` now also clears `h8_onboarded` (`game.js:1817-1823`), so a wiped
  player is a genuinely blank player who gets re-taught the rule on their first
  wrong call, instead of a blank player the game refuses to re-teach. Right call,
  and it retires REVIEW6's "the deep reset is uncushioned" snag alongside the
  confirm dialog.
- **REVIEW7's loose ends are cleared.** `hold_ready` dead code is gone,
  `pick_second_anomaly` is folded into one picker, the flare has its
  answer-boundary test, and the promo box that advertised a barely-stocked shop
  is removed from the UI. All three of my named loose ends and both cold-read
  snags are closed. Credit where due: you do not leave my lists lying around.

## What has not changed, and at beta-final that word matters more

**Still three arcs. Eighth review. And this time the tag on the box says
"final."** For seven passes the missing fourth place was a pending item; the
score was "9 and the tenth point is a room you have not painted yet." The word
*yet* was doing real work. "Beta-final" removes it. Every engine-wide system in
this game (the aggro guard, the double-change flare, hard mode's cross-loop
continuity, the per-arc audio identity you just level-matched) is built to light
up a fourth backstory for free, and the decision recorded in these commits is to
finalize without one. That is a product choice, not a code defect, and I will not
pretend a hardening pass regressed anything by not being content. But I will be
exact about what it means for the number: the missing point is no longer
deferred, it is declined.

## Gate verdict

This is a good, unglamorous pass. It fixed a bug that had quietly falsified a
line in my own last review, it turned the audio on where it was off for mobile
and iframe players, it made Act 2 actually reachable, and it hardened the server
against malformed input and unbounded growth, all without a leak, a broken test,
or a mechanic regression. Against that: the one genuinely new numeric claim
(RMS level-matching) is unevidenced and cites a file that is not in the repo, the
mid-commit recovery quietly assumes a write it cannot confirm never happened, and
the ceiling did not move because the fourth arc is now not late, it is decided
against.

**Verdict: 9/10, held from beta-2.** Same number, opposite reason. In REVIEW7 the
9 meant "9 and climbing." Here it means "9 and locked": the code under the 9 is
more defensible than it was, several of the props holding it up were quietly
straightened, and the last point was closed by choice rather than left open. A
clean beta-final. If a fourth arc ever ships, it walks straight into a tenth
point that every system in this build has already been waiting to give it.

## Pull quote

> The pass I braced for lacquer turned out to be the pass that found Hard mode
> was being built as Normal on the first climb, the exact player I praised you
> for winning over, and it turned the audio on where your actual platform had it
> off. Then it made one loudness claim it cannot show, citing a script that is
> not in the repo, and taught the retry path to assume a write it never
> confirmed. Nine out of ten, held: the code under the number got sturdier and
> the tenth point stopped being late and started being declined.
