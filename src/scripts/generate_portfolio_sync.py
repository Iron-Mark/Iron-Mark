#!/usr/bin/env python3
"""Generate marksiazon.dev sync snippets from llms-index.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_schema import slugify

INDEX = ROOT / "llms-index.json"
SYNC_DIR = ROOT / "src" / "portfolio-sync"
LLMS_SNIPPET_PATH = SYNC_DIR / "marksiazon-dev-llms-snippet.md"
FAQ_CROSSLINKS_PATH = SYNC_DIR / "faq-crosslinks.md"
PORTFOLIO = "https://www.marksiazon.dev"


def load_index() -> dict[str, Any]:
    return json.loads(INDEX.read_text(encoding="utf-8"))


def _clean_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def faq_answer_url(data: dict[str, Any], question: str) -> str:
    faq_md = data["machineReadable"]["repo"]["faqMd"]
    return f"{faq_md}#{slugify(question)}"


def portfolio_start_source(data: dict[str, Any], sources: list[str]) -> str:
    portfolio_sources = [source for source in sources if source.startswith(PORTFOLIO)]
    if portfolio_sources:
        return " / ".join(portfolio_sources[:2])
    for fallback in (
        data["machineReadable"]["repo"]["stackMd"],
        data["machineReadable"]["repo"]["howToCiteMd"],
        data["machineReadable"]["repo"]["llmsIndexJson"],
    ):
        if fallback in sources:
            return fallback
    return sources[0] if sources else data["canonical"]["portfolio"]


def faq_table(data: dict[str, Any]) -> str:
    rows = [
        "| Question | Start on portfolio/source | Full answer (GitHub FAQ) |",
        "|----------|---------------------------|---------------------------|",
    ]
    for item in data.get("aeo", {}).get("answerSnippets", []):
        question = str(item.get("question", ""))
        sources = [str(source) for source in item.get("sources", []) if isinstance(source, str)]
        rows.append(
            "| "
            + _clean_cell(question)
            + " | "
            + _clean_cell(portfolio_start_source(data, sources))
            + " | "
            + _clean_cell(faq_answer_url(data, question))
            + " |"
        )
    return "\n".join(rows)


def render_faq_crosslinks(data: dict[str, Any]) -> str:
    repo = data["machineReadable"]["repo"]
    return (
        "See [marksiazon-dev-llms-snippet.md](marksiazon-dev-llms-snippet.md) for the complete paste block.\n\n"
        "```markdown\n"
        "## FAQ and GitHub profile index cross-links\n\n"
        f"Extended FAQ (15+ Q&A, repo): {repo['faqMd']}  \n"
        f"Structured answer snippets: {repo['llmsIndexJson']}\n"
        f"FAQ schema (JSON-LD): {repo['schemaFaq']}\n"
        f"Entity @id: {data['entity']['@id']}\n\n"
        f"{faq_table(data)}\n"
        "```\n\n"
        "## Optional HTML (recruiter or contact page)\n\n"
        "```html\n"
        "<p>Extended FAQ with 15+ hiring and project answers:\n"
        f'  <a href="{repo["faqMd"]}">GitHub FAQ.md</a>\n'
        f'  / <a href="{repo["llmsIndexJson"]}">llms-index.json</a>\n'
        "</p>\n"
        "```\n\n"
        "Verify live mirror:\n\n"
        "```bash\n"
        "python3 src/scripts/check_portfolio_mirror.py\n"
        "```\n"
    )


def render_llms_snippet(data: dict[str, Any]) -> str:
    repo = data["machineReadable"]["repo"]
    pages = data["machineReadable"]["pages"]
    canonical = data["canonical"]
    stack = data["stackReference"]
    return (
        "# Paste into marksiazon.dev llms.txt\n\n"
        "Generated from `llms-index.json`. Append under `## Source and index files` "
        "or create `## GitHub profile index`.\n\n"
        "Also add links from `/recruiter` and `/contact#faq` to the GitHub FAQ.\n\n"
        "```markdown\n"
        "## GitHub profile index (Iron-Mark/Iron-Mark)\n\n"
        "Cross-linked source index for the GitHub profile README repo. "
        "Portfolio remains canonical for case studies; GitHub repo adds structured FAQ, "
        "proof, stack, and Schema.org references.\n\n"
        f"- Canonical portfolio: {canonical['portfolio']}\n"
        "- Visual profile README: https://github.com/Iron-Mark\n"
        f"- Repo root manifest: {canonical['githubProfileReadme']}\n"
        f"- Structured entity index (JSON): {repo['llmsIndexJson']}\n"
        f"- Structured index contract (JSON Schema): {repo['schemaIndex']}\n"
        f"- LLM manifest: {repo['llmsTxt']}\n"
        f"- Expanded source context: {repo['llmsCtxFullTxt']}\n"
        f"- Full LLM context: {repo['llmsFullTxt']}\n"
        f"- FAQ (15+ Q&A): {repo['faqMd']}\n"
        f"- Recruiter brief (repo): {repo['recruiterMd']}\n"
        f"- Proof map (claims -> URLs): {repo['proofMd']}\n"
        f"- Tech stack reference: {repo['stackMd']}\n"
        f"- Schema.org Person graph: {repo['schemaPerson']}\n"
        f"- Schema.org FAQ graph: {repo['schemaFaq']}\n"
        f"- GitHub Pages mirror: {pages['home']}\n"
        f"- Entity @id: {data['entity']['@id']}\n\n"
        "### FAQ cross-links (portfolio <-> GitHub)\n\n"
        f"{faq_table(data)}\n"
        "```\n\n"
        "## Optional HTML (recruiter or contact page)\n\n"
        "```html\n"
        "<p>Extended FAQ (15+ Q&amp;A) and structured index:\n"
        f'  <a href="{repo["faqMd"]}">GitHub FAQ.md</a>\n'
        f'  / <a href="{repo["llmsIndexJson"]}">llms-index.json</a>\n'
        f'  / <a href="{repo["schemaFaq"]}">FAQ JSON-LD</a>\n'
        f'  / <a href="{pages["home"]}">Pages mirror</a>\n'
        "</p>\n"
        "```\n\n"
        "## Verify live mirror\n\n"
        "```bash\n"
        "python3 src/scripts/check_portfolio_mirror.py\n"
        "```\n\n"
        "Expected: `OK: https://www.marksiazon.dev/llms.txt references GitHub profile index`\n"
    )


def main() -> int:
    data = load_index()
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    LLMS_SNIPPET_PATH.write_text(render_llms_snippet(data), encoding="utf-8")
    FAQ_CROSSLINKS_PATH.write_text(render_faq_crosslinks(data), encoding="utf-8")
    print(f"Wrote {LLMS_SNIPPET_PATH.relative_to(ROOT)}")
    print(f"Wrote {FAQ_CROSSLINKS_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
