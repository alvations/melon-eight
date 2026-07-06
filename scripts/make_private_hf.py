#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Toggle the visibility of the Hugging Face Space.

Keep it private until release, then flip it public on the day.

    pip install "huggingface_hub>=0.24"
    hf auth login            # or: export HF_TOKEN=hf_...  (write token)

    python scripts/make_private_hf.py            # make it PRIVATE (default)
    python scripts/make_private_hf.py --public   # make it PUBLIC (release day)

Optionally target a different space:
    python scripts/make_private_hf.py owner/space-name [--public]
"""

import os
import sys

from huggingface_hub import HfApi, get_token

args = [a for a in sys.argv[1:]]
make_public = "--public" in args
positional = [a for a in args if not a.startswith("-")]
REPO_ID = positional[0] if positional else "alvations/hallway8"
PRIVATE = not make_public


def main() -> None:
    token = os.environ.get("HF_TOKEN") or get_token()
    if not token:
        sys.exit("No token found. Run `hf auth login` or set HF_TOKEN.")

    api = HfApi(token=token)
    print(f"Authenticated as {api.whoami()['name']}")

    # update_repo_settings is the current API; fall back for older versions.
    try:
        api.update_repo_settings(repo_id=REPO_ID, repo_type="space", private=PRIVATE)
    except (AttributeError, TypeError):
        api.update_repo_visibility(repo_id=REPO_ID, repo_type="space", private=PRIVATE)

    state = "PRIVATE" if PRIVATE else "PUBLIC"
    print(f"{REPO_ID} is now {state}")
    print(f"https://huggingface.co/spaces/{REPO_ID}")


if __name__ == "__main__":
    main()
