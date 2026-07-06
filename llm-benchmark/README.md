<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 alvations (Melon Lab) -->

# 8: LLM benchmark

Can your language model **remember a place**? This harness lets you point a local
Hugging Face `transformers` model at the deployed **8** game and measure how many
rounds it needs to escape each arc. It is a clean, self-contained memory benchmark:
the model plays exactly like a human, the server owns correctness, and the answer
is never in the payload.

## The task

8 is a game of memory and doubt. You move through a place that should look the
same on every loop. Each loop you make one call:

- **go_on**: proceed, nothing has changed from the baseline you remember.
- **turn_back**: turn around, something is different.

`correct = (choice == "back") == has_anomaly`. **Eight correct calls in a row**
and the door opens; **one wrong call resets you to the very start.** The place is
described from rotating sentence pools with only a subset of details shown per
loop, so the model must remember the **meaning** of the place, not the wording.
That is the whole test: track state across noisy, partial, rephrased observations.

## What gets measured

The benchmark sweeps the full grid and reports, per cell, the win rate, the mean
**rounds** (committed loops) to a win, and the mean **resets** it took:

- **3 arcs**: `hallway-eight`, `stairway8`, `coach8` (same mechanic, different
  place, NPC, and pacing).
- **3 difficulty levels of eight**: `easy`, `normal`, `hard`. Hard escalates *in
  kind*: an anomaly can persist across loops or cleanly revert, so memory must
  span more than one loop.
- **2 reading levels**: `normal` and `simple`. This is the game's accessibility
  register; here it selects which phrasing of the rule the model is given. Neither
  spoils the answer.

(There is a fourth, hidden `insane` difficulty that randomizes the baseline every
run; it is not part of the default sweep. Pass `--difficulties ... insane` only if
your server build allows it.)

## Install

```bash
cd llm-benchmark
pip install -r requirements.txt        # requests is enough for the baselines
```

## Quickstart

**1. Smoke-test the harness with a zero-dependency baseline** (no model, no GPU).
This also shows you the floor an LLM must beat:

```bash
python benchmark.py --base-url https://alvations-hallway8.hf.space \
    --agent random --episodes 5
```

**2. Put a local model in the seat.** The default is a small, on-device example
(`google/gemma-3n-e4b-it`); swap it with `--model`:

```bash
python benchmark.py --base-url https://alvations-hallway8.hf.space \
    --agent llm --model google/gemma-3n-e4b-it --episodes 3
```

Point `--base-url` at your own local server instead to iterate fast:

```bash
# terminal 1: run the game locally
pip install -r ../requirements.txt && python ../app.py     # http://127.0.0.1:5000

# terminal 2: benchmark against it
python benchmark.py --base-url http://127.0.0.1:5000 --agent llm \
    --model google/gemma-3n-e4b-it --arcs hallway-eight --difficulties normal
```

Example output:

```
agent: gemma-3n-e4b-it   server: https://alvations-hallway8.hf.space   locale: en_US

arc             diff    reading    win%   rounds  resets
--------------------------------------------------------
hallway-eight   normal  normal      60%     22.0     1.8
hallway-eight   normal  simple      80%     14.5     0.9
...
full results -> results/gemma-3n-e4b-it-1783315391.json
```

## How it works

Each loop, the harness:

1. Renders the room the model sees: a heading, the rotating sentences, and the
   **legal actions** for this turn.
2. Passes the model its running **history** of prior loops this climb, so it can
   compare the current loop against its own established baseline.
3. Reads back a JSON action list and **calls the game API** to enact it.

```
your model  -->  {"reason": "...", "actions": ["go_on"]}
harness     -->  POST /api/act {choice:"continue"}   (X-Sid, X-Diff, X-Lang headers)
server      -->  {correct, won, level, room:<next loop>}   (answer never included)
```

The action vocabulary each turn is `go_on`, `turn_back`, and (if the loop offers
them) `touch:<detail>` for the game's optional Act 2 touches. Touches are flavour
only and never decide the call, but a curious touch can rarely **fold** the run
back to the start, so a model that pokes at everything pays for it. Hide touches
with `--no-touch` for a pure go_on/turn_back benchmark.

Files:

| file | role |
|---|---|
| `eight_env.py` | thin API client: `reset()`, `act("go_on"/"turn_back")`, `touch(prop)` |
| `prompts.py` | system prompt per reading level + observation/turn rendering |
| `agent.py` | `RandomAgent`, `AlwaysGoOnAgent`, and `LLMAgent` (transformers) |
| `benchmark.py` | the sweep runner + metrics |
| `results/` | JSON runs land here |

## The prompt

The model is given the rule (in the chosen reading register) and then, each turn,
its history plus the current loop, and is asked for a JSON action. The system
prompt is **answer-free** by design: it teaches how to play, never which detail to
watch. From `prompts.py` (`normal` register):

> You are playing a memory game called 8. You move through a place that should
> look the same on every loop. Each loop you read a short description and make one
> call:
> - go_on   : proceed, because nothing has changed from what you remember.
> - turn_back: turn around, because something is different from the baseline you
>   established.
>
> The wording is rephrased and only a subset of details is shown each loop, so you
> must remember the MEANING of the place, not the exact sentences. Eight correct
> calls in a row and the door opens. One wrong call sends you back to the very
> start. The first loop is your clean baseline: nothing has changed yet, so go_on
> and commit it to memory.

A turn then looks like:

```
Your run so far (oldest first):
Loop 1 of 8.
[Hallway 8]
  You hear the familiar drone of distant ventilation.
  The exit sign reads EXIT →.
  -> you chose go_on: correct
...
Loop 3 of 8.
[Hallway 8]
  The vent hums somewhere far off, as always.
  The sign by the door says  EXIT→.

Reply with ONLY a JSON object of the form {"reason": "...", "actions": [...]}
where each <action> is one of: go_on, turn_back, touch:door, touch:camera. ...
```

## Bring your own model or agent

Any Hugging Face causal LM with a chat template works with `--agent llm --model
<id>`. Models that run comfortably on modest hardware:

- `google/gemma-3n-e4b-it` (default, on-device)
- `google/gemma-2-2b-it`
- `Qwen/Qwen2.5-3B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`

To benchmark something the CLI does not cover (an API model, a custom scaffold,
tool use, a scratchpad), subclass `Agent` in `agent.py`:

```python
from agent import Agent

class MyAgent(Agent):
    name = "my-agent"
    def act(self, payload, actions, history):
        # payload["room"]["sentences"], payload["level"], `actions`, `history`
        # return a list ending in exactly one of "go_on" / "turn_back"
        return ["go_on"]
```

Register it in `make_agent()` and run with `--agent my-agent`.

## Other languages

The game is localized; pass `--locale` to benchmark reading comprehension in
another language (the prose comes back translated, the rule prompt stays English):

```bash
python benchmark.py --base-url ... --agent llm --model <id> --locale ja_JP
```

Exposed locales: `en_US de_DE fr_FR pt_PT ja_JP ko_KR zh_CN vi_VN`.

## Notes on fairness

- **The server is the judge.** Correctness is computed server-side and the answer
  keys (`_has_anomaly`, …) are stripped from every payload, so there is nothing to
  read; the model must actually remember.
- **Baselines matter.** `--agent random` and `--agent always_go_on` bound the
  problem: if your model cannot beat them, it is not tracking state.
- **Determinism.** `LLMAgent` generates greedily (`do_sample=False`) so a run is
  reproducible for a given model and server build. The game itself rotates wording
  per loop by design, which is the point.
- **Be polite to the public Space.** Keep `--episodes` modest against
  `hf.space`; run the full grid against a local server.
