// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Render-order diagnostic: verify that the prose lines reveal strictly in order
// and that the closing "sense" line (always last in the server's canonical
// order) is revealed last, never mid-load. This is the harness used to confirm
// the sense-line timing rather than guess at it: it polls the DOM during the
// staggered reveal across many loops and reports any out-of-order reveal.
//
// Usage:
//   node scripts/probe_render.cjs [baseURL] [arc] [loops]
//   # boot first, e.g.:  H8_GOAL=8 PORT=8070 python app.py
//   node scripts/probe_render.cjs http://127.0.0.1:8070 hallway-eight 12
//
// Portable browser resolution: see scripts/browser.cjs.

const { loadPlaywright, chromiumLaunchOptions } = require("./browser.cjs");
const playwright = loadPlaywright();

const BASE = process.argv[2] || "http://127.0.0.1:8070";
const ARC = process.argv[3] || "hallway-eight";
const LOOPS = parseInt(process.argv[4] || "12", 10);

(async () => {
  const browser = await playwright.chromium.launch(chromiumLaunchOptions());
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  await p.goto(BASE);
  await p.evaluate(() => localStorage.setItem("h8_mem", JSON.stringify({ v: 1, arcStarted: { "stairway8": true, "hallway-eight": true, "coach8": true } })));
  await p.goto(BASE);
  await p.waitForTimeout(300);
  await p.evaluate((a) => document.querySelector(`[data-arc="${a}"]`)?.click(), ARC);
  await p.waitForTimeout(600);
  await p.click("#begin").catch(() => {});
  await p.evaluate(() => document.querySelectorAll(".cutscene-overlay:not(.hidden),#learn:not(.hidden)").forEach(o => o.querySelector("button")?.click()));

  let violations = [], senseLoops = 0, senseLast = 0, checked = 0;
  for (let i = 0; i < LOOPS; i++) {
    await p.waitForFunction(() => {
      const ls = document.querySelectorAll("#prose .line");
      return ls.length > 0 && [...ls].some(l => !l.classList.contains("show"));
    }, { timeout: 6000 }).catch(() => {});

    const rec = await p.evaluate(async () => {
      const order = [], seen = new Set();
      const domOrder = [...document.querySelectorAll("#prose .line")].map((l, i) => l.dataset.prop || `#${i}`);
      const start = performance.now();
      let outOfOrder = false;
      while (performance.now() - start < 9000) {
        const ls = [...document.querySelectorAll("#prose .line")];
        ls.forEach((l, i) => {
          const key = l.dataset.prop || `#${i}`;
          if (l.classList.contains("show") && !seen.has(key)) {
            seen.add(key); order.push(key);
            for (let j = 0; j < i; j++) if (!ls[j].classList.contains("show")) outOfOrder = true;
          }
        });
        if (seen.size >= ls.length && ls.length > 0) break;
        await new Promise(r => setTimeout(r, 40));
      }
      return { order, domOrder, outOfOrder };
    });
    checked++;
    if (rec.outOfOrder) violations.push({ loop: i, order: rec.order, dom: rec.domOrder });
    if (rec.domOrder.includes("sense")) { senseLoops++; if (rec.order[rec.order.length - 1] === "sense") senseLast++; }

    await p.evaluate(() => document.querySelector('.choice[data-choice="continue"]')?.click());
    await p.waitForTimeout(120);
    await p.evaluate(() => document.querySelector('#confidence:not(.hidden) [data-conf="4"]')?.click());
    await p.waitForTimeout(2200);
  }
  console.log(`arc=${ARC} loops=${checked} out-of-order=${violations.length} senseShown=${senseLoops} senseRenderedLast=${senseLast}`);
  if (violations.length) console.log("VIOLATIONS:", JSON.stringify(violations.slice(0, 5), null, 2));
  await browser.close();
  process.exit(violations.length ? 1 : 0);
})().catch(e => { console.error("ERROR", e); process.exit(1); });
