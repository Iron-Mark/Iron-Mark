#!/usr/bin/env python3
"""Validate SEO/AEO/GEO index, schema, crawl, and asset consistency."""

from __future__ import annotations

import hashlib
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
from build_pages_mirror import (
    PAGES_PRIMARY_IMAGE,
    PAGES_SITEMAP_ENTRIES,
    featured_project_cover_urls,
    project_cover_asset,
)
from generate_schema import (
    DATASET_DATE_PUBLISHED,
    PROVIDE_SERVICE_BUSINESS_FUNCTION,
    SERVICE_PROVIDER_MOBILITY,
    data_catalog_description,
    data_catalog_name,
    dataset_alternate_names,
    dataset_measurement_techniques,
    dataset_temporal_coverage,
    download_description,
    download_integrity_metadata,
    faq_document_identifier,
    faq_item_identifier,
    featured_projects_list_description,
    lab_projects_list_description,
    offer_description,
    pages_section_id,
    pages_section_nav_item_id,
    pages_section_navigation_id,
    pages_section_relation_ids,
    pages_section_specs,
    person_occupations,
    person_work_locations,
    primary_image_description,
    profile_page_part_ids,
    profile_keywords,
    project_image_description,
    service_audience,
    service_description,
    service_focus_identifier,
)
from generate_portfolio_sync import (
    FAQ_CROSSLINKS_PATH,
    LLMS_SNIPPET_PATH,
    render_faq_crosslinks,
    render_llms_snippet,
)

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
FAVICON = ROOT / "assets" / "brand" / "mark-siazon-favicon.svg"
SOCIAL_IMAGE_ASSET = ROOT / "assets" / "brand" / "mark-siazon-product-design-full-stack-profile-banner.png"

GITHUB_RAW = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
PAGES = "https://iron-mark.github.io/Iron-Mark"
PAGES_HOST = "iron-mark.github.io"
PAGES_SITE_NAME = "Mark Siazon Profile Index"
PAGES_SITE_ALTERNATE_NAMES = {"Iron-Mark Profile Index", "Mark Siazon GitHub Profile Index"}
PAGES_SOCIAL_IMAGE = f"{PAGES}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.png"
SOCIAL_IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
SOCIAL_IMAGE_WIDTH = 1200
SOCIAL_IMAGE_HEIGHT = 675
OPEN_GRAPH_LOCALE = "en_US"
FAVICON_HREF = "assets/brand/mark-siazon-favicon.svg"
ABSTRACT_REQUIRED_TYPES = {
    "CollectionPage",
    "CreativeWork",
    "DataCatalog",
    "Dataset",
    "FAQPage",
    "ProfilePage",
    "WebSite",
    "WebPageElement",
    "SiteNavigationElement",
}
DATASET_SEARCH_TYPES = {"DataCatalog", "Dataset", "DataDownload"}
DATASET_TEXT_MIN_CHARS = 50
DATASET_TEXT_MAX_CHARS = 5000
DATASET_URL_PROPERTIES_BY_TYPE = {
    "DataCatalog": ("url", "isBasedOn", "license", "usageInfo", "publishingPrinciples", "sdLicense"),
    "Dataset": ("url", "sameAs", "isBasedOn", "license", "usageInfo", "publishingPrinciples", "sdLicense"),
    "DataDownload": (
        "url",
        "contentUrl",
        "isBasedOn",
        "license",
        "usageInfo",
        "publishingPrinciples",
        "sdLicense",
    ),
}
JSONLD_URL_VALUE_KEYS = {
    "@id",
    "url",
    "contentUrl",
    "sameAs",
    "mainEntityOfPage",
    "isBasedOn",
    "license",
    "usageInfo",
    "publishingPrinciples",
    "sdLicense",
    "significantLink",
    "relatedLink",
    "citation",
    "thumbnailUrl",
    "urlTemplate",
    "serviceUrl",
    "acquireLicensePage",
    "item",
    "actionPlatform",
    "businessFunction",
}
PROJECT_IMAGE_ENCODING = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}
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
PRODUCTION_SURFACE_FORBIDDEN_PATTERNS = {
    "po" + r"st[- ]merge": "post-merge workflow notes",
    "po" + r"st[- ]deployment": "post-deployment workflow notes",
    "po" + r"st[- ]deploy": "post-deploy workflow notes",
    r"after\s+deploy(?:ment)?": "after-deploy workflow notes",
    r"dev\s+branch": "development branch notes",
    r"development\s+branch": "development branch notes",
    r"deploy(?:ment)?\s+notes?": "deployment notes",
    r"repo\s+setup": "repo setup notes",
    r"maintenance\s+scripts?": "maintenance script notes",
    r"optional\s+local": "optional local tooling notes",
    r"internal\s+maintain(?:er|ance)": "internal maintainer notes",
}

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


def check_jsonld_graph_integrity(doc: dict[str, Any], label: str) -> None:
    if doc.get("@context") != "https://schema.org":
        errors.append(f"{label} must declare Schema.org @context")
    graph = doc.get("@graph")
    if not isinstance(graph, list) or not graph:
        errors.append(f"{label} must contain a non-empty @graph")
        return

    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []
    for position, node in enumerate(graph, start=1):
        if not isinstance(node, dict):
            errors.append(f"{label} @graph item #{position} must be an object")
            continue
        node_id = node.get("@id")
        if not isinstance(node_id, str) or not node_id:
            errors.append(f"{label} @graph item #{position} missing stable @id")
        elif node_id in seen_ids:
            duplicate_ids.append(node_id)
        else:
            seen_ids.add(node_id)
        raw_type = node.get("@type")
        if not isinstance(raw_type, str) and not (
            isinstance(raw_type, list) and any(isinstance(item, str) and item for item in raw_type)
        ):
            errors.append(f"{label} @graph item #{position} missing @type")
    if duplicate_ids:
        errors.append(f"{label} contains duplicate @id values: {sorted(set(duplicate_ids))}")


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
            check_jsonld_graph_integrity(doc, f"{surface} JSON-LD script #{index}")
            script_nodes = graph_nodes(doc)
            for node in script_nodes:
                check_jsonld_absolute_url_values(node, f"{surface} JSON-LD script #{index}")
            nodes.extend(script_nodes)
        elif isinstance(doc, dict):
            check_jsonld_absolute_url_values(doc, f"{surface} JSON-LD script #{index}")
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


def has_english_knows_language(node: dict[str, Any]) -> bool:
    languages = node.get("knowsLanguage", [])
    if isinstance(languages, dict):
        languages = [languages]
    if not isinstance(languages, list):
        return False
    return any(
        isinstance(language, dict)
        and language.get("@type") == "Language"
        and language.get("alternateName") == "en"
        and language.get("name") == "English"
        for language in languages
    )


def node_ref_ids(values: Any) -> set[str]:
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        return set()
    return {item.get("@id", "") for item in values if isinstance(item, dict) and item.get("@id")}


def unique_compact(values: list[str | None]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return output


def item_list_ref_ids(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    refs: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            continue
        ref_value = item.get("item", {})
        if isinstance(ref_value, dict) and ref_value.get("@id"):
            refs.add(ref_value["@id"])
    return refs


def item_list_urls(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {
        item["url"]
        for item in values
        if isinstance(item, dict) and isinstance(item.get("url"), str)
    }


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


def pages_rewrite_public_source(source: str) -> str:
    replacements = (
        (f"{GITHUB_BLOB}/public/schema/", f"{PAGES}/schema/"),
        (f"{GITHUB_BLOB}/public/", f"{PAGES}/"),
        (f"{GITHUB_RAW}/public/schema/", f"{PAGES}/schema/"),
        (f"{GITHUB_RAW}/public/", f"{PAGES}/"),
    )
    for prefix, replacement in replacements:
        if source.startswith(prefix):
            return source.replace(prefix, replacement, 1)
    return source


def area_names(values: Any) -> set[str]:
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        return set()
    return {item.get("name", "") for item in values if isinstance(item, dict) and item.get("name")}


def expected_area_nodes(regions: list[str]) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    for region in regions:
        region_lower = region.lower()
        if region_lower == "philippines":
            nodes.append({"@type": "Country", "name": "Philippines"})
        elif "remote" in region_lower:
            nodes.append({"@type": "VirtualLocation", "name": region})
        else:
            nodes.append({"@type": "AdministrativeArea", "name": region})
    return nodes


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


def expected_download_sources(repo: dict[str, str]) -> dict[str, str]:
    key_map = {
        "llms-index-json": "llmsIndexJson",
        "llms-txt": "llmsTxt",
        "llms-full-txt": "llmsFullTxt",
        "llms-ctx-full-txt": "llmsCtxFullTxt",
        "faq-md": "faqMd",
        "recruiter-md": "recruiterMd",
        "proof-md": "proofMd",
        "stack-md": "stackMd",
        "profile-md": "profileMd",
        "readme-md": "readmeMd",
        "how-to-cite-md": "howToCiteMd",
        "license-md": "licenseMd",
        "citation-cff": "citationCff",
        "person-jsonld": "schemaPerson",
        "faq-jsonld": "schemaFaq",
        "schema-json": "schemaIndex",
        "humans-txt": "humansTxt",
        "sitemap-xml": "sitemap",
        "robots-txt": "robots",
    }
    return {download_key: repo.get(repo_key, "") for download_key, repo_key in key_map.items()}


def expected_dataset_measurements(data: dict[str, Any], download_count: int) -> list[dict[str, Any]]:
    area_served = data.get("availability", {}).get("areaServed", [])
    return [
        {
            "@type": "PropertyValue",
            "name": "Person entity identifier",
            "value": data.get("entity", {}).get("@id"),
        },
        {
            "@type": "PropertyValue",
            "name": "Featured project count",
            "value": len(data.get("featuredProjects", [])),
        },
        {
            "@type": "PropertyValue",
            "name": "Hackathon and lab project count",
            "value": len(data.get("hackathonLab", [])),
        },
        {
            "@type": "PropertyValue",
            "name": "Verified achievement count",
            "value": len(data.get("achievements", [])),
        },
        {
            "@type": "PropertyValue",
            "name": "Answer snippet count",
            "value": len(data.get("aeo", {}).get("answerSnippets", [])),
        },
        {
            "@type": "PropertyValue",
            "name": "Primary keyword count",
            "value": len(data.get("seo", {}).get("primaryKeywords", [])),
        },
        {
            "@type": "PropertyValue",
            "name": "Service regions",
            "value": ", ".join(area_served),
        },
        {
            "@type": "PropertyValue",
            "name": "Machine-readable download count",
            "value": download_count,
        },
    ]


def expected_citation_targets(data: dict[str, Any]) -> list[str]:
    repo = data.get("machineReadable", {}).get("repo", {})
    values = (
        data.get("aeo", {}).get("preferredCitationOrder", [])
        + [
            repo.get("howToCiteMd", ""),
            repo.get("citationCff", ""),
        ]
    )
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str) and value and value not in seen:
            output.append(value)
            seen.add(value)
    return output


def expected_mention_ids(data: dict[str, Any], person_fragment_base: str) -> set[str]:
    service_ids = {
        f"{person_fragment_base}service-{slugify(focus)}"
        for focus in data.get("availability", {}).get("focus", [])
    }
    project_ids = {f"{project.get('caseStudy')}#project" for project in data.get("featuredProjects", [])}
    lab_project_ids = {lab_project_id(project) for project in data.get("hackathonLab", []) if lab_project_url(project)}
    return {
        f"{GITHUB_BLOB}/llms-index.json#featured-projects",
        f"{GITHUB_BLOB}/llms-index.json#hackathon-lab",
        f"{person_fragment_base}services",
        *service_ids,
        *project_ids,
        *lab_project_ids,
    }


def expected_profile_disambiguating_description(data: dict[str, Any]) -> str:
    entity = data.get("entity", {})
    return (
        f"{entity.get('name')} is the Philippines-based product designer and full-stack developer "
        "behind the Iron-Mark GitHub profile, marksiazon.dev portfolio, and proof-backed AI, "
        "mobile, Web3, and client web case studies."
    )


def expected_person_identifiers(data: dict[str, Any]) -> list[dict[str, str]]:
    entity = data.get("entity", {})
    canonical = data.get("canonical", {})
    return [
        {
            "@type": "PropertyValue",
            "propertyID": "GitHub username",
            "value": "Iron-Mark",
            "url": "https://github.com/Iron-Mark",
        },
        {
            "@type": "PropertyValue",
            "propertyID": "Canonical portfolio",
            "value": entity.get("url", ""),
            "url": entity.get("url", ""),
        },
        {
            "@type": "PropertyValue",
            "propertyID": "GitHub profile repository",
            "value": "Iron-Mark/Iron-Mark",
            "url": canonical.get("githubProfileReadme", ""),
        },
    ]


def lab_project_url(project: dict[str, Any]) -> str:
    return str(project.get("caseStudy") or project.get("demo") or project.get("live") or project.get("repo") or "")


def lab_project_id(project: dict[str, Any]) -> str:
    return f"{lab_project_url(project)}#project"


def awards_by_project(data: dict[str, Any]) -> dict[str, list[str]]:
    awards: dict[str, list[str]] = {}
    for achievement in data.get("achievements", []):
        project = achievement.get("project")
        title = achievement.get("title")
        if not project or not title:
            continue
        awards.setdefault(project, []).append(title)
    return awards


def profile_significant_links(data: dict[str, Any]) -> list[str]:
    availability = data.get("availability", {})
    canonical = data.get("canonical", {})
    return unique_compact(
        [
            canonical.get("portfolio"),
            availability.get("recruiterBrief"),
            availability.get("contact"),
            canonical.get("proofMatrix"),
            f"{canonical.get('portfolio', '').rstrip('/')}/projects",
            f"{canonical.get('portfolio', '').rstrip('/')}/achievements",
        ]
    )


def profile_related_links(data: dict[str, Any]) -> list[str]:
    repo = data.get("machineReadable", {}).get("repo", {})
    return unique_compact(
        [
            repo.get("llmsIndexJson"),
            repo.get("llmsCtxFullTxt"),
            repo.get("faqMd"),
            repo.get("recruiterMd"),
            repo.get("proofMd"),
            repo.get("schemaPerson"),
            repo.get("schemaFaq"),
            repo.get("schemaIndex"),
        ]
    )


def pages_significant_links(data: dict[str, Any]) -> list[str]:
    pages = data.get("machineReadable", {}).get("pages", {})
    return unique_compact(
        [
            pages.get("llmsIndexJson"),
            pages.get("llmsCtxFullTxt"),
            pages.get("faqMd"),
            pages.get("recruiterMd"),
            pages.get("proofMd"),
            pages.get("schemaPerson"),
        ]
    )


def pages_related_links(data: dict[str, Any]) -> list[str]:
    pages = data.get("machineReadable", {}).get("pages", {})
    return unique_compact(
        [
            pages.get("schemaFaq"),
            pages.get("schemaIndex"),
            pages.get("stackMd"),
            pages.get("profileMd"),
            pages.get("howToCiteMd"),
            pages.get("humansTxt"),
            pages.get("sitemap"),
            pages.get("robots"),
        ]
    )


def answer_dom_id(question: str) -> str:
    return f"answer-{slugify(question)}"


def expected_pages_speakable_selectors(data: dict[str, Any]) -> list[str]:
    selectors = ["#profile-summary"]
    for item in data.get("aeo", {}).get("answerSnippets", [])[:3]:
        question = item.get("question")
        if isinstance(question, str) and question:
            selectors.append(f"#{answer_dom_id(question)}")
    return selectors


def expected_pages_speakable(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "@type": "SpeakableSpecification",
        "@id": f"{PAGES}/#speakable",
        "cssSelector": expected_pages_speakable_selectors(data),
    }


def expected_topic_terms(data: dict[str, Any]) -> list[str]:
    return unique_compact(
        data.get("seo", {}).get("primaryKeywords", [])
        + data.get("availability", {}).get("focus", [])
        + data.get("seo", {}).get("geoTargets", [])
    )


def topic_term_set_id() -> str:
    return f"{PAGES}/#topic-taxonomy"


def topic_term_id(value: str) -> str:
    return f"{PAGES}/#term-{slugify(value)}"


def expected_topic_term_description(data: dict[str, Any], value: str) -> str:
    if value in data.get("seo", {}).get("geoTargets", []):
        return f"Geographic service target for the Mark Siazon profile index: {value}."
    if value in data.get("availability", {}).get("focus", []):
        return f"Service focus for Mark Siazon hiring and collaboration discovery: {value}."
    return f"Primary search and answer-engine topic for the Mark Siazon profile index: {value}."


def check_global_citation(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    if node.get("citation") != expected_citation_targets(data):
        errors.append(f"{label} citation chain drift")


def check_expected_mentions(node: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - node_ref_ids(node.get("mentions")))
    if missing:
        errors.append(f"{label} mentions missing: {missing}")


def check_person_identity_resolution(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    if node.get("disambiguatingDescription") != expected_profile_disambiguating_description(data):
        errors.append(f"{label} disambiguatingDescription drift")
    if node.get("identifier") != expected_person_identifiers(data):
        errors.append(f"{label} identifier drift")
    if node.get("sameAs") != data.get("entity", {}).get("sameAs", []):
        errors.append(f"{label} sameAs drift")
    if node.get("image", {}).get("@id") != f"{PAGES}/#primary-image":
        errors.append(f"{label} image drift")
    if not has_english_knows_language(node):
        errors.append(f"{label} knowsLanguage must include English language node")


def check_creativework_abstract(node: dict[str, Any], label: str) -> None:
    if not (node_types(node) & ABSTRACT_REQUIRED_TYPES):
        return
    description = node.get("description")
    if not isinstance(description, str) or not description:
        return
    if node.get("abstract") != description:
        errors.append(f"{label} abstract must match description")


def is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def check_jsonld_absolute_url_values(node: dict[str, Any], label: str) -> None:
    def check_url_value(value: Any, path: str) -> None:
        if isinstance(value, str):
            if not is_absolute_http_url(value):
                errors.append(f"{label} {path} must be an absolute HTTP(S) URL")
            return
        if isinstance(value, dict):
            if isinstance(value.get("@id"), str):
                check_url_value(value["@id"], f"{path}.@id")
            else:
                walk(value, path)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                check_url_value(item, f"{path}[{index}]")
            return
        errors.append(f"{label} {path} must be an absolute HTTP(S) URL")

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else key
                if key in JSONLD_URL_VALUE_KEYS:
                    check_url_value(child, child_path)
                else:
                    walk(child, child_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(node, "")


def check_dataset_search_metadata(node: dict[str, Any], label: str) -> None:
    types = node_types(node) & DATASET_SEARCH_TYPES
    if not types:
        return
    name = node.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{label} must expose a non-empty name")
    elif len(name) > DATASET_TEXT_MAX_CHARS:
        errors.append(f"{label} name must stay within {DATASET_TEXT_MAX_CHARS} characters")
    for key in ("description", "abstract"):
        value = node.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} must expose a non-empty {key}")
            continue
        if len(value) < DATASET_TEXT_MIN_CHARS:
            errors.append(f"{label} {key} must be at least {DATASET_TEXT_MIN_CHARS} characters")
        if len(value) > DATASET_TEXT_MAX_CHARS:
            errors.append(f"{label} {key} must stay within {DATASET_TEXT_MAX_CHARS} characters")
    required_url_properties = set()
    for node_type in types:
        required_url_properties.update(DATASET_URL_PROPERTIES_BY_TYPE.get(node_type, ()))
    for key in sorted(required_url_properties):
        value = node.get(key)
        if not isinstance(value, str) or not is_absolute_http_url(value):
            errors.append(f"{label} {key} must be an absolute HTTP(S) URL")


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
        if schema.get("uniqueItems") is True:
            seen: set[str] = set()
            duplicates: list[str] = []
            for item in value:
                key = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if key in seen:
                    duplicates.append(key)
                seen.add(key)
            if duplicates:
                errors.append(f"{path} must contain unique items; duplicate(s): {duplicates}")
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
    if not project_cover_asset(slug):
        errors.append(f"Missing featured project cover: assets/projects/{slug}/cover.(webp|png|svg)")


def file_integrity_metadata(path: Path) -> dict[str, str]:
    if path.suffix.lower() == ".svg":
        data = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    else:
        data = path.read_bytes()
    return {
        "contentSize": f"{len(data)} bytes",
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def expected_project_image(project: dict[str, Any]) -> dict[str, str] | None:
    asset = project_cover_asset(str(project.get("slug", "")))
    if not asset:
        return None
    url = f"{PAGES}/{asset}"
    return {
        "@id": f"{url}#image",
        "url": url,
        "encodingFormat": PROJECT_IMAGE_ENCODING.get(Path(asset).suffix, ""),
        **file_integrity_metadata(ROOT / asset),
    }


def check_image_rights(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    entity = data.get("entity", {})
    pages = data.get("machineReadable", {}).get("pages", {})
    availability = data.get("availability", {})
    expected_creator_id = entity.get("@id")
    expected_name = entity.get("name")
    if node.get("license") != pages.get("licenseMd"):
        errors.append(f"{label} license drift")
    if node.get("usageInfo") != pages.get("licenseMd"):
        errors.append(f"{label} usageInfo drift")
    if node.get("acquireLicensePage") != availability.get("contact"):
        errors.append(f"{label} acquireLicensePage drift")
    if node.get("creditText") != expected_name:
        errors.append(f"{label} creditText drift")
    if node.get("copyrightNotice") != f"Copyright {expected_name}":
        errors.append(f"{label} copyrightNotice drift")
    creator = node.get("creator", {})
    if not isinstance(creator, dict):
        errors.append(f"{label} creator must be a Person object")
        return
    if creator.get("@id") != expected_creator_id:
        errors.append(f"{label} creator @id drift")
    if creator.get("@type") != "Person":
        errors.append(f"{label} creator must be Person")
    if creator.get("name") != expected_name:
        errors.append(f"{label} creator name drift")
    if creator.get("url") != entity.get("url"):
        errors.append(f"{label} creator url drift")
    check_publisher_metadata(node, data, label)
    check_ownership_metadata(node, data, label)
    check_structured_data_provenance(node, data, label)


def png_dimensions(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        errors.append(f"Missing PNG image asset: {path.relative_to(ROOT)}")
        return None
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        errors.append(f"Image asset must be PNG: {path.relative_to(ROOT)}")
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def check_content_usage_policy(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    repo = data.get("machineReadable", {}).get("repo", {})
    if node.get("usageInfo") != repo.get("howToCiteMd"):
        errors.append(f"{label} usageInfo drift")
    if node.get("publishingPrinciples") != repo.get("proofMd"):
        errors.append(f"{label} publishingPrinciples drift")


def check_structured_data_provenance(
    node: dict[str, Any],
    data: dict[str, Any],
    label: str,
    expected_license: str | None = None,
) -> None:
    entity = data.get("entity", {})
    publisher = node.get("sdPublisher", {})
    if not isinstance(publisher, dict):
        errors.append(f"{label} missing sdPublisher Person object")
        return
    if publisher.get("@type") != "Person":
        errors.append(f"{label} sdPublisher must be Person")
    if publisher.get("@id") != entity.get("@id"):
        errors.append(f"{label} sdPublisher @id drift")
    if publisher.get("name") != entity.get("name"):
        errors.append(f"{label} sdPublisher name drift")
    if publisher.get("url") != entity.get("url"):
        errors.append(f"{label} sdPublisher url drift")
    if node.get("sdDatePublished") != data.get("updated"):
        errors.append(f"{label} sdDatePublished drift")
    if node.get("sdLicense") != (expected_license or data.get("license")):
        errors.append(f"{label} sdLicense drift")


def check_ownership_metadata(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    person_id = data.get("entity", {}).get("@id")
    if node.get("accountablePerson", {}).get("@id") != person_id:
        errors.append(f"{label} accountablePerson drift")
    if node.get("copyrightHolder", {}).get("@id") != person_id:
        errors.append(f"{label} copyrightHolder drift")
    expected_year = int(str(data.get("updated", "0000"))[:4])
    if node.get("copyrightYear") != expected_year:
        errors.append(f"{label} copyrightYear drift")


def check_publisher_metadata(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    person_id = data.get("entity", {}).get("@id")
    if node.get("publisher", {}).get("@id") != person_id:
        errors.append(f"{label} publisher drift")


def check_review_metadata(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    person_id = data.get("entity", {}).get("@id")
    if node.get("reviewedBy", {}).get("@id") != person_id:
        errors.append(f"{label} reviewedBy drift")
    if node.get("lastReviewed") != data.get("updated"):
        errors.append(f"{label} lastReviewed drift")


def check_spatial_coverage(node: dict[str, Any], data: dict[str, Any], label: str) -> None:
    expected = expected_area_nodes(data.get("availability", {}).get("areaServed", []))
    if node.get("spatialCoverage") != expected:
        errors.append(f"{label} spatialCoverage typed region drift")


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
    for pattern, reason in PRODUCTION_SURFACE_FORBIDDEN_PATTERNS.items():
        if re.search(pattern, lower):
            errors.append(f"README.md contains {reason}")


def check_public_surface() -> None:
    surfaces = {
        "README.md": README,
        "humans.txt": ROOT / "humans.txt",
        "llms.txt": ROOT / "llms.txt",
        "docs/index.html": DOCS_INDEX,
        "sitemap.xml": SITEMAP,
        "robots.txt": ROBOTS,
    }
    for name, path in surfaces.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for needle, reason in PRODUCTION_SURFACE_FORBIDDEN_LINKS.items():
            if needle.lower() in lower:
                errors.append(f"{name} exposes {reason}: {needle}")
        for pattern, reason in PRODUCTION_SURFACE_FORBIDDEN_PATTERNS.items():
            if re.search(pattern, lower):
                errors.append(f"{name} contains {reason}")
    for name in ("llms.txt", "humans.txt", "robots.txt"):
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        non_ascii = sorted({f"U+{ord(char):04X}" for char in text if ord(char) > 127})
        if non_ascii:
            errors.append(f"{name} must stay ASCII-only for plain-text crawler compatibility: {non_ascii}")


def check_pages_index_visible_content(data: dict[str, Any]) -> None:
    if not DOCS_INDEX.exists():
        errors.append("Missing docs/index.html")
        return
    raw_html = DOCS_INDEX.read_text(encoding="utf-8")
    html = unescape(raw_html)
    updated = str(data.get("updated", ""))
    if f'<meta name="date" content="{updated}"/>' not in html:
        errors.append("docs/index.html meta date must match llms-index.json updated")
    expected_modified_tags = {
        f'<meta property="og:updated_time" content="{updated}"/>',
        f'<meta property="article:modified_time" content="{updated}"/>',
        f'<meta itemprop="dateModified" content="{updated}"/>',
    }
    for tag in expected_modified_tags:
        if tag not in html:
            errors.append(f"docs/index.html missing modified-time metadata: {tag}")
    if f"Updated {updated}." not in html:
        errors.append("docs/index.html visible updated date must match llms-index.json updated")
    if '<main id="main-content">' not in html:
        errors.append("docs/index.html main content must expose #main-content")
    if '<nav id="section-navigation" class="section-nav" aria-label="Profile index sections">' not in html:
        errors.append("docs/index.html must expose visible section navigation")
    if f'<link rel="canonical" href="{PAGES}/"/>' not in html:
        errors.append("docs/index.html canonical must point to the GitHub Pages mirror")
    expected_hreflangs = {
        f'<link rel="alternate" hreflang="en" href="{PAGES}/"/>',
        f'<link rel="alternate" hreflang="x-default" href="{PAGES}/"/>',
    }
    for tag in expected_hreflangs:
        if tag not in html:
            errors.append(f"docs/index.html missing self-referencing hreflang link: {tag}")
    if f'<meta property="og:locale" content="{OPEN_GRAPH_LOCALE}"/>' not in html:
        errors.append("docs/index.html missing Open Graph locale metadata")
    expected_site_name_tags = {
        f"<title>{PAGES_SITE_NAME}</title>",
        f'<meta property="og:title" content="{PAGES_SITE_NAME}"/>',
        f'<meta property="og:site_name" content="{PAGES_SITE_NAME}"/>',
        f'<meta name="twitter:title" content="{PAGES_SITE_NAME}"/>',
        f"<h1>{PAGES_SITE_NAME}</h1>",
    }
    for tag in expected_site_name_tags:
        if tag not in html:
            errors.append(f"docs/index.html site-name signal drift: {tag}")
    if 'aria-label="Breadcrumb"' not in html:
        errors.append("docs/index.html missing visible breadcrumb navigation")
    if f'<a href="{data.get("canonical", {}).get("portfolio")}">Mark Siazon Portfolio</a> / <span>{PAGES_SITE_NAME}</span>' not in html:
        errors.append("docs/index.html visible breadcrumb must match BreadcrumbList")
    if f'<link rel="icon" type="image/svg+xml" href="{FAVICON_HREF}"/>' not in html:
        errors.append("docs/index.html missing SVG favicon link")
    favicon = FAVICON.read_text(encoding="utf-8") if FAVICON.exists() else ""
    if not favicon:
        errors.append("missing SVG favicon asset")
    elif 'viewBox="0 0 96 96"' not in favicon:
        errors.append("SVG favicon must declare a square viewBox")
    expected_image_tags = {
        f'<meta property="og:image" content="{PAGES_SOCIAL_IMAGE}"/>',
        f'<meta property="og:image:secure_url" content="{PAGES_SOCIAL_IMAGE}"/>',
        '<meta property="og:image:type" content="image/png"/>',
        f'<meta property="og:image:width" content="{SOCIAL_IMAGE_WIDTH}"/>',
        f'<meta property="og:image:height" content="{SOCIAL_IMAGE_HEIGHT}"/>',
        f'<meta property="og:image:alt" content="{SOCIAL_IMAGE_ALT}"/>',
        f'<meta name="twitter:image" content="{PAGES_SOCIAL_IMAGE}"/>',
        f'<meta name="twitter:image:alt" content="{SOCIAL_IMAGE_ALT}"/>',
    }
    for tag in expected_image_tags:
        if tag not in html:
            errors.append(f"docs/index.html missing social image metadata: {tag}")
    if png_dimensions(SOCIAL_IMAGE_ASSET) != (SOCIAL_IMAGE_WIDTH, SOCIAL_IMAGE_HEIGHT):
        errors.append("primary social image asset dimensions must match metadata")
    if f'<link rel="author" href="{PAGES}/humans.txt"/>' not in html:
        errors.append("docs/index.html missing author link to humans.txt")
    for same_as in data.get("entity", {}).get("sameAs", []):
        if isinstance(same_as, str) and same_as.startswith("https://") and f'<link rel="me" href="{same_as}"/>' not in html:
            errors.append(f"docs/index.html missing rel=me identity link: {same_as}")
    for section in pages_section_specs(data):
        heading_tag = f'<h2 id="{section["fragment"]}">{section["heading"]}</h2>'
        if heading_tag not in html:
            errors.append(f"docs/index.html missing visible anchored section: {heading_tag}")
        section_link = f'<a href="#{section["fragment"]}">{section["heading"]}</a>'
        if section_link not in html:
            errors.append(f"docs/index.html missing section navigation link: {section_link}")
    for selector in expected_pages_speakable_selectors(data):
        if selector.startswith("#") and f'id="{selector[1:]}"' not in html:
            errors.append(f"docs/index.html missing speakable selector target: {selector}")
    required_alternates = {
        f'type="application/json" href="{PAGES}/llms-index.json"',
        f'type="text/plain" href="{PAGES}/llms.txt"',
        f'type="text/plain" href="{PAGES}/llms-full.txt"',
        f'type="text/plain" href="{PAGES}/llms-ctx-full.txt"',
        f'type="text/markdown" href="{PAGES}/FAQ.md"',
        f'type="text/markdown" href="{PAGES}/RECRUITER.md"',
        f'type="text/markdown" href="{PAGES}/PROOF.md"',
        f'type="text/markdown" href="{PAGES}/STACK.md"',
        f'type="text/markdown" href="{PAGES}/PROFILE.md"',
        f'type="text/markdown" href="{PAGES}/README.md"',
        f'type="text/markdown" href="{PAGES}/HOW-TO-CITE.md"',
        f'type="text/markdown" href="{PAGES}/LICENSE.md"',
        f'type="text/plain" href="{PAGES}/CITATION.cff"',
        f'type="text/plain" href="{PAGES}/humans.txt"',
        f'type="application/ld+json" href="{PAGES}/schema/person.jsonld"',
        f'type="application/ld+json" href="{PAGES}/schema/faq.jsonld"',
        f'type="application/schema+json" href="{PAGES}/schema/llms-index.schema.json"',
    }
    for alternate in required_alternates:
        if alternate not in html:
            errors.append(f"docs/index.html missing alternate link: {alternate}")
    required_resource_links = {
        f'<link rel="license" href="{PAGES}/LICENSE.md"/>',
        f'<link rel="sitemap" type="application/xml" href="{PAGES}/sitemap.xml"/>',
    }
    for tag in required_resource_links:
        if tag not in html:
            errors.append(f"docs/index.html missing absolute resource link: {tag}")
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
    inline_faq_node = next(
        (node for node in jsonld_nodes if "FAQPage" in node_types(node) and node.get("@id") == inline_faq_id),
        None,
    )
    if not inline_faq_node:
        errors.append("docs/index.html inline JSON-LD missing FAQPage node")
    elif inline_faq_node.get("identifier") != faq_document_identifier(inline_faq_id):
        errors.append("docs/index.html inline JSON-LD FAQPage identifier drift")
    question_nodes = {node.get("@id", ""): node for node in jsonld_nodes if "Question" in node_types(node)}
    for snippet in data.get("aeo", {}).get("answerSnippets", []):
        expected = faq_question_id(inline_faq_id, snippet.get("question", ""))
        question_node = question_nodes.get(expected)
        if not question_node:
            errors.append(f"docs/index.html inline JSON-LD missing Question node: {expected}")
            continue
        if question_node.get("url") != expected:
            errors.append(f"docs/index.html inline JSON-LD Question url drift for: {snippet.get('question')}")
        if question_node.get("identifier") != faq_item_identifier(expected, "question"):
            errors.append(f"docs/index.html inline JSON-LD Question identifier drift for: {snippet.get('question')}")
        expected_citations = {pages_rewrite_public_source(str(source)) for source in snippet.get("sources", [])}
        question_citations = question_node.get("citation", [])
        if isinstance(question_citations, str):
            question_citations = [question_citations]
        if set(question_citations) != expected_citations:
            errors.append(f"docs/index.html inline JSON-LD Question citation drift for: {snippet.get('question')}")
        answer_node = question_node.get("acceptedAnswer", {})
        if not isinstance(answer_node, dict) or answer_node.get("text") != snippet.get("answer"):
            errors.append(f"docs/index.html inline JSON-LD answer drift for: {snippet.get('question')}")
            continue
        answer_id = f"{expected}-answer"
        if answer_node.get("url") != answer_id:
            errors.append(f"docs/index.html inline JSON-LD Answer url drift for: {snippet.get('question')}")
        if answer_node.get("identifier") != faq_item_identifier(answer_id, "answer"):
            errors.append(f"docs/index.html inline JSON-LD Answer identifier drift for: {snippet.get('question')}")
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
    faq_text = FAQ.read_text(encoding="utf-8") if FAQ.exists() else ""
    if len(snippets) < 15:
        warnings.append(f"Only {len(snippets)} answerSnippets (recommend 15+)")
    snippet_questions = [item.get("question", "") for item in snippets]
    duplicate_questions = sorted(
        {question for question in snippet_questions if question and snippet_questions.count(question) > 1}
    )
    if duplicate_questions:
        errors.append(f"AEO snippets contain duplicate question(s): {duplicate_questions}")
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
        answer = item.get("answer", "")
        if answer and answer not in faq_text:
            errors.append(f"AEO snippet answer missing from visible FAQ.md: {question}")
        relative_refs = re.findall(
            r"(?<![\w:/.-])(?:public/[\w./-]+|schema/[\w./-]+|llms-index\.json|llms\.txt|"
            r"llms-full\.txt|llms-ctx-full\.txt|FAQ\.md|HOW-TO-CITE\.md|STACK\.md|"
            r"person\.jsonld|faq\.jsonld|llms-index\.schema\.json)(?![\w./-])",
            answer,
        )
        if relative_refs:
            errors.append(f"AEO snippet answer must use absolute URLs for {question}: {sorted(set(relative_refs))}")


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
        focus = project.get("focus", "")
        if name:
            required.add((entity_name, "maintains", name))
        if name and focus:
            required.add((name, "focusesOn", focus))

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
    if "## Hackathon and lab projects" not in text:
        errors.append("public/llms-ctx-full.txt missing Hackathon and lab projects section")
    seo = data.get("seo", {})
    geo_signals = seo.get("geoSignals", {})
    generative = seo.get("generativeSearch", {})
    if "## Search and discovery signals" not in text:
        errors.append("public/llms-ctx-full.txt missing Search and discovery signals section")
    expected_search_lines = [
        f"- Primary keywords: {', '.join(seo.get('primaryKeywords', []))}",
        f"- Geo targets: {', '.join(seo.get('geoTargets', []))}",
        f"- Home country: {geo_signals.get('homeCountry', '')}",
        f"- Search modifiers: {', '.join(geo_signals.get('searchModifiers', []))}",
    ]
    for line in expected_search_lines:
        if line not in text:
            errors.append(f"public/llms-ctx-full.txt missing search signal line: {line}")
    if "## Generative search guidance" not in text:
        errors.append("public/llms-ctx-full.txt missing Generative search guidance section")
    for line in (
        f"- Principle: {generative.get('principle', '')}",
        f"- llms.txt role: {generative.get('llmsTxtRole', '')}",
    ):
        if line not in text:
            errors.append(f"public/llms-ctx-full.txt missing generative guidance line: {line}")
    for source in generative.get("answerSources", []):
        if f"- {source}" not in text:
            errors.append(f"public/llms-ctx-full.txt missing generative answer source: {source}")
    for surface in generative.get("agentReadySurfaces", []):
        if f"- {surface}" not in text:
            errors.append(f"public/llms-ctx-full.txt missing agent-ready surface: {surface}")
    if "## Preferred citation order" not in text:
        errors.append("public/llms-ctx-full.txt missing Preferred citation order section")
    for source in data.get("aeo", {}).get("preferredCitationOrder", []):
        if f"- {source}" not in text:
            errors.append(f"public/llms-ctx-full.txt missing preferred citation source: {source}")
    for triple in data.get("triples", []):
        if isinstance(triple, list) and len(triple) == 3:
            line = f"- {triple[0]} | {triple[1]} | {triple[2]}"
            if line not in text:
                errors.append(f"public/llms-ctx-full.txt missing knowledge graph triple: {line}")
    for project in data.get("hackathonLab", []):
        name = project.get("name", "")
        focus = project.get("focus", "")
        if name and f"### {name}" not in text:
            errors.append(f"public/llms-ctx-full.txt missing lab project heading: {name}")
        if focus and f"- Focus: {focus}" not in text:
            errors.append(f"public/llms-ctx-full.txt missing lab project focus: {name}")


def check_portfolio_sync_artifacts(data: dict[str, Any]) -> None:
    expected_artifacts = {
        LLMS_SNIPPET_PATH: render_llms_snippet(data),
        FAQ_CROSSLINKS_PATH: render_faq_crosslinks(data),
    }
    for path, expected in expected_artifacts.items():
        if not path.exists():
            errors.append(f"Missing generated portfolio sync artifact: {path.relative_to(ROOT)}")
            continue
        actual = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if actual != expected.replace("\r\n", "\n"):
            errors.append(f"{path.relative_to(ROOT)} is stale; run src/scripts/generate_portfolio_sync.py")

    snippet = LLMS_SNIPPET_PATH.read_text(encoding="utf-8") if LLMS_SNIPPET_PATH.exists() else ""
    repo = data.get("machineReadable", {}).get("repo", {})
    pages = data.get("machineReadable", {}).get("pages", {})
    required_references = [
        data.get("canonical", {}).get("githubProfileReadme", ""),
        repo.get("llmsIndexJson", ""),
        repo.get("schemaIndex", ""),
        repo.get("faqMd", ""),
        repo.get("stackMd", ""),
        repo.get("schemaPerson", ""),
        repo.get("schemaFaq", ""),
        pages.get("home", ""),
        data.get("entity", {}).get("@id", ""),
    ]
    for reference in required_references:
        if reference and reference not in snippet:
            errors.append(f"portfolio sync llms snippet missing required reference: {reference}")
    for item in data.get("aeo", {}).get("answerSnippets", []):
        question = item.get("question", "")
        if question and question not in snippet:
            errors.append(f"portfolio sync llms snippet missing AEO question: {question}")
        expected_answer_url = f"{repo.get('faqMd', '')}#{slugify(question)}" if question else ""
        if expected_answer_url and expected_answer_url not in snippet:
            errors.append(f"portfolio sync llms snippet missing FAQ answer URL: {expected_answer_url}")


def check_schema(data: dict[str, Any], questions: list[str]) -> None:
    index_schema_path = SCHEMA / "llms-index.schema.json"
    person_path = SCHEMA / "person.jsonld"
    faq_path = SCHEMA / "faq.jsonld"
    index_schema = load_json(index_schema_path)
    person_schema = load_json(person_path)
    faq_schema = load_json(faq_path)
    if not index_schema or not person_schema or not faq_schema:
        return
    check_jsonld_graph_integrity(person_schema, "person.jsonld")
    check_jsonld_graph_integrity(faq_schema, "faq.jsonld")
    for graph_label, graph_doc in (("person.jsonld", person_schema), ("faq.jsonld", faq_schema)):
        for node in graph_nodes(graph_doc):
            node_label = f"{graph_label} {node.get('@id', node.get('name', 'node'))}"
            check_jsonld_absolute_url_values(node, node_label)
    if index_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("llms-index.schema.json must declare JSON Schema draft 2020-12")
    validate_contract_subset(data, index_schema, "llms-index.json")
    required_index_keys = set(index_schema.get("required", []))
    for key in ("updated", "entity", "featuredProjects", "hackathonLab", "seo", "aeo", "triples", "schema"):
        if key not in required_index_keys:
            errors.append(f"llms-index.schema.json missing required key: {key}")
    project_contracts = {
        "featuredProjects": {"name", "slug", "caseStudy", "focus", "live", "repo", "model"},
        "hackathonLab": {"name", "focus", "caseStudy", "repo", "live", "demo", "model"},
        "achievements": {"title", "project", "team", "proof"},
    }
    for key, expected_properties in project_contracts.items():
        item_schema = index_schema.get("properties", {}).get(key, {}).get("items", {})
        actual_properties = set(item_schema.get("properties", {}))
        missing_properties = sorted(expected_properties - actual_properties)
        if missing_properties:
            errors.append(f"llms-index.schema.json {key} item schema missing properties: {missing_properties}")
        if item_schema.get("additionalProperties") is not False:
            errors.append(f"llms-index.schema.json {key} item schema must disallow additionalProperties")
    achievement_required = set(
        index_schema.get("properties", {})
        .get("achievements", {})
        .get("items", {})
        .get("required", [])
    )
    for key in ("title", "project", "proof"):
        if key not in achievement_required:
            errors.append(f"llms-index.schema.json achievements item schema missing required key: {key}")
    machine_readable_schema = index_schema.get("properties", {}).get("machineReadable", {}).get("properties", {})
    machine_readable_contracts = {
        "repo": {
            "llmsTxt",
            "llmsFullTxt",
            "llmsIndexJson",
            "llmsCtxFullTxt",
            "faqMd",
            "recruiterMd",
            "proofMd",
            "profileMd",
            "readmeMd",
            "howToCiteMd",
            "licenseMd",
            "citationCff",
            "schemaPerson",
            "schemaFaq",
            "schemaIndex",
            "humansTxt",
            "stackMd",
            "sitemap",
            "robots",
        },
        "pages": {
            "home",
            "llmsTxt",
            "llmsFullTxt",
            "llmsIndexJson",
            "llmsCtxFullTxt",
            "faqMd",
            "recruiterMd",
            "proofMd",
            "profileMd",
            "readmeMd",
            "howToCiteMd",
            "licenseMd",
            "citationCff",
            "schemaPerson",
            "schemaFaq",
            "schemaIndex",
            "humansTxt",
            "stackMd",
            "sitemap",
            "robots",
        },
        "portfolio": {"llmsTxt", "llmsFullTxt", "humansTxt", "sitemap", "rss", "jsonFeed"},
    }
    for key, expected_properties in machine_readable_contracts.items():
        item_schema = machine_readable_schema.get(key, {})
        actual_properties = set(item_schema.get("properties", {}))
        missing_properties = sorted(expected_properties - actual_properties)
        if missing_properties:
            errors.append(f"llms-index.schema.json machineReadable.{key} schema missing properties: {missing_properties}")
        if item_schema.get("additionalProperties") is not False:
            errors.append(f"llms-index.schema.json machineReadable.{key} schema must disallow additionalProperties")
        for property_name in expected_properties & actual_properties:
            property_schema = item_schema.get("properties", {}).get(property_name, {})
            if property_schema.get("type") != "string" or property_schema.get("format") != "uri":
                errors.append(f"llms-index.schema.json machineReadable.{key}.{property_name} must be a URI string")
    properties_schema = index_schema.get("properties", {})
    expected_top_level_properties = {
        "$schema",
        "version",
        "updated",
        "contentRoot",
        "license",
        "citation",
        "entity",
        "identifiers",
        "availability",
        "canonical",
        "machineReadable",
        "featuredProjects",
        "hackathonLab",
        "achievements",
        "coreStack",
        "stackReference",
        "seo",
        "aeo",
        "triples",
        "schema",
    }
    missing_top_level_properties = sorted(expected_top_level_properties - set(properties_schema))
    if missing_top_level_properties:
        errors.append(f"llms-index.schema.json missing top-level properties: {missing_top_level_properties}")
    if index_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json top-level schema must disallow additionalProperties")

    entity_schema = properties_schema.get("entity", {})
    if entity_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json entity schema must disallow additionalProperties")
    entity_expected_properties = {
        "@type",
        "@id",
        "name",
        "alternateName",
        "jobTitle",
        "description",
        "url",
        "email",
        "sameAs",
        "address",
    }
    entity_actual_properties = set(entity_schema.get("properties", {}))
    missing_entity_properties = sorted(entity_expected_properties - entity_actual_properties)
    if missing_entity_properties:
        errors.append(f"llms-index.schema.json entity schema missing properties: {missing_entity_properties}")
    address_schema = entity_schema.get("properties", {}).get("address", {})
    if address_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json entity.address schema must disallow additionalProperties")
    for key in ("@type", "addressCountry", "addressRegion"):
        if key not in address_schema.get("properties", {}):
            errors.append(f"llms-index.schema.json entity.address schema missing property: {key}")

    identifier_schema = properties_schema.get("identifiers", {})
    identifier_expected_properties = {
        "person",
        "portfolioWebsite",
        "githubProfilePage",
        "githubProfileIndex",
        "githubPagesMirror",
        "faqDocument",
        "structuredIndex",
        "wikidata",
        "wikidataGuide",
        "entityGuide",
        "indexSchema",
        "personSchema",
        "faqSchema",
    }
    identifier_actual_properties = set(identifier_schema.get("properties", {}))
    missing_identifier_properties = sorted(identifier_expected_properties - identifier_actual_properties)
    if missing_identifier_properties:
        errors.append(f"llms-index.schema.json identifiers schema missing properties: {missing_identifier_properties}")
    if identifier_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json identifiers schema must disallow additionalProperties")
    for key in sorted(identifier_expected_properties - {"wikidata"}):
        property_schema = identifier_schema.get("properties", {}).get(key, {})
        if property_schema.get("type") != "string" or property_schema.get("format") != "uri":
            errors.append(f"llms-index.schema.json identifiers.{key} must be a URI string")
    wikidata_schema = identifier_schema.get("properties", {}).get("wikidata", {})
    if set(wikidata_schema.get("type", [])) != {"string", "null"} or wikidata_schema.get("format") != "uri":
        errors.append("llms-index.schema.json identifiers.wikidata must allow a URI string or null")

    availability_schema = properties_schema.get("availability", {})
    availability_expected_properties = {
        "status",
        "focus",
        "engagement",
        "location",
        "areaServed",
        "remote",
        "contact",
        "recruiterBrief",
    }
    availability_actual_properties = set(availability_schema.get("properties", {}))
    missing_availability_properties = sorted(availability_expected_properties - availability_actual_properties)
    if missing_availability_properties:
        errors.append(f"llms-index.schema.json availability schema missing properties: {missing_availability_properties}")
    if availability_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json availability schema must disallow additionalProperties")
    for key in ("contact", "recruiterBrief"):
        property_schema = availability_schema.get("properties", {}).get(key, {})
        if property_schema.get("type") != "string" or property_schema.get("format") != "uri":
            errors.append(f"llms-index.schema.json availability.{key} must be a URI string")

    canonical_schema = properties_schema.get("canonical", {})
    canonical_expected_properties = {"portfolio", "githubProfileReadme", "techStack", "proofMatrix"}
    canonical_actual_properties = set(canonical_schema.get("properties", {}))
    missing_canonical_properties = sorted(canonical_expected_properties - canonical_actual_properties)
    if missing_canonical_properties:
        errors.append(f"llms-index.schema.json canonical schema missing properties: {missing_canonical_properties}")
    if canonical_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json canonical schema must disallow additionalProperties")
    for key in sorted(canonical_expected_properties):
        property_schema = canonical_schema.get("properties", {}).get(key, {})
        if property_schema.get("type") != "string" or property_schema.get("format") != "uri":
            errors.append(f"llms-index.schema.json canonical.{key} must be a URI string")

    stack_reference_schema = properties_schema.get("stackReference", {})
    stack_reference_expected_properties = {"file", "toolCount", "domains"}
    stack_reference_actual_properties = set(stack_reference_schema.get("properties", {}))
    missing_stack_reference_properties = sorted(stack_reference_expected_properties - stack_reference_actual_properties)
    if missing_stack_reference_properties:
        errors.append(f"llms-index.schema.json stackReference schema missing properties: {missing_stack_reference_properties}")
    if stack_reference_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json stackReference schema must disallow additionalProperties")

    schema_object_schema = properties_schema.get("schema", {})
    schema_expected_properties = {
        "context",
        "person",
        "faq",
        "index",
        "pagesPerson",
        "pagesFaq",
        "generatedBy",
        "validatesWith",
    }
    schema_actual_properties = set(schema_object_schema.get("properties", {}))
    missing_schema_properties = sorted(schema_expected_properties - schema_actual_properties)
    if missing_schema_properties:
        errors.append(f"llms-index.schema.json schema object missing properties: {missing_schema_properties}")
    if schema_object_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json schema object must disallow additionalProperties")
    if schema_object_schema.get("properties", {}).get("context", {}).get("const") != "https://schema.org":
        errors.append("llms-index.schema.json schema.context must be https://schema.org")
    for key in ("person", "faq", "index", "pagesPerson", "pagesFaq"):
        property_schema = schema_object_schema.get("properties", {}).get(key, {})
        if property_schema.get("type") != "string" or property_schema.get("format") != "uri":
            errors.append(f"llms-index.schema.json schema.{key} must be a URI string")
    for key in ("generatedBy", "validatesWith"):
        property_schema = schema_object_schema.get("properties", {}).get(key, {})
        if property_schema.get("type") != "string" or property_schema.get("pattern") != r"^src/scripts/[a-z0-9_]+\.py$":
            errors.append(f"llms-index.schema.json schema.{key} must be a src/scripts Python path")

    def schema_property(*keys: str) -> dict[str, Any]:
        node = properties_schema.get(keys[0], {}) if keys else {}
        for key in keys[1:]:
            node = node.get("properties", {}).get(key, {})
        return node if isinstance(node, dict) else {}

    unique_array_contracts = {
        "entity.alternateName": schema_property("entity", "alternateName"),
        "entity.jobTitle": schema_property("entity", "jobTitle"),
        "entity.sameAs": schema_property("entity", "sameAs"),
        "availability.focus": schema_property("availability", "focus"),
        "availability.engagement": schema_property("availability", "engagement"),
        "availability.areaServed": schema_property("availability", "areaServed"),
        "featuredProjects": properties_schema.get("featuredProjects", {}),
        "hackathonLab": properties_schema.get("hackathonLab", {}),
        "achievements": properties_schema.get("achievements", {}),
        "coreStack": properties_schema.get("coreStack", {}),
        "stackReference.domains": schema_property("stackReference", "domains"),
        "seo.primaryKeywords": schema_property("seo", "primaryKeywords"),
        "seo.geoTargets": schema_property("seo", "geoTargets"),
        "seo.technicalSignals.schemaGraphs": schema_property("seo", "technicalSignals", "schemaGraphs"),
        "seo.technicalSignals.sitemaps": schema_property("seo", "technicalSignals", "sitemaps"),
        "seo.technicalSignals.robots": schema_property("seo", "technicalSignals", "robots"),
        "seo.geoSignals.serviceRegions": schema_property("seo", "geoSignals", "serviceRegions"),
        "seo.geoSignals.searchModifiers": schema_property("seo", "geoSignals", "searchModifiers"),
        "seo.generativeSearch.answerSources": schema_property("seo", "generativeSearch", "answerSources"),
        "seo.generativeSearch.agentReadySurfaces": schema_property("seo", "generativeSearch", "agentReadySurfaces"),
        "aeo.preferredCitationOrder": schema_property("aeo", "preferredCitationOrder"),
        "aeo.answerSnippets": schema_property("aeo", "answerSnippets"),
        "aeo.answerSnippets.sources": (
            schema_property("aeo", "answerSnippets")
            .get("items", {})
            .get("properties", {})
            .get("sources", {})
        ),
        "triples": properties_schema.get("triples", {}),
    }
    for label, array_schema in unique_array_contracts.items():
        if array_schema.get("type") != "array" or array_schema.get("uniqueItems") is not True:
            errors.append(f"llms-index.schema.json {label} must require uniqueItems")

    seo_schema = properties_schema.get("seo", {})
    seo_expected_properties = {"primaryKeywords", "geoTargets", "technicalSignals", "geoSignals", "generativeSearch"}
    seo_actual_properties = set(seo_schema.get("properties", {}))
    missing_seo_properties = sorted(seo_expected_properties - seo_actual_properties)
    if missing_seo_properties:
        errors.append(f"llms-index.schema.json seo schema missing properties: {missing_seo_properties}")
    if seo_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json seo schema must disallow additionalProperties")
    seo_object_contracts = {
        "technicalSignals": {
            "canonicalPersonId",
            "canonicalPortfolio",
            "schemaGraphs",
            "sitemaps",
            "robots",
            "pagesMirror",
        },
        "geoSignals": {"homeCountry", "serviceRegions", "searchModifiers"},
        "generativeSearch": {"principle", "llmsTxtRole", "answerSources", "agentReadySurfaces"},
    }
    for key, expected_properties in seo_object_contracts.items():
        item_schema = seo_schema.get("properties", {}).get(key, {})
        actual_properties = set(item_schema.get("properties", {}))
        missing_properties = sorted(expected_properties - actual_properties)
        if missing_properties:
            errors.append(f"llms-index.schema.json seo.{key} schema missing properties: {missing_properties}")
        if item_schema.get("additionalProperties") is not False:
            errors.append(f"llms-index.schema.json seo.{key} schema must disallow additionalProperties")
    answer_source_items = (
        seo_schema.get("properties", {})
        .get("generativeSearch", {})
        .get("properties", {})
        .get("answerSources", {})
        .get("items", {})
    )
    if answer_source_items.get("type") != "string" or answer_source_items.get("format") != "uri":
        errors.append("llms-index.schema.json seo.generativeSearch.answerSources items must be URI strings")
    agent_surface_items = (
        seo_schema.get("properties", {})
        .get("generativeSearch", {})
        .get("properties", {})
        .get("agentReadySurfaces", {})
        .get("items", {})
    )
    if agent_surface_items.get("type") != "string" or agent_surface_items.get("minLength") != 1:
        errors.append("llms-index.schema.json seo.generativeSearch.agentReadySurfaces items must be non-empty strings")
    aeo_schema = properties_schema.get("aeo", {})
    aeo_expected_properties = {"preferredCitationOrder", "answerSnippets"}
    aeo_actual_properties = set(aeo_schema.get("properties", {}))
    missing_aeo_properties = sorted(aeo_expected_properties - aeo_actual_properties)
    if missing_aeo_properties:
        errors.append(f"llms-index.schema.json aeo schema missing properties: {missing_aeo_properties}")
    if aeo_schema.get("additionalProperties") is not False:
        errors.append("llms-index.schema.json aeo schema must disallow additionalProperties")
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
    service_channel_id = f"{person_fragment_base}hiring-service-channel"
    portfolio_site_id = data.get("identifiers", {}).get("portfolioWebsite")
    github_site_id = data.get("identifiers", {}).get("githubProfileIndex")
    profile_page_id = data.get("identifiers", {}).get("githubProfilePage")
    pages_site_id = data.get("identifiers", {}).get("githubPagesMirror")
    pages_page_id = f"{PAGES}/#webpage"
    pages_breadcrumb_id = f"{PAGES}/#breadcrumb"
    pages_catalog_id = f"{PAGES}/#data-catalog"
    pages_dataset_id = f"{PAGES}/#machine-readable-dataset"
    pages_image_id = f"{PAGES}/#primary-image"
    pages_main_content_id = f"{PAGES}/#main-content"
    pages_section_nav_id = pages_section_navigation_id()
    pages_section_ids = {pages_section_id(section["fragment"]) for section in pages_section_specs(data)}
    pages_section_relations = pages_section_relation_ids(data)
    pages_section_nav_item_ids = {
        pages_section_nav_item_id(section["fragment"])
        for section in pages_section_specs(data)
    }
    pages_topic_set_id = topic_term_set_id()
    expected_mentions = expected_mention_ids(data, person_fragment_base)
    for node in graph_nodes(person_schema):
        label = f"person.jsonld {node.get('@id', node.get('name', 'node'))}"
        check_creativework_abstract(node, label)
        check_dataset_search_metadata(node, label)
    for node in graph_nodes(faq_schema):
        check_creativework_abstract(node, f"faq.jsonld {node.get('@id', node.get('name', 'node'))}")
    person = node_by_id(person_schema, person_id)
    if not person or "Person" not in node_types(person):
        errors.append("person.jsonld missing Person node matching llms-index entity @id")
    else:
        check_person_identity_resolution(person, data, "person.jsonld Person")
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
        if person.get("jobTitle") != data.get("entity", {}).get("jobTitle", []):
            errors.append("person.jsonld Person jobTitle drift")
        if person.get("hasOccupation") != person_occupations(data):
            errors.append("person.jsonld Person hasOccupation drift")
        if person.get("workLocation") != person_work_locations():
            errors.append("person.jsonld Person workLocation drift")

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
        expected_service_ids = {
            f"{person_fragment_base}service-{slugify(focus)}"
            for focus in availability.get("focus", [])
        }
        if person.get("hasOfferCatalog", {}).get("@id") != f"{person_fragment_base}services":
            errors.append("person.jsonld Person hasOfferCatalog must reference services OfferCatalog")
        missing_offer_refs = sorted(expected_offer_ids - node_ref_ids(person.get("makesOffer")))
        if missing_offer_refs:
            errors.append(f"person.jsonld Person makesOffer missing: {missing_offer_refs}")
        if person.get("image", {}).get("@id") != f"{PAGES}/#primary-image":
            errors.append("person.jsonld Person image must reference Pages primary ImageObject")
        if person.get("potentialAction", {}).get("@id") != contact_action_id:
            errors.append("person.jsonld Person potentialAction must reference hiring ContactAction")
        if pages_page_id not in node_ref_ids(person.get("mainEntityOfPage")):
            errors.append("person.jsonld Person mainEntityOfPage must reference Pages CollectionPage")
        if pages_topic_set_id not in node_ref_ids(person.get("knowsAbout")):
            errors.append("person.jsonld Person knowsAbout must reference topic taxonomy")
        missing_known_terms = sorted(
            {topic_term_id(term) for term in expected_topic_terms(data)}
            - node_ref_ids(person.get("knowsAbout"))
        )
        if missing_known_terms:
            errors.append(f"person.jsonld Person knowsAbout missing topic terms: {missing_known_terms}")
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
            expected_catalog_identifier = {
                "@type": "PropertyValue",
                "propertyID": "Iron-Mark service catalog",
                "value": slugify("Mark Siazon services and availability"),
            }
            if offer_catalog.get("identifier") != expected_catalog_identifier:
                errors.append("person.jsonld OfferCatalog identifier drift")
            if offer_catalog.get("mainEntityOfPage") != availability.get("recruiterBrief"):
                errors.append("person.jsonld OfferCatalog mainEntityOfPage drift")
            if offer_catalog.get("about", {}).get("@id") != person_id:
                errors.append("person.jsonld OfferCatalog about drift")
            if offer_catalog.get("inLanguage") != "en":
                errors.append("person.jsonld OfferCatalog inLanguage must be en")
            if offer_catalog.get("dateModified") != data.get("updated"):
                errors.append("person.jsonld OfferCatalog dateModified drift")
            if offer_catalog.get("isAccessibleForFree") is not True:
                errors.append("person.jsonld OfferCatalog must be isAccessibleForFree")
            if offer_catalog.get("numberOfItems") != len(expected_offer_ids):
                errors.append("person.jsonld OfferCatalog numberOfItems drift")
            if offer_catalog.get("itemListOrder") != "https://schema.org/ItemListOrderAscending":
                errors.append("person.jsonld OfferCatalog itemListOrder drift")
            catalog_entries = offer_catalog.get("itemListElement", [])
            missing_catalog_refs = sorted(expected_offer_ids - item_list_ref_ids(catalog_entries))
            if missing_catalog_refs:
                errors.append(f"person.jsonld OfferCatalog itemListElement missing: {missing_catalog_refs}")
            if not isinstance(catalog_entries, list):
                errors.append("person.jsonld OfferCatalog itemListElement must be a list")
            else:
                for position, focus in enumerate(availability.get("focus", []), start=1):
                    expected_offer_id = f"{person_fragment_base}offer-{slugify(focus)}"
                    entry = next(
                        (
                            item
                            for item in catalog_entries
                            if isinstance(item, dict)
                            and item.get("item", {}).get("@id") == expected_offer_id
                        ),
                        None,
                    )
                    if not entry:
                        continue
                    if "ListItem" not in node_types(entry):
                        errors.append(f"person.jsonld OfferCatalog entry must be ListItem for: {focus}")
                    if entry.get("position") != position:
                        errors.append(f"person.jsonld OfferCatalog position drift for: {focus}")
                    if entry.get("name") != focus:
                        errors.append(f"person.jsonld OfferCatalog entry name drift for: {focus}")
        service_channel = node_by_id(person_schema, service_channel_id)
        if not service_channel or "ServiceChannel" not in node_types(service_channel):
            errors.append("person.jsonld missing hiring ServiceChannel node")
        else:
            if service_channel.get("serviceUrl") != availability.get("contact"):
                errors.append("person.jsonld ServiceChannel serviceUrl drift")
            if "en" not in service_channel.get("availableLanguage", []):
                errors.append("person.jsonld ServiceChannel availableLanguage must include en")
            missing_channel_services = sorted(expected_service_ids - node_ref_ids(service_channel.get("providesService")))
            if missing_channel_services:
                errors.append(f"person.jsonld ServiceChannel providesService missing: {missing_channel_services}")
            if service_channel.get("about", {}).get("@id") != person_id:
                errors.append("person.jsonld ServiceChannel about drift")
            if service_channel.get("dateModified") != data.get("updated"):
                errors.append("person.jsonld ServiceChannel dateModified drift")
        for focus in availability.get("focus", []):
            offer_id = f"{person_fragment_base}offer-{slugify(focus)}"
            service_id = f"{person_fragment_base}service-{slugify(focus)}"
            offer = node_by_id(person_schema, offer_id)
            if not offer or "Offer" not in node_types(offer):
                errors.append(f"person.jsonld missing Offer node: {offer_id}")
            else:
                if offer.get("identifier") != service_focus_identifier(focus, "offer"):
                    errors.append(f"person.jsonld Offer identifier drift for: {focus}")
                if offer.get("description") != offer_description(data, focus):
                    errors.append(f"person.jsonld Offer description drift for: {focus}")
                if offer.get("mainEntityOfPage") != availability.get("recruiterBrief"):
                    errors.append(f"person.jsonld Offer mainEntityOfPage drift for: {focus}")
                if offer.get("itemOffered", {}).get("@id") != service_id:
                    errors.append(f"person.jsonld Offer itemOffered drift for: {focus}")
                if offer.get("businessFunction") != PROVIDE_SERVICE_BUSINESS_FUNCTION:
                    errors.append(f"person.jsonld Offer businessFunction drift for: {focus}")
                if offer.get("seller", {}).get("@id") != person_id:
                    errors.append(f"person.jsonld Offer seller drift for: {focus}")
                missing_offer_area = sorted(area_served - area_names(offer.get("areaServed")))
                if missing_offer_area:
                    errors.append(f"person.jsonld Offer areaServed missing for {focus}: {missing_offer_area}")
                missing_eligible_region = sorted(area_served - area_names(offer.get("eligibleRegion")))
                if missing_eligible_region:
                    errors.append(
                        f"person.jsonld Offer eligibleRegion missing for {focus}: {missing_eligible_region}"
                    )
            service = node_by_id(person_schema, service_id)
            if not service or "Service" not in node_types(service):
                errors.append(f"person.jsonld missing Service node: {service_id}")
            else:
                if service.get("identifier") != service_focus_identifier(focus, "service"):
                    errors.append(f"person.jsonld Service identifier drift for: {focus}")
                if service.get("description") != service_description(data, focus):
                    errors.append(f"person.jsonld Service description drift for: {focus}")
                if service.get("mainEntityOfPage") != availability.get("recruiterBrief"):
                    errors.append(f"person.jsonld Service mainEntityOfPage drift for: {focus}")
                if service.get("provider", {}).get("@id") != person_id:
                    errors.append(f"person.jsonld Service provider drift for: {focus}")
                if service.get("offers", {}).get("@id") != offer_id:
                    errors.append(f"person.jsonld Service offers drift for: {focus}")
                if service.get("availableChannel", {}).get("@id") != service_channel_id:
                    errors.append(f"person.jsonld Service availableChannel drift for: {focus}")
                if service.get("providerMobility") != SERVICE_PROVIDER_MOBILITY:
                    errors.append(f"person.jsonld Service providerMobility drift for: {focus}")
                if service.get("audience") != service_audience():
                    errors.append(f"person.jsonld Service audience drift for: {focus}")
                if service.get("serviceAudience") != service_audience():
                    errors.append(f"person.jsonld Service serviceAudience drift for: {focus}")
                missing_service_area = sorted(area_served - area_names(service.get("areaServed")))
                if missing_service_area:
                    errors.append(f"person.jsonld Service areaServed missing for {focus}: {missing_service_area}")

    for node_id, label in (
        (portfolio_site_id, "person.jsonld Portfolio WebSite"),
        (github_site_id, "person.jsonld GitHub profile WebSite"),
        (profile_page_id, "person.jsonld GitHub ProfilePage"),
        (pages_site_id, "person.jsonld Pages WebSite"),
        (pages_page_id, "person.jsonld Pages CollectionPage"),
        (pages_catalog_id, "person.jsonld DataCatalog"),
        (pages_dataset_id, "person.jsonld Dataset"),
    ):
        node = node_by_id(person_schema, node_id)
        if not node:
            errors.append(f"{label} missing mention-bearing node")
            continue
        check_expected_mentions(node, expected_mentions, label)
        check_ownership_metadata(node, data, label)
        check_spatial_coverage(node, data, label)
        if node.get("keywords") != profile_keywords(data):
            errors.append(f"{label} keywords drift")

    profile_page = node_by_id(person_schema, profile_page_id)
    if not profile_page or "ProfilePage" not in node_types(profile_page):
        errors.append("person.jsonld missing GitHub ProfilePage node")
    else:
        if profile_page.get("significantLink") != profile_significant_links(data):
            errors.append("person.jsonld GitHub ProfilePage significantLink drift")
        if profile_page.get("relatedLink") != profile_related_links(data):
            errors.append("person.jsonld GitHub ProfilePage relatedLink drift")
        if profile_page.get("inLanguage") != "en":
            errors.append("person.jsonld GitHub ProfilePage inLanguage must be en")
        if profile_page.get("mainEntity", {}).get("@id") != person_id:
            errors.append("person.jsonld GitHub ProfilePage mainEntity drift")
        if profile_page.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld GitHub ProfilePage about drift")
        if profile_page.get("isPartOf", {}).get("@id") != github_site_id:
            errors.append("person.jsonld GitHub ProfilePage isPartOf drift")
        if profile_page.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld GitHub ProfilePage dateModified drift")
        if profile_page.get("author", {}).get("@id") != person_id:
            errors.append("person.jsonld GitHub ProfilePage author drift")
        if profile_page.get("publisher", {}).get("@id") != person_id:
            errors.append("person.jsonld GitHub ProfilePage publisher drift")
        if profile_page.get("primaryImageOfPage", {}).get("@id") != pages_image_id:
            errors.append("person.jsonld GitHub ProfilePage primaryImageOfPage drift")
        if profile_page.get("thumbnailUrl") != PAGES_SOCIAL_IMAGE:
            errors.append("person.jsonld GitHub ProfilePage thumbnailUrl drift")
        if profile_page.get("potentialAction", {}).get("@id") != contact_action_id:
            errors.append("person.jsonld GitHub ProfilePage potentialAction drift")
        missing_profile_parts = sorted(set(profile_page_part_ids(data)) - node_ref_ids(profile_page.get("hasPart")))
        if missing_profile_parts:
            errors.append(f"person.jsonld GitHub ProfilePage hasPart missing: {missing_profile_parts}")
        check_review_metadata(profile_page, data, "person.jsonld GitHub ProfilePage")
        check_content_usage_policy(profile_page, data, "person.jsonld GitHub ProfilePage")
        check_structured_data_provenance(profile_page, data, "person.jsonld GitHub ProfilePage")
        check_spatial_coverage(profile_page, data, "person.jsonld GitHub ProfilePage")

    pages_site = node_by_id(person_schema, pages_site_id)
    if not pages_site or "WebSite" not in node_types(pages_site):
        errors.append("person.jsonld missing GitHub Pages WebSite node")
    else:
        if pages_site.get("name") != PAGES_SITE_NAME:
            errors.append("person.jsonld Pages WebSite site name drift")
        if pages_site.get("url") != f"{PAGES}/":
            errors.append("person.jsonld Pages WebSite url drift")
        if pages_site.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld Pages WebSite dateModified drift")
        if pages_site.get("isBasedOn") != data.get("canonical", {}).get("githubProfileReadme"):
            errors.append("person.jsonld Pages WebSite isBasedOn drift")
        if pages_site.get("significantLink") != pages_significant_links(data):
            errors.append("person.jsonld Pages WebSite significantLink drift")
        if pages_site.get("relatedLink") != pages_related_links(data):
            errors.append("person.jsonld Pages WebSite relatedLink drift")
        required_site_parts = {
            pages_page_id,
            pages_catalog_id,
            pages_dataset_id,
            pages_main_content_id,
            pages_section_nav_id,
            pages_topic_set_id,
        }
        missing_site_parts = sorted(required_site_parts - node_ref_ids(pages_site.get("hasPart")))
        if missing_site_parts:
            errors.append(f"person.jsonld Pages WebSite hasPart missing: {missing_site_parts}")
        check_content_usage_policy(pages_site, data, "person.jsonld Pages WebSite")
        check_structured_data_provenance(pages_site, data, "person.jsonld Pages WebSite")
        missing_site_alternates = sorted(PAGES_SITE_ALTERNATE_NAMES - set(pages_site.get("alternateName", [])))
        if missing_site_alternates:
            errors.append(f"person.jsonld Pages WebSite alternateName missing: {missing_site_alternates}")
    pages_page = node_by_id(person_schema, pages_page_id)
    if not pages_page or "CollectionPage" not in node_types(pages_page):
        errors.append("person.jsonld missing GitHub Pages CollectionPage node")
    else:
        if pages_page.get("name") != PAGES_SITE_NAME:
            errors.append("person.jsonld Pages CollectionPage site name drift")
        missing_page_alternates = sorted(PAGES_SITE_ALTERNATE_NAMES - set(pages_page.get("alternateName", [])))
        if missing_page_alternates:
            errors.append(f"person.jsonld Pages CollectionPage alternateName missing: {missing_page_alternates}")
        if pages_page.get("url") != pages.get("home"):
            errors.append("person.jsonld Pages CollectionPage url drift")
        if pages_page.get("isPartOf", {}).get("@id") != pages_site_id:
            errors.append("person.jsonld Pages CollectionPage isPartOf drift")
        if pages_page.get("mainEntity", {}).get("@id") != person_id:
            errors.append("person.jsonld Pages CollectionPage mainEntity drift")
        if pages_page.get("author", {}).get("@id") != person_id:
            errors.append("person.jsonld Pages CollectionPage author drift")
        if pages_page.get("publisher", {}).get("@id") != person_id:
            errors.append("person.jsonld Pages CollectionPage publisher drift")
        if pages_page.get("breadcrumb", {}).get("@id") != pages_breadcrumb_id:
            errors.append("person.jsonld Pages CollectionPage breadcrumb drift")
        if pages_page.get("mainContentOfPage", {}).get("@id") != pages_main_content_id:
            errors.append("person.jsonld Pages CollectionPage mainContentOfPage drift")
        if pages_page.get("primaryImageOfPage", {}).get("@id") != pages_image_id:
            errors.append("person.jsonld Pages CollectionPage primaryImageOfPage drift")
        if pages_page.get("thumbnailUrl") != PAGES_SOCIAL_IMAGE:
            errors.append("person.jsonld Pages CollectionPage thumbnailUrl drift")
        if pages_page.get("potentialAction", {}).get("@id") != contact_action_id:
            errors.append("person.jsonld Pages CollectionPage potentialAction drift")
        if pages_page.get("isBasedOn") != repo.get("llmsIndexJson"):
            errors.append("person.jsonld Pages CollectionPage isBasedOn drift")
        if pages_page.get("significantLink") != pages_significant_links(data):
            errors.append("person.jsonld Pages CollectionPage significantLink drift")
        if pages_page.get("relatedLink") != pages_related_links(data):
            errors.append("person.jsonld Pages CollectionPage relatedLink drift")
        if pages_page.get("speakable") != expected_pages_speakable(data):
            errors.append("person.jsonld Pages CollectionPage speakable drift")
        check_review_metadata(pages_page, data, "person.jsonld Pages CollectionPage")
        check_content_usage_policy(pages_page, data, "person.jsonld Pages CollectionPage")
        check_global_citation(pages_page, data, "person.jsonld Pages CollectionPage")
        check_structured_data_provenance(pages_page, data, "person.jsonld Pages CollectionPage")
        required_parts = {
            pages_catalog_id,
            pages_dataset_id,
            pages_main_content_id,
            pages_section_nav_id,
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
            pages_topic_set_id,
        }
        required_parts.update(pages_section_ids)
        missing_parts = sorted(required_parts - node_ref_ids(pages_page.get("hasPart")))
        if missing_parts:
            errors.append(f"person.jsonld Pages CollectionPage hasPart missing: {missing_parts}")
    main_content = node_by_id(person_schema, pages_main_content_id)
    if not main_content or "WebPageElement" not in node_types(main_content):
        errors.append("person.jsonld missing Pages main WebPageElement node")
    else:
        if main_content.get("url") != f"{pages.get('home')}#main-content":
            errors.append("person.jsonld main WebPageElement url drift")
        if main_content.get("text") != data.get("entity", {}).get("description"):
            errors.append("person.jsonld main WebPageElement text drift")
        if main_content.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld main WebPageElement about drift")
        if main_content.get("isPartOf", {}).get("@id") != pages_page_id:
            errors.append("person.jsonld main WebPageElement isPartOf drift")
        if main_content.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld main WebPageElement dateModified drift")
        if main_content.get("isAccessibleForFree") is not True:
            errors.append("person.jsonld main WebPageElement must be isAccessibleForFree")
        check_content_usage_policy(main_content, data, "person.jsonld main WebPageElement")
        check_global_citation(main_content, data, "person.jsonld main WebPageElement")
        check_ownership_metadata(main_content, data, "person.jsonld main WebPageElement")
        check_structured_data_provenance(main_content, data, "person.jsonld main WebPageElement")
        missing_section_parts = sorted(pages_section_ids - node_ref_ids(main_content.get("hasPart")))
        if missing_section_parts:
            errors.append(f"person.jsonld main WebPageElement hasPart missing: {missing_section_parts}")
        if pages_section_nav_id not in node_ref_ids(main_content.get("hasPart")):
            errors.append("person.jsonld main WebPageElement hasPart missing section navigation")
    section_navigation = node_by_id(person_schema, pages_section_nav_id)
    if not section_navigation or "SiteNavigationElement" not in node_types(section_navigation):
        errors.append("person.jsonld missing section SiteNavigationElement node")
    else:
        if section_navigation.get("url") != f"{pages.get('home')}#section-navigation":
            errors.append("person.jsonld section navigation url drift")
        if section_navigation.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld section navigation about drift")
        if section_navigation.get("isPartOf", {}).get("@id") != pages_page_id:
            errors.append("person.jsonld section navigation isPartOf drift")
        if section_navigation.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld section navigation dateModified drift")
        if section_navigation.get("isAccessibleForFree") is not True:
            errors.append("person.jsonld section navigation must be isAccessibleForFree")
        missing_nav_items = sorted(pages_section_nav_item_ids - node_ref_ids(section_navigation.get("hasPart")))
        if missing_nav_items:
            errors.append(f"person.jsonld section navigation hasPart missing: {missing_nav_items}")
        check_content_usage_policy(section_navigation, data, "person.jsonld section navigation")
        check_global_citation(section_navigation, data, "person.jsonld section navigation")
        check_ownership_metadata(section_navigation, data, "person.jsonld section navigation")
        check_structured_data_provenance(section_navigation, data, "person.jsonld section navigation")
    for position, section in enumerate(pages_section_specs(data), start=1):
        nav_item_id = pages_section_nav_item_id(section["fragment"])
        nav_item = node_by_id(person_schema, nav_item_id)
        label = f"person.jsonld section navigation item {section['fragment']}"
        if not nav_item or "SiteNavigationElement" not in node_types(nav_item):
            errors.append(f"person.jsonld missing section navigation item: {nav_item_id}")
            continue
        if nav_item.get("name") != section["heading"]:
            errors.append(f"{label} name drift")
        if nav_item.get("url") != f"{pages.get('home')}#{section['fragment']}":
            errors.append(f"{label} url drift")
        if nav_item.get("description") != section["description"]:
            errors.append(f"{label} description drift")
        if nav_item.get("abstract") != nav_item.get("description"):
            errors.append(f"{label} abstract drift")
        if nav_item.get("about", {}).get("@id") != pages_section_id(section["fragment"]):
            errors.append(f"{label} about drift")
        if nav_item.get("isPartOf", {}).get("@id") != pages_section_nav_id:
            errors.append(f"{label} isPartOf drift")
        if nav_item.get("position") != position:
            errors.append(f"{label} position drift")
        if nav_item.get("inLanguage") != "en":
            errors.append(f"{label} inLanguage must be en")
        if nav_item.get("dateModified") != data.get("updated"):
            errors.append(f"{label} dateModified drift")
        if nav_item.get("isAccessibleForFree") is not True:
            errors.append(f"{label} must be isAccessibleForFree")
        check_ownership_metadata(nav_item, data, label)
    for section in pages_section_specs(data):
        section_id = pages_section_id(section["fragment"])
        section_node = node_by_id(person_schema, section_id)
        label = f"person.jsonld section WebPageElement {section['fragment']}"
        if not section_node or "WebPageElement" not in node_types(section_node):
            errors.append(f"person.jsonld missing section WebPageElement node: {section_id}")
            continue
        if section_node.get("name") != section["name"]:
            errors.append(f"{label} name drift")
        if section_node.get("url") != f"{pages.get('home')}#{section['fragment']}":
            errors.append(f"{label} url drift")
        if section_node.get("description") != section["description"]:
            errors.append(f"{label} description drift")
        if section_node.get("text") != section["text"]:
            errors.append(f"{label} text drift")
        if section_node.get("about", {}).get("@id") != person_id:
            errors.append(f"{label} about drift")
        if section_node.get("isPartOf", {}).get("@id") != pages_page_id:
            errors.append(f"{label} isPartOf drift")
        if section_node.get("dateModified") != data.get("updated"):
            errors.append(f"{label} dateModified drift")
        if section_node.get("isAccessibleForFree") is not True:
            errors.append(f"{label} must be isAccessibleForFree")
        relations = pages_section_relations.get(section["fragment"], {})
        missing_has_part = sorted(set(relations.get("hasPart", [])) - node_ref_ids(section_node.get("hasPart")))
        if missing_has_part:
            errors.append(f"{label} hasPart missing: {missing_has_part}")
        missing_mentions = sorted(set(relations.get("mentions", [])) - node_ref_ids(section_node.get("mentions")))
        if missing_mentions:
            errors.append(f"{label} mentions missing: {missing_mentions}")
        check_content_usage_policy(section_node, data, label)
        check_global_citation(section_node, data, label)
        check_ownership_metadata(section_node, data, label)
        check_structured_data_provenance(section_node, data, label)
    topic_terms = expected_topic_terms(data)
    topic_set = node_by_id(person_schema, pages_topic_set_id)
    if not topic_set or "DefinedTermSet" not in node_types(topic_set):
        errors.append("person.jsonld missing Pages DefinedTermSet node")
    else:
        if topic_set.get("name") != "Mark Siazon profile topic taxonomy":
            errors.append("person.jsonld DefinedTermSet name drift")
        if topic_set.get("url") != pages.get("home"):
            errors.append("person.jsonld DefinedTermSet url drift")
        if topic_set.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld DefinedTermSet dateModified drift")
        if topic_set.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld DefinedTermSet about drift")
        if topic_set.get("isPartOf", {}).get("@id") != pages_site_id:
            errors.append("person.jsonld DefinedTermSet isPartOf drift")
        missing_terms = sorted({topic_term_id(term) for term in topic_terms} - node_ref_ids(topic_set.get("hasDefinedTerm")))
        if missing_terms:
            errors.append(f"person.jsonld DefinedTermSet hasDefinedTerm missing: {missing_terms}")
        check_content_usage_policy(topic_set, data, "person.jsonld DefinedTermSet")
        check_global_citation(topic_set, data, "person.jsonld DefinedTermSet")
        check_ownership_metadata(topic_set, data, "person.jsonld DefinedTermSet")
        check_structured_data_provenance(topic_set, data, "person.jsonld DefinedTermSet")
    for term in topic_terms:
        term_node = node_by_id(person_schema, topic_term_id(term))
        if not term_node or "DefinedTerm" not in node_types(term_node):
            errors.append(f"person.jsonld missing DefinedTerm node: {term}")
            continue
        if term_node.get("name") != term:
            errors.append(f"person.jsonld DefinedTerm name drift: {term}")
        if term_node.get("termCode") != slugify(term):
            errors.append(f"person.jsonld DefinedTerm termCode drift: {term}")
        if term_node.get("description") != expected_topic_term_description(data, term):
            errors.append(f"person.jsonld DefinedTerm description drift: {term}")
        if term_node.get("url") != topic_term_id(term):
            errors.append(f"person.jsonld DefinedTerm url drift: {term}")
        if term_node.get("inDefinedTermSet", {}).get("@id") != pages_topic_set_id:
            errors.append(f"person.jsonld DefinedTerm set drift: {term}")
        if term_node.get("about", {}).get("@id") != person_id:
            errors.append(f"person.jsonld DefinedTerm about drift: {term}")
        if term_node.get("dateModified") != data.get("updated"):
            errors.append(f"person.jsonld DefinedTerm dateModified drift: {term}")
    data_catalog = node_by_id(person_schema, pages_catalog_id)
    if not data_catalog or "DataCatalog" not in node_types(data_catalog):
        errors.append("person.jsonld missing GitHub Pages DataCatalog node")
    else:
        if data_catalog.get("name") != data_catalog_name():
            errors.append("person.jsonld DataCatalog name drift")
        if data_catalog.get("url") != pages.get("home"):
            errors.append("person.jsonld DataCatalog url drift")
        if data_catalog.get("description") != data_catalog_description():
            errors.append("person.jsonld DataCatalog description drift")
        if data_catalog.get("abstract") != data_catalog.get("description"):
            errors.append("person.jsonld DataCatalog abstract drift")
        if data_catalog.get("dataset", {}).get("@id") != pages_dataset_id:
            errors.append("person.jsonld DataCatalog dataset drift")
        if data_catalog.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld DataCatalog about drift")
        if data_catalog.get("isBasedOn") != repo.get("llmsIndexJson"):
            errors.append("person.jsonld DataCatalog isBasedOn drift")
        if data_catalog.get("creator", {}).get("@id") != person_id:
            errors.append("person.jsonld DataCatalog creator drift")
        if data_catalog.get("publisher", {}).get("@id") != person_id:
            errors.append("person.jsonld DataCatalog publisher drift")
        if data_catalog.get("inLanguage") != "en":
            errors.append("person.jsonld DataCatalog inLanguage must be en")
        if data_catalog.get("datePublished") != DATASET_DATE_PUBLISHED:
            errors.append("person.jsonld DataCatalog datePublished drift")
        if data_catalog.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld DataCatalog dateModified drift")
        if data_catalog.get("license") != data.get("license"):
            errors.append("person.jsonld DataCatalog license drift")
        if data_catalog.get("keywords") != profile_keywords(data):
            errors.append("person.jsonld DataCatalog keywords drift")
        if data_catalog.get("temporalCoverage") != dataset_temporal_coverage(data):
            errors.append("person.jsonld DataCatalog temporalCoverage drift")
        if data_catalog.get("measurementTechnique") != dataset_measurement_techniques():
            errors.append("person.jsonld DataCatalog measurementTechnique drift")
        if data_catalog.get("isAccessibleForFree") is not True:
            errors.append("person.jsonld DataCatalog must be marked isAccessibleForFree")
        check_content_usage_policy(data_catalog, data, "person.jsonld DataCatalog")
        check_global_citation(data_catalog, data, "person.jsonld DataCatalog")
        check_structured_data_provenance(data_catalog, data, "person.jsonld DataCatalog")
    image = node_by_id(person_schema, pages_image_id)
    if not image or "ImageObject" not in node_types(image):
        errors.append("person.jsonld missing Pages primary ImageObject node")
    else:
        if image.get("url") != PAGES_SOCIAL_IMAGE:
            errors.append("person.jsonld ImageObject url drift")
        if image.get("contentUrl") != PAGES_SOCIAL_IMAGE:
            errors.append("person.jsonld ImageObject contentUrl drift")
        if image.get("encodingFormat") != "image/png":
            errors.append("person.jsonld ImageObject encodingFormat must be image/png")
        if image.get("width") != SOCIAL_IMAGE_WIDTH:
            errors.append("person.jsonld ImageObject width drift")
        if image.get("height") != SOCIAL_IMAGE_HEIGHT:
            errors.append("person.jsonld ImageObject height drift")
        if image.get("caption") != SOCIAL_IMAGE_ALT:
            errors.append("person.jsonld ImageObject caption drift")
        if image.get("description") != primary_image_description():
            errors.append("person.jsonld ImageObject description drift")
        if image.get("abstract") != image.get("description"):
            errors.append("person.jsonld ImageObject abstract drift")
        for key, expected in file_integrity_metadata(SOCIAL_IMAGE_ASSET).items():
            if image.get(key) != expected:
                errors.append(f"person.jsonld ImageObject {key} drift")
        check_image_rights(image, data, "person.jsonld primary ImageObject")
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
        if contact_entry.get("name") != "Mark Siazon contact form entry point":
            errors.append("person.jsonld ContactAction EntryPoint name drift")
        if (
            contact_entry.get("description")
            != "Web entry point for Mark Siazon hiring contact and recruiter inquiries."
        ):
            errors.append("person.jsonld ContactAction EntryPoint description drift")
        if contact_entry.get("contentType") != "text/html":
            errors.append("person.jsonld ContactAction EntryPoint contentType must be text/html")
        if contact_entry.get("httpMethod") != "GET":
            errors.append("person.jsonld ContactAction EntryPoint httpMethod must be GET")
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
        if dataset.get("sameAs") != repo.get("llmsIndexJson"):
            errors.append("person.jsonld Dataset sameAs source drift")
        if dataset.get("isBasedOn") != repo.get("llmsIndexJson"):
            errors.append("person.jsonld Dataset isBasedOn drift")
        if dataset.get("version") != data.get("updated"):
            errors.append("person.jsonld Dataset version must match updated date")
        if dataset.get("alternateName") != dataset_alternate_names(data):
            errors.append("person.jsonld Dataset alternateName drift")
        if dataset.get("datePublished") != DATASET_DATE_PUBLISHED:
            errors.append("person.jsonld Dataset datePublished drift")
        identifiers = dataset.get("identifier", [])
        if isinstance(identifiers, dict):
            identifiers = [identifiers]
        identifier_values = {item.get("value") for item in identifiers if isinstance(item, dict)}
        expected_identifier_values = {"Iron-Mark/Iron-Mark", pages_dataset_id}
        missing_identifier_values = sorted(expected_identifier_values - identifier_values)
        if missing_identifier_values:
            errors.append(f"person.jsonld Dataset identifier missing value(s): {missing_identifier_values}")
        if {person_id, pages_topic_set_id} - node_ref_ids(dataset.get("about")):
            errors.append("person.jsonld Dataset about must reference Person and topic taxonomy")
        if dataset.get("includedInDataCatalog", {}).get("@id") != pages_catalog_id:
            errors.append("person.jsonld Dataset catalog membership drift")
        if dataset.get("spatialCoverage") != expected_area_nodes(data.get("availability", {}).get("areaServed", [])):
            errors.append("person.jsonld Dataset spatialCoverage must match typed availability.areaServed")
        if dataset.get("temporalCoverage") != dataset_temporal_coverage(data):
            errors.append("person.jsonld Dataset temporalCoverage drift")
        if dataset.get("measurementTechnique") != dataset_measurement_techniques():
            errors.append("person.jsonld Dataset measurementTechnique drift")
        if dataset.get("variableMeasured") != expected_dataset_measurements(data, len(downloads)):
            errors.append("person.jsonld Dataset variableMeasured drift")
        check_content_usage_policy(dataset, data, "person.jsonld Dataset")
        check_global_citation(dataset, data, "person.jsonld Dataset")
        check_structured_data_provenance(dataset, data, "person.jsonld Dataset")
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
        download_sources = expected_download_sources(repo)
        if download.get("isBasedOn") != download_sources.get(key):
            errors.append(f"person.jsonld DataDownload isBasedOn drift for: {key}")
        check_content_usage_policy(download, data, f"person.jsonld DataDownload {key}")
        if download.get("encodingFormat") != encoding:
            errors.append(f"person.jsonld DataDownload encodingFormat drift for: {key}")
        if download.get("description") != download_description(download.get("name", ""), encoding):
            errors.append(f"person.jsonld DataDownload description drift for: {key}")
        if download.get("abstract") != download.get("description"):
            errors.append(f"person.jsonld DataDownload abstract drift for: {key}")
        expected_integrity = download_integrity_metadata(key, data)
        for integrity_key in ("contentSize", "sha256"):
            if expected_integrity:
                if download.get(integrity_key) != expected_integrity[integrity_key]:
                    errors.append(f"person.jsonld DataDownload {integrity_key} drift for: {key}")
            elif integrity_key in download:
                errors.append(f"person.jsonld DataDownload unexpected {integrity_key} for: {key}")
        if download.get("inLanguage") != "en":
            errors.append(f"person.jsonld DataDownload inLanguage must be en for: {key}")
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
        check_global_citation(download, data, f"person.jsonld DataDownload {key}")
        check_publisher_metadata(download, data, f"person.jsonld DataDownload {key}")
        check_ownership_metadata(download, data, f"person.jsonld DataDownload {key}")
        check_structured_data_provenance(download, data, f"person.jsonld DataDownload {key}")
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
        if work.get("publisher", {}).get("@id") != person_id:
            errors.append(f"person.jsonld CreativeWork publisher drift for: {node_id}")
        if work.get("about", {}).get("@id") != person_id:
            errors.append(f"person.jsonld CreativeWork about drift for: {node_id}")
        check_content_usage_policy(work, data, f"person.jsonld CreativeWork {node_id}")
        check_global_citation(work, data, f"person.jsonld CreativeWork {node_id}")
        check_ownership_metadata(work, data, f"person.jsonld CreativeWork {node_id}")
        check_spatial_coverage(work, data, f"person.jsonld CreativeWork {node_id}")
        check_structured_data_provenance(work, data, f"person.jsonld CreativeWork {node_id}")
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
            if items[0].get("name") != "Mark Siazon Portfolio" or items[0].get("position") != 1:
                errors.append("person.jsonld Pages BreadcrumbList portfolio name/position drift")
            if items[1].get("item") != pages.get("home"):
                errors.append("person.jsonld Pages BreadcrumbList Pages item drift")
            if items[1].get("name") != PAGES_SITE_NAME or items[1].get("position") != 2:
                errors.append("person.jsonld Pages BreadcrumbList Pages name/position drift")

    faq_id = data.get("identifiers", {}).get("faqDocument")
    person_faq_page = node_by_id(person_schema, faq_id)
    if not person_faq_page or "FAQPage" not in node_types(person_faq_page):
        errors.append("person.jsonld missing FAQPage node matching identifiers.faqDocument")
    else:
        if person_faq_page.get("identifier") != faq_document_identifier(faq_id):
            errors.append("person.jsonld FAQPage identifier drift")
        if person_faq_page.get("inLanguage") != "en":
            errors.append("person.jsonld FAQPage inLanguage must be en")
        if person_faq_page.get("author", {}).get("@id") != person_id:
            errors.append("person.jsonld FAQPage author drift")
        if person_faq_page.get("publisher", {}).get("@id") != person_id:
            errors.append("person.jsonld FAQPage publisher drift")
        if person_faq_page.get("keywords") != profile_keywords(data):
            errors.append("person.jsonld FAQPage keywords drift")
        if person_faq_page.get("isAccessibleForFree") is not True:
            errors.append("person.jsonld FAQPage must be isAccessibleForFree")
        expected_question_ids = {
            faq_question_id(faq_id, item.get("question", ""))
            for item in data.get("aeo", {}).get("answerSnippets", [])
        }
        missing_has_part = sorted(expected_question_ids - node_ref_ids(person_faq_page.get("hasPart")))
        if missing_has_part:
            errors.append(f"person.jsonld FAQPage hasPart missing questions: {missing_has_part}")
        check_review_metadata(person_faq_page, data, "person.jsonld FAQPage")
        check_spatial_coverage(person_faq_page, data, "person.jsonld FAQPage")
    faq_page = node_by_id(faq_schema, faq_id)
    faq_person = node_by_id(faq_schema, person_id)
    if not faq_person or "Person" not in node_types(faq_person):
        errors.append("faq.jsonld missing Person node matching llms-index entity @id")
    else:
        check_person_identity_resolution(faq_person, data, "faq.jsonld Person")
    if not faq_page or "FAQPage" not in node_types(faq_page):
        errors.append("faq.jsonld missing FAQPage node matching identifiers.faqDocument")
    else:
        if faq_page.get("identifier") != faq_document_identifier(faq_id):
            errors.append("faq.jsonld FAQPage identifier drift")
        if faq_page.get("dateModified") != data.get("updated"):
            errors.append("faq.jsonld FAQPage dateModified drift")
        if faq_page.get("isBasedOn") != repo.get("faqMd"):
            errors.append("faq.jsonld FAQPage isBasedOn drift")
        if faq_page.get("author", {}).get("@id") != person_id:
            errors.append("faq.jsonld FAQPage author drift")
        if faq_page.get("publisher", {}).get("@id") != person_id:
            errors.append("faq.jsonld FAQPage publisher drift")
        if faq_page.get("about", {}).get("@id") != person_id:
            errors.append("faq.jsonld FAQPage about drift")
        if faq_page.get("inLanguage") != "en":
            errors.append("faq.jsonld FAQPage inLanguage must be en")
        if faq_page.get("keywords") != profile_keywords(data):
            errors.append("faq.jsonld FAQPage keywords drift")
        if faq_page.get("isAccessibleForFree") is not True:
            errors.append("faq.jsonld FAQPage must be isAccessibleForFree")
        expected_question_ids = {
            faq_question_id(faq_id, item.get("question", ""))
            for item in data.get("aeo", {}).get("answerSnippets", [])
        }
        missing_has_part = sorted(expected_question_ids - node_ref_ids(faq_page.get("hasPart")))
        if missing_has_part:
            errors.append(f"faq.jsonld FAQPage hasPart missing questions: {missing_has_part}")
        check_content_usage_policy(faq_page, data, "faq.jsonld FAQPage")
        check_global_citation(faq_page, data, "faq.jsonld FAQPage")
        check_review_metadata(faq_page, data, "faq.jsonld FAQPage")
        check_ownership_metadata(faq_page, data, "faq.jsonld FAQPage")
        check_spatial_coverage(faq_page, data, "faq.jsonld FAQPage")
        check_structured_data_provenance(faq_page, data, "faq.jsonld FAQPage")

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
        if question_node.get("identifier") != faq_item_identifier(expected, "question"):
            errors.append(f"faq.jsonld Question identifier drift for: {question.get('question')}")
        if question_node.get("about", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Question about drift for: {question.get('question')}")
        if question_node.get("author", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Question author drift for: {question.get('question')}")
        if question_node.get("publisher", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Question publisher drift for: {question.get('question')}")
        if question_node.get("isPartOf", {}).get("@id") != faq_id:
            errors.append(f"faq.jsonld Question isPartOf drift for: {question.get('question')}")
        if question_node.get("parentItem", {}).get("@id") != faq_id:
            errors.append(f"faq.jsonld Question parentItem drift for: {question.get('question')}")
        if question_node.get("answerCount") != 1:
            errors.append(f"faq.jsonld Question answerCount drift for: {question.get('question')}")
        if question_node.get("inLanguage") != "en":
            errors.append(f"faq.jsonld Question inLanguage must be en for: {question.get('question')}")
        if question_node.get("dateModified") != data.get("updated"):
            errors.append(f"faq.jsonld Question dateModified drift for: {question.get('question')}")
        if question_node.get("isAccessibleForFree") is not True:
            errors.append(f"faq.jsonld Question must be isAccessibleForFree for: {question.get('question')}")
        expected_citations = set(question.get("sources", []))
        question_citations = question_node.get("citation", [])
        if isinstance(question_citations, str):
            question_citations = [question_citations]
        if set(question_citations) != expected_citations:
            errors.append(f"faq.jsonld Question citation drift for: {question.get('question')}")
        check_content_usage_policy(question_node, data, f"faq.jsonld Question {question.get('question')}")
        check_structured_data_provenance(question_node, data, f"faq.jsonld Question {question.get('question')}")
        accepted_answer = question_node.get("acceptedAnswer", {})
        if not isinstance(accepted_answer, dict):
            errors.append(f"faq.jsonld Question missing acceptedAnswer: {expected}")
            continue
        answer_id = f"{expected}-answer"
        if accepted_answer.get("url") != answer_id:
            errors.append(f"faq.jsonld Answer url drift for: {question.get('question')}")
        if accepted_answer.get("identifier") != faq_item_identifier(answer_id, "answer"):
            errors.append(f"faq.jsonld Answer identifier drift for: {question.get('question')}")
        if accepted_answer.get("text") != question.get("answer"):
            errors.append(f"faq.jsonld answer drift for: {question.get('question')}")
        if accepted_answer.get("author", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Answer author drift for: {question.get('question')}")
        if accepted_answer.get("publisher", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Answer publisher drift for: {question.get('question')}")
        if accepted_answer.get("about", {}).get("@id") != person_id:
            errors.append(f"faq.jsonld Answer about drift for: {question.get('question')}")
        if accepted_answer.get("isPartOf", {}).get("@id") != faq_id:
            errors.append(f"faq.jsonld Answer isPartOf drift for: {question.get('question')}")
        if accepted_answer.get("parentItem", {}).get("@id") != expected:
            errors.append(f"faq.jsonld Answer parentItem drift for: {question.get('question')}")
        if accepted_answer.get("inLanguage") != "en":
            errors.append(f"faq.jsonld Answer inLanguage must be en for: {question.get('question')}")
        if accepted_answer.get("dateModified") != data.get("updated"):
            errors.append(f"faq.jsonld Answer dateModified drift for: {question.get('question')}")
        if accepted_answer.get("isAccessibleForFree") is not True:
            errors.append(f"faq.jsonld Answer must be isAccessibleForFree for: {question.get('question')}")
        check_content_usage_policy(accepted_answer, data, f"faq.jsonld Answer {question.get('question')}")
        check_structured_data_provenance(accepted_answer, data, f"faq.jsonld Answer {question.get('question')}")
        answer_citations = accepted_answer.get("citation", [])
        if isinstance(answer_citations, str):
            answer_citations = [answer_citations]
        if set(answer_citations) != expected_citations:
            errors.append(f"faq.jsonld citation drift for: {question.get('question')}")

    project_nodes = {node.get("@id", ""): node for node in graph_nodes(person_schema)}
    featured_list_id = f"{GITHUB_BLOB}/llms-index.json#featured-projects"
    featured_list = project_nodes.get(featured_list_id)
    expected_featured_project_ids = {f"{project.get('caseStudy')}#project" for project in data.get("featuredProjects", [])}
    expected_featured_project_urls = {
        project.get("caseStudy")
        for project in data.get("featuredProjects", [])
        if isinstance(project.get("caseStudy"), str)
    }
    if not featured_list or "ItemList" not in node_types(featured_list):
        errors.append("person.jsonld missing featured projects ItemList")
    else:
        if "CreativeWork" not in node_types(featured_list):
            errors.append("person.jsonld featured projects ItemList must also be CreativeWork")
        if featured_list.get("description") != featured_projects_list_description(data):
            errors.append("person.jsonld featured projects ItemList description drift")
        if featured_list.get("abstract") != featured_list.get("description"):
            errors.append("person.jsonld featured projects ItemList abstract drift")
        if featured_list.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld featured projects ItemList about drift")
        if featured_list.get("publisher", {}).get("@id") != person_id:
            errors.append("person.jsonld featured projects ItemList publisher drift")
        if featured_list.get("isPartOf", {}).get("@id") != f"{GITHUB_BLOB}/llms-index.json#creativework":
            errors.append("person.jsonld featured projects ItemList isPartOf drift")
        if featured_list.get("inLanguage") != "en":
            errors.append("person.jsonld featured projects ItemList inLanguage must be en")
        if featured_list.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld featured projects ItemList dateModified drift")
        if featured_list.get("isAccessibleForFree") is not True:
            errors.append("person.jsonld featured projects ItemList must be marked isAccessibleForFree")
        if featured_list.get("numberOfItems") != len(data.get("featuredProjects", [])):
            errors.append("person.jsonld featured projects ItemList count drift")
        missing_featured_items = sorted(expected_featured_project_ids - item_list_ref_ids(featured_list.get("itemListElement")))
        if missing_featured_items:
            errors.append(f"person.jsonld featured projects ItemList missing: {missing_featured_items}")
        featured_item_urls = item_list_urls(featured_list.get("itemListElement"))
        missing_featured_urls = sorted(expected_featured_project_urls - featured_item_urls)
        if missing_featured_urls:
            errors.append(f"person.jsonld featured projects ItemList missing URLs: {missing_featured_urls}")
        bad_featured_urls = sorted(url for url in featured_item_urls if not is_absolute_http_url(url))
        if bad_featured_urls:
            errors.append(f"person.jsonld featured projects ItemList URLs must be absolute HTTP(S): {bad_featured_urls}")
        check_content_usage_policy(featured_list, data, "person.jsonld featured projects ItemList")
        check_global_citation(featured_list, data, "person.jsonld featured projects ItemList")
        check_ownership_metadata(featured_list, data, "person.jsonld featured projects ItemList")
        check_structured_data_provenance(featured_list, data, "person.jsonld featured projects ItemList")

    lab_list_id = f"{GITHUB_BLOB}/llms-index.json#hackathon-lab"
    lab_list = project_nodes.get(lab_list_id)
    expected_lab_project_ids = {lab_project_id(project) for project in data.get("hackathonLab", []) if lab_project_url(project)}
    expected_lab_project_urls = {lab_project_url(project) for project in data.get("hackathonLab", []) if lab_project_url(project)}
    if not lab_list or "ItemList" not in node_types(lab_list):
        errors.append("person.jsonld missing hackathon and lab ItemList")
    else:
        if "CreativeWork" not in node_types(lab_list):
            errors.append("person.jsonld hackathon and lab ItemList must also be CreativeWork")
        if lab_list.get("description") != lab_projects_list_description(data):
            errors.append("person.jsonld hackathon and lab ItemList description drift")
        if lab_list.get("abstract") != lab_list.get("description"):
            errors.append("person.jsonld hackathon and lab ItemList abstract drift")
        if lab_list.get("about", {}).get("@id") != person_id:
            errors.append("person.jsonld hackathon and lab ItemList about drift")
        if lab_list.get("publisher", {}).get("@id") != person_id:
            errors.append("person.jsonld hackathon and lab ItemList publisher drift")
        if lab_list.get("isPartOf", {}).get("@id") != f"{GITHUB_BLOB}/llms-index.json#creativework":
            errors.append("person.jsonld hackathon and lab ItemList isPartOf drift")
        if lab_list.get("inLanguage") != "en":
            errors.append("person.jsonld hackathon and lab ItemList inLanguage must be en")
        if lab_list.get("dateModified") != data.get("updated"):
            errors.append("person.jsonld hackathon and lab ItemList dateModified drift")
        if lab_list.get("isAccessibleForFree") is not True:
            errors.append("person.jsonld hackathon and lab ItemList must be marked isAccessibleForFree")
        if lab_list.get("numberOfItems") != len(data.get("hackathonLab", [])):
            errors.append("person.jsonld hackathon and lab ItemList count drift")
        missing_lab_items = sorted(expected_lab_project_ids - item_list_ref_ids(lab_list.get("itemListElement")))
        if missing_lab_items:
            errors.append(f"person.jsonld hackathon and lab ItemList missing: {missing_lab_items}")
        lab_item_urls = item_list_urls(lab_list.get("itemListElement"))
        missing_lab_urls = sorted(expected_lab_project_urls - lab_item_urls)
        if missing_lab_urls:
            errors.append(f"person.jsonld hackathon and lab ItemList missing URLs: {missing_lab_urls}")
        bad_lab_urls = sorted(url for url in lab_item_urls if not is_absolute_http_url(url))
        if bad_lab_urls:
            errors.append(f"person.jsonld hackathon and lab ItemList URLs must be absolute HTTP(S): {bad_lab_urls}")
        check_content_usage_policy(lab_list, data, "person.jsonld hackathon and lab ItemList")
        check_global_citation(lab_list, data, "person.jsonld hackathon and lab ItemList")
        check_ownership_metadata(lab_list, data, "person.jsonld hackathon and lab ItemList")
        check_structured_data_provenance(lab_list, data, "person.jsonld hackathon and lab ItemList")

    project_awards = awards_by_project(data)
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
        if project_node.get("mainEntityOfPage") != project.get("caseStudy"):
            errors.append(f"person.jsonld featured project mainEntityOfPage drift: {project.get('name')}")
        if project_node.get("description") != project.get("focus"):
            errors.append(f"person.jsonld featured project description drift: {project.get('name')}")
        if project_node.get("creator", {}).get("@id") != person_id:
            errors.append(f"person.jsonld featured project creator drift: {project.get('name')}")
        if project_node.get("author", {}).get("@id") != person_id:
            errors.append(f"person.jsonld featured project author drift: {project.get('name')}")
        if project_node.get("publisher", {}).get("@id") != person_id:
            errors.append(f"person.jsonld featured project publisher drift: {project.get('name')}")
        if project_node.get("about", {}).get("@id") != person_id:
            errors.append(f"person.jsonld featured project about drift: {project.get('name')}")
        if project_node.get("inLanguage") != "en":
            errors.append(f"person.jsonld featured project inLanguage must be en: {project.get('name')}")
        if project_node.get("dateModified") != data.get("updated"):
            errors.append(f"person.jsonld featured project dateModified drift: {project.get('name')}")
        if project_node.get("isAccessibleForFree") is not True:
            errors.append(f"person.jsonld featured project must be marked isAccessibleForFree: {project.get('name')}")
        expected_awards = project_awards.get(project.get("name", ""), [])
        if expected_awards and project_node.get("award") != expected_awards:
            errors.append(f"person.jsonld featured project award drift: {project.get('name')}")
        if not expected_awards and "award" in project_node:
            errors.append(f"person.jsonld featured project unexpected award: {project.get('name')}")
        check_content_usage_policy(project_node, data, f"person.jsonld featured project {project.get('name')}")
        check_global_citation(project_node, data, f"person.jsonld featured project {project.get('name')}")
        check_ownership_metadata(project_node, data, f"person.jsonld featured project {project.get('name')}")
        check_structured_data_provenance(project_node, data, f"person.jsonld featured project {project.get('name')}")
        expected_image = expected_project_image(project)
        if not expected_image:
            errors.append(f"person.jsonld featured project cannot resolve cover image: {project.get('name')}")
            continue
        if project_node.get("image", {}).get("@id") != expected_image["@id"]:
            errors.append(f"person.jsonld featured project image ref drift: {project.get('name')}")
        if project_node.get("thumbnailUrl") != expected_image["url"]:
            errors.append(f"person.jsonld featured project thumbnailUrl drift: {project.get('name')}")
        image_node = project_nodes.get(expected_image["@id"])
        if not image_node or "ImageObject" not in node_types(image_node):
            errors.append(f"person.jsonld missing featured project ImageObject: {project.get('name')}")
            continue
        if image_node.get("url") != expected_image["url"]:
            errors.append(f"person.jsonld featured project image url drift: {project.get('name')}")
        if image_node.get("contentUrl") != expected_image["url"]:
            errors.append(f"person.jsonld featured project image contentUrl drift: {project.get('name')}")
        if image_node.get("encodingFormat") != expected_image["encodingFormat"]:
            errors.append(f"person.jsonld featured project image encodingFormat drift: {project.get('name')}")
        if image_node.get("description") != project_image_description(project):
            errors.append(f"person.jsonld featured project image description drift: {project.get('name')}")
        if image_node.get("abstract") != image_node.get("description"):
            errors.append(f"person.jsonld featured project image abstract drift: {project.get('name')}")
        for key in ("contentSize", "sha256"):
            if image_node.get(key) != expected_image[key]:
                errors.append(f"person.jsonld featured project image {key} drift: {project.get('name')}")
        check_image_rights(image_node, data, f"person.jsonld featured project image {project.get('name')}")
        if image_node.get("about", {}).get("@id") != expected:
            errors.append(f"person.jsonld featured project image about drift: {project.get('name')}")
        if image_node.get("isPartOf", {}).get("@id") != expected:
            errors.append(f"person.jsonld featured project image isPartOf drift: {project.get('name')}")
        if image_node.get("dateModified") != data.get("updated"):
            errors.append(f"person.jsonld featured project image dateModified drift: {project.get('name')}")

    for project in data.get("hackathonLab", []):
        expected = lab_project_id(project)
        project_node = project_nodes.get(expected)
        if not project_node:
            errors.append(f"person.jsonld missing hackathon/lab project node: {project.get('name')}")
            continue
        expected_url = lab_project_url(project)
        if "CreativeWork" not in node_types(project_node):
            errors.append(f"person.jsonld hackathon/lab project node must be CreativeWork: {project.get('name')}")
        if project_node.get("url") != expected_url:
            errors.append(f"person.jsonld hackathon/lab project url drift: {project.get('name')}")
        if project_node.get("mainEntityOfPage") != expected_url:
            errors.append(f"person.jsonld hackathon/lab project mainEntityOfPage drift: {project.get('name')}")
        if project_node.get("description") != project.get("focus"):
            errors.append(f"person.jsonld hackathon/lab project description drift: {project.get('name')}")
        if project_node.get("creator", {}).get("@id") != person_id:
            errors.append(f"person.jsonld hackathon/lab project creator drift: {project.get('name')}")
        if project_node.get("author", {}).get("@id") != person_id:
            errors.append(f"person.jsonld hackathon/lab project author drift: {project.get('name')}")
        if project_node.get("publisher", {}).get("@id") != person_id:
            errors.append(f"person.jsonld hackathon/lab project publisher drift: {project.get('name')}")
        if project_node.get("about", {}).get("@id") != person_id:
            errors.append(f"person.jsonld hackathon/lab project about drift: {project.get('name')}")
        expected_parent = data.get("identifiers", {}).get("portfolioWebsite") if project.get("caseStudy") else data.get("identifiers", {}).get("githubProfileIndex")
        if project_node.get("isPartOf", {}).get("@id") != expected_parent:
            errors.append(f"person.jsonld hackathon/lab project isPartOf drift: {project.get('name')}")
        if project_node.get("inLanguage") != "en":
            errors.append(f"person.jsonld hackathon/lab project inLanguage must be en: {project.get('name')}")
        if project_node.get("dateModified") != data.get("updated"):
            errors.append(f"person.jsonld hackathon/lab project dateModified drift: {project.get('name')}")
        if project_node.get("isAccessibleForFree") is not True:
            errors.append(f"person.jsonld hackathon/lab project must be marked isAccessibleForFree: {project.get('name')}")
        expected_same_as = [
            value
            for value in unique_compact(
                [
                    project.get("caseStudy"),
                    project.get("demo"),
                    project.get("live"),
                    project.get("repo"),
                    project.get("model"),
                ]
            )
            if value != expected_url
        ]
        if project_node.get("sameAs") != expected_same_as:
            errors.append(f"person.jsonld hackathon/lab project sameAs drift: {project.get('name')}")
        if project_node.get("genre") != "Hackathon and lab project":
            errors.append(f"person.jsonld hackathon/lab project genre drift: {project.get('name')}")
        check_content_usage_policy(project_node, data, f"person.jsonld hackathon/lab project {project.get('name')}")
        check_global_citation(project_node, data, f"person.jsonld hackathon/lab project {project.get('name')}")
        check_ownership_metadata(project_node, data, f"person.jsonld hackathon/lab project {project.get('name')}")
        check_structured_data_provenance(project_node, data, f"person.jsonld hackathon/lab project {project.get('name')}")


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
        root_images = root_url.findall("image:image", ns) if root_url is not None else []
        if not root_images:
            errors.append("sitemap.xml root URL missing primary image sitemap entry")
        else:
            root_image_locs = [image.findtext("image:loc", default="", namespaces=ns) for image in root_images]
            if root_image_locs != [PAGES_PRIMARY_IMAGE]:
                errors.append("sitemap.xml primary image loc drift")
        readme_url = next(
            (url for url in sitemap.findall(".//sm:url", ns) if url.findtext("sm:loc", default="", namespaces=ns) == f"{PAGES}/README.md"),
            None,
        )
        readme_images = readme_url.findall("image:image", ns) if readme_url is not None else []
        readme_image_locs = [image.findtext("image:loc", default="", namespaces=ns) for image in readme_images]
        expected_project_images = featured_project_cover_urls()
        if readme_image_locs != expected_project_images:
            errors.append("sitemap.xml README.md image entries must match featured project cover assets")
        for image in root_images + readme_images:
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
    check_portfolio_sync_artifacts(data)
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
