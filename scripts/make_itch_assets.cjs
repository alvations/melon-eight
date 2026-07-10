// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Render the itch.io page assets from the REAL game (so the screenshots are the
// actual product, not mock-ups) plus the on-brand cover.
//
//   node scripts/make_itch_assets.cjs <baseURL> <outDir> [mode]
//     mode "main" (default): cover + landing + one loop per arc + credits roll
//     mode "win"           : the "You're out." win screen
//                            (run the server with H8_GOAL=1 for this pass)
//
// Outputs (2x, crisp): cover.png, 01-landing.png, 02-hallway.png,
// 03-stairway.png, 04-coach.png, 05-win.png, 06-credits.png
const path = require("path");
const { loadPlaywright, chromiumLaunchOptions } = require(path.join(__dirname, "browser.cjs"));
const playwright = loadPlaywright();

const BASE = process.argv[2] || "http://127.0.0.1:8071/";
const OUT = process.argv[3] || path.join(__dirname, "..", "press", "itch");
const MODE = process.argv[4] || "main";

const VIEW = { width: 1280, height: 800 };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function newCtx(browser, opts) {
  const ctx = await browser.newContext(Object.assign({
    viewport: VIEW, deviceScaleFactor: 2,
  }, opts || {}));
  return ctx;
}

async function shot(page, name) {
  const p = path.join(OUT, name);
  await page.screenshot({ path: p });
  console.log("  wrote", path.relative(path.join(__dirname, ".."), p));
}

async function toLoop(page, arc) {
  await page.goto(BASE, { waitUntil: "load" });
  await page.waitForSelector(".arc-card", { timeout: 10000 });
  await wait(1600); // let the cards finish fading in
  return page;
}

async function enterArc(page, arc) {
  await page.click(`.arc-card[data-arc="${arc}"]`);
  await page.waitForSelector("#intro:not(.hidden)", { timeout: 8000 });
  await wait(700);
  await page.click("#begin");
  await page.waitForSelector("#corridor:not(.hidden)", { timeout: 8000 });
  // let the prose type in and the choices arrive
  await page.waitForSelector("#controls:not(.hidden)", { timeout: 12000 }).catch(() => {});
  await wait(1200);
}

async function captureMain(browser) {
  // Cover: the REAL landing, framed to itch's 630x500 cover ratio (2x = crisp),
  // with the corner utility chrome hidden so the card reads as the game itself
  // (the 8, the tagline, the three arcs) rather than a mock-up.
  {
    const ctx = await newCtx(browser, { viewport: { width: 1000, height: 794 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await toLoop(page);
    await page.addStyleTag({ content:
      "#lang-corner,#sound-toggle,#settings-toggle,#ach-open{opacity:0!important}" });
    await wait(300);
    await shot(page, "cover.png");
    await ctx.close();
  }

  // Landing (arc select).
  {
    const ctx = await newCtx(browser);
    const page = await ctx.newPage();
    await toLoop(page);
    await shot(page, "01-landing.png");
    await ctx.close();
  }

  // One clean loop per arc (fresh context each = a first run, so Act 2 stays out
  // of the way and the core loop reads clearly).
  const arcs = [["hallway-eight", "02-hallway.png"],
                ["stairway8", "03-stairway.png"],
                ["coach8", "04-coach.png"]];
  for (const [arc, name] of arcs) {
    const ctx = await newCtx(browser);
    const page = await ctx.newPage();
    await toLoop(page, arc);
    await enterArc(page, arc);
    await shot(page, name);
    await ctx.close();
  }

  await captureCredits(browser);
}

async function captureCredits(browser) {
  // The credits roll, timed so the "A MELON LAB GAME / EIGHT" studio splash sits
  // around the centre rather than low with a lot of empty black above it.
  const ctx = await newCtx(browser);
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: "load" });
  await page.waitForFunction(() => typeof openCredits === "function", { timeout: 8000 });
  await page.evaluate(() => openCredits());
  // Fully opaque overlay (skip the 1.3s fade so the landing never bleeds
  // through) and hide the corner utility chrome for a clean promo frame.
  await page.addStyleTag({ content:
    ".credits-overlay{opacity:1!important;animation:none!important}" +
    "#lang-corner,#sound-toggle,#settings-toggle,#ach-open,#credits-done{opacity:0!important}" });
  // Snap the roll so the EIGHT title is vertically centred (deterministic,
  // rather than guessing a wall-clock offset into a 52s animation).
  await page.evaluate(() => {
    const roll = document.querySelector("#credits-roll");
    const target = document.querySelector(".credits-title") ||
                   document.querySelector(".credits-splash");
    if (!roll || !target) return;
    roll.style.animation = "none";
    const vh = window.innerHeight;
    const t = target.getBoundingClientRect();
    const r = roll.getBoundingClientRect();
    const offsetWithinRoll = (t.top - r.top) + t.height / 2;
    roll.style.top = "0px";
    roll.style.transform = `translate(-50%, ${vh / 2 - offsetWithinRoll}px)`;
  });
  await wait(400);
  await shot(page, "06-credits.png");
  await ctx.close();
}

async function captureWin(browser) {
  // Needs a server started with H8_GOAL=1 so a single correct "go on" wins.
  const ctx = await newCtx(browser);
  const page = await ctx.newPage();
  await toLoop(page, "hallway-eight");
  await enterArc(page, "hallway-eight");
  for (let i = 0; i < 24; i++) {
    if (await page.$("#win:not(.hidden)")) break;
    if (await page.$("#confidence:not(.hidden)")) {
      await page.click('#confidence [data-conf="4"]').catch(() => {});
    } else if (await page.$("#controls:not(.hidden)")) {
      await page.click('#controls .choice[data-choice="continue"]').catch(() => {});
    }
    await wait(700);
  }
  await page.waitForSelector("#win:not(.hidden)", { timeout: 8000 });
  await wait(1500); // let the win prose + share prompt settle
  await shot(page, "05-win.png");
  await ctx.close();
}

(async () => {
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  try {
    if (MODE === "win") await captureWin(browser);
    else if (MODE === "credits") await captureCredits(browser);
    else await captureMain(browser);
    console.log("done:", MODE);
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
