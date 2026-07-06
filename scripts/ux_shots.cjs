// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Capture the key screens of the game for a UX/design review: select, intro,
// loop, win, and credits, for every arc, at a desktop AND a mobile viewport.
// This is the tool used to eyeball layout, fonts, colour, and mobile clipping.
//
// Usage:
//   node scripts/ux_shots.cjs [baseURL] [outDir]
//   # Boot with a SHORT goal so the win shot is a REAL win, not a stub:
//   #   H8_GOAL=1 PORT=8070 python app.py
//   node scripts/ux_shots.cjs http://127.0.0.1:8070 ./shots
//
// The win/credits frames are captured by actually WINNING (making correct calls),
// so the win screen shows each arc's own real resting benediction. Use a low
// H8_GOAL so the win is reached in a call or two.
//
// Portable browser resolution: see scripts/browser.cjs (npm install && npx
// playwright install chromium).

const fs = require("fs");
const { loadPlaywright, chromiumLaunchOptions } = require("./browser.cjs");
const playwright = loadPlaywright();

const BASE = process.argv[2] || "http://127.0.0.1:8070";
const OUT = process.argv[3] || "./shots";
fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = { desktop: { width: 1280, height: 860 }, mobile: { width: 390, height: 844 } };
const ARCS = ["hallway-eight", "stairway8", "coach8"];

async function seed(p) {
  await p.evaluate(() => {
    localStorage.setItem("h8_mem", JSON.stringify({ v: 1, arcStarted: { "stairway8": true, "hallway-eight": true, "coach8": true } }));
    localStorage.setItem("h8_onboarded", "1");   // skip the first-reset instructions overlay
  });
}

// Win for real by making correct calls until the win screen appears (so the win
// shot shows the arc's true resting line, never a fabricated stub). Correct means
// continue when nothing changed; a rare early anomaly resets the run, so retry.
// Reliable on a low H8_GOAL. Returns true if the win screen was reached.
async function winForReal(p, tries = 16) {
  for (let i = 0; i < tries; i++) {
    if (await p.evaluate(() => !document.querySelector("#win").classList.contains("hidden"))) return true;
    await p.waitForSelector("#controls:not(.hidden)", { timeout: 8000 }).catch(() => {});
    await p.evaluate(() => document.querySelector('.choice[data-choice="continue"]')?.click());
    await p.waitForTimeout(150);
    await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
    await p.waitForFunction(() => {
      const w = !document.querySelector("#win").classList.contains("hidden");
      const c = !document.querySelector("#controls").classList.contains("hidden");
      return w || c;
    }, { timeout: 9000 }).catch(() => {});
    await p.waitForTimeout(150);
  }
  return await p.evaluate(() => !document.querySelector("#win").classList.contains("hidden"));
}

(async () => {
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  try {
    for (const [vp, size] of Object.entries(VIEWPORTS)) {
      const ctx = await browser.newContext({ viewport: size });
      const p = await ctx.newPage();
      await p.goto(BASE); await seed(p); await p.goto(BASE); await p.waitForTimeout(500);
      await p.evaluate(() => { if (typeof revealSelect === "function") revealSelect(); });
      await p.waitForTimeout(400);
      await p.screenshot({ path: `${OUT}/${vp}_01_select.png` });

      for (const arc of ARCS) {
        await p.evaluate((a) => document.querySelector(`[data-arc="${a}"]`)?.click(), arc);
        await p.waitForTimeout(700);
        await p.screenshot({ path: `${OUT}/${vp}_${arc}_02_intro.png` });
        await p.click("#begin").catch(() => {});
        await p.evaluate(() => document.querySelectorAll(".cutscene-overlay:not(.hidden),#learn:not(.hidden)").forEach(o => o.querySelector("button")?.click()));
        await p.waitForSelector("#controls:not(.hidden)", { timeout: 8000 }).catch(() => {});
        await p.waitForTimeout(700);
        await p.screenshot({ path: `${OUT}/${vp}_${arc}_03_loop.png` });
        // Win for real, then wait past the win-hush so the look-back and share
        // surfaces have faded up. Captures the arc's true resting benediction.
        const won = await winForReal(p);
        if (won) {
          await p.waitForTimeout(2100);
          await p.screenshot({ path: `${OUT}/${vp}_${arc}_04_win.png` });
        } else {
          console.log(`${vp} ${arc}: could not reach a real win (use a low H8_GOAL); skipping win shot`);
        }
        await p.evaluate(() => { if (typeof loadSelect === "function") loadSelect(); });
        await p.waitForTimeout(500);
        await p.evaluate(() => { if (typeof revealSelect === "function") revealSelect(); });
        await p.waitForTimeout(200);
      }
      await p.evaluate(() => { try { openCredits(); } catch (e) {} });
      await p.waitForTimeout(1500);   // let the fade-in settle so the overlay is opaque
      await p.screenshot({ path: `${OUT}/${vp}_05_credits.png` });
      await ctx.close();
    }
  } finally {
    await browser.close();
  }
  console.log("shots ->", OUT);
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
