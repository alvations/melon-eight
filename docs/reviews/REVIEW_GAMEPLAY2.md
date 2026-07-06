<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Gameplay review, second pass: did the loop get deeper

The same mechanics-only reviewer, back to judge the game and not the package.
`docs/REVIEW_GAMEPLAY.md` was the first pass (6.5/10) and stays as the record. I
asked, above everything, for the difficulty to change the *task* and not just the
odds, and for the false exit to stop being a blind gamble. Both got built. So the
question is narrow: did hard mode actually make level 8 a different problem than
level 2, and did the coach's trail turn a coin-flip secret into a read.

**Verdict: 7.5/10, up a point.** This is the first change in four reviews that
touched the *center* instead of the edges. Hard mode adds real kinds of problem
(two changes at once, a change that persists, a clean revert), which is exactly
the "escalate in kind" I kept asking for, and the coach's false exit is now
*earned* through the passenger rather than stumbled into. The core decision
finally has more than one shape. It is 7.5 and not higher because the new depth
is **opt-in and hidden**: a new player never meets it, normal mode is still the
single probability dial it always was, and the doubt button still does nothing.

## What actually got deeper

- **Hard mode escalates in kind, for real.** A second simultaneous change means
  you cannot stop scanning after the first hit. Persistence ("you caught it, is
  it still there?") and the clean revert both break the assumption that each loop
  is independent, so memory now has to span more than one loop. These are genuine
  new techniques to learn, not a heavier coin. This is the fix.
- **The coach false exit is now a read, not a dice roll.** The passenger has to
  actually engage you enough, then delivers one fixed line that *arms* the exit,
  which can surface a few loops later. That is a trail: the attentive player sees
  it coming and the inattentive one does not. Exactly the right correction, and
  arc-flavoured rather than bolted on.
- **Easy mode is honest.** Fewer changes, a floor so it is never wholly still (so
  "always continue" still can't win), a gentler curve. It widens who can play the
  mechanic without faking it. Good.
- **Hard is earned, then default.** Locking hard until the first escape and then
  switching to it is a clean progression gesture: the game teaches you the base
  skill, then hands you the harder version once you have it.

## Where it still falls short

### 1. The depth is behind a door most players won't open
Hard mode is the answer to my central complaint, and it is off by default and
invisible until you win once. So the *first* full playthrough, the one that
decides whether a player stays, is still the single-probability-dial game the
last review described. The best mechanical content is gated behind clearing the
weakest version of the game. That is backwards for retention even if it is tidy
as progression.

### 2. Normal mode is unchanged, and most people will live there
Easy and hard are the interesting poles; normal, where the defaulting funnels
everyone after one win... wait, it funnels them to *hard*. Fine. But a player who
finds hard too much dials back to normal, which is still the meta-gameable base
rate from last time (later loops likelier to change, so you can lean on the ramp
instead of your memory). The middle setting did not get the double/revert
treatment, so "normal" is still the shallowest kind of the three.

### 3. The doubt button is still not a mechanic
Unchanged from last pass (#2 there). A game about doubt still has a certainty
prompt that never touches the outcome. Hard mode added a second *kind of change*;
it did not add a second *decision*. The wager is still sitting right there,
unbuilt, and it would do for the decision layer what hard mode did for the
perception layer.

### 4. Two verbs still never touch (by decision)
The recall idea was parked on purpose (see `docs/FUTURE.md`), so this stays a
known gap, not a bug: touching the room still cannot inform the go-on/turn-back
call. Worth restating only because hard mode makes it more tempting. When the
loop demands you track two changes and a possible revert, a touch that legally
bought you one property's history would be a real trade. The wall holds; the
pressure on it just went up.

### 5. Double changes need to be legible or they read as unfair
A two-change loop deep in hard mode is only fair if the player can, in principle,
catch both. The fairness guard shows every changed property, good, but there is
no signal that "this is a two-change loop", so a player who finds one, turns
back, and was right will never learn that a second had also moved. The lesson
that teaches "keep scanning" never actually gets taught, because turning back on
either change is correct and ends the loop. Consider a post-hoc tell on a
correct hard turn-back that *two* things had shifted, so the skill can form.

### 6. The fold is still random (still unmanaged)
Also unchanged (#6 last time). Hard mode raises the stakes of every touch via the
collection and the coach trail, which makes the unmanageable fold sting more, not
less. A readable fold would now pay off more than it would have a review ago.

## If I were fixing it next, in order

1. **Let players choose hard up front, or surface a "which is harder" read.**
   Do not hide your best mechanic behind beating your weakest.
2. **Make certainty a wager.** The one decision-layer change that would match what
   hard mode did for the perception layer.
3. **Teach the double.** A tell after a correct hard turn-back that a second
   thing had also moved, so "keep scanning" becomes a learnable habit.
4. **Give normal one new kind, too.** Even one (the revert) would lift the setting
   most players actually sit in out of pure base-rate.
5. **Make the fold readable.** Now that touching matters more, an unmanaged
   random reset is the least fair thing left.

## One line

> For the first time in four visits the change is in the room and not the doorway.
> Hard mode gives the decision new shapes and the coach's secret a real trail, and
> both are exactly right. Now stop hiding the good version behind the plain one,
> make the doubt button finally cost something, and the mechanic will have become
> a game.
