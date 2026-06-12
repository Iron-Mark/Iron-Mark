#!/usr/bin/env python3
"""Validate llms-index.json consistency with README assets and project slugs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "llms-index.json"
README = ROOT / "README.md"

errors: list[str] = []
warnings: list[str] = []


def check_assets(slug: str) -> None:
    icon = ROOT / "assets" / "projects" / slug / "icon.png"
    if not icon.exists():
        errors.append(f"Missing icon: assets/projects/{slug}/icon.png")


def main() -> int:
    if not INDEX.exists():
        errors.append("llms-index.json not found")
        return 1

    data = json.loads(INDEX.read_text(encoding="utf-8"))
    readme = README.read_text(encoding="utf-8") if README.exists() else ""

    for p in data.get("featuredProjects", []):
        slug = p.get("slug", "")
        name = p.get("name", slug)
        check_assets(slug)
        cs = p.get("caseStudy", "")
        if cs and cs not in readme:
            warnings.append(f"{name}: case study URL not in README.md")
        if name not in readme:
            warnings.append(f"{name}: name not found in README.md")

    for key in ("updated", "entity", "featuredProjects", "aeo"):
        if key not in data:
            errors.append(f"llms-index.json missing key: {key}")

    snippets = data.get("aeo", {}).get("answerSnippets", [])
    if len(snippets) < 10:
        warnings.append(f"Only {len(snippets)} answerSnippets (recommend 10+)")

    for m in re.findall(r'src="(assets/[^"]+)"|srcset="(assets/[^"]+)"', readme):
        path = m[0] or m[1]
        if not (ROOT / path).exists():
            errors.append(f"README references missing asset: {path}")

    print("validate_index.py")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print("\nOK — no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
