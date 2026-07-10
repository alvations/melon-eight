#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Build BOTH deploy targets from the one engine, every time.

    python scripts/build_all.py

8 ships to two places from a single Python engine:

  * Hugging Face (or any Docker host): the Flask server, uploaded by
    `scripts/deploy_hf.py`. Here we run that script's PREFLIGHT, which boots the
    game from only the lean upload set and hits every endpoint, so a build that
    would not run never ships.

  * itch.io: a static HTML5 bundle that runs the SAME Flask engine in the
    browser via Pyodide, assembled by `scripts/build_itch.py` into
    dist/hallway8-itch.zip.

Because the itch bundle packs the exact runtime the server imports (app.py and
friends), the two targets cannot drift apart: this script validates the server
path and produces the itch artifact in one shot, so "every build" always means
both. Neither step needs network or credentials; the actual HF upload (which
does) stays in deploy_hf.py.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

import build_itch  # noqa: E402
import deploy_hf  # noqa: E402


def main() -> None:
    print("== 1/2  HF / Docker target: preflight the lean server build ==")
    deploy_hf._preflight()  # boots the lean upload set, hits every endpoint

    print("\n== 2/2  itch.io target: build the static Pyodide bundle ==")
    zip_path = build_itch.build(os.path.join(ROOT, "dist", "itch"))

    print("\nBoth targets built from one engine.")
    print("  HF / Docker : verified bootable; ship with  python scripts/deploy_hf.py")
    print(f"  itch.io     : {os.path.relpath(zip_path, ROOT)}  (drag into an HTML project)")


if __name__ == "__main__":
    main()
