// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Measure the ACTION SFX against the BGM beds, and show WHY the footsteps are
// (and must stay) louder than the room tone. This is the tool behind the "Why the
// action SFX sit above the BGM" section of docs/AUDIO.md, and the reasoning is
// worth stating up front because it is an easy mistake to make from numbers alone.
//
// THE LOGIC OF THE COMPARISON
// ---------------------------
// BGM is a STEADY-STATE signal (continuous room tone). An action SFX (a footstep)
// is a TRANSIENT (a brief event fired the instant a choice is committed). They do
// different jobs: the bed sits UNDER attention; the footstep is FEEDBACK for the
// player's own action and must land as a discrete, tactile event, or the move
// feels weightless.
//
// The ear registers a discrete event by its onset PEAK, not by its averaged energy
// (RMS). So the right way to compare a transient to a bed is NOT "match their
// levels", it is to look at three things:
//   1. peak            - the instantaneous height (what makes an event "pop").
//   2. RMS             - average energy over time (what makes a bed "loud").
//   3. crest = peak/RMS - how spiky a sound is. A steady bed is ~3; a percussive
//                         one-shot is ~10. The high crest IS the transient.
//
// The key finding this script demonstrates: the footstep's RMS is about the SAME
// as the bed's (it does not carry more energy), but its PEAK is ~2-4x higher. That
// peak is the signal. A naive "recalibration" that trims the footstep peak down to
// the bed peak (to make the numbers match) destroys exactly the crest that makes
// the action tactile: it looks balanced and sounds dead. So:
//
//   - Level-match the BEDS to each other / to landing (steady vs steady, by RMS).
//     That is scripts/measure_audio.cjs and the BUS map.
//   - Do NOT fold the action SFX into that match. An action sound should peak
//     clearly ABOVE the bed (here ~2x or more), with a crest several times the
//     bed's. Judge it by whether the action reads as tactile (player testing),
//     not by matching a number.
//
// Usage:
//   node scripts/measure_sfx_vs_bgm.cjs
//
// Portable browser resolution: see scripts/browser.cjs.

const fs = require("fs");
const path = require("path");
const { loadPlaywright, chromiumLaunchOptions } = require("./browser.cjs");
const playwright = loadPlaywright();

const AUDIO_JS = path.join(__dirname, "..", "static", "audio.js");
const BEDS = ["hallway", "coach", "stairway", "landing"];
const SFX = [["footstep (commit)", "continue"], ["turn-back step", "back"]];

async function measure(page, kind, arg) {
  return await page.evaluate(async ({ kind, arg }) => {
    const a = window.ambience; a.muted = false; a._ensure();
    const an = a.ctx.createAnalyser(); an.fftSize = 2048; a.master.connect(an);
    if (kind === "sfx") a.step(arg, 200, 4); else a.play(kind);
    const buf = new Float32Array(an.fftSize);
    let peak = 0, s = 0, n = 0;
    const dur = kind === "sfx" ? 1200 : 3000;
    const t0 = performance.now();
    while (performance.now() - t0 < dur) {
      an.getFloatTimeDomainData(buf);
      for (let i = 0; i < buf.length; i++) { const v = Math.abs(buf[i]); if (v > peak) peak = v; s += buf[i] * buf[i]; n++; }
      await new Promise((r) => setTimeout(r, 20));
    }
    a.stop(); try { a.master.disconnect(an); } catch (e) {}
    await new Promise((r) => setTimeout(r, 200));
    const rms = Math.sqrt(s / n);
    return { peak, rms, crest: peak / (rms || 1e-9) };
  }, { kind, arg });
}

(async () => {
  const audioJs = fs.readFileSync(AUDIO_JS, "utf8");
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  const rows = [];
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><body><button id="sound-toggle"></button></body>');
    await page.addScriptTag({ content: audioJs });
    for (const bed of BEDS) rows.push([bed, "bed", await measure(page, bed)]);
    for (const [label, arg] of SFX) rows.push([label, "sfx", await measure(page, "sfx", arg)]);
  } finally {
    await browser.close();
  }

  console.log("\n  sound              type  peak    RMS     crest(peak/RMS)");
  for (const [label, type, r] of rows) {
    console.log(`  ${label.padEnd(18)} ${type.padEnd(4)}  ${r.peak.toFixed(3)}   ${r.rms.toFixed(3)}   ${r.crest.toFixed(1)}`);
  }

  // The comparison the reasoning above predicts: SFX peak >> bed peak, SFX RMS ~ bed
  // RMS, SFX crest >> bed crest.
  const bedPeak = Math.max(...rows.filter((x) => x[1] === "bed").map((x) => x[2].peak));
  const sfxPeak = Math.max(...rows.filter((x) => x[1] === "sfx").map((x) => x[2].peak));
  const bedCrest = rows.filter((x) => x[1] === "bed").reduce((s, x) => s + x[2].crest, 0) / BEDS.length;
  const sfxCrest = rows.filter((x) => x[1] === "sfx").reduce((s, x) => s + x[2].crest, 0) / SFX.length;
  console.log(`\n  action peak / loudest bed peak = ${(sfxPeak / bedPeak).toFixed(1)}x   (should be > ~1.5x: the action must sit above the bed)`);
  console.log(`  action crest ~${sfxCrest.toFixed(0)} vs bed crest ~${bedCrest.toFixed(0)}   (the action is a transient; the bed is steady)`);
  const ok = sfxPeak > bedPeak * 1.5 && sfxCrest > bedCrest * 1.8;
  console.log(`\n  ${ok ? "OK" : "WARNING"}: the action SFX ${ok ? "sits above" : "does NOT sit clearly above"} the BGM.`);
  console.log("  If this warns, the SFX has been over-trimmed; do not RMS-match it to the bed. See docs/AUDIO.md.\n");
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
