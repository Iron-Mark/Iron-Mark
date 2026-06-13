#!/usr/bin/env python3
"""One-time path reference updater after public/ + src/ reorganization."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Order matters — longer / specific paths first
REPLACEMENTS = [
    ("blob/main/public/schema/", "blob/main/public/schema/"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/schema/", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/schema/"),
    ("blob/main/src/mcp-server/", "blob/main/src/mcp-server/"),
    ("blob/main/src/scripts/", "blob/main/src/scripts/"),
    ("blob/main/src/portfolio-sync/", "blob/main/src/portfolio-sync/"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/src/mcp-server/", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/src/mcp-server/"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/src/scripts/", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/src/scripts/"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/src/portfolio-sync/", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/src/portfolio-sync/"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/llms-ctx-full.txt", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/llms-ctx-full.txt"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/llms-full.txt", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/llms-full.txt"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/FAQ.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/FAQ.md"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/RECRUITER.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/RECRUITER.md"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/PROOF.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/PROOF.md"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/AGENTS.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/AGENTS.md"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/STACK.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/STACK.md"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/PROFILE.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/PROFILE.md"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/HOW-TO-CITE.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/HOW-TO-CITE.md"),
    ("raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/LICENSE.md", "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/LICENSE.md"),
    ("blob/main/public/llms-ctx-full.txt", "blob/main/public/llms-ctx-full.txt"),
    ("blob/main/public/llms-full.txt", "blob/main/public/llms-full.txt"),
    ("blob/main/public/FAQ.md", "blob/main/public/FAQ.md"),
    ("blob/main/public/RECRUITER.md", "blob/main/public/RECRUITER.md"),
    ("blob/main/public/PROOF.md", "blob/main/public/PROOF.md"),
    ("blob/main/public/AGENTS.md", "blob/main/public/AGENTS.md"),
    ("blob/main/public/STACK.md", "blob/main/public/STACK.md"),
    ("blob/main/public/PROFILE.md", "blob/main/public/PROFILE.md"),
    ("blob/main/public/HOW-TO-CITE.md", "blob/main/public/HOW-TO-CITE.md"),
    ("blob/main/public/LICENSE.md", "blob/main/public/LICENSE.md"),
    ("iron-mark.github.io/Iron-Mark/public/llms-full.txt", "iron-mark.github.io/Iron-Mark/public/llms-full.txt"),
    ("iron-mark.github.io/Iron-Mark/public/llms-ctx-full.txt", "iron-mark.github.io/Iron-Mark/public/llms-ctx-full.txt"),
    ("iron-mark.github.io/Iron-Mark/public/FAQ.md", "iron-mark.github.io/Iron-Mark/public/FAQ.md"),
    ("iron-mark.github.io/Iron-Mark/public/schema/", "iron-mark.github.io/Iron-Mark/public/schema/"),
    ("src/portfolio-sync/", "src/portfolio-sync/"),
    ("python3 src/scripts/", "python3 src/scripts/"),
    ("src/scripts/validate_index.py", "src/scripts/validate_index.py"),
    ("src/scripts/generate_llms_ctx.py", "src/scripts/generate_llms_ctx.py"),
    ("src/scripts/link_qa.py", "src/scripts/link_qa.py"),
    ("src/scripts/test_mcp_server.py", "src/scripts/test_mcp_server.py"),
    ("src/scripts/check_portfolio_mirror.py", "src/scripts/check_portfolio_mirror.py"),
    ("src/scripts/bump_index_dates.py", "src/scripts/bump_index_dates.py"),
    ("pip install -e src/mcp-server/", "pip install -e src/mcp-server/"),
    ("src/mcp-server/mcp-config", "src/mcp-server/mcp-config"),
    ("src/mcp-server/README.md", "src/mcp-server/README.md"),
    ("[FAQ.md](public/FAQ.md)", "[FAQ.md](public/FAQ.md)"),
    ("[RECRUITER.md](public/RECRUITER.md)", "[RECRUITER.md](public/RECRUITER.md)"),
    ("[PROOF.md](public/PROOF.md)", "[PROOF.md](public/PROOF.md)"),
    ("[AGENTS.md](public/AGENTS.md)", "[AGENTS.md](public/AGENTS.md)"),
    ("[STACK.md](public/STACK.md)", "[STACK.md](public/STACK.md)"),
    ("[PROFILE.md](public/PROFILE.md)", "[PROFILE.md](public/PROFILE.md)"),
    ("[HOW-TO-CITE.md](public/HOW-TO-CITE.md)", "[HOW-TO-CITE.md](public/HOW-TO-CITE.md)"),
    ("[LICENSE.md](public/LICENSE.md)", "[LICENSE.md](public/LICENSE.md)"),
    ("[llms-full.txt](public/llms-full.txt)", "[llms-full.txt](public/llms-full.txt)"),
    ("[llms-ctx-full.txt](public/llms-ctx-full.txt)", "[llms-ctx-full.txt](public/llms-ctx-full.txt)"),
    ("[person.jsonld](public/schema/person.jsonld)", "[person.jsonld](public/schema/person.jsonld)"),
    ('href="public/FAQ.md"', 'href="public/FAQ.md"'),
    ('href="public/RECRUITER.md"', 'href="public/RECRUITER.md"'),
    ('href="public/STACK.md"', 'href="public/STACK.md"'),
    ('href="public/llms-ctx-full.txt"', 'href="public/llms-ctx-full.txt"'),
    ('href="public/llms-full.txt"', 'href="public/llms-full.txt"'),
    ('href="public/PROOF.md"', 'href="public/PROOF.md"'),
    ('href="public/AGENTS.md"', 'href="public/AGENTS.md"'),
    ('href="public/LICENSE.md"', 'href="public/LICENSE.md"'),
    ('href="src/mcp-server/README.md"', 'href="src/mcp-server/README.md"'),
    ("Full stack ({data.get('stackReference', {}).get('toolCount', '?')} tools): public/STACK.md", "Full stack ({data.get('stackReference', {}).get('toolCount', '?')} tools): public/STACK.md"),
]

SKIP = {".git", "assets", "docs/index.html"}


def should_process(path: Path) -> bool:
    if any(part in SKIP for part in path.parts):
        return False
    if path.suffix not in {".md", ".txt", ".json", ".xml", ".yml", ".yaml", ".py", ".cff", ".html", ".jsonld"}:
        return False
    return True


def main() -> None:
    changed = 0
    for path in REPO.rglob("*"):
        if not path.is_file() or not should_process(path):
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            changed += 1
            print(f"updated {path.relative_to(REPO)}")
    print(f"done — {changed} files")


if __name__ == "__main__":
    main()
