#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
"""Compile the translation audit (data/i18n/lines.json) into runtime catalogs.

For each locale it emits:
  - data/i18n/compiled/<locale>.json   {key: final_text}   (server runtime)
  - static/i18n/<locale>.json          {ui_name: final_text} (client UI strings)

The "final" text is the post-edited string when present, else the first-pass
translation, else (missing) it is simply omitted so the runtime falls back to
English key by key. en_US is always emitted from source text.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n  # noqa: E402

LINES = os.path.join(i18n.I18N_DIR, "lines.json")
STATIC_I18N = os.path.join(i18n.HERE, "static", "i18n")


def final_text(entry: dict) -> str | None:
    """Prefer post-edited text, then first-pass, else None (fall back to en)."""
    if not isinstance(entry, dict):
        return None
    pe = entry.get("postedit")
    if isinstance(pe, str) and pe.strip():
        return pe
    tx = entry.get("text")
    if isinstance(tx, str) and tx.strip():
        return tx
    return None


def main():
    lines = json.load(open(LINES, encoding="utf-8"))
    os.makedirs(i18n.COMPILED_DIR, exist_ok=True)
    os.makedirs(STATIC_I18N, exist_ok=True)

    for loc in i18n.LOCALE_CODES:
        catalog = {}
        ui = {}
        for key, per_loc in lines.items():
            if loc == i18n.SOURCE_LOCALE:
                text = (per_loc.get("en_US") or {}).get("text")
            else:
                text = final_text(per_loc.get(loc))
            if text is None:
                continue
            catalog[key] = text
            if key.startswith("ui|"):
                ui[key[len("ui|"):]] = text

        with open(os.path.join(i18n.COMPILED_DIR, f"{loc}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=1, sort_keys=True)
        # UI catalog for the client: always fall back to English per-name.
        en_ui = {k[len("ui|"):]: v["text"] for k, v in
                 ((kk, lines[kk].get("en_US", {})) for kk in lines
                  if kk.startswith("ui|")) if v.get("text")}
        merged_ui = {**en_ui, **ui}
        with open(os.path.join(STATIC_I18N, f"{loc}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(merged_ui, f, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"{loc}: {len(catalog)} strings ({len(merged_ui)} ui)")

    i18n.clear_cache()


if __name__ == "__main__":
    main()
