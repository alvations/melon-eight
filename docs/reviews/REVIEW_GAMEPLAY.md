<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Gameplay review: the mechanics, and nothing else

A third reviewer, brought in for one job: judge the **game**, not the package. I
do not care here about the art, the eight languages, the share card, the audio,
or the achievement icons, other reviews cover those and they cover them well. I
care about the decision the player makes, over and over, and whether it is a good
one: is it a real choice with skill in it, does mastering it feel like mastering
something, does it get harder in ways that demand more of the player, and do the
pieces (the loop, the doubt prompt, the touch layer, the endings, the collection)
form a system that talks to itself. I read the resolution code, then I played to
lose and played to win and watched what my own decisions were actually made of.

**Verdict: 6.5/10 as a game.** The core is a clean, honest, genuinely unusual
skill test with no exploit in it, and it is also almost the entire game, run at
one difficulty of *kind* from start to finish, with a second verb bolted
alongside it that never once feeds back in. What is here is well-made. There is
just not very much of it that is *mechanical*, and the parts that look like
systems (the doubt rating, the false exit, the collection) turn out, under the
hood, not to change the decision you are making. It plays like an excellent
prototype of one mechanic that has not yet been built into a game *of* mechanics.

## What is mechanically right

- **The truth is clean and unexploitable.** `correct = (choice == "back") ==
  has_anomaly`, resolved server-side, with the answer stripped from every
  payload. There is no page-inspection cheat, no tell in the DOM, no way to game
  it except by actually remembering. For a browser game about honesty with
  yourself, the integrity of the core is exactly right.
- **It is fair in the way that matters.** If the changed property would not have
  been described this loop, the build swaps it into the shown set
  (`hallway.py`), so you are never asked to catch a change you were structurally
  incapable of seeing. That single guard is the difference between a memory test
  and a coin flip, and the team got it right.
- **The skill it tests is real and uncommon.** Because the prose rotates through
  equivalent sentences and only four to six of eight properties appear each loop,
  you cannot diff text, you must hold the *meaning* of a place and compare
  against it. That is a legitimate cognitive skill and I have not played much
  that tests it this cleanly. Memory load is real and well-tuned.
- **The red herring is the best-designed mechanic in the game.** A sensory detail
  that reads as evidence and is deliberately uncorrelated with the truth (the
  poster is freshly printed; it means nothing) attacks the exact failure mode of
  the core skill, mistaking plausibility for change. That is a mechanic that
  makes the central decision *harder in kind*. There should be ten more like it.

## Where it falls down as a game

### 1. The one real decision has no in-game inputs
Everything you need to make the call lives in your biological memory and nowhere
on the screen. That is the concept, and I respect it, but mechanically it means
there is no *reasoning* in the moment, only *recall*. You cannot deduce, combine
partial clues, hedge, or reconstruct; you either remember or you don't, and then
you press. A great decision mechanic gives the player levers to think with. This
one gives them a yes/no and asks their hippocampus to do the rest. The ceiling on
skill expression is therefore your memory, flat, with no technique to develop on
top of it.

### 2. The "how certain are you?" prompt is not a mechanic
It looks like risk/reward, it is not. Confidence never enters the correctness
check; rating yourself *guessing* just buys one more look, and rating yourself
*certain* just commits. There is no bet, no stake, no cost to overconfidence and
no reward for calibrated doubt. This is the single biggest missed opportunity in
the design: a game *about* doubt has a doubt button that does not do anything to
your outcome. Make certainty a wager, more progress for a confident correct
call, a steeper fall for a confident wrong one, and you would turn a pacing
speed-bump into the game's second real decision.

### 3. Difficulty changes the odds, never the task
From level 1 to level 8 exactly one thing moves: `anomaly_chance`, ~0.18 up to a
0.55 cap. The *decision* is identical at every depth; only the base rate shifts.
Worse, that shift is meta-gameable, a player who knows later loops are likelier
to have changed can lean on the base rate instead of their memory, which subtly
*rewards knowing the ramp over playing the game*. Difficulty should add kinds of
problem: two simultaneous changes, a change that reverts to baseline a loop
later, a decoy property that legally drifts every loop so it is always suspicious
and never wrong, a "name the property that changed" confirmation. The engine
already picks a property and a value; several of these are days of work, not
rewrites.

### 4. The second verb never touches the first
Touching the room (Act 2) is explicitly walled off from the go-on/turn-back
resolution, on purpose. As a systems critic that wall is the problem: two verbs
that never interact are not a system, they are two features sharing a screen. The
collection now pays you to touch, so you touch, get lore, and make the *same
untouched decision*. Imagine instead one arc where a touch legally reveals one
property's history ("this was blue last loop") at a cost, now the two verbs are
in tension and every touch is a real trade. As shipped, the touch is content
delivery, not play.

### 5. The false exit is a blind gamble dressed as a secret
The alternate endings are reached by taking a rare tempting exit, but the player
has no information about whether it is real, so taking it is not a *decision*, it
is pressing an unmarked button and seeing what happens. Discovering the ending
once is a nice surprise; there is no skill in it, nothing to read, nothing to
weigh, and no reason to ever take it twice except to tick the badge. A secret
that rewards guessing rather than noticing is at odds with a game whose whole
skill is noticing.

### 6. The fold is a random event, not a risk you manage
The fold (a touch that resets you) fires on an RNG roll weighted by depth, not on
anything the player reads or controls. You cannot see it coming, cannot play
around it, cannot trade for it. Mechanically it is a tax on the exact behaviour
the collection is paying you to do, the game hands you a reason to touch and a
random punishment for touching, and neither is legible to the other. Pick one:
make touching safe and purely rewarding, or make the fold a readable risk the
player chooses to run.

### 7. The collection measures participation, not mastery
Most badges are attendance: escape once, escape all three, play eight times, find
the fragments. Only "flawless" (a clean run) rewards *playing well*. There is no
accuracy score, no close-call meter, no measure of how good your reads were, 
nothing that lets a strong player see, or a weak player chase, actual mastery. A
game with a skill this clean should surface a skill signal. Right now winning and
barely-winning look identical on the board.

### 8. There is no mastery arc
Once you have internalised "remember the meaning, watch for the one change, don't
trust plausibility," you have learned the whole game; deeper play is the same
skill under more repetitions, not a laddder of new techniques, tells, or reads.
Expert play differs from novice play only in memory quality and calm. There is no
strategic layer to grow into, which is why a session ends when your attention
does, not when you have hit a wall you want to beat.

## If I were fixing the game, in order

1. **Make certainty a wager.** Tie the confidence rating to the stakes, bigger
  step for a confident correct call, harder fall for a confident wrong one. This
  turns the doubt theme into a doubt *mechanic* and gives the loop its second
  real decision for almost no new content.
2. **Escalate in kind.** Ship two or three new anomaly *types* (double change,
  revert, legal decoy, confirm-the-property) and roll them in by depth so level
  8 is a different problem, not a rarer one.
3. **Let one verb cost the other.** In at least one arc, make a touch trade real
  information for a real price, so Act 2 finally feeds Act 1.
4. **Reward the read, not the guess.** Give the false exit and the fold a
  readable tell, so taking or avoiding them is a decision with skill in it.
5. **Score mastery, not attendance.** Track and surface read accuracy / close
  calls; give the strong player something to perfect and the board something to
  measure beyond "showed up."

## One line

> Underneath everything is one clean, honest, unusually good decision, and the
> game has built a museum around it without ever giving it a second decision to
> talk to. Fix the doubt button so doubt costs something, make the difficulty
> change the question instead of the odds, and let the two verbs finally touch.
> The mechanic deserves to be a game.
