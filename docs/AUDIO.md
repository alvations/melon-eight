<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Audio: how the sound is made, added, and kept in balance

All sound in **8** is **synthesised live in the browser** with the Web Audio API
(`static/audio.js`). There are **no audio files and no external assets** shipped
for gameplay: every arc's ambience and every movement effect is built from
oscillators and filtered noise at runtime. (The one rendered file, a ~42s OGG of
the landing theme, is optional and produced offline from the *same* synth, see
below.) This doc is the whole pipeline: the design intent, how a soundscape is
built, how the SFX are added, how everything is kept at one level, and how to
reproduce and measure it.

There is no machine-learning or prompt-to-audio step. The "prompt" is the design
brief in prose (room tone, not music, not eerie stings); the implementation is
hand-written synthesis. That keeps it tiny, dependency-free, offline, and exactly
reproducible.

## The mental model

`window.ambience` is a single `Ambience` instance. It owns one `AudioContext`, a
`master` gain (the mute toggle rides this), and a per-scene `bus` gain.

- **BGM (room tone)** is built by a per-skin builder `_<skin>(bus)` and connects
  to the `bus`. `play(skin)` tears down the previous scene and routes to the
  right builder (`_hallway`, `_coach`, `_stairway`, or `_landing`).
- **SFX (movement)** are one-shots (`step`, `run`, `_footstep`, `_swish`) that
  connect **straight to `master`**, bypassing the `bus`. This separation is what
  lets the BGM be lifted under the SFX without also lifting the SFX.

```
oscillators / filtered noise  -> _<skin>(bus) -> bus (per-arc level) --\
                                                                        >- master (mute) -> destination
footstep / swish / run one-shots ------------------------------------ /
```

## Per-arc soundscapes (BGM)

Each arc is room tone with its own identity, kept sparse:

- **hallway** = mains hum (120Hz + harmonic) + a faint high whine + low-passed
  ventilation noise; an occasional soft flicker (hum dip + crackle).
- **coach** = a low rumble (noise through a low-pass) + an airy mid roll + a very
  slow sway, plus **steady soft rail-joint clacks** (its identity, so it does not
  sound like the stairwell), and occasional events: a lurch and a passing train.
- **stairway** = near silence: low room tone + a concrete-shaft hum + reverb
  space + a **soft distant extractor-fan drone** (so the two low arcs differ),
  with an occasional wind gust.
- **landing** (select screen) = a slow, muted vi-IV-I-V arpeggio, wistful, never
  epic or eerie. This is the **reference level** everything else is matched to.

Occasional events (flicker, lurch, train, wind) are scheduled with
`_every(minMs, maxMs, fn)`. They are tuned to land about **once every 30 seconds**
(`_every(22000, 40000, ...)`), so a normal climb actually meets them.

`play(skin)` starts on entering a loop (or `"landing"` on the select screen) and
stops/rebuilds on transitions.

## Movement SFX

Committing a choice plays `ambience.step(dir, dwellMs, confidence)`: a footstep
(low thud + a filtered-noise scuff) plus a directional scene-change swish. A
confidence score (0..1) derived from how long the player lingered (and any
explicit certainty rating) picks firm steps + swish, a lighter tiptoe, or a near
silent shuffle. After the result, `ambience.run(dir)` may add a hurried flurry
(used sparingly, mostly when the player turned back on a real change).

## Level-matching (keep it this way)

The room-tone beds are set with a **per-arc `BUS` map** in `play()`, originally
derived by measuring each bed's loudness (RMS) against the landing theme. Hallway
and stairway sit near the landing theme; **coach is deliberately the quietest bed**
(`BUS.coach = 0.8`, an almost-empty-subway hush, well below landing) by owner
preference, not a measured match. The movement SFX are left at their natural level
(a firm footstep is meant to sit a little above the room tone); only the beds are
calibrated. These values are **derived from measurement, not guessed.** If you
retune a bed, re-measure so the arcs stay matched to landing.

## Why the action SFX sit ABOVE the BGM (do not RMS-match them)

This is a lesson worth keeping, because it is an easy mistake to make from numbers
alone. **The footsteps are deliberately louder than the room tone, and they must
stay that way.** They were tuned by ear after player testing; a later "just match
the levels" pass trimmed them to sit at the BGM's intensity, and it was wrong.
Here is the reasoning, both the design intent and the measurement that backs it.

**Design intent.** A footstep is *feedback for the player's own action*. It has to
land as a discrete, tactile event the instant a choice is committed, or the move
feels weightless and the game feels unresponsive. The BGM is the opposite: ambient
room tone that should sit *under* attention. Foreground event feedback and
background ambience have different jobs, so they belong at different levels. An
action that only matches the bed does not read as an action.

**Why matching them by number is a category error.** BGM is a *steady-state*
signal; an SFX is a *transient*. Measure both (`scripts/measure_audio.cjs`) and the
difference is stark. Representative figures from this build:

| Sound | peak | RMS (avg energy) | crest factor (peak / RMS) |
|-------|------|------------------|---------------------------|
| hallway bed | ~0.11 | ~0.036 | ~3.1 |
| stairway bed | ~0.10 | ~0.037 | ~2.9 |
| landing theme | ~0.19 | ~0.037 | ~5.2 |
| footstep (commit) | ~0.42 | ~0.043 | ~10 |
| turn-back step | ~0.43 | ~0.040 | ~11 |

Read the last column. The footstep's **average energy (RMS) is about the same as
the room tone** (~0.04 either way), yet its **peak is 2 to 4 times higher**
(~0.42 vs a bed peak of ~0.10-0.19). That high **crest factor** (~10 for a step
versus ~3 for a steady bed) is the whole point: the ear registers a discrete event
by its onset transient and peak, not by its averaged energy. The footstep does not
carry more energy than the bed, it carries a sharper *spike*, and the spike is what
says "a step happened."

So a "recalibration" that pulls the footstep's peak down to the bed's peak (which a
naive RMS/peak-match does) collapses exactly the crest that makes the action
tactile. Numerically it looks balanced; perceptually the step vanishes into the
wash. The peak is not overshoot to be trimmed, it is the signal.

Reproduce this exact comparison (peak, RMS, and crest for every bed and the
footsteps, plus a pass/warn verdict on whether the action still sits above the
bed):

```bash
node scripts/measure_sfx_vs_bgm.cjs
```

Its header carries the full logic; run it after any SFX change to confirm you have
not over-trimmed the action back into the bed.

**The rule for agents.** Level-match the *beds* to each other and to the landing
theme (steady vs steady, by RMS, which the `BUS` map does). Do **not** fold the
action SFX into that match. Judge an SFX by whether the action reads as tactile
above the bed (player testing decides), not by matching its number to the BGM.
When in doubt, a committed-action sound should peak clearly above the room tone;
here that is roughly a 2x-or-more peak ratio over the bed, with a crest factor
several times the bed's. If you retune SFX, confirm by ear, not by RMS.

## Measuring / reproducing the balance

`scripts/measure_audio.cjs` loads `audio.js` in a blank headless-Chromium page
(no server needed), plays each skin, taps the master output, and reports RMS,
peak, and spectral centroid:

```bash
node scripts/measure_audio.cjs          # BGM (arcs vs landing) then SFX
node scripts/measure_audio.cjs --bgm    # just the beds
node scripts/measure_audio.cjs --sfx    # just the footstep/swish peaks
```

Read it like this: the three arcs should sit near the landing theme's RMS, each
with a **distinct centroid** (so they do not sound alike), and the footstep peak
should sit near the landing peak, not far above it. Chromium/Playwright are
resolved like `tests/emulation.cjs`; override with `H8_CHROMIUM` / `PW_PATH`.

`tests/test_audio.py` guards the wiring statically (every arc has a builder,
`play()` routes each skin, the landing theme exists, the `BUS` level-match is
present, `unlock()` exists, and the rare-event cadence is about 30s). Run it with
the rest: `python tests/test_game.py`.

## Rendering / auditioning the sound to a file

`static/audio.js` is the generator (edit it to change a sound);
`scripts/render_audio.cjs` is the way to **hear** the result outside the browser.
It captures any arc's bed or the movement SFX in real time (so the scheduled
events are included) to a WebM Opus file:

```bash
node scripts/render_audio.cjs coach 30      # 30s of the coach bed -> coach.webm
node scripts/render_audio.cjs sfx           # step / turn-back / run / swish
node scripts/render_audio.cjs               # all four beds
# convert if you like:  ffmpeg -i coach.webm coach.wav
```

The landing theme also has an **offline** render to a shipped OGG (and a video
card) via `scripts/export_landing_media.py`, which unrolls the landing scheduling
into an `OfflineAudioContext`. Between the live capture (any arc, faithful) and
the offline render (landing, deterministic), the whole soundscape is reproducible
outside the game.

## Mobile / iframe autoplay (the load-bearing bit)

Browsers block audio until a user gesture, and iOS/Safari plus the cross-site
Hugging Face Spaces iframe only start audio if the context is resumed
**synchronously inside the gesture**, before any `await`. So:

- `ambience.unlock()` resumes a suspended context and returns whether it is
  running.
- `game.js` registers `unlock()` on the **first** `pointerdown`/`touchstart`/
  `keydown` in the **capture phase** (not `{once}`), so even a first tap that is
  choosing an arc unlocks audio before the arc's fetch is awaited.

Do not move the resume after a fetch, or mobile audio dies silently.

## Authoring a soundscape with an AI agent (the method)

This is how the BGM and SFX were actually created: by prompting a coding agent in
plain language and having it write, measure, render, and iterate on the synth.
Any capable model (including a local one driving Claude Code, see
[`REPRODUCE.md`](REPRODUCE.md)) can do the same, because all the pieces are in the
repo. The workflow is a tight loop, not a one-shot.

### 1. Give a design brief, in prose (not notes or a score)

Describe the *feeling and the physical source*, and the constraints. Room tone,
not music; not eerie stings; sparse. Real prompts from this build, generalised:

- "The coach should sound like an almost-empty subway car: a steady low roll, not
  chuggy. Add soft rail-joint clacks so it is clearly a train and does not sound
  like the stairwell."
- "The stairwell is near silence. Low room tone, a concrete-shaft hum, a sense of
  echoing space, and a faint distant extractor fan so it is not mistaken for the
  coach."
- "Make the passing train and the lurch land about once every 30 seconds, so a
  normal climb actually hears them. Keep them soft."
- "The footsteps feel too sudden over the room tone. Bring them down to sit at the
  same level as the background."
- "Every arc should be as loud as the landing theme, and each should sound
  distinct. Measure it and calibrate."

The model turns the brief into synthesis using the toolkit below.

### 2. The synth toolkit (the building blocks in `static/audio.js`)

A soundscape is composed from a small set of primitives on the `Ambience` class.
This is the whole vocabulary an agent needs:

- `_osc(type, freq)` a raw oscillator (sine/triangle/square/sawtooth).
- `_noise(seconds)` a looping filtered-noise source (the basis of hum, hiss, wind,
  rumble, room tone).
- `_gain(v)` / `_filter(type, freq, q)` level and tone shaping (lowpass for body,
  bandpass for airy mids, highpass for a thin crackle).
- `_reverb(seconds, decay)` a cheap convolution space (the stairwell echo).
- `_pluck(out, verb, freq, t, dur)` a soft ringing note (the landing arpeggio).
- `_mtof(midi)` note-to-frequency, for anything tonal.
- `_every(minMs, maxMs, fn)` schedule a sparse recurring event (flicker, lurch,
  train, gust); tuned to ~30s here.
- `_footstep(...)`, `_swish(...)` the SFX primitives, plus `step`/`run` that
  sequence them by the player's confidence.

A bed is just a handful of these connected to `bus`; an SFX is a one-shot
connected to `master`. Nothing else is needed, which is why there are no audio
files and no dependencies.

### 3. The loop: build, measure, render, iterate, guard

Each change to a sound runs the same rhythm, and the tools hand off to each other:

1. **Build / edit** the `_<skin>(bus)` builder (or a SFX) in `static/audio.js`.
2. **Measure** with `node scripts/measure_audio.cjs`: is the arc at the landing
   theme's RMS, with a distinct centroid, and are the SFX peaks in line?
3. **Render / listen** with `node scripts/render_audio.cjs <skin>` (or `sfx`) to
   hear it as a file and confirm by ear what the numbers imply.
4. **Iterate** on the brief by ear and by measurement (louder, sparser, brighter,
   a different centre) until it sits right.
5. **Guard** it: `tests/test_audio.py` (wiring, level-match, SFX trim, cadence,
   unlock) and the audio checks in `tests/emulation.cjs` (the graph builds, mute
   works, unlock resumes) keep a future edit from silently regressing it.

That is the entire method: a prose brief, the primitives, and the
measure/render/test tools closing the loop. The same five example prompts above,
handed to a model with this repo, reproduce the current soundscapes.

### 4. This is not limited to room tone: melody and harmony too

The synth is a general instrument, not an ambience-only trick. The **landing
theme is proof**: it is real music, a `vi-IV-I-V` arpeggio built from `_pluck` +
`_mtof` + a chord array. So a prompt like *"joyful, upbeat town music, bright and
bouncy, like a cosy village theme in a creature-collecting game"* is fully within
reach. The difference from the room tones is only the composition choices:

- a **bright major key** and a happy progression (for example `I-V-vi-IV`),
- a **faster step** between notes and a shorter ring (bouncy, not wistful),
- a **higher octave** and less reverb (near, cheerful, not distant),
- optionally a light bass pulse or an off-beat for lift.

A copy-pasteable starting point, using only the existing toolkit (drop it into
`static/audio.js`, route it in `play()`, and audition with
`node scripts/render_audio.cjs <name>`):

```js
_towntheme(bus) {
  const verb = this._reverb(1.6, 2.0); const verbG = this._gain(0.18);
  verb.connect(verbG).connect(bus);            // a little sparkle, not a cavern
  const lead = this._gain(0.06); lead.connect(bus);
  const chords = [                              // I - V - vi - IV in C major (happy)
    [60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60],
  ];
  const step = 0.14, ring = 0.28, perChord = 8; // fast + short = bouncy
  let idx = 0, t = this.ctx.currentTime + 0.1;
  const tick = () => {
    const ahead = this.ctx.currentTime + 0.4;
    while (t < ahead) {
      const c = chords[Math.floor(idx / perChord) % chords.length];
      const up = c.concat(c.map((m) => m + 12));       // reach an octave up
      this._pluck(lead, verb, this._mtof(up[idx % up.length]), t, ring);
      if (idx % 4 === 0) this._pluck(lead, verb, this._mtof(c[0] - 12), t, 0.5); // bass pulse
      t += step; idx++;
    }
    const h = setTimeout(tick, 60); this.timers.push(h);
  };
  tick();
}
```

Then iterate exactly as with the room tones: render it, listen, adjust the key,
tempo, octave, and level, and measure against a reference. Keep any private
reference a developer uses (a specific game or track they have in mind) **in their
own prompt, not in the repo**: this project's own files stay free of external IP,
so the checked-in example above is described generically.

### Legend: the melodic and synth terms (how to choose)

You do not need to read music to pick these. Each row says what the term is and
which way to move it for the feeling you want.

Musical choices:

| Term | What it is | How to choose |
|------|-----------|---------------|
| **Key** | The home note the tune centres on (e.g. C). | Any note works; the *mode* below matters more than which one. |
| **Major / minor (mode)** | The "colour" of the scale. | **Major = happy, bright, cheerful.** Minor = sad, tense, uneasy. Pick major for joyful, minor for eerie. |
| **Chord** | A few notes sounded together (e.g. `[60,64,67]` = C major). | In code, an array of MIDI notes. Three notes is a plain chord; add more for richness. |
| **Progression** | The order chords move in, written as roman numerals of the key. | `I-V-vi-IV` = the classic happy/pop loop. `vi-IV-I-V` = wistful (the landing theme). `I-IV-V` = simple and folky. `ii-V-I` = jazzy. Upper case = major chord, lower case = minor. |
| **MIDI note number** | An integer per pitch; 60 is middle C, +1 is a semitone up. | `this._mtof(n)` turns it into a frequency. Higher number = higher pitch. |
| **Octave** | Same note, twelve semitones apart. | `+12` = one octave up (brighter, lighter), `-12` = down (heavier, bassier). |
| **Arpeggio** | A chord played one note at a time instead of all at once. | The default here: it sparkles and feels light. Play the notes together instead for a pad/organ feel. |
| **Tempo (via `step`)** | Seconds between notes. | Smaller = faster and bouncier (`0.12-0.16` upbeat), larger = slower and calmer (`0.22+` wistful). |
| **Ring / sustain (`dur`)** | How long each note rings. | Short (`0.2-0.3`) = plucky and cheerful; long (`0.8-1.0`) = flowing and dreamy. |

Timbre and space (shared with the room tones):

| Term | What it is | How to choose |
|------|-----------|---------------|
| **Waveform (`_osc` type)** | The raw tone colour. | `sine` = pure and soft; `triangle` = soft and bell-like (used for plucks); `square`/`sawtooth` = buzzy and bright (chiptune energy). |
| **Filter (`_filter`)** | Tone shaping on a sound. | `lowpass` = warmer/muffled (cut highs), `bandpass` = focused/airy (a narrow band), `highpass` = thin/bright (cut lows). |
| **Q (filter resonance)** | How sharp the filter's focus is. | Low (`0.5`) = gentle; high (`2+`) = a ringing, whistling emphasis. |
| **Reverb (`_reverb` + send level)** | Simulated room/echo. | More = distant, cavernous, dreamy; less = near, intimate, cheerful. Joyful themes want *less*. |
| **Gain / level (`_gain`)** | Loudness of a part. | Keep the whole thing near the landing theme's level (measure with `measure_audio.cjs`); balance parts so the lead sits above the bass. |
| **Centroid** | A brightness number the measure tool reports. | Higher = brighter/tinnier, lower = darker/warmer. Use it to keep parts (or arcs) distinct. |

Rule of thumb for "joyful town music": **major key, `I-V-vi-IV`, fast `step`,
short `ring`, `triangle` lead up an octave, light reverb, a soft bass note on the
downbeat.** For "eerie", flip most of those: minor key, slow, long ring, lots of
reverb, low octave.

Four of these are worked, **runnable, self-verifying** examples in
`scripts/examples/melodic_themes.cjs` (joyful, heroic, eerie, chiptune). Run it to
hear them and to confirm each prompt actually produces audible music:

```bash
node scripts/examples/melodic_themes.cjs        # renders + verifies each theme
```

### 5. Sound effects (SFX): the same method

An SFX is just a very short sound with a sharp envelope. The primitives are the
same toolkit, used as one-shots connected to `master` (SFX bypass the bus):

- **Envelope** the shape of a sound over time, done with gain ramps: a fast
  `linearRampToValueAtTime` up (the *attack*) then an `exponentialRampToValueAtTime`
  down (the *decay*). Short attack + short decay = a click or blip; slower = a
  swell.
- **Pitch sweep** ramp an oscillator's `frequency` (down for a thud, up for a
  zip). This is most of the character of a thunk or a laser.
- **Noise burst** `_noiseOneShot` through a filter, enveloped: the basis of a
  whoosh, a scuff, an impact's "air".
- **Waveform** `sine` (soft), `triangle` (bell), `square`/`sawtooth` (bright,
  buzzy, retro).

Example prompts and their recipes (all in `scripts/examples/sfx_kit.cjs`):

| Prompt | Recipe |
|--------|--------|
| "bright pickup/coin blip" | two quick rising **square** notes, tiny decay |
| "warm success chime" | a **major arpeggio** of `_pluck` notes with light reverb |
| "soft low door thunk" | a **sine pitch sweep** 120->48 Hz + a low-passed noise thud |
| "harsh error buzz" | two detuned **sawtooth** notes held then cut (dissonant) |
| "quick whoosh / transition" | a **band-passed noise** with the band swept upward |

Legend of SFX terms: **attack** = how fast it starts (short = percussive);
**decay/release** = how fast it fades (short = tight, long = ringing);
**transient** = the sharp onset that makes it read as an event; **sweep** = a
gliding pitch or filter; **burst** = a brief enveloped noise. Louder, brighter,
and faster reads as "positive/UI"; lower, slower, dissonant reads as
"negative/impact".

Render and verify the whole SFX kit:

```bash
node scripts/examples/sfx_kit.cjs               # renders + verifies each effect
```

### 6. This works with any model, and putting it all together

None of this is specific to a particular model. The only skill required is
*writing a few lines of Web Audio JavaScript with the toolkit above*; the
measure/render/verify tools are deterministic scripts. So a developer running
**Claude Code with a local or third-party model** (see `docs/REPRODUCE.md`) can
prompt "make me a joyful town theme" or "a coin pickup" and have their model
author the builder and run these tools to hear and check it, exactly as here.

To render the complete set (the game's beds and SFX plus every example theme and
effect) into one folder with an `INDEX.md` manifest:

```bash
node scripts/render_all_audio.cjs ./audio-all   # everything, then an index
```

## Adding a soundscape for a new arc

1. Add a `_<skin>(bus)` builder in `static/audio.js` that connects its nodes to
   `bus`. Keep it room tone, sparse, and distinct from the other arcs (a
   different spectral centre helps).
2. Add a branch in `play()`: `else if (skin === "<skin>") this._<skin>(bus);`.
3. Add an entry to the `BUS` map and run `scripts/measure_audio.cjs` to set the
   level so the arc matches the landing theme.
4. `tests/test_audio.py` will require the builder and route to exist.

## Offline render of the landing theme (optional)

`scripts/export_landing_media.py` renders the landing theme to
`static/audio/landing.ogg` (mono OGG Vorbis, normalized) from the *same* synth
via an `OfflineAudioContext`, plus a 1080p video for a landing/marketing loop. It
is optional (the game never loads the file for play) and is run locally.
