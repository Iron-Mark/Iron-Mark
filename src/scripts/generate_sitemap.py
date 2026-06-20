#!/usr/bin/env python3
"""Generate the host-specific GitHub Pages sitemap."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pages_mirror import build_pages_sitemap

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "llms-index.json"
SITEMAP = ROOT / "sitemap.xml"


def index_lastmod() -> str:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    return str(data.get("updated", ""))


def main() -> None:
    SITEMAP.write_text(build_pages_sitemap(index_lastmod()), encoding="utf-8")
    print(f"Wrote {SITEMAP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
