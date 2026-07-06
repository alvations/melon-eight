<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# The collection: Memory (achievements + recollections), save/load, codes

The **Memory** overlay is the game's persistence and replayability layer. It
turns the things a player does across runs (escaping arcs, finding alternate
endings, uncovering flashback fragments, *how* they won) into a record they can
see fill in, carry between devices, and extend with codes. It is reached from a
quiet **corner button** (`#ach-open`, in the top-right cluster with the sound and
settings toggles, shown on the selection screen only) so it lives off the
landing's main path; the overlay's header is **Memory** (`mem_title`). It is
engine-wide: arcs supply flashback/ending content, the engine supplies the board.

Everything here is **client-side**. Progress lives in `localStorage` under
`h8_mem`; the server never sees or scores it. This is the deliberate opposite of
the game's core answer state (which is server-only), a collection is the
player's to keep, so it stays on the player's machine.

## Layout

Top to bottom (device controls first, then the record):

- **Save / Load** and a redeem **Code** row (see below).
- **Achievements**: a grid of tiles, each a **drawn line glyph** in the game's
  thin, single-weight noir hand. **Only earned achievements appear**, populated
  as they unlock; there is no wall of padlocks and no `{n} of {total}` count (it
  would spoil how many exist). Order follows the `ACHS` array (grouped).
- **Recollections** (`col_section`): the flashback **fragment ledger**, a quieter
  inset panel: one row per arc, a dot per fragment, filled in the arc's skin
  colour as it is seen. A seen dot is a **button**: tap it to *recall* that
  fragment's own words in a fleeting italic line under the ledger (see
  *Fragment recall*).

All of it is driven from `renderAchievements()` in `static/game.js`.

## The badges

The board includes the play achievements, the **records** (how a run was won:
`steady`, `cold`, `nerve`, `streak`, see below), the hard-mode escapes, and one
hidden studio badge. Only earned badges are shown, so a new player sees an empty
board (an `ach_empty` line) that fills in as they play; there is no count and no
locked tiles. The studio badge, like all the rest, simply appears once redeemed.

| Badge (`id`) | Unlocked by |
|---|---|
| `out_hallway-eight` / `out_stairway8` / `out_coach8` | Escape that arc once |
| `out_all` | Escape all three arcs |
| `flawless` | Escape an arc with no reset (clean first run) |
| `eight_times` | Escape one arc eight times |
| `end_hallway-eight` / `end_stairway8` / `end_coach8` | Find that arc's alternate (false-exit) ending |
| `npc_knows` | Be acknowledged by the loop-aware NPC |
| `shared` | Pass the place on (any share target) |
| `opening_night` | Play on release day (unlocks the day after) |
| `flash_hallway-eight` / `flash_stairway8` / `flash_coach8` | See every flashback fragment in that arc |
| `total_recall` | See every fragment, in every arc |
| `melon` *(hidden)* | **Melon Supporter**: redeemed with a studio code |

Badge criteria live as `{id, test()}` in the `ACHS` array; the test reads
`mem`. Names and one-line descriptions are localized UI strings
(`ach_n_<id>` / `ach_d_<id>`), with an English fallback in `ACH_TEXT`.
Descriptions are written to avoid spoiling the specific detail a player must
watch, they name the *achievement*, never the anomaly.

### The Melon Supporter badge is the one deliberate style break

Every other icon is monochrome line-work. The studio badge is a warm,
full-colour **watermelon slice**: the single intentional break from the noir
palette, a small thank-you that pops. Its name is *Melon Supporter* and its
caption is a thank-you note, not a task. It exists only once redeemed, so it
reads as a bonus, never as something withheld.

## Fragment recall

When a player uncovers a flashback during Act 2, the client already receives the
fragment's `idx` and its localized `line`. `recordFlashback(arc, idx, line)`
stores the index in `mem.flash[arc]` **and** the text in `mem.flashText[arc]`,
so the collection can quote the fragment back later. In the ledger, tapping a
filled dot surfaces its stored words (`col_recall` is the button label;
`col_recall_empty` is the fallback for a fragment collected before text was
kept). The recalled line fades in, and a ring marks the chosen dot.

The text is captured in whatever locale it was collected in, a memory as it was
seen. Only collected fragments are ever quoted; uncollected ones stay dots.

## Records (how a run was won): now achievements

How a run was won is graded and **surfaced as achievements** on the board (not a
separate strip), so, like every other badge, they stay hidden until earned. Each
escape's winning climb (the unbroken run from level 0 to the exit) is graded on
marks tracked client-side in a live `run` object and stored in `mem.records`;
matching `ACHS` entries turn each into a badge:

- **Steady** (`steady`): won without ever admitting a guess (no low-confidence
  re-decide on the winning climb).
- **Cold read** (`cold`): won without a single touch or second look (pure memory,
  no Act 2 assistance).
- **Nerve** (`nerve`): the final call was a correct *turn-back on a real change*
  (the hardest, clutch read), not a walk-on.
- **On a roll** (`streak`): a best clean streak of **three** consecutive escapes
  made without a reset.

The `run` object resets whenever a climb starts fresh (entering a corridor, a
wrong call, or a fold), so the marks always describe the actual winning climb.
None of this changes the win logic; it only observes it.

On the win screen, the strongest mark of the just-finished climb also surfaces as
a fleeting **read record**, one in-world line (`read_steady` / `read_cold` /
`read_nerve`) tucked under the existing "look back" run-count line and fading with
it. It is the in-the-moment skill signal, in the game's own quiet voice, no
numbers.

## Save and load (obfuscated, not encrypted)

The **Save** button exports `eight-save.json`; **Load** reads one back. The file
holds three blobs, the player's memory (NPC habits + collection), the computed
achievement state, and the **settings** (difficulty, reading register, text
size, brightness, reduce-motion, language), each passed through `encBlob`, a
keystream XOR (FNV-1a seed → xorshift stream) seeded with the phrase `melon8`.
This is **light obfuscation, not cryptography**: it stops a save from being
human-readable and stops the number of achievements being eyeballed from the
JSON, nothing more. Loading a file decodes the memory back into `mem` and
restores the settings to `localStorage` (re-applying them live), so a device
swap carries the whole setup, not just progress. A wrong or corrupt file is
ignored silently.

## Promo codes

An 8-character code redeems a reward (`redeemPromo` in `static/game.js`). The
engine is extensible (arcs or features could be gated later); today two families
exist:

- **`MELONADE`** → unlocks the **Melon Supporter** badge.
- **`I18N-XX`** (XX = a short ISO code, e.g. `I18N-TH`) → unlocks one of the 21
  supported languages, adds it to the picker, and switches to it. The map of
  short code → locale is `i18n.PROMO_LOCALE`, exposed to the client via
  `/api/langs` (`unlock_map()`), restricted to locales that actually have a
  compiled catalog.

Redeemed codes are recorded in `mem.promos` and **persist through save/load**,
so an unlocked language or the studio badge survives export/import and reappears
in the picker on load (`rebuildLangPicker()`).

## Memory shape (`blankMem`)

```js
{ v, flash:{arc:[idx…]}, flashText:{arc:{idx:line}}, wins:{arc:n},
  clean:{arc:bool}, ends:{arc:bool}, npc:{arc:{prop:true}}, shared:bool,
  releaseDay:bool, plays:n, promos:[code…], melon:bool, langs:[locale…],
  records:{ steady:bool, cold:bool, nerve:bool, streak:n, best:n } }
```

Recording happens at the natural moments: `recordWin`/`noteAnomaly` on a win,
`recordEnding` on a false exit, `recordFlashback` on a touch, `recordShare` on a
share, `recordPlay` on entering a loop. `saveMem()` writes through and re-renders
the board if it is open.

## Localization

All collection strings go through the same pipeline as the rest of the game
(see [`LOCALIZATION.md`](LOCALIZATION.md)): the two section headers
(`ach_section`, `col_section`), the 34 badge strings (`ach_n_*` / `ach_d_*`),
and the two recall strings (`col_recall`, `col_recall_empty`). Arc names and
"Melon Labs" are kept verbatim across locales; metaphoric lines are translated
by meaning. All are translated and compiled for the eight exposed base locales,
with English fallback per key for the hidden ones.

## Conventions to keep

- **The collection stays client-side.** Never move answer state here, and never
  send collection state to the server for scoring.
- **Descriptions never spoil.** A badge names the feat, not the detail to watch.
- **Only earned badges show, no count.** The board fills in as achievements
  unlock; do not reintroduce locked tiles or a `{n} of {total}` denominator (it
  spoils how many exist).
- **One colour break, only the melon.** Every other icon stays monochrome
  line-work in the chrome/accent tier.
