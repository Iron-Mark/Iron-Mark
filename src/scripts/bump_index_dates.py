#!/usr/bin/env python3
"""Bump updated date in llms-index.json and lastmod in sitemap.xml."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TODAY = date.today().isoformat()


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


def main() -> None:
    changed = bump_json() or bump_sitemap()
    print(f"date={TODAY} changed={changed}")


if __name__ == "__main__":
    main()
