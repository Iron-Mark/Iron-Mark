#!/usr/bin/env python3
"""HEAD-check external URLs in index files. Skip LinkedIn/TikTok bot blocks."""

from __future__ import annotations

import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "README.md",
    "public/STACK.md",
    "public/FAQ.md",
    "public/RECRUITER.md",
    "llms.txt",
    "public/llms-full.txt",
    "humans.txt",
    "sitemap.xml",
]

SKIP_SUBSTR = ("linkedin.com", "tiktok.com")
LOCAL_BLOB_PREFIX = "https://github.com/Iron-Mark/Iron-Mark/blob/main/"
PRE_PAGES_PREFIX = "https://iron-mark.github.io/Iron-Mark/"


def extract_urls() -> set[str]:
    urls: set[str] = set()
    for name in FILES:
        p = ROOT / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r'href="(https?://[^"]+)"|(?:^|\s|-\s)(https?://[^\s\"\'<>\)]+)', text):
            u = (m.group(1) or m.group(2)).rstrip(".,;")
            urls.add(u)
    return urls


def local_blob_ok(url: str) -> bool:
    if not url.startswith(LOCAL_BLOB_PREFIX):
        return False
    rel = url[len(LOCAL_BLOB_PREFIX) :].split("#", 1)[0]
    return (ROOT / rel).is_file()


def check(url: str) -> tuple[str, str]:
    if any(s in url for s in SKIP_SUBSTR):
        return url, "skip"
    if url.startswith(PRE_PAGES_PREFIX):
        return url, "prepages"
    if local_blob_ok(url):
        return url, "local"
    try:
        r = subprocess.run(
            ["curl", "-sI", "-L", "--max-time", "15", "-A", "LinkQA/1.0", url],
            capture_output=True,
            text=True,
            timeout=20,
        )
        status = 0
        for line in r.stdout.splitlines():
            if line.startswith("HTTP/"):
                status = int(line.split()[1])
        if 200 <= status < 400:
            return url, "ok"
        return url, f"fail:{status}"
    except Exception as e:
        return url, f"err:{e}"


def main() -> int:
    urls = sorted(extract_urls())
    issues: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(check, u): u for u in urls}
        for fut in as_completed(futs):
            url, status = fut.result()
            if status not in ("ok", "skip", "local", "prepages"):
                issues.append((url, status))

    print(f"link_qa: checked {len(urls)} urls, issues {len(issues)}")
    for url, status in sorted(issues):
        print(f"  {status} {url[:100]}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
