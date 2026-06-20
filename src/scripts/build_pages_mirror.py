#!/usr/bin/env python3
"""Rewrite paths in docs/ after flattening public/ for GitHub Pages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
INDEX = ROOT / "llms-index.json"

PAGES_BASE = "https://iron-mark.github.io/Iron-Mark"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
GITHUB_RAW = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main"
PAGES_PRIMARY_IMAGE = f"{PAGES_BASE}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.webp"
PROJECT_COVER_EXTENSIONS = (".webp", ".png", ".svg")

TEXT_SUFFIXES = {".md", ".txt", ".xml", ".html", ".jsonld", ".cff"}
SKIP_NAMES = {"index.html"}
PAGES_SITEMAP_ENTRIES = (
    ("", "weekly", "0.9"),
    ("llms.txt", "weekly", "0.9"),
    ("llms-index.json", "weekly", "0.9"),
    ("llms-full.txt", "weekly", "0.85"),
    ("llms-ctx-full.txt", "weekly", "0.85"),
    ("FAQ.md", "monthly", "0.85"),
    ("RECRUITER.md", "monthly", "0.85"),
    ("PROOF.md", "monthly", "0.85"),
    ("STACK.md", "monthly", "0.8"),
    ("PROFILE.md", "monthly", "0.75"),
    ("README.md", "monthly", "0.75"),
    ("HOW-TO-CITE.md", "yearly", "0.7"),
    ("LICENSE.md", "yearly", "0.5"),
    ("CITATION.cff", "yearly", "0.5"),
    ("humans.txt", "monthly", "0.75"),
    ("robots.txt", "monthly", "0.55"),
    ("schema/person.jsonld", "monthly", "0.85"),
    ("schema/faq.jsonld", "monthly", "0.85"),
    ("schema/llms-index.schema.json", "monthly", "0.8"),
)


def project_cover_asset(slug: str) -> str | None:
    for suffix in PROJECT_COVER_EXTENSIONS:
        path = ROOT / "assets" / "projects" / slug / f"cover{suffix}"
        if path.exists():
            return f"assets/projects/{slug}/cover{suffix}"
    return None


def featured_project_cover_urls() -> list[str]:
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    urls: list[str] = []
    for project in data.get("featuredProjects", []):
        if not isinstance(project, dict):
            continue
        slug = str(project.get("slug", ""))
        asset = project_cover_asset(slug)
        if asset:
            urls.append(f"{PAGES_BASE}/{asset}")
    return urls


def rewrite_github_public_urls(text: str) -> str:
    """Point GitHub blob/raw public/ URLs at the flat Pages mirror."""
    text = text.replace(f"{GITHUB_BLOB}/public/schema/", f"{PAGES_BASE}/schema/")
    text = text.replace(f"{GITHUB_BLOB}/public/", f"{PAGES_BASE}/")
    text = text.replace(f"{GITHUB_RAW}/public/schema/", f"{PAGES_BASE}/schema/")
    text = text.replace(f"{GITHUB_RAW}/public/", f"{PAGES_BASE}/")
    text = text.replace(f"{PAGES_BASE}/public/schema/", f"{PAGES_BASE}/schema/")
    text = text.replace(f"{PAGES_BASE}/public/", f"{PAGES_BASE}/")
    return text


def rewrite_relative_public_paths(text: str, path: Path) -> str:
    """Strip public/ prefix from relative links and plain-text references."""
    text = text.replace("public/schema/", "schema/")
    text = text.replace("../assets/", "assets/")
    if path.parent.name != "schema":
        for root_name in ("llms.txt", "llms-index.json", "robots.txt", "sitemap.xml", "humans.txt"):
            text = text.replace(f"../{root_name}", root_name)
        text = text.replace("../README.md", f"{GITHUB_BLOB}/README.md")
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
    text = re.sub(r"\]\(\.\./(src/[^)]+)\)", rf"]({GITHUB_BLOB}/\1)", text)
    text = re.sub(r'href="(src/[^"]+)"', rf'href="{GITHUB_BLOB}/\1"', text)
    text = re.sub(r'href="\.\./(src/[^"]+)"', rf'href="{GITHUB_BLOB}/\1"', text)
    text = re.sub(
        r"\]\((?:\.\./)?docs/([^)]+)\)",
        rf"]({GITHUB_BLOB}/docs/\1)",
        text,
    )
    return text


def rewrite_robots(text: str) -> str:
    text = text.replace("Allow: /public/", "Allow: /")
    text = re.sub(
        rf"^Sitemap:\s+{re.escape(GITHUB_RAW)}/sitemap\.xml\s*$\n?",
        "",
        text,
        flags=re.MULTILINE,
    )
    return text


def build_pages_sitemap(lastmod: str) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for path, changefreq, priority in PAGES_SITEMAP_ENTRIES:
        loc = f"{PAGES_BASE}/{path}" if path else f"{PAGES_BASE}/"
        lines.extend(
            [
                "  <url>",
                f"    <loc>{loc}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                f"    <changefreq>{changefreq}</changefreq>",
                f"    <priority>{priority}</priority>",
            ]
        )
        if not path:
            lines.extend(
                [
                    "    <image:image>",
                    f"      <image:loc>{escape(PAGES_PRIMARY_IMAGE)}</image:loc>",
                    "    </image:image>",
                ]
            )
        if path == "README.md":
            for image_url in featured_project_cover_urls():
                lines.extend(
                    [
                        "    <image:image>",
                        f"      <image:loc>{escape(image_url)}</image:loc>",
                        "    </image:image>",
                    ]
                )
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def rewrite_sitemap(text: str) -> str:
    match = re.search(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", text)
    return build_pages_sitemap(match.group(1) if match else "")


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
    if path.name == "llms-index.json":
        updated = rewrite_llms_index(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            return True
        return False

    updated = original
    updated = rewrite_github_public_urls(updated)
    updated = rewrite_relative_public_paths(updated, path)
    updated = rewrite_repo_only_paths(updated)
    if path.name == "robots.txt":
        updated = rewrite_robots(updated)
    if path.name == "sitemap.xml":
        updated = rewrite_sitemap(updated)

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
