#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Deploy this repo to a Hugging Face Docker Space.

Run from a machine with normal internet access (not the sandboxed web session,
whose network policy blocks huggingface.co):

    pip install "huggingface_hub>=0.24"
    export HF_TOKEN=hf_...          # a *write* token from hf.co/settings/tokens
    python scripts/deploy_hf.py     # defaults to alvations/hallway8

Optionally pass a different target: python scripts/deploy_hf.py owner/space-name
"""

import os
import secrets
import sys

from huggingface_hub import HfApi, get_token
from huggingface_hub.errors import HfHubHTTPError

REPO_ID = sys.argv[1] if len(sys.argv) > 1 else "alvations/hallway8"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The single source of truth for what the Space needs. Keep the Space lean: ship
# only what the running game needs (server modules, arc data, compiled i18n
# catalogs, templates, static, the Dockerfile, and the README Space card). GitHub
# keeps the dev tool-chain, tests, docs, reviews, and the i18n source/audit; the
# Space needs none of it at runtime. `tests/test_deploy.py` imports this exact
# list and boots the game from ONLY these files, so a change that would exclude a
# runtime-needed file (or otherwise break the Space) fails the suite, not prod.
IGNORE_PATTERNS = [
    # version control / caches / local env
    ".git*", "**/__pycache__/**", "*.pyc", ".venv/**", "venv/**", ".env",
    # dev tool-chain and tests (not used at runtime)
    "tests/**", "scripts/**", "package.json", "package-lock.json",
    "node_modules/**", "*.cjs",
    # the LLM benchmark harness (a dev/research tool, not the game runtime)
    "llm-benchmark/**",
    # docs, reviews, the agent brief, and other-host config (GitHub keeps these)
    "docs/**", "CLAUDE.md", "fly.toml",
    # itch.io build: the static bundle output and its browser-only Pyodide
    # bootstrap (the Flask server never loads itch-boot.js). Keeps the HF path
    # byte-for-byte untouched by the itch target.
    "dist/**", "static/itch-boot.js",
    # store/press art (itch cover + screenshots): uploaded to the itch page by
    # hand, not part of the running game.
    "press/**",
    # translation SOURCE + audit: the server loads only data/i18n/compiled/
    "data/i18n/src/**", "data/i18n/lines.json", "data/i18n/levels.json",
    # dev media/outputs (audio is synthesised live; no files needed)
    "static/audio/**", "shots/**", "video/**",
    "theme-out/**", "sfx-out/**", "audio-out/**", "*.webm",
]


def build_lean_tree(dst: str) -> list:
    """Copy exactly the files the Space would receive (ROOT minus IGNORE_PATTERNS)
    into `dst`, mirroring `upload_folder`'s selection. Returns the file list."""
    import shutil
    from huggingface_hub.utils import filter_repo_objects

    allf = []
    for dp, _, fns in os.walk(ROOT):
        if os.sep + ".git" in dp:
            continue
        for fn in fns:
            allf.append(os.path.relpath(os.path.join(dp, fn), ROOT).replace(os.sep, "/"))
    kept = list(filter_repo_objects(allf, ignore_patterns=IGNORE_PATTERNS))
    for rel in kept:
        d = os.path.join(dst, os.path.dirname(rel))
        os.makedirs(d, exist_ok=True)
        shutil.copy2(os.path.join(ROOT, rel), os.path.join(dst, rel))
    return kept


def _preflight() -> None:
    """Boot the game from ONLY the lean upload set and hit its endpoints. Raises
    SystemExit if the built Space would not run, so a broken deploy never ships."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        kept = build_lean_tree(tmp)
        need = ["app.py", "hallway.py", "anomalies.py", "memory.py", "i18n.py",
                "requirements.txt", "Dockerfile", "README.md",
                "templates/index.html", "static/game.js"]
        missing = [f for f in need if f not in kept]
        if missing:
            sys.exit(f"PREFLIGHT FAILED: runtime files excluded from the Space: {missing}")
        # Boot the app from the lean tree and exercise the core endpoints.
        probe = (
            "import app;c=app.app.test_client();"
            "r=c.get('/');assert r.status_code==200,('/',r.status_code);"
            "assert c.get('/api/arcs').status_code==200;"
            "assert c.get('/api/langs').status_code==200;"
            "n=c.post('/api/new',json={'arc':'hallway-eight'},headers={'X-Sid':'pf'});"
            "assert n.status_code==200,('new',n.status_code);"
            "a=c.post('/api/act',json={'choice':'continue','confidence':3},headers={'X-Sid':'pf'});"
            "assert a.status_code==200,('act',a.status_code);"
            "print('PREFLIGHT OK')"
        )
        res = subprocess.run([sys.executable, "-c", probe], cwd=tmp,
                             capture_output=True, text=True)
        if res.returncode != 0 or "PREFLIGHT OK" not in res.stdout:
            sys.exit("PREFLIGHT FAILED: the lean Space build does not run.\n"
                     + (res.stderr or res.stdout))
        print(f"Preflight OK: {len(kept)} files, game boots and serves from the lean set.")


def main() -> None:
    # Preflight FIRST: boot the game from only the lean upload set and hit its
    # endpoints, before any network call, so a broken build aborts instantly and
    # never touches the Space.
    _preflight()

    # Prefer an explicit HF_TOKEN, but fall back to a stored `hf auth login`
    # credential so this works without exporting anything.
    token = os.environ.get("HF_TOKEN") or get_token()
    if not token:
        sys.exit(
            "No token found. Run `hf auth login` or set HF_TOKEN to a write token."
        )

    api = HfApi(token=token)
    who = api.whoami()
    print(f"Authenticated as {who['name']}")

    try:
        url = api.create_repo(
            repo_id=REPO_ID, repo_type="space", space_sdk="docker", exist_ok=True
        )
    except HfHubHTTPError as exc:
        if getattr(exc.response, "status_code", None) == 402:
            sys.exit(
                "\nHugging Face now requires a PRO subscription to host Docker "
                "Spaces on free cpu-basic (HTTP 402 on create_repo). This game is a "
                "Flask backend (the loop's answer lives server-side), so it cannot "
                "be a free Static Space without moving the game logic into the "
                "browser and losing that anti-cheat property.\n\n"
                "Options:\n"
                "  1. Subscribe to HF PRO, then re-run this script unchanged: "
                "https://huggingface.co/pro\n"
                "  2. Host the SAME Docker image free elsewhere. The Dockerfile is "
                "portable; see docs/HOSTING.md for Fly.io / Render / Cloud Run "
                "(pin ONE instance, since game state is in-memory).\n"
                "  3. Ship a static, client-only build (loses the server-owns-the-"
                "answer design).\n"
            )
        raise
    print(f"Space ready: {url}")

    # Stable session key so in-progress runs survive Space restarts.
    try:
        api.add_space_secret(REPO_ID, "SECRET_KEY", secrets.token_hex(32))
        print("SECRET_KEY secret set")
    except Exception as exc:  # non-fatal
        print(f"Could not set SECRET_KEY (set it manually if you want): {exc}")

    api.upload_folder(
        folder_path=ROOT,
        repo_id=REPO_ID,
        repo_type="space",
        commit_message="Deploy Hallway 8 (multi-arc memory game)",
        ignore_patterns=IGNORE_PATTERNS,
    )
    print(f"\nDone → https://huggingface.co/spaces/{REPO_ID}")
    print("The Space will build the Docker image and go live in a couple of minutes.")


if __name__ == "__main__":
    main()
