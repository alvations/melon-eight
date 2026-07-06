// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Worked, RUNNABLE examples of sound EFFECTS built from the game's synth toolkit
// (static/audio.js). Companion to scripts/examples/melodic_themes.cjs: the same
// primitives that make the game's footstep and swish also make pickups, chimes,
// thunks, error buzzes, and whooshes. Each example corresponds to a prompt in
// docs/AUDIO.md.
//
// It renders each effect to a short WebM you can listen to, and SELF-VERIFIES:
// every effect must produce audible output, or the script exits non-zero.
//
// Nothing here is Claude-specific: an effect is just a few lines of Web Audio
// (an envelope on an oscillator or a noise burst), so any model that writes
// JavaScript, driven by Claude Code with any backend, can author these.
//
// Usage:
//   node scripts/examples/sfx_kit.cjs [outDir]
//   node scripts/examples/sfx_kit.cjs ./sfx-out
//
// Portable browser resolution: see scripts/browser.cjs.

const fs = require("fs");
const path = require("path");
const { loadPlaywright, chromiumLaunchOptions } = require("../browser.cjs");
const playwright = loadPlaywright();

const AUDIO_JS = path.join(__dirname, "..", "..", "static", "audio.js");
const OUT = process.argv[2] || "./sfx-out";
fs.mkdirSync(OUT, { recursive: true });

// Each effect is a function body added to Ambience.prototype and fired once. `out`
// is this.master (SFX bypass the ambience bus, as the real ones do). Uses toolkit
// primitives: _osc, _gain, _filter, _noiseOneShot, _pluck, _mtof, this.ctx.
const SFX = {
  // Prompt: "a bright pickup/coin blip, two quick rising notes."
  pickup: `
    const out=this.master,t=this.ctx.currentTime+0.02;
    const blip=(f,at,d)=>{const o=this.ctx.createOscillator();o.type='square';o.frequency.value=f;
      const g=this._gain(0.0001);o.connect(g).connect(out);g.gain.setValueAtTime(0.0001,at);
      g.gain.exponentialRampToValueAtTime(0.4,at+0.005);g.gain.exponentialRampToValueAtTime(0.0008,at+d);
      o.start(at);o.stop(at+d+0.02);};
    blip(this._mtof(72),t,0.09);blip(this._mtof(79),t+0.09,0.14);`,

  // Prompt: "a warm success chime, a little major arpeggio."
  chime_success: `
    const out=this.master,t=this.ctx.currentTime+0.02;
    const verb=this._reverb(1.2,2.0),vg=this._gain(0.25);verb.connect(vg).connect(out);
    [60,64,67,72].forEach((m,i)=>this._pluck(out,verb,this._mtof(m),t+i*0.08,0.5));`,

  // Prompt: "a soft low door thunk, a closing sound."
  thunk_door: `
    const out=this.master,t=this.ctx.currentTime+0.02;
    const o=this.ctx.createOscillator();o.type='sine';const g=this._gain(0.0001);o.connect(g).connect(out);
    o.frequency.setValueAtTime(120,t);o.frequency.exponentialRampToValueAtTime(48,t+0.18);
    g.gain.setValueAtTime(0.0001,t);g.gain.linearRampToValueAtTime(0.5,t+0.01);g.gain.exponentialRampToValueAtTime(0.0006,t+0.35);
    o.start(t);o.stop(t+0.4);
    const n=this._noiseOneShot(0.2),ng=this._gain(0.0001);n.connect(this._filter('lowpass',400,1)).connect(ng).connect(out);
    ng.gain.setValueAtTime(0.3,t);ng.gain.exponentialRampToValueAtTime(0.0004,t+0.12);n.start(t);n.stop(t+0.2);`,

  // Prompt: "a harsh error buzz, a wrong-answer sound."
  error_buzz: `
    const out=this.master,t=this.ctx.currentTime+0.02;
    const mk=(f)=>{const o=this.ctx.createOscillator();o.type='sawtooth';o.frequency.value=f;
      const g=this._gain(0.0001);o.connect(g).connect(out);g.gain.setValueAtTime(0.0001,t);
      g.gain.linearRampToValueAtTime(0.18,t+0.01);g.gain.setValueAtTime(0.18,t+0.22);
      g.gain.exponentialRampToValueAtTime(0.0006,t+0.32);o.start(t);o.stop(t+0.34);};
    mk(110);mk(116.5);`,

  // Prompt: "a quick whoosh, a transition sweep."
  whoosh: `
    const out=this.master,t=this.ctx.currentTime+0.02;
    const n=this._noiseOneShot(0.6),bp=this._filter('bandpass',600,0.8),g=this._gain(0.0001);
    n.connect(bp).connect(g).connect(out);
    bp.frequency.setValueAtTime(300,t);bp.frequency.exponentialRampToValueAtTime(2600,t+0.3);
    g.gain.setValueAtTime(0.0001,t);g.gain.linearRampToValueAtTime(0.35,t+0.08);g.gain.exponentialRampToValueAtTime(0.0004,t+0.42);
    n.start(t);n.stop(t+0.5);`,

  // The game's own footstep + swish, for reference (already in audio.js).
  footstep_ref: `this.step('continue',200,4);`,
};

async function renderSfx(page, body) {
  return await page.evaluate(async ({ body }) => {
    const A = window.ambience.constructor;
    A.prototype._demoSfx = new Function(body);
    const a = window.ambience; a.muted = false; a._ensure();
    const dest = a.ctx.createMediaStreamDestination(); a.master.connect(dest);
    const rec = new MediaRecorder(dest.stream, { mimeType: "audio/webm" });
    const chunks = []; rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    const stopped = new Promise((r) => (rec.onstop = r));
    const an = a.ctx.createAnalyser(); a.master.connect(an); const buf = new Float32Array(an.fftSize);
    rec.start();
    a._demoSfx();
    let peak = 0; const start = performance.now();
    while (performance.now() - start < 1300) {
      an.getFloatTimeDomainData(buf);
      for (let i = 0; i < buf.length; i++) peak = Math.max(peak, Math.abs(buf[i]));
      await new Promise((r) => setTimeout(r, 40));
    }
    rec.stop(); await stopped;
    const bytes = new Uint8Array(await new Blob(chunks, { type: "audio/webm" }).arrayBuffer());
    let s = ""; for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return { b64: btoa(s), peak };
  }, { body });
}

(async () => {
  const audioJs = fs.readFileSync(AUDIO_JS, "utf8");
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  let silent = [];
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><body><button id="sound-toggle"></button></body>');
    await page.addScriptTag({ content: audioJs });
    for (const [name, body] of Object.entries(SFX)) {
      const { b64, peak } = await renderSfx(page, body);
      const file = path.join(OUT, `${name}.webm`);
      fs.writeFileSync(file, Buffer.from(b64, "base64"));
      const ok = peak > 0.01;
      console.log(`${ok ? "OK  " : "SILENT"} ${name.padEnd(14)} peak=${peak.toFixed(4)} -> ${file}`);
      if (!ok) silent.push(name);
    }
  } finally {
    await browser.close();
  }
  if (silent.length) { console.error("FAIL: silent effects:", silent.join(", ")); process.exit(1); }
  console.log("\nAll effects produced audible output.");
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
