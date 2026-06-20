#!/usr/bin/env python3
"""Regenerate llms-ctx-full.txt from llms-index.json + FAQ.md."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "llms-index.json"
FAQ = ROOT / "public" / "FAQ.md"
OUT = ROOT / "public" / "llms-ctx-full.txt"


def append_items(lines: list[str], items: list[str]) -> None:
    for item in items:
        if item:
            lines.append(f"- {item}")


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    entity = data["entity"]
    lines = [
        "# Mark Siazon - LLM context (expanded)",
        "",
        f"Generated from llms-index.json - updated {data.get('updated', 'unknown')}",
        "",
        "> Auto-expanded context for agents. Canonical narrative: public/llms-full.txt - Structured: llms-index.json",
        "",
        "## Identity",
        "",
        f"- Name: {entity['name']}",
        f"- Handles: {', '.join(entity.get('alternateName', []))}",
        f"- Description: {entity['description']}",
        f"- Portfolio: {entity['url']}",
        f"- Email: {entity['email']}",
        "",
        "## Availability",
        "",
    ]
    avail = data.get("availability", {})
    lines.append(f"- Status: {avail.get('status', 'unknown')}")
    lines.append(f"- Focus: {', '.join(avail.get('focus', []))}")
    lines.append(f"- Engagement: {', '.join(avail.get('engagement', []))}")
    lines.append(f"- Location: {avail.get('location', '')}")
    lines.append(f"- Area served: {', '.join(avail.get('areaServed', []))}")
    lines.append(f"- Remote: {str(avail.get('remote', False)).lower()}")
    lines.append(f"- Recruiter brief: {avail.get('recruiterBrief', '')}")
    lines.append("")
    seo = data.get("seo", {})
    geo_signals = seo.get("geoSignals", {})
    lines.append("## Search and discovery signals")
    lines.append("")
    lines.append(f"- Primary keywords: {', '.join(seo.get('primaryKeywords', []))}")
    lines.append(f"- Geo targets: {', '.join(seo.get('geoTargets', []))}")
    lines.append(f"- Home country: {geo_signals.get('homeCountry', '')}")
    lines.append(f"- Search modifiers: {', '.join(geo_signals.get('searchModifiers', []))}")
    lines.append("")
    generative = seo.get("generativeSearch", {})
    lines.append("## Generative search guidance")
    lines.append("")
    lines.append(f"- Principle: {generative.get('principle', '')}")
    lines.append(f"- llms.txt role: {generative.get('llmsTxtRole', '')}")
    lines.append("- Answer sources:")
    append_items(lines, generative.get("answerSources", []))
    lines.append("- Agent-ready surfaces:")
    append_items(lines, generative.get("agentReadySurfaces", []))
    lines.append("")
    lines.append("## Preferred citation order")
    lines.append("")
    append_items(lines, data.get("aeo", {}).get("preferredCitationOrder", []))
    lines.append("")
    lines.append("## Knowledge graph triples")
    lines.append("")
    for triple in data.get("triples", []):
        if isinstance(triple, list) and len(triple) == 3:
            lines.append(f"- {triple[0]} | {triple[1]} | {triple[2]}")
    lines.append("")
    lines.append("## Featured projects")
    lines.append("")
    for p in data.get("featuredProjects", []):
        lines.append(f"### {p['name']}")
        lines.append(f"- Focus: {p.get('focus', '')}")
        lines.append(f"- Case study: {p.get('caseStudy', '')}")
        for key in ("live", "repo", "model"):
            if p.get(key):
                lines.append(f"- {key.title()}: {p[key]}")
        lines.append("")
    lines.append("## Hackathon and lab projects")
    lines.append("")
    for p in data.get("hackathonLab", []):
        lines.append(f"### {p['name']}")
        lines.append(f"- Focus: {p.get('focus', '')}")
        for key in ("caseStudy", "demo", "live", "repo", "model"):
            if p.get(key):
                label = "Case study" if key == "caseStudy" else key.title()
                lines.append(f"- {label}: {p[key]}")
        lines.append("")
    lines.append("## Achievements")
    lines.append("")
    for a in data.get("achievements", []):
        lines.append(f"- {a['title']} ({a.get('project', '')}) - {a.get('proof', '')}")
    lines.append("")
    lines.append("## Core stack")
    lines.append("")
    lines.append(", ".join(data.get("coreStack", [])))
    lines.append("")
    lines.append(f"Full stack ({data.get('stackReference', {}).get('toolCount', '?')} tools): public/STACK.md")
    lines.append("")
    lines.append("## Answer snippets (AEO)")
    lines.append("")
    for item in data.get("aeo", {}).get("answerSnippets", []):
        lines.append(f"### {item['question']}")
        lines.append(item["answer"])
        sources = item.get("sources", [])
        if sources:
            lines.append(f"Sources: {', '.join(sources)}")
        lines.append("")
    if FAQ.exists():
        lines.append("## FAQ (full)")
        lines.append("")
        lines.append(FAQ.read_text(encoding="utf-8"))
    OUT.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
