# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Guards the Hugging Face Space deploy so a broken build can never ship.

The failure this catches: the deploy uploads only a LEAN subset of the repo
(`deploy_hf.IGNORE_PATTERNS`), so a change that excludes a runtime-needed file, or
a runtime import that isn't in requirements.txt, would run fine in the full repo
but crash the Space. These tests build the exact lean upload set and boot the game
from ONLY those files, the same way the Space does.
"""

import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import deploy_hf  # noqa: E402  (scripts/deploy_hf.py, the single source of truth)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lean_dir():
    tmp = tempfile.mkdtemp(prefix="lean_deploy_")
    deploy_hf.build_lean_tree(tmp)
    return tmp


def test_lean_deploy_ships_every_runtime_file():
    tmp = _lean_dir()
    need = [
        "app.py", "hallway.py", "anomalies.py", "memory.py", "i18n.py",
        "requirements.txt", "Dockerfile", "README.md",
        "templates/index.html", "static/style.css", "static/game.js",
        "static/audio.js",
    ]
    for f in need:
        assert os.path.exists(os.path.join(tmp, f)), f"lean deploy is missing {f}"
    # all three arcs, all 21 compiled catalogs, the client i18n + share art
    assert len([f for f in os.listdir(os.path.join(tmp, "data/arcs")) if f.endswith(".json")]) == 3
    assert len(os.listdir(os.path.join(tmp, "data/i18n/compiled"))) == 21
    assert os.path.isdir(os.path.join(tmp, "static/i18n"))
    assert os.path.isdir(os.path.join(tmp, "static/img"))


def test_lean_deploy_boots_and_serves():
    # Boot the app from ONLY the lean upload set (src/lines/levels/docs absent) and
    # exercise the core endpoints, exactly as the Space runs it.
    tmp = _lean_dir()
    probe = (
        "import app;c=app.app.test_client();"
        "assert c.get('/').status_code==200;"
        "assert c.get('/api/arcs').status_code==200;"
        "assert c.get('/api/langs').status_code==200;"
        "assert c.get('/static/game.js').status_code==200;"
        "assert c.get('/static/i18n/ja_JP.json').status_code==200;"
        "n=c.post('/api/new',json={'arc':'coach8'},headers={'X-Sid':'d','X-Lang':'ja_JP'});"
        "assert n.status_code==200,('new',n.status_code);"
        "a=c.post('/api/act',json={'choice':'continue','confidence':3},headers={'X-Sid':'d'});"
        "assert a.status_code==200,('act',a.status_code);"
        "print('OK')"
    )
    res = subprocess.run([sys.executable, "-c", probe], cwd=tmp,
                         capture_output=True, text=True)
    assert res.returncode == 0 and "OK" in res.stdout, \
        f"lean Space build does not run:\n{res.stderr or res.stdout}"


def test_runtime_imports_are_all_in_requirements():
    # A slim Docker image has only Flask + gunicorn (+ stdlib). A runtime import of
    # anything else runs locally but crashes the Space.
    import ast
    reqs = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read().lower()
    allowed = set(sys.stdlib_module_names) | {"flask", "gunicorn"}
    local = {"app", "hallway", "anomalies", "memory", "i18n"}
    for f in ["app.py", "hallway.py", "anomalies.py", "memory.py", "i18n.py"]:
        tree = ast.parse(open(os.path.join(ROOT, f), encoding="utf-8").read())
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [n.name.split(".")[0] for n in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            for m in mods:
                assert m in allowed or m in local or m in reqs, \
                    f"{f} imports '{m}' which is not stdlib/Flask nor in requirements.txt"


def test_space_card_matches_the_dockerfile_port():
    # The README front matter is the Space card. app_port must match the port the
    # Dockerfile actually serves, or the Space health-check never goes green.
    fm = re.match(r"^---\n(.*?)\n---\n", open(os.path.join(ROOT, "README.md"),
                  encoding="utf-8").read(), re.DOTALL)
    assert fm, "README has no Space-card front matter"
    body = fm.group(1)
    assert re.search(r"^sdk:\s*docker\s*$", body, re.MULTILINE), "sdk must be docker"
    m = re.search(r"^app_port:\s*(\d+)\s*$", body, re.MULTILINE)
    assert m, "app_port missing from the Space card"
    port = m.group(1)
    docker = open(os.path.join(ROOT, "Dockerfile"), encoding="utf-8").read()
    assert f"EXPOSE {port}" in docker, f"Dockerfile must EXPOSE {port}"
    assert f":{port}" in docker, f"Dockerfile CMD must bind :{port}"
