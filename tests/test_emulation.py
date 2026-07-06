# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Browser emulation test: drives the real client in headless Chromium.

Unit tests cover the server's math and payloads; this covers the *client*
rendering that only a browser exercises: reduced-motion rendering, Act 2 touch
verbs and the flavour line, the inspect aside, and the alternate-ending
achievement gate. The assertions live in ``tests/emulation.cjs`` (Playwright);
this wrapper boots the app on a free port and runs them.

It is **opt-in and skips gracefully**: it does nothing unless ``H8_EMU=1`` is
set and Node + Playwright + Chromium are present, so the fast default suite
(``python tests/test_game.py``) and browserless CI stay green. Run the full
thing with::

    H8_EMU=1 python tests/test_game.py
"""

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "tests", "emulation.cjs")
# The harness (tests/emulation.cjs via scripts/browser.cjs) resolves Playwright
# and Chromium portably: a plain checkout works after
# ``npm install && npx playwright install chromium``. These envs only steer the
# sandbox; on a normal machine they are unset and the harness picks its own.
CHROMIUM = os.environ.get("H8_CHROMIUM", "")
NODE_PATH = os.environ.get("NODE_PATH", "")


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_up(url, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def _skip(reason):
    print(f"    (skip test_emulation: {reason})")


def test_emulation():
    if os.environ.get("H8_EMU") not in ("1", "true", "yes"):
        return _skip("set H8_EMU=1 to run the browser emulation checks")
    node = shutil.which("node")
    if not node:
        return _skip("node not found")
    # Do not hard-require a specific Chromium/Playwright path here: the harness
    # resolves them itself and exits 2 when the environment is unavailable, which
    # we treat as a skip below. That keeps this portable across a plain checkout
    # and the sandbox.

    port = _free_port()
    env = dict(os.environ, PORT=str(port), HOST="127.0.0.1")
    if NODE_PATH:
        env["NODE_PATH"] = NODE_PATH
    app = subprocess.Popen([sys.executable, os.path.join(ROOT, "app.py")],
                           cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = f"http://127.0.0.1:{port}"
        assert _wait_up(url), "app did not start"
        # Pass an explicit Chromium path only if one was given; otherwise let the
        # harness use Playwright's own installed Chromium.
        cmd = [node, HARNESS, url] + ([CHROMIUM] if CHROMIUM else [])
        proc = subprocess.run(
            cmd, cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=300)
        sys.stdout.write(proc.stdout)
        if proc.returncode == 2:
            return _skip("harness reported environment unavailable")
        assert proc.returncode == 0, (
            "emulation checks failed:\n" + proc.stdout + proc.stderr)
    finally:
        app.terminate()
        try:
            app.wait(timeout=5)
        except Exception:
            app.kill()
