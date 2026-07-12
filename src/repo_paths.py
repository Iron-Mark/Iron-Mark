"""Shared repo layout paths (root · public · src)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = REPO_ROOT / "public"
SRC_DIR = REPO_ROOT / "src"
DOCS_DIR = REPO_ROOT / "docs"
ASSETS_DIR = REPO_ROOT / "assets"

# Crawler entrypoints kept at repository root
ROOT_INDEX_FILES = (
    "README.md",
    "llms.txt",
    "llms-index.json",
    "robots.txt",
    "sitemap.xml",
    "humans.txt",
)

# Canonical content under public/
PUBLIC_CONTENT = (
    "FAQ.md",
    "RECRUITER.md",
    "PROOF.md",
    "AGENTS.md",
    "STACK.md",
    "PROFILE.md",
    "HOW-TO-CITE.md",
    "LICENSE.md",
    "CITATION.cff",
    "llms-full.txt",
    "llms-ctx-full.txt",
    "schema/llms-index.schema.json",
    "schema/person.jsonld",
    "schema/faq.jsonld",
    "schema/ENTITY.md",
    "schema/WIKIDATA.md",
)


def resolve_content(name: str) -> Path:
    """Resolve a content file: root index files vs public/."""
    if name in ROOT_INDEX_FILES or name == "README.md":
        return REPO_ROOT / name
    return PUBLIC_DIR / name
