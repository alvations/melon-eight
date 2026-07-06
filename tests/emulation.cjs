// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Browser emulation tests for the client rendering mechanisms that unit tests
// cannot reach: reduced-motion rendering, Act 2 touch verbs + flavour line, the
// inspect aside, and the alternate-ending achievement gate. Driven with a real
// (headless) Chromium via Playwright.
//
// Usage:  node tests/emulation.cjs <baseURL> [chromiumPath]
// Exits 0 if every check passes, 1 otherwise. Prints PASS/FAIL per check.
//
// It is normally run by tests/test_emulation.py, which boots the app and skips
// gracefully when Chromium/Playwright are unavailable.

const BASE = process.argv[2] || "http://127.0.0.1:8078";
const CHROMIUM = process.argv[3];   // optional explicit Chromium path override

// Portable toolchain resolution (see scripts/browser.cjs): works in a plain
// checkout after `npm install && npx playwright install chromium`, or in a
// preconfigured sandbox. An explicit path can still be passed as argv[3].
const { loadPlaywright, chromiumLaunchOptions } = require("../scripts/browser.cjs");
const playwright = loadPlaywright();
const launchOpts = CHROMIUM ? { executablePath: CHROMIUM, args: ["--autoplay-policy=no-user-gesture-required"] } : chromiumLaunchOptions();

const results = [];
function check(name, ok, detail) {
  results.push({ name, ok: !!ok, detail: detail || "" });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok ? "" : "  :: " + (detail || "")}`);
}

async function newPage(browser, { reduce = false, deterministic = false } = {}) {
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  if (deterministic) await p.addInitScript(() => { Math.random = () => 0; });
  // seed: skip first-run suppression for all arcs, optional reduce-motion
  await p.goto(BASE);
  await p.evaluate((r) => {
    if (r) localStorage.setItem("h8_motion", "1");
    localStorage.setItem("h8_mem", JSON.stringify({ v: 1, arcStarted: { "stairway8": true, "hallway-eight": true, "coach8": true } }));
  }, reduce);
  await p.goto(BASE);
  await p.waitForTimeout(300);
  return p;
}

async function enter(p, arc) {
  await p.evaluate((a) => document.querySelector(`[data-arc="${a}"]`)?.click(), arc);
  await p.waitForTimeout(600);
  await p.click("#begin").catch(() => {});
  await p.evaluate(() => document.querySelectorAll(".cutscene-overlay:not(.hidden),#learn:not(.hidden)").forEach(o => o.querySelector("button")?.click()));
  await p.waitForSelector("#controls:not(.hidden)", { timeout: 8000 });
  await p.waitForTimeout(250);
}

// advance one loop; handle the (possibly always-on) doubt prompt
async function commit(p, reduce) {
  await p.evaluate(() => document.querySelector('.choice[data-choice="continue"]')?.click());
  await p.waitForTimeout(120);
  await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
  await p.waitForTimeout(reduce ? 1400 : 1900);
  await p.waitForSelector("#controls:not(.hidden)", { timeout: 8000 }).catch(() => {});
  await p.waitForTimeout(reduce ? 150 : 250);
}

(async () => {
  const browser = await playwright.chromium.launch(launchOpts);
  try {
    // 1) Reduced motion: prose renders in canonical order, fully visible.
    {
      const p = await newPage(browser, { reduce: true });
      await enter(p, "stairway8");
      const s = await p.evaluate(() => {
        const lines = [...document.querySelectorAll("#prose .line")];
        const domOrder = lines.map(l => l.dataset.prop);
        let serverOrder = []; try { serverOrder = (current.room.shown || []); } catch (e) {}
        const allVisible = lines.every(l => l.classList.contains("show") && parseFloat(getComputedStyle(l).opacity) > 0.9);
        return { domOrder, serverOrder, allVisible, corridorHidden: document.querySelector("#corridor").classList.contains("hidden") };
      });
      check("reduce-motion prose in canonical order", JSON.stringify(s.domOrder) === JSON.stringify(s.serverOrder), `${JSON.stringify(s.domOrder)} vs ${JSON.stringify(s.serverOrder)}`);
      check("reduce-motion prose fully visible at settle", s.allVisible && !s.corridorHidden);
      await p.context().close();
    }

    // 2) Reduced motion does NOT hide the Act 2 verbs: once past the onset the
    //    touch buttons render AND are actually visible (real box + opacity).
    //    Tested at the gate directly so it is deterministic (not dependent on
    //    reaching a given level through play).
    {
      const p = await newPage(browser, { reduce: true, deterministic: true });
      await enter(p, "stairway8");
      const s = await p.evaluate(() => {
        const fake = { level: 4, room: { touch: [
          { prop: "door", verb: "try the door" },
          { prop: "railing", verb: "grip the rail" },
        ] } };
        buildTouch(fake);
        const btns = [...document.querySelectorAll(".touch-btn")];
        const vis = btns.filter(b => { const r = b.getBoundingClientRect(); return r.width > 2 && r.height > 2 && parseFloat(getComputedStyle(b).opacity) > 0.05; });
        const n = btns.length, v = vis.length;
        clearTouch();
        return { n, v };
      });
      check("reduce-motion: Act 2 verbs render and are visible past the onset", s.n > 0 && s.v === s.n, `visible ${s.v}/${s.n}`);
      await p.context().close();
    }

    // 3) Flavour line: clicking a verb shows the line, which then auto-fades,
    //    and the fade is visible under reduced motion.
    {
      const p = await newPage(browser, { reduce: true, deterministic: true });
      await enter(p, "stairway8");
      // Force a verb past the onset (level 4) so the click path is deterministic,
      // then click it. (Reaching a verb through play is level-gated now.)
      const clicked = await p.evaluate(() => {
        buildTouch({ level: 4, room: { touch: [{ prop: "door", verb: "try the door" }] } });
        const b = document.querySelector(".touch-btn");
        if (b) { b.click(); return true; }
        return false;
      });
      check("flavour line: a verb was available to click", clicked);
      if (clicked) {
        await p.waitForTimeout(800);
        const shown = await p.evaluate(() => { const e = document.querySelector("#touch-line"); return { op: parseFloat(getComputedStyle(e).opacity), txt: (e.textContent || "").length }; });
        check("flavour line appears on click", shown.op > 0.5 && shown.txt > 0, `opacity ${shown.op}`);
        // transition kept alive under reduced motion (so a fade is possible)
        const trans = await p.evaluate(() => getComputedStyle(document.querySelector("#touch-line")).transitionDuration);
        check("flavour line keeps a fade under reduced motion", parseFloat(trans) >= 0.3, `transition-duration ${trans}`);
        await p.waitForTimeout(5200);   // past the 4.5s auto-fade
        const faded = await p.evaluate(() => parseFloat(getComputedStyle(document.querySelector("#touch-line")).opacity));
        check("flavour line auto-fades after a readable dwell", faded < 0.2, `opacity ${faded}`);
      }
      await p.context().close();
    }

    // 4) Alternate-ending achievement is gated: never unlocked by ordinary play,
    //    and its predicate reflects mem.ends exactly.
    {
      const p = await newPage(browser, { reduce: false });
      await enter(p, "hallway-eight");
      for (let i = 0; i < 4; i++) await commit(p, false);
      const a = await p.evaluate(() => {
        const ach = computeAch();
        const anyEnd = Object.keys(ach).some(k => k.startsWith("end_") && ach[k]);
        const endsEmpty = !mem.ends || Object.keys(mem.ends).length === 0;
        return { anyEnd, endsEmpty };
      });
      check("end_ achievement NOT unlocked by ordinary play", !a.anyEnd && a.endsEmpty);
      const b = await p.evaluate(() => { mem.ends = mem.ends || {}; mem.ends["hallway-eight"] = true; return computeAch()["end_hallway-eight"]; });
      check("end_ predicate reflects mem.ends", b === true);
      await p.context().close();
    }

    // 5) Ending credits + adaptive nudge.
    {
      const p = await newPage(browser, { reduce: false });
      await enter(p, "hallway-eight");
      const cr = await p.evaluate(() => {
        openCredits();
        const open = !document.querySelector("#credits").classList.contains("hidden");
        const roll = document.querySelector("#credits-roll").textContent;
        closeCredits();
        return { open, hasTitle: roll.includes("EIGHT"), hasMaker: roll.includes("alvations"), hasStudio: roll.toUpperCase().includes("MELON LAB") };
      });
      check("credits open with our own roll content", cr.open && cr.hasTitle && cr.hasMaker && cr.hasStudio);

      // "View credits" is gated on having won at least once.
      const gate = await p.evaluate(() => {
        mem.wins = {}; renderAchievements();
        const hiddenNoWin = document.querySelector("#credits-row").classList.contains("hidden");
        mem.wins = { "hallway-eight": 1 }; renderAchievements();
        const shownWithWin = !document.querySelector("#credits-row").classList.contains("hidden");
        return { hiddenNoWin, shownWithWin };
      });
      check("View credits appears only after a win", gate.hiddenNoWin && gate.shownWithWin);

      // The adaptive nudge changes tier with fragment progress.
      const nud = await p.evaluate(() => {
        const arc = "hallway-eight";
        const total = (ARCS_BY_ID[arc].flashbacks) || 8;
        mem.flash = {}; buildNudge(arc);
        const frags = document.querySelector("#nudge").textContent;
        mem.flash = { [arc]: Array.from({ length: total }, (_, i) => i) }; buildNudge(arc);
        const arcs = document.querySelector("#nudge").textContent;
        ["hallway-eight", "stairway8", "coach8"].forEach(a => { const t = (ARCS_BY_ID[a].flashbacks) || 8; mem.flash[a] = Array.from({ length: t }, (_, i) => i); });
        buildNudge(arc);
        const eight = document.querySelector("#nudge").textContent;
        return { frags, arcs, eight };
      });
      check("nudge tier 1: unseen fragments here", /\d/.test(nud.frags) && nud.frags !== nud.arcs);
      check("nudge tier 2: other places (distinct)", nud.arcs && nud.arcs !== nud.frags && nud.arcs !== nud.eight);
      check("nudge tier 3: eight escapes (distinct)", nud.eight && nud.eight !== nud.arcs);
      await p.context().close();
    }

    // 6) Under reduced motion the credits roll does not animate (reads static).
    {
      const p = await newPage(browser, { reduce: true });
      await enter(p, "stairway8");
      const anim = await p.evaluate(() => {
        openCredits();
        const name = getComputedStyle(document.querySelector("#credits-roll")).animationName;
        closeCredits();
        return name;
      });
      check("reduced-motion credits are static (no roll animation)", anim === "none");
      await p.context().close();
    }

    // 7) Erase wipes the local memory, and only behind the confirm gate.
    {
      const p = await newPage(browser, { reduce: false });
      await enter(p, "hallway-eight");
      const r = await p.evaluate(() => {
        mem.wins = { "hallway-eight": 3 }; mem.flash = { "hallway-eight": [0, 1] }; saveMem();
        const before = Object.values(computeAch()).some(Boolean);
        document.querySelector("#ach-erase").click();
        const confirmShown = !document.querySelector("#erase-confirm").classList.contains("hidden");
        document.querySelector("#erase-cancel").click();
        const keptOnCancel = (mem.wins["hallway-eight"] || 0);
        document.querySelector("#ach-erase").click();
        document.querySelector("#erase-ok").click();
        localStorage.setItem("h8_onboarded", "1");   // mark the rule as seen
        document.querySelector("#ach-erase").click();
        document.querySelector("#erase-ok").click();
        const winsAfter = Object.keys(mem.wins || {}).length;
        const anyAch = Object.values(computeAch()).some(Boolean);
        const storedGone = !localStorage.getItem("h8_mem") || localStorage.getItem("h8_mem").indexOf('"hallway-eight":3') === -1;
        const onboardCleared = !localStorage.getItem("h8_onboarded");
        return { before, confirmShown, keptOnCancel, winsAfter, anyAch, storedGone, onboardCleared };
      });
      check("erase is gated behind a confirm dialog", r.before && r.confirmShown);
      check("cancel keeps the memory", r.keptOnCancel === 3);
      check("erase wipes runs, achievements, and storage", r.winsAfter === 0 && !r.anyAch && r.storedGone);
      check("erase also forgets the onboarding (instructions return)", r.onboardCleared);
      await p.context().close();
    }

    // 7a2) First-reset onboarding gates the loop controls: the instructions come
    //      up on the first reset and the level-0 controls must NOT go live behind
    //      the rule cutscene, or the player could cross into level 1 before ever
    //      seeing the instructions (the reported lag bug). newPage does not set
    //      h8_onboarded, so a fresh reset triggers onboarding.
    {
      const p = await newPage(browser, { reduce: false });
      await enter(p, "hallway-eight");
      // Force a reset: turning back on level 0 is a false alarm (~98% clean), so it
      // is a wrong call and resets. Retry a few times to be robust to the rare
      // opening anomaly, until the onboarding overlay appears.
      let onboarded = false;
      for (let k = 0; k < 5 && !onboarded; k++) {
        await p.evaluate(() => document.querySelector('.choice[data-choice="back"]')?.click());
        await p.waitForTimeout(160);
        await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
        onboarded = await p.waitForFunction(() => {
          const cut = !document.querySelector("#cutscene").classList.contains("hidden");
          const learn = !document.querySelector("#learn").classList.contains("hidden");
          return cut || learn;
        }, { timeout: 6000 }).then(() => true).catch(() => false);
      }
      check("first reset triggers the onboarding", onboarded);
      // Invariant: while the onboarding (cutscene or instructions) is up, the loop
      // controls stay hidden, so no call can be committed to cross level 0.
      let leaked = false;
      for (let i = 0; i < 30; i++) {
        const s = await p.evaluate(() => ({
          learn: !document.querySelector("#learn").classList.contains("hidden"),
          controls: !document.querySelector("#controls").classList.contains("hidden"),
        }));
        if (s.controls) { leaked = true; break; }   // controls live during onboarding = the bug
        if (s.learn) break;                          // reached the instructions, still gated
        await p.waitForTimeout(300);
      }
      check("onboarding gates the controls (cannot cross level 0 first)", !leaked);
      // Dismissing the instructions hands the loop back.
      await p.waitForSelector("#learn:not(.hidden)", { timeout: 12000 }).catch(() => {});
      await p.evaluate(() => document.querySelector("#learn-go")?.click());
      const back = await p.waitForSelector("#controls:not(.hidden)", { timeout: 6000 }).then(() => true).catch(() => false);
      check("dismissing the instructions hands the controls back", back);
      await p.context().close();
    }

    // 7b) Act 2 onset: touch verbs hold back through the opening loops and appear
    //     reliably from the mid-climb on (level >= 3). Tested at the gate directly.
    {
      const p = await newPage(browser, { reduce: false, deterministic: true });
      await enter(p, "hallway-eight");   // arcStarted seeded -> firstArcRun false, onset 3
      const counts = await p.evaluate(() => {
        const fake = (level) => ({ level, room: { touch: [
          { prop: "door", verb: "try the door" },
          { prop: "poster", verb: "read the poster" },
        ] } });
        const out = {};
        [0, 1, 2, 3, 4, 5].forEach((L) => { buildTouch(fake(L)); out[L] = document.querySelectorAll(".touch-btn").length; });
        clearTouch();
        return out;
      });
      const below = [0, 1, 2].every((L) => counts[L] === 0);
      const at = [3, 4, 5].every((L) => counts[L] > 0);
      check("Act 2 verbs hold back below the onset (level < 3)", below, JSON.stringify(counts));
      check("Act 2 verbs appear from the onset (level >= 3)", at, JSON.stringify(counts));
      await p.context().close();
    }

    // 7c) A network failure mid-commit recovers instead of soft-locking the run:
    //     the controls return so the same call can simply be made again.
    {
      const p = await newPage(browser, { reduce: false });
      await enter(p, "hallway-eight");
      let dropped = false;
      await p.route("**/api/act", (route) => {
        if (!dropped) { dropped = true; return route.abort(); }
        return route.continue();
      });
      // commit (click choice, answer the doubt prompt if it shows)
      await p.evaluate(() => document.querySelector('.choice[data-choice="continue"]')?.click());
      await p.waitForTimeout(160);
      await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
      // recovery resyncs via /api/room and re-renders, so controls return after the
      // reveal (not instantly); wait for them.
      const recovered = await p.waitForSelector("#controls:not(.hidden)", { timeout: 9000 }).then(() => true).catch(() => false);
      check("network failure mid-commit recovers (controls return)", recovered);
      // the retry now succeeds and the loop advances (controls return after the
      // next room finishes revealing; the closing-beat makes that reveal longer)
      await p.unroute("**/api/act");
      await p.evaluate(() => document.querySelector('.choice[data-choice="continue"]')?.click());
      await p.waitForTimeout(160);
      await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
      const advanced = await p.waitForSelector("#controls:not(.hidden)", { timeout: 9000 }).then(() => true).catch(() => false);
      check("after a failed commit, the next commit still advances", advanced);
      await p.context().close();
    }

    // 8) The win screen itself renders (guards showWin / setAgainMode wiring; a
    //    scope bug here would silently break every win).
    {
      const p = await newPage(browser, { reduce: false });
      await enter(p, "hallway-eight");
      const r = await p.evaluate(() => {
        winIsFirst = true;
        showWin({ win_text: ["You are out."], attempts: 1, attempt_text: "", stats: {} });
        const shown = !document.querySelector("#win").classList.contains("hidden");
        const again = document.querySelector("#again").textContent;
        // The linger auto-roll (same path the 20s timer fires) opens the credits,
        // and closing hands back the replay button + reveals the nudge.
        playCredits();
        const creditsOpen = !document.querySelector("#credits").classList.contains("hidden");
        closeCredits();
        const afterBtn = document.querySelector("#again").textContent;
        const nudgeShown = !document.querySelector("#nudge").classList.contains("hidden");
        return { shown, again, creditsOpen, afterBtn, nudgeShown };
      });
      check("win screen renders (showWin does not throw)", r.shown);
      check("first-win button reads End Credits", r.again === "End Credits");
      check("linger auto-roll opens the credits", r.creditsOpen);
      check("after credits: replay button + nudge return", r.afterBtn !== "End Credits" && r.nudgeShown);
      await p.context().close();
    }

    // 9) Audio: every arc's soundscape (plus the landing theme) builds a live
    //    graph without throwing, the context unlocks from a gesture, and muting
    //    silences the master. (The test context allows autoplay, so unlock()
    //    reports the running state directly.)
    {
      const p = await newPage(browser, { reduce: false });
      const r = await p.evaluate(async () => {
        const a = window.ambience;
        a.muted = false;
        const out = {};
        for (const skin of ["hallway", "coach", "stairway", "landing"]) {
          try {
            a.play(skin);
            out[skin] = a.sources.length + (a.timers.length ? 1000 : 0); // built + has scheduled events
          } catch (e) { out[skin] = -1; }
          await new Promise((res) => setTimeout(res, 60));
        }
        const unlocked = a.unlock();
        // mute drives master to 0 (over a short ramp, so wait it out before reading)
        a.setMuted(true);
        await new Promise((res) => setTimeout(res, 300));
        const mutedGain = a.master.gain.value;
        a.setMuted(false);
        a.stop();
        return { out, unlocked, mutedGain };
      });
      const built = ["hallway", "coach", "stairway", "landing"].every(s => r.out[s] > 0);
      check("audio: all arc soundscapes build a live graph", built, JSON.stringify(r.out));
      check("audio: context unlocks from a gesture", r.unlocked === true);
      check("audio: mute silences the master bus", r.mutedGain === 0, `gain ${r.mutedGain}`);

      // Substantiate the "level-matched to the landing theme" claim by actually
      // MEASURING loudness (RMS) per arc, not just checking a config string. Each
      // arc must sit within a band of the landing theme's level (the pre-fix coach
      // bug was ~0.16x landing, which this would catch).
      const rms = await p.evaluate(async () => {
        const a = window.ambience; a.muted = false; a._ensure();
        const out = {};
        for (const skin of ["hallway", "coach", "stairway", "landing"]) {
          const an = a.ctx.createAnalyser(); an.fftSize = 2048; a.master.connect(an);
          a.play(skin);
          const buf = new Float32Array(an.fftSize); let s = 0, n = 0;
          const t0 = performance.now();
          while (performance.now() - t0 < 1500) {
            an.getFloatTimeDomainData(buf);
            for (let i = 0; i < buf.length; i++) { s += buf[i] * buf[i]; n++; }
            await new Promise((res) => setTimeout(res, 50));
          }
          a.stop(); try { a.master.disconnect(an); } catch (e) {}
          out[skin] = Math.sqrt(s / n);
          await new Promise((res) => setTimeout(res, 200));
        }
        return out;
      });
      const L = rms.landing;
      const matched = L > 0 && ["hallway", "coach", "stairway"].every(s => rms[s] > L * 0.6 && rms[s] < L * 1.5);
      check("audio: arcs are level-matched to the landing theme (measured RMS)", matched, JSON.stringify(Object.fromEntries(Object.entries(rms).map(([k, v]) => [k, +v.toFixed(4)]))));
      await p.context().close();
    }

    // 10) Every arc is reachable and playable: entering the corridor renders the
    //     prose and the controls for each of the three arcs.
    {
      for (const arc of ["hallway-eight", "stairway8", "coach8"]) {
        const p = await newPage(browser, { reduce: false });
        await enter(p, arc);
        const s = await p.evaluate(() => ({
          lines: document.querySelectorAll("#prose .line").length,
          controls: !document.querySelector("#controls").classList.contains("hidden"),
          hasChoices: document.querySelectorAll(".choice").length >= 2,
        }));
        check(`arc playable: ${arc} renders prose + controls`, s.lines > 0 && s.controls && s.hasChoices, JSON.stringify(s));
        await p.context().close();
      }
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter(r => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
