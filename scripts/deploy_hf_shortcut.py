#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Deploy a NON-CANONICAL *shortcut* build of the game for quick testing.

This is exactly the same game as `scripts/deploy_hf.py` ships, but the win is
reached in **3 stages instead of 8**, so you can get to the end screen (the
look-back line and the share block) in a few calls instead of a full run. It is
for testing only and must not be treated as the real game.

How it works: the goal is read from the `H8_GOAL` environment variable at
startup (see `hallway.py`, clamped to 1..8). This script uploads the repo to a
separate Space and sets that Space's `H8_GOAL` variable to 3. It also sets
`H8_ACT2_TEST=1`, which boosts the Act 2 triggers so the folds and the alternate
endings can actually be reached in a short test session (in the real game they
are rare by design). The code is identical; only the target and these env vars
differ.

Run from a machine with normal internet access (not the sandboxed web session,
whose network policy blocks huggingface.co):

    pip install "huggingface_hub>=0.24"
    export HF_TOKEN=hf_...                 # a *write* token
    python scripts/deploy_hf_shortcut.py   # -> alvations/hallway8-shortcut, 3 stages

Optionally pass a different target or stage count:
    python scripts/deploy_hf_shortcut.py owner/space-name 3

Locally you can get the same shortcut without deploying:
    H8_GOAL=3 python app.py
"""

import os
import secrets
import sys

from huggingface_hub import HfApi, get_token

REPO_ID = sys.argv[1] if len(sys.argv) > 1 else "alvations/hallway8-shortcut"
GOAL = sys.argv[2] if len(sys.argv) > 2 else "3"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    if REPO_ID.endswith("/hallway8"):
        sys.exit("Refusing to overwrite the canonical Space; pick a different id.")

    token = os.environ.get("HF_TOKEN") or get_token()
    if not token:
        sys.exit(
            "No token found. Run `hf auth login` or set HF_TOKEN to a write token."
        )

    api = HfApi(token=token)
    who = api.whoami()
    print(f"Authenticated as {who['name']}")
    print(f"SHORTCUT (non-canonical) build: {REPO_ID}, goal = {GOAL} stages")

    url = api.create_repo(
        repo_id=REPO_ID, repo_type="space", space_sdk="docker", exist_ok=True
    )
    print(f"Space ready: {url}")

    # The one thing that makes this a shortcut: fewer stages, via env var.
    try:
        api.add_space_variable(REPO_ID, "H8_GOAL", str(GOAL))
        print(f"H8_GOAL variable set to {GOAL}")
    except Exception as exc:
        sys.exit(f"Could not set H8_GOAL (shortcut would not apply): {exc}")

    # Boost the Act 2 triggers so the folds and the alternate endings can be
    # reached quickly for testing. This flag is NOT set on the real deploy.
    try:
        api.add_space_variable(REPO_ID, "H8_ACT2_TEST", "1")
        print("H8_ACT2_TEST variable set to 1 (Act 2 endings easy to reach)")
    except Exception as exc:
        print(f"Could not set H8_ACT2_TEST: {exc}")

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
        commit_message=f"Deploy shortcut test build ({GOAL} stages, non-canonical)",
        # Same lean upload as the canonical deploy: only the runtime game, not the
        # dev tool-chain, tests, docs, reviews, or the i18n source/audit.
        ignore_patterns=[
            ".git*", "**/__pycache__/**", "*.pyc", ".venv/**", "venv/**", ".env",
            "tests/**", "scripts/**", "package.json", "package-lock.json",
            "node_modules/**", "*.cjs", "docs/**", "CLAUDE.md", "llm-benchmark/**",
            "data/i18n/src/**", "data/i18n/lines.json", "data/i18n/levels.json",
            "static/audio/**", "shots/**", "video/**",
            "theme-out/**", "sfx-out/**", "audio-out/**", "*.webm",
        ],
    )
    print(f"\nDone -> https://huggingface.co/spaces/{REPO_ID}")
    print(f"Reaches the end screen in {GOAL} correct calls. Test-only build.")


if __name__ == "__main__":
    main()
