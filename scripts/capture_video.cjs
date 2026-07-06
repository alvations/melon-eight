// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Record a video of a specific scene, to visualise and document the game (the
// loop / Act 1, the Act 2 touch interaction, the win screen, and the ending
// credits roll). Uses Playwright's context video recording, so no external
// screen capture is needed.
//
// Usage:
//   # boot first, e.g.:  H8_GOAL=3 PORT=8070 python app.py
//   node scripts/capture_video.cjs [baseURL] [scene] [arc] [outDir] [viewport]
//     scene    = loop | act2 | win | credits   (default: credits)
//     arc      = hallway-eight | stairway8 | coach8   (default: hallway-eight)
//     viewport = desktop | mobile              (default: desktop)
//   node scripts/capture_video.cjs http://127.0.0.1:8070 credits hallway-eight ./video
//
// Output: a .webm in outDir. Convert to mp4 with ffmpeg if you like:
//   ffmpeg -i credits.webm -c:v libx264 -pix_fmt yuv420p credits.mp4
//
// Portable browser resolution: see scripts/browser.cjs.

const fs = require("fs");
const path = require("path");
const { loadPlaywright, chromiumLaunchOptions } = require("./browser.cjs");
const playwright = loadPlaywright();

const BASE = process.argv[2] || "http://127.0.0.1:8070";
const SCENE = process.argv[3] || "credits";
const ARC = process.argv[4] || "hallway-eight";
const OUT = process.argv[5] || "./video";
const VP = (process.argv[6] || "desktop") === "mobile"
  ? { width: 390, height: 844 } : { width: 1280, height: 860 };
fs.mkdirSync(OUT, { recursive: true });

async function enter(p) {
  await p.goto(BASE);
  await p.evaluate(() => { localStorage.setItem("h8_mem", JSON.stringify({ v: 1, arcStarted: { "stairway8": true, "hallway-eight": true, "coach8": true } })); localStorage.setItem("h8_onboarded", "1"); });
  await p.goto(BASE); await p.waitForTimeout(400);
  await p.evaluate((a) => document.querySelector(`[data-arc="${a}"]`)?.click(), ARC);
  await p.waitForTimeout(700);
  await p.click("#begin").catch(() => {});
  await p.evaluate(() => document.querySelectorAll(".cutscene-overlay:not(.hidden),#learn:not(.hidden)").forEach(o => o.querySelector("button")?.click()));
  await p.waitForSelector("#controls:not(.hidden)", { timeout: 8000 }).catch(() => {});
}

// Win for real by making correct calls until the win screen appears, so the win
// and credits scenes show the arc's true resting line (not a fabricated stub).
// Reliable on a low H8_GOAL. Returns true if the win was reached.
async function winForReal(p, tries = 16) {
  for (let i = 0; i < tries; i++) {
    if (await p.evaluate(() => !document.querySelector("#win").classList.contains("hidden"))) return true;
    await p.waitForSelector("#controls:not(.hidden)", { timeout: 8000 }).catch(() => {});
    await p.evaluate(() => document.querySelector('.choice[data-choice="continue"]')?.click());
    await p.waitForTimeout(150);
    await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
    await p.waitForFunction(() => !document.querySelector("#win").classList.contains("hidden") || !document.querySelector("#controls").classList.contains("hidden"), { timeout: 9000 }).catch(() => {});
    await p.waitForTimeout(150);
  }
  return await p.evaluate(() => !document.querySelector("#win").classList.contains("hidden"));
}

async function scene(p) {
  if (SCENE === "loop") {
    // Act 1: the core loop. Reveal, commit continue, next loop reveals.
    await p.waitForTimeout(2500);
    await p.evaluate(() => document.querySelector('.choice[data-choice="continue"]')?.click());
    await p.waitForTimeout(200);
    await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
    await p.waitForTimeout(4000);
  } else if (SCENE === "act2") {
    // Act 2: force a touch verb past the onset, click it, show the flavour line.
    await p.waitForTimeout(1200);
    await p.evaluate(() => { buildTouch({ level: 4, room: { touch: [{ prop: "door", verb: "try the door" }] } }); });
    await p.waitForTimeout(600);
    await p.evaluate(() => document.querySelector(".touch-btn")?.click());
    await p.waitForTimeout(4500);
  } else if (SCENE === "win") {
    if (!(await winForReal(p))) { console.log("could not reach a real win (use a low H8_GOAL)"); return; }
    await p.waitForTimeout(2600);
    await p.evaluate(() => document.querySelector("#look-back")?.click());   // expand the look-back
    await p.waitForTimeout(3000);
  } else { // credits
    if (!(await winForReal(p))) { console.log("could not reach a real win (use a low H8_GOAL)"); return; }
    await p.waitForTimeout(2200);   // past the win-hush; a first escape shows End Credits
    await p.evaluate(() => { if (typeof playCredits === "function") playCredits(); else openCredits(); });
    await p.waitForTimeout(12000);   // let the roll play
  }
}

(async () => {
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  const ctx = await browser.newContext({ viewport: VP, recordVideo: { dir: OUT, size: VP } });
  const p = await ctx.newPage();
  try {
    await enter(p);
    await scene(p);
  } finally {
    await ctx.close();   // finalises the video file
    await browser.close();
  }
  // Rename the auto-named video to something meaningful.
  const vids = fs.readdirSync(OUT).filter((f) => f.endsWith(".webm") && !f.startsWith(`${SCENE}_`));
  if (vids.length) {
    const src = path.join(OUT, vids[vids.length - 1]);
    const dst = path.join(OUT, `${SCENE}_${ARC}.webm`);
    fs.renameSync(src, dst);
    console.log(`wrote ${dst} (${(fs.statSync(dst).size / 1024).toFixed(1)} KiB)`);
  }
})().catch((e) => { console.error("ERROR", e); process.exit(1); });
