#!/usr/bin/env python3
"""Verify marksiazon.dev llms.txt links to GitHub profile index files."""

from __future__ import annotations

import sys
import time
import urllib.request

PORTFOLIO_LLMS = "https://www.marksiazon.dev/llms.txt"
FETCH_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (2, 4)
USER_AGENT = "Mozilla/5.0 (compatible; IronMarkMirrorQA/1.0; +https://github.com/Iron-Mark/Iron-Mark)"
REQUIRED = [
    "Iron-Mark/Iron-Mark",
    "llms-index.json",
    "llms-index.schema.json",
    "FAQ.md",
    "STACK.md",
    "github.com/Iron-Mark",
    "iron-mark.github.io",
    "FAQ & GitHub",
    "contact#faq",
    "#mark-siazon",
    "person.jsonld",
    "faq.jsonld",
]


def fetch_portfolio_llms() -> str:
    request = urllib.request.Request(PORTFOLIO_LLMS, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001 - retry all fixed-URL transport failures
            if attempt == FETCH_ATTEMPTS:
                raise
            delay = RETRY_DELAYS_SECONDS[attempt - 1]
            print(
                f"WARN: portfolio mirror fetch attempt {attempt}/{FETCH_ATTEMPTS} failed; "
                f"retrying in {delay}s: {error}"
            )
            time.sleep(delay)

    raise RuntimeError("portfolio mirror retry loop exited unexpectedly")


def main() -> int:
    try:
        body = fetch_portfolio_llms()
    except Exception as error:
        print(f"FAIL: could not fetch {PORTFOLIO_LLMS} after {FETCH_ATTEMPTS} attempts: {error}")
        print("Add src/portfolio-sync/marksiazon-dev-llms-snippet.md to marksiazon.dev llms.txt")
        return 1

    missing = [s for s in REQUIRED if s not in body]
    if missing:
        print(f"FAIL: marksiazon.dev/llms.txt missing references: {missing}")
        print("See src/portfolio-sync/marksiazon-dev-llms-snippet.md")
        return 1

    print(f"OK: {PORTFOLIO_LLMS} references GitHub profile index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
