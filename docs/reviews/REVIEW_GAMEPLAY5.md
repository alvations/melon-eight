<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Gameplay review 5: the call, eight times, under a microscope

I do not care about the prose or the art. I care whether the call you make,
eight times in a row, is honest, interesting, and fair. So I did not read the
code. I booted the server and played: thousands of loops across all three arcs
and all three difficulties, deep runs and shallow, always logging what the
server admitted after I had already committed. Here is what the system actually
does when you press on it.

## Method (so you can reproduce it)

I drove the JSON API only (`POST /api/new`, `POST /api/act` with an `X-Sid`
header), never peeking at the answer before deciding. Every `/api/act` response
returns `had_anomaly` and `correct` for the room you just judged, so after the
fact I could label each room I had seen. `shown[i]` lines up with `sentences[i]`,
so I could attribute every sentence to its property. From that I built a census:
for every property, which exact sentences appear in clean rooms versus rooms the
server flagged as anomalous.

Samples: 400 to 600 fresh runs per arc per difficulty, tens of thousands of
individual calls.

## The core finding: the anomaly and the baseline are two disjoint, fixed word lists

The single most important thing I learned is that, for every property in every
arc, the sentence pool splits cleanly into two sets that never overlap:

- a small **all-clear set** (hallway: 47 lines total; stairway: 32; coach: 28)
  that appears in clean rooms, and
- a larger **wrongness set** (hallway: 75 lines; stairway: 111; coach: 95) that
  appears **only** in rooms the server marks anomalous.

Not "mostly." Exactly. Across the whole census there was not one sentence that
was baseline in one loop and the anomaly in another. The all-clear lines are
saturated with reassurance tags ("as always", "as usual", "the way it always
is", "as it should", "steady as ever", "shut tight", "still taped", "dry and
dull"). The wrongness lines describe a specific changed state ("the camera has
turned", "a crack that wasn't there before", "the poster hangs upside down",
"EXIT left, the arrow has reversed", "footsteps that don't match your own").

Because the two sets are disjoint and static, **the whole game is solved by
recognition, not memory.** I wrote a player that learns the all-clear list once
and then follows one rule: turn back if and only if a room contains any line that
is not on the all-clear list. Its record:

| arc + difficulty | wins | false negatives (missed anomaly) | false positives (false alarm) |
|---|---|---|---|
| hallway easy/normal/hard | 600/600 each | 0 | 0 |
| stairway normal/hard | 600/600 each | 0 | 0 |
| coach normal/hard | 600/600 each | 0 | 0 |

100 percent, everywhere, with zero errors over roughly 29,000 individual calls.
The presence of a single out-of-vocabulary line is *perfectly* equivalent to the
server's hidden `had_anomaly`. There is no case where a room looks clean but is
secretly changed, and no case where a room looks changed but is secretly clean.

## What this means for "remember meaning, not wording"

That premise, the thing the whole design is built around, is not what the game
actually tests. You never have to remember what the poster looked like last loop.
You have to notice that "the poster hangs upside down" is a line about something
being wrong. The rotating baseline wordings are not a memory challenge; they are
noise you learn to wave through, because they all carry the same "nothing to see
here" register. The skill the game trains is **spotting the wrongness register**,
and that skill transfers across runs and even works cold, on a room you have
never seen.

Two things make this concrete:

1. Roughly half the wrongness lines announce themselves outright ("wasn't there
   before", "for the first time", "never used to blink", "has reversed", "though
   you never saw it open", "not a beach"). A careful first-timer catches these
   with zero prior loops. (My tell-detector flagged 39 of 75 hallway anomaly
   lines as self-labeling, and it undercounts, since it missed "this time",
   "who isn't in the coach", "not the night setting", and so on.)
2. I confirmed there is a genuine minority of memory-honest anomalies, the ones
   with no built-in tell: dimness and colour and length and silence ("a grey
   dimness has settled over everything", "the lights are up full, harsh and
   white", "the coffee sits cold and still, no steam"). These are the good ones.
   But even they do not require *recall*, because the baseline is a fixed calm
   vocabulary. You do not think "the light was cold white last loop"; you think
   "this light line is not one of the calm light lines." Recognition again.

So: **fair, yes. Honest to its own premise, not really.** You can always win, but
you win by learning a register, not by holding a loop in your head.

## The three difficulties differ in frequency, not in kind

The anomaly rate does move meaningfully with difficulty (share of calls that were
a real change, measured on runs that reached the goal):

- easy: about 16 percent
- normal: about 28 percent
- hard: about 34 percent

But the *nature* of the call is identical at all three. Every anomaly, on every
difficulty, is still a single out-of-vocabulary line, still perfectly separable,
still caught 100 percent by the same recognizer. Hard mode's advertised tricks,
continuity that persists a change across loops, clean reverts, a second
simultaneous change, do not create a single room where the naive "any wrong line
means back" rule fails. Whatever those features do to the fiction, they do not
change the decision. A persisted anomaly still shows a wrong line and still
scores as back-is-correct; a revert shows only calm lines and scores as
on-is-correct. The player who reads each room on its own never needs to track
continuity at all.

Net: the difficulties change *how often you act*, not *how hard the act is*. If
anything, more anomalies means more of the easy detections, so "hard" is not
obviously harder per call for someone who has the register. Easy leaning toward
"go on" is real and appropriate for young players; I just would not tell an adult
that hard is a different mechanical test, because it is not.

## The genuinely honest parts

Credit where due, the core is clean in the ways that matter for trust:

- **The answer never leaks and confidence never counts.** I committed 600 calls
  at confidence 0.01, 0.5, and 0.99. `correct` was `(choice == back) ==
  had_anomaly` in every single one, zero violations, and no underscore-prefixed
  key ever appeared in a payload. Certainty is pure flavour, exactly as intended.
- **Absence is never a silent trap.** Only a subset of properties is described
  each loop, and a property simply not being mentioned is never the anomaly. When
  absence *is* the change ("there is no figure ahead this time", "no
  extinguisher on the wall this time"), it is spelled out as its own line under
  that property. So the rotating subset is not a source of unfair loss. Good.
- **Every anomaly is expressible and detectable.** Zero false negatives across
  the whole sample. There is no undetectable "you should have remembered"
  gotcha.

## Where it is exploitable or thin

- **The register is a hard exploit.** Once a player internalises the two
  vocabularies (a few runs, tops), the game collapses to a reading-comprehension
  scan: is any line phrased as wrongness? This is why my bot never loses. A
  returning player is not being memory-tested; they are speed-reading for the odd
  line out. That is a real ceiling on how interesting the eighth call can ever be.
- **First-appearance anomalies undercut the "baseline first" fairness story for
  regular props.** The design guard that an anomaly cannot land on a property
  before you have seen it clean applies to the held late-reveal items, but I
  logged 61 cases (in 600 hard runs) where a *regular* property was already
  anomalous the very first time it appeared in that run, across every property,
  concentrated at low levels. These are only winnable via cross-run vocabulary
  knowledge, not within-run memory. Fine for a veteran; quietly impossible for a
  player actually trying to play by memory.
- **Level-0 anomalies exist and are a pure vocabulary check.** They are rare (I
  measured about 1.5 to 2 percent), but at level 0 the player has literally no
  baseline for anything, so an opening-loop anomaly can only be caught by
  recognising the wrongness register. For a first-timer relying on memory, as the
  intro tells them to, an opening-loop change is an unavoidable loss. Rare, but it
  contradicts the stated reason level 0 is kept low.
- **Arrow-glyph drift is the one real discrimination trap, and it is unsignposted.**
  The exit sign baseline drifts its glyph and casing (EXIT arrow rendered as
  a right arrow, a dashed right arrow, extra spaces, "Exit" vs "EXIT"), all of
  which are clean, while a *reversed* arrow is the anomaly. A nervous player who
  turns back because the arrow "looks different" is punished for noticing exactly
  the kind of change the game tells them to notice. The rule (direction matters,
  style does not) is never stated. This is the single most interesting honest
  call in the game, and it is buried.

## Act 2 (touchable verbs): mechanically inert

The touch verbs show up in the room payload early (I saw them at level 1, not
just 3 to 4) and I ignored every one of them and still won 100 percent. They
cannot change `had_anomaly`, cannot reveal it, and are not required. As a
decision, Act 2 is a neutral red herring: it never adds information and never
adds risk. It is texture. It neither helps nor hurts the call, which means from a
pure mechanics seat it is closer to "distract" than "add", though harmlessly so.
The coach false-exit side path likewise never corrupted the core eight calls; my
on/back player reached the goal in coach without ever touching it.

## Bottom line

The core call is fair and tamper-proof: the answer is honest, confidence is inert,
nothing leaks, and there is no undetectable change. But it is not the memory game
it says it is. Because the calm lines and the wrong lines are two fixed,
non-overlapping vocabularies, the real skill is recognising a register of
wrongness, which a player learns in a few runs and which then solves the game 100
percent, on every arc and every difficulty, with no loop-to-loop memory at all.
The difficulties differ in how often you act, not in how hard the act is. The most
interesting honest calls the system already contains, colour and dimness and
length changes with no built-in tell, and the reversed-arrow-versus-glyph-drift
discrimination, are drowned out by a majority of anomalies that announce
themselves. If you want the eighth call to actually bite, that is the lever: let
baseline states sometimes migrate into the wrongness set and back, so the same
line can be clean one run and the trap the next, and force real recall instead of
register-spotting.
