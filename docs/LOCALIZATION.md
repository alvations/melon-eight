<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# Localization playbook

This document is the portable, reproducible procedure for localizing this game,
and for applying the same rigor to any future game. It is written so that an
agent (or a person) who clones the repo onto a fresh machine can run the *exact*
same process: author, audit, per-line QE, post-edit + post-edit QE,
level-composition QE (the "longer-context / whole-doc" test), revise the weakest
lines, re-QE, and iterate until the gate is met, with a full audit trail
committed at every step.

Read this before touching any translation. Read `docs/ARCS.md` first if you are
also adding or changing an arc, since the English source is the thing you
translate.

## 0. Principles (why it is built this way)

1. **English is the single source of truth and is never scored.** The English
   text lives in the arc JSON (`data/arcs/*.json`) and in `i18n.UI_STRINGS_EN`.
   Every other locale is measured against it. `en_US` is the fixed reference;
   scoring it would be scoring the ruler.
2. **Translate meaning, compose deterministically.** The game shows a *subset*
   of rotating sentence pools each loop, so a translation is correct only if it
   still reads fluently and coherently *after the engine pieces arbitrary lines
   together into a level*. A line that is fine alone but clashes in a level is a
   defect. This is why per-line QE is necessary but **not sufficient**; the
   level-composition QE below is the real gate.
3. **Every judgement is auditable.** Each line records its first-pass text, a
   first-pass score, a post-edited text, and a post-edit score. Superseded
   versions are kept in `revisions[]`. Level scores are the mean of the audited
   per-line post-edit scores of the lines that compose the level, so a level
   score can always be traced back to lines.
4. **No external machine translation.** Translations are model-generated and
   the scores are honest model self-assessments (LLM-as-translator +
   LLM-as-judge). Be conservative: a score is a floor you can defend as a native
   reader, not an aspiration. Never inflate a score to clear the gate; raise the
   score only by genuinely improving the `postedit`.
5. **Graceful degradation.** A missing translation for a key falls back to
   English, key by key. Partial locales are safe to ship; they are just partly
   English. The level QE counts any such fallback as a `leak` and scores it 0
   for that level, so leaks are visible, not silent.
6. **Model-agnostic, no API.** The intelligence (translating a line, post-editing
   it, and scoring it as a native reader would) is the *agent's*, done in the
   conversation and written into the `data/i18n/src/` files. The scripts
   (`i18n_extract`, `i18n_ingest`, `i18n_compile`, `i18n_levelqe`, `i18n_selfqe`)
   are **pure, deterministic Python and call no translation service or model API**
   at all: they only extract, merge, compile, and average the scores the agent
   authored. So this pipeline reproduces identically under Claude Code with **any
   backend model, local or hosted** (see `docs/REPRODUCE.md`): the model fills the
   src files, the scripts do the bookkeeping and enforce the gate. Nothing here is
   tied to a particular provider.

## 1. Architecture (what each piece does)

```
i18n.py                     the key scheme + locale registry + runtime loader
data/arcs/<arc>.json        English source of truth (per arc)
i18n.UI_STRINGS_EN          English source of truth (shared UI), in i18n.py
data/i18n/lines.json        THE AUDIT TRAIL (every key, every locale, full history)
data/i18n/src/<locale>.json          author here: shared/UI + any arc (flat)
data/i18n/src/<arc>/<locale>.json    author here: one arc's strings (per-arc)
   (both patterns are ingested; today the shared UI + coach8 live in the flat
    files, hallway-eight + stairway8 in per-arc files. Either works.)
data/i18n/compiled/<locale>.json     emitted: {key: final_text} for the server
static/i18n/<locale>.json            emitted: {ui_name: text} for the client UI
data/i18n/levels.json       emitted: level-composition QE evidence
scripts/i18n_extract.py     seed/refresh en_US keys into lines.json
scripts/i18n_ingest.py      merge src/ files into lines.json (keeps revisions)
scripts/i18n_compile.py     lines.json -> compiled/ + static/ catalogs
scripts/i18n_levelqe.py     level-composition QE + the >=95 gate
```

### The key scheme (`i18n.arc_items`)

Every translatable string has a deterministic key computed from its position in
the arc JSON. The runtime recomputes the identical key when it renders a line,
so the lookup is exact. Keys:

- `a:<arc>|title_main` `|tagline` `|go_on` `|turn_back` `|progress`
- `a:<arc>|share_prompt`: the win-screen share invitation (arc-flavoured)
- `a:<arc>|attempt`: the "look back" run-count line (contains `{n}`)
- `a:<arc>|attempt_first`: the "look back" line for a clean first run
- `a:<arc>|label|<prop>`: the noun the adaptive templates splice in
- `a:<arc>|title|<i>`: title drift variants
- `a:<arc>|p:<prop>|v:<val>|<i>`: a normal (non-anomaly) sentence
- `a:<arc>|p:<prop>|x:<val>|<i>`: an anomaly sentence
- `a:<arc>|adaptive|<kind>|<i>`: `repeat_inspect`, `long_look`, …
- `a:<arc>|framing|<kind>|<i>`: `intro`, `win`
- `a:<arc>|act2|…`: the Act 2 "touch the room" content (flashbacks, per-prop
  touch reactions, the false-exit tempt/action, alternate endings). See
  [`ACT2.md`](ACT2.md).
- `ui|<name>`: shared UI strings (from `UI_STRINGS_EN`). Includes the buttons
  and prompts, plus `instructions` (the first-reset onboarding heading),
  `look_back` (the fleeting win-screen toggle), `share_1..8` / `share_native` /
  `share_copy` / `share_copied` (the win-screen share block), the settings and
  fold strings (`set_*`, `fold_*`), and the collection strings (`ach_section`,
  `col_section`, the 34 badge names/descriptions `ach_n_*` / `ach_d_*`, the
  recall strings `col_recall` / `col_recall_empty`, and the promo strings
  `promo_*`). Arc names and "Melon Labs" stay verbatim across locales; the
  collection design is in [`COLLECTION.md`](COLLECTION.md).

If you change the English arc content, the keys for the changed lines change;
re-run extract and the affected keys simply need (re)translation.

### The audit entry shape (`data/i18n/lines.json`)

```json
"a:coach8|p:door|v:closed|0": {
  "en_US":  {"text": "The connecting door ... is shut, its glass dark."},
  "de_DE":  {"text": "<first-pass>", "score": 92,
             "postedit": "<improved>", "postedit_score": 96,
             "revisions": [ {"text": "...", "score": ..., "postedit": "...",
                             "postedit_score": ...} ]},
  "ja_JP":  { ... }
}
```

- `text` / `score`: the first-pass translation and its self-score.
- `postedit` / `postedit_score`: the corrected translation and its self-score.
  This is what compiles into the runtime and what the level QE averages.
- `revisions[]`: every prior version, appended automatically by ingest when a
  re-ingest changes an entry. Nothing is ever lost.

## 2. Placeholders and grammatical composition (the hard part)

Some strings contain placeholders the engine fills at runtime. **Every
placeholder in the English MUST survive in the translation, spelled exactly:**

- `{THING}`: a `label` noun spliced into an `adaptive` template.
- `{SIGN}`: an on-sign token (e.g. the exit word).
- `{level}` `{goal}` `{floor}`: progress counters.
- `{n}`: the run count, spliced into the win-screen `attempt` line. Front-load
  it (`{n} times down this corridor, …`) so it works across counter systems
  (German *Mal*, French *fois*, Japanese *回*, Korean *번*, Chinese *次*,
  Vietnamese *lần*). The `attempt_first` line has no placeholder.

**Metaphor caution.** Some short strings are idioms, not literal phrases, and a
word-for-word translation is wrong. The clearest example is the `look_back`
label: it means *reflect on the run just finished*, not *physically turn
around*. Use the retrospective sense your language actually uses for looking
back on the past (振り返る, 돌아보기, 回望, Nhìn lại, Regarder en arrière, Olhar
para trás, Zurückblicken), never the "about-face" verb. When a UI string reads
as a metaphor in English, translate the meaning.

Because `{THING}` is composed into a sentence, gendered / case / particle
languages must make the **label** and the **template** agree *as a pair*:

- **German:** write labels in the case the templates demand and keep all
  templates in that one case. This repo uses accusative labels with
  `auf {THING}` templates, e.g. label `den Handlauf` + template
  `Erneut fällt dein Blick auf {THING}.` Rephrase any template whose English
  makes `{THING}` the subject (nominative) so `{THING}` stays the object, so one
  label form works everywhere.
- **Japanese:** labels are bare nouns; the template supplies the particle, e.g.
  label `手すり` + template `また{THING}を確かめる。` Choose the particle in the
  template, never inside the label.
- General rule: **decide one grammatical role for `{THING}` per arc and make
  every label and every template obey it.** Verify by reading the composed
  sentences, not the pieces (the level QE prints composed level text for this).

## 3. The reproducible workflow (fresh clone, any machine)

Prerequisites: Python 3, `pip install -r requirements.txt` (the i18n scripts
only need the stdlib + the repo itself). All commands run from the repo root.
Set `PYTHONPATH` to the repo root so the scripts import `i18n`.

```bash
export PYTHONPATH="$PWD"
```

### 3.1 Seed / refresh the audit trail from English

```bash
python scripts/i18n_extract.py
```

Idempotent. Writes/updates `en_US` text for every key in `lines.json` and leaves
existing translations untouched. Run it after any English change or new arc.

### 3.2 Author a locale

Create a source file (author here, never edit `lines.json` by hand):

- shared UI + small/flat sets: `data/i18n/src/<locale>.json`
- one arc: `data/i18n/src/<arc>/<locale>.json`

Map each key to `{text, score, postedit, postedit_score}`. Cover **every**
non-empty key for the arc/UI you are doing (empty English spacer lines are
skipped). Preserve every placeholder. Keep register and tense consistent across
a pool so any two lines read well back-to-back.

Verify coverage before ingesting (adapt arc id):

```bash
python - <<'PY'
import json, i18n
arc = "hallway-eight"; loc = "de_DE"   # per-arc file: data/i18n/src/<arc>/<loc>.json
data = json.load(open(f"data/arcs/{arc}.json"))
items = dict(i18n.arc_items(arc, data))
keys = [k for k,v in items.items() if v.strip()]
src  = json.load(open(f"data/i18n/src/{arc}/{loc}.json"))
print("missing:", [k for k in keys if k not in src])
print("extra:  ", [k for k in src if k not in items])
for k,v in src.items():
    for ph in ("{THING}","{SIGN}","{level}","{goal}","{floor}"):
        if ph in items.get(k,"") and ph not in v["postedit"]:
            print("MISSING PLACEHOLDER", ph, k)
PY
```

### 3.3 Ingest → compile

```bash
python scripts/i18n_ingest.py     # merges src/*.json and src/*/*.json; keeps revisions[]
python scripts/i18n_compile.py    # emits compiled/<locale>.json + static/i18n/<locale>.json
```

### 3.4 Level-composition QE (the doc / longer-context gate)

```bash
python scripts/i18n_levelqe.py --arc <arc> --n 120 --locales de_DE ja_JP
```

What it does, per locale:

1. Generates `--n` levels in English with fixed seeds (`seed = 1000 + i`,
   `PlayerMemory(level = i % 8)`), so line selection is deterministic.
2. Re-renders each level in the locale from the **same** seed, so it is the
   translated version of the identical level.
3. Scores each level as the **mean of the audited `postedit_score`s** of the
   lines that composed it. A leaked (untranslated) line counts as **0**.
4. Writes `data/i18n/levels.json` (composed English + localized level text, per
   level, per locale, with score and leak count) as the QE evidence.
5. Prints, per locale: `mean`, `min`, how many of the N levels are `>=95`, total
   `leaks`, and the verdict `PASS` / `REVISE`.

**The gate: mean `>= 95` over 120 levels, with 0 leaks.** `PASS` ships; `REVISE`
does not.

### 3.5 Revise → re-QE → iterate

If a locale is `REVISE` (or `min` is low, or there are leaks):

1. Open `data/i18n/levels.json` and read the *composed localized level text* for
   the lowest-scoring levels. Judge them as a whole: does the level read
   fluently and coherently, do the pieces agree grammatically, is the register
   consistent, did a placeholder break?
2. Fix the weakest **lines** in `data/i18n/src/<arc>/<locale>.json` by genuinely
   improving the `postedit`, and set `postedit_score` to the honest new value.
   Do not raise a score without improving the text.
3. Re-run **3.3 → 3.4**. `ingest` moves the prior version into `revisions[]`
   automatically, so the audit shows the before/after.
4. Repeat until `PASS`. Leaks must reach 0 (fill the missing keys).

### 3.6 Regression + game tests

```bash
# re-QE every already-shipped arc so a shared-file edit didn't regress it
for arc in coach8 hallway-eight stairway8; do
  python scripts/i18n_levelqe.py --arc "$arc" --n 120 --locales de_DE ja_JP
done
python tests/test_game.py            # expect 8/8
```

Also sanity-check that a localized room renders and never leaks the answer
(`public()` must strip every `_`-prefixed key):

```bash
python - <<'PY'
import random, i18n
from hallway import Hallway
from memory import PlayerMemory
h = Hallway("coach8")
r = h.build(PlayerMemory(level=5), random.Random(42), "ja_JP")
print(r["heading"]); [print(" ", s) for s in r["sentences"][:3]]
assert not any(k.startswith("_") for k in h.public(r)), "ANSWER LEAK"
print("no answer leak: OK")
PY
```

### 3.7 Commit the whole audit trail

Commit **all** of: `data/i18n/src/**`, `data/i18n/lines.json`,
`data/i18n/compiled/*.json`, `static/i18n/*.json`, `data/i18n/levels.json`, and
any script/doc change. That is the complete, portable record: another machine
can reproduce every number from these files. Author as the repo owner only, no
AI attribution (see `CLAUDE.md` → Working conventions).

Deployment to the live Space is separate and local-only (see `CLAUDE.md` →
Run/test/deploy).

## 4. Adding a new language

1. Confirm the code exists in `i18n.LOCALES` (add it there if not: `code`,
   `name`, `native`; keep it LTR-aware). `is_locale()` and the picker read this.
2. For each arc and for the shared UI, author `data/i18n/src/<arc>/<locale>.json`
   and `data/i18n/src/<locale>.json` (UI keys `ui|<name>`).
3. Run the full **section 3** loop for each arc until every arc `PASS`es and the
   UI is complete. RTL languages are not yet handled by the client CSS; add
   direction handling before shipping one.

## 5. Adding a new arc's translations

1. Add/finish the arc in English first (`docs/ARCS.md`).
2. `python scripts/i18n_extract.py` to seed its keys.
3. Author `data/i18n/src/<arc>/<locale>.json` for each locale you support, then
   run **section 3**. Decide the `{THING}` grammatical role for the arc up front
   (section 2) and keep labels/templates consistent with it.

## 5b. Adding a single string (UI or per-arc), the way sharing was added

Small feature strings (a new button, the share invitations, the look-back line)
follow the same pipeline; you just add a few keys instead of a whole arc.

**A shared UI string** (same text regardless of arc, e.g. `look_back`,
`share_copy`):

1. Add it to `i18n.UI_STRINGS_EN` in `i18n.py` (`"<name>": "English text"`).
2. For each exposed non-English locale, add `"ui|<name>": {text, score, postedit,
   postedit_score}` to `data/i18n/src/<locale>.json` (the flat file).
3. `extract → ingest → compile`. The client picks it up from
   `static/i18n/<locale>.json`; unexposed locales fall back to English.

**A per-arc `meta` string** (arc-specific, e.g. `share_prompt`, `attempt`):

1. Add the field to each arc's `meta` in `data/arcs/<arc>.json` (English source).
2. Emit its key from `i18n.arc_items` (one `yield f"a:{arc_id}|<field>", ...`).
3. If the runtime needs it in a payload, localize it where that payload is built
   (e.g. `Hallway.meta_for` / a small helper like `attempt_line`).
4. Add `"a:<arc>|<field>": {…}` translations to the arc's source file
   (`data/i18n/src/<arc>/<locale>.json`, or the flat file for arcs that live
   there, like coach8).
5. `extract → ingest → compile`, then add or update a test.

Because these strings do not compose into levels, they do not go through the
120-level gate; instead, lock them down with unit tests (see
`tests/test_i18n.py`): assert every exposed locale has the key, that prose
strings are actually translated (not silently English), and that placeholders
like `{n}` survive. Authoring many locales at once is easiest with a small
injector script that writes the `{text, score, postedit, postedit_score}`
entries into each source file, then runs the pipeline (this is how the eight
share invitations and the attempt lines were added).

## 5c. The simple reading register (an "explain like I am young" gate)

The game ships an age-match **reading register** (`simple`/`normal`, default
normal; see `docs/COLLECTION.md` and CLAUDE.md). Simple exists so a younger
player can grasp the *mechanism*: it surfaces a plain-language rule
(`ui|rules_plain`) and can overlay a plainer `static/i18n/<lang>.simple.json` UI
catalog on top of the normal one (per key; missing keys fall back to normal). It
never changes a mechanic.

Simple-register strings carry an **extra QE gate** beyond the usual >=95
adequacy score: an **ELI ("explain like I am young") simplicity check**. A simple
string only passes if, in its own language, it also clears:

1. **Plain words.** Everyday, high-frequency vocabulary; no jargon, no rare or
   literary register, no idioms a child would not know.
2. **Short, direct sentences.** One idea per clause; prefer imperative, active
   voice; avoid subordinate stacking.
3. **Same meaning, no spoilers.** It must still say exactly what the normal
   string says (the rule, generically), and must NOT name the specific detail or
   NPC to watch. Simpler wording, never simpler *game*.
4. **Age-appropriate tone.** Calm and clear; the mood may soften but the meaning
   is intact.

Score each simple string twice: the normal adequacy score (vs the English
source's *meaning*) and a 0-100 **simplicity** score against the four points
above. A simple string ships only when both are `>= 95`. Record the simplicity
score alongside the adequacy score in the audit trail (reuse the `postedit`
fields; note "simple" in a revision entry). Author simple strings via the same
injector pattern as any single string (5b), writing to `<lang>.simple.json` (or,
for `rules_plain` and other keys that also exist normally, the normal flat file).

## 6. Porting this rigor to a different game / project

The methodology is engine-agnostic. To reuse it elsewhere, reproduce these
invariants; the four scripts are ~70 lines each and translate directly:

1. **A deterministic key per translatable string**, recomputed identically by
   the runtime and the tooling (the analogue of `i18n.arc_items`). This is what
   lets you compile to a flat catalog and fall back per key.
2. **English (or your chosen source) as an unscored reference**, held in the
   content files, never in the translation catalog by hand.
3. **An audit file** holding, per key per locale,
   `{text, score, postedit, postedit_score, revisions[]}`. Author in small
   per-language source files; a merge step preserves history. Never hand-edit
   the audit file.
4. **A compile step** that prefers `postedit`, then `text`, else omits the key
   (English fallback), emitting a runtime catalog.
5. **Level / document-composition QE**: don't score lines in isolation. Generate
   real units of output (a level, a screen, a page, a dialogue) with fixed
   seeds, render them in the target locale, and score the *composed* unit as the
   mean of its lines' audited post-edit scores; count fallbacks as 0. This is
   the "longer-context" test that catches register drift, grammatical
   disagreement across spliced pieces, and broken placeholders that per-line
   review misses.
6. **A published numeric gate** (here: mean `>= 95` over 120 units, 0 leaks) and
   a **revision loop** that only raises a score by improving the text, re-runs
   ingest/compile/QE, and iterates to `PASS`.
7. **Commit the evidence** (`levels.json` analogue) alongside the catalogs so any
   clone can reproduce and audit every number.

Keep scores honest (they are model self-assessments, not external MT metrics),
preserve placeholders exactly, and always judge the composed whole, not the
isolated line.
