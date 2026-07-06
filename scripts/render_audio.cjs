// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Render / audition the game's synthesised sound to audio files, straight from
// the same generator the game uses (static/audio.js). This is the tool for
// hearing what a soundscape or an effect actually sounds like outside the
// browser, so a change to audio.js can be exported and listened to (or attached
// to a review).
//
// It captures in REAL TIME through a MediaStream + MediaRecorder, so it faithfully
// includes the scheduled events (flicker, lurch, passing train, wind, rail
// clacks), which an offline render of the setTimeout-based synth would miss.
//
// Usage:
//   node scripts/render_audio.cjs [what] [seconds] [outDir]
//     what     = hallway | coach | stairway | landing | sfx   (default: all beds)
//     seconds  = capture length for a bed (default 20; sfx ignores it)
//   node scripts/render_audio.cjs coach 30 ./audio-out
//   node scripts/render_audio.cjs sfx 0 ./audio-out    # step/turn-back/run/swish
//
// Output: <what>.webm (Opus). Convert to wav/ogg with ffmpeg if you like:
//   ffmpeg -i coach.webm coach.wav
//
// Portable browser resolution: see scripts/browser.cjs.

const fs = require("fs");
const path = require("path");
const { loadPlaywright, chromiumLaunchOptions } = require("./browser.cjs");
const playwright = loadPlaywright();

const AUDIO_JS = path.join(__dirname, "..", "static", "audio.js");
const what = process.argv[2] || "all";
const seconds = parseFloat(process.argv[3] || "20");
const OUT = process.argv[4] || "./audio-out";
fs.mkdirSync(OUT, { recursive: true });

const BEDS = ["hallway", "coach", "stairway", "landing"];
const targets = what === "all" ? BEDS : [what];

// Record whatever the ambience routes to `master`, for `ms` milliseconds, and
// return the bytes as a base64 string. For a bed we play(skin); for "sfx" we
// fire the movement effects in sequence.
async function capture(page, kind, ms) {
  return await page.evaluate(async ({ kind, ms }) => {
    const a = window.ambience;
    a.muted = false; a._ensure();
    const ctx = a.ctx;
    const dest = ctx.createMediaStreamDestination();
    a.master.connect(dest);
    const rec = new MediaRecorder(dest.stream, { mimeType: "audio/webm" });
    const chunks = [];
    rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    const done = new Promise((res) => (rec.onstop = res));
    rec.start();

    if (kind === "sfx") {
      // a representative spread of the movement effects
      a.step("continue", 200, 4); await new Promise(r => setTimeout(r, 900));
      a.step("back", 200, 4);     await new Promise(r => setTimeout(r, 900));
      a.run("back");              await new Promise(r => setTimeout(r, 1200));
      a._swish(ctx.currentTime + 0.02, false); await new Promise(r => setTimeout(r, 700));
    } else {
      a.play(kind);
      await new Promise((r) => setTimeout(r, ms));
      a.stop();
      await new Promise((r) => setTimeout(r, 400));
    }
    rec.stop();
    await done;
    const blob = new Blob(chunks, { type: "audio/webm" });
    const buf = await blob.arrayBuffer();
    let s = ""; const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  }, { kind, ms });
}

(async () => {
  const audioJs = fs.readFileSync(AUDIO_JS, "utf8");
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><html><body><button id="sound-toggle"></button></body></html>');
    await page.addScriptTag({ content: audioJs });

    const jobs = what === "sfx" ? [["sfx", 0]] : targets.map((t) => [t, Math.round(seconds * 1000)]);
    for (const [kind, ms] of jobs) {
      const b64 = await capture(page, kind, ms);
      const out = path.join(OUT, `${kind}.webm`);
      fs.writeFileSync(out, Buffer.from(b64, "base64"));
      console.log(`wrote ${out} (${(fs.statSync(out).size / 1024).toFixed(1)} KiB)`);
    }
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
