# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Guards the itch.io static build so it stays in lock-step with the server.

itch.io has no backend: the itch build (scripts/build_itch.py) runs the SAME
Flask engine in the browser via Pyodide (static/itch-boot.js), dispatching /api/*
through Flask's test client. These tests prove three things without needing a
browser or network (the sandbox has neither for Pyodide):

  1. The bundle assembles and carries every runtime file the browser will need.
  2. index.html is a valid standalone page (no leftover Jinja; itch-boot.js is
     installed before the game scripts).
  3. Booting from ONLY app.tar's contents (the exact tree Pyodide unpacks) and
     driving app.test_client the way itch-boot.js's `h8_dispatch` does serves
     every endpoint game.js calls. If the server engine works, so does itch.
"""

import json
import os
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_itch  # noqa: E402
import deploy_hf  # noqa: E402


def _build():
    tmp = tempfile.mkdtemp(prefix="itch_build_")
    out = os.path.join(tmp, "itch")
    build_itch.build(out)
    return out


def test_bundle_has_page_shim_engine_and_assets():
    out = _build()
    for f in ["index.html", "app.tar", "UPLOAD.txt",
              "static/itch-boot.js", "static/game.js", "static/audio.js",
              "static/style.css", "static/i18n/en_US.json",
              "static/i18n/vi_VN.json", "static/img"]:
        assert os.path.exists(os.path.join(out, f)), f"itch bundle missing {f}"
    # the live-synth audio renders are not needed in the browser; keep it lean
    assert not os.path.isdir(os.path.join(out, "static/audio")), \
        "static/audio/ should not ship in the itch bundle (audio is synthesised)"


def test_index_is_standalone_and_loads_the_shim_first():
    out = _build()
    html = open(os.path.join(out, "index.html"), encoding="utf-8").read()
    assert "{{" not in html and "url_for" not in html, \
        "index.html still has unresolved Jinja"
    assert "static/itch-boot.js" in html, "itch-boot.js is not referenced"
    # The shim patches window.fetch, so it must load before the game scripts.
    assert html.index("static/itch-boot.js") < html.index("static/game.js"), \
        "itch-boot.js must be loaded before game.js"
    # The config globals must be set before the shim reads them, and by default
    # left as editable, commented lines (no live override baked in).
    assert "H8_SHARE_URL" in html and "H8_PYODIDE_VER" in html, \
        "config block missing from index.html"
    assert html.index("H8_SHARE_URL") < html.index("static/itch-boot.js"), \
        "config block must precede itch-boot.js"
    assert "// window.H8_SHARE_URL" in html, \
        "default build should leave the share URL commented/editable"


def test_build_time_share_url_is_baked_in_live():
    tmp = tempfile.mkdtemp(prefix="itch_share_")
    out = os.path.join(tmp, "itch")
    build_itch.build(out, share_url="https://melon.itch.io/eight")
    html = open(os.path.join(out, "index.html"), encoding="utf-8").read()
    assert 'window.H8_SHARE_URL = "https://melon.itch.io/eight";' in html, \
        "a build-time share URL should be emitted as a live global"
    assert html.index("H8_SHARE_URL") < html.index("static/itch-boot.js")


def test_app_tar_carries_the_exact_server_runtime():
    out = _build()
    with tarfile.open(os.path.join(out, "app.tar")) as tar:
        members = set(tar.getnames())
    for f in ["app.py", "hallway.py", "anomalies.py", "memory.py", "i18n.py"]:
        assert f in members, f"app.tar missing runtime module {f}"
    arcs = [m for m in members if m.startswith("data/arcs/") and m.endswith(".json")]
    compiled = [m for m in members if m.startswith("data/i18n/compiled/")]
    assert len(arcs) == 3, f"expected 3 arcs in app.tar, got {arcs}"
    assert len(compiled) == 21, f"expected 21 compiled catalogs, got {len(compiled)}"


def test_the_itch_bundle_never_leaks_into_the_hf_upload():
    # itch-boot.js and dist/ must be excluded from the HF/Docker upload so the
    # server build stays byte-for-byte what it was before the itch target.
    tmp = tempfile.mkdtemp(prefix="lean_for_itch_")
    kept = set(deploy_hf.build_lean_tree(tmp))
    assert "static/itch-boot.js" not in kept, \
        "itch-boot.js must not ship to the Flask server (it is browser-only)"
    assert not any(k.startswith("dist/") for k in kept), \
        "the dist/ build output must not ship to HF"


# The Python `h8_dispatch` in itch-boot.js, distilled: unpack app.tar, chdir into
# it, import app, and drive test_client for every endpoint game.js calls. Run in a
# fresh process (as Pyodide would), from ONLY the tar's contents.
_PROBE = r"""
import json, sys
import app
c = app.app.test_client()

def dispatch(path, method, headers, body):
    kw = {'method': method, 'headers': dict(headers)}
    if body is not None:
        kw['data'] = body
        kw['headers'].setdefault('Content-Type', 'application/json')
    r = c.open(path, **kw)
    return r.status_code, r.get_data(as_text=True)

def j(path, method='GET', headers=None, body=None):
    st, txt = dispatch(path, method, headers or {}, body)
    assert st == 200, (path, st, txt[:200])
    return json.loads(txt)

sid = 'itch-probe'
h = {'X-Sid': sid, 'X-Lang': 'vi_VN', 'X-Diff': 'normal'}

# the calls game.js makes, in order
assert 'langs' in j('/api/langs')
assert 'arcs' in j('/api/arcs', headers=h)
new = j('/api/new', 'POST', h, json.dumps({'arc': 'stairway8'}))
assert new.get('sid'), 'new must return a sid'
assert 'room' in new and 'meta' in new and 'intro' in new
j('/api/room', headers=h)
j('/api/inspect', 'POST', h, json.dumps({'prop': 'x'}))
j('/api/interact', 'POST', h, json.dumps({'prop': 'x'}))
act = j('/api/act', 'POST', h, json.dumps({'choice': 'continue', 'confidence': 3}))
assert 'correct' in act and 'won' in act, act
# the answer must never cross the wire, exactly as on the server
assert not any(k.startswith('_') for k in new['room']), 'answer key leaked to client'
print('ITCH DISPATCH OK')
"""


def test_pyodide_dispatch_serves_every_endpoint_from_app_tar():
    out = _build()
    work = tempfile.mkdtemp(prefix="itch_fs_")
    with tarfile.open(os.path.join(out, "app.tar")) as tar:
        tar.extractall(work)
    res = subprocess.run([sys.executable, "-c", _PROBE], cwd=work,
                         capture_output=True, text=True)
    assert res.returncode == 0 and "ITCH DISPATCH OK" in res.stdout, \
        f"in-browser dispatch would fail:\n{res.stderr or res.stdout}"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all itch tests passed")
