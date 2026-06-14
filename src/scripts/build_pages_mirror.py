#!/usr/bin/env python3
"""Rewrite paths in docs/ after flattening public/ for GitHub Pages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

PAGES_BASE = "https://iron-mark.github.io/Iron-Mark"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
GITHUB_RAW = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main"

TEXT_SUFFIXES = {".md", ".txt", ".xml", ".html", ".jsonld", ".cff"}
SKIP_NAMES = {"index.html"}


def rewrite_github_public_urls(text: str) -> str:
    """Point GitHub blob/raw public/ URLs at the flat Pages mirror."""
    text = text.replace(f"{GITHUB_BLOB}/public/schema/", f"{PAGES_BASE}/schema/")
    text = text.replace(f"{GITHUB_BLOB}/public/", f"{PAGES_BASE}/")
    text = text.replace(f"{GITHUB_RAW}/public/schema/", f"{PAGES_BASE}/schema/")
    text = text.replace(f"{GITHUB_RAW}/public/", f"{PAGES_BASE}/")
    text = text.replace(f"{PAGES_BASE}/public/schema/", f"{PAGES_BASE}/schema/")
    text = text.replace(f"{PAGES_BASE}/public/", f"{PAGES_BASE}/")
    return text


def rewrite_relative_public_paths(text: str) -> str:
    """Strip public/ prefix from relative links and plain-text references."""
    text = text.replace("public/schema/", "schema/")
    text = re.sub(r"\((public/)", "(", text)
    text = re.sub(r'href="(public/)', 'href="', text)
    text = re.sub(
        r"(?<![/\w])public/([a-zA-Z0-9_.-]+\.(?:md|txt|cff|jsonld))",
        r"\1",
        text,
    )
    return text


def rewrite_repo_only_paths(text: str) -> str:
    """Send src/ and docs/ relative links to GitHub (not deployed on Pages)."""
    text = re.sub(r"\]\((src/[^)]+)\)", rf"]({GITHUB_BLOB}/\1)", text)
    text = re.sub(r'href="(src/[^"]+)"', rf'href="{GITHUB_BLOB}/\1"', text)
    text = re.sub(
        r"\]\((?:\.\./)?docs/([^)]+)\)",
        rf"]({GITHUB_BLOB}/docs/\1)",
        text,
    )
    return text


def rewrite_robots(text: str) -> str:
    return text.replace("Allow: /public/", "Allow: /")


def rewrite_llms_index(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    if data.get("contentRoot") == "public/":
        data["contentRoot"] = "./"
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def rewrite_file(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return False
    if path.suffix not in TEXT_SUFFIXES and path.name != "llms-index.json":
        return False

    original = path.read_text(encoding="utf-8")
    updated = original
    updated = rewrite_github_public_urls(updated)
    updated = rewrite_relative_public_paths(updated)
    updated = rewrite_repo_only_paths(updated)
    if path.name == "robots.txt":
        updated = rewrite_robots(updated)
    if path.name == "llms-index.json":
        updated = rewrite_llms_index(updated)

    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    if not DOCS.is_dir():
        print(f"error: {DOCS} not found — run after copying files into docs/", file=sys.stderr)
        return 1

    changed = 0
    for path in sorted(DOCS.rglob("*")):
        if not path.is_file():
            continue
        if rewrite_file(path):
            changed += 1
            print(f"rewrote {path.relative_to(DOCS)}")

    print(f"done — {changed} files rewritten for Pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
