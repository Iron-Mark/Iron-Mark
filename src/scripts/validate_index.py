#!/usr/bin/env python3
"""Validate SEO/AEO/GEO index, schema, crawl, and asset consistency."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pages_mirror import PAGES_PRIMARY_IMAGE, PAGES_SITEMAP_ENTRIES

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "public"
SCHEMA = PUBLIC / "schema"
INDEX = ROOT / "llms-index.json"
README = ROOT / "README.md"
FAQ = PUBLIC / "FAQ.md"
SITEMAP = ROOT / "sitemap.xml"
ROBOTS = ROOT / "robots.txt"
DOCS_INDEX = ROOT / "docs" / "index.html"
LLMS_CTX = PUBLIC / "llms-ctx-full.txt"

GITHUB_RAW = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
PAGES = "https://iron-mark.github.io/Iron-Mark"
PAGES_HOST = "iron-mark.github.io"
PAGES_SOCIAL_IMAGE = f"{PAGES}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.webp"
SOCIAL_IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
SOCIAL_IMAGE_WIDTH = 400
SOCIAL_IMAGE_HEIGHT = 225
OPEN_GRAPH_LOCALE = "en_US"
README_PRODUCTION_FORBIDDEN_LINKS = {
    ".github/": "GitHub maintenance files",
    "docs/STRUCTURE.md": "internal repository layout docs",
    "docs/internal/": "internal maintainer docs",
    "src/mcp-server": "optional local MCP server docs",
    "src/scripts/": "maintenance scripts",
    "public/AGENTS.md": "agent maintenance instructions",
    "public/FAQ.md": "machine-readable source files; use the Pages mirror instead",
    "public/PROOF.md": "machine-readable source files; use the Pages mirror instead",
    "public/RECRUITER.md": "machine-readable source files; use the Pages mirror instead",
    "public/llms-": "machine-readable source files; use the Pages mirror instead",
    "public/schema/": "machine-readable schema files; use the Pages mirror instead",
    "llms-index.json": "machine-readable source files; use the Pages mirror instead",
    "llms.txt": "machine-readable source files; use the Pages mirror instead",
    "humans.txt": "crawler source files; use the Pages mirror instead",
    "robots.txt": "crawler source files; use the Pages mirror instead",
    "sitemap.xml": "crawler source files; use the Pages mirror instead",
    "REPO_SETUP": "repo setup checklist",
}
PRODUCTION_SURFACE_FORBIDDEN_LINKS = {
    ".github/": "GitHub maintenance files",
    "docs/internal/": "internal maintainer docs",
    "src/": "source/development files",
    "src/mcp-server": "optional local MCP server docs",
    "src/scripts/": "maintenance scripts",
    "src/portfolio-sync": "portfolio sync helper files",
    "public/AGENTS.md": "agent maintenance instructions",
    "mcp-server": "optional local MCP server docs",
    "REPO_SETUP": "repo setup checklist",
}
README_PRODUCTION_FORBIDDEN_PATTERNS = (
    "po" + r"st[- ]merge",
    "po" + r"st[- ]deployment",
    "po" + r"st deploy",
    "after " + "deploy",
)

errors: list[str] = []
warnings: list[str] = []


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"Missing JSON file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")
    return {}


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value


def faq_question_id(faq_id: str, question: str) -> str:
    faq_url = faq_id.split("#", 1)[0]
    return f"{faq_url}#{slugify(question)}"


def pages_faq_id(data: dict[str, Any]) -> str:
    return f"{data.get('machineReadable', {}).get('pages', {}).get('faqMd', '')}#faq"


def graph_nodes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    graph = doc.get("@graph", [])
    return [node for node in graph if isinstance(node, dict)]


def node_by_id(doc: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in graph_nodes(doc):
        if node.get("@id") == node_id:
            return node
    return None


def html_jsonld_nodes(html: str, surface: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    scripts = re.findall(
        r"<script\s+type=[\"']application/ld\+json[\"']>\s*(.*?)\s*</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if len(scripts) < 2:
        errors.append(f"{surface} must inline both Person/content and FAQ JSON-LD graphs")
    for index, script in enumerate(scripts, start=1):
        try:
            doc = json.loads(script)
        except json.JSONDecodeError as exc:
            errors.append(f"{surface} contains invalid JSON-LD script #{index}: {exc}")
            continue
        if isinstance(doc, dict) and "@graph" in doc:
            nodes.extend(graph_nodes(doc))
        elif isinstance(doc, dict):
            nodes.append(doc)
        else:
            errors.append(f"{surface} JSON-LD script #{index} must be an object or @graph")
    return nodes


def node_types(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type", [])
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    return set()


def node_ref_ids(values: Any) -> set[str]:
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        return set()
    return {item.get("@id", "") for item in values if isinstance(item, dict) and item.get("@id")}


def repo_public_url_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for child in value.values():
            found.extend(repo_public_url_values(child))
        return found
    if isinstance(value, list):
        found = []
        for child in value:
            found.extend(repo_public_url_values(child))
        return found
    if isinstance(value, str) and (value.startswith(f"{GITHUB_BLOB}/public/") or value.startswith(f"{GITHUB_RAW}/public/")):
        return [value]
    return []


def area_names(values: Any) -> set[str]:
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        return set()
    return {item.get("name", "") for item in values if isinstance(item, dict) and item.get("name")}


def download_id(key: str) -> str:
    return f"{PAGES}/#download-{slugify(key)}"


def expected_downloads(pages: dict[str, str]) -> dict[str, tuple[str, str]]:
    return {
        "llms-index-json": (pages.get("llmsIndexJson", ""), "application/json"),
        "llms-txt": (pages.get("llmsTxt", ""), "text/plain"),
        "llms-full-txt": (pages.get("llmsFullTxt", ""), "text/plain"),
        "llms-ctx-full-txt": (pages.get("llmsCtxFullTxt", ""), "text/plain"),
        "faq-md": (pages.get("faqMd", ""), "text/markdown"),
        "recruiter-md": (pages.get("recruiterMd", ""), "text/markdown"),
        "proof-md": (pages.get("proofMd", ""), "text/markdown"),
        "stack-md": (pages.get("stackMd", ""), "text/markdown"),
        "profile-md": (pages.get("profileMd", ""), "text/markdown"),
        "readme-md": (pages.get("readmeMd", ""), "text/markdown"),
        "how-to-cite-md": (pages.get("howToCiteMd", ""), "text/markdown"),
        "license-md": (pages.get("licenseMd", ""), "text/markdown"),
        "citation-cff": (pages.get("citationCff", ""), "text/plain"),
        "person-jsonld": (pages.get("schemaPerson", ""), "application/ld+json"),
        "faq-jsonld": (pages.get("schemaFaq", ""), "application/ld+json"),
        "schema-json": (pages.get("schemaIndex", ""), "application/schema+json"),
        "humans-txt": (pages.get("humansTxt", ""), "text/plain"),
        "sitemap-xml": (pages.get("sitemap", ""), "application/xml"),
        "robots-txt": (pages.get("robots", ""), "text/plain"),
    }


def schema_type_ok(value: Any, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def schema_format_ok(value: str, schema_format: str) -> bool:
    if schema_format == "uri":
        parsed = urlparse(value)
        if not parsed.scheme:
            return False
        if parsed.scheme in {"http", "https"} and not parsed.netloc:
            return False
        return True
    if schema_format == "date":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    return True


def validate_contract_subset(value: Any, schema: dict[str, Any], path: str) -> None:
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must be {schema['const']!r}")
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        if not schema_type_ok(value, schema_type):
            errors.append(f"{path} must be type {schema_type}")
            return
    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(f"{path} must be at least {min_length} characters")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.fullmatch(pattern, value):
            errors.append(f"{path} does not match pattern {pattern}")
        schema_format = schema.get("format")
        if isinstance(schema_format, str) and not schema_format_ok(value, schema_format):
            errors.append(f"{path} must be format {schema_format}")
    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path} must contain at least {min_items} items")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            errors.append(f"{path} must contain at most {max_items} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_contract_subset(item, item_schema, f"{path}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(f"{path} missing required key: {key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            if schema.get("additionalProperties") is False:
                extra = sorted(set(value) - set(properties))
                if extra:
                    errors.append(f"{path} has unsupported key(s): {extra}")
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, dict):
                    validate_contract_subset(value[key], child_schema, f"{path}.{key}")


def check_assets(slug: str) -> None:
    icon = ROOT / "assets" / "projects" / slug / "icon.png"
    if not icon.exists():
        errors.append(f"Missing icon: assets/projects/{slug}/icon.png")


def check_required_index_keys(data: dict[str, Any]) -> None:
    for key in ("updated", "entity", "featuredProjects", "hackathonLab", "aeo", "triples", "schema", "machineReadable"):
        if key not in data:
            errors.append(f"llms-index.json missing key: {key}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("updated", ""))):
        errors.append("llms-index.json updated must be YYYY-MM-DD")
    expected_schema = f"{GITHUB_RAW}/public/schema/llms-index.schema.json"
    if data.get("$schema") != expected_schema:
        errors.append(f"llms-index.json $schema must point to {expected_schema}")
    sitemaps = data.get("seo", {}).get("technicalSignals", {}).get("sitemaps", [])
    if f"{PAGES}/sitemap.xml" not in sitemaps:
        errors.append("llms-index.json seo.technicalSignals.sitemaps missing GitHub Pages sitemap")
    raw_sitemaps = sorted(item for item in sitemaps if str(item).startswith(f"{GITHUB_RAW}/"))
    if raw_sitemaps:
        errors.append(f"llms-index.json seo.technicalSignals.sitemaps must not use raw GitHub sitemap(s): {raw_sitemaps}")


def check_seo_geo_consistency(data: dict[str, Any]) -> None:
    seo = data.get("seo", {})
    technical = seo.get("technicalSignals", {})
    canonical = data.get("canonical", {})
    machine = data.get("machineReadable", {})
    repo = machine.get("repo", {})
    pages = machine.get("pages", {})
    availability = data.get("availability", {})
    geo = seo.get("geoSignals", {})
    generative = seo.get("generativeSearch", {})

    if technical.get("canonicalPersonId") != data.get("entity", {}).get("@id"):
        errors.append("llms-index.json seo.technicalSignals.canonicalPersonId drift")
    if technical.get("canonicalPortfolio") != canonical.get("portfolio"):
        errors.append("llms-index.json seo.technicalSignals.canonicalPortfolio drift")
    if technical.get("pagesMirror") != pages.get("home"):
        errors.append("llms-index.json seo.technicalSignals.pagesMirror drift")

    schema_graphs = set(technical.get("schemaGraphs", []))
    for key in ("schemaPerson", "schemaFaq"):
        if repo.get(key) not in schema_graphs:
            errors.append(f"llms-index.json seo.technicalSignals.schemaGraphs missing repo.{key}")

    availability_regions = set(availability.get("areaServed", []))
    geo_targets = set(seo.get("geoTargets", []))
    service_regions = set(geo.get("serviceRegions", []))
    missing_geo_targets = sorted(availability_regions - geo_targets)
    if missing_geo_targets:
        errors.append(f"llms-index.json seo.geoTargets missing availability region(s): {missing_geo_targets}")
    missing_service_regions = sorted(availability_regions - service_regions)
    if missing_service_regions:
        errors.append(f"llms-index.json seo.geoSignals.serviceRegions missing availability region(s): {missing_service_regions}")
    if geo.get("homeCountry") != availability.get("location"):
        errors.append("llms-index.json seo.geoSignals.homeCountry must match availability.location")

    answer_sources = set(generative.get("answerSources", []))
    required_answer_sources = {
        repo.get("faqMd", ""),
        repo.get("llmsIndexJson", ""),
        repo.get("llmsCtxFullTxt", ""),
        canonical.get("proofMatrix", ""),
        availability.get("recruiterBrief", ""),
    }
    missing_answer_sources = sorted(required_answer_sources - answer_sources)
    if missing_answer_sources:
        errors.append(f"llms-index.json seo.generativeSearch.answerSources missing: {missing_answer_sources}")

    agent_surfaces = set(generative.get("agentReadySurfaces", []))
    required_agent_surfaces = {
        "llms-index.json",
        "llms.txt",
        "public/llms-full.txt",
        "public/llms-ctx-full.txt",
        "public/FAQ.md",
        "public/schema/person.jsonld",
        "public/schema/faq.jsonld",
    }
    missing_agent_surfaces = sorted(required_agent_surfaces - agent_surfaces)
    if missing_agent_surfaces:
        errors.append(f"llms-index.json seo.generativeSearch.agentReadySurfaces missing: {missing_agent_surfaces}")


def check_projects(data: dict[str, Any], readme: str) -> None:
    for project in data.get("featuredProjects", []):
        slug = project.get("slug", "")
        name = project.get("name", slug)
        check_assets(slug)
        case_study = project.get("caseStudy", "")
        if case_study and case_study not in readme:
            warnings.append(f"{name}: case study URL not in README.md")
        if name not in readme:
            warnings.append(f"{name}: name not found in README.md")


def check_readme_assets(readme: str) -> None:
    for match in re.findall(r'src="(assets/[^"]+)"|srcset="(assets/[^"]+)"', readme):
        path = match[0] or match[1]
        if not (ROOT / path).exists():
            errors.append(f"README references missing asset: {path}")


def check_readme_public_surface(readme: str) -> None:
    lower = readme.lower()
    for needle, reason in README_PRODUCTION_FORBIDDEN_LINKS.items():
        if needle.lower() in lower:
            errors.append(f"README.md links production surface to {reason}: {needle}")
    for pattern in README_PRODUCTION_FORBIDDEN_PATTERNS:
        if re.search(pattern, lower):
            errors.append("README.md contains retired deployment/setup phrasing")


def check_public_surface() -> None:
    surfaces = {
        "README.md": README,
        "humans.txt": ROOT / "humans.txt",
        "llms.txt": ROOT / "llms.txt",
        "docs/index.html": DOCS_INDEX,
        "sitemap.xml": SITEMAP,
    }
    for name, path in surfaces.items():
        if not path.exists():
            continue
        lower = path.read_text(encoding="utf-8").lower()
        for needle, reason in PRODUCTION_SURFACE_FORBIDDEN_LINKS.items():
            if needle.lower() in lower:
                errors.append(f"{name} exposes {reason}: {needle}")
        for pattern in README_PRODUCTION_FORBIDDEN_PATTERNS:
            if re.search(pattern, lower):
                errors.append(f"{name} contains retired deployment/setup phrasing")


def check_pages_index_visible_content(data: dict[str, Any]) -> None:
    if not DOCS_INDEX.exists():
        errors.append("Missing docs/index.html")
        return
    raw_html = DOCS_INDEX.read_text(encoding="utf-8")
    html = unescape(raw_html)
    updated = str(data.get("updated", ""))
    if f'<meta name="date" content="{updated}"/>' not in html:
        errors.append("docs/index.html meta date must match llms-index.json updated")
    if f"Updated {updated}." not in html:
        errors.append("docs/index.html visible updated date must match llms-index.json updated")
    if f'<link rel="canonical" href="{PAGES}/"/>' not in html:
        errors.append("docs/index.html canonical must point to the GitHub Pages mirror")
    if f'<meta property="og:locale" content="{OPEN_GRAPH_LOCALE}"/>' not in html:
        errors.append("docs/index.html missing Open Graph locale metadata")
    expected_image_tags = {
        f'<meta property="og:image" content="{PAGES_SOCIAL_IMAGE}"/>',
        f'<meta property="og:image:secure_url" content="{PAGES_SOCIAL_IMAGE}"/>',
        '<meta property="og:image:type" content="image/webp"/>',
        f'<meta property="og:image:width" content="{SOCIAL_IMAGE_WIDTH}"/>',
        f'<meta property="og:image:height" content="{SOCIAL_IMAGE_HEIGHT}"/>',
        f'<meta property="og:image:alt" content="{SOCIAL_IMAGE_ALT}"/>',
        f'<meta name="twitter:image" content="{PAGES_SOCIAL_IMAGE}"/>',
        f'<meta name="twitter:image:alt" content="{SOCIAL_IMAGE_ALT}"/>',
    }
    for tag in expected_image_tags:
        if tag not in html:
            errors.append(f"docs/index.html missing social image metadata: {tag}")
    if '<link rel="author" href="humans.txt"/>' not in html:
        errors.append("docs/index.html missing author link to humans.txt")
    for same_as in data.get("entity", {}).get("sameAs", []):
        if isinstance(same_as, str) and same_as.startswith("https://") and f'<link rel="me" href="{same_as}"/>' not in html:
            errors.append(f"docs/index.html missing rel=me identity link: {same_as}")
    for heading in ("Profile Facts", "Featured Work", "Answer Corpus", "Geo And Topic Signals", "Knowledge Graph", "Citation"):
        if heading not in html:
            errors.append(f"docs/index.html missing visible section: {heading}")
    required_alternates = {
        'type="application/json" href="llms-index.json"',
        'type="text/plain" href="llms.txt"',
        'type="text/plain" href="llms-full.txt"',
        'type="text/plain" href="llms-ctx-full.txt"',
        'type="text/markdown" href="FAQ.md"',
        'type="text/markdown" href="RECRUITER.md"',
        'type="text/markdown" href="PROOF.md"',
        'type="text/markdown" href="STACK.md"',
        'type="text/markdown" href="PROFILE.md"',
        'type="text/markdown" href="README.md"',
        'type="text/markdown" href="HOW-TO-CITE.md"',
        'type="text/markdown" href="LICENSE.md"',
        'type="text/plain" href="CITATION.cff"',
        'type="text/plain" href="humans.txt"',
        'type="application/ld+json" href="schema/person.jsonld"',
        'type="application/ld+json" href="schema/faq.jsonld"',
        'type="application/schema+json" href="schema/llms-index.schema.json"',
    }
    for alternate in required_alternates:
        if alternate not in html:
            errors.append(f"docs/index.html missing alternate link: {alternate}")
    entity = data.get("entity", {})
    if entity.get("description") and entity["description"] not in html:
        errors.append("docs/index.html missing visible entity description")
    for title in entity.get("jobTitle", []):
        if title not in html:
            errors.append(f"docs/index.html missing visible jobTitle: {title}")
    for region in data.get("availability", {}).get("areaServed", []):
        if region not in html:
            errors.append(f"docs/index.html missing visible service region: {region}")
    for project in data.get("featuredProjects", []):
        name = project.get("name", "")
        focus = project.get("focus", "")
        if name and name not in html:
            errors.append(f"docs/index.html missing visible featured project: {name}")
        if focus and focus not in html:
            errors.append(f"docs/index.html missing visible project focus: {name}")
    for snippet in data.get("aeo", {}).get("answerSnippets", []):
        question = snippet.get("question", "")
        answer = snippet.get("answer", "")
        if question and question not in html:
            errors.append(f"docs/index.html missing visible answer question: {question}")
        if answer and answer not in html:
            errors.append(f"docs/index.html missing visible answer text for: {question}")
    for triple in data.get("triples", []):
        if isinstance(triple, list) and len(triple) == 3:
            for part in triple:
                if part not in html:
                    errors.append(f"docs/index.html missing visible knowledge graph term: {part}")
    jsonld_nodes = html_jsonld_nodes(raw_html, "docs/index.html")
    if not any("Person" in node_types(node) and node.get("@id") == data.get("entity", {}).get("@id") for node in jsonld_nodes):
        errors.append("docs/index.html inline JSON-LD missing Person node")
    inline_faq_id = pages_faq_id(data)
    if not any("FAQPage" in node_types(node) and node.get("@id") == inline_faq_id for node in jsonld_nodes):
        errors.append("docs/index.html inline JSON-LD missing FAQPage node")
    question_nodes = {node.get("@id", ""): node for node in jsonld_nodes if "Question" in node_types(node)}
    for snippet in data.get("aeo", {}).get("answerSnippets", []):
        expected = faq_question_id(inline_faq_id, snippet.get("question", ""))
        question_node = question_nodes.get(expected)
        if not question_node:
            errors.append(f"docs/index.html inline JSON-LD missing Question node: {expected}")
            continue
        answer_node = question_node.get("acceptedAnswer", {})
        if not isinstance(answer_node, dict) or answer_node.get("text") != snippet.get("answer"):
            errors.append(f"docs/index.html inline JSON-LD answer drift for: {snippet.get('question')}")
    for index, script in enumerate(
        re.findall(
            r"<script\s+type=[\"']application/ld\+json[\"']>\s*(.*?)\s*</script>",
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        ),
        start=1,
    ):
        try:
            jsonld = json.loads(script)
        except json.JSONDecodeError:
            continue
        public_urls = repo_public_url_values(jsonld)
        if public_urls:
            errors.append(
                f"docs/index.html inline JSON-LD script #{index} must use Pages URLs for deployed public files: {public_urls}"
            )


def check_people_first_search_signals(readme: str) -> None:
    surfaces = {
        "README.md": readme,
        "public/STACK.md": (PUBLIC / "STACK.md").read_text(encoding="utf-8") if (PUBLIC / "STACK.md").exists() else "",
        "docs/index.html": DOCS_INDEX.read_text(encoding="utf-8") if DOCS_INDEX.exists() else "",
    }
    for name, text in surfaces.items():
        if re.search(r"<!--\s*(SEO|LLM|AEO|GEO)", text, re.IGNORECASE):
            errors.append(f"{name} contains hidden SEO/LLM keyword comment")
    docs_index = surfaces["docs/index.html"]
    if re.search(r"<meta\s+name=[\"']keywords[\"']", docs_index, re.IGNORECASE):
        errors.append("docs/index.html contains obsolete meta keywords tag")


def enforce_production_readme_surface() -> bool:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if base_ref:
        return base_ref == "main"
    if ref_name:
        return ref_name == "main"
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return True
    return branch in ("", "main")


def faq_questions() -> list[str]:
    if not FAQ.exists():
        errors.append("Missing public/FAQ.md")
        return []
    text = FAQ.read_text(encoding="utf-8")
    return [q.strip() for q in re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE)]


def check_aeo_coverage(data: dict[str, Any], questions: list[str]) -> None:
    snippets = data.get("aeo", {}).get("answerSnippets", [])
    if len(snippets) < 15:
        warnings.append(f"Only {len(snippets)} answerSnippets (recommend 15+)")
    snippet_questions = [item.get("question", "") for item in snippets]
    missing_from_faq = sorted(q for q in snippet_questions if q and q not in questions)
    if missing_from_faq:
        errors.append(f"AEO snippets missing visible FAQ question(s): {missing_from_faq}")
    missing_from_snippets = sorted(q for q in questions if q not in snippet_questions)
    if missing_from_snippets:
        warnings.append(f"FAQ question(s) not in answerSnippets: {missing_from_snippets}")
    for item in snippets:
        question = item.get("question", "")
        sources = item.get("sources", [])
        if not isinstance(sources, list) or not sources:
            errors.append(f"AEO snippet missing citation sources: {question}")
            continue
        bad_sources = [source for source in sources if not isinstance(source, str) or not source.startswith("https://")]
        if bad_sources:
            errors.append(f"AEO snippet has invalid source URL(s) for {question}: {bad_sources}")


def check_knowledge_graph(data: dict[str, Any]) -> None:
    triples_raw = data.get("triples", [])
    if not isinstance(triples_raw, list):
        errors.append("llms-index.json triples must be a list")
        return
    triples: set[tuple[str, str, str]] = set()
    for index, triple in enumerate(triples_raw):
        if (
            not isinstance(triple, list)
            or len(triple) != 3
            or not all(isinstance(part, str) and part.strip() for part in triple)
        ):
            errors.append(f"llms-index.json triples[{index}] must be [subject, predicate, object] strings")
            continue
        item = (triple[0], triple[1], triple[2])
        if item in triples:
            errors.append(f"llms-index.json duplicate triple: {item}")
        triples.add(item)

    entity_name = data.get("entity", {}).get("name", "Mark Siazon")
    required: set[tuple[str, str, str]] = set()
    required.add((entity_name, "basedIn", data.get("availability", {}).get("location", "")))
    for title in data.get("entity", {}).get("jobTitle", []):
        required.add((entity_name, "isA", title))
    for region in data.get("availability", {}).get("areaServed", []):
        required.add((entity_name, "serves", region))
    for project in data.get("featuredProjects", []):
        name = project.get("name", "")
        focus = project.get("focus", "")
        if name:
            required.add((entity_name, "built", name))
        if name and focus:
            required.add((name, "focusesOn", focus))
    for project in data.get("hackathonLab", []):
        name = project.get("name", "")
        if name:
            required.add((entity_name, "maintains", name))

    missing = sorted(item for item in required if item not in triples)
    if missing:
        errors.append(f"llms-index.json triples missing required knowledge facts: {missing}")


def check_generated_context(data: dict[str, Any]) -> None:
    if not LLMS_CTX.exists():
        errors.append("Missing public/llms-ctx-full.txt")
        return
    text = LLMS_CTX.read_text(encoding="utf-8")
    availability = data.get("availability", {})
    for region in availability.get("areaServed", []):
        if region not in text:
            errors.append(f"public/llms-ctx-full.txt missing availability areaServed region: {region}")
    if "- Remote:" not in text:
        errors.append("public/llms-ctx-full.txt missing Availability remote flag")
    if "## Knowledge graph triples" not in text:
        errors.append("public/llms-ctx-full.txt missing Knowledge graph triples section")
    for triple in data.get("triples", []):
        if isinstance(triple, list) and len(triple) == 3:
            line = f"- {triple[0]} | {triple[1]} | {triple[2]}"
            if line not in text:
                errors.append(f"public/llms-ctx-full.txt missing knowledge graph triple: {line}")


def check_schema(data: dict[str, Any], questions: list[str]) -> None:
    index_schema_path = SCHEMA / "llms-index.schema.json"
    person_path = SCHEMA / "person.jsonld"
    faq_path = SCHEMA / "faq.jsonld"
    index_schema = load_json(index_schema_path)
    person_schema = load_json(person_path)
    faq_schema = load_json(faq_path)
    if not index_schema or not person_schema or not faq_schema:
        return
    if index_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("llms-index.schema.json must declare JSON Schema draft 2020-12")
    validate_contract_subset(data, index_schema, "llms-index.json")
    required_index_keys = set(index_schema.get("required", []))
    for key in ("updated", "entity", "featuredProjects", "hackathonLab", "seo", "aeo", "triples", "schema"):
        if key not in required_index_keys:
            errors.append(f"llms-index.schema.json missing required key: {key}")
    schema_index_url = data.get("schema", {}).get("index")
    if schema_index_url != f"{GITHUB_BLOB}/public/schema/llms-index.schema.json":
        errors.append("llms-index.json schema.index must point to public/schema/llms-index.schema.json")
    repo_schema_index_url = data.get("machineReadable", {}).get("repo", {}).get("schemaIndex")
    if repo_schema_index_url != f"{GITHUB_BLOB}/public/schema/llms-index.schema.json":
        errors.append("llms-index.json machineReadable.repo.schemaIndex must point to public/schema/llms-index.schema.json")
    machine_readable = data.get("machineReadable", {})
    repo = machine_readable.get("repo", {})
    pages = machine_readable.get("pages", {})
    expected_repo = {
        "llmsTxt": f"{GITHUB_BLOB}/llms.txt",
        "llmsFullTxt": f"{GITHUB_BLOB}/public/llms-full.txt",
        "llmsIndexJson": f"{GITHUB_BLOB}/llms-index.json",
        "llmsCtxFullTxt": f"{GITHUB_BLOB}/public/llms-ctx-full.txt",
        "faqMd": f"{GITHUB_BLOB}/public/FAQ.md",
        "recruiterMd": f"{GITHUB_BLOB}/public/RECRUITER.md",
        "proofMd": f"{GITHUB_BLOB}/public/PROOF.md",
        "stackMd": f"{GITHUB_BLOB}/public/STACK.md",
        "profileMd": f"{GITHUB_BLOB}/public/PROFILE.md",
        "readmeMd": f"{GITHUB_BLOB}/public/README.md",
        "howToCiteMd": f"{GITHUB_BLOB}/public/HOW-TO-CITE.md",
        "licenseMd": f"{GITHUB_BLOB}/public/LICENSE.md",
        "citationCff": f"{GITHUB_BLOB}/public/CITATION.cff",
        "schemaPerson": f"{GITHUB_BLOB}/public/schema/person.jsonld",
        "schemaFaq": f"{GITHUB_BLOB}/public/schema/faq.jsonld",
        "schemaIndex": f"{GITHUB_BLOB}/public/schema/llms-index.schema.json",
        "humansTxt": f"{GITHUB_BLOB}/humans.txt",
        "sitemap": f"{GITHUB_BLOB}/sitemap.xml",
        "robots": f"{GITHUB_BLOB}/robots.txt",
    }
    for key, expected in expected_repo.items():
        if repo.get(key) != expected:
            errors.append(f"llms-index.json machineReadable.repo.{key} must point to {expected}")
    expected_pages = {
        "home": f"{PAGES}/",
        "llmsTxt": f"{PAGES}/llms.txt",
        "llmsFullTxt": f"{PAGES}/llms-full.txt",
        "llmsIndexJson": f"{PAGES}/llms-index.json",
        "llmsCtxFullTxt": f"{PAGES}/llms-ctx-full.txt",
        "faqMd": f"{PAGES}/FAQ.md",
        "recruiterMd": f"{PAGES}/RECRUITER.md",
        "proofMd": f"{PAGES}/PROOF.md",
        "stackMd": f"{PAGES}/STACK.md",
        "profileMd": f"{PAGES}/PROFILE.md",
        "readmeMd": f"{PAGES}/README.md",
        "howToCiteMd": f"{PAGES}/HOW-TO-CITE.md",
        "licenseMd": f"{PAGES}/LICENSE.md",
        "citationCff": f"{PAGES}/CITATION.cff",
        "schemaPerson": f"{PAGES}/schema/person.jsonld",
        "schemaFaq": f"{PAGES}/schema/faq.jsonld",
        "schemaIndex": f"{PAGES}/schema/llms-index.schema.json",
        "humansTxt": f"{PAGES}/humans.txt",
        "sitemap": f"{PAGES}/sitemap.xml",
        "robots": f"{PAGES}/robots.txt",
    }
    for key, expected in expected_pages.items():
        if pages.get(key) != expected:
            errors.append(f"llms-index.json machineReadable.pages.{key} must point to {expected}")

    person_id = data.get("entity", {}).get("@id")
    person_fragment_base = f"{str(person_id).split('#', 1)[0]}#"
    contact_action_id = f"{person_fragment_base}contact-action"
    contact_entry_id = f"{person_fragment_base}contact-entrypoint"
    person = node_by_id(person_schema, person_id)
    if not person or "Person" not in node_types(person):
        errors.append("person.jsonld missing Person node matching llms-index entity @id")
    else:
        index_same_as = set(data.get("entity", {}).get("sameAs", []))
        schema_same_as = set(person.get("sameAs", []))
        missing_same_as = sorted(index_same_as - schema_same_as)
        if missing_same_as:
            errors.append(f"person.jsonld Person sameAs missing: {missing_same_as}")
        achievement_titles = {item.get("title", "") for item in data.get("achievements", []) if item.get("title")}
        schema_awards = set(person.get("award", []))
        missing_awards = sorted(achievement_titles - schema_awards)
        if missing_awards:
            errors.append(f"person.jsonld Person award missing: {missing_awards}")

        availability = data.get("availability", {})
        area_served = set(availability.get("areaServed", []))
        contact_points = person.get("contactPoint", [])
        if isinstance(contact_points, dict):
            contact_points = [contact_points]
        hiring_contact = next(
            (
                item
                for item in contact_points
                if isinstance(item, dict) and item.get("contactType") == "hiring"
            ),
            None,
        )
        if not hiring_contact:
            errors.append("person.jsonld Person missing hiring contactPoint")
        else:
            missing_contact_area = sorted(area_served - area_names(hiring_contact.get("areaServed")))
            if missing_contact_area:
                errors.append(f"person.jsonld hiring contactPoint areaServed missing: {missing_contact_area}")

        expected_offer_ids = {f"{person_fragment_base}offer-{slugify(focus)}" for focus in availability.get("focus", [])}
        missing_offer_refs = sorted(expected_offer_ids - node_ref_ids(person.get("makesOffer")))
        if missing_offer_refs:
            errors.append(f"person.jsonld Person makesOffer missing: {missing_offer_refs}")
        if person.get("image", {}).get("@id") != f"{PAGES}/#primary-image":
            errors.append("person.jsonld Person image must reference Pages primary ImageObject")
        if person.get("potentialAction", {}).get("@id") != contact_action_id:
            errors.append("person.jsonld Person potentialAction must reference hiring ContactAction")
        known_languages = person.get("knowsLanguage", [])
        if not isinstance(known_languages, list):
            known_languages = [known_languages]
        if not any(
            isinstance(language, dict)
            and language.get("@type") == "Language"
            and language.get("alternateName") == "en"
            and language.get("name") == "English"
            for language in known_languages
        ):
            errors.append("person.jsonld Person knowsLanguage must include English language node")
        offer_catalog = node_by_id(person_schema, f"{person_fragment_base}services")
        if not offer_catalog or "OfferCatalog" not in node_types(offer_catalog):
            errors.append("person.jsonld missing OfferCatalog services node")
        else:
            missing_catalog_refs = sorted(expected_offer_ids - node_ref_ids(offer_catalog.get("itemListElement")))
            if missing_catalog_refs:
                errors.append(f"person.jsonld OfferCatalog itemListElement missing: {missing_catalog_refs}")
        for focus in availability.get("focus", []):
            offer_id = f"{person_fragment_base}offer-{slugify(focus)}"
            service_id = f"{person_fragment_base}service-{slugify(focus)}"
            offer = node_by_id(person_schema, offer_id)
            if not offer or "Offer" not in node_types(offer):
                errors.append(f"person.jsonld missing Offer node: {offer_id}")
            else:
                if offer.get("itemOffered", {}).get("@id") != service_id:
                    errors.append(f"person.jsonld Offer itemOffered drift for: {focus}")
                missing_offer_area = sorted(area_served - area_names(offer.get("areaServed")))
                if missing_offer_area:
                    errors.append(f"person.jsonld Offer areaServed missing for {focus}: {missing_offer_area}")
            service = node_by_id(person_schema, service_id)
            if not service or "Service" not in node_types(service):
                errors.append(f"person.jsonld missing Service node: {service_id}")
            else:
                if service.get("provider", {}).get("@id") != person_id:
                    errors.append(f"person.jsonld Service provider drift for: {focus}")
                missing_service_area = sorted(area_served - area_names(service.get("areaServed")))
                if missing_service_area:
                    errors.append(f"person.jsonld Service areaServed missing for {focus}: {missing_service_area}")

    pages = data.get("machineReadable", {}).get("pages", {})
    pages_site_id = data.get("identifiers", {}).get("githubPagesMirror")
    pages_page_id = f"{PAGES}/#webpage"
    pages_breadcrumb_id = f"{PAGES}/#breadcrumb"
    pages_catalog_id = f"{PAGES}/#data-catalog"
    pages_dataset_id = f"{PAGES}/#machine-readable-dataset"
    pages_image_id = f"{PAGES}/#primary-image"
    pages_page = node_by_id(person_schema, pages_page_id)
    if not pages_page or "CollectionPage" not in node_types(pages_page):
        errors.append("person.jsonld missing GitHub Pages CollectionPage node")
    else:
        if pages_page.get("url") != pages.get("home"):
            errors.append("person.jsonld Pages CollectionPage url drift")
        if pages_page.get("isPartOf", {}).get("@id") != pages_site_id:
            errors.append("person.jsonld Pages CollectionPage isPartOf drift")
        if pages_page.get("mainEntity", {}).get("@id") != person_id:
            errors.append("person.jsonld Pages CollectionPage mainEntity drift")
        if pages_page.get("breadcrumb", {}).get("@id") != pages_breadcrumb_id:
            errors.append("person.jsonld Pages CollectionPage breadcrumb drift")
        if pages_page.get("primaryImageOfPage", {}).get("@id") != pages_image_id:
            errors.append("person.jsonld Pages CollectionPage primaryImageOfPage drift")
        if pages_page.get("thumbnailUrl") != PAGES_SOCIAL_IMAGE:
            errors.append("person.jsonld Pages CollectionPage thumbnailUrl drift")
        if pages_page.get("potentialAction", {}).get("@id") != contact_action_id:
            errors.append("person.jsonld Pages CollectionPage potentialAction drift")
        required_parts = {
            pages_catalog_id,
            pages_dataset_id,
            pages.get("llmsIndexJson", ""),
            pages.get("llmsTxt", ""),
            pages.get("llmsCtxFullTxt", ""),
            pages.get("faqMd", ""),
            pages.get("recruiterMd", ""),
            pages.get("proofMd", ""),
            pages.get("stackMd", ""),
            pages.get("profileMd", ""),
            pages.get("readmeMd", ""),
            pages.get("howToCiteMd", ""),
            pages.get("licenseMd", ""),
            pages.get("citationCff", ""),
            pages.get("schemaPerson", ""),
            pages.get("schemaFaq", ""),
            pages.get("schemaIndex", ""),
            pages.get("humansTxt", ""),
            pages.get("sitemap", ""),
            pages.get("robots", ""),
        }
        missing_parts = sorted(required_parts - node_ref_ids(pages_page.get("hasPart")))
        if missing_parts:
            errors.append(f"person.jsonld Pages CollectionPage hasPart missing: {missing_parts}")
    data_catalog = node_by_id(person_schema, pages_catalog_id)
    if not data_catalog or "DataCatalog" not in node_types(data_catalog):
        errors.append("person.jsonld missing GitHub Pages DataCatalog node")
    else:
        if data_catalog.get("dataset", {}).get("@id") != pages_dataset_id:
            errors.append("person.jsonld DataCatalog dataset drift")
        if data_catalog.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld DataCatalog about drift")
    image = node_by_id(person_schema, pages_image_id)
    if not image or "ImageObject" not in node_types(image):
        errors.append("person.jsonld missing Pages primary ImageObject node")
    else:
        if image.get("url") != PAGES_SOCIAL_IMAGE:
            errors.append("person.jsonld ImageObject url drift")
        if image.get("contentUrl") != PAGES_SOCIAL_IMAGE:
            errors.append("person.jsonld ImageObject contentUrl drift")
        if image.get("encodingFormat") != "image/webp":
            errors.append("person.jsonld ImageObject encodingFormat must be image/webp")
        if image.get("width") != SOCIAL_IMAGE_WIDTH:
            errors.append("person.jsonld ImageObject width drift")
        if image.get("height") != SOCIAL_IMAGE_HEIGHT:
            errors.append("person.jsonld ImageObject height drift")
        if image.get("caption") != SOCIAL_IMAGE_ALT:
            errors.append("person.jsonld ImageObject caption drift")
        if image.get("creator", {}).get("@id") != person_id:
            errors.append("person.jsonld ImageObject creator drift")
        if image.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld ImageObject about drift")
        if image.get("isPartOf", {}).get("@id") != pages_page_id:
            errors.append("person.jsonld ImageObject isPartOf drift")
        if image.get("representativeOfPage") is not True:
            errors.append("person.jsonld ImageObject must be representativeOfPage")
    contact_action = node_by_id(person_schema, contact_action_id)
    if not contact_action or "ContactAction" not in node_types(contact_action):
        errors.append("person.jsonld missing hiring ContactAction node")
    else:
        if contact_action.get("target", {}).get("@id") != contact_entry_id:
            errors.append("person.jsonld ContactAction target drift")
        if contact_action.get("recipient", {}).get("@id") != person_id:
            errors.append("person.jsonld ContactAction recipient drift")
        if contact_action.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld ContactAction about drift")
        if contact_action.get("object", {}).get("@id") != person_id:
            errors.append("person.jsonld ContactAction object drift")
    contact_entry = node_by_id(person_schema, contact_entry_id)
    if not contact_entry or "EntryPoint" not in node_types(contact_entry):
        errors.append("person.jsonld missing hiring ContactAction EntryPoint node")
    else:
        if contact_entry.get("urlTemplate") != data.get("availability", {}).get("contact"):
            errors.append("person.jsonld ContactAction EntryPoint urlTemplate drift")
        if contact_entry.get("inLanguage") != "en":
            errors.append("person.jsonld ContactAction EntryPoint inLanguage must be en")
    dataset = node_by_id(person_schema, pages_dataset_id)
    downloads = expected_downloads(pages)
    expected_download_ids = {download_id(key) for key in downloads}
    if not dataset or "Dataset" not in node_types(dataset):
        errors.append("person.jsonld missing GitHub Pages Dataset node")
    else:
        if dataset.get("url") != pages.get("llmsIndexJson"):
            errors.append("person.jsonld Dataset url drift")
        if dataset.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld Dataset about drift")
        if dataset.get("includedInDataCatalog", {}).get("@id") != pages_catalog_id:
            errors.append("person.jsonld Dataset catalog membership drift")
        if dataset.get("isAccessibleForFree") is not True:
            errors.append("person.jsonld Dataset must be marked isAccessibleForFree")
        expected_keywords = set(
            data.get("seo", {}).get("primaryKeywords", [])
            + data.get("seo", {}).get("geoTargets", [])
            + data.get("availability", {}).get("areaServed", [])
        )
        dataset_keywords = dataset.get("keywords")
        if not isinstance(dataset_keywords, list):
            errors.append("person.jsonld Dataset keywords must be a list")
        else:
            missing_keywords = sorted(expected_keywords - set(dataset_keywords))
            if missing_keywords:
                errors.append(f"person.jsonld Dataset keywords missing: {missing_keywords}")
        missing_distribution = sorted(expected_download_ids - node_ref_ids(dataset.get("distribution")))
        if missing_distribution:
            errors.append(f"person.jsonld Dataset distribution missing: {missing_distribution}")
    for key, (content_url, encoding) in downloads.items():
        download = node_by_id(person_schema, download_id(key))
        if not download or "DataDownload" not in node_types(download):
            errors.append(f"person.jsonld missing DataDownload node: {download_id(key)}")
            continue
        if download.get("contentUrl") != content_url:
            errors.append(f"person.jsonld DataDownload contentUrl drift for: {key}")
        if download.get("url") != content_url:
            errors.append(f"person.jsonld DataDownload url drift for: {key}")
        if download.get("encodingFormat") != encoding:
            errors.append(f"person.jsonld DataDownload encodingFormat drift for: {key}")
        if download.get("dateModified") != data.get("updated"):
            errors.append(f"person.jsonld DataDownload dateModified drift for: {key}")
        if download.get("license") != data.get("license"):
            errors.append(f"person.jsonld DataDownload license drift for: {key}")
        if download.get("isAccessibleForFree") is not True:
            errors.append(f"person.jsonld DataDownload must be marked isAccessibleForFree for: {key}")
        if download.get("isPartOf", {}).get("@id") != pages_dataset_id:
            errors.append(f"person.jsonld DataDownload isPartOf drift for: {key}")
        if download.get("about", {}).get("@id") != person_id:
            errors.append(f"person.jsonld DataDownload about drift for: {key}")
    repo = data.get("machineReadable", {}).get("repo", {})
    expected_content_works = {
        f"{GITHUB_BLOB}/llms-index.json#creativework": (repo.get("llmsIndexJson"), "application/json"),
        f"{GITHUB_BLOB}/public/FAQ.md#creativework": (repo.get("faqMd"), "text/markdown"),
        f"{GITHUB_BLOB}/public/PROOF.md#creativework": (repo.get("proofMd"), "text/markdown"),
        f"{GITHUB_BLOB}/public/RECRUITER.md#creativework": (repo.get("recruiterMd"), "text/markdown"),
        f"{GITHUB_BLOB}/public/STACK.md#creativework": (repo.get("stackMd"), "text/markdown"),
        f"{GITHUB_BLOB}/public/schema/llms-index.schema.json#creativework": (
            repo.get("schemaIndex"),
            "application/schema+json",
        ),
    }
    for node_id, (url, encoding) in expected_content_works.items():
        work = node_by_id(person_schema, node_id)
        if not work or "CreativeWork" not in node_types(work):
            errors.append(f"person.jsonld missing CreativeWork node: {node_id}")
            continue
        if work.get("url") != url:
            errors.append(f"person.jsonld CreativeWork url drift for: {node_id}")
        if work.get("encodingFormat") != encoding:
            errors.append(f"person.jsonld CreativeWork encodingFormat drift for: {node_id}")
        if work.get("dateModified") != data.get("updated"):
            errors.append(f"person.jsonld CreativeWork dateModified drift for: {node_id}")
        if work.get("license") != data.get("license"):
            errors.append(f"person.jsonld CreativeWork license drift for: {node_id}")
        if work.get("isAccessibleForFree") is not True:
            errors.append(f"person.jsonld CreativeWork must be marked isAccessibleForFree for: {node_id}")
        if work.get("author", {}).get("@id") != person_id:
            errors.append(f"person.jsonld CreativeWork author drift for: {node_id}")
        if work.get("about", {}).get("@id") != person_id:
            errors.append(f"person.jsonld CreativeWork about drift for: {node_id}")
    breadcrumb = node_by_id(person_schema, pages_breadcrumb_id)
    if not breadcrumb or "BreadcrumbList" not in node_types(breadcrumb):
        errors.append("person.jsonld missing GitHub Pages BreadcrumbList node")
    else:
        items = breadcrumb.get("itemListElement", [])
        if not isinstance(items, list) or len(items) < 2:
            errors.append("person.jsonld Pages BreadcrumbList must contain portfolio and Pages items")
        else:
            if items[0].get("item") != data.get("canonical", {}).get("portfolio"):
                errors.append("person.jsonld Pages BreadcrumbList portfolio item drift")
            if items[1].get("item") != pages.get("home"):
                errors.append("person.jsonld Pages BreadcrumbList Pages item drift")

    faq_id = data.get("identifiers", {}).get("faqDocument")
    faq_page = node_by_id(faq_schema, faq_id)
    if not faq_page or "FAQPage" not in node_types(faq_page):
        errors.append("faq.jsonld missing FAQPage node matching identifiers.faqDocument")
    else:
        if faq_page.get("dateModified") != data.get("updated"):
            errors.append("faq.jsonld FAQPage dateModified drift")
        if faq_page.get("author", {}).get("@id") != person_id:
            errors.append("faq.jsonld FAQPage author drift")
        if faq_page.get("about", {}).get("@id") != person_id:
            errors.append("faq.jsonld FAQPage about drift")
        if faq_page.get("inLanguage") != "en":
            errors.append("faq.jsonld FAQPage inLanguage must be en")

    question_nodes = [node for node in graph_nodes(faq_schema) if "Question" in node_types(node)]
    if len(question_nodes) < len(questions):
        errors.append(f"faq.jsonld has {len(question_nodes)} Question nodes; FAQ.md has {len(questions)}")
    question_by_id = {node.get("@id", ""): node for node in question_nodes}
    question_ids = set(question_by_id)
    for question in data.get("aeo", {}).get("answerSnippets", []):
        expected = faq_question_id(faq_id, question.get("question", ""))
        if expected not in question_ids:
            errors.append(f"faq.jsonld missing Question node: {expected}")
            continue
        question_node = question_by_id[expected]
        if question_node.get("url") != expected:
            errors.append(f"faq.jsonld Question url drift for: {question.get('question')}")
        if question_node.get("about", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Question about drift for: {question.get('question')}")
        if question_node.get("inLanguage") != "en":
            errors.append(f"faq.jsonld Question inLanguage must be en for: {question.get('question')}")
        if question_node.get("dateModified") != data.get("updated"):
            errors.append(f"faq.jsonld Question dateModified drift for: {question.get('question')}")
        accepted_answer = question_node.get("acceptedAnswer", {})
        if not isinstance(accepted_answer, dict):
            errors.append(f"faq.jsonld Question missing acceptedAnswer: {expected}")
            continue
        if accepted_answer.get("text") != question.get("answer"):
            errors.append(f"faq.jsonld answer drift for: {question.get('question')}")
        if accepted_answer.get("author", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Answer author drift for: {question.get('question')}")
        if accepted_answer.get("about", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Answer about drift for: {question.get('question')}")
        if accepted_answer.get("inLanguage") != "en":
            errors.append(f"faq.jsonld Answer inLanguage must be en for: {question.get('question')}")
        if accepted_answer.get("dateModified") != data.get("updated"):
            errors.append(f"faq.jsonld Answer dateModified drift for: {question.get('question')}")
        expected_citations = set(question.get("sources", []))
        answer_citations = accepted_answer.get("citation", [])
        if isinstance(answer_citations, str):
            answer_citations = [answer_citations]
        if set(answer_citations) != expected_citations:
            errors.append(f"faq.jsonld citation drift for: {question.get('question')}")

    project_nodes = {node.get("@id", ""): node for node in graph_nodes(person_schema)}
    for project in data.get("featuredProjects", []):
        expected = f"{project.get('caseStudy')}#project"
        project_node = project_nodes.get(expected)
        if not project_node:
            errors.append(f"person.jsonld missing featured project node: {project.get('name')}")
            continue
        if "CreativeWork" not in node_types(project_node):
            errors.append(f"person.jsonld featured project node must be CreativeWork: {project.get('name')}")
        if project_node.get("url") != project.get("caseStudy"):
            errors.append(f"person.jsonld featured project url drift: {project.get('name')}")
        if project_node.get("description") != project.get("focus"):
            errors.append(f"person.jsonld featured project description drift: {project.get('name')}")
        if project_node.get("creator", {}).get("@id") != person_id:
            errors.append(f"person.jsonld featured project creator drift: {project.get('name')}")
        if project_node.get("author", {}).get("@id") != person_id:
            errors.append(f"person.jsonld featured project author drift: {project.get('name')}")
        if project_node.get("about", {}).get("@id") != person_id:
            errors.append(f"person.jsonld featured project about drift: {project.get('name')}")
        if project_node.get("inLanguage") != "en":
            errors.append(f"person.jsonld featured project inLanguage must be en: {project.get('name')}")
        if project_node.get("dateModified") != data.get("updated"):
            errors.append(f"person.jsonld featured project dateModified drift: {project.get('name')}")
        if project_node.get("isAccessibleForFree") is not True:
            errors.append(f"person.jsonld featured project must be marked isAccessibleForFree: {project.get('name')}")


def sitemap_entries() -> list[dict[str, str]]:
    if not SITEMAP.exists():
        errors.append("Missing sitemap.xml")
        return []
    try:
        tree = ET.parse(SITEMAP)
    except ET.ParseError as exc:
        errors.append(f"Invalid sitemap.xml: {exc}")
        return []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries: list[dict[str, str]] = []
    for url in tree.findall(".//sm:url", ns):
        entries.append(
            {
                "loc": (url.findtext("sm:loc", default="", namespaces=ns) or ""),
                "lastmod": (url.findtext("sm:lastmod", default="", namespaces=ns) or ""),
                "changefreq": (url.findtext("sm:changefreq", default="", namespaces=ns) or ""),
                "priority": (url.findtext("sm:priority", default="", namespaces=ns) or ""),
            }
        )
    return entries


def check_crawl_files(data: dict[str, Any]) -> None:
    robots = ROBOTS.read_text(encoding="utf-8") if ROBOTS.exists() else ""
    if not robots:
        errors.append("Missing robots.txt")
    updated = str(data.get("updated", ""))
    if f"# Last updated: {updated}" not in robots:
        errors.append("robots.txt Last updated comment must match llms-index.json updated")
    for agent in ("OAI-SearchBot", "GPTBot", "Google-Extended", "Claude-SearchBot", "PerplexityBot"):
        if f"User-agent: {agent}" not in robots:
            errors.append(f"robots.txt missing explicit user-agent: {agent}")
    if "Sitemap:" not in robots:
        errors.append("robots.txt missing Sitemap directive")
    if f"Sitemap: {GITHUB_RAW}/sitemap.xml" in robots:
        errors.append("robots.txt must not advertise raw GitHub sitemap; use the host-specific Pages sitemap")
    if f"Sitemap: {PAGES}/sitemap.xml" not in robots:
        errors.append("robots.txt missing GitHub Pages sitemap directive")
    sitemap_text = SITEMAP.read_text(encoding="utf-8") if SITEMAP.exists() else ""
    if 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"' not in sitemap_text:
        errors.append("sitemap.xml missing Google image sitemap namespace")

    entries = sitemap_entries()
    locs = {entry["loc"] for entry in entries}
    expected_sitemap_entries = [
        {
            "loc": f"{PAGES}/{path}" if path else f"{PAGES}/",
            "lastmod": updated,
            "changefreq": changefreq,
            "priority": priority,
        }
        for path, changefreq, priority in PAGES_SITEMAP_ENTRIES
    ]
    if entries != expected_sitemap_entries:
        errors.append("sitemap.xml entries must match build_pages_mirror.PAGES_SITEMAP_ENTRIES and llms-index.json updated")
    fragment_locs = sorted(loc for loc in locs if "#" in loc)
    if fragment_locs:
        errors.append(f"sitemap.xml must not contain fragment URL(s): {fragment_locs}")
    non_pages_locs = sorted(
        loc
        for loc in locs
        if urlparse(loc).netloc != PAGES_HOST or not urlparse(loc).path.startswith("/Iron-Mark/")
    )
    if non_pages_locs:
        errors.append(f"sitemap.xml must contain only GitHub Pages URLs: {non_pages_locs}")
    required_locs = {
        f"{PAGES}/",
        f"{PAGES}/llms.txt",
        f"{PAGES}/llms-index.json",
        f"{PAGES}/FAQ.md",
        f"{PAGES}/RECRUITER.md",
        f"{PAGES}/PROOF.md",
        f"{PAGES}/STACK.md",
        f"{PAGES}/PROFILE.md",
        f"{PAGES}/README.md",
        f"{PAGES}/HOW-TO-CITE.md",
        f"{PAGES}/LICENSE.md",
        f"{PAGES}/CITATION.cff",
        f"{PAGES}/schema/llms-index.schema.json",
        f"{PAGES}/schema/person.jsonld",
        f"{PAGES}/schema/faq.jsonld",
        f"{PAGES}/humans.txt",
        f"{PAGES}/robots.txt",
    }
    missing = sorted(required_locs - locs)
    if missing:
        errors.append(f"sitemap.xml missing schema URL(s): {missing}")

    try:
        sitemap = ET.parse(SITEMAP)
        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }
        root_url = next(
            (url for url in sitemap.findall(".//sm:url", ns) if url.findtext("sm:loc", default="", namespaces=ns) == f"{PAGES}/"),
            None,
        )
        image = root_url.find("image:image", ns) if root_url is not None else None
        if image is None:
            errors.append("sitemap.xml root URL missing primary image sitemap entry")
        else:
            if image.findtext("image:loc", default="", namespaces=ns) != PAGES_PRIMARY_IMAGE:
                errors.append("sitemap.xml primary image loc drift")
            deprecated_image_tags = [
                tag
                for tag in ("caption", "geo_location", "title", "license")
                if image.find(f"image:{tag}", ns) is not None
            ]
            if deprecated_image_tags:
                errors.append(f"sitemap.xml must not use deprecated image sitemap tags: {deprecated_image_tags}")
    except ET.ParseError:
        pass


def main() -> int:
    if not INDEX.exists():
        errors.append("llms-index.json not found")
        return 1

    data = load_json(INDEX)
    readme = README.read_text(encoding="utf-8") if README.exists() else ""

    check_required_index_keys(data)
    check_seo_geo_consistency(data)
    check_projects(data, readme)
    check_readme_assets(readme)
    check_people_first_search_signals(readme)
    if enforce_production_readme_surface():
        check_readme_public_surface(readme)
        check_public_surface()
    check_pages_index_visible_content(data)
    questions = faq_questions()
    check_aeo_coverage(data, questions)
    check_knowledge_graph(data)
    check_generated_context(data)
    check_schema(data, questions)
    check_crawl_files(data)

    mcp_readme = ROOT / "src" / "mcp-server" / "README.md"
    mcp_server = ROOT / "src" / "mcp-server" / "iron_mark_profile" / "server.py"
    if not mcp_readme.exists() or not mcp_server.exists():
        warnings.append("MCP server files missing under src/mcp-server/")

    if not (PUBLIC / "STACK.md").exists():
        errors.append("Missing public/STACK.md")

    print("validate_index.py")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  WARN {warning}")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  ERROR {error}")
        return 1
    print("\nOK - no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
