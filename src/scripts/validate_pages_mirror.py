#!/usr/bin/env python3
"""Build and validate the GitHub Pages mirror artifact in a temp directory."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
PUBLIC = ROOT / "public"
PAGES_BASE = "https://iron-mark.github.io/Iron-Mark"
PAGES_HOST = "iron-mark.github.io"

ROOT_FILES = ("llms.txt", "llms-index.json", "humans.txt", "robots.txt", "sitemap.xml")
PUBLIC_FILES = (
    "README.md",
    "FAQ.md",
    "RECRUITER.md",
    "PROOF.md",
    "PROFILE.md",
    "STACK.md",
    "HOW-TO-CITE.md",
    "LICENSE.md",
    "CITATION.cff",
    "llms-full.txt",
    "llms-ctx-full.txt",
)
REQUIRED_FILES = (
    "index.html",
    "README.md",
    "llms.txt",
    "llms-index.json",
    "llms-full.txt",
    "llms-ctx-full.txt",
    "FAQ.md",
    "RECRUITER.md",
    "PROOF.md",
    "STACK.md",
    "HOW-TO-CITE.md",
    "schema/llms-index.schema.json",
    "schema/person.jsonld",
    "schema/faq.jsonld",
    "robots.txt",
    "sitemap.xml",
)
FORBIDDEN_FILES = ("AGENTS.md",)
TEXT_SUFFIXES = {".md", ".txt", ".xml", ".html", ".json", ".jsonld", ".cff"}


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def build_temp_artifact() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="iron-mark-pages-"))
    artifact = temp_root / "docs"
    copy_tree(DOCS, artifact)

    for name in ROOT_FILES:
        shutil.copy2(ROOT / name, artifact / name)
    for name in PUBLIC_FILES:
        shutil.copy2(PUBLIC / name, artifact / name)
    copy_tree(ROOT / "assets", artifact / "assets")
    copy_tree(PUBLIC / "schema", artifact / "schema")

    sys.path.insert(0, str(ROOT / "src" / "scripts"))
    from build_pages_mirror import rewrite_file  # noqa: PLC0415

    for path in sorted(artifact.rglob("*")):
        if path.is_file():
            rewrite_file(path)
    return artifact


def extract_local_links(path: Path, text: str) -> list[str]:
    links: list[str] = []
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)|href=\"([^\"]+)\"|src=\"([^\"]+)\"|srcset=\"([^\"]+)\"")
    for match in link_re.finditer(text):
        raw = next(group for group in match.groups() if group)
        if re.match(r"^(https?:|mailto:|#|data:)", raw, re.IGNORECASE):
            continue
        target = raw.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split()[0].split("#", 1)[0]
        if target:
            links.append(target)
    return links


def validate_artifact(artifact: Path) -> list[str]:
    issues: list[str] = []
    for name in REQUIRED_FILES:
        if not (artifact / name).is_file():
            issues.append(f"missing Pages artifact file: {name}")
    for name in FORBIDDEN_FILES:
        if (artifact / name).exists():
            issues.append(f"forbidden production Pages artifact file: {name}")

    for json_name in ("llms-index.json", "schema/llms-index.schema.json", "schema/person.jsonld", "schema/faq.jsonld"):
        try:
            json.loads((artifact / json_name).read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(f"invalid JSON in Pages artifact {json_name}: {exc}")

    index_text = (artifact / "index.html").read_text(encoding="utf-8") if (artifact / "index.html").exists() else ""
    for needle in ("schema/llms-index.schema.json", "schema/person.jsonld", "schema/faq.jsonld", "llms-index.json"):
        if needle not in index_text:
            issues.append(f"Pages index missing reference: {needle}")

    index_data = json.loads((artifact / "llms-index.json").read_text(encoding="utf-8"))
    if index_data.get("contentRoot") != "./":
        issues.append("Pages llms-index.json contentRoot must be ./")
    machine_readable = index_data.get("machineReadable", {})
    repo = machine_readable.get("repo", {})
    pages = machine_readable.get("pages", {})
    if not str(repo.get("llmsIndexJson", "")).startswith("https://github.com/Iron-Mark/Iron-Mark/blob/main/"):
        issues.append("Pages llms-index.json must preserve machineReadable.repo source URLs")
    expected_pages = {
        "home": f"{PAGES_BASE}/",
        "llmsTxt": f"{PAGES_BASE}/llms.txt",
        "llmsFullTxt": f"{PAGES_BASE}/llms-full.txt",
        "llmsIndexJson": f"{PAGES_BASE}/llms-index.json",
        "llmsCtxFullTxt": f"{PAGES_BASE}/llms-ctx-full.txt",
        "faqMd": f"{PAGES_BASE}/FAQ.md",
        "recruiterMd": f"{PAGES_BASE}/RECRUITER.md",
        "proofMd": f"{PAGES_BASE}/PROOF.md",
        "stackMd": f"{PAGES_BASE}/STACK.md",
        "profileMd": f"{PAGES_BASE}/PROFILE.md",
        "readmeMd": f"{PAGES_BASE}/README.md",
        "howToCiteMd": f"{PAGES_BASE}/HOW-TO-CITE.md",
        "licenseMd": f"{PAGES_BASE}/LICENSE.md",
        "citationCff": f"{PAGES_BASE}/CITATION.cff",
        "schemaPerson": f"{PAGES_BASE}/schema/person.jsonld",
        "schemaFaq": f"{PAGES_BASE}/schema/faq.jsonld",
        "schemaIndex": f"{PAGES_BASE}/schema/llms-index.schema.json",
        "humansTxt": f"{PAGES_BASE}/humans.txt",
        "sitemap": f"{PAGES_BASE}/sitemap.xml",
        "robots": f"{PAGES_BASE}/robots.txt",
    }
    for key, expected in expected_pages.items():
        if pages.get(key) != expected:
            issues.append(f"Pages llms-index.json machineReadable.pages.{key} must be {expected}")

    robots_text = (artifact / "robots.txt").read_text(encoding="utf-8")
    if "Allow: /public/" in robots_text:
        issues.append("Pages robots.txt still references /public/")
    if f"Sitemap: {PAGES_BASE}/sitemap.xml" not in robots_text:
        issues.append("Pages robots.txt missing Pages sitemap directive")
    if "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/sitemap.xml" in robots_text:
        issues.append("Pages robots.txt must not point at the raw GitHub sitemap")

    sitemap_path = artifact / "sitemap.xml"
    try:
        sitemap = ET.parse(sitemap_path)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [loc.text or "" for loc in sitemap.findall(".//sm:loc", ns)]
    except Exception as exc:
        issues.append(f"invalid Pages sitemap.xml: {exc}")
        locs = []
    required_locs = {
        f"{PAGES_BASE}/",
        f"{PAGES_BASE}/llms.txt",
        f"{PAGES_BASE}/llms-index.json",
        f"{PAGES_BASE}/FAQ.md",
        f"{PAGES_BASE}/RECRUITER.md",
        f"{PAGES_BASE}/PROOF.md",
        f"{PAGES_BASE}/STACK.md",
        f"{PAGES_BASE}/PROFILE.md",
        f"{PAGES_BASE}/README.md",
        f"{PAGES_BASE}/HOW-TO-CITE.md",
        f"{PAGES_BASE}/LICENSE.md",
        f"{PAGES_BASE}/CITATION.cff",
        f"{PAGES_BASE}/schema/person.jsonld",
        f"{PAGES_BASE}/schema/faq.jsonld",
        f"{PAGES_BASE}/schema/llms-index.schema.json",
        f"{PAGES_BASE}/humans.txt",
        f"{PAGES_BASE}/robots.txt",
    }
    missing_locs = sorted(required_locs - set(locs))
    if missing_locs:
        issues.append(f"Pages sitemap missing required loc(s): {missing_locs}")
    for loc in locs:
        parsed = urlparse(loc)
        if parsed.netloc != PAGES_HOST or not parsed.path.startswith("/Iron-Mark/"):
            issues.append(f"Pages sitemap contains non-Pages URL: {loc}")

    for path in sorted(artifact.rglob("*")):
        if not path.is_file() or (path.suffix not in TEXT_SUFFIXES and path.name != "llms-index.json"):
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(artifact)
        for target in extract_local_links(path, text):
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(artifact)
            except ValueError:
                issues.append(f"{rel}: local link escapes Pages artifact: {target}")
                continue
            if not resolved.exists():
                issues.append(f"{rel}: missing Pages local link target: {target}")
    return issues


def main() -> int:
    artifact = build_temp_artifact()
    issues = validate_artifact(artifact)
    if issues:
        print(f"validate_pages_mirror.py: FAIL ({len(issues)} issue(s))")
        for issue in issues:
            print(f"  ERROR {issue}")
        return 1
    print(f"validate_pages_mirror.py: OK ({artifact})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
