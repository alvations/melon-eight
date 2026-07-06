<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Act 2: the interactions ("touch the room")

Act 1 is the memory loop: read the place, decide **go on** or **turn back**,
eight correct calls escape, one wrong call resets. That never changes.

Act 2 is an optional layer on top: some details in the scene can be **touched**
(a verb per detail), and touching them deepens the story and the dread without
altering the win math. This document is the design of record. Read it before
adding interaction content to an arc.

## The one iron rule

**Interactions never change the forward/back judgement.** Correctness is still
`correct = (choice == "back") == has_anomaly`, computed only when the player
commits. Touching a detail can, very rarely, restart the run or end it in a wrong
ending, but it never decides the go-on/turn-back call, and it never reveals
whether the place changed. In almost every case touching changes nothing
mechanical; the player then makes the normal call, and that call is **go on as
often as turn back**. The interaction never tells you which. The one moment where
"just turn back and ignore it" is the lesson is the false exit below, and that is
made so rare it almost never happens.

## The five outcomes of a touch

When a detail is touched, the server rolls one outcome (weighted by level, never
by the detail's actual state, so it cannot be used as a detector):

1. **Flashback** (common), a fragment of backstory, then back to the loop.
   Free lore, no mechanical effect. Each fragment is **collected**: the client
   records its index and text, fills a dot on the Collectibles ledger, and lets
   the player recall its words later. Seeing every fragment in an arc earns a
   badge (see [`COLLECTION.md`](COLLECTION.md)), this is what turns the touch
   from inert flavour into a rewarded habit.
2. **Neutral reaction** (common), the world responds and tells you nothing (you
   wave, the camera swivels; you call out, the figure may turn). Happens whether
   or not the detail is the anomaly this loop.
3. **Red-herring reaction** (common), a *false clue*: a sensory detail that
   reads as evidence and is not (the poster is freshly printed, the seat is still
   warm). It appears on normal loops exactly as often as on changed ones, so it
   misleads as much as it "helps". Raises doubt, never resolves it.
4. **The fold** (uncommon), the place pulls you back to level 0. A self-inflicted
   reset, curiosity's price. More likely the deeper you are.
5. **The false exit** (very rare, trigger-gated), the run ends in a *wrong*
   ending, never a win. This is NOT a low-percentage roll on every touch: a "way
   out" dressed as salvation only *appears* on ~7% of loops around the
   three-quarter mark (levels 6-7), not near the finish, and it only fires if the
   player chooses to take it instead of turning back. Ignore it, which is the
   right move, and nothing happens. Most runs never see one.

Weighting (defaults; all tunable in one place in `hallway.py`). An ordinary
touch rolls only flavour vs fold:

| Level band | flashback / neutral / red-herring | fold (reset to 0) |
|---|---|---|
| L1–2 | 100% | 0% |
| L3–5 | ~90% | ~10% |
| L6–8 | ~85% | ~15% |

Levels 1–2 are pure, safe flavour: touching only ever gives a flashback or a
reaction, so the player learns the verb without risk. **From level 3 the
different consequences become triggerable** (the fold appears), rising to ~15% at
the bottom: a deep sting, never frequent. Whatever the outcome, **the touch is
always optional, and in most cases the player just ignores it and commits
forward or backward as normal.**

**The false exit is separate and gated, not a per-touch percentage:**

- it can only involve the **one exit-capable detail per arc** (Hallway's lit
  EXIT door, Stairway's shortcut landing door, Coach's carriage door onto a
  platform),
- the "way out dressed as salvation" only *appears at all* on **~7%** of loops
  around the **three-quarter mark (levels 6–7)**, not near the finish (rare
  enough to stay a discovery across runs, common enough that a player who keeps
  playing will eventually meet one). The
  temptation should bite when the end is in sight but not imminent. It is
  **visually distinct** so taking it is always a deliberate choice, never a
  misclick,
- even when it appears it does nothing unless the player **chooses to take it**;
  turning back or going on normally makes it evaporate.

Net effect: most runs never surface one, and most players who do surface one
ignore it. It stays a whispered secret, not a resented punishment.

## What the player sees

Only details actually shown this loop can be touched, so the available verbs
rotate with the scene (usually one or two). Each is a quiet contextual control
next to the loop, separate from the two commit buttons. Touching shows a short
line; the player then still makes the normal go-on/turn-back call. A given detail
can be touched once per loop.

**Onset (client, `buildTouch`):** the verbs hold back through the opening loops so
a new player learns the core turn-back/go-on cleanly, then appear **reliably from
level 3 onward** (level 4 on the very first climb of an arc), offered on most
loops (~0.55, rising to ~0.72 deep in a run), a couple at a time. They are not a
rare surprise: the point is that a returning player actually *meets* the layer
once they are past the learning loops. Below the onset there are no verbs at all.

Verbs are per-detail and themed, not always "open a door":

- **Hallway 8:** try the maintenance door · wave at the camera · look closer at
  the poster · call out to the man in grey.
- **Coach 8:** open the luggage · look out the window · read the scratched note ·
  nudge the sleeping passenger.
- **Stairway 8:** look out the landing window · read the scratches on the wall ·
  grip the handrail · call down the stairwell.

## The story Act 2 tells

The touches are the game's soul: they are the player's own memory, offering lore,
a false way out, or a fold back to the start. The through-line (per arc) is that
the player has done this walk before and the openings along it are not exits,
they are memories of leaving that the place keeps open because an easy lie is
more tempting than remembering why they are still here. See the per-arc
`interactions` (flashbacks) and `alt_endings` (false exits) in the arc JSON for
the concrete fragments and endings.

## Content schema (per arc JSON)

```jsonc
"interactions": {
  "<prop>": {
    "verb": "try the door",            // the contextual control label
    "flashback": ["...", "..."],       // outcome pools; picked by the roll
    "reaction": ["...", "..."],        // neutral reactions
    "herring":  ["...", "..."],        // red-herring reactions
    "fold":     ["..."],               // flavour shown as the place folds you
    "exit": "break_room"               // OPTIONAL: this prop can be the rare
                                       // false exit -> alt_endings["break_room"]
  }
},
"alt_endings": {
  "break_room": ["...", "...", "..."]  // the wrong-ending screen text
}
```

Rules for content:
- Keep flavour lines **state-agnostic**: they must read the same whether or not
  the prop is the anomaly (the server never passes the state in). This is what
  makes a touch un-cheatable.
- Only give `exit` to a detail that can plausibly look like a way out (a door, a
  window, a platform), and only one or two per arc.
- No em-dashes; no spoilers in the loop UI or intro (players discover the touch,
  and discover it changed nothing, on their own).

## Keys and localization

The interaction strings get deterministic keys via `i18n.arc_items`:

- `a:<arc>|ix|<prop>|verb`
- `a:<arc>|ix|<prop>|<kind>|<i>` for kind in flashback / reaction / herring / fold
- `a:<arc>|end|<id>|<i>` for the alternate endings

They localize through the normal pipeline (`docs/LOCALIZATION.md`) and fall back
to English key by key until translated, so Act 2 can ship in English first and be
localized after. They do not enter the level-composition QE gate (that composes
only loop prose), so translate them with per-line QE when the time comes.

## Server / client contract

- The public room carries `interactions: [{prop, verb}]` for the shown,
  touchable props (no answer leak; interactability is static per prop, never a
  function of the anomaly).
- `POST /api/interact {prop}` rolls an outcome and returns
  `{kind, line, level, goal, ending?}`. `fold` sets level 0; `false exit` returns
  the ending lines and resets progress for a fresh run. Neither reads or returns
  `_has_anomaly`. The commit endpoint `/api/act` is untouched.
