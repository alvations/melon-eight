// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 alvations (Melon Lab)
//
// Shared browser resolver for the repo's headless-Chromium tools (the emulation
// tests, the audio measurement, the screenshot capture, the render probe). It
// makes those tools PORTABLE: a normal developer installs the open-source
// toolchain once and everything runs; there is nothing sandbox-specific to
// configure.
//
//   npm install                 # installs Playwright (see package.json)
//   npx playwright install chromium
//
// Resolution order (first hit wins), so the same scripts run in a plain checkout
// or in a preconfigured sandbox:
//   - Playwright module: PW_PATH env, then a normal require('playwright') from
//     node_modules, then a common global path.
//   - Chromium binary: H8_CHROMIUM env (if it exists), then a known sandbox path
//     (if it exists), else NONE, which lets Playwright launch its own installed
//     Chromium (the portable default after `npx playwright install chromium`).

const fs = require("fs");

function loadPlaywright() {
  const candidates = [
    process.env.PW_PATH,
    "playwright",                                   // node_modules (the portable path)
    "/opt/node22/lib/node_modules/playwright",      // a common preinstalled global
  ].filter(Boolean);
  for (const c of candidates) {
    try { return require(c); } catch (e) { /* try the next */ }
  }
  console.error(
    "SKIP: Playwright not found. Install the toolchain:\n" +
    "  npm install && npx playwright install chromium"
  );
  process.exit(2);
}

// Options for chromium.launch(). Adds the autoplay flag the audio tools need.
// Only sets executablePath when a real file exists; otherwise Playwright uses
// its own installed Chromium.
function chromiumLaunchOptions(extraArgs) {
  const args = ["--autoplay-policy=no-user-gesture-required"].concat(extraArgs || []);
  const explicit = process.env.H8_CHROMIUM;
  const sandbox = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
  if (explicit && fs.existsSync(explicit)) return { executablePath: explicit, args };
  if (fs.existsSync(sandbox)) return { executablePath: sandbox, args };
  return { args };
}

module.exports = { loadPlaywright, chromiumLaunchOptions };
