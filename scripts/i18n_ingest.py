#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Merge per-language translation files into the audit trail (lines.json).

Translators (here, the model) author one file per locale under
data/i18n/src/<locale>.json, mapping key -> {text, score, postedit,
postedit_score}. This merges them into data/i18n/lines.json under
lines[key][locale], preserving the audit shape and any revision history.

Re-running is idempotent; existing per-locale entries are overwritten by the
src file, and a `revisions` list keeps prior (text, score, postedit,
postedit_score) tuples so nothing is lost.
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n  # noqa: E402

LINES = os.path.join(i18n.I18N_DIR, "lines.json")
SRC_DIR = os.path.join(i18n.I18N_DIR, "src")

FIELDS = ("text", "score", "postedit", "postedit_score")


def main():
    lines = json.load(open(LINES, encoding="utf-8"))
    merged = 0
    # Flat per-locale files (src/<locale>.json) and per-arc ones
    # (src/<arc>/<locale>.json); locale is always the file's basename.
    paths = sorted(glob.glob(os.path.join(SRC_DIR, "*.json"))
                   + glob.glob(os.path.join(SRC_DIR, "*", "*.json")))
    for path in paths:
        loc = os.path.splitext(os.path.basename(path))[0]
        if not i18n.is_locale(loc):
            print(f"skip {path}: unknown locale")
            continue
        src = json.load(open(path, encoding="utf-8"))
        for key, val in src.items():
            if key not in lines:
                print(f"  warn: {loc} has unknown key {key!r} (skipped)")
                continue
            new = {f: val[f] for f in FIELDS if f in val}
            prev = lines[key].get(loc)
            if prev and prev != new:
                # keep the old version for audit
                revs = new.setdefault("revisions", prev.get("revisions", []))
                snapshot = {f: prev[f] for f in FIELDS if f in prev}
                if snapshot:
                    revs.append(snapshot)
            lines[key][loc] = new
            merged += 1
        print(f"{loc}: merged {len(src)} entries")

    with open(LINES, "w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"total merged: {merged}")


if __name__ == "__main__":
    main()
