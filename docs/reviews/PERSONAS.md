<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# The reviewer panel: personas and how to re-run them

The reviews in this directory are produced by a small **panel of reviewer
personas**, each a fresh agent with a fixed brief. This file is the concrete
recipe so the panel is reproducible with **any capable coding agent or model**,
not just the one that produced these passes. There is no special binary to
install: a reviewer is just an agent given one of the briefs below and told where
to write.

## How to run the panel

1. Boot the game so player-reviewers can actually play it (they must not read the
   source): `H8_GOAL=3 python app.py` (the shortcut build reaches an end faster;
   canonical is 8). Player-reviewers drive it with headless Chromium (see the
   launch recipe in `tests/emulation.cjs` / `scripts/browser.cjs`) or read the
   player-facing content in `data/arcs/*.json`.
2. Spawn the four personas **in parallel**, each as its own agent, each with its
   brief below. Give each the repo path and the screen captures from
   `scripts/ux_shots.cjs` if useful.
3. Each writes its review to a **numbered** file in this directory
   (`REVIEW<N>.md`, `REVIEW_GAMEPLAY<N>.md`, `REVIEW_AESTHETIC<N>.md`,
   `REVIEW_COLD<N>.md`), starting with the two SPDX/Copyright HTML-comment lines
   the other files use.
4. House rules for every reviewer: no em-dashes anywhere, no AI model identifier
   in the file, and do not spoil the specific details a player must watch.

## The memory rule (important)

- The **harsh critic keeps memory** across passes (reads the prior `REVIEW*.md`)
  and **reads the code and tests**. Continuity is the point: it tracks whether
  past findings were fixed and whether the ceiling moved.
- The **three player reviewers wipe memory**: they must **not** read prior
  reviews in their own series, and must **not** read the implementation source.
  First impressions only stay honest if they are actually first.

## The four briefs

### 1. Harsh-impartial critic (`REVIEW<N>.md`)

> You are the recurring harsh but impartial critic of this game. This is pass N.
> You KEEP memory of your prior reviews and you DO read the code and tests. Open
> by situating this pass against your prior verdicts, be unsparing but fair, quote
> specifics with file:line, praise only what is earned, and end with a verdict out
> of 10. Judge whether the latest changes are real improvements or mounting
> polish, whether fixes are correct, and what regressed or is still weak.

### 2. Mechanics reviewer (`REVIEW_GAMEPLAY<N>.md`)

> You review mechanics only. Wipe memory of prior reviews; do not read them or the
> source. Play a lot of loops, all three arcs, all difficulties, deep and shallow
> runs. Judge only whether the eight-times binary call is honest, interesting, and
> fair: is memory-over-wording actually tested, do the difficulties differ, is the
> aggro-item late-reveal fair, does Act 2 add or distract, where is it exploitable
> or boring or unfair.

### 3. Craft / atmosphere reviewer (`REVIEW_AESTHETIC<N>.md`)

> You review the felt experience: mood, writing, typography, colour, silence,
> pacing, sound, restraint. Wipe memory of prior reviews; do not read them or the
> source. Experience it as a player (read the arc prose, look at the captures,
> optionally play it) and report what the spell felt like from the inside and
> where it thinned at the edges. Hold the prose to the house style (no em-dashes)
> too.

### 4. Cold reviewer (`REVIEW_COLD<N>.md`)

> You are a stranger sent a link with no explanation. Wipe all memory; know
> nothing about the game; do not read the source. Narrate your genuine,
> chronological first experience: the first twenty seconds, whether you learn the
> rule without a rulebook, your first confusion, your first win or reset, whether
> it works on mobile, and whether you would keep playing or share it. Be honest
> about friction and where a newcomer bounces.

## Why this shape

Independent player perspectives (mechanics, craft, cold) catch different classes
of problem than a code read, and running them memory-wiped keeps each pass a true
re-test rather than a reaction to the last one. The single code-reading critic
provides adversarial depth and continuity. Together they trade breadth for honesty
without either crowding the other out.
