#!/usr/bin/env python3
"""Build docs/index.html for the GitHub Pages machine-readable mirror."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SCHEMA_PERSON = ROOT / "public" / "schema" / "person.jsonld"
SCHEMA_FAQ = ROOT / "public" / "schema" / "faq.jsonld"
INDEX = ROOT / "llms-index.json"

PAGES_URL = "https://iron-mark.github.io/Iron-Mark/"
PAGES_BASE = PAGES_URL.rstrip("/")
PORTFOLIO_URL = "https://www.marksiazon.dev"
SITE_NAME = "Mark Siazon Profile Index"
SOCIAL_IMAGE = f"{PAGES_BASE}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.webp"
SOCIAL_IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
SOCIAL_IMAGE_WIDTH = 400
SOCIAL_IMAGE_HEIGHT = 225
OPEN_GRAPH_LOCALE = "en_US"
FAVICON = "assets/brand/mark-siazon-favicon.svg"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
GITHUB_RAW = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main"


def csv(values: list[str]) -> str:
    return ", ".join(escape(value) for value in values if value)


def linked(url: str, label: str) -> str:
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value


def answer_dom_id(question: str) -> str:
    return f"answer-{slugify(question)}"


def render_projects(projects: list[dict[str, str]]) -> str:
    items: list[str] = []
    for project in projects:
        links = [
            linked(project["caseStudy"], "case study") if project.get("caseStudy") else "",
            linked(project["live"], "live") if project.get("live") else "",
            linked(project["repo"], "repo") if project.get("repo") else "",
            linked(project["model"], "model") if project.get("model") else "",
        ]
        proof_links = " | ".join(link for link in links if link)
        proof = f" <span class=\"meta\">({proof_links})</span>" if proof_links else ""
        items.append(
            "      <li>"
            f"<strong>{escape(project.get('name', 'Project'))}</strong> - "
            f"{escape(project.get('focus', 'featured work'))}.{proof}"
            "</li>"
        )
    return "\n".join(items)


def render_answers(snippets: list[dict[str, str]]) -> str:
    items: list[str] = []
    for item in snippets:
        source_links = [
            linked(source, source)
            for source in item.get("sources", [])
            if isinstance(source, str) and source
        ]
        sources = ""
        if source_links:
            sources = f"<br/><span class=\"meta\">Sources: {' | '.join(source_links)}</span>"
        items.append(
            f"      <li id=\"{escape(answer_dom_id(item.get('question', '')), quote=True)}\">"
            f"<strong>{escape(item.get('question', 'Question'))}</strong><br/>"
            f"{escape(item.get('answer', ''))}"
            f"{sources}"
            "</li>"
        )
    return "\n".join(items)


def render_triples(triples: list[list[str]]) -> str:
    items: list[str] = []
    for triple in triples:
        if len(triple) != 3:
            continue
        subject, predicate, object_value = triple
        items.append(
            "      <li>"
            f"<strong>{escape(subject)}</strong> "
            f"<span class=\"meta\">{escape(predicate)}</span> "
            f"{escape(object_value)}"
            "</li>"
        )
    return "\n".join(items)


def render_citation_links(urls: list[str]) -> str:
    items: list[str] = []
    for url in urls:
        items.append(f"      <li>{linked(url, url)}</li>")
    return "\n".join(items)


def render_identity_links(urls: list[str]) -> str:
    links: list[str] = []
    for url in urls:
        if isinstance(url, str) and url.startswith("https://"):
            links.append(f'  <link rel="me" href="{escape(url, quote=True)}"/>')
    return "\n".join(links)


def pages_local_schema(value: Any) -> Any:
    """Rewrite public source-file identifiers to the deployed Pages mirror."""
    if isinstance(value, dict):
        return {key: pages_local_schema(child) for key, child in value.items()}
    if isinstance(value, list):
        return [pages_local_schema(child) for child in value]
    if isinstance(value, str):
        replacements = (
            (f"{GITHUB_BLOB}/public/schema/", f"{PAGES_BASE}/schema/"),
            (f"{GITHUB_BLOB}/public/", f"{PAGES_BASE}/"),
            (f"{GITHUB_RAW}/public/schema/", f"{PAGES_BASE}/schema/"),
            (f"{GITHUB_RAW}/public/", f"{PAGES_BASE}/"),
        )
        for source, target in replacements:
            if value.startswith(source):
                return value.replace(source, target, 1)
        return value
    return value


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    person_schema = json.dumps(
        pages_local_schema(json.loads(SCHEMA_PERSON.read_text(encoding="utf-8"))),
        indent=2,
        ensure_ascii=False,
    )
    faq_schema = json.dumps(
        pages_local_schema(json.loads(SCHEMA_FAQ.read_text(encoding="utf-8"))),
        indent=2,
        ensure_ascii=False,
    )
    entity = data.get("entity", {})
    availability = data.get("availability", {})
    seo = data.get("seo", {})
    aeo = data.get("aeo", {})
    description = (
        "Machine-readable GitHub profile index for Mark Siazon: structured entity data, "
        "FAQ, proof map, recruiter brief, llms.txt, and Schema.org JSON-LD."
    )
    updated = data.get("updated", "")
    job_titles = csv(entity.get("jobTitle", []))
    focus = csv(availability.get("focus", []))
    engagement = csv(availability.get("engagement", []))
    area_served = csv(availability.get("areaServed", []))
    primary_keywords = csv(seo.get("primaryKeywords", []))
    geo_targets = csv(seo.get("geoTargets", []))
    projects = render_projects(data.get("featuredProjects", []))
    answers = render_answers(aeo.get("answerSnippets", []))
    triples = render_triples(data.get("triples", []))
    citation_links = render_citation_links(aeo.get("preferredCitationOrder", []))
    identity_links = render_identity_links(entity.get("sameAs", []))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"/>
  <meta name="description" content="{escape(description)}"/>
  <meta name="author" content="Mark Siazon"/>
  <meta property="og:type" content="profile"/>
  <meta property="og:locale" content="{OPEN_GRAPH_LOCALE}"/>
  <meta property="og:title" content="{SITE_NAME}"/>
  <meta property="og:description" content="{escape(description)}"/>
  <meta property="og:url" content="{PAGES_URL}"/>
  <meta property="og:image" content="{SOCIAL_IMAGE}"/>
  <meta property="og:image:secure_url" content="{SOCIAL_IMAGE}"/>
  <meta property="og:image:type" content="image/webp"/>
  <meta property="og:image:width" content="{SOCIAL_IMAGE_WIDTH}"/>
  <meta property="og:image:height" content="{SOCIAL_IMAGE_HEIGHT}"/>
  <meta property="og:image:alt" content="{SOCIAL_IMAGE_ALT}"/>
  <meta property="og:site_name" content="{SITE_NAME}"/>
  <meta property="og:updated_time" content="{escape(updated)}"/>
  <meta property="article:modified_time" content="{escape(updated)}"/>
  <meta property="profile:first_name" content="Mark"/>
  <meta property="profile:last_name" content="Siazon"/>
  <meta property="profile:username" content="Iron-Mark"/>
  <meta name="date" content="{escape(updated)}"/>
  <meta itemprop="dateModified" content="{escape(updated)}"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{SITE_NAME}"/>
  <meta name="twitter:description" content="{escape(description)}"/>
  <meta name="twitter:image" content="{SOCIAL_IMAGE}"/>
  <meta name="twitter:image:alt" content="{SOCIAL_IMAGE_ALT}"/>
  <title>{SITE_NAME}</title>
  <link rel="icon" type="image/svg+xml" href="{FAVICON}"/>
  <link rel="canonical" href="{PAGES_URL}"/>
  <link rel="alternate" hreflang="en" href="{PAGES_URL}"/>
  <link rel="alternate" hreflang="x-default" href="{PAGES_URL}"/>
  <link rel="author" href="humans.txt"/>
{identity_links}
  <link rel="alternate" type="application/json" href="llms-index.json"/>
  <link rel="alternate" type="text/plain" href="llms.txt"/>
  <link rel="alternate" type="text/plain" href="llms-full.txt"/>
  <link rel="alternate" type="text/plain" href="llms-ctx-full.txt"/>
  <link rel="alternate" type="text/markdown" href="FAQ.md"/>
  <link rel="alternate" type="text/markdown" href="RECRUITER.md"/>
  <link rel="alternate" type="text/markdown" href="PROOF.md"/>
  <link rel="alternate" type="text/markdown" href="STACK.md"/>
  <link rel="alternate" type="text/markdown" href="PROFILE.md"/>
  <link rel="alternate" type="text/markdown" href="README.md"/>
  <link rel="alternate" type="text/markdown" href="HOW-TO-CITE.md"/>
  <link rel="alternate" type="text/markdown" href="LICENSE.md"/>
  <link rel="alternate" type="text/plain" href="CITATION.cff"/>
  <link rel="alternate" type="text/plain" href="humans.txt"/>
  <link rel="license" href="LICENSE.md"/>
  <link rel="alternate" type="application/ld+json" href="schema/person.jsonld"/>
  <link rel="alternate" type="application/ld+json" href="schema/faq.jsonld"/>
  <link rel="alternate" type="application/schema+json" href="schema/llms-index.schema.json"/>
  <link rel="sitemap" type="application/xml" href="sitemap.xml"/>
  <script type="application/ld+json">
{person_schema}
  </script>
  <script type="application/ld+json">
{faq_schema}
  </script>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; line-height: 1.55; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 48px 20px; }}
    h1 {{ font-size: clamp(2rem, 5vw, 3.25rem); line-height: 1.05; margin: 0 0 12px; letter-spacing: 0; }}
    h2 {{ margin-top: 32px; }}
    a {{ color: #2563eb; }}
    ul {{ padding-left: 1.25rem; }}
    li {{ margin: 8px 0; }}
    code {{ font-size: 0.95em; }}
    .meta {{ color: #64748b; }}
    .breadcrumb {{ margin: 0 0 20px; font-size: 0.95rem; color: #64748b; }}
    .breadcrumb a {{ color: inherit; }}
    .facts {{ display: grid; gap: 10px; padding-left: 0; list-style: none; }}
    .facts li {{ margin: 0; }}
  </style>
</head>
<body>
  <main id="main-content">
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <a href="{PORTFOLIO_URL}">Mark Siazon Portfolio</a> / <span>{SITE_NAME}</span>
    </nav>
    <h1>{SITE_NAME}</h1>
    <p id="profile-summary">{escape(entity.get("description", description))}</p>
    <p>Machine-readable mirror of <a href="https://github.com/Iron-Mark/Iron-Mark">Iron-Mark/Iron-Mark</a>. Canonical portfolio: <a href="{PORTFOLIO_URL}">marksiazon.dev</a>. Updated {escape(updated)}.</p>
    <h2 id="profile-facts">Profile Facts</h2>
    <ul class="facts">
      <li><strong>Name:</strong> {escape(entity.get("name", "Mark Siazon"))} ({csv(entity.get("alternateName", []))})</li>
      <li><strong>Roles:</strong> {job_titles}</li>
      <li><strong>Availability:</strong> {escape(availability.get("status", "open"))}; {engagement}; {focus}</li>
      <li><strong>Geography:</strong> based in {escape(availability.get("location", "Philippines"))}; serves {area_served}</li>
      <li><strong>Contact:</strong> {linked(availability.get("contact", f"{PORTFOLIO_URL}/contact"), "contact form")} | {escape(entity.get("email", ""))}</li>
      <li><strong>Recruiter brief:</strong> {linked(availability.get("recruiterBrief", f"{PORTFOLIO_URL}/recruiter"), "marksiazon.dev/recruiter")}</li>
    </ul>
    <h2 id="featured-work">Featured Work</h2>
    <ul>
{projects}
    </ul>
    <h2 id="answer-corpus">Answer Corpus</h2>
    <ul>
{answers}
    </ul>
    <h2 id="geo-topic-signals">Geo And Topic Signals</h2>
    <p><strong>Primary search topics:</strong> {primary_keywords}</p>
    <p><strong>Service regions:</strong> {geo_targets}</p>
    <h2 id="knowledge-graph">Knowledge Graph</h2>
    <ul>
{triples}
    </ul>
    <h2 id="start-here">Start Here</h2>
    <ul>
      <li><a href="llms-index.json">llms-index.json</a> - structured entity, project, SEO, AEO, and GEO index</li>
      <li><a href="llms-ctx-full.txt">llms-ctx-full.txt</a> - expanded agent context</li>
      <li><a href="FAQ.md">FAQ.md</a> - visible question and answer corpus</li>
      <li><a href="RECRUITER.md">RECRUITER.md</a> - recruiter brief</li>
      <li><a href="PROOF.md">PROOF.md</a> - claim verification map</li>
      <li><a href="llms.txt">llms.txt</a> - LLM manifest</li>
      <li><a href="schema/llms-index.schema.json">schema/llms-index.schema.json</a> - JSON Schema contract for llms-index.json</li>
      <li><a href="schema/person.jsonld">schema/person.jsonld</a> - Person, profile, project, and content graph</li>
      <li><a href="schema/faq.jsonld">schema/faq.jsonld</a> - FAQPage, Question, and Answer graph</li>
    </ul>
    <h2 id="citation">Citation</h2>
    <p><a href="HOW-TO-CITE.md">HOW-TO-CITE.md</a> and <a href="PROOF.md">PROOF.md</a> define citation order, verification boundaries, and public evidence.</p>
    <ol>
{citation_links}
    </ol>
    <p class="meta">This mirror exposes the same facts in readable HTML, JSON, Markdown, text, sitemap, and Schema.org JSON-LD formats; the portfolio remains the canonical human-facing site.</p>
  </main>
</body>
</html>
"""
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print("Wrote docs/index.html")


if __name__ == "__main__":
    main()
