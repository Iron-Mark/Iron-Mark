"""Load profile index files from repo root and public/."""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

# src/mcp-server/iron_mark_profile/store.py → repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC = REPO_ROOT / "public"

if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_paths import resolve_content  # noqa: E402

ROOT_ONLY = {"llms-index.json", "llms.txt", "humans.txt", "robots.txt", "sitemap.xml"}


def repo_path(name: str) -> Path:
    if name.startswith("public/"):
        return REPO_ROOT / name
    if name in ROOT_ONLY:
        return REPO_ROOT / name
    return resolve_content(name)


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    return json.loads(repo_path("llms-index.json").read_text(encoding="utf-8"))


def read_text(name: str) -> str:
    return repo_path(name).read_text(encoding="utf-8")


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def search_faq(query: str, limit: int = 5) -> list[dict[str, str]]:
    q = normalize(query)
    if not q:
        return []

    index = load_index()
    hits: list[tuple[int, dict[str, str]]] = []

    for item in index.get("aeo", {}).get("answerSnippets", []):
        question = item.get("question", "")
        answer = item.get("answer", "")
        blob = normalize(f"{question} {answer}")
        score = sum(1 for token in q.split() if token in blob)
        if q in blob:
            score += 3
        if score:
            hits.append((score, {"question": question, "answer": answer}))

    hits.sort(key=lambda x: (-x[0], x[1]["question"]))
    return [h[1] for h in hits[:limit]]


def list_featured_projects() -> list[dict[str, Any]]:
    return load_index().get("featuredProjects", [])


def list_hackathon_projects() -> list[dict[str, Any]]:
    return load_index().get("hackathonLab", [])


def find_project(slug_or_name: str) -> dict[str, Any] | None:
    key = normalize(slug_or_name).replace(" ", "-")
    for project in list_featured_projects() + list_hackathon_projects():
        slug = normalize(project.get("slug", project.get("name", ""))).replace(" ", "-")
        name = normalize(project.get("name", "")).replace(" ", "-")
        if key in (slug, name) or key in slug or key in name:
            return project
    return None


def profile_summary() -> dict[str, Any]:
    index = load_index()
    return {
        "entity": index.get("entity"),
        "identifiers": index.get("identifiers"),
        "availability": index.get("availability"),
        "canonical": index.get("canonical"),
        "coreStack": index.get("coreStack"),
        "stackReference": index.get("stackReference"),
        "updated": index.get("updated"),
        "contentRoot": "public/",
    }


def proof_for_project(slug_or_name: str) -> dict[str, Any] | None:
    project = find_project(slug_or_name)
    if not project:
        return None
    return {
        "project": project,
        "proofMatrix": load_index().get("canonical", {}).get("proofMatrix"),
        "achievements": [
            a
            for a in load_index().get("achievements", [])
            if normalize(a.get("project", "")) in normalize(slug_or_name)
        ],
    }
