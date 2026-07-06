// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Render EVERYTHING audio in one command: the game's own arc beds and SFX, plus
// the worked example themes and effects, into a single output folder, and write
// an INDEX.md manifest describing each file and the prompt that produced it. This
// is the "put it all together" step after authoring: a complete, listenable set
// of the generated BGM and SFX, straight from the live synth (static/audio.js).
//
// Usage:
//   node scripts/render_all_audio.cjs [outDir] [bedSeconds]
//   node scripts/render_all_audio.cjs ./audio-all 20
//
// It just orchestrates the already-verified tools (render_audio.cjs,
// examples/melodic_themes.cjs, examples/sfx_kit.cjs), so it needs the same
// portable tool-chain (npm install && npx playwright install chromium).

const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const OUT = process.argv[2] || "./audio-all";
const BED_SECONDS = process.argv[3] || "20";
const NODE = process.execPath;
const S = path.join(__dirname);

const steps = [
  ["game beds (hallway/coach/stairway/landing)", [path.join(S, "render_audio.cjs"), "all", BED_SECONDS, path.join(OUT, "beds")]],
  ["game SFX (footsteps/swish/run)",             [path.join(S, "render_audio.cjs"), "sfx", "0", path.join(OUT, "game-sfx")]],
  ["example themes (joyful/heroic/eerie/chiptune)", [path.join(S, "examples", "melodic_themes.cjs"), "6", path.join(OUT, "themes")]],
  ["example effects (pickup/chime/thunk/buzz/whoosh)", [path.join(S, "examples", "sfx_kit.cjs"), path.join(OUT, "effects")]],
];

fs.mkdirSync(OUT, { recursive: true });
for (const [label, args] of steps) {
  console.log(`\n=== ${label} ===`);
  execFileSync(NODE, args, { stdio: "inherit" });
}

const index = `# Generated audio (BGM + SFX)

Rendered from the live synth in \`static/audio.js\` by \`scripts/render_all_audio.cjs\`.
See \`docs/AUDIO.md\` for how each was authored (the prose brief, the toolkit, and
the build/measure/render/test loop) and the prompt behind each example.

## Game beds  (\`beds/\`)
The three arc room tones plus the landing theme, each level-matched to the landing.

## Game SFX  (\`game-sfx/\`)
The movement effects (footstep, turn-back, run flurry, swish).

## Example themes  (\`themes/\`)
Proof the synth is a general instrument, one file per prompt:
- \`joyful_town\` : "joyful, upbeat town music, bright and bouncy."
- \`heroic\`      : "warm, heroic, hopeful theme."
- \`eerie\`       : "eerie, unsettling, dreamlike, sparse."
- \`chiptune\`    : "playful 8-bit chiptune, fast and square."

## Example effects  (\`effects/\`)
One file per prompt:
- \`pickup\`        : "a bright pickup/coin blip."
- \`chime_success\` : "a warm success chime."
- \`thunk_door\`    : "a soft low door thunk."
- \`error_buzz\`    : "a harsh error buzz."
- \`whoosh\`        : "a quick whoosh/transition sweep."

Files are WebM (Opus). Convert with ffmpeg, e.g. \`ffmpeg -i beds/coach.webm coach.wav\`.
`;
fs.writeFileSync(path.join(OUT, "INDEX.md"), index);
console.log(`\nAll audio rendered to ${OUT} (see ${path.join(OUT, "INDEX.md")}).`);
