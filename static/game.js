/* SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 alvations (Melon Lab)
 */
/* Eight -- client.
 *
 * The server owns the truth (whether a place changed) and ships several arcs
 * (skins/backstories). This file lets the player pick an arc, applies its skin,
 * then renders, paces, and quietly drifts the presentation so no two loops can
 * be compared pixel-for-pixel. The unease is in the timing and typography as
 * much as in the words.
 */

const $ = (sel) => document.querySelector(sel);

const el = {
  select: $("#select"),
  arcs: $("#arcs"),
  intro: $("#intro"),
  introTitle: $("#intro-title"),
  introText: $("#intro-text"),
  begin: $("#begin"),
  introBack: $("#intro-back"),
  corridor: $("#corridor"),
  progress: $("#progress"),
  best: $("#best"),
  heading: $("#heading"),
  prose: $("#prose"),
  aside: $("#aside"),
  controls: $("#controls"),
  confidence: $("#confidence"),
  touchRow: $("#touch-row"),
  touchLine: $("#touch-line"),
  exitOffer: $("#exit-offer"),
  exitTempt: $("#exit-tempt"),
  exitTake: $("#exit-take"),
  win: $("#win"),
  winText: $("#win-text"),
  again: $("#again"),
  giveup: $("#giveup"),
  ending: $("#ending"),
  endingText: $("#ending-text"),
  endingBack: $("#ending-back"),
  selectLead: $("#select-lead"),
  selectReveal: $("#select-reveal"),
  langLabel: $("#lang-label"),
  langSelect: $("#lang-select"),
  langCorner: $("#lang-corner"),
  learn: $("#learn"),
  learnTitle: $("#learn-title"),
  learnLines: $("#learn-lines"),
  learnGo: $("#learn-go"),
  settingsToggle: $("#settings-toggle"),
  settings: $("#settings"),
  settingsTitle: $("#settings-title"),
  setTextLabel: $("#set-text-label"),
  setBrightLabel: $("#set-bright-label"),
  setText: $("#set-text"),
  setBright: $("#set-bright"),
  setMotion: $("#set-motion"),
  setMotionLabel: $("#set-motion-label"),
  setDiffLabel: $("#set-diff-label"),
  setDiffHint: $("#set-diff-hint"),
  setDiffHard: $("#set-diff-hard"),
  setDiffInsane: $("#set-diff-insane"),
  setAgeLabel: $("#set-age-label"),
  settingsGo: $("#settings-go"),
  achOpen: $("#ach-open"),
  achievements: $("#achievements"),
  achTitle: $("#ach-title"),
  achClose: $("#ach-close"),
  achGrid: $("#ach-grid"),
  colSectionLabel: $("#col-section-label"),
  achFlash: $("#ach-flash"),
  colRecap: $("#col-recap"),
  npcUtterance: $("#npc-utterance"),
  achSave: $("#ach-save"),
  achLoad: $("#ach-load"),
  achErase: $("#ach-erase"),
  achFile: $("#ach-file"),
  eraseConfirm: $("#erase-confirm"),
  eraseTitle: $("#erase-title"),
  eraseBody: $("#erase-body"),
  eraseOk: $("#erase-ok"),
  eraseCancel: $("#erase-cancel"),
  cutscene: $("#cutscene"),
  cutsceneText: $("#cutscene-text"),
  credits: $("#credits"),
  creditsScroller: $("#credits-scroller"),
  creditsRoll: $("#credits-roll"),
  creditsDone: $("#credits-done"),
  creditsRow: $("#credits-row"),
  viewCredits: $("#view-credits"),
  nudge: $("#nudge"),
  fold: $("#fold"),
  foldTitle: $("#fold-title"),
  foldLines: $("#fold-lines"),
  foldHideRow: $("#fold-hide-row"),
  foldHide: $("#fold-hide"),
  foldHideLabel: $("#fold-hide-label"),
  foldGo: $("#fold-go"),
  look: $("#look"),
  lookBack: $("#look-back"),
  lookLine: $("#look-line"),
  share: $("#share"),
  shareOpen: $("#share-open"),
  sharePanel: $("#share-panel"),
  shareLine: $("#share-line"),
  shareNative: $("#share-native"),
  sharePlatforms: $("#share-platforms"),
  shareX: $("#share-x"),
  shareFb: $("#share-fb"),
  shareLi: $("#share-li"),
  shareCopy: $("#share-copy"),
  body: document.body,
};

let current = null;       // latest room payload
let meta = null;          // current arc's presentation meta
let selectedArc = null;   // arc id in play
let firstArcRun = false;  // the player's very first run of this arc: no Act 2
let onboarding = false;   // first-reset instructions are up; gate the loop controls
let pendingChoice = null; // choice awaiting a confidence rating
let touchLineTimer = null; // auto-fade timer for the Act 2 flavour line
let winIsFirst = false;   // this win is the first escape of the arc (roll credits)
let againMode = "replay"; // the win button: "replay" (Walk it again) or "credits"
let creditsAutoTimer = null; // first-win: auto-roll the credits if the player lingers
// Long enough to read the benediction and take in the look-back / share triggers
// (~18s), plus 10%. The win screen returns after the roll, so this only ever
// gives the player MORE, never takes the moment away.
const CREDITS_DWELL = 20000;
let hesitated = false;    // player already admitted doubt this turn (one re-decide)
let decideStart = 0;      // when the controls appeared, to time the player's dwell
let renderGen = 0;        // bumped each loop; stale inspect asides are dropped
let drift = 0;            // slowly accumulating presentation drift

// Quality of the current unbroken climb (level 0 -> win), used to reflect *how*
// a run was won, not just that it was. Reset whenever a climb starts fresh.
function freshRun() { return { touches: 0, guessed: false }; }
let run = freshRun();
let readRecordText = "";  // the fleeting "how you did" line for the win screen
let introLines = [];      // the current arc's localized intro, reused on first reset
let cutsceneLines = [];   // the arc's rule-reminder, shown before the first-reset instructions

// Respect reduced motion (OS setting or the in-app toggle). The game leans on
// slow fades and line-by-line reveals; for these users we show text at once (JS)
// and drop the transitions/animations (CSS). Recomputed by applySettings().
function osReduceMotion() {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
  catch (e) { return false; }
}
let reduceMotion = osReduceMotion();

// Reveal the arc cards + language row a beat after the title paints. Idempotent;
// the first paint is just "8" and the two lead lines (the mystery, on purpose).
function revealSelect() {
  // The ways-through fade in, but their space was reserved from first paint (the
  // .pre state keeps layout), so the title and lead never shift position.
  if (el.selectReveal) el.selectReveal.classList.remove("pre");
}

// --- helpers ---------------------------------------------------------------

// The server hands us a session id on /api/new; we echo it on every request so
// state survives even where cookies don't (e.g. a cross-site iframe on Spaces).
let sid = null;

// Chosen language; echoed on every request so the server localizes content.
let lang = localStorage.getItem("h8_lang") || "en_US";
let ui = {}; // current UI-string catalog {name: text}

// Chosen difficulty (easy/normal/hard); echoed so the server scales the loop.
// Hard is available to everyone from the start; Normal is the default.
let difficulty = localStorage.getItem("h8_diff") || "normal";
// Reading register (simple/normal): simple loads a plainer-language UI overlay,
// for younger players. Default normal. Does not change any mechanic.
let register = localStorage.getItem("h8_register") || "normal";

// Hard is available to everyone from the start; Normal stays the default. Insane
// is honoured only once it is unlocked (all achievements bar the held/date-locked
// ones), so a stale saved "insane" never takes effect before it is earned.
function effectiveDifficulty() {
  if (difficulty === "insane" && !insaneUnlocked()) return "normal";
  return difficulty;
}

function headers(extra) {
  const h = Object.assign({}, extra || {});
  if (sid) h["X-Sid"] = sid;
  if (lang) h["X-Lang"] = lang;
  h["X-Diff"] = effectiveDifficulty();
  return h;
}

// Fetch and apply the UI-string catalog for the current language.
async function applyUI() {
  try {
    const res = await fetch(`/static/i18n/${lang}.json`);
    ui = res.ok ? await res.json() : {};
  } catch (e) {
    ui = {};
  }
  // Simple register: overlay a plainer-language catalog on top of the normal
  // one, per key, for younger players. Missing keys fall back to normal.
  if (register === "simple") {
    try {
      const r = await fetch(`/static/i18n/${lang}.simple.json`);
      if (r.ok) ui = Object.assign({}, ui, await r.json());
    } catch (e) {}
  }
  const t = (k, fallback) => ui[k] || fallback;
  if (el.selectLead) {
    el.selectLead.innerHTML =
      `${t("select_lead_1", "Somewhere you can't quite leave.")}<br>` +
      `${t("select_lead_2", "Choose a way through.")}`;
  }
  el.begin.textContent = t("begin", "Begin");
  el.introBack.textContent = t("back", "Back");
  el.again.textContent = t("again", "Walk it again");
  el.giveup.textContent = t("give_up", "Give up · back to start");
  if (el.endingBack) el.endingBack.textContent = t("ending_back", "Back to the start");
  // Accessibility labels for the icon-only controls.
  if (el.settingsToggle) el.settingsToggle.setAttribute("aria-label", t("a11y_settings", "Display settings"));
  if (el.achClose) el.achClose.setAttribute("aria-label", t("a11y_close", "Close"));
  // The sound toggle repaints its own aria-label (on mute state) from audio.js;
  // hand it the localized strings to use.
  if (window.ambience && window.ambience.setLabels) {
    window.ambience.setLabels(t("a11y_sound_on", "Sound on"), t("a11y_sound_off", "Sound off"));
  }
  if (el.langLabel) el.langLabel.textContent = t("language", "Language");
  const cq = document.querySelector(".conf-q");
  if (cq) cq.textContent = t("conf_q", "How certain are you?");
  [1, 2, 3, 4].forEach((n) => {
    const b = document.querySelector(`[data-conf="${n}"]`);
    const d = { 1: "Guessing", 2: "I think so", 3: "Almost sure", 4: "Certain" };
    if (b) b.textContent = t(`conf_${n}`, d[n]);
  });
  // The first-reset onboarding panel reuses the arc's own (already localized)
  // intro; only its dismiss button is a shared UI string.
  if (el.learnGo) el.learnGo.textContent = t("begin", "Begin");
  // Win-screen share labels (the prompt is per-arc, set in buildShare; the
  // invitation line itself is chosen per win).
  if (el.shareNative) el.shareNative.textContent = t("share_native", "Share");
  if (el.shareCopy) el.shareCopy.textContent = t("share_copy", "Copy link");
  if (el.lookBack) el.lookBack.textContent = t("look_back", "Look back.");
  if (el.foldGo) el.foldGo.textContent = t("begin", "Go on");
  if (el.foldHideLabel) el.foldHideLabel.textContent = t("fold_hide", "Don't show this again.");
  if (el.settingsTitle) el.settingsTitle.textContent = t("settings_title", "Display");
  if (el.setTextLabel) el.setTextLabel.textContent = t("set_text", "Text size");
  if (el.setBrightLabel) el.setBrightLabel.textContent = t("set_bright", "Brightness");
  if (el.setMotionLabel) el.setMotionLabel.textContent = t("set_motion", "Reduce motion");
  if (el.setDiffLabel) el.setDiffLabel.textContent = t("set_diff", "Difficulty");
  if (el.setAgeLabel) el.setAgeLabel.textContent = t("set_age", "Reading");
  document.querySelectorAll('.set-opts[data-set="diff"] button').forEach((b) => {
    const d = { easy: "Easy", normal: "Normal", hard: "Hard", insane: "Insane" };
    b.textContent = t("diff_" + b.dataset.diff, d[b.dataset.diff]);
  });
  document.querySelectorAll('.set-opts[data-set="register"] button').forEach((b) => {
    const d = { simple: "Simple", normal: "Normal" };
    b.textContent = t("age_" + b.dataset.age, d[b.dataset.age]);
  });
  if (el.settingsGo) el.settingsGo.textContent = t("set_done", "Done");
  if (el.achOpen) el.achOpen.setAttribute("aria-label", t("ach_open", "Achievements"));
  if (el.achTitle) el.achTitle.textContent = t("mem_title", "Memory");
  if (el.achSave) el.achSave.textContent = t("ach_save", "Save");
  if (el.achLoad) el.achLoad.textContent = t("ach_load", "Load");
  if (el.achErase) el.achErase.textContent = t("erase", "Erase");
  if (el.eraseTitle) el.eraseTitle.textContent = t("erase_title", "Erase your memory?");
  if (el.eraseBody) el.eraseBody.textContent = t("erase_body",
    "Everything this place remembers of you goes: the fragments you have recollected, the marks you have earned, every run. This cannot be undone.");
  if (el.eraseOk) el.eraseOk.textContent = t("erase", "Erase");
  if (el.eraseCancel) el.eraseCancel.textContent = t("erase_cancel", "Keep it");
  if (el.colSectionLabel) el.colSectionLabel.textContent = t("col_section", "Recollections");
  if (el.viewCredits) el.viewCredits.textContent = t("view_credits", "View credits");
  if (el.langSelect) el.langSelect.setAttribute("aria-label", t("language", "Language"));
}

// --- display / accessibility settings --------------------------------------
// Defaults leave the look exactly as it is; these only change on opt-in, and
// persist to localStorage.
function markOpts(set, val) {
  document.querySelectorAll(`.set-opts[data-set="${set}"] button`).forEach((b) =>
    b.classList.toggle("on", b.dataset.val === String(val))
  );
}
function applySettings() {
  // Ship defaults (a fresh visitor, and so every redeploy): text "0" = smallest,
  // bright "0" = most dim. Difficulty and register default to "normal" above.
  // Keep these as the resting state; the sliders/words only move on opt-in.
  let text = "0", bright = "0", motionPref = null;
  try {
    text = localStorage.getItem("h8_text") || "0";
    bright = localStorage.getItem("h8_bright") || "0";
    motionPref = localStorage.getItem("h8_motion");   // null | "0" | "1"
  } catch (e) {}
  document.documentElement.dataset.text = text;
  document.body.dataset.bright = bright;
  // Tri-state so the in-app toggle can OVERRIDE the OS, not merely add to it:
  //   "1" -> reduced (user asked), "0" -> full motion (user asked, beats the OS),
  //   unset -> follow the OS (prefers-reduced-motion / Low Power Mode).
  // Without this a phone in Low Power Mode forced reduced motion even after the
  // player turned the toggle off, so "full motion" looked broken on mobile.
  reduceMotion = motionPref === "1" ? true
    : motionPref === "0" ? false
    : osReduceMotion();
  document.documentElement.classList.toggle("motion-reduce", reduceMotion);
  if (el.setText) el.setText.value = text;
  if (el.setBright) el.setBright.value = bright;
  // The checkbox reflects the effective state, so with OS reduce-motion on it
  // shows checked until the player explicitly clears it.
  if (el.setMotion) el.setMotion.checked = reduceMotion;
  applyDifficultyUI();
  markOpts("register", register);
}
// Reflect the chosen difficulty. Hard is available to everyone from the start;
// the default is still Normal.
function applyDifficultyUI() {
  markOpts("diff", difficulty);
  // Reveal the Insane option only once it is unlocked (a completionist reward);
  // it ships hidden. If a stale save selected it while still locked, fall back to
  // the effective (clamped) difficulty for the highlight.
  const unlocked = insaneUnlocked();
  if (el.setDiffInsane) el.setDiffInsane.classList.toggle("hidden", !unlocked);
  if (!unlocked && difficulty === "insane") markOpts("diff", "normal");
  if (el.setDiffHint) {
    el.setDiffHint.textContent = (difficulty === "insane" && unlocked)
      ? (ui["diff_hint_insane"] || "Insane remakes what normal is, every run.")
      : (ui["diff_hint_hard"] || "Hard adds new kinds of change.");
  }
}
applySettings();

if (el.settingsToggle) {
  el.settingsToggle.addEventListener("click", () => {
    // Refresh the difficulty row against the live unlock state: applySettings()
    // first runs at load, before `mem` exists (temporal dead zone), so Insane is
    // hidden then even for a completionist. Recompute on open so an earned Insane
    // actually appears without needing to toggle another setting first.
    applyDifficultyUI();
    if (el.settings) { el.settings.classList.remove("hidden"); }
    if (el.settingsGo) el.settingsGo.focus();
  });
}
const closeSettings = () => { if (el.settings) el.settings.classList.add("hidden"); };
if (el.settingsGo) el.settingsGo.addEventListener("click", closeSettings);
if (el.settings) {
  el.settings.addEventListener("click", (e) => { if (e.target === el.settings) closeSettings(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el.settings.classList.contains("hidden")) closeSettings();
  });
}
document.querySelectorAll(".set-opts").forEach((group) => {
  group.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-val]");
    if (!b || b.disabled) return;
    const set = group.dataset.set;
    const val = b.dataset.val;
    if (set === "diff") {
      if (val === "insane" && !insaneUnlocked()) return;   // locked until earned
      difficulty = val;   // hard is available to everyone
    }
    if (set === "register") register = val;
    try { localStorage.setItem("h8_" + set, val); } catch (e) {}
    applySettings();
    if (set === "register") applyUI().then(() => { if (current) renderRoom(current); });
  });
});
if (el.setMotion) {
  el.setMotion.addEventListener("change", () => {
    try { localStorage.setItem("h8_motion", el.setMotion.checked ? "1" : "0"); } catch (e) {}
    applySettings();
  });
}
// Text-size and brightness are 3-stop sliders (0/1/2).
[["setText", "h8_text"], ["setBright", "h8_bright"]].forEach(([ref, key]) => {
  if (!el[ref]) return;
  el[ref].addEventListener("input", () => {
    try { localStorage.setItem(key, el[ref].value); } catch (e) {}
    applySettings();
  });
});

let EXPOSED_LANGS = [];   // the picker's set (from the server)
let LANG_DEFAULT = "en_US";

// The picker's options: only the exposed core set. Other locales are fully
// translated and compiled on disk but stay hidden (not exposed) for now.
function langOptions() {
  const seen = new Set();
  const list = [];
  EXPOSED_LANGS.forEach((l) => { if (!seen.has(l.code)) { seen.add(l.code); list.push(l); } });
  return list;
}
function rebuildLangPicker() {
  if (!el.langSelect) return;
  const list = langOptions();
  el.langSelect.innerHTML = "";
  list.forEach((l) => {
    const o = document.createElement("option");
    o.value = l.code;
    o.textContent = l.native;
    if (l.code === lang) o.selected = true;
    el.langSelect.appendChild(o);
  });
}
async function setLang(code) {
  lang = code;
  try { localStorage.setItem("h8_lang", lang); } catch (e) {}
  document.documentElement.lang = lang.split("_")[0];
  rebuildLangPicker();
  await applyUI();
  loadSelect(); // re-render arc cards with localized titles/taglines
}
async function initLangPicker() {
  const data = await get("/api/langs");
  if (!el.langSelect || !data.langs) return;
  EXPOSED_LANGS = data.langs;
  LANG_DEFAULT = data.default || "en_US";
  // A previously-picked locale may no longer be exposed; fall back so the
  // picker and `lang` stay in sync.
  if (!langOptions().some((l) => l.code === lang)) {
    lang = LANG_DEFAULT;
    localStorage.setItem("h8_lang", lang);
  }
  rebuildLangPicker();
  el.langSelect.addEventListener("change", () => setLang(el.langSelect.value));
}

async function get(url) {
  const res = await fetch(url, { headers: headers() });
  const data = await res.json();
  if (data && data.sid) sid = data.sid;
  return data;
}

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  if (data && data.sid) sid = data.sid;
  return data;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// A tiny jitter so pacing feels alive but not like noise.
const jitter = (base, spread) => base + Math.floor(Math.random() * spread);

function show(section) {
  [el.select, el.intro, el.corridor, el.win, el.ending].forEach((s) =>
    s.classList.add("hidden")
  );
  section.classList.remove("hidden");
  // The language corner and the collection button belong to the selection screen
  // only; both are chosen before a run, not mid-loop, so the loop stays clean.
  const onSelect = section === el.select;
  if (el.langCorner) el.langCorner.classList.toggle("hidden", !onSelect);
  if (el.achOpen) el.achOpen.classList.toggle("hidden", !onSelect);
}

// Nudge the presentation a fraction every loop. Individually invisible;
// cumulatively, "something feels off."
function applyDrift() {
  drift += 1;
  el.body.style.setProperty("--bg-shift", Math.min(drift * 0.25, 6).toFixed(2));
  const weight = 340 + Math.round(Math.sin(drift / 3) * 30);
  document.documentElement.style.setProperty("--weight", String(weight));
  const track = (0.01 + Math.sin(drift / 5) * 0.012).toFixed(4);
  document.documentElement.style.setProperty("--tracking", `${track}em`);
}

// Strip any directional glyphs an arc baked into its labels, so the UI can
// impose a single consistent convention.
function stripArrows(s) {
  return (s || "").replace(/[↑↓←→⇠⇢]/g, "").trim();
}

// Apply an arc's skin, title, and button labels. Convention, always: back sits
// on the LEFT, forward on the RIGHT. The arrow glyph follows the arc's axis of
// travel -- horizontal (←/→) by default, vertical (↑ back / ↓ forward) for
// stairs and the like.
// The last arc the player entered, remembered so the landing chrome (and the
// settings panel opened from it) keep that arc's colour instead of snapping
// back to a default. First-ever visit falls back to the canonical hallway blue.
function lastSkin() {
  try { return localStorage.getItem("h8_last_skin") || "hallway"; }
  catch (e) { return "hallway"; }
}

function applyMeta(m) {
  meta = m;
  el.body.dataset.skin = m.skin || "hallway";
  try { localStorage.setItem("h8_last_skin", m.skin || "hallway"); } catch (e) {}
  document.title = m.title || "8";
  el.introTitle.textContent = m.title || "8";
  const fwd = stripArrows(m.go_on) || "Go on";
  const back = stripArrows(m.turn_back) || "Turn back";
  const vertical = m.axis === "vertical";
  const backArrow = vertical ? "↑" : "←";
  const fwdArrow = vertical ? "↓" : "→";
  el.controls.querySelector('[data-choice="continue"]').textContent =
    `${fwd}  ${fwdArrow}`;
  el.controls.querySelector('[data-choice="back"]').textContent =
    `${backArrow}  ${back}`;
}

// --- rendering -------------------------------------------------------------

function setHud(p) {
  const floor = p.goal - p.level;
  const remaining = p.goal - p.level;
  const tmpl = (meta && meta.progress) || "{level} / {goal}";
  const label = tmpl
    .replace("{level}", p.level)
    .replace("{goal}", p.goal)
    .replace("{floor}", floor)
    .replace("{remaining}", remaining);
  const dots = Array.from({ length: p.goal }, (_, i) =>
    i < p.level ? "•" : "·"
  ).join(" ");
  el.progress.textContent = `${label}    ${dots}`;
  el.best.textContent = p.best ? (ui["furthest"] || "furthest {n}").replace("{n}", p.best) : "";
}

async function renderRoom(p) {
  current = p;
  renderGen++;              // invalidate any inspect aside pending from a past loop
  if (p.meta) applyMeta(p.meta);
  setHud(p);
  applyDrift();

  el.heading.textContent = p.room.heading;
  el.prose.innerHTML = "";
  el.aside.textContent = "";
  el.aside.classList.remove("show");
  el.controls.classList.add("hidden");
  el.confidence.classList.add("hidden");
  clearTouch();
  pendingChoice = null;
  hesitated = false;

  const lines = p.room.sentences;
  const shown = p.room.shown || [];

  lines.forEach((text, i) => {
    const div = document.createElement("div");
    div.className = "line";
    div.textContent = text;
    if (shown[i]) {
      div.dataset.prop = shown[i];
      attachInspect(div);
    }
    el.prose.appendChild(div);
  });

  // Reveal one line at a time with drifting pauses. The closing line (the
  // sense/atmosphere is always last in the server's canonical order) gets a
  // deliberate longer beat so it always lands on its own, after the rest have
  // settled, rather than washing in together with them (the line fade is ~0.9s,
  // so a short stagger would overlap the finish of the previous line). Under
  // reduced motion, show them all at once.
  const nodes = [...el.prose.children];
  if (reduceMotion) {
    nodes.forEach((n) => n.classList.add("show"));
  } else {
    for (let i = 0; i < nodes.length; i++) {
      const isLast = i === nodes.length - 1;
      if (isLast && nodes.length > 1) {
        // Let the preceding lines finish arriving, then a clear pause, so the
        // closing sense reads as the end and never appears mid-load.
        await sleep(jitter(1050, 400));
      } else {
        const long = Math.random() < 0.16;
        await sleep(long ? jitter(1000, 450) : jitter(360, 320));
      }
      nodes[i].classList.add("show");
    }
  }

  if (p.room.adaptive) {
    await sleep(reduceMotion ? 0 : 600);
    el.aside.textContent = p.room.adaptive;
    el.aside.classList.add("show");
  }

  await sleep(reduceMotion ? 0 : 400);
  // Do not reveal the loop controls while the first-reset instructions are up (or
  // pending behind the rule cutscene): otherwise the level-0 controls go live
  // under the overlay and the player can slip a call through and cross into
  // level 1 before ever seeing the instructions. hideOnboard() shows them.
  if (!onboarding) el.controls.classList.remove("hidden");
  buildTouch(p);                    // Act 2: the touchable details this loop
  decideStart = performance.now(); // start timing the player's deliberation
}

// --- Act 2: touch the room -------------------------------------------------

function clearTouch() {
  clearTimeout(touchLineTimer);
  if (el.touchRow) el.touchRow.innerHTML = "";
  // Fade the flavour line out (keep its text so the CSS opacity transition can
  // run) instead of blanking it instantly; otherwise a fast commit right after a
  // touch makes the line vanish with no fade. The text is left in place, now
  // invisible, and the next showTouchLine replaces it.
  if (el.touchLine) el.touchLine.classList.remove("show");
  if (el.exitOffer) el.exitOffer.classList.add("hidden");
}

// Build the contextual verbs for whatever details are shown, plus the rare
// false-way-out affordance. Touching never decides the forward/back call.
function buildTouch(p) {
  clearTouch();
  const room = p.room || {};
  const level = p.level || 0;

  // Act 2 (the touchable details) holds back through the opening loops so a
  // player first learns the core turn-back/go-on cleanly, then appears reliably
  // from the middle of a climb on. Onset is one loop later on the very first
  // climb of an arc (a gentler introduction), otherwise from level 3 (~the
  // fourth loop). Once past the onset it is usually offered, a couple of details
  // at a time, so the layer is actually met instead of being a rare surprise.
  const onset = firstArcRun ? 4 : 3;
  const touch = (room.touch || []).slice();
  const chance = level >= 5 ? 0.72 : 0.55;
  if (level >= onset && touch.length && Math.random() < chance) {
    for (let i = touch.length - 1; i > 0; i--) {   // shuffle
      const j = Math.floor(Math.random() * (i + 1));
      [touch[i], touch[j]] = [touch[j], touch[i]];
    }
    touch.slice(0, 2).forEach((t) => {             // at most two items
      const b = document.createElement("button");
      b.className = "touch-btn link-btn";
      b.textContent = t.verb;
      b.addEventListener("click", () => interactTouch(t.prop, b));
      el.touchRow.appendChild(b);
    });
  }

  if (room.exit_offer && el.exitOffer) {
    el.exitTempt.textContent = room.exit_offer.tempt || "";
    el.exitTake.textContent = room.exit_offer.action || "";
    el.exitOffer.classList.remove("hidden");
  }
  // The passenger's fixed utterance (coach). Passive and skippable; rendered
  // louder in easy mode so a younger player notices the trail.
  if (el.npcUtterance) {
    const u = room.npc_utterance || "";
    el.npcUtterance.textContent = u;
    el.npcUtterance.classList.toggle("show", !!u);
    el.npcUtterance.classList.toggle("prominent",
      !!u && effectiveDifficulty() === "easy");
  }
}

async function interactTouch(prop, btn) {
  if (btn) btn.disabled = true;
  const res = await post("/api/interact", { prop });
  if (!res || res.kind === "none") return;
  if (res.kind === "fold") {
    // Curiosity folded the run back to the start. Hold the fold line long enough
    // to actually read (it was flashing past before), then drop into the fresh
    // level-0 loop the server handed back and explain that the reset was this
    // touch, so it never reads as a glitch. The explainer gates the controls
    // (below), so the scene does not visibly rush to level 0 underneath it.
    showTouchLine(res.line);
    await sleep(reduceMotion ? 1200 : 2600);
    run = freshRun();   // the fold sent the climb back to the start
    renderRoom(res);
    maybeFoldExplainer();
    return;
  }
  // flashback / neutral reaction / red herring: flavour only. It still counts as
  // a second look, so an unaided ("cold") escape is one made without any touch.
  run.touches++;
  if (res.kind === "flashback") recordFlashback(selectedArc, res.idx, res.line);
  showTouchLine(res.line);
}

function showTouchLine(text) {
  if (!el.touchLine) return;
  clearTimeout(touchLineTimer);
  el.touchLine.textContent = text || "";
  el.touchLine.classList.remove("show");
  requestAnimationFrame(() => el.touchLine.classList.add("show"));
  // Let it hold long enough to read, then fade on its own, so a flavour line
  // never lingers until the next commit. The fade is a plain opacity change
  // (not motion), so it stays visible even under reduced motion (see the CSS
  // exemption for .touch-line), where other animations are suppressed.
  touchLineTimer = setTimeout(() => {
    el.touchLine.classList.remove("show");
  }, 4500);
}

async function takeExit() {
  const res = await post("/api/interact", { action: "exit" });
  // Only record the alternate ending (and unlock its achievement) once the
  // server has actually resolved the exit for this arc. Guarding on the
  // server's own kind == "exit" means the badge can never appear without the
  // ending truly being reached.
  if (!res || res.kind !== "exit") return;
  recordEnding(selectedArc);
  showEnding(res.ending || []);
}

function showEnding(lines) {
  el.endingText.innerHTML = "";
  lines.forEach((ln, i) => {
    const div = document.createElement("div");
    div.textContent = ln;
    if (i === lines.length - 1) div.className = "lead";
    el.endingText.appendChild(div);
  });
  if (window.ambience) window.ambience.play((meta && meta.skin) || "hallway");
  show(el.ending);
}

// After a touch folds the run, explain that the reset was the player's own doing
// (not a bug). The "don't show this again" opt-out only appears from the 2nd
// time on; once chosen, the explainer never shows again.
function maybeFoldExplainer() {
  if (!el.fold) return;
  let hide = false, seen = 0;
  try {
    hide = localStorage.getItem("h8_fold_hide") === "1";
    seen = parseInt(localStorage.getItem("h8_fold_seen") || "0", 10) || 0;
  } catch (e) {}
  if (hide) return;
  seen += 1;
  try { localStorage.setItem("h8_fold_seen", String(seen)); } catch (e) {}
  el.foldTitle.textContent = ui["fold_title"] || "Back to the start.";
  el.foldLines.innerHTML = "";
  [ui["fold_1"], ui["fold_2"]].forEach((tx) => {
    if (!tx) return;
    const p = document.createElement("p");
    p.textContent = tx;
    el.foldLines.appendChild(p);
  });
  if (el.foldHideRow) el.foldHideRow.classList.toggle("hidden", seen < 2);
  if (el.foldHide) el.foldHide.checked = false;
  // Gate the loop controls while the explainer is up (shares the onboarding
  // gate): the level-0 controls must not go live under the modal, so the reset
  // reads as a deliberate beat, not a scene that rushed past. hideFoldExplainer
  // releases it.
  onboarding = true;
  el.controls.classList.add("hidden");
  el.fold.classList.remove("hidden");
  if (el.foldGo) el.foldGo.focus();
}
function hideFoldExplainer() {
  if (el.foldHide && el.foldHide.checked) {
    try { localStorage.setItem("h8_fold_hide", "1"); } catch (e) {}
  }
  if (el.fold) el.fold.classList.add("hidden");
  // Release the control gate and hand the loop back at level 0.
  onboarding = false;
  if (el.corridor && !el.corridor.classList.contains("hidden")) {
    el.controls.classList.remove("hidden");
    decideStart = performance.now();
  }
}
if (el.foldGo) el.foldGo.addEventListener("click", hideFoldExplainer);
if (el.fold) {
  el.fold.addEventListener("click", (e) => { if (e.target === el.fold) hideFoldExplainer(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el.fold.classList.contains("hidden")) hideFoldExplainer();
  });
}

// Lingering on a detail may earn an unsettling aside from the server.
function attachInspect(node) {
  let timer = null;
  node.addEventListener("mouseenter", () => {
    const gen = renderGen;   // the loop this hover belongs to
    timer = setTimeout(async () => {
      // Bail if the loop moved on (or the line left the screen) before the
      // dwell elapsed, so a stale aside never lands on the next loop, appearing
      // "before" its prose has rendered.
      if (gen !== renderGen || !node.isConnected) return;
      const { line } = await post("/api/inspect", { prop: node.dataset.prop });
      if (gen !== renderGen || !node.isConnected) return;   // loop changed mid-request
      if (line && !el.aside.textContent) {
        el.aside.textContent = line;
        el.aside.classList.add("show");
      }
    }, 1300);
  });
  node.addEventListener("mouseleave", () => clearTimeout(timer));
}

function flash(correct) {
  const cls = correct ? "flash-good" : "flash-bad";
  el.corridor.classList.add(cls);
  setTimeout(() => el.corridor.classList.remove(cls), 1400);
}

// Hard mode's "keep scanning" lesson: pulse the prose lines whose details had
// changed, so a correct turn-back on a two-change loop reveals both. Silent, no
// text; the two lines briefly glow the arc's accent.
function flareLines(props) {
  (props || []).forEach((prop) => {
    const line = el.prose.querySelector(`.line[data-prop="${prop}"]`);
    if (line) {
      line.classList.remove("flare");
      // reflow so the animation restarts even if the class lingered
      void line.offsetWidth;
      line.classList.add("flare");
    }
  });
}

// The rule is taught by failing, not up front. The very first time the place
// resets the player, re-show the arc's own backstory intro (already localized),
// line by line, as a plain reminder of how it works. Once only.
function buildOnboard() {
  // Heading is a neutral "Instructions" label (localized), not the arc's scene
  // banner (intro[0], e.g. a time-of-day framing) which could read as part of
  // the how-to. The body keeps the backstory's own wording verbatim, minus that
  // banner line. Empty spacer lines are skipped.
  const lines = introLines.filter((s) => (s || "").trim() !== "");
  if (el.learnTitle) el.learnTitle.textContent = ui["instructions"] || "Instructions";
  if (el.learnLines) {
    el.learnLines.innerHTML = "";
    // Simple (younger-reader) register: show ONLY the short plain rule, not the
    // arc's atmospheric backstory, so the how-to is short and unmistakable.
    if (register === "simple" && ui["rules_plain"]) {
      const plain = document.createElement("p");
      plain.className = "learn-plain";
      plain.textContent = ui["rules_plain"];
      el.learnLines.appendChild(plain);
      return;
    }
    lines.slice(1).forEach((text) => {
      const p = document.createElement("p");
      p.textContent = text;
      el.learnLines.appendChild(p);
    });
  }
}
// A brief, arc-specific rule cutscene that fades into the instructions. Click,
// key, or a beat's pause advances it. Under reduced motion it waits for input
// (no timed disappearance).
function playCutscene(lines, then) {
  const clean = (lines || []).filter((s) => s && s.trim());
  if (!el.cutscene || !clean.length) { then(); return; }
  el.cutsceneText.innerHTML = "";
  clean.forEach((tx) => {
    const p = document.createElement("p");
    p.textContent = tx;
    el.cutsceneText.appendChild(p);
  });
  el.cutscene.classList.remove("hidden");
  let done = false;
  let timer = null;
  const advance = () => {
    if (done) return;
    done = true;
    clearTimeout(timer);
    document.removeEventListener("keydown", onKey);
    el.cutscene.classList.add("hidden");
    then();
  };
  function onKey() { advance(); }
  el.cutscene.onclick = advance;
  document.addEventListener("keydown", onKey);
  if (!reduceMotion) timer = setTimeout(advance, 7200);
}

// --- ending credits ---------------------------------------------------------
// Authored, English-only content (a personal dedication in the maker's voice;
// only the "View credits" trigger is localized). Rendered in the landing's
// quiet style. Each entry is [cssClass, text]; "gap" is a spacer.
const CREDITS = [
  { presenter: "a Melon Lab game", title: "EIGHT" },
  { cast: [["Game Developer, Designer & Writer", ["alvations", { n: "Claude Code", sm: true }]]] },
  { head: "PRODUCTION", cast: [
    ["Executive Producer", ["alvations"]],
    ["Administrative Support", [{ n: "Claire (AI Secretary)", sm: true }]],
  ] },
  // Single-role departments: shown directly, no section header.
  { cast: [
    ["Art Director", ["alvations"]],
    ["BGM & SFX Director", [{ n: "Claude Code", sm: true }]],
  ] },
  { head: "SPECIAL THANKS", notes: ["The AI critics who never pulled their punches"] },
  { head: "DEDICATED TO", ded: [
    ["the eldest", "“Ask your robot to make me a game”"],
    ["the youngest", "the ewe of my life"],
    ["the support", "who always believe my craziest ideas"],
  ] },
  // The closing studio splash: the wordmark alone, a copyright beneath.
  { splash: "MELON LAB", copy: "© 2026 alvations", solo: true },
];

let creditsTimer = null;
function renderCredits() {
  if (!el.creditsRoll) return;
  const cline = (cls, text) => {
    const d = document.createElement("div");
    d.className = cls;
    d.textContent = text;
    return d;
  };
  el.creditsRoll.innerHTML = "";
  CREDITS.forEach((b) => {
    const block = document.createElement("div");
    block.className = "credits-block" + (b.solo ? " credits-solo" : "");
    if (b.presenter) block.appendChild(cline("credits-presenter", b.presenter));
    if (b.splash) block.appendChild(cline("credits-splash", b.splash));
    if (b.title) block.appendChild(cline("credits-title", b.title));
    if (b.head) block.appendChild(cline("credits-head", b.head));
    (b.cast || []).forEach(([role, names]) => {
      const c = document.createElement("div");
      c.className = "credits-cast";
      c.appendChild(cline("credits-role", role));
      // A name is a string (default size) or { n, sm } for a smaller line.
      names.forEach((nm) => {
        const text = typeof nm === "string" ? nm : nm.n;
        const small = typeof nm === "object" && nm.sm;
        c.appendChild(cline("credits-name" + (small ? " credits-name-sm" : ""), text));
      });
      block.appendChild(c);
    });
    (b.notes || []).forEach((n) => block.appendChild(cline("credits-note", n)));
    (b.ded || []).forEach(([who, note]) => {
      const d = document.createElement("div");
      d.className = "credits-ded";
      d.appendChild(cline("credits-role", who));
      d.appendChild(cline("credits-note", note));
      block.appendChild(d);
    });
    (b.quote || []).forEach((q) => block.appendChild(cline("credits-quote", q)));
    if (b.by) block.appendChild(cline("credits-by", b.by));
    if (b.copy) block.appendChild(cline("credits-copy", b.copy));
    el.creditsRoll.appendChild(block);
  });
}
let creditsAfter = null;   // run once when the roll closes (win-screen transition)
function closeCredits() {
  if (!el.credits) return;
  clearTimeout(creditsTimer);
  el.credits.classList.add("hidden");
  el.creditsRoll.style.animation = "";
  const cb = creditsAfter; creditsAfter = null;
  if (typeof cb === "function") cb();
}
function openCredits(after) {
  if (!el.credits) return;
  creditsAfter = typeof after === "function" ? after : null;
  renderCredits();
  el.credits.classList.remove("hidden");
  if (window.ambience) window.ambience.play("landing");
  // Restart the roll animation from the top each time it opens.
  el.creditsRoll.style.animation = "none";
  // eslint-disable-next-line no-unused-expressions
  el.creditsRoll.offsetHeight;   // reflow so the restart takes
  el.creditsRoll.style.animation = "";
  clearTimeout(creditsTimer);
  if (reduceMotion) {
    // No roll: it reads statically, closed by the player (or after a long dwell).
    el.creditsScroller.scrollTop = 0;
  } else {
    // Auto-close a beat after the roll finishes (kept in JS so it survives even
    // if the animationend event is missed).
    creditsTimer = setTimeout(closeCredits, 54000);
  }
}
if (el.creditsDone) el.creditsDone.addEventListener("click", closeCredits);
if (el.credits) el.credits.addEventListener("click", (e) => {
  // A tap anywhere but the scrollbar skips/closes.
  if (e.target === el.credits || e.target === el.creditsScroller) closeCredits();
});
if (el.creditsRoll) el.creditsRoll.addEventListener("animationend", closeCredits);
if (el.viewCredits) el.viewCredits.addEventListener("click", openCredits);

function maybeOnboard(reset) {
  if (!reset || !el.learn || !introLines.length) return;
  if (localStorage.getItem("h8_onboarded")) return;
  localStorage.setItem("h8_onboarded", "1");
  // Gate the loop controls until the instructions are dismissed: the rule
  // cutscene runs first (several seconds), and the level-0 controls must not go
  // live underneath it. renderRoom() checks this flag; hideOnboard() releases it.
  onboarding = true;
  el.controls.classList.add("hidden");
  // First reset: the rule cutscene, then the instructions it fades into.
  playCutscene(cutsceneLines, () => {
    buildOnboard();
    el.learn.classList.remove("hidden");
    if (el.learnGo) el.learnGo.focus();
  });
}
function hideOnboard() {
  if (el.learn) el.learn.classList.add("hidden");
  // Release the gate and hand the loop back: reveal the controls (only if we are
  // actually in the corridor) and restart the deliberation timer so the first
  // post-instructions call is timed from now, not from when the room rendered.
  onboarding = false;
  if (el.corridor && !el.corridor.classList.contains("hidden")) {
    el.controls.classList.remove("hidden");
    decideStart = performance.now();
  }
}
if (el.learnGo) el.learnGo.addEventListener("click", hideOnboard);
if (el.learn) {
  // dismiss on backdrop click or Escape, like any quiet modal
  el.learn.addEventListener("click", (e) => {
    if (e.target === el.learn) hideOnboard();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el.learn.classList.contains("hidden")) hideOnboard();
  });
}

// --- flow ------------------------------------------------------------------

function renderArcCards(arcs) {
  el.arcs.innerHTML = "";
  arcs.forEach((a) => {
    const card = document.createElement("button");
    card.className = "arc-card";
    card.dataset.arc = a.id;
    card.dataset.skin = a.skin;
    card.innerHTML =
      `<div class="arc-title">${a.title}</div>` +
      `<div class="arc-tag">${a.tagline}</div>`;
    card.addEventListener("click", () => chooseArc(a));
    el.arcs.appendChild(card);
  });
}

function renderIntro(lines) {
  el.introText.innerHTML = "";
  lines.forEach((ln, i) => {
    const div = document.createElement("div");
    div.textContent = ln;
    if (i === 0) div.className = "lead";
    el.introText.appendChild(div);
  });
  // Simple reading register: a plain, spoiler-free statement of the rule under
  // the atmospheric intro, so a younger player has it in plain words up front.
  if (register === "simple" && ui["rules_plain"]) {
    const help = document.createElement("div");
    help.className = "intro-plain";
    help.textContent = ui["rules_plain"];
    el.introText.appendChild(help);
  }
}

async function chooseArc(a) {
  selectedArc = a.id;
  // The first time a player ever runs an arc, Act 2 (the touch / action / flavour
  // layer) stays out of the way so they meet the core loop first. It holds for
  // the whole first run; from the next run on, the layer appears (gated).
  if (!mem.arcStarted) mem.arcStarted = {};
  firstArcRun = !mem.arcStarted[a.id];
  if (firstArcRun) { mem.arcStarted[a.id] = true; saveMem(); }
  applyMeta(a);              // skin the intro screen immediately
  const p = await post("/api/new", { arc: a.id });
  applyMeta(p.meta);
  introLines = p.intro || [];   // keep for the first-reset onboarding panel
  cutsceneLines = p.cutscene || [];   // the rule cutscene before those instructions
  renderIntro(p.intro);
  current = p;
  drift = 0;
  show(el.intro);
}

function enterCorridor() {
  show(el.corridor);
  run = freshRun();   // a new climb begins
  onboarding = false; // safety: never carry a stale instructions gate into a climb
  recordPlay();   // notes a play, and the release-day badge if today is the day
  if (window.ambience) window.ambience.play((meta && meta.skin) || "hallway");
  renderRoom(current);
}

// The URL a winner passes on. Inside the Spaces iframe this is the live app
// itself (directly playable); locally it is the dev origin. Owner can override
// with window.H8_SHARE_URL if a canonical landing page is preferred.
function shareUrl() {
  return (window.H8_SHARE_URL || (location.origin + location.pathname))
    .replace(/[?#].*$/, "");
}

// Pick one of the eight invitation lines at random and wire the share targets.
// Progressive disclosure: the panel stays collapsed behind the arc's quiet
// prompt until the player taps it, so the win screen stays calm by default.
function buildShare() {
  if (!el.share) return;
  const t = (k, fb) => ui[k] || fb;
  const n = 1 + Math.floor(Math.random() * 8);
  const line = t(`share_${n}`, "I found the way out. Now it's your turn.");
  const url = shareUrl();
  // The trigger is the arc's own (localized) prompt; the panel starts collapsed.
  if (el.shareOpen) {
    el.shareOpen.textContent = (meta && meta.share_prompt) || t("share_native", "Share");
    el.shareOpen.classList.remove("hidden");
  }
  if (el.sharePanel) {
    el.sharePanel.classList.add("hidden");
    el.sharePanel.classList.remove("show");
  }
  if (el.shareLine) el.shareLine.textContent = line;

  const eLine = encodeURIComponent(line);
  const eUrl = encodeURIComponent(url);
  // X and Facebook carry the invitation text; LinkedIn only takes a URL (it
  // pulls its own preview text), so the line rides along in the others.
  if (el.shareX) el.shareX.href =
    `https://twitter.com/intent/tweet?text=${eLine}&url=${eUrl}`;
  if (el.shareFb) el.shareFb.href =
    `https://www.facebook.com/sharer/sharer.php?u=${eUrl}&quote=${eLine}`;
  if (el.shareLi) el.shareLi.href =
    `https://www.linkedin.com/sharing/share-offsite/?url=${eUrl}`;

  // Mobile-first: where a native share sheet exists (all modern phones, many
  // desktops), that single button reaches Instagram, Snapchat, X, Messages,
  // everything, so we lead with it and hide the explicit platform row. Only
  // browsers without the API (mostly older desktop) fall back to the X /
  // Facebook / LinkedIn links. Copy link is always available.
  const hasNative = typeof navigator.share === "function";
  if (el.shareNative) {
    el.shareNative.classList.toggle("hidden", !hasNative);
    if (hasNative) {
      el.shareNative.onclick = () => {
        recordShare();
        navigator.share({ text: line, url }).catch(() => {});
      };
    }
  }
  if (el.sharePlatforms) el.sharePlatforms.classList.toggle("hidden", hasNative);

  // Copy link: copies the invitation plus the URL, ready to paste anywhere
  // (including an Instagram caption). Brief confirmation, then reverts.
  if (el.shareCopy) {
    el.shareCopy.onclick = async () => {
      recordShare();
      const payload = `${line} ${url}`;
      try {
        await navigator.clipboard.writeText(payload);
      } catch (e) {
        const ta = document.createElement("textarea");
        ta.value = payload;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); } catch (_) {}
        ta.remove();
      }
      const was = el.shareCopy.textContent;
      el.shareCopy.textContent = t("share_copied", "Link copied");
      setTimeout(() => { el.shareCopy.textContent = was; }, 1800);
    };
  }
}

// Clicking any explicit platform target counts as sharing (for the badge).
[el.shareX, el.shareFb, el.shareLi].forEach((a) => {
  if (a) a.addEventListener("click", () => recordShare());
});

// Tap the quiet prompt to disclose the share panel (invitation line + targets).
if (el.shareOpen) {
  el.shareOpen.addEventListener("click", () => {
    el.shareOpen.classList.add("hidden");
    el.shareOpen.setAttribute("aria-expanded", "true");
    if (el.sharePanel) {
      el.sharePanel.classList.remove("hidden");
      requestAnimationFrame(() => el.sharePanel.classList.add("show"));
    }
  });
}

// The fleeting "look back" reveal. Reset to its collapsed state each win; the
// line only appears (and then self-erases) if the player taps the toggle.
let lookText = "";
let lookTimer = null;
let lookFade = null;
function buildLook(p) {
  if (!el.look) return;
  clearTimeout(lookTimer);
  clearTimeout(lookFade);
  lookText = p.attempt_text || "";
  if (!lookText) {
    el.look.classList.add("hidden");
    return;
  }
  el.look.classList.remove("hidden");
  el.lookBack.classList.remove("hidden");
  el.lookBack.setAttribute("aria-expanded", "false");
  el.lookLine.classList.remove("show");
  el.lookLine.textContent = "";
}
if (el.lookBack) {
  el.lookBack.addEventListener("click", () => {
    el.lookBack.classList.add("hidden");
    el.lookBack.setAttribute("aria-expanded", "true");
    // The run-count line, and (if the climb earned one) the quieter "how you did"
    // record beneath it. Both our own catalog strings, so building the node is safe.
    el.lookLine.textContent = lookText;
    if (readRecordText) {
      const rec = document.createElement("span");
      rec.className = "look-record";
      rec.textContent = readRecordText;
      el.lookLine.appendChild(document.createElement("br"));
      el.lookLine.appendChild(rec);
    }
    requestAnimationFrame(() => el.lookLine.classList.add("show"));
    // Let it linger, then fade out and reclaim the space so the eye returns to
    // sharing or replaying. Under reduced motion we leave it in place: text that
    // vanishes on a timer is hostile to anyone who reads slowly.
    if (reduceMotion) return;
    clearTimeout(lookTimer);
    lookTimer = setTimeout(() => {
      el.lookLine.classList.remove("show");
      clearTimeout(lookFade);
      lookFade = setTimeout(() => el.look.classList.add("hidden"), 900);
    }, 6500);
  });
}

// A quiet, adaptive nudge toward what is left to find: unseen fragments here,
// then the other places, then eight escapes from one.
function buildNudge(arc) {
  if (!el.nudge) return;
  el.nudge.classList.add("hidden");
  el.nudge.textContent = "";
  const total = flashCount(arc), seen = flashSeen(arc);
  let text = "";
  if (total && seen < total) {
    text = (ui["nudge_frags"] || "There are {n} memories here you have not seen yet.")
      .replace("{n}", String(total - seen));
  } else if (!ARC_IDS.every((a) => flashCount(a) && flashSeen(a) >= flashCount(a))) {
    text = ui["nudge_arcs"] || "Two other places are also called 8.";
  } else {
    text = ui["nudge_eight"] || "Eight escapes from one place is a different kind of remembering.";
  }
  if (text) { el.nudge.textContent = text; el.nudge.classList.remove("hidden"); }
}

// The win screen's primary button: on a first escape it invites the credits
// ("End Credits"); otherwise it replays ("Walk it again").
function setAgainMode(mode) {
  againMode = mode;
  if (el.again) el.again.textContent = (mode === "credits")
    ? (ui["end_credits"] || "End Credits")
    : (ui["again"] || "Walk it again");
}

// Roll the credits (from the button OR the linger timer), then hand back the
// replay button and reveal the nudge. No-op once played, or if the player has
// already left the win screen.
function playCredits() {
  clearTimeout(creditsAutoTimer);
  if (againMode !== "credits") return;
  if (el.win && el.win.classList.contains("hidden")) return;
  openCredits(() => { setAgainMode("replay"); buildNudge(selectedArc); });
}

function showWin(p) {
  el.winText.innerHTML = "";
  (p.win_text || []).forEach((ln, i) => {
    const div = document.createElement("div");
    div.textContent = ln;
    if (i === p.win_text.length - 1) div.className = "lead";
    el.winText.appendChild(div);
  });
  buildLook(p);
  buildShare();
  clearTimeout(creditsAutoTimer);
  if (winIsFirst) {
    // First escape of this arc: the credits are the next beat. Hold the nudge
    // back and turn the primary button into the invitation to roll them; the
    // nudge and "Walk it again" arrive only after the credits have played, so
    // the player has time to sit with the look-back and share first. If they
    // just linger, the credits auto-roll after a readable dwell (the win screen
    // returns after, so this only ever gives them more).
    if (el.nudge) el.nudge.classList.add("hidden");
    setAgainMode("credits");
    creditsAutoTimer = setTimeout(playCredits, CREDITS_DWELL);
  } else {
    buildNudge(selectedArc);
    setAgainMode("replay");
  }
  // Let the ending itself land first: the "look back" and share surfaces are
  // hushed for a beat so the benediction is not sharing the moment with a
  // scoreboard and a share sheet. Then they fade up.
  el.win.classList.add("win-hush");
  show(el.win);
  const settle = () => el.win.classList.remove("win-hush");
  if (reduceMotion) settle();
  else setTimeout(settle, 1600);
}

async function loadSelect() {
  const { arcs } = await get("/api/arcs");
  ARCS_BY_ID = Object.fromEntries(arcs.map((a) => [a.id, a]));
  renderArcCards(arcs);
  el.body.dataset.skin = lastSkin();   // keep the last arc's colour on the landing
  show(el.select);
  revealSelect(); // returning from a loop: the ways are already known, show them
  if (window.ambience) window.ambience.play("landing");
}

// Lines shown when the player admits doubt and is sent back to look again.
// Localized (ui|hesitate_1..4), with an English fallback per line.
const HESITATION_EN = [
  "You hesitate. Look again.",
  "You're not sure. You take another look.",
  "Doubt stops you. Read it once more.",
  "You hold back, and let your eyes travel over it again.",
];
function hesitationLine() {
  const i = Math.floor(Math.random() * HESITATION_EN.length);
  return ui["hesitate_" + (i + 1)] || HESITATION_EN[i];
}

// Commit the pending choice to the server and move on.
async function commit(confidence) {
  const dir = pendingChoice;
  // Movement sound, keyed to how long the player lingered and, if they answered
  // the certainty prompt, how sure they said they were.
  if (window.ambience) {
    window.ambience.step(dir, performance.now() - decideStart, confidence);
  }
  el.confidence.classList.add("hidden");
  let p;
  try {
    p = await post("/api/act", { choice: dir, confidence });
    if (!p || !p.room || typeof p.correct !== "boolean") throw new Error("bad payload");
  } catch (e) {
    // Network blip or a bad response mid-commit. /api/act is NOT idempotent, so we
    // must not just let the player re-decide against the stale render: the call may
    // actually have landed and advanced (or reset) the server. Resync to the
    // server's real current room and render THAT, so whatever actually happened,
    // the next decision is made against what is truly there. If the server is also
    // unreachable, fall back to restoring controls on the current render so the run
    // is never soft-locked.
    pendingChoice = null;
    hesitated = false;
    try {
      const cur = await get("/api/room");
      if (cur && cur.room) { renderRoom(cur); return; }
    } catch (e2) { /* still unreachable; fall through to the best-effort restore */ }
    el.controls.classList.remove("hidden");
    if (current) buildTouch(current);
    decideStart = performance.now();
    return;
  }
  pendingChoice = null;
  hesitated = false;
  // Sparingly, when the player bolts back from a changed loop, add hurried
  // running steps. Mostly on a real anomaly; rarely on a false alarm.
  if (window.ambience && dir === "back" && Math.random() < (p.had_anomaly ? 0.22 : 0.05)) {
    window.ambience.run(dir);
  }
  flash(p.correct);
  noteAnomaly(selectedArc, p.anomaly);   // collect a loop-aware NPC acknowledgement
  // Hard mode: on a correct turn-back where TWO details had moved, pulse both
  // lines so the player learns a second had also changed (keep scanning). Silent,
  // post-decision, only when a double really happened. Give it a beat to be seen.
  if (p.flare_props && p.flare_props.length >= 2) {
    flareLines(p.flare_props);
    await sleep(1100);
  }
  await sleep(1500);
  if (p.won) {
    // How this climb was won: steady (never guessed), cold (no touches), and
    // nerve (the final call was a correct turn-back on a real change).
    const marks = {
      steady: !run.guessed,
      cold: run.touches === 0,
      nerve: !!p.had_anomaly && dir === "back",
    };
    winIsFirst = !((mem.wins[selectedArc] || 0) > 0);
    recordWin(selectedArc, p.attempts || 1);
    recordRun(marks, p.attempts || 1);
    readRecordText = readRecord(marks);
    showWin(p);
    return;
  }
  // A wrong call resets to the start (server sends level 0). Re-render the
  // restarted place, then, if this is the player's first reset, teach the rule.
  const wasReset = !p.correct;
  if (wasReset) run = freshRun();   // the climb broke; the next one starts clean
  renderRoom(p);
  maybeOnboard(wasReset);
}

// choice -> sometimes the game stops to ask how sure you are.
// The chance grows as you near the exit, and never fires twice in one turn.
el.controls.addEventListener("click", (e) => {
  const btn = e.target.closest(".choice");
  if (!btn) return;
  pendingChoice = btn.dataset.choice;
  el.controls.classList.add("hidden");
  clearTouch();                     // touches close once a call is committed

  const level = (current && current.level) || 0;
  const goal = (current && current.goal) || 8;
  const chance = Math.min(0.85, 0.12 + level * (0.7 / goal));
  if (!hesitated && Math.random() < chance) {
    el.confidence.classList.remove("hidden");
  } else {
    commit(null);
  }
});

// confidence -> certainty commits; doubt buys one more look and a re-decide.
el.confidence.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-conf]");
  if (!btn || !pendingChoice) return;
  const confidence = parseInt(btn.dataset.conf, 10);

  if (confidence >= 3) {
    commit(confidence);
    return;
  }
  // Uncertain: don't commit. Return to the scene to decide again.
  run.guessed = true;   // admitting a guess this climb forfeits a "steady" escape
  hesitated = true;
  pendingChoice = null;
  el.confidence.classList.add("hidden");
  el.aside.textContent = hesitationLine();
  el.aside.classList.add("show");
  el.controls.classList.remove("hidden");
  if (current) buildTouch(current);   // let the room be touched again on re-look
});

if (el.exitTake) el.exitTake.addEventListener("click", takeExit);
if (el.endingBack) el.endingBack.addEventListener("click", loadSelect);
el.begin.addEventListener("click", enterCorridor);
el.giveup.addEventListener("click", loadSelect);
el.introBack.addEventListener("click", loadSelect);
// (the win screen's "Change scenario" was removed; use the backstory Back)
// "Walk it again" returns to the arc's own backstory screen: Begin replays it,
// and Back (on that screen) goes to scenario selection. That backstory Back is
// the route to change scenario, so the win screen needs no separate button.
el.again.addEventListener("click", async () => {
  if (againMode === "credits") { playCredits(); return; }
  const a = ARCS_BY_ID[selectedArc];
  if (a) await chooseArc(a);
});

// --- collection + achievements (persistent, exportable) --------------------
// A per-player memory of what they have seen and done: which flashbacks, which
// arcs cleared and how, alternate endings, the NPC's acknowledgements. It lives
// in localStorage, unlocks achievements, and can be exported to an (obfuscated)
// JSON save. Because the NPC reacts to each player differently, no two full
// saves are alike.
const RELEASE_DAY = "2026-07-06";   // play on this local date...
const RELEASE_REVEAL = "2026-07-07"; // ...and the badge shows from here (all of earth past the 6th)
// Order matches the landing/select screen (server list_arcs: default first, then
// alphabetical), so the Recollections ledger and anything else iterating arcs
// reads in the same order the player sees on the way in.
const ARC_IDS = ["hallway-eight", "coach8", "stairway8"];
const NPC_PROP = { "hallway-eight": "figure", "stairway8": "figure", "coach8": "passenger" };

function blankMem() {
  return { v: 1, flash: {}, flashText: {}, wins: {}, hardWins: {}, insaneWins: {}, clean: {}, ends: {}, npc: {},
           shared: false, releaseDay: false, plays: 0, promos: [], melon: false, langs: [],
           arcStarted: {},
           records: { steady: false, cold: false, nerve: false, streak: 0, best: 0 } };
}
let mem = loadMem();
// `mem` now exists, so the Insane unlock gate can finally be evaluated. The first
// applySettings() ran before this (with mem in the temporal dead zone), so redo
// just the difficulty row to reveal an already-earned Insane on a fresh load.
try { applyDifficultyUI(); } catch (e) {}
function loadMem() {
  try {
    const raw = localStorage.getItem("h8_mem");
    if (raw) return Object.assign(blankMem(), JSON.parse(raw));
  } catch (e) {}
  return blankMem();
}
function saveMem() {
  try { localStorage.setItem("h8_mem", JSON.stringify(mem)); } catch (e) {}
  if (el.achievements && !el.achievements.classList.contains("hidden")) renderAchievements();
}
function localDate() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function recordFlashback(arc, idx, line) {
  if (idx == null) return;
  const a = mem.flash[arc] || (mem.flash[arc] = []);
  let dirty = false;
  if (!a.includes(idx)) { a.push(idx); dirty = true; }
  // Keep the fragment's own words so the collection can recap it later.
  if (line) {
    if (!mem.flashText) mem.flashText = {};
    const t = mem.flashText[arc] || (mem.flashText[arc] = {});
    if (t[idx] !== line) { t[idx] = line; dirty = true; }
  }
  if (dirty) saveMem();
}
function recordWin(arc, attempts) {
  // Record the escape, and (if it was a hard/insane run) that tier's escape.
  const diff = effectiveDifficulty();
  if (diff === "hard") {
    if (!mem.hardWins) mem.hardWins = {};
    mem.hardWins[arc] = (mem.hardWins[arc] || 0) + 1;
  } else if (diff === "insane") {
    if (!mem.insaneWins) mem.insaneWins = {};
    mem.insaneWins[arc] = (mem.insaneWins[arc] || 0) + 1;
  }
  mem.wins[arc] = (mem.wins[arc] || 0) + 1;
  if (attempts <= 1) mem.clean[arc] = true;
  saveMem();
}
// Personal records: a quiet, self-competition ledger of *how* runs were won. Not
// badges, not scored, never sent anywhere. Persisted in mem (so it rides along in
// the exported save) and surfaced on the collection page.
function recordRun(marks, attempts) {
  const r = mem.records || (mem.records = { steady: false, cold: false, nerve: false, streak: 0, best: 0 });
  if (marks.steady) r.steady = true;
  if (marks.cold) r.cold = true;
  if (marks.nerve) r.nerve = true;
  // A run of consecutive escapes made without a single reset.
  r.streak = attempts <= 1 ? (r.streak || 0) + 1 : 0;
  r.best = Math.max(r.best || 0, r.streak);
  saveMem();
}
// The fleeting "how you did" line for the win screen: one in-world sentence for
// the strongest thing about this climb, or nothing if it was an ordinary win.
function readRecord(marks) {
  if (marks.nerve) return ui["read_nerve"] || "You turned back at the very last door, and you were right.";
  if (marks.cold) return ui["read_cold"] || "You walked it without a second look.";
  if (marks.steady) return ui["read_steady"] || "You never once called it a guess.";
  return "";
}
function recordEnding(arc) { mem.ends[arc] = true; saveMem(); }
function recordShare() { if (!mem.shared) { mem.shared = true; saveMem(); } }
function recordNpc(arc, val) {
  const m = mem.npc[arc] || (mem.npc[arc] = {});
  m[val] = (m[val] || 0) + 1;
  saveMem();
}
function recordPlay() {
  mem.plays = (mem.plays || 0) + 1;
  if (localDate() === RELEASE_DAY) mem.releaseDay = true;
  saveMem();
}
// The loop-aware NPC twist: figures that turn/beckon ("knows"), talkers ("speaks").
function noteAnomaly(arc, anomaly) {
  if (!anomaly) return;
  if (anomaly.prop === NPC_PROP[arc] && (anomaly.val === "knows" || anomaly.val === "speaks")) {
    recordNpc(arc, anomaly.val);
  }
}

function flashCount(arc) {
  const a = ARCS_BY_ID[arc];
  return (a && a.flashbacks) || 0;
}
function flashSeen(arc) { return (mem.flash[arc] || []).length; }

// Each achievement is {id, test(mem)->bool}; names/descriptions are UI text.
const ACHS = [
  { id: "out_hallway-eight", test: () => (mem.wins["hallway-eight"] || 0) > 0 },
  { id: "out_stairway8", test: () => (mem.wins["stairway8"] || 0) > 0 },
  { id: "out_coach8", test: () => (mem.wins["coach8"] || 0) > 0 },
  { id: "out_all", test: () => ARC_IDS.every((a) => (mem.wins[a] || 0) > 0) },
  { id: "flawless", test: () => ARC_IDS.some((a) => mem.clean[a]) },
  { id: "eight_times", test: () => ARC_IDS.some((a) => (mem.wins[a] || 0) >= 8) },
  { id: "end_hallway-eight", test: () => !!mem.ends["hallway-eight"] },
  { id: "end_stairway8", test: () => !!mem.ends["stairway8"] },
  { id: "end_coach8", test: () => !!mem.ends["coach8"] },
  { id: "npc_knows", test: () => ARC_IDS.some((a) => mem.npc[a] && Object.keys(mem.npc[a]).length) },
  { id: "shared", test: () => !!mem.shared },
  { id: "opening_night", test: () => mem.releaseDay && localDate() >= RELEASE_REVEAL },
  { id: "flash_hallway-eight", test: () => flashCount("hallway-eight") > 0 && flashSeen("hallway-eight") >= flashCount("hallway-eight") },
  { id: "flash_stairway8", test: () => flashCount("stairway8") > 0 && flashSeen("stairway8") >= flashCount("stairway8") },
  { id: "flash_coach8", test: () => flashCount("coach8") > 0 && flashSeen("coach8") >= flashCount("coach8") },
  { id: "total_recall", test: () => ARC_IDS.every((a) => flashCount(a) > 0 && flashSeen(a) >= flashCount(a)) },
  // How a run was won (formerly the "records" ledger): now achievements, so they
  // stay hidden until earned like everything else.
  { id: "steady", test: () => !!(mem.records || {}).steady },
  { id: "cold", test: () => !!(mem.records || {}).cold },
  { id: "nerve", test: () => !!(mem.records || {}).nerve },
  { id: "streak", test: () => ((mem.records || {}).best || 0) >= 3 },
  // Hard-mode escapes.
  { id: "hard_hallway-eight", test: () => (mem.hardWins || {})["hallway-eight"] > 0 },
  { id: "hard_stairway8", test: () => (mem.hardWins || {})["stairway8"] > 0 },
  { id: "hard_coach8", test: () => (mem.hardWins || {})["coach8"] > 0 },
  { id: "hard_all", test: () => ARC_IDS.every((a) => (mem.hardWins || {})[a] > 0) },
  // Insane-tier escapes (the hidden difficulty that randomizes the baseline each
  // run). Earnable only after Insane is unlocked, so they are NOT part of the
  // unlock gate below (that would be a chicken-and-egg).
  { id: "insane_hallway-eight", test: () => (mem.insaneWins || {})["hallway-eight"] > 0 },
  { id: "insane_stairway8", test: () => (mem.insaneWins || {})["stairway8"] > 0 },
  { id: "insane_coach8", test: () => (mem.insaneWins || {})["coach8"] > 0 },
  { id: "insane_all", test: () => ARC_IDS.every((a) => (mem.insaneWins || {})[a] > 0) },
  { id: "melon", test: () => !!mem.melon },   // studio badge (kept for later use)
];

// Insane unlocks only for a true completionist: every achievement earned, EXCEPT
// the ones that cannot be earned through skill right now (the held studio badge,
// the date-locked opening-night badge) and the Insane badges themselves. Nobody
// is expected to reach this for weeks. Kept out of the difficulty picker until
// then, so Insane ships hidden and unlockable, never breaking the other modes.
const INSANE_GATE_EXCLUDE = new Set([
  "melon", "opening_night",
  "insane_hallway-eight", "insane_stairway8", "insane_coach8", "insane_all",
]);
function insaneUnlocked() {
  // Defensive: this is reachable very early (effectiveDifficulty -> headers on the
  // first fetch) before ACHS is initialized. If achievements cannot be computed
  // yet, Insane is simply locked (the correct default), never a load-time crash.
  try {
    const state = computeAch();
    return ACHS.every((a) => INSANE_GATE_EXCLUDE.has(a.id) || state[a.id]);
  } catch (e) {
    return false;
  }
}

// English badge text (name + one-line description). Discovered by playing; no
// spoilers of the specific detail to watch.
const ACH_TEXT = {
  "out_hallway-eight": ["Out of Hallway 8", "Escape the corridor."],
  "out_stairway8": ["Out of Stairway 8", "Reach the ground floor."],
  "out_coach8": ["Out of Coach 8", "Step off the train."],
  "out_all": ["All the way out", "Escape all three places."],
  "flawless": ["Flawless", "Escape a place without a single reset."],
  "eight_times": ["Eight times through", "Escape one place eight times."],
  "end_hallway-eight": ["The lobby that won't open", "Find Hallway 8's other ending."],
  "end_stairway8": ["The stairs that only climb", "Find Stairway 8's other ending."],
  "end_coach8": ["The platform that isn't yours", "Find Coach 8's other ending."],
  "npc_knows": ["It knows you", "Be acknowledged by the one who is always ahead."],
  "shared": ["Passed it on", "Send the place to someone else."],
  "opening_night": ["Opening night", "Play on the day it opened."],
  "flash_hallway-eight": ["Hallway, remembered", "See every fragment in Hallway 8."],
  "flash_stairway8": ["Stairway, remembered", "See every fragment in Stairway 8."],
  "flash_coach8": ["Coach, remembered", "See every fragment in Coach 8."],
  "total_recall": ["Total recall", "See every last fragment, everywhere."],
  "steady": ["Steady", "Escape without a single guess."],
  "cold": ["Cold read", "Escape without a second look."],
  "nerve": ["Nerve", "Turn back at the final door, and be right."],
  "streak": ["On a roll", "Three clean escapes in a row."],
  "hard_hallway-eight": ["Hallway, harder", "Escape Hallway 8 on hard."],
  "hard_stairway8": ["Stairway, harder", "Escape Stairway 8 on hard."],
  "hard_coach8": ["Coach, harder", "Escape Coach 8 on hard."],
  "hard_all": ["Nowhere left soft", "Escape all three on hard."],
  "insane_hallway-eight": ["Hallway, unmade", "Escape Hallway 8 on insane."],
  "insane_stairway8": ["Stairway, unmade", "Escape Stairway 8 on insane."],
  "insane_coach8": ["Coach, unmade", "Escape Coach 8 on insane."],
  "insane_all": ["Trust nothing", "Escape all three on insane."],
  "melon": ["Melon Supporter", "Thank you for keeping the lights on. From all of us at Melon Labs."],
};
function computeAch() {
  const out = {};
  ACHS.forEach((a) => { try { out[a.id] = !!a.test(); } catch (e) { out[a.id] = false; } });
  return out;
}

// Per-badge line glyphs, drawn in the game's own hand: thin single-weight
// strokes on a 24 grid, no fill, inheriting the tile colour (dim when locked,
// accent when earned). Elegant and a little cryptic, never loud or cartoonish.
const ACH_ICON = {
  // three ways out: a door swung open, stairs let down, a car with an open side
  "out_hallway-eight": '<path d="M5 21V4h8v17"/><path d="M13 5l5-1v15l-5-1"/><path d="M11 13v1"/>',
  "out_stairway8": '<path d="M4 6h4v4h4v4h4v4h4"/><path d="M18 15v3m-2-1l2 2 2-2"/>',
  "out_coach8": '<rect x="3" y="6" width="18" height="11" rx="2"/><path d="M9 6v11"/><path d="M6 20l1.4-3M18 20l-1.4-3"/>',
  "out_all": '<path d="M3 21V9h4v12M10 21V5h4v16M17 21V10h4v11"/>',
  // flawless: a whole, unbroken gem
  "flawless": '<path d="M12 3l7 6-7 12L5 9z"/><path d="M5 9h14M12 3v18"/>',
  // eight times: the mark of the place, twice-drawn
  "eight_times": '<circle cx="12" cy="8" r="3"/><circle cx="12" cy="15.5" r="3.6"/>',
  // wrong endings: a door with no give, stairs that only rise, a leaving platform
  "end_hallway-eight": '<rect x="5" y="3" width="14" height="18" rx="1"/><circle cx="15" cy="12" r="1"/><path d="M15 13v3"/>',
  "end_stairway8": '<path d="M4 19h4v-4h4v-4h4v-4h4"/><path d="M18 8V5m-2 2l2-2 2 2"/>',
  "end_coach8": '<path d="M2 18h20"/><rect x="4" y="8" width="11" height="6" rx="1"/><path d="M17 11h4m-2-2l2 2-2 2"/>',
  // it knows you: an eye that is always ahead
  "npc_knows": '<path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="2.5"/>',
  // passed it on: three points, joined and sent outward
  "shared": '<circle cx="6" cy="12" r="2"/><circle cx="17" cy="6" r="2"/><circle cx="17" cy="18" r="2"/><path d="M7.8 11l7.4-4M7.8 13l7.4 4"/>',
  // opening night: a first, thin moon
  "opening_night": '<path d="M17 12.5A6 6 0 1111 6.5a5 5 0 006 6z"/><path d="M18.5 4l.5 1.4 1.4.5-1.4.5-.5 1.4-.5-1.4L16.6 6l1.4-.5z"/>',
  // fragments remembered (per place): a single spark
  "flash_hallway-eight": '<path d="M12 3l1.7 6.3L20 11l-6.3 1.7L12 20l-1.7-7.3L4 11l6.3-1.7z"/>',
  "flash_stairway8": '<path d="M12 3l1.7 6.3L20 11l-6.3 1.7L12 20l-1.7-7.3L4 11l6.3-1.7z"/>',
  "flash_coach8": '<path d="M12 3l1.7 6.3L20 11l-6.3 1.7L12 20l-1.7-7.3L4 11l6.3-1.7z"/>',
  // total recall: every spark, a small constellation
  "total_recall": '<path d="M9 6l1 3.2L13 10l-3 .8L9 14l-1-3.2L5 10l3-.8z"/><path d="M17 12l.7 2.2L20 15l-2.3.8L17 18l-.7-2.2L14 15l2.3-.8z"/><circle cx="18" cy="6" r="1"/><circle cx="6" cy="17" r="1"/>',
  // how a run was won: steady (a level), cold read (a snow star), nerve (a
  // return arrow), streak (three in a row).
  "steady": '<path d="M4 12h16"/><circle cx="12" cy="12" r="2.4"/>',
  "cold": '<path d="M12 3v18M4.5 7.5l15 9M19.5 7.5l-15 9"/>',
  "nerve": '<path d="M9 5l-4 4 4 4"/><path d="M5 9h9a5 5 0 015 5v4"/>',
  "streak": '<circle cx="6" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="18" cy="12" r="1.6"/>',
  // hard-mode escapes: a sharpened, nested gem; all-three is a small trio.
  "hard_hallway-eight": '<path d="M12 2l6 10-6 10-6-10z"/><path d="M12 7l3 5-3 5-3-5z"/>',
  "hard_stairway8": '<path d="M12 2l6 10-6 10-6-10z"/><path d="M12 7l3 5-3 5-3-5z"/>',
  "hard_coach8": '<path d="M12 2l6 10-6 10-6-10z"/><path d="M12 7l3 5-3 5-3-5z"/>',
  "hard_all": '<path d="M7 4l3 5-3 5-3-5z"/><path d="M17 4l3 5-3 5-3-5z"/><path d="M12 12l3 5-3 5-3-5z"/>',
  "insane_hallway-eight": '<path d="M12 2l7 6-7 14-7-14z"/><path d="M12 8v8"/><path d="M9 12h6"/>',
  "insane_stairway8": '<path d="M12 2l7 6-7 14-7-14z"/><path d="M12 8v8"/><path d="M9 12h6"/>',
  "insane_coach8": '<path d="M12 2l7 6-7 14-7-14z"/><path d="M12 8v8"/><path d="M9 12h6"/>',
  "insane_all": '<path d="M6 3l2.5 4L6 11z"/><path d="M18 3l-2.5 4L18 11z"/><path d="M12 9l3 6-3 6-3-6z"/><path d="M12 13v4"/>',
  // the studio: handled specially (a full-colour melon), see achIconSvg.
  "melon": "",
};
// The one deliberate break from the monochrome line style: a warm, full-colour
// watermelon slice for the studio-supporter badge. A little thank-you that pops.
const ACH_MELON_SVG =
  '<svg class="ach-icon ach-icon-melon" viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">' +
  '<path d="M2 6.5 A10 10 0 0 0 22 6.5 Z" fill="#3f8f45"/>' +
  '<path d="M3.4 6.5 A8.6 8.6 0 0 0 20.6 6.5 Z" fill="#8ecb6a"/>' +
  '<path d="M4.9 6.5 A7.1 7.1 0 0 0 19.1 6.5 Z" fill="#ec5567"/>' +
  '<g fill="#2b2b2b">' +
  '<ellipse cx="9" cy="8.4" rx=".55" ry=".85"/>' +
  '<ellipse cx="12" cy="9.1" rx=".55" ry=".85"/>' +
  '<ellipse cx="15" cy="8.4" rx=".55" ry=".85"/>' +
  '<ellipse cx="10.6" cy="10.8" rx=".55" ry=".85"/>' +
  '<ellipse cx="13.4" cy="10.8" rx=".55" ry=".85"/>' +
  '</g></svg>';
// A padlock for a badge not yet earned: clearer than an abstract node, and it
// keeps the specific glyph (and its hint) hidden until the moment it unlocks.
const ACH_LOCKED_ICON = '<rect x="5" y="11" width="14" height="9" rx="1.5"/>' +
  '<path d="M8 11V8a4 4 0 018 0v3"/><circle cx="12" cy="15" r="1"/><path d="M12 15.8v2"/>';
function achIconSvg(id, on) {
  if (id === "melon" && on) return ACH_MELON_SVG;   // the one full-colour badge
  const inner = on ? (ACH_ICON[id] || ACH_LOCKED_ICON) : ACH_LOCKED_ICON;
  return '<svg class="ach-icon" viewBox="0 0 24 24" width="26" height="26" fill="none" ' +
    'stroke="currentColor" stroke-width="1.4" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' + inner + '</svg>';
}
// Localized badge name + description, falling back to the English ACH_TEXT.
function achText(id) {
  const fb = ACH_TEXT[id] || [id, ""];
  return [ui["ach_n_" + id] || fb[0], ui["ach_d_" + id] || fb[1]];
}

// --- (light) obfuscation for the save file: a keystream XOR seeded with a
// phrase the player never sees, so a save is not human-readable and the number
// of achievements cannot be eyeballed from the JSON. Not real cryptography. ---
function keystream(seed, len) {
  let h = 2166136261 >>> 0;
  for (const c of seed) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }
  const out = new Uint8Array(len);
  let x = h || 1;
  for (let i = 0; i < len; i++) {
    x ^= x << 13; x >>>= 0; x ^= x >> 17; x ^= x << 5; x >>>= 0;
    out[i] = x & 0xff;
  }
  return out;
}
const SEED = "melon8";
function encBlob(obj) {
  const data = new TextEncoder().encode(JSON.stringify(obj));
  const ks = keystream(SEED, data.length);
  const out = new Uint8Array(data.length);
  for (let i = 0; i < data.length; i++) out[i] = data[i] ^ ks[i];
  let s = ""; out.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s);
}
function decBlob(str) {
  const bytes = Uint8Array.from(atob(str), (c) => c.charCodeAt(0));
  const ks = keystream(SEED, bytes.length);
  const out = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) out[i] = bytes[i] ^ ks[i];
  return JSON.parse(new TextDecoder().decode(out));
}

// The player's chosen settings (difficulty, reading register, display, language)
// travel with the save so a device swap carries the whole setup, not just
// progress. Kept in localStorage; gathered here and restored on import.
const SETTING_KEYS = ["h8_diff", "h8_register", "h8_text", "h8_bright", "h8_motion", "h8_lang"];
function gatherSettings() {
  const s = {};
  SETTING_KEYS.forEach((k) => { const v = localStorage.getItem(k); if (v != null) s[k] = v; });
  return s;
}
function applyImportedSettings(s) {
  if (!s || typeof s !== "object") return;
  SETTING_KEYS.forEach((k) => {
    if (s[k] != null) { try { localStorage.setItem(k, s[k]); } catch (e) {} }
  });
  // Re-sync the in-memory choices and the whole UI to the restored settings.
  difficulty = localStorage.getItem("h8_diff") || "normal";
  register = localStorage.getItem("h8_register") || "normal";
  const newLang = localStorage.getItem("h8_lang");
  if (newLang && newLang !== lang) { lang = newLang; document.documentElement.lang = lang.split("_")[0]; }
  applySettings();
  applyUI();
}

function exportSave() {
  const payload = {
    game: "8", version: 1,
    memory: encBlob(mem),          // NPC memory + collection, obfuscated
    achievements: encBlob(computeAch()),  // unlocks, obfuscated
    settings: encBlob(gatherSettings()),  // difficulty, reading, display, language
  };
  const blob = new Blob([JSON.stringify(payload, null, 1)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "eight-save.json";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function importSave(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(reader.result);
      const loaded = decBlob(payload.memory);
      mem = Object.assign(blankMem(), loaded);   // decrypted only inside the game
      saveMem();
      if (payload.settings) {
        try { applyImportedSettings(decBlob(payload.settings)); } catch (e) {}
      }
      rebuildLangPicker();   // unlocked languages persist and reappear in the picker
      renderAchievements();
    } catch (e) { /* wrong file / wrong seed: ignore */ }
  };
  reader.readAsText(file);
}

function renderAchievements() {
  if (!el.achGrid) return;
  const state = computeAch();
  // "View credits" appears once any place has been escaped (the credits also
  // roll automatically the first time you escape each arc).
  if (el.creditsRow) {
    const anyWin = Object.values(mem.wins || {}).some((v) => v > 0);
    el.creditsRow.classList.toggle("hidden", !anyWin);
  }
  // Only earned achievements appear; the board fills in as they unlock, so a
  // new player is never shown a wall of padlocks or a count that spoils how many
  // there are. Kept in ACHS order (grouped), which reads as a natural sort.
  const earned = ACHS.filter((a) => state[a.id]);
  el.achGrid.innerHTML = "";
  if (!earned.length) {
    const empty = document.createElement("p");
    empty.className = "ach-empty";
    empty.textContent = ui["ach_empty"] || "Nothing yet. Escape a place to begin.";
    el.achGrid.appendChild(empty);
  }
  earned.forEach((a) => {
    const [name, desc] = achText(a.id);
    const tile = document.createElement("div");
    tile.className = "ach-tile on";
    tile.innerHTML = achIconSvg(a.id, true) +
      `<div class="ach-body">` +
      `<div class="ach-name">${name}</div>` +
      `<div class="ach-desc">${desc}</div></div>`;
    el.achGrid.appendChild(tile);
  });
  // Flashback collection: a dot per fragment, filled when seen. A seen dot is a
  // button that recaps its fragment's own words below the ledger.
  if (el.achFlash) {
    el.achFlash.innerHTML = "";
    ARC_IDS.forEach((arc) => {
      const total = flashCount(arc);
      if (!total) return;
      const seen = new Set(mem.flash[arc] || []);
      const row = document.createElement("div");
      row.className = "flash-row";
      row.dataset.skin = (ARCS_BY_ID[arc] || {}).skin || "hallway";
      const title = (ARCS_BY_ID[arc] || {}).title || arc;
      const dots = document.createElement("span");
      dots.className = "flash-dots";
      for (let i = 0; i < total; i++) {
        const got = seen.has(i);
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "flash-dot" + (got ? " on" : "");
        dot.disabled = !got;
        if (got) {
          dot.setAttribute("aria-label", (ui["col_recall"] || "Recall this fragment"));
          dot.addEventListener("click", () => recapFragment(arc, i, dot));
        }
        dots.appendChild(dot);
      }
      const arcLbl = document.createElement("span");
      arcLbl.className = "flash-arc"; arcLbl.textContent = title;
      const num = document.createElement("span");
      num.className = "flash-num"; num.textContent = `${seen.size}/${total}`;
      row.appendChild(arcLbl); row.appendChild(dots); row.appendChild(num);
      el.achFlash.appendChild(row);
    });
    // A single quiet line under the ledger where a tapped fragment surfaces.
    if (el.colRecap) el.colRecap.textContent = colRecapText || "";
  }
}
// The last fragment the player asked to recall, so a re-render keeps it shown.
let colRecapText = "";
function recapFragment(arc, idx, dot) {
  // Prefer the fragment in the CURRENT session language (from the localized arc
  // list), falling back to the text stored at collection time only if that is
  // unavailable (e.g. an old save loaded offline).
  const cur = ((ARCS_BY_ID[arc] || {}).flash_texts || [])[idx];
  const stored = ((mem.flashText && mem.flashText[arc]) || {})[idx];
  colRecapText = cur || stored || (ui["col_recall_empty"] ||
    "A fragment you have seen, its words already fading.");
  if (el.achFlash) el.achFlash.querySelectorAll(".flash-dot.recall")
    .forEach((d) => d.classList.remove("recall"));
  if (dot) dot.classList.add("recall");
  if (el.colRecap) {
    el.colRecap.textContent = colRecapText;
    el.colRecap.classList.remove("show");
    requestAnimationFrame(() => el.colRecap.classList.add("show"));
  }
}
function openAchievements() {
  if (!el.achievements) return;
  renderAchievements();
  el.achievements.classList.remove("hidden");
  if (el.achClose) el.achClose.focus();
}
function closeAchievements() { if (el.achievements) el.achievements.classList.add("hidden"); }
if (el.achOpen) el.achOpen.addEventListener("click", openAchievements);
if (el.achClose) el.achClose.addEventListener("click", closeAchievements);
if (el.achievements) {
  el.achievements.addEventListener("click", (e) => { if (e.target === el.achievements) closeAchievements(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el.achievements.classList.contains("hidden")) closeAchievements();
  });
}
if (el.achSave) el.achSave.addEventListener("click", exportSave);
if (el.achLoad) el.achLoad.addEventListener("click", () => el.achFile && el.achFile.click());
if (el.achFile) el.achFile.addEventListener("change", (e) => {
  const f = e.target.files && e.target.files[0];
  if (f) importSave(f);
  e.target.value = "";
});

// Erase: nuke the local memory (runs, achievements, recollections, records)
// back to a blank slate. Gated behind a deliberate, undoable-warning dialog.
// Display/language settings are preferences, not run-memory, so they are kept.
function eraseMemory() {
  try { localStorage.removeItem("h8_mem"); } catch (e) {}
  // The first-reset onboarding is part of what the place remembers of you, so a
  // wipe must forget it too: otherwise the instructions never return, and a
  // newly-blank player is never taught the rule on their first wrong call.
  try { localStorage.removeItem("h8_onboarded"); } catch (e) {}
  mem = blankMem();
  saveMem();
  renderAchievements();
}
const closeErase = () => { if (el.eraseConfirm) el.eraseConfirm.classList.add("hidden"); };
if (el.achErase) el.achErase.addEventListener("click", () => {
  if (el.eraseConfirm) el.eraseConfirm.classList.remove("hidden");
});
if (el.eraseCancel) el.eraseCancel.addEventListener("click", closeErase);
if (el.eraseOk) el.eraseOk.addEventListener("click", () => { eraseMemory(); closeErase(); });
if (el.eraseConfirm) {
  el.eraseConfirm.addEventListener("click", (e) => { if (e.target === el.eraseConfirm) closeErase(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el.eraseConfirm.classList.contains("hidden")) closeErase();
  });
}

// keep a lookup of arcs so "walk it again" can restart the same one
let ARCS_BY_ID = {};
(async function boot() {
  document.documentElement.lang = lang.split("_")[0];
  await initLangPicker();
  await applyUI();
  const { arcs } = await get("/api/arcs");
  ARCS_BY_ID = Object.fromEntries(arcs.map((a) => [a.id, a]));
  renderArcCards(arcs);
  el.body.dataset.skin = lastSkin();   // returning visitors keep their arc colour
  show(el.select);
  // Let the title "8" and the two lead lines stand alone for a beat, then fade
  // the ways through in. An early interaction reveals them at once.
  setTimeout(revealSelect, 1400);

  // Do NOT create the AudioContext at load. On mobile Chrome (and inside the
  // Spaces cross-origin iframe) a context constructed before any user gesture
  // can get stuck 'suspended' and a later resume() will not reliably start it,
  // which is why the landing/arc audio was silent on mobile. Instead the context
  // is created lazily INSIDE the first gesture (unlockAudio below), which mobile
  // Chrome requires, and the landing theme starts the instant it can be heard.

  // Unlock audio on the first real gesture. This is the load-bearing part for
  // mobile (and for the Spaces iframe): it must resume the context
  // SYNCHRONOUSLY inside the gesture, before any await, or iOS/Safari and mobile
  // Chrome will silently refuse to start audio. So it is registered in the
  // CAPTURE phase and is NOT {once:true}: every early gesture (including tapping
  // an arc, which then awaits a fetch before playing) gets a chance to unlock,
  // and the landing theme is rebuilt the moment we can actually hear it. The
  // handlers remove themselves once the context is running.
  const unlockEvents = ["pointerdown", "touchstart", "keydown"];
  const unlockAudio = () => {
    const a = window.ambience;
    if (!a) return;
    const wasSuspended = !a.ctx || a.ctx.state !== "running";
    a.unlock();
    // Rebuild the landing theme now that it can be heard, but only when we just
    // came out of a suspended state and are still on the select screen (so a tap
    // that is choosing an arc does not restart it).
    if (wasSuspended && el.select && !el.select.classList.contains("hidden")) {
      a.play("landing");
    }
    if (a.ctx && a.ctx.state === "running") {
      unlockEvents.forEach((ev) =>
        document.removeEventListener(ev, unlockAudio, true)
      );
    }
  };
  unlockEvents.forEach((ev) =>
    document.addEventListener(ev, unlockAudio, true)
  );

  // The very first interaction (any kind) reveals the ways, unless it is
  // choosing an arc (which leaves the landing straight away). Audio unlock is
  // handled separately above so this can stay a one-shot reveal.
  const firstGesture = (e) => {
    if (e.target.closest && e.target.closest(".arc-card")) return;
    revealSelect();
  };
  ["pointerdown", "keydown", "touchstart"].forEach((ev) =>
    document.addEventListener(ev, firstGesture, { once: true })
  );
})();
