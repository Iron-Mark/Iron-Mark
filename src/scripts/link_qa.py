#!/usr/bin/env python3
"""HEAD-check external URLs in index files. Skip LinkedIn/TikTok bot blocks."""

from __future__ import annotations

import argparse
import os
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
    "public/schema/llms-index.schema.json",
    "public/schema/person.jsonld",
    "public/schema/faq.jsonld",
    "humans.txt",
    "sitemap.xml",
    "docs/index.html",
]
LOCAL_LINK_FILES = [
    "README.md",
    "llms.txt",
    "public/README.md",
    "public/STACK.md",
    "public/FAQ.md",
    "public/RECRUITER.md",
    "public/PROOF.md",
    "public/HOW-TO-CITE.md",
    "public/PROFILE.md",
    "public/AGENTS.md",
    "public/schema/ENTITY.md",
    "docs/STRUCTURE.md",
    "docs/internal/LINK_QA.md",
]

SKIP_SUBSTR = ("linkedin.com", "tiktok.com")
LOCAL_BLOB_PREFIX = "https://github.com/Iron-Mark/Iron-Mark/blob/main/"
LOCAL_RAW_PREFIX = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/"
PRE_PAGES_PREFIX = "https://iron-mark.github.io/Iron-Mark/"
USER_AGENT = "Mozilla/5.0 (compatible; IronMarkLinkQA/1.0; +https://github.com/Iron-Mark/Iron-Mark)"


def curl_status(args: list[str]) -> int:
    r = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=20,
    )
    status = 0
    for line in r.stdout.splitlines():
        if line.startswith("HTTP/"):
            status = int(line.split()[1])
    if status == 0 and r.stdout.strip().isdigit():
        status = int(r.stdout.strip())
    return status


def extract_urls() -> set[str]:
    urls: set[str] = set()
    for name in FILES:
        p = ROOT / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r'href="(https?://[^"]+)"|(?:^|\s|-\s)(https?://[^\s\"\'<>\)`\]]+)', text):
            u = (m.group(1) or m.group(2)).rstrip(".,;`]")
            urls.add(u)
    return urls


def clean_local_target(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split()[0]
    return target.split("#", 1)[0]


def check_local_links() -> list[str]:
    issues: list[str] = []
    local_link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)|href=\"([^\"]+)\"|src=\"([^\"]+)\"|srcset=\"([^\"]+)\"")
    for name in LOCAL_LINK_FILES:
        p = ROOT / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for match in local_link_re.finditer(text):
            raw = next(group for group in match.groups() if group)
            if re.match(r"^(https?:|mailto:|#|data:)", raw, re.IGNORECASE):
                continue
            target = clean_local_target(raw)
            if not target or target.startswith("#"):
                continue
            resolved = (p.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                issues.append(f"{name}: local link escapes repo: {raw}")
                continue
            if not resolved.exists():
                issues.append(f"{name}: missing local link target: {raw}")
    return issues


def local_blob_ok(url: str) -> bool:
    prefix = ""
    if url.startswith(LOCAL_BLOB_PREFIX):
        prefix = LOCAL_BLOB_PREFIX
    elif url.startswith(LOCAL_RAW_PREFIX):
        prefix = LOCAL_RAW_PREFIX
    if not prefix:
        return False
    rel = url[len(prefix) :].split("#", 1)[0]
    return (ROOT / rel).is_file()


def check(url: str) -> tuple[str, str]:
    if any(s in url for s in SKIP_SUBSTR):
        return url, "skip"
    if url.startswith(PRE_PAGES_PREFIX):
        return url, "prepages"
    if local_blob_ok(url):
        return url, "local"
    try:
        status = curl_status(["curl", "-sI", "-L", "--max-time", "15", "-A", USER_AGENT, url])
        if status == 0:
            status = curl_status(
                [
                    "curl",
                    "-sL",
                    "--max-time",
                    "15",
                    "-A",
                    USER_AGENT,
                    "-o",
                    os.devnull,
                    "-w",
                    "%{http_code}",
                    url,
                ]
            )
        if 200 <= status < 400:
            return url, "ok"
        return url, f"fail:{status}"
    except Exception as e:
        return url, f"err:{e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local links and external URLs in public index files.")
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Only validate local relative links; skip external URL HEAD checks.",
    )
    args = parser.parse_args()

    local_issues = check_local_links()
    if args.local_only:
        print(f"link_qa: checked 0 urls, issues 0, local issues {len(local_issues)}")
        for issue in sorted(local_issues):
            print(f"  local {issue}")
        return 1 if local_issues else 0

    urls = sorted(extract_urls())
    issues: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(check, u): u for u in urls}
        for fut in as_completed(futs):
            url, status = fut.result()
            if status not in ("ok", "skip", "local", "prepages"):
                issues.append((url, status))

    print(f"link_qa: checked {len(urls)} urls, issues {len(issues)}, local issues {len(local_issues)}")
    for issue in sorted(local_issues):
        print(f"  local {issue}")
    for url, status in sorted(issues):
        print(f"  {status} {url[:100]}")
    return 1 if issues or local_issues else 0


if __name__ == "__main__":
    sys.exit(main())
