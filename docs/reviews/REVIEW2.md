<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Critical review, second pass

A second deliberately harsh but impartial review, written after the first round
of fixes landed (`docs/REVIEW.md` is the first pass and is left untouched as the
record). Same method: read the code and arc content, play the running build,
look at the actual screens (landing, corridor, all three win screens, mobile).
Same rules of engagement: credit what improved, then go hunting for what is still
wrong, in the tone of someone who wants the game to be better, not flattered.

**Verdict: 7/10, up from 6.** The front door opens now. The first paint is a
clean "8", the mechanic gets explained after the first reset, the exit rewards
you and hands you something to share, the tab has a face, and the whole thing
speaks eight languages without a native `<select>` breaking the mood. That is a
real jump in polish. But the score is capped at 7 because every one of those wins
is on the *edges* of the experience, the packaging, the onramp, the exit, the
share. The **middle** of the game, the thing you actually do for the two minutes
between "Begin" and "You're out", is exactly what it was: read a paragraph, press
one of two buttons. The game got a better coat of paint and a better goodbye. It
did not get a deeper verb.

## What actually works now (credit where due)

- **The onboarding is solved, gracefully.** Introducing the rule *after* the
  first reset, in the arc's own words under a neutral "Instructions" heading, is a
  better solution than the "one-screen how-it-works" the first review asked for.
  It teaches at the exact moment of confusion and never nags again.
- **The exit finally feels like an ending.** The fleeting "look back" line is a
  genuinely tasteful touch: it appears, it is read, it removes itself. That is
  confident design. The per-arc share prompt ("Leave the door open" / "Hold the
  doors") is a small, correct detail.
- **Sharing is built the right way for once.** Mobile-first native share, a
  generated Open Graph card in the game's own identity, a favicon. Most indie
  games ship a raw URL; this ships a card.
- **The i18n rigor held.** New strings (eight invitations, per-arc run-count
  lines, the metaphoric "look back") went through the same pipeline and tests.
  The discipline did not lapse under feature pressure.

## The criticisms

### 1. The verb is still "read, then click one of two buttons"

This was point 2 last time and it is still the elephant. Everything added this
round is around the loop, not in it. A player's actual moment-to-moment is
unchanged: parse a paragraph, decide same/different, press. No spatial sense, no
manipulation, no second kind of action. The polish raises the *presentation*
score and leaves the *play* score where it was. Until the middle gets a second
verb, the ceiling is a clever curiosity, not a game people describe to friends by
what they *did*.

### 2. You built the sharing loop before the game earns a second session

Share buttons, an OG card, "leave the door open", this is distribution
machinery, and it is now more sophisticated than the retention machinery, which
is still nonexistent. There is no reason to come back after one win. "Walk it
again" is the identical run. No streak, no ladder, no daily seed, no unlock,
nothing that is different on visit two. Optimizing virality before retention is
pouring water into a bucket with no bottom: you will bring people in and they
will leave at the same rate, having shared a link that leads their friends to the
same one-and-done.

### 3. Difficulty is still a single probability dial

`anomaly_chance` ramps from ~0.18 to a 0.55 cap, and that is the entire
escalation. Level 8 is not a *different* challenge from level 2, it is the same
task with a differently weighted coin. Real difficulty would change *kind*: two
simultaneous changes, a change that reverts, a decoy that drifts suspiciously but
is legal, a "which detail changed?" recall check. Right now a skilled player and
a beginner do the identical activity; only the frequency of payoff differs.

### 4. The win screen is now the busiest screen in a minimalist game

Count what lives on the exit: three lines of win prose, a "look back" toggle that
expands to a fourth line, a share prompt, a randomly chosen invitation line, up
to four share buttons, and two action buttons. In a game whose entire aesthetic
argument is restraint, the *reward* screen is the one place that looks like a
landing page. It was tightened, and the fleeting fade helps, but the instinct to
put everything on the moment of victory is at odds with the taste on every other
screen. Consider earning the share with a second tap instead of showing it all at
once.

### 5. The all-or-nothing reset got *reinforced*, not reconsidered

Keeping the hard reset was the right call thematically, and the review agrees the
game should not go soft. But note what happened: the reset is now the only
punishing thing left in an experience that got friendlier everywhere else, which
makes it stick out more, not less. One wrong call still vaporizes three to eight
loops of careful attention with no checkpoint and no insurance. That is coherent
with the theme and hostile to the exact players the new share loop is trying to
recruit. At minimum it deserves an *optional* forgiving mode, kept out of the
canonical scoring, the way the shortcut build is kept non-canonical.

### 6. The "8" identity is a strong brand and a low ceiling

The number-8 identity is genuinely well executed now (card, favicon, title,
eight languages, eight loops). But it is also a box. Everything is "something 8",
and a one-note brand reads as clever the first time and as a gimmick the tenth.
What is arc nine called? The identity that is helping today will constrain the
catalogue tomorrow; decide now whether "8" is the game or just this season of it.

### 7. Breadth is outpacing depth, conspicuously

Twenty-one locales translated, eight exposed, a full QE gate, and behind all that
machinery sits roughly twenty minutes of distinct content across three arcs that
play identically. That is a beautifully engineered distribution layer wrapped
around a thin core. It is the same imbalance the first review flagged
(localization polished to a mirror shine), just now joined by sharing polished to
the same shine. Impressive engineering is being spent on getting more people to
the same short experience in more languages, rather than on making the experience
longer or deeper.

### 8. The new controls are visually right but a11y-unverified

The drawn sound icon and the corner language globe look correct and fixed the
mood complaints. But the share block, the "look back" toggle, and the corner
picker are new interactive surfaces, and there is no evidence in the repo that
they were checked for keyboard focus order, screen-reader labels, or the
`prefers-reduced-motion` case (the whole game leans on slow fades). Small serif
on near-black with timed fade-outs is a hostile combination for some users; the
contrast pass helped the text but the interaction layer has not had the same
audit.

### 9. Randomised share copy can undercut itself

One of eight invitation lines is chosen at random per win. That is nice for
variety, but it means the shared artifact is inconsistent, and a couple of the
eight are noticeably weaker/cryptic-to-the-point-of-opaque than the best two. A
first-time recipient who lands on a weak line gets a worse hook than one who lands
on the best. Either curate to the three strongest, or weight the selection.

### 10. Still no sound by default, so most of the craft is unheard

The procedural audio is a real achievement, and it is muted until a gesture and
easy to never turn on. The single most distinctive production asset is opt-in and
invisible on the screen that sells the game (the landing is silent until you
click). That is a lot of craft behind a door most players never open.

## If you fix only five things, in order

1. **Give the middle a second verb.** One additional kind of interaction inside
   the loop (a recall check, a two-change level, a manipulable detail) would do
   more for this game than anything on the edges. This is the whole ballgame.
2. **Add one reason to return.** A streak, a daily fixed seed ("today's 8"),
   arcs that unlock, or a depth ladder. Anything that makes visit two different
   from visit one, so the share loop has a bucket to fill.
3. **Escalate in kind, not just probability.** Introduce a genuinely new twist
   every couple of levels so level 8 feels different from level 2, not just rarer.
4. **Offer a forgiving mode (non-canonical).** Keep the hard reset as the true
   game, but give newcomers a streak-insurance or checkpoint option so the reset
   stops evicting the players you just invited. You already have the pattern for
   "non-canonical variant" in the shortcut build.
5. **Let the win screen breathe.** Progressive disclosure: show the ending, then
   reveal the share on a tap. Curate the invitation lines. The reward moment
   should feel like the calmest screen, not the fullest.

## Pull quote

> It used to be a clever idea with a broken front door. Now it is a clever idea
> in a beautifully wrapped box that opens, greets you, and says a graceful
> goodbye in eight languages, around a middle that is still one paragraph and two
> buttons. Stop decorating the entrance and the exit. Build the room.
