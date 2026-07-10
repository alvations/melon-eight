#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Build the itch.io static bundle.

itch.io serves an HTML5 game as static files inside a sandboxed iframe: there is
no server there. To avoid maintaining a second, drift-prone JavaScript engine,
the itch build runs the SAME Flask engine in the browser via Pyodide (see
`static/itch-boot.js`). This script assembles the bundle:

    dist/itch/
      index.html          static page (Jinja rewritten to relative paths,
                          itch-boot.js injected before the game scripts)
      static/...          style.css, game.js, audio.js, itch-boot.js, img, i18n
                          (the live-synth audio needs no audio files, so the
                          static/audio/ renders are left out to stay lean)
      app.tar             the runtime Python + arc data + compiled i18n, which
                          itch-boot.js unpacks into Pyodide's filesystem
      UPLOAD.txt          how to upload to itch.io

    dist/hallway8-itch.zip   the whole thing, ready to drag into itch.io

The Python packed into app.tar is EXACTLY what the Flask server imports (app.py
imports these), so the itch build can never diverge from the server build:

    python scripts/build_itch.py            # -> dist/hallway8-itch.zip
    python scripts/build_itch.py /some/dir  # build into a chosen output dir

Optional build-time config (baked into index.html as live globals; left blank
they are emitted as commented, editable lines you can change without rebuilding):

    H8_ITCH_SHARE_URL=https://you.itch.io/eight \\
    H8_PYODIDE_VER=0.26.4 python scripts/build_itch.py
"""

import json
import os
import re
import shutil
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The runtime Python the server imports. app.py imports i18n/hallway/memory;
# hallway imports anomalies/i18n/memory. These are stdlib-only apart from Flask
# (installed in-browser by micropip), so Pyodide needs nothing else.
RUNTIME_PY = ["app.py", "hallway.py", "anomalies.py", "memory.py", "i18n.py"]

# Runtime data, resolved by the modules relative to their own __file__, so the
# tar must preserve this layout under /app.
DATA_DIRS = [
    os.path.join("data", "arcs"),
    os.path.join("data", "i18n", "compiled"),
]

# Static assets the client actually loads. The ambience is synthesised live in
# the browser (static/audio.js), so the exported static/audio/ renders are not
# needed at runtime and are skipped to keep the upload small.
STATIC_SKIP_DIRS = {"audio"}


def _config_block(share_url: str, pyodide_ver: str) -> str:
    """A small inline <script> that sets the itch build's optional globals BEFORE
    itch-boot.js runs. A share URL / Pyodide version passed at build time are
    emitted live; otherwise the lines are left commented for the owner to edit in
    place (no rebuild needed)."""
    share = (
        f'    window.H8_SHARE_URL = {json.dumps(share_url)};'
        if share_url else
        '    // window.H8_SHARE_URL = "https://YOURNAME.itch.io/eight";'
    )
    ver = (
        f'    window.H8_PYODIDE_VER = {json.dumps(pyodide_ver)};'
        if pyodide_ver else
        '    // window.H8_PYODIDE_VER = "0.26.4";  // bump to the current Pyodide '
        'and re-test in a browser'
    )
    return (
        "  <script>\n"
        "    /* itch.io build config. The share link defaults to the iframe URL; "
        "point it at your\n"
        "       itch page below. Pyodide version is overridable without a "
        "rebuild. */\n"
        f"{share}\n"
        f"{ver}\n"
        "  </script>\n"
    )


def _rewrite_index(html: str, share_url: str = "", pyodide_ver: str = "") -> str:
    """Turn the Flask/Jinja template into a standalone static page:
    - `{{ url_for('static', filename='X'[, _external=True]) }}` -> `static/X`
    - inject the config block then itch-boot.js in <head>, so the globals are set
      and the fetch shim is installed before the game scripts run.
    """
    def repl(m):
        return "static/" + m.group(1)

    html = re.sub(
        r"\{\{\s*url_for\(\s*'static'\s*,\s*filename='([^']+)'(?:\s*,\s*_external=True)?\s*\)\s*\}\}",
        repl,
        html,
    )
    if "{{" in html or "url_for" in html:
        leftover = [ln for ln in html.splitlines() if "{{" in ln or "url_for" in ln]
        raise SystemExit(
            "build_itch: unresolved template expression(s) in index.html:\n  "
            + "\n  ".join(leftover)
        )
    inject = _config_block(share_url, pyodide_ver) + \
        '  <script src="static/itch-boot.js"></script>\n'
    if "static/itch-boot.js" not in html:
        html = html.replace("</head>", inject + "</head>", 1)
    return html


def _copy_static(dst_static: str) -> None:
    src = os.path.join(ROOT, "static")
    os.makedirs(dst_static, exist_ok=True)
    for name in sorted(os.listdir(src)):
        s = os.path.join(src, name)
        if os.path.isdir(s):
            if name in STATIC_SKIP_DIRS:
                continue
            shutil.copytree(s, os.path.join(dst_static, name))
        else:
            shutil.copy2(s, os.path.join(dst_static, name))


def _build_app_tar(tar_path: str) -> list:
    """Pack the runtime Python + data into a tar, preserving the /app-relative
    layout the modules expect. Returns the member names for verification."""
    members = []
    with tarfile.open(tar_path, "w") as tar:
        for rel in RUNTIME_PY:
            src = os.path.join(ROOT, rel)
            if not os.path.exists(src):
                raise SystemExit(f"build_itch: missing runtime file {rel}")
            tar.add(src, arcname=rel)
            members.append(rel)
        for d in DATA_DIRS:
            base = os.path.join(ROOT, d)
            if not os.path.isdir(base):
                raise SystemExit(f"build_itch: missing data dir {d}")
            for fn in sorted(os.listdir(base)):
                if not fn.endswith(".json"):
                    continue
                rel = os.path.join(d, fn).replace(os.sep, "/")
                tar.add(os.path.join(base, fn), arcname=rel)
                members.append(rel)
    return members


UPLOAD_TXT = """\
8 -- itch.io upload

This folder is a self-contained HTML5 build. To publish it:

1. Zip the CONTENTS of this folder (index.html must be at the zip root), or use
   the ready-made dist/hallway8-itch.zip.
2. On itch.io: Create/Edit project -> Kind of project: HTML.
3. Upload the zip and tick "This file will be played in the browser."
4. Embed options -> Viewport dimensions: 1000 x 760 (it's a tall reading
   column, so height matters). Enable "Fullscreen button" and "Mobile friendly".
   1120 x 800 also works if you want it larger; wider just adds side margin
   since the text column is intentionally narrow.
5. Save & view.

Notes
- The game engine is the real Python server, run in your browser via Pyodide
  (loaded from a CDN on first play, then cached). First load pulls a few MB and
  takes a couple of seconds; the landing paints immediately while it settles.
- No data leaves the browser; there is no backend to run or pay for.
- Optional: to make the win-screen "share" link point at your itch page instead
  of the raw iframe URL, add this near the top of index.html's <head>:
      <script>window.H8_SHARE_URL = "https://YOURNAME.itch.io/eight";</script>
"""


def build(out_dir: str, share_url: str = "", pyodide_ver: str = "") -> str:
    """Assemble the itch bundle into out_dir. Returns the zip path.

    share_url / pyodide_ver (or the env vars H8_ITCH_SHARE_URL / H8_PYODIDE_VER)
    are baked into the generated index.html as live globals; left blank they are
    emitted as commented, editable lines instead.
    """
    share_url = share_url or os.environ.get("H8_ITCH_SHARE_URL", "")
    pyodide_ver = pyodide_ver or os.environ.get("H8_PYODIDE_VER", "")
    dst = out_dir
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)

    # index.html (static)
    with open(os.path.join(ROOT, "templates", "index.html"), encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(dst, "index.html"), "w", encoding="utf-8") as f:
        f.write(_rewrite_index(html, share_url, pyodide_ver))

    # static assets (minus the live-synth audio renders)
    _copy_static(os.path.join(dst, "static"))
    if not os.path.exists(os.path.join(dst, "static", "itch-boot.js")):
        raise SystemExit("build_itch: static/itch-boot.js is missing from the repo")

    # the engine + data, packed for Pyodide
    members = _build_app_tar(os.path.join(dst, "app.tar"))

    with open(os.path.join(dst, "UPLOAD.txt"), "w", encoding="utf-8") as f:
        f.write(UPLOAD_TXT)

    # zip it (index.html at the archive root, as itch expects)
    zip_base = os.path.join(os.path.dirname(dst), "hallway8-itch")
    if os.path.exists(zip_base + ".zip"):
        os.remove(zip_base + ".zip")
    shutil.make_archive(zip_base, "zip", root_dir=dst)

    print(f"itch bundle: {dst}")
    print(f"  app.tar: {len(members)} runtime files")
    print(f"  zip:     {zip_base}.zip")
    return zip_base + ".zip"


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist", "itch")
    build(out)


if __name__ == "__main__":
    main()
