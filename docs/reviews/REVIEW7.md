<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Critical review, seventh pass: beta-2, and the first patch in a while that deepened

Same reviewer, seventh visit. The record stands: `REVIEW.md` (6), `REVIEW2`
(7), `REVIEW3` (7.5), `REVIEW4` (8), `REVIEW5` (8.5), `REVIEW6` (8.5, the beta-1
sign-off). Every one of the last three passes I said the same thing in a
different jacket: the systems keep getting finished to a shine around the same
three places, and the best mechanic hides behind a win. So I came into beta-2
expecting more frame around the same picture. I did not get that. For the first
time since REVIEW4 the patch touched the *mechanic*, not the mounting, and it
touched it in a way a player can actually feel. Tests are 36/36 green, i18n is
still zero-leak, and the new work carries an invariant test that holds under 300
seeds a difficulty across all three arcs.

**Verdict: 9/10, moved up half a point from the beta-1 sign-off.** Read the
reason before you celebrate: the half-point is earned almost entirely by two
things, opening hard mode to everyone and the double-change flare, both of which
are *felt*. It is NOT earned by the headline "aggro-item," which is fair,
correct, tested, and nearly imperceptible. And it is capped there, hard, by the
one number that has not moved in seven reviews: still three arcs.

## What actually moved the score

### 1. Hard mode is no longer behind a win. This resolves a standing complaint.
Three reviews running I logged it: "the best mechanic is still behind a win,"
and put it top of the 1.0 list. It is gone. The client offers all three
difficulties from the landing, default Normal, no escape required
(`game.js`: "hard is available to everyone"). That is not polish. That is the
single deepest lever in the game moved from "hidden until you already won once"
to "available to the curious on their first run." A first-timer who reads the
hint and picks Hard now meets cross-loop persistence, revert, and double changes
on day one. This is the correct fix and it directly retires REVIEW6's item #2.

### 2. The double-change flare is the best-designed thing in the patch.
Hard's second simultaneous change is back, and the old fairness worry (how do
you learn a second thing moved if turning back on the first is already correct?)
is answered honestly. On a *correct turn-back where two details moved*,
`app.py` hands back `flare_props`, and the client pulses both lines *after* the
call is committed (`flareLines`, 1.1s beat, then the normal transition). It never
touches the decision, it only teaches "keep scanning." It respects
`motion-reduce` (still reveals the two lines, just without the glow). The leak
surface is clean: the flare only fires post-decision on an already-correct call,
and `_anomaly_props` is stripped from the room payload like every other
underscore key. This is the kind of restraint the early reviews begged for:
a lesson delivered by the game, silently, without a text tell.

## The headline mechanic is the weakest part of the patch

The "aggro-item / late reveal" is where I have to be blunt, because the docs
oversell what the player experiences.

**The engineering is genuinely fair, and I verified it, not just read it.** The
`seen_props` guard holds. I walked full climbs across all three arcs, 4000 seeds
in hard, and an anomaly never once landed on the held item before that item had
been shown at baseline on an earlier loop. Hard always holds one, normal holds
~one in four, easy never. The reveal is paced to levels 4 to 6, never the last
loop, and the held item is force-shown at baseline on its reveal loop before it
can ever be the trap. The persist/revert branch cannot smuggle a held item in
early either, because a held item is excluded from the running until it is seen.
The test at `tests/test_game.py::test_aggro_item_is_held_then_revealed_fairly`
encodes exactly this and it is a good test. On fairness: full marks. This does
not turn the finish into luck.

**But ask what the player actually perceives, and the answer is: almost
nothing.** Two problems.

- **It is a no-op in most runs.** In hard, the held item becomes an anomaly at
  any point in only ~13% of runs (548/4000, 559, 502 across the three arcs). In
  the other ~87% the entire apparatus does one thing: it withholds a detail for
  a few loops, then shows it as an ordinary baseline sentence. The player has no
  way to distinguish that "arrival" from the constant rotation noise, because the
  loop already shows a random 4-to-6 of N details every time. A detail you have
  not seen in three loops is the *normal* texture of this game. So the
  "arrival" the docs describe as raising the stakes is, for the player, just
  another line scrolling into the subset.
- **Even when it does become the change, nothing marks it as the late one.** It
  renders as a plain anomaly from the same pool, indistinguishable from any other
  change. The "stakes rise once a detail you never had to track suddenly matters"
  framing is real inside the engine and invisible at the glass. Compare the
  flare, which the player *sees*. The aggro-item has no equivalent felt beat, by
  design, and that design choice makes most of it ceremony.

I am not asking for a text tell; that would violate the whole aesthetic. I am
saying the CLAUDE.md and ARCS.md prose claims a felt experience the mechanic does
not deliver, and a returning reviewer should call that gap. Right now the
aggro-item is a correctness achievement wearing a game-design headline.

## Loose ends I want named

- **The flare has no server test.** This codebase's discipline is its best trait:
  you test that compiled catalogs carry no answer keys, that every skin routes to
  its own audio builder. The newest answer-adjacent payload, `flare_props`, has
  zero direct coverage. Nothing asserts it appears only on a correct two-change
  turn-back, and nothing asserts it never appears otherwise. The aggro path got a
  300-seed invariant test; the flare, which actually crosses the server/client
  answer boundary, got none. Add one. It is the exact shape of test you already
  write well.
- **`hold_ready` is dead code.** `memory.py` declares `hold_ready: bool` with a
  comment ("whether a hold has been decided this run") and nothing ever reads or
  writes it; the real decision rides on `held_prop`/`held_reveal` set at level 0.
  Delete it or wire it. A misleading field in the one module that must stay
  legible is a small rot.
- **`pick_second_anomaly` is a byte-for-byte copy of `pick_anomaly`.** The only
  difference is the docstring. Fine for now, but it is duplication pretending to
  be two functions; if the selection logic ever changes, one will drift.

## What has not changed, and is now the whole ceiling

**Still three arcs. Seventh review.** I will not re-litigate it at length because
I have written it four times, but the calculus is now stark: beta-2 added real
mechanical depth to the same three places, and that depth is exactly why the
missing fourth place stings more, not less. Hard mode is now open to everyone and
genuinely deeper, which means there is more reason than ever to want a new
backstory to bring that depth into. The double-change and the aggro guard are
engine-wide and will light up a fourth arc for free the day it exists. Every
system in this game is now waiting on content that is not being written. This is
the reason 9 is the ceiling and not higher, and it is the reason the next
half-point cannot be bought with another mechanic. Paint a room.

The two cold-read snags from REVIEW6 also still stand: the promo box still
advertises a shop that is barely stocked, and the deep reset is still
uncushioned. Neither blocks anything; both are still on the list.

## Gate verdict

beta-2 is a real step, not motion. It resolved my longest-standing complaint
(hard mode gated behind a win), it added the cleanest, fairest piece of
"teach by showing" this game has (the flare), and it did it without a single
regression, leak, or broken test. The headline mechanic is honest engineering
dressed as a design beat, and the flare wants a test. Neither is a blocker. Move
the number to 9 and tag it.

## Pull quote

> For the first time in three reviews you deepened the game instead of framing
> it, and it shows: hard mode is out from behind its win and the double-change
> teaches itself in silence. Then you spent your headline on an aggro-item that
> is provably fair and practically invisible, and left the flare, the one piece
> that crosses the answer line, without a test. Nine out of ten, and every point
> of the missing one is a fourth place you still have not built.
