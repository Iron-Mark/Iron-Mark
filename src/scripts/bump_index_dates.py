#!/usr/bin/env python3
"""Bump public freshness dates for the production-facing index files."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Manila")
TODAY = datetime.now(PROJECT_TIMEZONE).date().isoformat()
LAST_UPDATED_DOCS = (
    ROOT / "public/FAQ.md",
    ROOT / "public/llms-full.txt",
    ROOT / "public/RECRUITER.md",
    ROOT / "public/PROFILE.md",
    ROOT / "public/PROOF.md",
    ROOT / "llms.txt",
)


def bump_json() -> bool:
    path = ROOT / "llms-index.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("updated") == TODAY:
        return False
    data["updated"] = TODAY
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def bump_sitemap() -> bool:
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    new = re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", f"<lastmod>{TODAY}</lastmod>", text)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def bump_robots() -> bool:
    path = ROOT / "robots.txt"
    text = path.read_text(encoding="utf-8")
    new = re.sub(r"# Last updated: \d{4}-\d{2}-\d{2}", f"# Last updated: {TODAY}", text)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def bump_last_updated(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    new = re.sub(r"Last updated: \d{4}-\d{2}-\d{2}", f"Last updated: {TODAY}", text, count=1)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def main() -> None:
    changed = any(
        (
            bump_json(),
            bump_sitemap(),
            bump_robots(),
            *(bump_last_updated(path) for path in LAST_UPDATED_DOCS),
        )
    )
    print(f"date={TODAY} changed={changed}")


if __name__ == "__main__":
    main()
