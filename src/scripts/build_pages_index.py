#!/usr/bin/env python3
"""Build GitHub Pages HTML files for the machine-readable mirror."""

from __future__ import annotations

import json
import re
import sys
from html import escape
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from generate_schema import pages_section_specs

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SCHEMA_PERSON = ROOT / "public" / "schema" / "person.jsonld"
SCHEMA_FAQ = ROOT / "public" / "schema" / "faq.jsonld"
INDEX = ROOT / "llms-index.json"
LAB_MD = ROOT / "public" / "LAB.md"

PAGES_URL = "https://iron-mark.github.io/Iron-Mark/"
PAGES_BASE = PAGES_URL.rstrip("/")
PORTFOLIO_URL = "https://www.marksiazon.dev"
SITE_NAME = "Mark Siazon Profile Index"
SOCIAL_IMAGE = f"{PAGES_BASE}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.png"
SOCIAL_IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
SOCIAL_IMAGE_WIDTH = 1200
SOCIAL_IMAGE_HEIGHT = 675
OPEN_GRAPH_LOCALE = "en_US"
FAVICON = "assets/brand/mark-siazon-favicon.svg"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
GITHUB_RAW = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main"


def csv(values: list[str]) -> str:
    return ", ".join(escape(value) for value in values if value)


def linked(url: str, label: str) -> str:
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def pages_href(path: str) -> str:
    return f"{PAGES_BASE}/{path.lstrip('/')}"


def linkify_plain_text(value: str) -> str:
    escaped = escape(value)
    return re.sub(
        r"https://[^\s<]+",
        lambda match: (
            f'<a href="{match.group(0)}" rel="noopener noreferrer">'
            f"{match.group(0)}</a>"
        ),
        escaped,
    )


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


def render_simple_markdown(markdown: str) -> str:
    parts: list[str] = []
    in_list = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if in_list:
                parts.append("</ul>")
                in_list = False
            continue
        if re.fullmatch(r"-{3,}", line.strip()):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append("<hr/>")
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            if in_list:
                parts.append("</ul>")
                in_list = False
            level = len(heading.group(1))
            parts.append(f"<h{level}>{linkify_plain_text(heading.group(2))}</h{level}>")
            continue
        bullet = re.match(r"^-\s+(.+)$", line)
        if bullet:
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{linkify_plain_text(bullet.group(1))}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        parts.append(f"<p>{linkify_plain_text(line)}</p>")
    if in_list:
        parts.append("</ul>")
    return "\n".join(parts)


def build_lab_page() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    portfolio_feeds = data.get("machineReadable", {}).get("portfolio", {})
    rss_feed = portfolio_feeds.get("rss", f"{PORTFOLIO_URL}/feed.xml")
    json_feed = portfolio_feeds.get("jsonFeed", f"{PORTFOLIO_URL}/feed.json")
    markdown = LAB_MD.read_text(encoding="utf-8")
    body = render_simple_markdown(markdown)
    title_match = re.search(r"^#\s+(.+)$", markdown, flags=re.MULTILINE)
    title = title_match.group(1) if title_match else "Mark Siazon - Hackathon & Lab Projects"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"/>
  <meta name="description" content="Rendered lab index for Mark Siazon hackathon projects across AI UI experiments, SaaS credentials, Baybayin learning, and Wear OS telemetry."/>
  <meta property="og:type" content="article"/>
  <meta property="og:title" content="{escape(title)}"/>
  <meta property="og:description" content="Hackathon and lab project index for Mark Siazon, a Philippines-based product designer and full-stack developer."/>
  <meta property="og:url" content="{pages_href('lab/')}"/>
  <title>{escape(title)}</title>
  <link rel="canonical" href="{pages_href('lab/')}"/>
  <link rel="alternate" type="application/rss+xml" href="{escape(rss_feed, quote=True)}"/>
  <link rel="alternate" type="application/feed+json" href="{escape(json_feed, quote=True)}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('LAB.md')}"/>
  <link rel="author" href="{PORTFOLIO_URL}"/>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f8fb;
      color: #172033;
    }}
    body {{ margin: 0; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 42px 22px 70px; }}
    article {{
      background: #fff;
      border: 1px solid #d8dee8;
      border-radius: 10px;
      padding: 34px 38px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }}
    .eyebrow {{
      display: inline-block;
      margin-bottom: 18px;
      font-size: 0.83rem;
      color: #475569;
      background: #eef2ff;
      border: 1px solid #c7d2fe;
      border-radius: 999px;
      padding: 5px 10px;
    }}
    h1 {{ font-size: clamp(2rem, 5vw, 2.7rem); line-height: 1.08; margin: 0 0 10px; color: #0f172a; }}
    h2 {{ font-size: 1.45rem; margin: 32px 0 8px; color: #111827; }}
    p {{ line-height: 1.65; margin: 10px 0; color: #334155; }}
    ul {{ margin: 10px 0 0; padding-left: 1.25rem; }}
    li {{ margin: 7px 0; line-height: 1.55; color: #334155; }}
    a {{ color: #2563eb; text-decoration: none; overflow-wrap: anywhere; }}
    a:hover {{ text-decoration: underline; }}
    hr {{ border: 0; border-top: 1px solid #e2e8f0; margin: 26px 0; }}
    @media (prefers-color-scheme: dark) {{
      :root {{ background: #0b1020; color: #e5e7eb; }}
      article {{ background: #111827; border-color: #273449; box-shadow: none; }}
      h1, h2 {{ color: #f8fafc; }}
      p, li {{ color: #d1d5db; }}
      hr {{ border-color: #334155; }}
      .eyebrow {{ color: #c7d2fe; background: #1e1b4b; border-color: #3730a3; }}
      a {{ color: #93c5fd; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">Rendered Pages view · source: <a href="{pages_href('LAB.md')}" rel="noopener noreferrer">LAB.md</a></div>
    <article>
{body}
    </article>
  </main>
</body>
</html>
"""
    DOCS.mkdir(parents=True, exist_ok=True)
    lab_dir = DOCS / "lab"
    lab_dir.mkdir(parents=True, exist_ok=True)
    (lab_dir / "index.html").write_text(html, encoding="utf-8")
    print("Wrote docs/lab/index.html")


def render_identity_links(urls: list[str]) -> str:
    links: list[str] = []
    for url in urls:
        if isinstance(url, str) and url.startswith("https://"):
            links.append(f'  <link rel="me" href="{escape(url, quote=True)}"/>')
    return "\n".join(links)


def render_section_navigation(sections: list[dict[str, str]]) -> str:
    links: list[str] = []
    for section in sections:
        links.append(
            f'<a href="#{escape(section["fragment"], quote=True)}">'
            f'{escape(section["heading"])}</a>'
        )
    return "\n      ".join(links)


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
    portfolio_feeds = data.get("machineReadable", {}).get("portfolio", {})
    rss_feed = portfolio_feeds.get("rss", f"{PORTFOLIO_URL}/feed.xml")
    json_feed = portfolio_feeds.get("jsonFeed", f"{PORTFOLIO_URL}/feed.json")
    projects = render_projects(data.get("featuredProjects", []))
    answers = render_answers(aeo.get("answerSnippets", []))
    triples = render_triples(data.get("triples", []))
    citation_links = render_citation_links(aeo.get("preferredCitationOrder", []))
    identity_links = render_identity_links(entity.get("sameAs", []))
    section_navigation = render_section_navigation(pages_section_specs(data))

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
  <meta property="og:image:type" content="image/png"/>
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
  <link rel="author" href="{pages_href('humans.txt')}"/>
{identity_links}
  <link rel="alternate" type="application/rss+xml" href="{escape(rss_feed, quote=True)}"/>
  <link rel="alternate" type="application/feed+json" href="{escape(json_feed, quote=True)}"/>
  <link rel="alternate" type="application/json" href="{pages_href('llms-index.json')}"/>
  <link rel="alternate" type="text/plain" href="{pages_href('llms.txt')}"/>
  <link rel="alternate" type="text/plain" href="{pages_href('llms-full.txt')}"/>
  <link rel="alternate" type="text/plain" href="{pages_href('llms-ctx-full.txt')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('FAQ.md')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('RECRUITER.md')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('PROOF.md')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('LAB.md')}"/>
  <link rel="alternate" type="text/html" href="{pages_href('lab/')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('STACK.md')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('PROFILE.md')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('README.md')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('HOW-TO-CITE.md')}"/>
  <link rel="alternate" type="text/markdown" href="{pages_href('LICENSE.md')}"/>
  <link rel="alternate" type="text/plain" href="{pages_href('CITATION.cff')}"/>
  <link rel="alternate" type="text/plain" href="{pages_href('humans.txt')}"/>
  <link rel="license" href="{pages_href('LICENSE.md')}"/>
  <link rel="alternate" type="application/ld+json" href="{pages_href('schema/person.jsonld')}"/>
  <link rel="alternate" type="application/ld+json" href="{pages_href('schema/faq.jsonld')}"/>
  <link rel="alternate" type="application/schema+json" href="{pages_href('schema/llms-index.schema.json')}"/>
  <link rel="sitemap" type="application/xml" href="{pages_href('sitemap.xml')}"/>
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
    .section-nav {{ display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 20px 0 28px; font-size: 0.95rem; }}
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
    <nav id="section-navigation" class="section-nav" aria-label="Profile index sections">
      {section_navigation}
    </nav>
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
      <li><a href="LAB.md">LAB.md</a> - hackathon and lab project index</li>
      <li><a href="lab/">lab</a> - rendered hackathon and lab project page</li>
      <li><a href="{escape(rss_feed, quote=True)}">Portfolio RSS</a> - canonical portfolio updates feed</li>
      <li><a href="{escape(json_feed, quote=True)}">Portfolio JSON Feed</a> - canonical machine-readable updates feed</li>
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
    build_lab_page()


if __name__ == "__main__":
    main()
