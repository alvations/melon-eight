# Arc roadmap

This is the living plan for the game's arcs (skins/backstories). It records the
design rules every arc must follow, what's already built, and the queue of
future arcs so we can pick up any of them later without re-deriving the idea.

Each arc is one self-contained `data/arcs/<id>.json` file plus a
`body[data-skin="<name>"]` block in `static/style.css`. See the README section
*Adding an arc* for the file schema. New arcs appear on the opening screen
automatically.

The content and writing (the properties, the rotating prose pools, the intro and
win text, the NPC, the `sense` layer) are **authored by the agent as JSON**, then
validated by the deterministic test suite. There is no content API or generator
service, so a developer running Claude Code with any local or hosted model can
write a new arc the same way we did: describe the place, have the model fill the
JSON to this schema, and let the tests confirm it loads and stays fair. See
`docs/REPRODUCE.md` (the "every kind of content" table) for the full picture.

---

## Design rules (apply to every arc)

The mechanic is fixed: move through a place that should be identical each loop;
**turn back** if something changed, **go on** if nothing did; eight correct
calls in a row wins, one wrong call resets. What differs per arc is the story,
vocabulary, skin, and the *flavour* of the anomalies. Every arc must include:

1. **A strong motivation ("the hook").** A concrete in-world reason you're stuck
   doing this, revealed in the intro, the equivalent of Stairway 8's
   out-of-order elevator. Never "you are being tested" with no diegetic cause.
2. **An NPC.** A recurring character that is normally passive but can become the
   anomaly, turning, watching, approaching, vanishing, duplicating. Every arc
   needs its own recurring uncanny figure.
3. **A loop-aware NPC twist.** At least one NPC anomaly that breaks past physical
   change into the uncanny: the character *acknowledges you* or the loop itself
   (waves, beckons, mouths/says "again"). Property key convention: `knows` for
   silent figures, `speaks` for ones that can talk.
4. **A psychological layer (`sense`).** A non-physical property whose baseline is
   your ordinary state and whose anomalies are perceptual/emotional wrongness, 
   losing count, a calm that shouldn't be there, a conviction you're going the
   wrong way. Anomalies beyond objects, per the "twists" requirement.
5. **Meta drift (free).** The engine already drifts the heading, wording, pacing,
   weight, spacing and background every loop, no per-arc work needed, but keep
   `title_variants` themed.
6. **Win-screen strings (in `meta`).** Three short, arc-flavoured lines the exit
   screen needs, so the reward matches the place:
   - `share_prompt`: the invitation above the share row, phrased for this arc's
     exit (Hallway: *Leave the door open.*, Stairway: *Leave the door open
     below.*, Coach: *Hold the doors.*).
   - `attempt`: the "look back" line shown when the run took more than one try.
     **Must contain the `{n}` placeholder** (the run count), spliced in front so
     it localizes cleanly, e.g. *{n} times down this corridor, and this time it
     opened.*
   - `attempt_first`: the line for a clean first run (no placeholder), a small
     reward for a flawless escape, e.g. *First time through, and the corridor let
     you go.*

Keep anomalies *plausible*, never loud. One property mutates per anomalous loop,
and it is always among the details shown that loop (the engine guarantees this).

---

## Shared tuning (all arcs inherit this, do not re-tune per arc)

These curves are engine-wide, not per-arc. A new arc gets them for free; only
change them if you intend to change the feel of *every* arc.

### Difficulty ramp, `hallway.py`

The chance a loop contains an anomaly is a function of the player's level, so the
first stage after entering leans toward "nothing changed" (learn the baseline by
proceeding) and gets harder as you descend/advance:

```
anomaly_chance(level) = min(ANOMALY_MAX, ANOMALY_BASE + ANOMALY_STEP * level)
ANOMALY_BASE = 0.02   # level 0: VERY low, no baseline seen yet
ANOMALY_STEP = 0.076  # per level cleared (steep, to reach the cap by ~L7)
ANOMALY_MAX  = 0.55   # capped so "always turn back" never wins
```

So the opening loop (level 0) is only ~2% (easy 1%, hard 3%), rising steeply to
the cap by around level 7 (normal 55%, easy 30%, hard 60%). The very-low opening
is deliberate: on your first loop you have no baseline, so being turned back
would be a coin flip you cannot win. It is not zero (a rare early jolt keeps the
place honest). Level resets to 0 on a wrong call, which re-eases the first stage,
intentional re-onboarding, not a bug. There is no level-0 floor (the low opening
is the point; levels 1+ ramp well clear of zero so "always continue" still
loses). Because content is *shown* fairly (the mutated property is always among
the details displayed), the ramp changes frequency, never fairness. Guard: keep
`ANOMALY_MAX ≤ ~0.55` or turning back becomes dominant.

### Aggro-item / late reveal (`hallway.py`)

Each arc's `meta.late_props` names a couple of small, inconspicuous properties
(existing details, not new ones). Once per climb, `build()` may **hold some out**
of the early loops so they first surface mid-run. `mem.held` maps each held prop
to its reveal level:

```
reveal level ∈ [2, GOAL-2]   # ~level 2-6 at goal 8, never the last
hold: hard  → always, 1 or 2 items (the "not everything up front" pressure)
      normal → rare (~15%), a single item; rotation is the everyday replay hook
      easy  → never
```

Holding 1-2 items reliably is a **hard-mode** feature. Normal mode leans on the
ordinary fact that only 4-6 of ~9 details show each loop (and Act 2 touch
outcomes vary), so a normal player meets almost every encounter over a few runs
without ever being deliberately starved. Not showing everything every run is a
core principle and the replay hook.

Fairness guard (`mem.seen_props`): an anomaly may only land on a detail the
player has already seen at **baseline on an earlier loop**, so the held item is
never the change on the loop it first appears. Its debut is always a calm
baseline; only later can it move. This keeps a late arrival a memory test, never
pure luck, even at the last level (by then it is long established). Pick
`late_props` that are genuinely minor (a fixture, a small object), never the NPC
or the `sense`.

### Doubt prompt curve, `static/game.js`

The confidence prompt is not shown every turn. After a Go-on/Turn-back choice,
the chance it interrupts grows as you near the exit:

```
chance = min(0.85, 0.12 + level * (0.7 / goal))     # ~12% early → ~73% at level 7
```

- **Certain / Almost sure** (conf ≥ 3) → the choice commits and is judged.
- **Guessing / I think so** (conf ≤ 2) → does *not* commit; returns you to the
  scene for exactly **one** re-decide (the `hesitated` flag blocks a second
  prompt that turn). The re-look is the only "reward", no points, no safety net.

This is pure client-side UX: confidence never enters the server's correctness
formula (`correct = (choice == "back") == has_anomaly`). New arcs need no work to
inherit it.

### Session state, `app.py`

State is keyed by a client-echoed `sid` (X-Sid header), **not** the session
cookie, so an arc and its progress survive in a cross-site iframe (Spaces). Arcs
never need to touch this.

### Win screen & sharing, engine-wide

The exit screen is shared by every arc; an arc only fills in the three `meta`
strings above. The engine handles the rest:

- **Look back (fleeting run count).** A quiet toggle under "You're out." surfaces
  the arc's `attempt` / `attempt_first` line, then fades after a few seconds and
  reclaims its space so the eye settles on sharing or replaying. The run count is
  a per-session counter in `PlayerMemory` (`attempts`, resets + 1), and the line
  is localized server-side like win text.
- **Sharing.** One of eight cryptic "invitation" lines (shared UI strings
  `share_1..8`) is chosen at random, with the arc's `share_prompt` above it.
  Mobile-first: where a native share sheet exists it is the single button (it
  reaches Instagram, Snapchat, X, Messages, everything); otherwise explicit X /
  Facebook / LinkedIn links plus Copy link. The shared URL unfurls as the game's
  own "8" Open Graph card (`static/img/og.png`).

New arcs inherit all of this for free once the three `meta` strings are set.

---

## Built

*These three are the only production arcs for the current phase. Everything in
"Planned", "Backlog", and "Brainstorm" below is idea-stage only, keep it out of
the live 3-arc game until an idea is deliberately promoted up into this table.*

| Arc | Hook | Loop unit | NPC (+ twist) | `sense` anomalies | Skin |
|-----|------|-----------|---------------|-------------------|------|
| **Hallway 8** (`hallway-eight`) | Locked in after hours; a sign points to the fire exit | corridor | man in grey suit (`knows`: turns/beckons/"again") | longer, forget, calm | cold teal |
| **Stairway 8** (`stairway8`) | Elevator out of order; descend on foot | landing | figure on the stairs below (`knows`: looks up, waves, ascends) | deeper, forget, wrong-way | emergency green |
| **Coach 8** (`coach8`) | Conductor sent you to coach 8; the train never reaches it | carriage | sleeping passenger (`speaks`: murmurs "again", "you were just here") | forget, calm, watched | cabin amber |

---

## Planned (not yet built)

Each entry is enough to implement directly. Ordered by how strong/fresh the loop
feels; pick any.

### Platform 8 (`platform8`), the underpass
- **Hook:** last train of the night; the turnstiles are shut and a sign routes
  you through the pedestrian underpass, FOLLOW SIGNS TO PLATFORM 8.
- **Loop unit:** identical tiled underpass segments. **Go on** = walk on /
  **Turn back** = double back.
- **NPC:** a busker sitting against the wall with an open case. Twist (`knows`):
  stops playing to watch you; case is suddenly empty/overfull; plays the same
  bar as you pass "again."
- **Physical anomalies:** tiled advert, the drip-puddle, map's "YOU ARE HERE"
  dot, poster date, platform number on the sign, tile colour, a pigeon.
- **`sense`:** the tunnel feels longer; you forget which platform you wanted; a
  certainty you already caught the train.
- **Skin:** cold blue-white station tile (`--hue: 205`).

### Aisle 8 (`aisle8`), locked in the supermarket
- **Hook:** you looked up and the shop had closed around you; the tannoy loops
  "please proceed to checkout 8 to exit."
- **Loop unit:** identical grocery aisles. **Go on** = next aisle / **Turn
  back** = previous aisle.
- **NPC:** a night-shift stocker with a trolley, back to you. Twist (`knows`):
  turns and stares; trolley abandoned mid-aisle; softly says "again" over the
  muzak.
- **Physical anomalies:** a shelf gap, a product facing the wrong way, a price
  label, the end-cap promo, the muzak track, the abandoned trolley, floor sheen.
- **`sense`:** the aisle feels longer; you forget your list; a calm certainty
  you've already paid.
- **Skin:** flat retail fluorescent, a touch too bright (`--hue: 60`, high L).

### Ward 8 (`ward8`), the hospital at night
- **Hook:** visiting hours are over; the night sign says the way out is via Ward
  8. *(Handle tone with care, dread, not gore.)*
- **Loop unit:** identical hospital corridors. **Go on** / **Turn back**.
- **NPC:** a patient in a gown standing in a doorway, or a nurse at the far
  station. Twist (`knows`): the figure has moved to the next doorway; is facing
  you; mouths "again."
- **Physical anomalies:** a gurney's position, the room-number plate, a
  flickering "NIL BY MOUTH" sign, the hand-gel dispenser, a chart on a door,
  distant monitor beeps, a wheelchair.
- **`sense`:** the corridor feels longer; you forget why you came; a wrong calm.
- **Skin:** pale clinical green-grey (`--hue: 160`, low sat).

### Level 8 (`level8`), the underground car park
- **Hook:** your ticket says Level 8; the lift to the street is dead, so follow
  the ramp up. (Ascending mirror of Stairway 8.)
- **Loop unit:** identical parking rows. **Go on** = up a ramp / **Turn back** =
  back down.
- **NPC:** a figure between the parked cars, or someone sitting in a driver's
  seat. Twist (`knows`): the seated figure's headlights flick on as you pass; it
  has moved cars; it waves.
- **Physical anomalies:** a parked car's colour, the level number on the pillar,
  a flickering strip light, the arrow painted on the floor, an oil stain, a
  distant engine, a car alarm.
- **`sense`:** the level feels deeper; you forget where you parked; certainty
  you're descending, not climbing.
- **Skin:** concrete grey with sodium-orange pools (`--hue: 30`, low L).

### Gate 8 (`gate8`), the airport after the last flight
- **Hook:** you dozed off; the terminal's near-empty and the board shows one
  route left, EXIT VIA GATE 8.
- **Loop unit:** identical concourse stretches / travelators. **Go on** /
  **Turn back**.
- **NPC:** a lone cleaner with a floor-buffer, or a single seated passenger.
  Twist (`knows`): stops buffing to watch; the seated passenger is gone/closer;
  a gate announcement says your name.
- **Physical anomalies:** the gate number, a departures-board row, the duty-free
  window display, an abandoned bag (unsettling), the announcement chime, a clock,
  a potted plant.
- **`sense`:** the concourse feels longer; you forget your destination; a calm
  that you've already boarded.
- **Skin:** glassy blue night-terminal (`--hue: 215`).

---

## Backlog ideas (thin, flesh out before building)

- **Museum after close**: galleries loop; NPC is a security guard or a statue
  that isn't always in the same pose.
- **Motel corridor**: reach room 8 / the exit; NPC is someone at an ice machine.
- **Ferry decks**: climb decks to the exit; NPC a lone smoker at the rail;
  motion + sea outside the windows.

---

## Brainstorm, later phases (idea-stage, NOT production)

Fresh settings that complement the transit/civic bias of the Planned queue: a
knowledge space, a money/dread space, a modern-tech space, a sacred space, and a
play-gone-wrong space, five different emotional registers, still melancholy
rather than violent. Each satisfies the design rules (hook, loop unit, NPC with
a loop-aware twist, physical anomalies, a `sense` property). Suggested skin hues
are candidates only; whichever get built must stay visually distinct from the
live blue/amber/green and from each other.

### Stacks 8 (`stacks8`), the library at lockup
- **Hook:** the lights dropped to night mode while you read; a card says the way
  out is past Aisle 8 of the stacks.
- **Loop unit:** identical rows of tall shelving. **Go on** = next aisle /
  **Turn back**.
- **NPC:** a night librarian re-shelving from a trolley, back to you. Twist
  (`knows`): stops, turns to watch, mouths "again". Or a reader asleep at a
  carrel (`speaks`: "you already returned it").
- **Physical anomalies:** a book's spine title, a shelf gap, a volume shelved
  upside-down or backwards, the aisle-number sign, a reading lamp on/off, the
  step-stool moved.
- **`sense`:** the aisle feels longer; you forget which book you came for; a
  wrong calm that you've already checked out.
- **Skin:** violet dusk through high windows (`--hue: ~275`). Books are an
  unusually strong anomaly engine, probably the richest of these five.

### Vault 8 (`vault8`), the bank vault, timelock running down
- **Hook:** your safe-deposit box is in aisle 8; the outer door is on a timelock
  that reopens at dawn, so keep going.
- **Loop unit:** identical corridors of numbered brass boxes. **Go on** /
  **Turn back**.
- **NPC:** a night guard on his rounds (`knows`: stops, watches, nearer) or a
  customer at an open box who won't leave (`speaks`: "you were just here").
- **Physical anomalies:** a box number, a box door ajar, a dropped key on the
  runner, the timelock clock's hands, the carpet runner's colour, a convex
  security mirror's angle.
- **`sense`:** the vault feels deeper; you forget your box number; a calm that
  you've already emptied it; wrong-way.
- **Skin:** crimson carpet + burnished brass (`--hue: ~350`).

### Data Hall 8 (`datahall8`), the data-centre cold aisle at 3am
- **Hook:** the badge reader sent you to Hall 8 to reseat a server; the lift back
  is locked to your card, so walk the aisle.
- **Loop unit:** identical rows of caged server racks. **Go on** / **Turn back**.
- **NPC:** a lone technician with a laptop cart far down the aisle (`knows`:
  turns, watches, closer), very modern loneliness.
- **Physical anomalies:** a rack's blinking-LED count, a cage door ajar, a coiled
  cable on the floor, a KVM screen showing your own login, a warm aisle where it
  should be cold, the hum's pitch.
- **`sense`:** the hall feels longer; you forget which rack; the hum stops (a
  diegetic "wrong silence"); a wrong calm.
- **Skin:** indigo LED wash (`--hue: ~265`). The only contemporary/tech setting.

### Cloister 8 (`cloister8`), the abbey at night
- **Hook:** locked in after the last visitors; complete the eighth circuit of the
  cloister to reach the chapel door.
- **Loop unit:** identical vaulted arcades around a dark garth. **Go on** /
  **Turn back**.
- **NPC:** a cowled figure with a taper at the far arcade (`knows`: turns, raises
  a hand, nearer each loop, mouths "again").
- **Physical anomalies:** a wall sconce lit/dark, a carved boss or gargoyle, a
  statue's pose out in the garth, a grave-slab inscription underfoot, the bell
  (tolls once too many), a stained-glass panel.
- **`sense`:** the walk feels longer; you forget which office you came to pray; a
  wrong serenity; wrong-way (the cloister circles anticlockwise now).
- **Skin:** candle-lit stone, very low saturation warm grey (`--hue: ~35`,
  desaturated so it reads neutral, not Coach's amber).

### Midway 8 (`midway8`), the shuttered funfair
- **Hook:** you stayed past closing; the only lit exit sign is down the midway,
  past booth 8.
- **Loop unit:** identical stretches of game stalls and strung bulbs. **Go on** /
  **Turn back**.
- **NPC:** a costumed mascot standing dead still by a stall. Twist (`knows`): it
  has turned to face you; it's closer; its head is tilted. (Unsettling without
  gore.)
- **Physical anomalies:** a prize wall, a strung bulb dark/lit, a carousel
  horse's position, a ticket-booth number, the calliope music (loops backward),
  a balloon snagged on a wire.
- **`sense`:** the midway feels longer; you forget which ride you were heading
  to; a wrong festive calm; wrong-way.
- **Skin:** faded pink-and-gold neon (`--hue: ~320`).
