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

REPO_ID = sys.argv[1] if len(sys.argv) > 1 else "alvations/hallway8"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
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

    url = api.create_repo(
        repo_id=REPO_ID, repo_type="space", space_sdk="docker", exist_ok=True
    )
    print(f"Space ready: {url}")

    # Stable session key so in-progress runs survive Space restarts.
    try:
        api.add_space_secret(REPO_ID, "SECRET_KEY", secrets.token_hex(32))
        print("SECRET_KEY secret set")
    except Exception as exc:  # non-fatal
        print(f"Could not set SECRET_KEY (set it manually if you want): {exc}")

    # Keep the Space lean: upload only what the running game needs (the server
    # modules, the arc data, the compiled i18n catalogs, templates, static, the
    # Dockerfile, and the README Space card). The full repo on GitHub keeps the
    # dev tool-chain, tests, docs, reviews, and the translation source/audit; the
    # Space does not need any of it at runtime, and skipping it (~11 MB of i18n
    # source/audit alone) makes builds smaller and faster.
    api.upload_folder(
        folder_path=ROOT,
        repo_id=REPO_ID,
        repo_type="space",
        commit_message="Deploy Hallway 8 (multi-arc memory game)",
        ignore_patterns=[
            # version control / caches / local env
            ".git*", "**/__pycache__/**", "*.pyc", ".venv/**", "venv/**", ".env",
            # dev tool-chain and tests (not used at runtime)
            "tests/**", "scripts/**", "package.json", "package-lock.json",
            "node_modules/**", "*.cjs",
            # docs, reviews, and the agent brief (GitHub keeps these)
            "docs/**", "CLAUDE.md",
            # translation SOURCE + audit: the server loads only data/i18n/compiled/
            "data/i18n/src/**", "data/i18n/lines.json", "data/i18n/levels.json",
            # dev media/outputs (audio is synthesised live; no files needed)
            "static/audio/**", "shots/**", "video/**",
            "theme-out/**", "sfx-out/**", "audio-out/**", "*.webm",
        ],
    )
    print(f"\nDone → https://huggingface.co/spaces/{REPO_ID}")
    print("The Space will build the Docker image and go live in a couple of minutes.")


if __name__ == "__main__":
    main()
