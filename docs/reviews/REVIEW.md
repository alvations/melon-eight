<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Critical review and improvement backlog

An internal, deliberately harsh but impartial review of the game as it stands:
aesthetics, writing, core loop, and product. Written from actually reading the
code and the arc content and looking at the running build (landing screenshots),
not from memory. Treat it as a prioritized backlog, not gospel; some points are
taste, and the tone is intentionally severe to surface real gaps.

**Verdict: 6/10.** A genuinely clever core idea and rare good taste, held back by
punishing onboarding, a near-invisible visual identity, and one-note
replayability. The ceiling is an 8; it currently ships a 6 because the
localization is polished to a mirror shine while the front door barely opens.

## What actually works (credit where due)

- **The central conceit is smart and original-feeling.** You must remember
  *meaning*, not wording, because the drift engine (`anomalies.py`) mutates
  punctuation, phrasing, and even the heading so two loops can never be compared
  character for character. That is a real design idea, not a gimmick.
- **`PlayerMemory` ("the corridor that remembers you")** is a subtle touch most
  projects this size never bother with.
- **Procedurally generated audio, no assets** (`static/audio.js`): technically
  impressive and on theme.
- **Restraint.** Type on black, no jump scares, disciplined prose. Tasteful in a
  genre drowning in cheap shocks.
- **The localization is absurdly over-delivered** (21 languages behind a >=95 QE
  gate). See the last point for why that is also a criticism.

## The criticisms

### 1. The first impression is a blank void, literally
The arc cards are injected only after `/api/arcs` resolves, so a cold visitor
gets a beat of empty black with a title and a poetic lead and no call to action.
On a slow connection that beat is the whole first impression. Server-render the
cards or show a skeleton. Cheapest high-impact fix in the list.

### 2. It does not look like a game, it looks like a text file
Pure type on near-black, zero imagery, zero motion on the landing, no logo, no
thumbnail. For a game whose entire pitch is atmosphere, the landing delivers
almost none of it, and there is nothing to screenshot for a store page or a
post. The browser tab is titled `8` with no favicon, which reads as a
broken or untrusted page. Minimalism is a style; invisibility is a bug.

### 3. Contrast is punishing, and probably an accessibility fail
`--dim: #6d7076` on `#0b0c0e` carries most of the reading surface (taglines,
lead, HUD, asides, give-up link) at roughly 3:1, under WCAG AA for body text.
The mood is intentional; the illegibility is not. Lift dim text one or two steps
without losing the gloom.

### 4. Onboarding assumes the player already understands the trick
The rule is woven into the intro prose, which is great for tone and terrible for
comprehension. "Turn back is the correct move when something changed" is
counterintuitive; a first-timer fails the first anomaly, eats the full reset,
and bounces before the idea clicks. Add one explicit, skippable "how it works"
beat, or guarantee a clean (no-anomaly) first loop with a gentle prompt.

### 5. The punishment and retention math is brutal
Eight correct in a row, one wrong call resets the entire run to zero, with no
checkpoint and no streak insurance, on top of a memory task that costs 30 to 60
seconds per attempt. Hardcore players will love it; everyone else closes the
tab. At minimum surface the near miss ("you reached 6, your best"), and consider
one soft-fail per run.

### 6. Three arcs, one game
Coach 8, Hallway 8, and Stairway 8 differ in vocabulary and skin, not in play.
Once the player internalizes read, remember, compare, the second and third arcs
are the same loop reskinned. The most distinctive content (the NPC `knows`/
`speaks` twists and the psychological `sense` property, a wrongness you feel
rather than see) is rare among the ordinary anomalies, so most players barely
notice your best ideas.

### 7. Difficulty escalates in probability, not in kind
The ramp only raises the anomaly and doubt chance from loop to loop. Every loop
is the same binary UI with the same verbs. Nothing new is introduced deeper in:
no compounding mechanic at level 5, no second axis of pressure. The tension
rests entirely on the harsh reset, which is a blunt instrument.

### 8. Pacing tax
Lines fade in one at a time (~0.9s each). Atmospheric on loop 1; by loop 6 of
run 4 it is a toll booth between the player and a decision they already know how
to make. Give returning players a way to speed or skip the reveal.

### 9. Small tells of unfinishedness
- The sound toggle is a raw emoji floating in an otherwise meticulous serif
  design; it reads as a placeholder.
- The native `<select>` language picker drops OS chrome into the mood board, and
  it sits below the arcs where a utility control competes with the actual choice.
- The win screen is four lines and two buttons after an eight-streak
  achievement: no run stats, no "solved in N attempts," nothing shareable. It
  wastes the one moment a player feels triumphant and might tell someone.
- `.line:hover -> #fff` invites players to hover-scan and cheat around the low
  contrast, an accidental exploit born from point 3.

### 10. The irony
Best-in-class 21-language localization on a game most people cannot find, cannot
identify in five seconds, and may quit before the mechanic clicks. The engine
bay is immaculate on a car that is hard to start. Reallocate some of that rigor
to the funnel: onboarding, first paint, visual identity, retention.

## If you fix only five things, in order

1. **Kill the empty first paint.** Server-render or skeleton the arc cards; add a
   real `<title>` and a favicon.
2. **Onboard the mechanic explicitly.** A skippable one-screen "how it works," or
   a guaranteed clean first loop with a nudge.
3. **Soften the reset and reward the win.** Show best-reached-this-run and/or one
   forgiveness per run; make the win screen a moment with stats and a shareable
   result.
4. **Give the landing a visual identity.** Even one procedural, animated motif per
   arc (a drifting corridor line, a swaying cabin, descending steps) turns "text
   file" into "game" and gives you something to screenshot.
5. **Lift dim-text contrast** a step or two, and replace the emoji toggle and
   native select with in-house styled controls.

## Pull quote

*"A beautifully restrained idea about memory and doubt, that forgets to help you
remember how to play, and doubts whether you will stick around to find out."*
