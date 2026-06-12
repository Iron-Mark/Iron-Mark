#!/usr/bin/env python3
"""Verify marksiazon.dev llms.txt links to GitHub profile index files."""

from __future__ import annotations

import sys
import urllib.request

PORTFOLIO_LLMS = "https://www.marksiazon.dev/llms.txt"
REQUIRED = [
    "Iron-Mark/Iron-Mark",
    "llms-index.json",
    "FAQ.md",
    "STACK.md",
    "github.com/Iron-Mark",
]
FAQ_OPTIONAL = [
    "FAQ & GitHub",
    "contact#faq",
    "#person",
]

def main() -> int:
    try:
        with urllib.request.urlopen(PORTFOLIO_LLMS, timeout=20) as r:
            body = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"FAIL: could not fetch {PORTFOLIO_LLMS}: {e}")
        print("Add portfolio-sync/marksiazon-dev-append.md to marksiazon.dev llms.txt")
        return 1

    missing = [s for s in REQUIRED if s not in body]
    if missing:
        print(f"FAIL: marksiazon.dev/llms.txt missing references: {missing}")
        print("See portfolio-sync/marksiazon-dev-append.md")
        return 1

    faq_missing = [s for s in FAQ_OPTIONAL if s not in body]
    if faq_missing:
        print(f"WARN: FAQ cross-links not yet in portfolio llms.txt: {faq_missing}")
        print("See portfolio-sync/faq-crosslinks.md")

    print(f"OK: {PORTFOLIO_LLMS} references GitHub profile index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
