#!/usr/bin/env python3
"""Generate recruiter-fit README intelligence from public profile data."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "llms-index.json"
README = ROOT / "README.md"
PUBLIC = ROOT / "public"
OUTPUT = PUBLIC / "readme-intelligence.json"

START_MARKER = "<!-- PROFILE-INTELLIGENCE:START -->"
END_MARKER = "<!-- PROFILE-INTELLIGENCE:END -->"
PAGES_INTELLIGENCE_URL = "https://iron-mark.github.io/Iron-Mark/readme-intelligence.json"

PROOF_WEIGHTS = {
    "caseStudy": 12,
    "live": 8,
    "demo": 8,
    "repo": 8,
    "model": 5,
}

ROLE_KEYWORDS = {
    "Product Design Engineer": {
        "product": 4,
        "design": 4,
        "ux": 4,
        "ui": 3,
        "trust": 2,
        "safety": 2,
        "education": 2,
        "client": 2,
        "seo": 2,
    },
    "Full-Stack Developer": {
        "full-stack": 4,
        "react": 4,
        "next": 4,
        "web": 3,
        "platform": 3,
        "pwa": 3,
        "saas": 3,
        "supabase": 3,
        "client": 2,
    },
    "AI Workflow Builder": {
        "ai": 5,
        "ml": 4,
        "qwen": 4,
        "legal": 3,
        "trust": 3,
        "safety": 3,
        "credential": 3,
        "chat": 2,
    },
    "Mobile and Web3 Builder": {
        "mobile": 4,
        "android": 4,
        "flutter": 4,
        "kotlin": 4,
        "wear": 4,
        "gps": 3,
        "stellar": 4,
        "web3": 4,
        "minipay": 3,
        "celo": 3,
        "soroban": 3,
        "fintech": 3,
    },
}

DOMAIN_KEYWORDS = {
    "AI": {"ai", "ml", "qwen", "legal", "chat", "trust", "safety"},
    "Mobile": {"mobile", "android", "flutter", "kotlin", "wear", "gps", "sensor"},
    "Web3": {"web3", "stellar", "celo", "soroban", "minipay", "fintech", "payment"},
    "Client Web": {"client", "seo", "web", "launch", "podcast"},
    "Product": {"product", "ux", "ui", "design", "education", "platform"},
}


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value


def tokens(value: str) -> set[str]:
    normalized = value.lower().replace("/", " ").replace("_", " ")
    return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", normalized))


def achievement_map(data: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    by_project: dict[str, list[dict[str, str]]] = {}
    for achievement in data.get("achievements", []):
        project = str(achievement.get("project", "")).strip()
        if project:
            by_project.setdefault(project, []).append(achievement)
    return by_project


def proof_score(project: dict[str, Any]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    for key, weight in PROOF_WEIGHTS.items():
        if project.get(key):
            score += weight
            reasons.append(f"{key} proof")
    return min(score, 35), reasons


def impact_score(project_name: str, achievements: dict[str, list[dict[str, str]]]) -> tuple[int, list[str]]:
    project_achievements = achievements.get(project_name, [])
    if not project_achievements:
        return 0, []
    score = 12
    reasons: list[str] = []
    for achievement in project_achievements:
        title = str(achievement.get("title", ""))
        title_lower = title.lower()
        if any(term in title_lower for term in ("champion", "winner", "top 5")):
            score += 8
        if achievement.get("proof"):
            score += 3
        if title:
            reasons.append(title)
    return min(score, 25), reasons


def role_scores(project: dict[str, Any]) -> tuple[dict[str, int], list[str]]:
    text = " ".join(str(project.get(key, "")) for key in ("name", "slug", "focus"))
    project_tokens = tokens(text)
    scores: dict[str, int] = {}
    matched_terms: list[str] = []
    for role, keywords in ROLE_KEYWORDS.items():
        score = 0
        for keyword, weight in keywords.items():
            if keyword in project_tokens:
                score += weight
                matched_terms.append(keyword)
        scores[role] = min(score, 30)
    return scores, sorted(set(matched_terms))


def coverage_score(project: dict[str, Any]) -> tuple[int, list[str]]:
    text = " ".join(str(project.get(key, "")) for key in ("name", "slug", "focus"))
    project_tokens = tokens(text)
    domains = [
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if project_tokens.intersection(keywords)
    ]
    return min(len(domains) * 2, 10), domains


def project_url(project: dict[str, Any]) -> str:
    return str(
        project.get("caseStudy")
        or project.get("live")
        or project.get("demo")
        or project.get("repo")
        or project.get("model")
        or ""
    )


def evidence_links(project: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    labels = {
        "caseStudy": "case study",
        "live": "live",
        "demo": "demo",
        "repo": "repo",
        "model": "model",
    }
    for key, label in labels.items():
        value = project.get(key)
        if isinstance(value, str) and value:
            links.append({"label": label, "url": value})
    return links


def score_project(
    project: dict[str, Any],
    position: int,
    achievements: dict[str, list[dict[str, str]]],
    source: str,
) -> dict[str, Any]:
    proof, proof_reasons = proof_score(project)
    impact, impact_reasons = impact_score(str(project.get("name", "")), achievements)
    roles, matched_terms = role_scores(project)
    coverage, domains = coverage_score(project)
    role_match = max(roles.values()) if roles else 0
    total = proof + impact + role_match + coverage
    best_role = max(roles.items(), key=lambda item: item[1])[0] if roles else "Generalist"
    explanation_parts = []
    if proof_reasons:
        explanation_parts.append(f"proof: {', '.join(proof_reasons[:3])}")
    if impact_reasons:
        explanation_parts.append(f"impact: {impact_reasons[0]}")
    if domains:
        explanation_parts.append(f"coverage: {', '.join(domains)}")
    if matched_terms:
        explanation_parts.append(f"role terms: {', '.join(matched_terms[:5])}")

    return {
        "name": project.get("name", ""),
        "slug": project.get("slug") or slugify(str(project.get("name", ""))),
        "source": source,
        "url": project_url(project),
        "focus": project.get("focus", ""),
        "score": total,
        "scoreBreakdown": {
            "proof": proof,
            "impact": impact,
            "roleMatch": role_match,
            "coverage": coverage,
        },
        "bestRole": best_role,
        "roleScores": roles,
        "domains": domains,
        "evidence": evidence_links(project),
        "explanation": "; ".join(explanation_parts) or "Source-backed profile entry.",
        "sourcePosition": position,
    }


def role_summary(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for role in ROLE_KEYWORDS:
        ranked = sorted(
            projects,
            key=lambda project: (
                int(project.get("roleScores", {}).get(role, 0)),
                int(project.get("score", 0)),
                -int(project.get("sourcePosition", 999)),
            ),
            reverse=True,
        )
        top = [project for project in ranked if project.get("roleScores", {}).get(role, 0) > 0][:3]
        summaries.append(
            {
                "role": role,
                "score": sum(int(project.get("roleScores", {}).get(role, 0)) for project in top),
                "topProjects": [
                    {
                        "name": project["name"],
                        "url": project["url"],
                        "score": project.get("roleScores", {}).get(role, 0),
                    }
                    for project in top
                ],
                "explanation": f"Ranked from public project focus terms and proof links for {role.lower()} fit.",
            }
        )
    return sorted(summaries, key=lambda item: item["score"], reverse=True)


def build_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    achievements = achievement_map(data)
    scored: list[dict[str, Any]] = []
    for position, project in enumerate(data.get("featuredProjects", []), start=1):
        scored.append(score_project(project, position, achievements, "featuredProjects"))
    offset = len(scored)
    for position, project in enumerate(data.get("hackathonLab", []), start=1):
        scored.append(score_project(project, offset + position, achievements, "hackathonLab"))
    ranked = sorted(
        scored,
        key=lambda project: (
            int(project.get("score", 0)),
            int(project.get("scoreBreakdown", {}).get("proof", 0)),
            -int(project.get("sourcePosition", 999)),
        ),
        reverse=True,
    )
    return {
        "version": "1.0.0",
        "generatedBy": "src/scripts/generate_readme_intelligence.py",
        "generatedFrom": "llms-index.json",
        "updated": data.get("updated", ""),
        "objective": "recruiter-fit profile README intelligence",
        "claimPolicy": "Scores are deterministic hints generated only from public profile data and proof links; they are not external rankings.",
        "weights": {
            "proof": 35,
            "impact": 25,
            "roleMatch": 30,
            "coverage": 10,
        },
        "topProjects": ranked[:5],
        "rankedProjects": ranked,
        "roleSignals": role_summary(ranked),
        "machineReadable": {
            "pages": PAGES_INTELLIGENCE_URL,
            "source": "https://github.com/Iron-Mark/Iron-Mark/blob/main/public/readme-intelligence.json",
        },
    }


def markdown_link(label: str, url: str) -> str:
    if not url:
        return label
    return f'<a href="{url}" rel="noopener noreferrer">{label}</a>'


def render_readme_block(intelligence: dict[str, Any]) -> str:
    top_projects = intelligence.get("topProjects", [])[:3]
    role_signals = intelligence.get("roleSignals", [])[:3]
    rows = []
    for project in top_projects:
        breakdown = project.get("scoreBreakdown", {})
        evidence = project.get("evidence", [])[:3]
        evidence_links = " | ".join(
            markdown_link(item["label"], item["url"])
            for item in evidence
            if isinstance(item, dict) and item.get("url")
        )
        rows.append(
            "    <tr>"
            f'<td><b>{markdown_link(project.get("name", "Project"), project.get("url", ""))}</b><br>'
            f'<sub>{project.get("focus", "")}</sub></td>'
            f'<td><sub>{project.get("bestRole", "Generalist")} | score {project.get("score", 0)}/100</sub><br>'
            f'<sub>proof {breakdown.get("proof", 0)} | impact {breakdown.get("impact", 0)} | '
            f'fit {breakdown.get("roleMatch", 0)} | coverage {breakdown.get("coverage", 0)}</sub></td>'
            f"<td><sub>{evidence_links}</sub></td>"
            "</tr>"
        )

    role_text = " | ".join(
        f'{item.get("role", "Role")}: {", ".join(project.get("name", "") for project in item.get("topProjects", [])[:2])}'
        for item in role_signals
    )

    block = [
        START_MARKER,
        "",
        '<h2 align="center">Profile Intelligence</h2>',
        "",
        (
            '<p align="center"><sub>Deterministic recruiter-fit ranking generated from public proof links, '
            f'project focus, achievements, and role signals | updated {intelligence.get("updated", "")} | '
            f'<a href="{PAGES_INTELLIGENCE_URL}" rel="noopener noreferrer">machine-readable JSON</a></sub></p>'
        ),
        "",
        '<div align="center" style="width:100%;max-width:100%;overflow-x:auto">',
        "",
        '<table width="100%" style="table-layout:fixed;border-collapse:collapse">',
        "  <colgroup>",
        '    <col width="34%"/>',
        '    <col width="34%"/>',
        '    <col width="32%"/>',
        "  </colgroup>",
        "  <thead>",
        "    <tr>",
        '      <th align="left"><sub>Best proof routes</sub></th>',
        '      <th align="left"><sub>Why it ranks</sub></th>',
        '      <th align="left"><sub>Evidence</sub></th>',
        "    </tr>",
        "  </thead>",
        "  <tbody>",
        *rows,
        "  </tbody>",
        "</table>",
        "",
        "</div>",
        "",
        f'<p align="center"><sub>{role_text}</sub></p>',
        "",
        END_MARKER,
    ]
    return "\n".join(block)


def update_readme(readme: str, block: str) -> str:
    if START_MARKER in readme and END_MARKER in readme:
        pattern = re.compile(
            rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
            flags=re.DOTALL,
        )
        return pattern.sub(block, readme)
    insertion = "\n---\n\n<h2 align=\"center\">Featured Work</h2>"
    if insertion not in readme:
        raise RuntimeError("README.md missing Featured Work insertion point")
    return readme.replace(insertion, f"\n---\n\n{block}\n\n---\n\n<h2 align=\"center\">Featured Work</h2>", 1)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}")


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    intelligence = build_intelligence(data)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT, intelligence)
    block = render_readme_block(intelligence)
    README.write_text(update_readme(README.read_text(encoding="utf-8"), block), encoding="utf-8")
    print(f"Updated {README.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI failure path
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
