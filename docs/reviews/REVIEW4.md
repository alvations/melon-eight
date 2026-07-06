<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Critical review, fourth pass

The same deliberately harsh but impartial reviewer, back for a fourth look.
`docs/REVIEW.md` (6/10), `docs/REVIEW2.md` (7/10), and `docs/REVIEW3.md`
(7.5/10) are the prior record and stay untouched. Same method: read the code and
the arc content, play the running build, look at the actual screens (landing,
corridor, the touch layer, all three win screens, the new collection page, the
settings, mobile). The headline change this round is the **collection**:
achievements, a flashback ledger you can fill and recall, save/load, promo
codes. That is, almost line for line, the number-one fix I asked for last time
("make the touch pay off... a visible collection that turns curiosity into a
rewarded habit"). So the pointed question is: did giving the flashbacks a home
turn Act 2 from a mood option into a mechanic, or did it just add a fifth
beautifully made thing on the edge of the game?

**Verdict: 8/10, up half a point.** The team did the thing I asked, and did it
with taste. The flashbacks are collected and recallable, the endings and clean
runs are badges worth chasing, the reset is finally explained in the moment,
the type can be made legible, and the sound is on when you arrive. Every
individual complaint from the cold read has a real answer now. The reason it is
8 and not higher is that all of this is still **meta-progression wrapped around
an unchanged core**. The collection gives you reasons to *re-enter* the loop; it
does not change what the loop *is*. Level 8 is still level 2 with a heavier coin,
the second verb is still one you can ignore, and there are still three places.
The game got a memory. It did not get a deeper present tense.

## What actually improved

- **The flashbacks finally add up to something.** This was the crux of the last
  review and it landed. A fragment you touch fills a dot, and you can tap it to
  hear its words again; seeing them all is a badge. The best writing in the game
  now has a place to live and a reason to be hunted. That is the correct fix,
  executed cleanly.
- **The badges are honest and legible.** Sixteen earned by play, drawn as line
  glyphs in the game's own hand, locked ones a plain padlock, descriptions that
  name the feat without spoiling the detail to watch. The one full-colour
  watermelon for the studio-supporter badge is a genuinely charming exception
  that proves the rule. This is restrained achievement design, not a Steam
  checklist.
- **The gotchas got explained.** The fold now tells you *you* did that, with an
  opt-out from the second time; the false exit is common enough (raised to the
  last third of a run) to actually be found; the reset is taught on first
  occurrence. Three separate "the game feels broken" complaints from the cold
  read are answered in-world, without softening anything.
- **The accessibility and sound gaps closed.** A settings gear does text size,
  brightness, and reduce-motion, defaulting to the current look; the soundscape
  starts on load. The single most-hidden pieces of craft (legible text, the
  audio) are now reachable without spelunking.

## The criticisms

### 1. The collection is retention *machinery*, not retention

I asked for a reason to return, and strictly speaking there now is one: badges
to complete. But every badge is a **finite, one-time** unlock. Escape each arc,
escape all three, a clean run, eight runs, three endings, all the fragments, 
it is a checklist with a bottom. There is still no *renewable* reason to come
back tomorrow: no daily seed, no streak, no ladder, nothing that makes visit six
different from visit five once the list is done. This buys a completionist a few
extra sessions and then empties exactly as the share loop did. A finite
collection is a longer bucket, not a bottom for it.

### 2. You rewarded touching the room without making touching the room matter

The flashback ledger is a real pull to touch details, but touching still has no
bearing on the go-on/turn-back call, which is the actual game. So the collection
motivates a behaviour that runs *parallel* to the mechanic rather than *into* it.
A curious player now touches everything for the codex, gets their flashback, and
then makes the same binary decision they always did. The verb got a reward; it
still did not get consequence inside the loop. (To be clear, this is a design
axiom the team has stated on purpose, touches never move the win logic, so I am
not calling it a bug. I am saying the axiom caps how much the collection can ever
deepen the *core*, as opposed to the *around*.)

### 3. Act 1 is still a single probability dial (fourth time)

I have flagged this three reviews running and it remains the truest thing I can
say about the game. The escalation from level 1 to level 8 is still one number,
`anomaly_chance`, drifting from ~0.18 to a 0.55 cap. No second simultaneous
change, no change that reverts, no legal-but-suspicious decoy, no "which detail
moved?" recall check. A collection cannot fix this because it lives outside the
loop. The deep levels are rarer, not harder-in-kind, and a game about escalating
doubt should escalate the *kind* of doubt.

### 4. Save/load is theatre in a game with nothing to protect

There is now an obfuscated save file with a keystream XOR "seeded with a phrase
the player never sees." The code comments are honest that this is not real
crypto, good, but step back and ask what it is *for*. The collection is local,
unscored, and worth nothing to anyone but the player; there is no leaderboard to
cheat, no economy to protect. So the obfuscation guards a thing that does not
need guarding, and the export/import mostly serves moving progress between your
own devices, which a plain JSON would do just as well and more debuggably.
Effort spent making the save unreadable is effort the core loop did not get.

### 5. The promo-code system is infrastructure for a game that isn't there yet

An 8-character redeem engine that can unlock languages and, "in the future,"
arcs and features (DLC). That is a storefront built before there is anything to
sell. Today it does two things (a studio badge, a language unlock), and one of
those, gating an already-translated language behind a code, actively *hides*
finished content from players for no player-facing benefit. This is the
breadth-over-depth pattern in a new costume: building the commerce layer for
content that does not exist instead of the content.

### 6. Seventeen badges over twenty minutes of distinct play

The ratio the last three reviews kept naming is now starker, not softer. There
are seventeen achievements, a fragment codex per arc, save/load, and a promo
economy, wrapped around the same three arcs and the same ~twenty minutes of
mechanically-distinct content. The meta-game is now more elaborate than the game.
A completion board implies there is a lot to complete; here the board is the
larger artifact.

### 7. The one intentional colour break is a tell

The full-colour watermelon among the monochrome glyphs is charming, and I called
it out as a positive, but it is also the studio winking at itself on the
achievement wall. In a game whose entire aesthetic argument is disciplined
restraint, the single loudest pixel on the collection screen is the *maker's own
badge*. It is a small thing, but taste is made of small things, and this one puts
the studio's logo in colour above the player's actual accomplishments in grey.

### 8. Discovery still depends on the player poking a wall

The collection rewards touching, but nothing teaches a new player that touching
is worth doing, and the cold read's "I clicked them, they did nothing, I
stopped" risk is only partly addressed: the payoff (a filled dot on a page you
have to know to open) is quieter than the thing that taught them to stop
(nothing happening in the loop). The reward exists; its *visibility at the moment
of the first few touches* still trails the discouragement.

## If you fix only five things, in order

1. **Give the loop a renewable reason to exist.** A daily fixed seed ("today's
  8") or a streak is a day of work and finally puts a bottom in the bucket the
  share loop and the collection both pour into. This is now the number-one gap.
2. **Escalate Act 1 in kind.** Two changes, a revert, a legal decoy, a recall
  check, anything that makes level 8 a *different* task. Four reviews, one ask.
3. **Make one touch matter inside the loop, once.** Not always, that would break
  the axiom, but a single arc mechanic where a touch legally informs (or costs)
  the call would connect the second verb to the first. Right now they never meet.
4. **Cut the store you can't stock.** Drop the promo-gated languages (ship them),
  and hold the DLC plumbing until there is DLC. Build the fourth arc instead.
5. **Widen.** A fourth and fifth place would do more than a third pass on the
  meta-layer. You have an engine and a collection frame begging for more content
  to hang on it. Feed them.

## Pull quote

> I asked it to reward curiosity and it built a beautiful cabinet to keep the
> rewards in. Now the game remembers everything you did and still asks you to do
> the same thing to fill the shelf. Four visits in, the frame around the loop is
> exquisite and the loop is unchanged. Stop building rooms to display the game
> and put a second verb, a second difficulty, and a fourth place *in* it.
