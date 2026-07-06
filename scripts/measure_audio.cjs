// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Measure the per-arc ambience (and the movement SFX) so the beds can be kept
// level-matched to the landing theme. This is the tool behind the per-arc BUS map
// in static/audio.js: it loads audio.js in a blank headless-Chromium page (no
// server needed), plays each skin through a real AudioContext, taps the master
// output with an AnalyserNode, and reports loudness (RMS), peak, and spectral
// centroid.
//
// Usage:
//   node scripts/measure_audio.cjs            # all arcs + landing, then SFX
//   node scripts/measure_audio.cjs --bgm      # just the arc beds vs landing
//   node scripts/measure_audio.cjs --sfx      # just the movement SFX peaks
//
// Chromium + Playwright are resolved the same way as tests/emulation.cjs; set
// PW_PATH / H8_CHROMIUM to override. Exits 2 (skips) if they are unavailable.
//
// Reading the numbers: the three arcs should land near the landing theme's RMS
// (they are calibrated to it), each with a DISTINCT centroid so they do not sound
// alike. The footstep SFX peak sits well ABOVE the bed peak on purpose (an action
// is a transient event, not part of the bed): see scripts/measure_sfx_vs_bgm.cjs
// and the "Why the action SFX sit above the BGM" section of docs/AUDIO.md.

const path = require("path");
const fs = require("fs");
const { loadPlaywright, chromiumLaunchOptions } = require("./browser.cjs");

const playwright = loadPlaywright();
const AUDIO_JS = path.join(__dirname, "..", "static", "audio.js");
const SKINS = ["hallway", "coach", "stairway", "landing"];

const arg = process.argv[2] || "";
const doBgm = arg !== "--sfx";
const doSfx = arg !== "--bgm";

async function measureBgm(page) {
  const out = {};
  for (const skin of SKINS) {
    out[skin] = await page.evaluate(async (skin) => {
      const a = window.ambience;
      a.muted = false; a._ensure();
      const ctx = a.ctx, an = ctx.createAnalyser();
      an.fftSize = 2048; a.master.connect(an);
      a.play(skin);
      const buf = new Float32Array(an.fftSize), freq = new Uint8Array(an.frequencyBinCount);
      let sumSq = 0, n = 0, peak = 0, cenNum = 0, cenDen = 0;
      const start = performance.now();
      await new Promise((res) => {
        const tick = () => {
          an.getFloatTimeDomainData(buf);
          for (let i = 0; i < buf.length; i++) { const v = buf[i]; sumSq += v * v; n++; if (Math.abs(v) > peak) peak = Math.abs(v); }
          an.getByteFrequencyData(freq);
          for (let i = 0; i < freq.length; i++) { const hz = i * ctx.sampleRate / an.fftSize; cenNum += hz * freq[i]; cenDen += freq[i]; }
          if (performance.now() - start > 7000) return res();
          setTimeout(tick, 50);
        };
        tick();
      });
      a.stop();
      await new Promise((r) => setTimeout(r, 400));
      return { rms: Math.sqrt(sumSq / n), peak, centroidHz: cenDen ? cenNum / cenDen : 0 };
    }, skin);
  }
  return out;
}

async function measureSfx(page) {
  const cases = [
    ["confident step", "step", ["continue", 200, 4]],
    ["turn-back", "step", ["back", 200, 4]],
    ["run flurry", "run", ["back"]],
    ["swish", "_swish", []],
  ];
  const out = {};
  for (const [name, fn, args] of cases) {
    out[name] = await page.evaluate(async ({ fn, args }) => {
      const a = window.ambience;
      a.muted = false; a._ensure();
      const ctx = a.ctx, an = ctx.createAnalyser();
      an.fftSize = 2048; a.master.connect(an);
      if (fn === "_swish") a._swish(ctx.currentTime + 0.02, false);
      else a[fn](...args);
      const buf = new Float32Array(an.fftSize);
      let peak = 0, sumSq = 0, n = 0;
      const start = performance.now();
      await new Promise((res) => {
        const tick = () => {
          an.getFloatTimeDomainData(buf);
          for (let i = 0; i < buf.length; i++) { const v = Math.abs(buf[i]); if (v > peak) peak = v; sumSq += buf[i] * buf[i]; n++; }
          if (performance.now() - start > 1600) return res();
          setTimeout(tick, 20);
        };
        tick();
      });
      return { peak, rms: Math.sqrt(sumSq / n) };
    }, { fn, args });
  }
  return out;
}

(async () => {
  const audioJs = fs.readFileSync(AUDIO_JS, "utf8");
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><html><body><button id="sound-toggle"></button></body></html>');
    await page.addScriptTag({ content: audioJs });

    if (doBgm) {
      const bgm = await measureBgm(page);
      console.log("\nBGM (each arc should sit near landing's RMS, distinct centroid):");
      for (const s of SKINS) {
        const r = bgm[s];
        console.log(`  ${s.padEnd(9)} rms=${r.rms.toFixed(5)} peak=${r.peak.toFixed(4)} centroid=${Math.round(r.centroidHz)}Hz`);
      }
    }
    if (doSfx) {
      const sfx = await measureSfx(page);
      console.log("\nSFX (footstep peak should sit near the landing BGM peak, not far above):");
      for (const k of Object.keys(sfx)) {
        console.log(`  ${k.padEnd(14)} peak=${sfx[k].peak.toFixed(4)} rms=${sfx[k].rms.toFixed(5)}`);
      }
    }
    console.log("");
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
