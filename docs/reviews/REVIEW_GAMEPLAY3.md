<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Gameplay review, third pass: the beta-1 gate

The mechanics-only reviewer, a short third visit specifically to sign off (or
not) on beta-1. `docs/REVIEW_GAMEPLAY.md` (6.5) and `docs/REVIEW_GAMEPLAY2.md`
(7.5) are the record. My remit is narrow and I will keep this narrow: since the
last pass the changes are localization completeness (the last English-only
strings got translated), a per-arc audio guard, and settings that travel with
the save. None of that is a mechanic. So my number does not move, and it should
not: **the decision layer is unchanged since the difficulty work landed.**

**Verdict: 7.5/10, held.** This is a stable, honest build with one genuinely good
core decision and, in hard mode, a second *kind* of that decision. Nothing since
the last pass touched the loop, so nothing here re-scores. I am signing off on
beta-1 as *mechanically sound and shippable*, not as *mechanically finished*.

## What I re-checked (and it still holds)

- **The core is still clean and unexploitable.** Server truth, answer stripped,
  fairness guard extended correctly to hard mode's multi-anomaly loops. I re-read
  the build path; the double-change still shows every changed property. Good.
- **Hard mode is still the real deepening.** Two changes at once, persistence,
  revert. It remains the one place the task changes shape, and it remains gated
  behind the first escape. Correct and still my main structural note.
- **No regressions in the loop.** The i18n and audio work did not perturb the
  resolution, the ramp, or the touch layer. Verified by replay and the suite.

## What is still open (unchanged, and fair to restate at a gate)

1. **The depth is opt-in and hidden.** Hard mode, my headline fix, is still off by
   default and unreachable on a first playthrough. For beta this is acceptable;
   for 1.0 it is the first thing to reconsider.
2. **The doubt button is still not a mechanic.** Confidence still never enters the
   outcome. The single highest-leverage decision-layer change remains unbuilt (and
   parked on purpose in `docs/FUTURE.md`, which I respect as a decision).
3. **Normal mode is still the single dial.** Most players sit here; it did not get
   a new kind. The new depth lives only at the poles.
4. **The two verbs still do not touch**, by explicit design. A known, accepted gap.

## Gate verdict

Ship beta-1. The mechanic is clean, fair, and now has one real difficulty of
kind. It is not yet a deep game, and the path to one is well understood and
written down. Nothing here blocks a beta; several things here should shape the
road to 1.0.

## One line

> Nothing since the last pass was a mechanic, so nothing re-scores; the loop is
> the same clean, honest, still-shallow-at-normal decision it was. Stable enough
> to call beta-1, not yet deep enough to call done. Ship it, then build the fourth
> arc and make the doubt button cost something.
