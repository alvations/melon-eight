// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Worked, RUNNABLE examples of melodic BGM built from the game's own synth
// toolkit (static/audio.js). This is the proof, and the starting kit, for the
// claim in docs/AUDIO.md that the synth is a general instrument: the same
// primitives that make the game's room tone also make joyful, heroic, eerie, and
// chiptune themes. Each example corresponds to a prompt in docs/AUDIO.md.
//
// It renders each theme to a short WebM you can listen to, and SELF-VERIFIES:
// every theme must produce audible output, or the script exits non-zero. That is
// how "make sure the prompts work" is kept honest.
//
// Usage:
//   node scripts/examples/melodic_themes.cjs [seconds] [outDir]
//   node scripts/examples/melodic_themes.cjs 6 ./theme-out
//
// Portable browser resolution: see scripts/browser.cjs.

const fs = require("fs");
const path = require("path");
const { loadPlaywright, chromiumLaunchOptions } = require("../browser.cjs");
const playwright = loadPlaywright();

const AUDIO_JS = path.join(__dirname, "..", "..", "static", "audio.js");
const SECONDS = parseFloat(process.argv[2] || "6");
const OUT = process.argv[3] || "./theme-out";
fs.mkdirSync(OUT, { recursive: true });

// Each theme is a builder body (string) added to Ambience.prototype in the page.
// They use only toolkit primitives (_pluck, _osc, _gain, _filter, _reverb,
// _mtof, this.ctx, this.timers). `bus` is the destination gain.
const THEMES = {
  // Prompt: "joyful, upbeat town music, bright and bouncy."
  // Major key, I-V-vi-IV, fast step, short ring, triangle up an octave, light reverb.
  joyful_town: `
    const verb=this._reverb(1.6,2.0),vg=this._gain(0.18);verb.connect(vg).connect(bus);
    const lead=this._gain(0.06);lead.connect(bus);
    const chords=[[60,64,67],[55,59,62],[57,60,64],[53,57,60]]; // I V vi IV in C
    const step=0.14,ring=0.28,per=8;let i=0,t=this.ctx.currentTime+0.1;
    const go=()=>{const a=this.ctx.currentTime+0.4;while(t<a){const c=chords[Math.floor(i/per)%4];
      const up=c.concat(c.map(m=>m+12));this._pluck(lead,verb,this._mtof(up[i%up.length]),t,ring);
      if(i%4===0)this._pluck(lead,verb,this._mtof(c[0]-12),t,0.5);t+=step;i++;}
      this.timers.push(setTimeout(go,60));};go();`,

  // Prompt: "warm, heroic, hopeful theme, like arriving somewhere important."
  // Major, IV-I-V-vi, slower, longer ring, a fifth stacked for weight.
  heroic: `
    const verb=this._reverb(2.4,2.4),vg=this._gain(0.3);verb.connect(vg).connect(bus);
    const lead=this._gain(0.055);lead.connect(bus);
    const chords=[[53,57,60,64],[48,52,55,60],[55,59,62,67],[57,60,64]];
    const step=0.2,ring=0.6,per=6;let i=0,t=this.ctx.currentTime+0.1;
    const go=()=>{const a=this.ctx.currentTime+0.4;while(t<a){const c=chords[Math.floor(i/per)%4];
      this._pluck(lead,verb,this._mtof(c[i%c.length]+12),t,ring);
      if(i%3===0)this._pluck(lead,verb,this._mtof(c[0]-12),t,0.9);t+=step;i++;}
      this.timers.push(setTimeout(go,60));};go();`,

  // Prompt: "eerie, unsettling, dreamlike, sparse."
  // Minor key, slow, long ring, heavy reverb, low octave.
  eerie: `
    const verb=this._reverb(3.4,2.8),vg=this._gain(0.6);verb.connect(vg).connect(bus);
    const lead=this._gain(0.05);lead.connect(bus);
    const chords=[[57,60,64],[56,59,63],[53,56,60],[55,58,62]]; // Am-ish, drifting
    const step=0.34,ring=1.0,per=5;let i=0,t=this.ctx.currentTime+0.1;
    const go=()=>{const a=this.ctx.currentTime+0.5;while(t<a){const c=chords[Math.floor(i/per)%4];
      this._pluck(lead,verb,this._mtof(c[i%c.length]-12),t,ring);t+=step;i++;}
      this.timers.push(setTimeout(go,80));};go();`,

  // Prompt: "playful 8-bit chiptune, fast and square."
  // Square-wave lead (a tiny inline note using _osc), very fast, short.
  chiptune: `
    const lead=this._gain(0.05);lead.connect(bus);
    const note=(freq,t,dur)=>{const o=this.ctx.createOscillator();o.type='square';o.frequency.value=freq;
      const g=this._gain(0.0001);o.connect(g).connect(lead);g.gain.setValueAtTime(0.0001,t);
      g.gain.exponentialRampToValueAtTime(0.5,t+0.005);g.gain.exponentialRampToValueAtTime(0.0008,t+dur);
      o.start(t);o.stop(t+dur+0.02);};
    const chords=[[60,64,67],[55,59,62],[57,60,64],[53,57,60]];
    const step=0.1,ring=0.09,per=8;let i=0,t=this.ctx.currentTime+0.1;
    const go=()=>{const a=this.ctx.currentTime+0.35;while(t<a){const c=chords[Math.floor(i/per)%4];
      const up=c.concat(c.map(m=>m+12));note(this._mtof(up[i%up.length]),t,ring);
      if(i%4===0)note(this._mtof(c[0]-12),t,0.16);t+=step;i++;}
      this.timers.push(setTimeout(go,50));};go();`,
};

async function renderTheme(page, body, ms) {
  return await page.evaluate(async ({ body, ms }) => {
    const A = window.ambience.constructor;
    A.prototype._demoTheme = new Function("bus", body);
    const a = window.ambience; a.muted = false; a._ensure(); a.stop();
    const bus = a.ctx.createGain(); bus.gain.value = 1; bus.connect(a.master); a.bus = bus;
    const dest = a.ctx.createMediaStreamDestination(); a.master.connect(dest);
    const rec = new MediaRecorder(dest.stream, { mimeType: "audio/webm" });
    const chunks = []; rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    const stopped = new Promise((r) => (rec.onstop = r));
    const an = a.ctx.createAnalyser(); a.master.connect(an); const buf = new Float32Array(an.fftSize);
    rec.start();
    a._demoTheme(bus);
    let peak = 0;
    const start = performance.now();
    while (performance.now() - start < ms) {
      an.getFloatTimeDomainData(buf);
      for (let i = 0; i < buf.length; i++) peak = Math.max(peak, Math.abs(buf[i]));
      await new Promise((r) => setTimeout(r, 50));
    }
    a.stop(); rec.stop(); await stopped;
    const blob = new Blob(chunks, { type: "audio/webm" });
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let s = ""; for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return { b64: btoa(s), peak };
  }, { body, ms });
}

(async () => {
  const audioJs = fs.readFileSync(AUDIO_JS, "utf8");
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  let silent = [];
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><body><button id="sound-toggle"></button></body>');
    await page.addScriptTag({ content: audioJs });
    for (const [name, body] of Object.entries(THEMES)) {
      const { b64, peak } = await renderTheme(page, body, Math.round(SECONDS * 1000));
      const file = path.join(OUT, `${name}.webm`);
      fs.writeFileSync(file, Buffer.from(b64, "base64"));
      const ok = peak > 0.01;
      console.log(`${ok ? "OK  " : "SILENT"} ${name.padEnd(12)} peak=${peak.toFixed(4)} -> ${file}`);
      if (!ok) silent.push(name);
    }
  } finally {
    await browser.close();
  }
  if (silent.length) { console.error("FAIL: silent themes:", silent.join(", ")); process.exit(1); }
  console.log("\nAll themes produced audible output.");
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
