#!/usr/bin/env python3
"""Regenerate llms-ctx-full.txt from llms-index.json + FAQ.md."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "llms-index.json"
FAQ = ROOT / "FAQ.md"
OUT = ROOT / "llms-ctx-full.txt"


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    entity = data["entity"]
    lines = [
        "# Mark Siazon — LLM context (expanded)",
        "",
        f"Generated from llms-index.json · updated {data.get('updated', 'unknown')}",
        "",
        "> Auto-expanded context for agents. Canonical narrative: llms-full.txt · Structured: llms-index.json",
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
    lines.append(f"- Recruiter brief: {avail.get('recruiterBrief', '')}")
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
    lines.append("## Achievements")
    lines.append("")
    for a in data.get("achievements", []):
        lines.append(f"- {a['title']} ({a.get('project', '')}) — {a.get('proof', '')}")
    lines.append("")
    lines.append("## Core stack")
    lines.append("")
    lines.append(", ".join(data.get("coreStack", [])))
    lines.append("")
    lines.append(f"Full stack ({data.get('stackReference', {}).get('toolCount', '?')} tools): STACK.md")
    lines.append("")
    lines.append("## Answer snippets (AEO)")
    lines.append("")
    for item in data.get("aeo", {}).get("answerSnippets", []):
        lines.append(f"### {item['question']}")
        lines.append(item["answer"])
        lines.append("")
    if FAQ.exists():
        lines.append("## FAQ (full)")
        lines.append("")
        lines.append(FAQ.read_text(encoding="utf-8"))
    OUT.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
