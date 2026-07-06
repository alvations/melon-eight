/* SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 alvations (Melon Lab)
 */
/* Procedural ambience, generated live with the Web Audio API.
 *
 * No audio files: each arc's soundscape is synthesised from oscillators and
 * filtered noise. It is deliberately not music and not eerie stings, just the
 * room tone of the place:
 *   hallway  - fluorescent buzz + ventilation hum, the odd flicker
 *   coach    - rolling rumble + steady rail-joint clacks, an opposing train now and then
 *   stairway - near silence: low room tone, a distant extractor fan, slow wind, echo
 *
 * The three arcs are level-matched to the landing theme (see the per-arc BUS map
 * in play()). The movement SFX play at their natural level.
 *
 * Browsers block audio until a user gesture, so play() is only ever called from
 * a click (entering a loop). A always-visible mute toggle persists the choice.
 */

class Ambience {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.bus = null;
    this.sources = [];
    this.timers = [];
    let muted = false;
    try {
      muted = localStorage.getItem("h8_muted") === "1";
    } catch (e) {} // localStorage can throw on opaque origins / private mode
    this.muted = muted;
    // Master output level. 1.08 = 8% above the old unity level, a small lift to
    // every sound (SFX and the quiet ambience alike) without letting the room
    // tone get loud.
    this.level = 1.08;
  }

  _ensure() {
    if (this.ctx) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    this.ctx = new AC();
    this.master = this.ctx.createGain();
    this.master.gain.value = this.muted ? 0 : this.level;
    this.master.connect(this.ctx.destination);
  }

  _noiseBuffer(seconds) {
    const len = Math.floor(this.ctx.sampleRate * seconds);
    const buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }

  _noise(seconds) {
    const s = this.ctx.createBufferSource();
    s.buffer = this._noiseBuffer(seconds || 3);
    s.loop = true;
    this.sources.push(s);
    return s;
  }

  _osc(type, freq) {
    const o = this.ctx.createOscillator();
    o.type = type;
    o.frequency.value = freq;
    this.sources.push(o);
    return o;
  }

  _gain(v) {
    const g = this.ctx.createGain();
    g.gain.value = v;
    return g;
  }

  _filter(type, freq, q) {
    const f = this.ctx.createBiquadFilter();
    f.type = type;
    f.frequency.value = freq;
    if (q != null) f.Q.value = q;
    return f;
  }

  // a decaying-noise impulse response for a cheap sense of space
  _reverb(seconds, decay) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) {
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
      }
    }
    const c = this.ctx.createConvolver();
    c.buffer = buf;
    return c;
  }

  _mtof(m) {
    return 440 * Math.pow(2, (m - 69) / 12);
  }

  // A short noise source that is NOT tracked (one-shot SFX manage their own
  // lifetime), so repeated sound effects don't grow the sources list.
  _noiseOneShot(seconds) {
    const s = this.ctx.createBufferSource();
    s.buffer = this._noiseBuffer(seconds || 0.3);
    return s;
  }

  // one soft, ringing arpeggio note (bell/harp-like) at a scheduled time
  _pluck(out, verb, freq, t, dur) {
    const o = this.ctx.createOscillator();
    o.type = "triangle";
    o.frequency.value = freq;
    const lp = this._filter("lowpass", 2400, 0.5);
    const g = this._gain(0.0001);
    o.connect(lp).connect(g);
    g.connect(out);
    g.connect(verb);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.9, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0008, t + dur);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  _every(minMs, maxMs, fn) {
    const tick = () => {
      fn();
      const t = setTimeout(tick, minMs + Math.random() * (maxMs - minMs));
      this.timers.push(t);
    };
    const t = setTimeout(tick, minMs + Math.random() * (maxMs - minMs));
    this.timers.push(t);
  }

  // --- per-arc soundscapes -------------------------------------------------

  _hallway(bus) {
    const now = this.ctx.currentTime;
    // mains buzz: a low hum plus a thin harmonic
    const hum = this._osc("sine", 120);
    const humG = this._gain(0.028);
    hum.connect(humG).connect(bus);
    const harm = this._osc("triangle", 240);
    const harmG = this._gain(0.011);
    harm.connect(harmG).connect(bus);
    // faint high whine
    const whine = this._osc("sine", 8200);
    const whineG = this._gain(0.0021);
    whine.connect(whineG).connect(bus);
    // ventilation: brown-ish noise, low-passed
    const vent = this._noise(4);
    const ventG = this._gain(0.046);
    vent.connect(this._filter("lowpass", 320, 0.7)).connect(ventG).connect(bus);
    [hum, harm, whine, vent].forEach((s) => s.start(now));
    // a flicker, soft: a small dip in the hum and a faint crackle, about once
    // every 30 seconds.
    this._every(22000, 40000, () => {
      const t = this.ctx.currentTime;
      humG.gain.setValueAtTime(humG.gain.value, t);
      humG.gain.linearRampToValueAtTime(0.012, t + 0.04);
      humG.gain.linearRampToValueAtTime(0.021, t + 0.25);
      const cr = this._noise(0.2);
      const crG = this._gain(0);
      cr.connect(this._filter("highpass", 2000)).connect(crG).connect(bus);
      cr.start(t);
      crG.gain.setValueAtTime(0.014, t);
      crG.gain.exponentialRampToValueAtTime(0.0004, t + 0.12);
      cr.stop(t + 0.2);
    });
  }

  _coach(bus) {
    const now = this.ctx.currentTime;
    // an almost-empty subway car: a steady, smooth roll, no constant clatter.
    // deep rumble of the car on the rails. The cutoff is opened up from a pure
    // sub-bass floor (which barely reproduces on laptop speakers) to carry some
    // low-mid body, so the car is heard, not just felt.
    const rumble = this._noise(4);
    const rumbleG = this._gain(0.13);
    rumble.connect(this._filter("lowpass", 140, 0.8)).connect(rumbleG).connect(bus);
    // airy hiss of rolling, steady: the mid layer that gives the car presence
    // and sets it apart from the stairwell's still air.
    const roll = this._noise(4);
    const rollG = this._gain(0.05);
    roll.connect(this._filter("bandpass", 700, 0.6)).connect(rollG).connect(bus);
    // a very slow breathing sway in the rumble, so it feels alive but not chuggy
    const sway = this._osc("sine", 0.13);
    const swayG = this._gain(0.021);
    sway.connect(swayG).connect(rumbleG.gain);
    [rumble, roll, sway].forEach((s) => s.start(now));

    // steady rail-joint clacks: soft, evenly spaced knocks of the wheels over
    // the joints. This is what tells the car apart from the stairwell's still
    // room tone. Kept quiet and a touch irregular so it never turns chuggy.
    const railTick = () => {
      const t = this.ctx.currentTime;
      const c = this._noiseOneShot(0.12);
      const bp = this._filter("bandpass", 180, 1.5);
      const g = this._gain(0.0001);
      c.connect(bp).connect(g).connect(bus);
      c.start(t);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(0.034, t + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0004, t + 0.08);
      c.stop(t + 0.14);
      const nx = setTimeout(railTick, 1250 + Math.random() * 550);
      this.timers.push(nx);
    };
    const rt = setTimeout(railTick, 900);
    this.timers.push(rt);

    // a lurch/jerk of the car: a soft low thud with a short rattle. Now that the
    // coach bed is quieter and calmer, its events are spaced out too (about once
    // every 42s), so the car still moves under you but interrupts the quiet less.
    this._every(30000, 54000, () => {
      const t = this.ctx.currentTime;
      const thud = this._osc("sine", 80);
      const tg = this._gain(0.0001);
      thud.connect(tg).connect(bus);
      thud.start(t);
      thud.frequency.setValueAtTime(85, t);
      thud.frequency.exponentialRampToValueAtTime(45, t + 0.4);
      tg.gain.setValueAtTime(0.0001, t);
      tg.gain.linearRampToValueAtTime(0.085, t + 0.03);
      tg.gain.exponentialRampToValueAtTime(0.0005, t + 0.5);
      thud.stop(t + 0.6);
      const r = this._noise(0.5);
      const rg = this._gain(0.0001);
      r.connect(this._filter("bandpass", 320, 1.2)).connect(rg).connect(bus);
      r.start(t);
      rg.gain.setValueAtTime(0.0001, t);
      rg.gain.linearRampToValueAtTime(0.028, t + 0.05);
      rg.gain.exponentialRampToValueAtTime(0.0004, t + 0.4);
      r.stop(t + 0.6);
    });

    // a train passing the other way: a swell that rises and recedes as it goes
    // by. Spaced with the quieter coach bed to about once every 42s (still well
    // inside a normal climb, so it is met, just not as often).
    this._every(30000, 54000, () => {
      const t = this.ctx.currentTime;
      const n = this._noise(4);
      const bp = this._filter("bandpass", 300, 0.9);
      const g = this._gain(0.0001);
      n.connect(bp).connect(g).connect(bus);
      n.start(t);
      bp.frequency.setValueAtTime(260, t);
      bp.frequency.linearRampToValueAtTime(950, t + 1.6);
      bp.frequency.linearRampToValueAtTime(300, t + 3.4);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(0.11, t + 1.6);
      g.gain.linearRampToValueAtTime(0.0001, t + 3.5);
      n.stop(t + 3.7);
    });
  }

  _stairway(bus) {
    const now = this.ctx.currentTime;
    const verb = this._reverb(2.6, 2.2);
    const verbG = this._gain(0.6);
    verb.connect(verbG).connect(bus);
    // Low room tone, continuous, with a little sent to the reverb for space.
    // Quiet, but present: a stairwell is near-silent, not silent.
    const room = this._noise(4);
    const roomG = this._gain(0.082);
    room.connect(this._filter("lowpass", 240, 0.6)).connect(roomG);
    roomG.connect(bus);
    roomG.connect(verb);
    room.start(now);
    // A faint concrete-shaft hum: the building itself, a low steady presence so
    // the arc is not mistaken for muted. Kept soft.
    const hum = this._osc("sine", 66);
    const humG = this._gain(0.044);
    hum.connect(humG).connect(bus);
    const air = this._noise(4);
    const airG = this._gain(0.019);
    air.connect(this._filter("bandpass", 420, 0.5)).connect(airG).connect(bus);
    // A soft ventilation drone: a distant extractor fan somewhere in the shaft.
    // Steady low-passed noise plus a slow tremolo, sitting lower and airier than
    // the coach roll, so the stairwell reads as a still building, not a moving
    // car. Kept quiet so the arc stays near-silent.
    const fan = this._noise(4);
    const fanG = this._gain(0.017);
    fan.connect(this._filter("lowpass", 500, 0.7)).connect(fanG).connect(bus);
    const fanLfo = this._osc("sine", 0.18);
    const fanLfoG = this._gain(0.006);
    fanLfo.connect(fanLfoG).connect(fanG.gain);
    [hum, air, fan, fanLfo].forEach((s) => s.start(now));
    // wind: not constant. A gust that swells and fades into the echo, about
    // once every 30 seconds, so a normal climb meets it.
    this._every(22000, 40000, () => {
      const t = this.ctx.currentTime;
      const w = this._noise(6);
      const bp = this._filter("bandpass", 500, 0.7);
      const g = this._gain(0.0001);
      w.connect(bp).connect(g);
      g.connect(bus);
      g.connect(verb);
      w.start(t);
      bp.frequency.setValueAtTime(300, t);
      bp.frequency.linearRampToValueAtTime(720, t + 2.5);
      bp.frequency.linearRampToValueAtTime(350, t + 5);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(0.07, t + 2);
      g.gain.linearRampToValueAtTime(0.0001, t + 5);
      w.stop(t + 5.3);
    });
  }

  // Landing theme: a soft, slow arpeggio. Wistful fantasy, not epic, not eerie,
  // and quiet enough to stay background. vi-IV-I-V, gently voiced.
  _landing(bus) {
    const verb = this._reverb(3.2, 2.6);
    const verbG = this._gain(0.5);
    verb.connect(verbG).connect(bus);
    const voice = this._gain(0.042); // muted (~70% of the prior level)
    voice.connect(bus);
    // a faint warm pad underneath
    const padG = this._gain(0.0126);
    padG.connect(bus);
    const pad = this._noise(4);
    pad.connect(this._filter("lowpass", 240, 0.5)).connect(padG);
    pad.start(this.ctx.currentTime);

    const chords = [
      [57, 60, 64],        // Am
      [53, 57, 60, 64],    // Fmaj7
      [48, 52, 55, 60],    // C
      [55, 59, 62],        // G
    ];
    const step = 0.22;   // time between notes (slow, calm)
    const ring = 0.95;   // each note rings and overlaps the next
    const perChord = 12;
    let idx = 0;
    let nextTime = this.ctx.currentTime + 0.2;
    const tick = () => {
      const ahead = this.ctx.currentTime + 0.5;
      while (nextTime < ahead) {
        const chord = chords[Math.floor(idx / perChord) % chords.length];
        const tones = chord.concat(chord.map((m) => m + 12));
        const seq = tones.concat(tones.slice(1, -1).reverse());
        const m = seq[idx % seq.length];
        this._pluck(voice, verb, this._mtof(m), nextTime, ring);
        nextTime += step;
        idx++;
      }
      const t = setTimeout(tick, 120);
      this.timers.push(t);
    };
    tick();
  }

  // --- action sound effects -----------------------------------------------
  // A footstep: a soft low heel-thud plus a short scuff. Routed through the
  // master gain so the mute toggle covers it.
  _footstep(t, gain, pitch, bright) {
    const out = this.master;
    const o = this.ctx.createOscillator();
    o.type = "triangle";
    const base = 110 * pitch;
    o.frequency.setValueAtTime(base * 1.7, t);
    o.frequency.exponentialRampToValueAtTime(base * 0.7, t + 0.07);
    const g = this._gain(0.0001);
    o.connect(g).connect(out);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(gain, t + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0006, t + 0.13);
    o.start(t);
    o.stop(t + 0.17);

    const n = this._noiseOneShot(0.2);
    const bp = this._filter("bandpass", 1600 * bright, 0.8);
    const ng = this._gain(0.0001);
    n.connect(bp).connect(ng).connect(out);
    ng.gain.setValueAtTime(0.0001, t);
    ng.gain.linearRampToValueAtTime(gain * 0.5, t + 0.004);
    ng.gain.exponentialRampToValueAtTime(0.0004, t + 0.05);
    n.start(t);
    n.stop(t + 0.12);
  }

  // A brief directional swish, a nod to an old-school scene-change: sweeps up
  // when moving on, down when turning back.
  _swish(t, back) {
    const n = this._noiseOneShot(0.5);
    const bp = this._filter("bandpass", back ? 1600 : 700, 0.7);
    const g = this._gain(0.0001);
    n.connect(bp).connect(g).connect(this.master);
    bp.frequency.setValueAtTime(back ? 1600 : 700, t);
    bp.frequency.exponentialRampToValueAtTime(back ? 600 : 1800, t + 0.28);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.06, t + 0.06);
    g.gain.exponentialRampToValueAtTime(0.0004, t + 0.3);
    n.start(t);
    n.stop(t + 0.4);
  }

  // Play the movement sound for a committed choice. `dwellMs` is how long the
  // player lingered before pressing: a quick, confident press gets real
  // footsteps; a long deliberation softens to a tiptoe, then to near silence.
  step(dir, dwellMs, confidence) {
    this._ensure();
    if (!this.ctx) return;
    if (this.ctx.state === "suspended") this.ctx.resume();
    const t = this.ctx.currentTime + 0.01;
    const back = dir === "back";
    const pitch = back ? 0.82 : 1.0; // turning back sits a touch lower

    // Confidence 0..1: fast presses read as confident; an explicit certainty
    // rating (only 3/4 ever reach a commit) raises it, so "I took my time but
    // I'm sure" still lands firm footsteps rather than a tiptoe.
    let conf = Math.max(0, Math.min(1, 1 - (dwellMs - 500) / 5000));
    if (confidence >= 4) conf = Math.max(conf, 0.95);
    else if (confidence >= 3) conf = Math.max(conf, 0.7);

    const randInt = (lo, hi) => lo + Math.floor(Math.random() * (hi - lo + 1));
    const firm = 0.85 + conf * 0.15; // more certain, a touch firmer

    if (conf >= 0.55) {
      // confident: firm steps (3-5) + a scene-change swish
      const n = randInt(3, 5);
      for (let i = 0; i < n; i++) {
        this._footstep(t + i * 0.185, (0.4 - i * 0.035) * firm, pitch * (1 + i * 0.02), 1.0 + i * 0.03);
      }
      this._swish(t, back);
    } else if (conf >= 0.25) {
      // hesitant: light, slower tiptoe (2-4)
      const n = randInt(2, 4);
      for (let i = 0; i < n; i++) {
        this._footstep(t + i * 0.27, (0.16 - i * 0.02) * firm, pitch * 1.15 * (1 + i * 0.02), 1.4);
      }
    } else {
      // long and unsure: a single, near-silent shuffle
      this._footstep(t, 0.06, pitch * 1.2, 1.6);
    }
  }

  // A quick flurry of light, fast steps: the player hurrying away. Used
  // sparingly (see game.js) when someone bolts back from a changed loop.
  run(dir) {
    this._ensure();
    if (!this.ctx) return;
    if (this.ctx.state === "suspended") this.ctx.resume();
    const t = this.ctx.currentTime + 0.02;
    const pitch = (dir === "back" ? 0.9 : 1.05) * 1.12; // lighter, quicker
    const n = 5 + Math.floor(Math.random() * 3); // 5-7 hurried steps
    for (let i = 0; i < n; i++) {
      this._footstep(t + i * 0.11, 0.2 - i * 0.012, pitch * (1 + i * 0.01), 1.25);
    }
  }

  // --- controls ------------------------------------------------------------

  play(skin) {
    this._ensure();
    if (!this.ctx) return;
    if (this.ctx.state === "suspended") this.ctx.resume();
    this.stop();
    const bus = this.ctx.createGain();
    bus.gain.value = 0.0001;
    bus.connect(this.master);
    this.bus = bus;
    // Per-arc bus level. The room tone runs on this bus; the movement SFX bypass
    // it (they connect straight to master), so lifting only the bus makes the BGM
    // sit up under the footsteps rather than dropping out beneath them. Each arc
    // is calibrated so its measured loudness (RMS) matches the landing theme, so
    // the whole game sits at one level: the low-frequency coach needs the most
    // lift (sub-bass reads quiet), the stairwell the least. See
    // scripts/measure_audio.cjs for how these were derived.
    const BUS = { landing: 1, hallway: 2.2, coach: 0.8, stairway: 1.48 };
    const busLevel = BUS[skin] || 2.2;
    if (skin === "coach") this._coach(bus);
    else if (skin === "stairway") this._stairway(bus);
    else if (skin === "landing") this._landing(bus);
    else this._hallway(bus);
    // fade in
    const t = this.ctx.currentTime;
    bus.gain.setValueAtTime(0.0001, t);
    bus.gain.exponentialRampToValueAtTime(busLevel, t + 1.5);
  }

  stop() {
    this.timers.forEach((t) => clearTimeout(t));
    this.timers = [];
    const bus = this.bus;
    const srcs = this.sources;
    this.bus = null;
    this.sources = [];
    if (!bus) return;
    const t = this.ctx.currentTime;
    try {
      bus.gain.cancelScheduledValues(t);
      bus.gain.setValueAtTime(bus.gain.value, t);
      bus.gain.exponentialRampToValueAtTime(0.0001, t + 0.3);
    } catch (e) {}
    setTimeout(() => {
      srcs.forEach((s) => {
        try { s.stop(); } catch (e) {}
        try { s.disconnect(); } catch (e) {}
      });
      try { bus.disconnect(); } catch (e) {}
    }, 350);
  }

  setMuted(m) {
    this.muted = m;
    try {
      localStorage.setItem("h8_muted", m ? "1" : "0");
    } catch (e) {}
    if (this.master && this.ctx) {
      const t = this.ctx.currentTime;
      this.master.gain.cancelScheduledValues(t);
      this.master.gain.linearRampToValueAtTime(m ? 0 : this.level, t + 0.2);
    }
  }

  toggle() {
    this.setMuted(!this.muted);
    return this.muted;
  }

  // Resume a suspended context from inside a user gesture. iOS/Safari, and
  // mobile Chrome inside a cross-origin iframe (as the game runs on Spaces),
  // only start audio if resume() is called synchronously within the gesture
  // handler; a resume() that runs after an await (e.g. once an arc's fetch has
  // resolved) is ignored. So this must be called first thing on the gesture,
  // before any async work. Returns true once the context is actually running.
  unlock() {
    this._ensure();
    if (!this.ctx) return false;
    if (this.ctx.state === "suspended") {
      try { this.ctx.resume(); } catch (e) {}
    }
    return this.ctx.state === "running";
  }

  // Localized aria-labels for the mute toggle, handed in by the UI layer once the
  // catalog loads. Falls back to English until then.
  setLabels(on, off) {
    this.labelOn = on;
    this.labelOff = off;
    if (this._repaint) this._repaint();
  }
}

window.ambience = new Ambience();

// Wire the always-visible mute toggle. Drawn as a minimal line icon (not an
// emoji) so it matches the game's quiet, monochrome look and inherits the
// chrome-tier colour: a speaker cone with two sound waves, or with a small X
// when muted.
(function () {
  const btn = document.getElementById("sound-toggle");
  if (!btn) return;
  const CONE = "M4 9 H7 L11 5.5 V16.5 L7 13 H4 Z";
  const svg = (inner) =>
    '<svg viewBox="0 0 22 22" width="20" height="20" fill="none" ' +
    'stroke="currentColor" stroke-width="1.4" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' + inner + "</svg>";
  const ON = svg(
    `<path d="${CONE}"/>` +
    '<path d="M14.3 8.8 Q16 11 14.3 13.2"/>' +
    '<path d="M16.6 6.8 Q19.4 11 16.6 15.2"/>'
  );
  const OFF = svg(
    `<path d="${CONE}"/>` +
    '<path d="M14.7 8.6 L18.6 13.4"/>' +
    '<path d="M18.6 8.6 L14.7 13.4"/>'
  );
  const paint = () => {
    const a = window.ambience;
    btn.innerHTML = a.muted ? OFF : ON;
    btn.setAttribute(
      "aria-label",
      a.muted ? (a.labelOff || "Sound off") : (a.labelOn || "Sound on")
    );
  };
  window.ambience._repaint = paint;   // so setLabels() can refresh the label
  paint();
  btn.addEventListener("click", () => {
    window.ambience.toggle();
    paint();
  });
})();
