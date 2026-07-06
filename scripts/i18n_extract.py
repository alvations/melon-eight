#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Seed / refresh the translation audit file with the English source strings.

Walks every arc (via i18n.arc_items) plus the UI strings and writes their keys
and English text into data/i18n/lines.json, the audit trail. Existing
translations are preserved; only the en_US source text is (re)written, so this
is safe to re-run whenever the English content changes.

Audit shape (exactly as requested):

    {
      "<key>": {
        "en_US": {"text": "..."},
        "de_DE": {"text": "...", "score": 92, "postedit": "...", "postedit_score": 96},
        ...
      },
      ...
    }
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n  # noqa: E402

ARCS_DIR = os.path.join(i18n.HERE, "data", "arcs")
LINES = os.path.join(i18n.I18N_DIR, "lines.json")


def source_items():
    """Yield (key, english_text) for all translatable strings."""
    for path in sorted(glob.glob(os.path.join(ARCS_DIR, "*.json"))):
        # skip already-localized arc copies, if any ever exist
        base = os.path.basename(path)
        if base.count(".") > 1:
            continue
        data = json.load(open(path, encoding="utf-8"))
        arc_id = data.get("meta", {}).get("id")
        if not arc_id:
            continue
        for key, text in i18n.arc_items(arc_id, data):
            yield key, text
    for key, text in i18n.ui_items():
        yield key, text


def main():
    os.makedirs(i18n.I18N_DIR, exist_ok=True)
    lines = {}
    if os.path.exists(LINES):
        lines = json.load(open(LINES, encoding="utf-8"))

    n = 0
    for key, text in source_items():
        entry = lines.setdefault(key, {})
        entry["en_US"] = {"text": text}
        n += 1

    with open(LINES, "w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"wrote {LINES} with {n} source keys ({len(lines)} total)")


if __name__ == "__main__":
    main()
