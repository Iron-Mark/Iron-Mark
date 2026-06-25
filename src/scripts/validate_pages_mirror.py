#!/usr/bin/env python3
"""Build and validate the GitHub Pages mirror artifact in a temp directory."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from build_pages_mirror import featured_project_cover_urls, project_cover_asset, rewrite_github_public_urls
from generate_schema import (
    DATASET_DATE_PUBLISHED,
    PROVIDE_SERVICE_BUSINESS_FUNCTION,
    SERVICE_PROVIDER_MOBILITY,
    available_languages,
    content_language,
    contact_action_description,
    contact_action_name,
    contact_action_platforms,
    contact_entry_content_type,
    contact_entry_description,
    contact_entry_http_method,
    contact_entry_name,
    data_catalog_description,
    data_catalog_name,
    dataset_alternate_names,
    dataset_measurement_techniques,
    dataset_temporal_coverage,
    download_description,
    download_id,
    download_integrity_metadata,
    faq_document_identifier,
    faq_item_identifier,
    faq_question_id,
    featured_projects_list_description,
    lab_projects_list_description,
    lab_project_id,
    lab_project_url,
    machine_downloads,
    offer_availability,
    offer_description,
    pages_section_id,
    pages_section_nav_item_id,
    pages_section_navigation_id,
    pages_section_relation_ids,
    pages_section_specs,
    person_core_identity,
    person_email,
    person_hiring_contact,
    person_knows_about,
    person_languages,
    person_main_entity_pages,
    person_occupations,
    person_subjects,
    person_work_locations,
    primary_image_description,
    profile_page_part_ids,
    profile_keywords,
    project_image_description,
    service_audience,
    service_channel_description,
    service_channel_name,
    service_description,
    service_focus_identifier,
    slugify,
    unique_compact,
)

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
PUBLIC = ROOT / "public"
PAGES_BASE = "https://iron-mark.github.io/Iron-Mark"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
GITHUB_RAW = "https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main"
PAGES_HOST = "iron-mark.github.io"
PAGES_SITE_NAME = "Mark Siazon Profile Index"
PAGES_SITE_ALTERNATE_NAMES = {"Iron-Mark Profile Index", "Mark Siazon GitHub Profile Index"}
PAGES_SOCIAL_IMAGE = f"{PAGES_BASE}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.png"
SOCIAL_IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
SOCIAL_IMAGE_WIDTH = 1200
SOCIAL_IMAGE_HEIGHT = 675
OPEN_GRAPH_LOCALE = "en_US"
FAVICON_HREF = "assets/brand/mark-siazon-favicon.svg"
IMAGE_SITEMAP_NS = "http://www.google.com/schemas/sitemap-image/1.1"
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

ROOT_FILES = ("llms.txt", "llms-index.json", "humans.txt", "robots.txt", "sitemap.xml")
PUBLIC_FILES = (
    "README.md",
    "FAQ.md",
    "RECRUITER.md",
    "PROOF.md",
    "LAB.md",
    "PROFILE.md",
    "STACK.md",
    "HOW-TO-CITE.md",
    "LICENSE.md",
    "CITATION.cff",
    "llms-full.txt",
    "llms-ctx-full.txt",
)
REQUIRED_FILES = (
    "index.html",
    "README.md",
    "llms.txt",
    "llms-index.json",
    "llms-full.txt",
    "llms-ctx-full.txt",
    "FAQ.md",
    "RECRUITER.md",
    "PROOF.md",
    "lab/index.html",
    "LAB.md",
    "STACK.md",
    "HOW-TO-CITE.md",
    "schema/llms-index.schema.json",
    "schema/person.jsonld",
    "schema/faq.jsonld",
    "robots.txt",
    "sitemap.xml",
)
FORBIDDEN_FILES = ("AGENTS.md",)
TEXT_SUFFIXES = {".md", ".txt", ".xml", ".html", ".json", ".jsonld", ".cff"}
PRODUCTION_ARTIFACT_SURFACES = {"index.html", "README.md", "llms.txt", "humans.txt", "robots.txt", "sitemap.xml"}
PRODUCTION_ARTIFACT_FORBIDDEN_LINKS = {
    ".github/": "GitHub maintenance files",
    "docs/internal/": "internal maintainer docs",
    "src/": "source/development files",
    "src/mcp-server": "optional local MCP server docs",
    "src/scripts/": "maintenance scripts",
    "src/portfolio-sync": "portfolio sync helper files",
    "AGENTS.md": "agent maintenance instructions",
    "mcp-server": "optional local MCP server docs",
    "REPO_SETUP": "repo setup checklist",
}
PRODUCTION_ARTIFACT_FORBIDDEN_PATTERNS = {
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


def repo_public_url_values(value: object) -> list[str]:
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
    if isinstance(value, str) and value.startswith("https://github.com/Iron-Mark/Iron-Mark/blob/main/public/"):
        return [value]
    return []


def jsonld_nodes(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        nodes: list[dict[str, object]] = [value]
        graph = value.get("@graph", [])
        if isinstance(graph, list):
            nodes.extend(node for node in graph if isinstance(node, dict))
        return nodes
    if isinstance(value, list):
        return [node for node in value if isinstance(node, dict)]
    return []


def check_jsonld_graph_integrity(issues: list[str], value: object, label: str) -> None:
    if not isinstance(value, dict):
        issues.append(f"{label} must be a JSON-LD object")
        return
    if value.get("@context") != "https://schema.org":
        issues.append(f"{label} must declare Schema.org @context")
    graph = value.get("@graph")
    if not isinstance(graph, list) or not graph:
        issues.append(f"{label} must contain a non-empty @graph")
        return

    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []
    for position, node in enumerate(graph, start=1):
        if not isinstance(node, dict):
            issues.append(f"{label} @graph item #{position} must be an object")
            continue
        node_id = node.get("@id")
        if not isinstance(node_id, str) or not node_id:
            issues.append(f"{label} @graph item #{position} missing stable @id")
        elif node_id in seen_ids:
            duplicate_ids.append(node_id)
        else:
            seen_ids.add(node_id)
        raw_type = node.get("@type")
        if not isinstance(raw_type, str) and not (
            isinstance(raw_type, list) and any(isinstance(item, str) and item for item in raw_type)
        ):
            issues.append(f"{label} @graph item #{position} missing @type")
    if duplicate_ids:
        issues.append(f"{label} contains duplicate @id values: {sorted(set(duplicate_ids))}")


def node_type_set(node: dict[str, object]) -> set[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def has_english_knows_language(node: dict[str, object]) -> bool:
    languages = node.get("knowsLanguage", [])
    if isinstance(languages, dict):
        languages = [languages]
    if not isinstance(languages, list):
        return False
    return any(
        isinstance(language, dict)
        and language.get("@type") == "Language"
        and language.get("name") == "English"
        and language.get("alternateName") == content_language()
        for language in languages
    )


def ref_ids(value: object) -> set[str]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return set()
    return {item.get("@id", "") for item in value if isinstance(item, dict)}


def area_names(value: object) -> set[str]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return set()
    return {item.get("name", "") for item in value if isinstance(item, dict) and item.get("name")}


def expected_area_nodes(regions: list[object]) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    for region_value in regions:
        region = str(region_value)
        region_lower = region.lower()
        if region_lower == "philippines":
            nodes.append({"@type": "Country", "name": "Philippines"})
        elif "remote" in region_lower:
            nodes.append({"@type": "VirtualLocation", "name": region})
        else:
            nodes.append({"@type": "AdministrativeArea", "name": region})
    return nodes


def item_list_ref_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    refs: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        item_ref = item.get("item", {})
        if isinstance(item_ref, dict) and item_ref.get("@id"):
            refs.add(str(item_ref["@id"]))
    return refs


def item_list_urls(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        item["url"]
        for item in value
        if isinstance(item, dict) and isinstance(item.get("url"), str)
    }


def expected_project_image(project: dict[str, object]) -> dict[str, str] | None:
    asset = project_cover_asset(str(project.get("slug", "")))
    if not asset:
        return None
    url = f"{PAGES_BASE}/{asset}"
    return {
        "@id": f"{url}#image",
        "url": url,
        "encodingFormat": PROJECT_IMAGE_ENCODING.get(Path(asset).suffix, ""),
        **file_integrity_metadata(ROOT / asset),
    }


def file_integrity_metadata(path: Path) -> dict[str, str]:
    if path.suffix.lower() == ".svg":
        data = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    else:
        data = path.read_bytes()
    return {
        "contentSize": f"{len(data)} bytes",
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def expected_dataset_measurements(index_data: dict[str, object]) -> list[dict[str, object]]:
    availability = index_data.get("availability", {})
    seo = index_data.get("seo", {})
    aeo = index_data.get("aeo", {})
    entity = index_data.get("entity", {})
    if not isinstance(availability, dict):
        availability = {}
    if not isinstance(seo, dict):
        seo = {}
    if not isinstance(aeo, dict):
        aeo = {}
    if not isinstance(entity, dict):
        entity = {}
    area_served = availability.get("areaServed", [])
    if not isinstance(area_served, list):
        area_served = []
    featured_projects = index_data.get("featuredProjects", [])
    if not isinstance(featured_projects, list):
        featured_projects = []
    lab_projects = index_data.get("hackathonLab", [])
    if not isinstance(lab_projects, list):
        lab_projects = []
    achievements = index_data.get("achievements", [])
    if not isinstance(achievements, list):
        achievements = []
    answer_snippets = aeo.get("answerSnippets", [])
    if not isinstance(answer_snippets, list):
        answer_snippets = []
    primary_keywords = seo.get("primaryKeywords", [])
    if not isinstance(primary_keywords, list):
        primary_keywords = []
    machine_readable = index_data.get("machineReadable", {})
    if not isinstance(machine_readable, dict):
        machine_readable = {}
    pages = machine_readable.get("pages", {})
    if not isinstance(pages, dict):
        pages = {}
    return [
        {
            "@type": "PropertyValue",
            "name": "Person entity identifier",
            "value": entity.get("@id"),
        },
        {
            "@type": "PropertyValue",
            "name": "Featured project count",
            "value": len(featured_projects),
        },
        {
            "@type": "PropertyValue",
            "name": "Hackathon and lab project count",
            "value": len(lab_projects),
        },
        {
            "@type": "PropertyValue",
            "name": "Verified achievement count",
            "value": len(achievements),
        },
        {
            "@type": "PropertyValue",
            "name": "Answer snippet count",
            "value": len(answer_snippets),
        },
        {
            "@type": "PropertyValue",
            "name": "Primary keyword count",
            "value": len(primary_keywords),
        },
        {
            "@type": "PropertyValue",
            "name": "Service regions",
            "value": ", ".join(str(region) for region in area_served),
        },
        {
            "@type": "PropertyValue",
            "name": "Machine-readable download count",
            "value": len(machine_downloads(pages)),
        },
    ]


def expected_citation_targets(index_data: dict[str, object]) -> list[str]:
    aeo = index_data.get("aeo", {})
    if not isinstance(aeo, dict):
        aeo = {}
    preferred = aeo.get("preferredCitationOrder", [])
    if not isinstance(preferred, list):
        preferred = []
    values = [
        *(str(item) for item in preferred if isinstance(item, str) and item),
        f"{PAGES_BASE}/HOW-TO-CITE.md",
        f"{PAGES_BASE}/CITATION.cff",
    ]
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


def expected_mention_ids(index_data: dict[str, object]) -> set[str]:
    availability = index_data.get("availability", {})
    if not isinstance(availability, dict):
        availability = {}
    focus_items = availability.get("focus", [])
    if not isinstance(focus_items, list):
        focus_items = []
    service_ids = {
        f"https://www.marksiazon.dev/#service-{slugify(str(focus))}"
        for focus in focus_items
        if focus
    }
    project_ids = {
        f"{project.get('caseStudy')}#project"
        for project in index_data.get("featuredProjects", [])
        if isinstance(project, dict) and project.get("caseStudy")
    }
    lab_project_ids = {
        lab_project_id(project)
        for project in index_data.get("hackathonLab", [])
        if isinstance(project, dict) and lab_project_url(project)
    }
    return {
        f"{GITHUB_BLOB}/llms-index.json#featured-projects",
        f"{GITHUB_BLOB}/llms-index.json#hackathon-lab",
        "https://www.marksiazon.dev/#services",
        *service_ids,
        *project_ids,
        *lab_project_ids,
    }


def expected_profile_disambiguating_description(index_data: dict[str, object]) -> str:
    entity = index_data.get("entity", {})
    name = entity.get("name") if isinstance(entity, dict) else ""
    return (
        f"{name} is the Philippines-based product designer and full-stack developer "
        "behind the Iron-Mark GitHub profile, marksiazon.dev portfolio, and proof-backed AI, "
        "mobile, Web3, and client web case studies."
    )


def expected_person_identifiers(index_data: dict[str, object]) -> list[dict[str, str]]:
    entity = index_data.get("entity", {})
    canonical = index_data.get("canonical", {})
    entity_url = entity.get("url", "") if isinstance(entity, dict) else ""
    github_profile = canonical.get("githubProfileReadme", "") if isinstance(canonical, dict) else ""
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
            "value": entity_url,
            "url": entity_url,
        },
        {
            "@type": "PropertyValue",
            "propertyID": "GitHub profile repository",
            "value": "Iron-Mark/Iron-Mark",
            "url": github_profile,
        },
    ]


def awards_by_project(index_data: dict[str, object]) -> dict[str, list[str]]:
    awards: dict[str, list[str]] = {}
    achievements = index_data.get("achievements", [])
    if not isinstance(achievements, list):
        return awards
    for achievement in achievements:
        if not isinstance(achievement, dict):
            continue
        project = achievement.get("project")
        title = achievement.get("title")
        if not isinstance(project, str) or not isinstance(title, str):
            continue
        awards.setdefault(project, []).append(title)
    return awards


def pages_significant_links(index_data: dict[str, object]) -> list[str]:
    machine_readable = index_data.get("machineReadable", {})
    pages = machine_readable.get("pages", {}) if isinstance(machine_readable, dict) else {}
    if not isinstance(pages, dict):
        pages = {}
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


def pages_related_links(index_data: dict[str, object]) -> list[str]:
    machine_readable = index_data.get("machineReadable", {})
    pages = machine_readable.get("pages", {}) if isinstance(machine_readable, dict) else {}
    if not isinstance(pages, dict):
        pages = {}
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


def expected_pages_speakable_selectors(index_data: dict[str, object]) -> list[str]:
    selectors = ["#profile-summary"]
    aeo = index_data.get("aeo", {})
    snippets = aeo.get("answerSnippets", []) if isinstance(aeo, dict) else []
    if not isinstance(snippets, list):
        snippets = []
    for item in snippets[:3]:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        if isinstance(question, str) and question:
            selectors.append(f"#{answer_dom_id(question)}")
    return selectors


def expected_pages_speakable(index_data: dict[str, object]) -> dict[str, object]:
    return {
        "@type": "SpeakableSpecification",
        "@id": f"{PAGES_BASE}/#speakable",
        "cssSelector": expected_pages_speakable_selectors(index_data),
    }


def expected_topic_terms(index_data: dict[str, object]) -> list[str]:
    seo = index_data.get("seo", {})
    availability = index_data.get("availability", {})
    primary = seo.get("primaryKeywords", []) if isinstance(seo, dict) else []
    focus = availability.get("focus", []) if isinstance(availability, dict) else []
    geo = seo.get("geoTargets", []) if isinstance(seo, dict) else []
    return unique_compact(
        [str(item) for item in primary if isinstance(item, str)]
        + [str(item) for item in focus if isinstance(item, str)]
        + [str(item) for item in geo if isinstance(item, str)]
    )


def topic_term_set_id() -> str:
    return f"{PAGES_BASE}/#topic-taxonomy"


def topic_term_id(value: str) -> str:
    return f"{PAGES_BASE}/#term-{slugify(value)}"


def expected_topic_term_description(index_data: dict[str, object], value: str) -> str:
    seo = index_data.get("seo", {})
    availability = index_data.get("availability", {})
    geo = seo.get("geoTargets", []) if isinstance(seo, dict) else []
    focus = availability.get("focus", []) if isinstance(availability, dict) else []
    if value in geo:
        return f"Geographic service target for the Mark Siazon profile index: {value}."
    if value in focus:
        return f"Service focus for Mark Siazon hiring and collaboration discovery: {value}."
    return f"Primary search and answer-engine topic for the Mark Siazon profile index: {value}."


def pages_rewrite_public_source(source: str) -> str:
    replacements = (
        (f"{GITHUB_BLOB}/public/schema/", f"{PAGES_BASE}/schema/"),
        (f"{GITHUB_BLOB}/public/", f"{PAGES_BASE}/"),
        (f"{GITHUB_RAW}/public/schema/", f"{PAGES_BASE}/schema/"),
        (f"{GITHUB_RAW}/public/", f"{PAGES_BASE}/"),
    )
    for prefix, replacement in replacements:
        if source.startswith(prefix):
            return source.replace(prefix, replacement, 1)
    return source


def pages_rewrite_ids(values: list[str]) -> set[str]:
    return {pages_rewrite_public_source(value) for value in values if value}


def pages_rewrite_agent_surface(surface: str) -> str:
    if surface.startswith("public/"):
        return surface.removeprefix("public/")
    return surface


def check_pages_generated_context(issues: list[str], artifact: Path, index_data: dict[str, object]) -> None:
    path = artifact / "llms-ctx-full.txt"
    if not path.exists():
        issues.append("Pages artifact missing llms-ctx-full.txt")
        return
    text = path.read_text(encoding="utf-8")
    seo = index_data.get("seo", {})
    if not isinstance(seo, dict):
        seo = {}
    geo_signals = seo.get("geoSignals", {})
    if not isinstance(geo_signals, dict):
        geo_signals = {}
    generative = seo.get("generativeSearch", {})
    if not isinstance(generative, dict):
        generative = {}
    if "## Search and discovery signals" not in text:
        issues.append("Pages llms-ctx-full.txt missing Search and discovery signals section")
    expected_search_lines = [
        f"- Primary keywords: {', '.join(seo.get('primaryKeywords', []))}",
        f"- Geo targets: {', '.join(seo.get('geoTargets', []))}",
        f"- Home country: {geo_signals.get('homeCountry', '')}",
        f"- Search modifiers: {', '.join(geo_signals.get('searchModifiers', []))}",
    ]
    for line in expected_search_lines:
        if line not in text:
            issues.append(f"Pages llms-ctx-full.txt missing search signal line: {line}")
    if "## Generative search guidance" not in text:
        issues.append("Pages llms-ctx-full.txt missing Generative search guidance section")
    for line in (
        f"- Principle: {generative.get('principle', '')}",
        f"- llms.txt role: {generative.get('llmsTxtRole', '')}",
    ):
        if line not in text:
            issues.append(f"Pages llms-ctx-full.txt missing generative guidance line: {line}")
    for source in generative.get("answerSources", []):
        expected = pages_rewrite_public_source(str(source))
        if f"- {expected}" not in text:
            issues.append(f"Pages llms-ctx-full.txt missing generative answer source: {expected}")
    for surface in generative.get("agentReadySurfaces", []):
        expected = pages_rewrite_agent_surface(str(surface))
        if f"- {expected}" not in text:
            issues.append(f"Pages llms-ctx-full.txt missing agent-ready surface: {expected}")
    aeo = index_data.get("aeo", {})
    if not isinstance(aeo, dict):
        aeo = {}
    if "## Preferred citation order" not in text:
        issues.append("Pages llms-ctx-full.txt missing Preferred citation order section")
    for source in aeo.get("preferredCitationOrder", []):
        expected = pages_rewrite_public_source(str(source))
        if f"- {expected}" not in text:
            issues.append(f"Pages llms-ctx-full.txt missing preferred citation source: {expected}")


def check_global_citation(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    if node.get("citation") != expected_citation_targets(index_data):
        issues.append(f"{label} citation chain drift")


def check_expected_mentions(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    missing = sorted(expected_mention_ids(index_data) - ref_ids(node.get("mentions")))
    if missing:
        issues.append(f"{label} mentions missing: {missing}")


def check_person_identity_resolution(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    if node.get("disambiguatingDescription") != expected_profile_disambiguating_description(index_data):
        issues.append(f"{label} disambiguatingDescription drift")
    if node.get("identifier") != expected_person_identifiers(index_data):
        issues.append(f"{label} identifier drift")
    entity = index_data.get("entity", {})
    if not isinstance(entity, dict) or node.get("sameAs") != entity.get("sameAs", []):
        issues.append(f"{label} sameAs drift")
    if node.get("image", {}).get("@id") != f"{PAGES_BASE}/#primary-image":
        issues.append(f"{label} image drift")
    if not has_english_knows_language(node):
        issues.append(f"{label} knowsLanguage must include English language node")


def check_creativework_abstract(issues: list[str], node: dict[str, object], label: str) -> None:
    if not (node_type_set(node) & ABSTRACT_REQUIRED_TYPES):
        return
    description = node.get("description")
    if not isinstance(description, str) or not description:
        return
    if node.get("abstract") != description:
        issues.append(f"{label} abstract must match description")


def is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def check_jsonld_absolute_url_values(issues: list[str], node: dict[str, object], label: str) -> None:
    def check_url_value(value: object, path: str) -> None:
        if isinstance(value, str):
            if not is_absolute_http_url(value):
                issues.append(f"{label} {path} must be an absolute HTTP(S) URL")
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
        issues.append(f"{label} {path} must be an absolute HTTP(S) URL")

    def walk(value: object, path: str) -> None:
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


def check_dataset_search_metadata(issues: list[str], node: dict[str, object], label: str) -> None:
    types = node_type_set(node) & DATASET_SEARCH_TYPES
    if not types:
        return
    name = node.get("name")
    if not isinstance(name, str) or not name.strip():
        issues.append(f"{label} must expose a non-empty name")
    elif len(name) > DATASET_TEXT_MAX_CHARS:
        issues.append(f"{label} name must stay within {DATASET_TEXT_MAX_CHARS} characters")
    for key in ("description", "abstract"):
        value = node.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{label} must expose a non-empty {key}")
            continue
        if len(value) < DATASET_TEXT_MIN_CHARS:
            issues.append(f"{label} {key} must be at least {DATASET_TEXT_MIN_CHARS} characters")
        if len(value) > DATASET_TEXT_MAX_CHARS:
            issues.append(f"{label} {key} must stay within {DATASET_TEXT_MAX_CHARS} characters")
    required_url_properties = set()
    for node_type in types:
        required_url_properties.update(DATASET_URL_PROPERTIES_BY_TYPE.get(node_type, ()))
    for key in sorted(required_url_properties):
        value = node.get(key)
        if not isinstance(value, str) or not is_absolute_http_url(value):
            issues.append(f"{label} {key} must be an absolute HTTP(S) URL")


def check_image_rights(issues: list[str], node: dict[str, object], index_data: dict[str, object], label: str) -> None:
    entity = index_data.get("entity", {})
    availability = index_data.get("availability", {})
    if not isinstance(entity, dict) or not isinstance(availability, dict):
        issues.append(f"{label} cannot validate image rights metadata")
        return
    expected_name = entity.get("name")
    if node.get("license") != f"{PAGES_BASE}/LICENSE.md":
        issues.append(f"{label} license drift")
    if node.get("usageInfo") != f"{PAGES_BASE}/LICENSE.md":
        issues.append(f"{label} usageInfo drift")
    if node.get("acquireLicensePage") != availability.get("contact"):
        issues.append(f"{label} acquireLicensePage drift")
    if node.get("creditText") != expected_name:
        issues.append(f"{label} creditText drift")
    if node.get("copyrightNotice") != f"Copyright {expected_name}":
        issues.append(f"{label} copyrightNotice drift")
    creator = node.get("creator", {})
    if not isinstance(creator, dict):
        issues.append(f"{label} creator must be a Person object")
        return
    if creator.get("@id") != entity.get("@id"):
        issues.append(f"{label} creator @id drift")
    if creator.get("@type") != "Person":
        issues.append(f"{label} creator type drift")
    if creator.get("name") != expected_name:
        issues.append(f"{label} creator name drift")
    if creator.get("url") != entity.get("url"):
        issues.append(f"{label} creator url drift")
    check_publisher_metadata(issues, node, index_data, label)
    check_ownership_metadata(issues, node, index_data, label)
    check_structured_data_provenance(issues, node, index_data, label)


def png_dimensions(path: Path, issues: list[str]) -> tuple[int, int] | None:
    if not path.exists():
        issues.append(f"Pages artifact missing PNG image asset: {path}")
        return None
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        issues.append(f"Pages image asset must be PNG: {path}")
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def check_content_usage_policy(issues: list[str], node: dict[str, object], label: str) -> None:
    if node.get("usageInfo") != f"{PAGES_BASE}/HOW-TO-CITE.md":
        issues.append(f"{label} usageInfo drift")
    if node.get("publishingPrinciples") != f"{PAGES_BASE}/PROOF.md":
        issues.append(f"{label} publishingPrinciples drift")


def check_structured_data_provenance(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    entity = index_data.get("entity", {})
    if not isinstance(entity, dict):
        issues.append(f"{label} cannot validate sdPublisher")
        return
    publisher = node.get("sdPublisher", {})
    if not isinstance(publisher, dict):
        issues.append(f"{label} missing sdPublisher Person object")
        return
    if publisher.get("@type") != "Person":
        issues.append(f"{label} sdPublisher type drift")
    if publisher.get("@id") != entity.get("@id"):
        issues.append(f"{label} sdPublisher @id drift")
    if publisher.get("name") != entity.get("name"):
        issues.append(f"{label} sdPublisher name drift")
    if publisher.get("url") != entity.get("url"):
        issues.append(f"{label} sdPublisher url drift")
    if node.get("sdDatePublished") != index_data.get("updated"):
        issues.append(f"{label} sdDatePublished drift")
    if node.get("sdLicense") != f"{PAGES_BASE}/LICENSE.md":
        issues.append(f"{label} sdLicense drift")


def check_ownership_metadata(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    entity = index_data.get("entity", {})
    if not isinstance(entity, dict):
        issues.append(f"{label} cannot validate ownership metadata")
        return
    person_id = entity.get("@id")
    accountable = node.get("accountablePerson", {})
    if not isinstance(accountable, dict) or accountable.get("@id") != person_id:
        issues.append(f"{label} accountablePerson drift")
    holder = node.get("copyrightHolder", {})
    if not isinstance(holder, dict) or holder.get("@id") != person_id:
        issues.append(f"{label} copyrightHolder drift")
    expected_year = int(str(index_data.get("updated", "0000"))[:4])
    if node.get("copyrightYear") != expected_year:
        issues.append(f"{label} copyrightYear drift")


def check_publisher_metadata(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    entity = index_data.get("entity", {})
    if not isinstance(entity, dict):
        issues.append(f"{label} cannot validate publisher metadata")
        return
    publisher = node.get("publisher", {})
    if not isinstance(publisher, dict) or publisher.get("@id") != entity.get("@id"):
        issues.append(f"{label} publisher drift")


def check_review_metadata(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    entity = index_data.get("entity", {})
    if not isinstance(entity, dict):
        issues.append(f"{label} cannot validate review metadata")
        return
    reviewed_by = node.get("reviewedBy", {})
    if not isinstance(reviewed_by, dict) or reviewed_by.get("@id") != entity.get("@id"):
        issues.append(f"{label} reviewedBy drift")
    if node.get("lastReviewed") != index_data.get("updated"):
        issues.append(f"{label} lastReviewed drift")


def check_spatial_coverage(
    issues: list[str],
    node: dict[str, object],
    index_data: dict[str, object],
    label: str,
) -> None:
    availability = index_data.get("availability", {})
    if not isinstance(availability, dict):
        issues.append(f"{label} cannot validate spatialCoverage")
        return
    area_served = availability.get("areaServed", [])
    if not isinstance(area_served, list):
        area_served = []
    expected = expected_area_nodes(area_served)
    if node.get("spatialCoverage") != expected:
        issues.append(f"{label} spatialCoverage typed region drift")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def build_temp_artifact() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="iron-mark-pages-"))
    artifact = temp_root / "docs"
    copy_tree(DOCS, artifact)

    for name in ROOT_FILES:
        shutil.copy2(ROOT / name, artifact / name)
    for name in PUBLIC_FILES:
        shutil.copy2(PUBLIC / name, artifact / name)
    copy_tree(ROOT / "assets", artifact / "assets")
    copy_tree(PUBLIC / "schema", artifact / "schema")

    sys.path.insert(0, str(ROOT / "src" / "scripts"))
    from build_pages_mirror import rewrite_file  # noqa: PLC0415

    for path in sorted(artifact.rglob("*")):
        if path.is_file():
            rewrite_file(path)
    return artifact


def extract_local_links(path: Path, text: str) -> list[str]:
    links: list[str] = []
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)|href=\"([^\"]+)\"|src=\"([^\"]+)\"|srcset=\"([^\"]+)\"")
    for match in link_re.finditer(text):
        raw = next(group for group in match.groups() if group)
        if re.match(r"^(https?:|mailto:|#|data:)", raw, re.IGNORECASE):
            continue
        target = raw.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split()[0].split("#", 1)[0]
        if target:
            links.append(target)
    return links


def validate_artifact(artifact: Path) -> list[str]:
    issues: list[str] = []
    for name in REQUIRED_FILES:
        if not (artifact / name).is_file():
            issues.append(f"missing Pages artifact file: {name}")
    for name in FORBIDDEN_FILES:
        if (artifact / name).exists():
            issues.append(f"forbidden production Pages artifact file: {name}")

    for json_name in ("llms-index.json", "schema/llms-index.schema.json", "schema/person.jsonld", "schema/faq.jsonld"):
        try:
            parsed_json = json.loads((artifact / json_name).read_text(encoding="utf-8"))
            if json_name.endswith(".jsonld"):
                check_jsonld_graph_integrity(issues, parsed_json, f"Pages artifact {json_name}")
                for node in jsonld_nodes(parsed_json):
                    if "@graph" in node and "@id" not in node:
                        continue
                    check_jsonld_absolute_url_values(
                        issues,
                        node,
                        f"Pages artifact {json_name} {node.get('@id', node.get('name', 'node'))}",
                    )
        except Exception as exc:
            issues.append(f"invalid JSON in Pages artifact {json_name}: {exc}")
    try:
        index_data = json.loads((artifact / "llms-index.json").read_text(encoding="utf-8"))
    except Exception:
        index_data = {}
    faq_text = (artifact / "FAQ.md").read_text(encoding="utf-8") if (artifact / "FAQ.md").exists() else ""
    aeo = index_data.get("aeo", {}) if isinstance(index_data, dict) else {}
    snippets = aeo.get("answerSnippets", []) if isinstance(aeo, dict) else []
    for item in snippets:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", ""))
        answer = str(item.get("answer", ""))
        deployed_answer = rewrite_github_public_urls(answer)
        if question and question not in faq_text:
            issues.append(f"Pages FAQ.md missing visible AEO question: {question}")
        if deployed_answer and deployed_answer not in faq_text:
            issues.append(f"Pages FAQ.md missing visible AEO answer: {question}")
    for name in ("llms.txt", "humans.txt", "robots.txt"):
        path = artifact / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        non_ascii = sorted({f"U+{ord(char):04X}" for char in text if ord(char) > 127})
        if non_ascii:
            issues.append(f"Pages {name} must stay ASCII-only for plain-text crawler compatibility: {non_ascii}")
    for name in sorted(PRODUCTION_ARTIFACT_SURFACES):
        path = artifact / name
        if not path.exists():
            continue
        lower = path.read_text(encoding="utf-8").lower()
        for needle, reason in PRODUCTION_ARTIFACT_FORBIDDEN_LINKS.items():
            if needle.lower() in lower:
                issues.append(f"Pages {name} exposes {reason}: {needle}")
        for pattern, reason in PRODUCTION_ARTIFACT_FORBIDDEN_PATTERNS.items():
            if re.search(pattern, lower):
                issues.append(f"Pages {name} contains {reason}")
    check_pages_generated_context(issues, artifact, index_data)

    index_text = (artifact / "index.html").read_text(encoding="utf-8") if (artifact / "index.html").exists() else ""
    for needle in ("schema/llms-index.schema.json", "schema/person.jsonld", "schema/faq.jsonld", "llms-index.json"):
        if needle not in index_text:
            issues.append(f"Pages index missing reference: {needle}")
    jsonld_scripts = re.findall(
        r"<script\s+type=[\"']application/ld\+json[\"']>\s*(.*?)\s*</script>",
        index_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if len(jsonld_scripts) < 2:
        issues.append("Pages index must inline both Person/content and FAQ JSON-LD graphs")
    if '"@type": "Question"' not in index_text or '"acceptedAnswer"' not in index_text:
        issues.append("Pages index missing inline FAQ Question/Answer JSON-LD")
    public_url_values: list[str] = []
    parsed_jsonld_nodes: list[dict[str, object]] = []
    for index, script in enumerate(jsonld_scripts, start=1):
        try:
            jsonld = json.loads(script)
            check_jsonld_graph_integrity(issues, jsonld, f"Pages index inline JSON-LD script #{index}")
            public_url_values.extend(repo_public_url_values(jsonld))
            script_nodes = jsonld_nodes(jsonld)
            for node in script_nodes:
                if "@graph" in node and "@id" not in node:
                    continue
                check_jsonld_absolute_url_values(
                    issues,
                    node,
                    f"Pages index inline JSON-LD script #{index} {node.get('@id', node.get('name', 'node'))}",
                )
            parsed_jsonld_nodes.extend(script_nodes)
        except json.JSONDecodeError:
            issues.append("Pages index contains invalid inline JSON-LD")
    if public_url_values:
        issues.append(f"Pages index inline JSON-LD must use Pages URLs for deployed public files: {public_url_values}")
    for node in parsed_jsonld_nodes:
        label = f"Pages index {node.get('@id', node.get('name', 'node'))}"
        check_creativework_abstract(issues, node, label)
        check_dataset_search_metadata(issues, node, label)
    if "https://iron-mark.github.io/Iron-Mark/FAQ.md#faq" not in "\n".join(jsonld_scripts):
        issues.append("Pages index inline FAQ JSON-LD must use the Pages FAQ identifier")
    if '"@type": "ImageObject"' not in index_text:
        issues.append("Pages index inline JSON-LD missing ImageObject")
    if '"primaryImageOfPage"' not in index_text:
        issues.append("Pages index inline JSON-LD missing primaryImageOfPage")
    if PAGES_SOCIAL_IMAGE not in "\n".join(jsonld_scripts):
        issues.append("Pages index inline JSON-LD missing Pages social image URL")
    social_image_path = artifact / "assets" / "brand" / "mark-siazon-product-design-full-stack-profile-banner.png"
    primary_image = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#primary-image"), None)
    if not primary_image or "ImageObject" not in node_type_set(primary_image):
        issues.append("Pages index inline JSON-LD missing primary ImageObject node")
    else:
        if primary_image.get("url") != PAGES_SOCIAL_IMAGE:
            issues.append("Pages index primary ImageObject url drift")
        if primary_image.get("contentUrl") != PAGES_SOCIAL_IMAGE:
            issues.append("Pages index primary ImageObject contentUrl drift")
        if primary_image.get("encodingFormat") != "image/png":
            issues.append("Pages index primary ImageObject encodingFormat must be image/png")
        if primary_image.get("width") != SOCIAL_IMAGE_WIDTH:
            issues.append("Pages index primary ImageObject width drift")
        if primary_image.get("height") != SOCIAL_IMAGE_HEIGHT:
            issues.append("Pages index primary ImageObject height drift")
        if primary_image.get("caption") != SOCIAL_IMAGE_ALT:
            issues.append("Pages index primary ImageObject caption drift")
        if primary_image.get("description") != primary_image_description():
            issues.append("Pages index primary ImageObject description drift")
        if primary_image.get("abstract") != primary_image.get("description"):
            issues.append("Pages index primary ImageObject abstract drift")
        if social_image_path.exists():
            for key, expected in file_integrity_metadata(social_image_path).items():
                if primary_image.get(key) != expected:
                    issues.append(f"Pages index primary ImageObject {key} drift")
        check_image_rights(issues, primary_image, index_data, "Pages index primary ImageObject")
    if '"@type": "ContactAction"' not in index_text:
        issues.append("Pages index inline JSON-LD missing hiring ContactAction")
    if '"@type": "EntryPoint"' not in index_text:
        issues.append("Pages index inline JSON-LD missing hiring ContactAction EntryPoint")
    if "https://www.marksiazon.dev/contact" not in "\n".join(jsonld_scripts):
        issues.append("Pages index inline JSON-LD missing contact URL")
    availability = index_data.get("availability", {})
    if not isinstance(availability, dict):
        availability = {}
    contact_action = next(
        (node for node in parsed_jsonld_nodes if node.get("@id") == "https://www.marksiazon.dev/#contact-action"),
        None,
    )
    if not contact_action or "ContactAction" not in node_type_set(contact_action):
        issues.append("Pages index inline JSON-LD missing ContactAction node")
    else:
        if contact_action.get("name") != contact_action_name():
            issues.append("Pages index ContactAction name drift")
        if contact_action.get("description") != contact_action_description():
            issues.append("Pages index ContactAction description drift")
        if contact_action.get("target", {}).get("@id") != "https://www.marksiazon.dev/#contact-entrypoint":
            issues.append("Pages index ContactAction target drift")
        if contact_action.get("recipient", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index ContactAction recipient drift")
        if contact_action.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index ContactAction about drift")
        if contact_action.get("object", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index ContactAction object drift")
    contact_entry = next(
        (node for node in parsed_jsonld_nodes if node.get("@id") == "https://www.marksiazon.dev/#contact-entrypoint"),
        None,
    )
    if not contact_entry or "EntryPoint" not in node_type_set(contact_entry):
        issues.append("Pages index inline JSON-LD missing contact EntryPoint node")
    else:
        if contact_entry.get("name") != contact_entry_name():
            issues.append("Pages index contact EntryPoint name drift")
        if contact_entry.get("description") != contact_entry_description():
            issues.append("Pages index contact EntryPoint description drift")
        if contact_entry.get("urlTemplate") != availability.get("contact"):
            issues.append("Pages index contact EntryPoint urlTemplate drift")
        if contact_entry.get("contentType") != contact_entry_content_type():
            issues.append("Pages index contact EntryPoint contentType drift")
        if contact_entry.get("httpMethod") != contact_entry_http_method():
            issues.append("Pages index contact EntryPoint httpMethod drift")
        if contact_entry.get("inLanguage") != content_language():
            issues.append("Pages index contact EntryPoint inLanguage drift")
        if contact_entry.get("actionPlatform") != contact_action_platforms():
            issues.append("Pages index contact EntryPoint actionPlatform drift")
    if "Knowledge Graph" not in index_text:
        issues.append("Pages index missing visible Knowledge Graph section")
    if '<main id="main-content">' not in index_text:
        issues.append("Pages index main content must expose #main-content")
    if '<nav id="section-navigation" class="section-nav" aria-label="Profile index sections">' not in index_text:
        issues.append("Pages index must expose visible section navigation")
    for section in pages_section_specs(index_data):
        heading_tag = f'<h2 id="{section["fragment"]}">{section["heading"]}</h2>'
        if heading_tag not in index_text:
            issues.append(f"Pages index missing visible anchored section: {heading_tag}")
        section_link = f'<a href="#{section["fragment"]}">{section["heading"]}</a>'
        if section_link not in index_text:
            issues.append(f"Pages index missing section navigation link: {section_link}")
    for selector in expected_pages_speakable_selectors(index_data):
        if selector.startswith("#") and f'id="{selector[1:]}"' not in index_text:
            issues.append(f"Pages index missing speakable selector target: {selector}")
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
        if tag not in index_text:
            issues.append(f"Pages index missing social image metadata: {tag}")
    if png_dimensions(social_image_path, issues) != (SOCIAL_IMAGE_WIDTH, SOCIAL_IMAGE_HEIGHT):
        issues.append("Pages primary social image dimensions must match metadata")
    if f'<meta property="og:locale" content="{OPEN_GRAPH_LOCALE}"/>' not in index_text:
        issues.append("Pages index missing Open Graph locale metadata")
    updated = str(index_data.get("updated", ""))
    expected_modified_tags = {
        f'<meta property="og:updated_time" content="{updated}"/>',
        f'<meta property="article:modified_time" content="{updated}"/>',
        f'<meta itemprop="dateModified" content="{updated}"/>',
    }
    for tag in expected_modified_tags:
        if tag not in index_text:
            issues.append(f"Pages index missing modified-time metadata: {tag}")
    expected_site_name_tags = {
        f"<title>{PAGES_SITE_NAME}</title>",
        f'<meta property="og:title" content="{PAGES_SITE_NAME}"/>',
        f'<meta property="og:site_name" content="{PAGES_SITE_NAME}"/>',
        f'<meta name="twitter:title" content="{PAGES_SITE_NAME}"/>',
        f"<h1>{PAGES_SITE_NAME}</h1>",
    }
    for tag in expected_site_name_tags:
        if tag not in index_text:
            issues.append(f"Pages index site-name signal drift: {tag}")
    expected_hreflangs = {
        f'<link rel="alternate" hreflang="en" href="{PAGES_BASE}/"/>',
        f'<link rel="alternate" hreflang="x-default" href="{PAGES_BASE}/"/>',
    }
    for tag in expected_hreflangs:
        if tag not in index_text:
            issues.append(f"Pages index missing self-referencing hreflang link: {tag}")
    if 'aria-label="Breadcrumb"' not in index_text:
        issues.append("Pages index missing visible breadcrumb navigation")
    if f'<a href="https://www.marksiazon.dev">Mark Siazon Portfolio</a> / <span>{PAGES_SITE_NAME}</span>' not in index_text:
        issues.append("Pages index visible breadcrumb must match BreadcrumbList")
    if f'<link rel="icon" type="image/svg+xml" href="{FAVICON_HREF}"/>' not in index_text:
        issues.append("Pages index missing SVG favicon link")
    favicon = artifact / FAVICON_HREF
    favicon_text = favicon.read_text(encoding="utf-8") if favicon.exists() else ""
    if not favicon_text:
        issues.append("Pages artifact missing SVG favicon asset")
    elif 'viewBox="0 0 96 96"' not in favicon_text:
        issues.append("Pages SVG favicon must declare a square viewBox")
    if not any("Person" in node_type_set(node) and has_english_knows_language(node) for node in parsed_jsonld_nodes):
        issues.append("Pages index inline JSON-LD missing Person English knowsLanguage signal")
    person = next((node for node in parsed_jsonld_nodes if node.get("@id") == "https://www.marksiazon.dev/#person"), None)
    if not person or "Person" not in node_type_set(person):
        issues.append("Pages index inline JSON-LD missing Person node")
    elif ref_ids(person.get("mainEntityOfPage")) != ref_ids(person_main_entity_pages(index_data)):
        issues.append("Pages index inline JSON-LD Person mainEntityOfPage identity references drift")
    person_nodes = [
        node
        for node in parsed_jsonld_nodes
        if node.get("@id") == "https://www.marksiazon.dev/#person" and "Person" in node_type_set(node)
    ]
    for person_node in person_nodes:
        check_person_identity_resolution(issues, person_node, index_data, "Pages index Person")
    pages_topic_set_id = topic_term_set_id()
    if person:
        actual_person_identity = {key: person.get(key) for key in person_core_identity(index_data)}
        if actual_person_identity != person_core_identity(index_data):
            issues.append("Pages index Person core identity drift")
        if person.get("email") != person_email(index_data):
            issues.append("Pages index Person email drift")
        if person.get("hasOccupation") != person_occupations(index_data):
            issues.append("Pages index Person hasOccupation drift")
        if person.get("workLocation") != person_work_locations(index_data):
            issues.append("Pages index Person workLocation drift")
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
            issues.append("Pages index Person missing hiring contactPoint")
        elif hiring_contact != person_hiring_contact(index_data):
            issues.append("Pages index Person hiring contactPoint drift")
    if person:
        if person.get("knowsAbout") != person_knows_about(index_data):
            issues.append("Pages index Person knowsAbout drift")
        if person.get("knowsLanguage") != person_languages():
            issues.append("Pages index Person knowsLanguage drift")
        if pages_topic_set_id not in ref_ids(person.get("knowsAbout")):
            issues.append("Pages index Person knowsAbout missing topic taxonomy")
        missing_known_terms = sorted(
            {topic_term_id(term) for term in expected_topic_terms(index_data)}
            - ref_ids(person.get("knowsAbout"))
        )
        if missing_known_terms:
            issues.append(f"Pages index Person knowsAbout missing topic terms: {missing_known_terms}")
    availability = index_data.get("availability", {})
    if not isinstance(availability, dict):
        availability = {}
    focus_items = availability.get("focus", [])
    if not isinstance(focus_items, list):
        focus_items = []
    expected_offer_ids = {
        f"https://www.marksiazon.dev/#offer-{slugify(str(focus))}"
        for focus in focus_items
        if focus
    }
    expected_service_ids = {
        f"https://www.marksiazon.dev/#service-{slugify(str(focus))}"
        for focus in focus_items
        if focus
    }
    services_catalog_id = "https://www.marksiazon.dev/#services"
    service_channel_id = "https://www.marksiazon.dev/#hiring-service-channel"
    if person and person.get("hasOfferCatalog", {}).get("@id") != services_catalog_id:
        issues.append("Pages index Person hasOfferCatalog drift")
    if person:
        expected_subjects = pages_rewrite_ids([item["@id"] for item in person_subjects(index_data)])
        if ref_ids(person.get("subjectOf")) != expected_subjects:
            issues.append("Pages index Person subjectOf proof/schema references drift")
    offer_catalog = next((node for node in parsed_jsonld_nodes if node.get("@id") == services_catalog_id), None)
    if not offer_catalog or "OfferCatalog" not in node_type_set(offer_catalog):
        issues.append("Pages index inline JSON-LD missing services OfferCatalog")
    else:
        expected_catalog_identifier = {
            "@type": "PropertyValue",
            "propertyID": "Iron-Mark service catalog",
            "value": slugify("Mark Siazon services and availability"),
        }
        if offer_catalog.get("identifier") != expected_catalog_identifier:
            issues.append("Pages index OfferCatalog identifier drift")
        if offer_catalog.get("mainEntityOfPage") != availability.get("recruiterBrief"):
            issues.append("Pages index OfferCatalog mainEntityOfPage drift")
        if offer_catalog.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index OfferCatalog about drift")
        if offer_catalog.get("inLanguage") != content_language():
            issues.append("Pages index OfferCatalog inLanguage drift")
        if offer_catalog.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index OfferCatalog dateModified drift")
        if offer_catalog.get("isAccessibleForFree") is not True:
            issues.append("Pages index OfferCatalog must be isAccessibleForFree")
        if offer_catalog.get("numberOfItems") != len(expected_offer_ids):
            issues.append("Pages index OfferCatalog numberOfItems drift")
        if offer_catalog.get("itemListOrder") != "https://schema.org/ItemListOrderAscending":
            issues.append("Pages index OfferCatalog itemListOrder drift")
        catalog_entries = offer_catalog.get("itemListElement", [])
        missing_catalog_refs = sorted(expected_offer_ids - item_list_ref_ids(catalog_entries))
        if missing_catalog_refs:
            issues.append(f"Pages index OfferCatalog itemListElement missing: {missing_catalog_refs}")
        if not isinstance(catalog_entries, list):
            issues.append("Pages index OfferCatalog itemListElement must be a list")
        else:
            for position, focus in enumerate(focus_items, start=1):
                expected_offer_id = f"https://www.marksiazon.dev/#offer-{slugify(str(focus))}"
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
                if "ListItem" not in node_type_set(entry):
                    issues.append(f"Pages index OfferCatalog entry must be ListItem: {focus}")
                if entry.get("position") != position:
                    issues.append(f"Pages index OfferCatalog position drift: {focus}")
                if entry.get("name") != str(focus):
                    issues.append(f"Pages index OfferCatalog entry name drift: {focus}")
    service_channel = next((node for node in parsed_jsonld_nodes if node.get("@id") == service_channel_id), None)
    if not service_channel or "ServiceChannel" not in node_type_set(service_channel):
        issues.append("Pages index inline JSON-LD missing hiring ServiceChannel")
    else:
        if service_channel.get("name") != service_channel_name():
            issues.append("Pages index ServiceChannel name drift")
        if service_channel.get("description") != service_channel_description():
            issues.append("Pages index ServiceChannel description drift")
        if service_channel.get("serviceUrl") != availability.get("contact"):
            issues.append("Pages index ServiceChannel serviceUrl drift")
        if service_channel.get("availableLanguage") != available_languages():
            issues.append("Pages index ServiceChannel availableLanguage drift")
        missing_channel_services = sorted(expected_service_ids - ref_ids(service_channel.get("providesService")))
        if missing_channel_services:
            issues.append(f"Pages index ServiceChannel providesService missing: {missing_channel_services}")
        if service_channel.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index ServiceChannel about drift")
        if service_channel.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index ServiceChannel dateModified drift")
    area_served = set(availability.get("areaServed", []))
    for focus in focus_items:
        offer_id = f"https://www.marksiazon.dev/#offer-{slugify(str(focus))}"
        service_id = f"https://www.marksiazon.dev/#service-{slugify(str(focus))}"
        offer = next((node for node in parsed_jsonld_nodes if node.get("@id") == offer_id), None)
        if not offer or "Offer" not in node_type_set(offer):
            issues.append(f"Pages index missing Offer node: {offer_id}")
        else:
            if offer.get("name") != f"{focus} availability":
                issues.append(f"Pages index Offer name drift: {focus}")
            if offer.get("category") != str(focus):
                issues.append(f"Pages index Offer category drift: {focus}")
            if offer.get("identifier") != service_focus_identifier(str(focus), "offer"):
                issues.append(f"Pages index Offer identifier drift: {focus}")
            if offer.get("description") != offer_description(index_data, str(focus)):
                issues.append(f"Pages index Offer description drift: {focus}")
            if offer.get("url") != availability.get("recruiterBrief"):
                issues.append(f"Pages index Offer url drift: {focus}")
            if offer.get("mainEntityOfPage") != availability.get("recruiterBrief"):
                issues.append(f"Pages index Offer mainEntityOfPage drift: {focus}")
            if offer.get("availability") != offer_availability(index_data):
                issues.append(f"Pages index Offer availability drift: {focus}")
            if offer.get("itemOffered", {}).get("@id") != service_id:
                issues.append(f"Pages index Offer itemOffered drift: {focus}")
            if offer.get("businessFunction") != PROVIDE_SERVICE_BUSINESS_FUNCTION:
                issues.append(f"Pages index Offer businessFunction drift: {focus}")
            if offer.get("offeredBy", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Offer offeredBy drift: {focus}")
            if offer.get("seller", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Offer seller drift: {focus}")
            missing_offer_area = sorted(area_served - area_names(offer.get("areaServed")))
            if missing_offer_area:
                issues.append(f"Pages index Offer areaServed missing for {focus}: {missing_offer_area}")
            missing_eligible_region = sorted(area_served - area_names(offer.get("eligibleRegion")))
            if missing_eligible_region:
                issues.append(f"Pages index Offer eligibleRegion missing for {focus}: {missing_eligible_region}")
        service = next((node for node in parsed_jsonld_nodes if node.get("@id") == service_id), None)
        if not service or "Service" not in node_type_set(service):
            issues.append(f"Pages index missing Service node: {service_id}")
        else:
            if service.get("name") != str(focus):
                issues.append(f"Pages index Service name drift: {focus}")
            if service.get("serviceType") != str(focus):
                issues.append(f"Pages index Service serviceType drift: {focus}")
            if service.get("identifier") != service_focus_identifier(str(focus), "service"):
                issues.append(f"Pages index Service identifier drift: {focus}")
            if service.get("description") != service_description(index_data, str(focus)):
                issues.append(f"Pages index Service description drift: {focus}")
            if service.get("url") != availability.get("recruiterBrief"):
                issues.append(f"Pages index Service url drift: {focus}")
            if service.get("mainEntityOfPage") != availability.get("recruiterBrief"):
                issues.append(f"Pages index Service mainEntityOfPage drift: {focus}")
            if service.get("provider", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Service provider drift: {focus}")
            if service.get("offers", {}).get("@id") != offer_id:
                issues.append(f"Pages index Service offers drift: {focus}")
            if service.get("availableChannel", {}).get("@id") != service_channel_id:
                issues.append(f"Pages index Service availableChannel drift: {service_id}")
            if service.get("providerMobility") != SERVICE_PROVIDER_MOBILITY:
                issues.append(f"Pages index Service providerMobility drift: {focus}")
            if service.get("audience") != service_audience():
                issues.append(f"Pages index Service audience drift: {focus}")
            if service.get("serviceAudience") != service_audience():
                issues.append(f"Pages index Service serviceAudience drift: {focus}")
            missing_service_area = sorted(area_served - area_names(service.get("areaServed")))
            if missing_service_area:
                issues.append(f"Pages index Service areaServed missing for {focus}: {missing_service_area}")
    profile_page = next((node for node in parsed_jsonld_nodes if node.get("@id") == "https://github.com/Iron-Mark/Iron-Mark#profilepage"), None)
    if not profile_page or "ProfilePage" not in node_type_set(profile_page):
        issues.append("Pages index inline JSON-LD missing GitHub ProfilePage")
    else:
        if profile_page.get("inLanguage") != "en":
            issues.append("Pages index GitHub ProfilePage inLanguage must be en")
        if profile_page.get("author", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index GitHub ProfilePage author drift")
        if profile_page.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index GitHub ProfilePage publisher drift")
        if profile_page.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index GitHub ProfilePage keywords drift")
        if profile_page.get("mainEntity", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index GitHub ProfilePage mainEntity drift")
        if profile_page.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index GitHub ProfilePage about drift")
        if profile_page.get("isPartOf", {}).get("@id") != "https://github.com/Iron-Mark/Iron-Mark#website":
            issues.append("Pages index GitHub ProfilePage isPartOf drift")
        if profile_page.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index GitHub ProfilePage dateModified drift")
        if profile_page.get("primaryImageOfPage", {}).get("@id") != f"{PAGES_BASE}/#primary-image":
            issues.append("Pages index GitHub ProfilePage primaryImageOfPage drift")
        if profile_page.get("thumbnailUrl") != PAGES_SOCIAL_IMAGE:
            issues.append("Pages index GitHub ProfilePage thumbnailUrl drift")
        if profile_page.get("potentialAction", {}).get("@id") != "https://www.marksiazon.dev/#contact-action":
            issues.append("Pages index GitHub ProfilePage potentialAction drift")
        missing_profile_parts = sorted(pages_rewrite_ids(profile_page_part_ids(index_data)) - ref_ids(profile_page.get("hasPart")))
        if missing_profile_parts:
            issues.append(f"Pages index GitHub ProfilePage hasPart missing: {missing_profile_parts}")
        check_review_metadata(issues, profile_page, index_data, "Pages index GitHub ProfilePage")
        check_content_usage_policy(issues, profile_page, "Pages index GitHub ProfilePage")
        check_ownership_metadata(issues, profile_page, index_data, "Pages index GitHub ProfilePage")
        check_spatial_coverage(issues, profile_page, index_data, "Pages index GitHub ProfilePage")
        check_structured_data_provenance(issues, profile_page, index_data, "Pages index GitHub ProfilePage")
        check_expected_mentions(issues, profile_page, index_data, "Pages index GitHub ProfilePage")
    pages_site = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#website"), None)
    if not pages_site or "WebSite" not in node_type_set(pages_site):
        issues.append("Pages index inline JSON-LD missing Pages WebSite node")
    else:
        if pages_site.get("name") != PAGES_SITE_NAME:
            issues.append("Pages index inline JSON-LD WebSite site-name drift")
        if pages_site.get("url") != f"{PAGES_BASE}/":
            issues.append("Pages index inline JSON-LD WebSite url drift")
        if pages_site.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index inline JSON-LD WebSite dateModified drift")
        canonical = index_data.get("canonical", {})
        expected_based_on = canonical.get("githubProfileReadme") if isinstance(canonical, dict) else None
        if pages_site.get("isBasedOn") != expected_based_on:
            issues.append("Pages index WebSite isBasedOn drift")
        if pages_site.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index WebSite keywords drift")
        if pages_site.get("significantLink") != pages_significant_links(index_data):
            issues.append("Pages index WebSite significantLink drift")
        if pages_site.get("relatedLink") != pages_related_links(index_data):
            issues.append("Pages index WebSite relatedLink drift")
        required_site_parts = {
            f"{PAGES_BASE}/#webpage",
            f"{PAGES_BASE}/#data-catalog",
            f"{PAGES_BASE}/#machine-readable-dataset",
            f"{PAGES_BASE}/#main-content",
            pages_section_navigation_id(),
            pages_topic_set_id,
        }
        missing_site_parts = sorted(required_site_parts - ref_ids(pages_site.get("hasPart")))
        if missing_site_parts:
            issues.append(f"Pages index WebSite hasPart missing: {missing_site_parts}")
        check_content_usage_policy(issues, pages_site, "Pages index WebSite")
        check_ownership_metadata(issues, pages_site, index_data, "Pages index WebSite")
        check_spatial_coverage(issues, pages_site, index_data, "Pages index WebSite")
        check_structured_data_provenance(issues, pages_site, index_data, "Pages index WebSite")
        check_expected_mentions(issues, pages_site, index_data, "Pages index WebSite")
        missing_alternates = sorted(PAGES_SITE_ALTERNATE_NAMES - set(pages_site.get("alternateName", [])))
        if missing_alternates:
            issues.append(f"Pages index inline JSON-LD WebSite alternateName missing: {missing_alternates}")
    machine_readable_for_sources = index_data.get("machineReadable", {})
    repo_sources = machine_readable_for_sources.get("repo", {}) if isinstance(machine_readable_for_sources, dict) else {}
    if not isinstance(repo_sources, dict):
        repo_sources = {}
    expected_based_on = repo_sources.get("llmsIndexJson")
    pages_main_content_id = f"{PAGES_BASE}/#main-content"
    pages_section_nav_id = pages_section_navigation_id()
    pages_section_ids = {pages_section_id(section["fragment"]) for section in pages_section_specs(index_data)}
    pages_section_relations = pages_section_relation_ids(index_data)
    pages_section_nav_item_ids = {
        pages_section_nav_item_id(section["fragment"])
        for section in pages_section_specs(index_data)
    }
    pages_page = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#webpage"), None)
    if not pages_page or "CollectionPage" not in node_type_set(pages_page):
        issues.append("Pages index inline JSON-LD missing CollectionPage")
    else:
        if pages_page.get("isBasedOn") != expected_based_on:
            issues.append("Pages index CollectionPage isBasedOn drift")
        if pages_page.get("significantLink") != pages_significant_links(index_data):
            issues.append("Pages index CollectionPage significantLink drift")
        if pages_page.get("relatedLink") != pages_related_links(index_data):
            issues.append("Pages index CollectionPage relatedLink drift")
        if pages_page.get("speakable") != expected_pages_speakable(index_data):
            issues.append("Pages index CollectionPage speakable drift")
        if pages_page.get("mainContentOfPage", {}).get("@id") != pages_main_content_id:
            issues.append("Pages index CollectionPage mainContentOfPage drift")
        if pages_page.get("author", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index CollectionPage author drift")
        if pages_page.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index CollectionPage publisher drift")
        if pages_page.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index CollectionPage keywords drift")
        if pages_topic_set_id not in ref_ids(pages_page.get("hasPart")):
            issues.append("Pages index CollectionPage hasPart missing topic taxonomy")
        if pages_main_content_id not in ref_ids(pages_page.get("hasPart")):
            issues.append("Pages index CollectionPage hasPart missing main content")
        if pages_section_nav_id not in ref_ids(pages_page.get("hasPart")):
            issues.append("Pages index CollectionPage hasPart missing section navigation")
        missing_section_parts = sorted(pages_section_ids - ref_ids(pages_page.get("hasPart")))
        if missing_section_parts:
            issues.append(f"Pages index CollectionPage hasPart missing sections: {missing_section_parts}")
        check_review_metadata(issues, pages_page, index_data, "Pages index CollectionPage")
        check_content_usage_policy(issues, pages_page, "Pages index CollectionPage")
        check_global_citation(issues, pages_page, index_data, "Pages index CollectionPage")
        check_ownership_metadata(issues, pages_page, index_data, "Pages index CollectionPage")
        check_spatial_coverage(issues, pages_page, index_data, "Pages index CollectionPage")
        check_structured_data_provenance(issues, pages_page, index_data, "Pages index CollectionPage")
        check_expected_mentions(issues, pages_page, index_data, "Pages index CollectionPage")
    main_content = next((node for node in parsed_jsonld_nodes if node.get("@id") == pages_main_content_id), None)
    if not main_content or "WebPageElement" not in node_type_set(main_content):
        issues.append("Pages index inline JSON-LD missing main WebPageElement")
    else:
        if main_content.get("url") != f"{PAGES_BASE}/#main-content":
            issues.append("Pages index main WebPageElement url drift")
        entity = index_data.get("entity", {})
        expected_text = entity.get("description") if isinstance(entity, dict) else None
        if main_content.get("text") != expected_text:
            issues.append("Pages index main WebPageElement text drift")
        if main_content.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index main WebPageElement about drift")
        if main_content.get("isPartOf", {}).get("@id") != f"{PAGES_BASE}/#webpage":
            issues.append("Pages index main WebPageElement isPartOf drift")
        if main_content.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index main WebPageElement dateModified drift")
        if main_content.get("isAccessibleForFree") is not True:
            issues.append("Pages index main WebPageElement must be isAccessibleForFree")
        check_content_usage_policy(issues, main_content, "Pages index main WebPageElement")
        check_global_citation(issues, main_content, index_data, "Pages index main WebPageElement")
        check_ownership_metadata(issues, main_content, index_data, "Pages index main WebPageElement")
        check_structured_data_provenance(issues, main_content, index_data, "Pages index main WebPageElement")
        missing_section_parts = sorted(pages_section_ids - ref_ids(main_content.get("hasPart")))
        if missing_section_parts:
            issues.append(f"Pages index main WebPageElement hasPart missing sections: {missing_section_parts}")
        if pages_section_nav_id not in ref_ids(main_content.get("hasPart")):
            issues.append("Pages index main WebPageElement hasPart missing section navigation")
    section_navigation = next((node for node in parsed_jsonld_nodes if node.get("@id") == pages_section_nav_id), None)
    if not section_navigation or "SiteNavigationElement" not in node_type_set(section_navigation):
        issues.append("Pages index inline JSON-LD missing section SiteNavigationElement")
    else:
        if section_navigation.get("url") != f"{PAGES_BASE}/#section-navigation":
            issues.append("Pages index section navigation url drift")
        if section_navigation.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index section navigation about drift")
        if section_navigation.get("isPartOf", {}).get("@id") != f"{PAGES_BASE}/#webpage":
            issues.append("Pages index section navigation isPartOf drift")
        if section_navigation.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index section navigation dateModified drift")
        if section_navigation.get("isAccessibleForFree") is not True:
            issues.append("Pages index section navigation must be isAccessibleForFree")
        missing_nav_items = sorted(pages_section_nav_item_ids - ref_ids(section_navigation.get("hasPart")))
        if missing_nav_items:
            issues.append(f"Pages index section navigation hasPart missing: {missing_nav_items}")
        check_content_usage_policy(issues, section_navigation, "Pages index section navigation")
        check_global_citation(issues, section_navigation, index_data, "Pages index section navigation")
        check_ownership_metadata(issues, section_navigation, index_data, "Pages index section navigation")
        check_structured_data_provenance(issues, section_navigation, index_data, "Pages index section navigation")
    for position, section in enumerate(pages_section_specs(index_data), start=1):
        nav_item_id = pages_section_nav_item_id(section["fragment"])
        nav_item = next((node for node in parsed_jsonld_nodes if node.get("@id") == nav_item_id), None)
        label = f"Pages index section navigation item {section['fragment']}"
        if not nav_item or "SiteNavigationElement" not in node_type_set(nav_item):
            issues.append(f"Pages index missing section navigation item: {nav_item_id}")
            continue
        if nav_item.get("name") != section["heading"]:
            issues.append(f"{label} name drift")
        if nav_item.get("url") != f"{PAGES_BASE}/#{section['fragment']}":
            issues.append(f"{label} url drift")
        if nav_item.get("description") != section["description"]:
            issues.append(f"{label} description drift")
        if nav_item.get("abstract") != nav_item.get("description"):
            issues.append(f"{label} abstract drift")
        if nav_item.get("about", {}).get("@id") != pages_section_id(section["fragment"]):
            issues.append(f"{label} about drift")
        if nav_item.get("isPartOf", {}).get("@id") != pages_section_nav_id:
            issues.append(f"{label} isPartOf drift")
        if nav_item.get("position") != position:
            issues.append(f"{label} position drift")
        if nav_item.get("inLanguage") != "en":
            issues.append(f"{label} inLanguage must be en")
        if nav_item.get("dateModified") != index_data.get("updated"):
            issues.append(f"{label} dateModified drift")
        if nav_item.get("isAccessibleForFree") is not True:
            issues.append(f"{label} must be isAccessibleForFree")
        check_ownership_metadata(issues, nav_item, index_data, label)
    for section in pages_section_specs(index_data):
        section_id = pages_section_id(section["fragment"])
        section_node = next((node for node in parsed_jsonld_nodes if node.get("@id") == section_id), None)
        label = f"Pages index section WebPageElement {section['fragment']}"
        if not section_node or "WebPageElement" not in node_type_set(section_node):
            issues.append(f"Pages index inline JSON-LD missing section WebPageElement: {section_id}")
            continue
        if section_node.get("name") != section["name"]:
            issues.append(f"{label} name drift")
        if section_node.get("url") != f"{PAGES_BASE}/#{section['fragment']}":
            issues.append(f"{label} url drift")
        if section_node.get("description") != section["description"]:
            issues.append(f"{label} description drift")
        if section_node.get("text") != section["text"]:
            issues.append(f"{label} text drift")
        if section_node.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append(f"{label} about drift")
        if section_node.get("isPartOf", {}).get("@id") != f"{PAGES_BASE}/#webpage":
            issues.append(f"{label} isPartOf drift")
        if section_node.get("dateModified") != index_data.get("updated"):
            issues.append(f"{label} dateModified drift")
        if section_node.get("isAccessibleForFree") is not True:
            issues.append(f"{label} must be isAccessibleForFree")
        relations = pages_section_relations.get(section["fragment"], {})
        missing_has_part = sorted(pages_rewrite_ids(relations.get("hasPart", [])) - ref_ids(section_node.get("hasPart")))
        if missing_has_part:
            issues.append(f"{label} hasPart missing: {missing_has_part}")
        missing_mentions = sorted(pages_rewrite_ids(relations.get("mentions", [])) - ref_ids(section_node.get("mentions")))
        if missing_mentions:
            issues.append(f"{label} mentions missing: {missing_mentions}")
        check_content_usage_policy(issues, section_node, label)
        check_global_citation(issues, section_node, index_data, label)
        check_ownership_metadata(issues, section_node, index_data, label)
        check_structured_data_provenance(issues, section_node, index_data, label)
    topic_terms = expected_topic_terms(index_data)
    topic_set = next((node for node in parsed_jsonld_nodes if node.get("@id") == pages_topic_set_id), None)
    if not topic_set or "DefinedTermSet" not in node_type_set(topic_set):
        issues.append("Pages index inline JSON-LD missing DefinedTermSet")
    else:
        if topic_set.get("name") != "Mark Siazon profile topic taxonomy":
            issues.append("Pages index DefinedTermSet name drift")
        if topic_set.get("url") != f"{PAGES_BASE}/":
            issues.append("Pages index DefinedTermSet url drift")
        if topic_set.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index DefinedTermSet dateModified drift")
        if topic_set.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index DefinedTermSet about drift")
        if topic_set.get("isPartOf", {}).get("@id") != f"{PAGES_BASE}/#website":
            issues.append("Pages index DefinedTermSet isPartOf drift")
        missing_terms = sorted({topic_term_id(term) for term in topic_terms} - ref_ids(topic_set.get("hasDefinedTerm")))
        if missing_terms:
            issues.append(f"Pages index DefinedTermSet hasDefinedTerm missing: {missing_terms}")
        check_content_usage_policy(issues, topic_set, "Pages index DefinedTermSet")
        check_global_citation(issues, topic_set, index_data, "Pages index DefinedTermSet")
        check_ownership_metadata(issues, topic_set, index_data, "Pages index DefinedTermSet")
        check_structured_data_provenance(issues, topic_set, index_data, "Pages index DefinedTermSet")
    for term in topic_terms:
        term_node = next((node for node in parsed_jsonld_nodes if node.get("@id") == topic_term_id(term)), None)
        if not term_node or "DefinedTerm" not in node_type_set(term_node):
            issues.append(f"Pages index missing DefinedTerm node: {term}")
            continue
        if term_node.get("name") != term:
            issues.append(f"Pages index DefinedTerm name drift: {term}")
        if term_node.get("termCode") != slugify(term):
            issues.append(f"Pages index DefinedTerm termCode drift: {term}")
        if term_node.get("description") != expected_topic_term_description(index_data, term):
            issues.append(f"Pages index DefinedTerm description drift: {term}")
        if term_node.get("url") != topic_term_id(term):
            issues.append(f"Pages index DefinedTerm url drift: {term}")
        if term_node.get("inDefinedTermSet", {}).get("@id") != pages_topic_set_id:
            issues.append(f"Pages index DefinedTerm set drift: {term}")
        if term_node.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append(f"Pages index DefinedTerm about drift: {term}")
        if term_node.get("dateModified") != index_data.get("updated"):
            issues.append(f"Pages index DefinedTerm dateModified drift: {term}")
    data_catalog = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#data-catalog"), None)
    if not data_catalog or "DataCatalog" not in node_type_set(data_catalog):
        issues.append("Pages index inline JSON-LD missing DataCatalog")
    else:
        if data_catalog.get("name") != data_catalog_name():
            issues.append("Pages index DataCatalog name drift")
        if data_catalog.get("url") != f"{PAGES_BASE}/":
            issues.append("Pages index DataCatalog url drift")
        if data_catalog.get("description") != data_catalog_description():
            issues.append("Pages index DataCatalog description drift")
        if data_catalog.get("abstract") != data_catalog.get("description"):
            issues.append("Pages index DataCatalog abstract drift")
        if data_catalog.get("dataset", {}).get("@id") != f"{PAGES_BASE}/#machine-readable-dataset":
            issues.append("Pages index DataCatalog dataset drift")
        if data_catalog.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index DataCatalog about drift")
        if data_catalog.get("isBasedOn") != expected_based_on:
            issues.append("Pages index DataCatalog isBasedOn drift")
        if data_catalog.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index DataCatalog keywords drift")
        if data_catalog.get("creator", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index DataCatalog creator drift")
        if data_catalog.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index DataCatalog publisher drift")
        if data_catalog.get("inLanguage") != "en":
            issues.append("Pages index DataCatalog inLanguage must be en")
        if data_catalog.get("datePublished") != DATASET_DATE_PUBLISHED:
            issues.append("Pages index DataCatalog datePublished drift")
        if data_catalog.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index DataCatalog dateModified drift")
        if data_catalog.get("license") != f"{PAGES_BASE}/LICENSE.md":
            issues.append("Pages index DataCatalog license drift")
        if data_catalog.get("temporalCoverage") != dataset_temporal_coverage(index_data):
            issues.append("Pages index DataCatalog temporalCoverage drift")
        if data_catalog.get("measurementTechnique") != dataset_measurement_techniques():
            issues.append("Pages index DataCatalog measurementTechnique drift")
        if data_catalog.get("isAccessibleForFree") is not True:
            issues.append("Pages index DataCatalog must be isAccessibleForFree")
        check_content_usage_policy(issues, data_catalog, "Pages index DataCatalog")
        check_global_citation(issues, data_catalog, index_data, "Pages index DataCatalog")
        check_ownership_metadata(issues, data_catalog, index_data, "Pages index DataCatalog")
        check_spatial_coverage(issues, data_catalog, index_data, "Pages index DataCatalog")
        check_structured_data_provenance(issues, data_catalog, index_data, "Pages index DataCatalog")
        check_expected_mentions(issues, data_catalog, index_data, "Pages index DataCatalog")
    breadcrumb = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#breadcrumb"), None)
    if not breadcrumb or "BreadcrumbList" not in node_type_set(breadcrumb):
        issues.append("Pages index inline JSON-LD missing BreadcrumbList")
    else:
        items = breadcrumb.get("itemListElement", [])
        if not isinstance(items, list) or len(items) < 2:
            issues.append("Pages index inline BreadcrumbList must contain portfolio and Pages items")
        else:
            if items[0].get("name") != "Mark Siazon Portfolio" or items[0].get("item") != "https://www.marksiazon.dev":
                issues.append("Pages index inline BreadcrumbList portfolio item drift")
            if items[1].get("name") != PAGES_SITE_NAME or items[1].get("item") != f"{PAGES_BASE}/":
                issues.append("Pages index inline BreadcrumbList Pages item drift")
    dataset = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#machine-readable-dataset"), None)
    if not dataset or "Dataset" not in node_type_set(dataset):
        issues.append("Pages index inline JSON-LD missing Dataset")
    else:
        if dataset.get("sameAs") != "https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json":
            issues.append("Pages index inline Dataset sameAs source drift")
        if dataset.get("isBasedOn") != "https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json":
            issues.append("Pages index inline Dataset isBasedOn drift")
        if dataset.get("version") != index_data.get("updated"):
            issues.append("Pages index inline Dataset version drift")
        if dataset.get("alternateName") != dataset_alternate_names(index_data):
            issues.append("Pages index inline Dataset alternateName drift")
        if dataset.get("datePublished") != DATASET_DATE_PUBLISHED:
            issues.append("Pages index inline Dataset datePublished drift")
        identifiers = dataset.get("identifier", [])
        if isinstance(identifiers, dict):
            identifiers = [identifiers]
        identifier_values = {item.get("value") for item in identifiers if isinstance(item, dict)}
        expected_values = {"Iron-Mark/Iron-Mark", f"{PAGES_BASE}/#machine-readable-dataset"}
        missing_values = sorted(expected_values - identifier_values)
        if missing_values:
            issues.append(f"Pages index inline Dataset identifier missing value(s): {missing_values}")
        availability = index_data.get("availability", {})
        area_served = availability.get("areaServed", []) if isinstance(availability, dict) else []
        if dataset.get("spatialCoverage") != expected_area_nodes(area_served if isinstance(area_served, list) else []):
            issues.append("Pages index inline Dataset spatialCoverage typed region drift")
        if dataset.get("temporalCoverage") != dataset_temporal_coverage(index_data):
            issues.append("Pages index inline Dataset temporalCoverage drift")
        if dataset.get("measurementTechnique") != dataset_measurement_techniques():
            issues.append("Pages index inline Dataset measurementTechnique drift")
        if dataset.get("variableMeasured") != expected_dataset_measurements(index_data):
            issues.append("Pages index inline Dataset variableMeasured drift")
        if {"https://www.marksiazon.dev/#person", pages_topic_set_id} - ref_ids(dataset.get("about")):
            issues.append("Pages index Dataset about must reference Person and topic taxonomy")
        if dataset.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index Dataset keywords drift")
        check_content_usage_policy(issues, dataset, "Pages index Dataset")
        check_global_citation(issues, dataset, index_data, "Pages index Dataset")
        check_ownership_metadata(issues, dataset, index_data, "Pages index Dataset")
        check_spatial_coverage(issues, dataset, index_data, "Pages index Dataset")
        check_structured_data_provenance(issues, dataset, index_data, "Pages index Dataset")
        check_expected_mentions(issues, dataset, index_data, "Pages index Dataset")
    pages_faq_id = f"{PAGES_BASE}/FAQ.md#faq"
    expected_question_ids = {
        faq_question_id(pages_faq_id, str(item.get("question", "")))
        for item in index_data.get("aeo", {}).get("answerSnippets", [])
        if isinstance(item, dict)
    }
    faq_page = next((node for node in parsed_jsonld_nodes if node.get("@id") == pages_faq_id), None)
    if not faq_page or "FAQPage" not in node_type_set(faq_page):
        issues.append("Pages index inline JSON-LD missing FAQPage")
    else:
        if faq_page.get("identifier") != faq_document_identifier(pages_faq_id):
            issues.append("Pages index FAQPage identifier drift")
        if faq_page.get("isBasedOn") != f"{PAGES_BASE}/FAQ.md":
            issues.append("Pages index FAQPage isBasedOn drift")
        if faq_page.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index FAQPage dateModified drift")
        if faq_page.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index FAQPage about drift")
        if faq_page.get("inLanguage") != content_language():
            issues.append("Pages index FAQPage inLanguage drift")
        if faq_page.get("author", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index FAQPage author drift")
        if faq_page.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index FAQPage publisher drift")
        if faq_page.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index FAQPage keywords drift")
        if faq_page.get("isAccessibleForFree") is not True:
            issues.append("Pages index FAQPage must be isAccessibleForFree")
        actual_has_part = ref_ids(faq_page.get("hasPart"))
        missing_has_part = sorted(expected_question_ids - actual_has_part)
        if missing_has_part:
            issues.append(f"Pages index FAQPage hasPart missing questions: {missing_has_part}")
        extra_has_part = sorted(actual_has_part - expected_question_ids)
        if extra_has_part:
            issues.append(f"Pages index FAQPage hasPart unexpected questions: {extra_has_part}")
        actual_main_entity = ref_ids(faq_page.get("mainEntity"))
        missing_main_entity = sorted(expected_question_ids - actual_main_entity)
        if missing_main_entity:
            issues.append(f"Pages index FAQPage mainEntity missing questions: {missing_main_entity}")
        extra_main_entity = sorted(actual_main_entity - expected_question_ids)
        if extra_main_entity:
            issues.append(f"Pages index FAQPage mainEntity unexpected questions: {extra_main_entity}")
        check_content_usage_policy(issues, faq_page, "Pages index FAQPage")
        check_global_citation(issues, faq_page, index_data, "Pages index FAQPage")
        check_review_metadata(issues, faq_page, index_data, "Pages index FAQPage")
        check_ownership_metadata(issues, faq_page, index_data, "Pages index FAQPage")
        check_spatial_coverage(issues, faq_page, index_data, "Pages index FAQPage")
        check_structured_data_provenance(issues, faq_page, index_data, "Pages index FAQPage")
    faq_sources_by_question = {
        str(item.get("question", "")): [
            pages_rewrite_public_source(str(source))
            for source in item.get("sources", [])
        ]
        for item in index_data.get("aeo", {}).get("answerSnippets", [])
        if isinstance(item, dict)
    }
    faq_answers_by_question = {
        str(item.get("question", "")): str(item.get("answer", ""))
        for item in index_data.get("aeo", {}).get("answerSnippets", [])
        if isinstance(item, dict)
    }
    question_node_ids = {
        str(node.get("@id", ""))
        for node in parsed_jsonld_nodes
        if "Question" in node_type_set(node)
    }
    missing_question_nodes = sorted(expected_question_ids - question_node_ids)
    if missing_question_nodes:
        issues.append(f"Pages index missing Question nodes: {missing_question_nodes}")
    unexpected_question_nodes = sorted(question_node_ids - expected_question_ids)
    if unexpected_question_nodes:
        issues.append(f"Pages index unexpected Question nodes: {unexpected_question_nodes}")
    for node in parsed_jsonld_nodes:
        node_types = node_type_set(node)
        if "Question" in node_types:
            question_id = str(node.get("@id", ""))
            question_name = str(node.get("name", ""))
            if node.get("url") != question_id:
                issues.append(f"Pages index Question url drift: {node.get('name')}")
            if node.get("identifier") != faq_item_identifier(question_id, "question"):
                issues.append(f"Pages index Question identifier drift: {node.get('name')}")
            if node.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Question about drift: {node.get('name')}")
            if node.get("author", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Question author drift: {node.get('name')}")
            if node.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Question publisher drift: {node.get('name')}")
            if node.get("isPartOf", {}).get("@id") != f"{PAGES_BASE}/FAQ.md#faq":
                issues.append(f"Pages index Question isPartOf drift: {node.get('name')}")
            if node.get("parentItem", {}).get("@id") != f"{PAGES_BASE}/FAQ.md#faq":
                issues.append(f"Pages index Question parentItem drift: {node.get('name')}")
            if node.get("answerCount") != 1:
                issues.append(f"Pages index Question answerCount drift: {node.get('name')}")
            if node.get("inLanguage") != content_language():
                issues.append(f"Pages index Question inLanguage drift: {node.get('name')}")
            if node.get("dateModified") != index_data.get("updated"):
                issues.append(f"Pages index Question dateModified drift: {node.get('name')}")
            if node.get("isAccessibleForFree") is not True:
                issues.append(f"Pages index Question must be isAccessibleForFree: {node.get('name')}")
            expected_citations = set(faq_sources_by_question.get(question_name, []))
            question_citations = node.get("citation", [])
            if isinstance(question_citations, str):
                question_citations = [question_citations]
            if set(question_citations) != expected_citations:
                issues.append(f"Pages index Question citation drift: {node.get('name')}")
            check_content_usage_policy(issues, node, f"Pages index Question {node.get('name')}")
            check_structured_data_provenance(issues, node, index_data, f"Pages index Question {node.get('name')}")
            answer = node.get("acceptedAnswer", {})
            if not isinstance(answer, dict):
                issues.append(f"Pages index Question missing acceptedAnswer: {node.get('name')}")
                continue
            answer_id = f"{question_id}-answer"
            if answer.get("url") != answer_id:
                issues.append(f"Pages index Answer url drift: {node.get('name')}")
            if answer.get("identifier") != faq_item_identifier(answer_id, "answer"):
                issues.append(f"Pages index Answer identifier drift: {node.get('name')}")
            if answer.get("text") != faq_answers_by_question.get(question_name):
                issues.append(f"Pages index Answer text drift: {node.get('name')}")
            if answer.get("author", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Answer author drift: {node.get('name')}")
            if answer.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Answer publisher drift: {node.get('name')}")
            if answer.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Answer about drift: {node.get('name')}")
            if answer.get("isPartOf", {}).get("@id") != f"{PAGES_BASE}/FAQ.md#faq":
                issues.append(f"Pages index Answer isPartOf drift: {node.get('name')}")
            if answer.get("parentItem", {}).get("@id") != question_id:
                issues.append(f"Pages index Answer parentItem drift: {node.get('name')}")
            if answer.get("inLanguage") != content_language():
                issues.append(f"Pages index Answer inLanguage drift: {node.get('name')}")
            if answer.get("dateModified") != index_data.get("updated"):
                issues.append(f"Pages index Answer dateModified drift: {node.get('name')}")
            if answer.get("isAccessibleForFree") is not True:
                issues.append(f"Pages index Answer must be isAccessibleForFree: {node.get('name')}")
            answer_citations = answer.get("citation", [])
            if isinstance(answer_citations, str):
                answer_citations = [answer_citations]
            if set(answer_citations) != expected_citations:
                issues.append(f"Pages index Answer citation drift: {node.get('name')}")
            check_content_usage_policy(issues, answer, f"Pages index Answer {node.get('name')}")
            check_structured_data_provenance(issues, answer, index_data, f"Pages index Answer {node.get('name')}")
    jsonld_node_by_id = {str(node.get("@id", "")): node for node in parsed_jsonld_nodes}
    featured_list = jsonld_node_by_id.get(f"{GITHUB_BLOB}/llms-index.json#featured-projects")
    if not featured_list or "ItemList" not in node_type_set(featured_list):
        issues.append("Pages index inline JSON-LD missing featured projects ItemList")
    else:
        if "CreativeWork" not in node_type_set(featured_list):
            issues.append("Pages index featured projects ItemList must also be CreativeWork")
        featured_projects = index_data.get("featuredProjects", [])
        if not isinstance(featured_projects, list):
            featured_projects = []
        if featured_list.get("description") != featured_projects_list_description(index_data):
            issues.append("Pages index featured projects ItemList description drift")
        if featured_list.get("abstract") != featured_list.get("description"):
            issues.append("Pages index featured projects ItemList abstract drift")
        if featured_list.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index featured projects ItemList about drift")
        check_publisher_metadata(issues, featured_list, index_data, "Pages index featured projects ItemList")
        if featured_list.get("isPartOf", {}).get("@id") != f"{GITHUB_BLOB}/llms-index.json#creativework":
            issues.append("Pages index featured projects ItemList isPartOf drift")
        if featured_list.get("inLanguage") != "en":
            issues.append("Pages index featured projects ItemList inLanguage must be en")
        if featured_list.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index featured projects ItemList dateModified drift")
        if featured_list.get("isAccessibleForFree") is not True:
            issues.append("Pages index featured projects ItemList must be isAccessibleForFree")
        if featured_list.get("numberOfItems") != len(featured_projects):
            issues.append("Pages index featured projects ItemList count drift")
        expected_featured_ids = {
            f"{project.get('caseStudy')}#project"
            for project in featured_projects
            if isinstance(project, dict)
        }
        expected_featured_urls = {
            project.get("caseStudy")
            for project in featured_projects
            if isinstance(project, dict) and isinstance(project.get("caseStudy"), str)
        }
        missing_featured_ids = sorted(expected_featured_ids - item_list_ref_ids(featured_list.get("itemListElement")))
        if missing_featured_ids:
            issues.append(f"Pages index featured projects ItemList missing: {missing_featured_ids}")
        featured_item_urls = item_list_urls(featured_list.get("itemListElement"))
        missing_featured_urls = sorted(expected_featured_urls - featured_item_urls)
        if missing_featured_urls:
            issues.append(f"Pages index featured projects ItemList missing URLs: {missing_featured_urls}")
        bad_featured_urls = sorted(url for url in featured_item_urls if not is_absolute_http_url(url))
        if bad_featured_urls:
            issues.append(f"Pages index featured projects ItemList URLs must be absolute HTTP(S): {bad_featured_urls}")
        check_content_usage_policy(issues, featured_list, "Pages index featured projects ItemList")
        check_global_citation(issues, featured_list, index_data, "Pages index featured projects ItemList")
        check_ownership_metadata(issues, featured_list, index_data, "Pages index featured projects ItemList")
        check_structured_data_provenance(issues, featured_list, index_data, "Pages index featured projects ItemList")
    lab_list = jsonld_node_by_id.get(f"{GITHUB_BLOB}/llms-index.json#hackathon-lab")
    if not lab_list or "ItemList" not in node_type_set(lab_list):
        issues.append("Pages index inline JSON-LD missing hackathon and lab ItemList")
    else:
        if "CreativeWork" not in node_type_set(lab_list):
            issues.append("Pages index hackathon and lab ItemList must also be CreativeWork")
        lab_projects = index_data.get("hackathonLab", [])
        if not isinstance(lab_projects, list):
            lab_projects = []
        if lab_list.get("description") != lab_projects_list_description(index_data):
            issues.append("Pages index hackathon and lab ItemList description drift")
        if lab_list.get("abstract") != lab_list.get("description"):
            issues.append("Pages index hackathon and lab ItemList abstract drift")
        if lab_list.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index hackathon and lab ItemList about drift")
        check_publisher_metadata(issues, lab_list, index_data, "Pages index hackathon and lab ItemList")
        if lab_list.get("isPartOf", {}).get("@id") != f"{GITHUB_BLOB}/llms-index.json#creativework":
            issues.append("Pages index hackathon and lab ItemList isPartOf drift")
        if lab_list.get("inLanguage") != "en":
            issues.append("Pages index hackathon and lab ItemList inLanguage must be en")
        if lab_list.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index hackathon and lab ItemList dateModified drift")
        if lab_list.get("isAccessibleForFree") is not True:
            issues.append("Pages index hackathon and lab ItemList must be isAccessibleForFree")
        if lab_list.get("numberOfItems") != len(lab_projects):
            issues.append("Pages index hackathon and lab ItemList count drift")
        expected_lab_ids = {
            lab_project_id(project)
            for project in lab_projects
            if isinstance(project, dict) and lab_project_url(project)
        }
        expected_lab_urls = {
            lab_project_url(project)
            for project in lab_projects
            if isinstance(project, dict) and lab_project_url(project)
        }
        missing_lab_ids = sorted(expected_lab_ids - item_list_ref_ids(lab_list.get("itemListElement")))
        if missing_lab_ids:
            issues.append(f"Pages index hackathon and lab ItemList missing: {missing_lab_ids}")
        lab_item_urls = item_list_urls(lab_list.get("itemListElement"))
        missing_lab_urls = sorted(expected_lab_urls - lab_item_urls)
        if missing_lab_urls:
            issues.append(f"Pages index hackathon and lab ItemList missing URLs: {missing_lab_urls}")
        bad_lab_urls = sorted(url for url in lab_item_urls if not is_absolute_http_url(url))
        if bad_lab_urls:
            issues.append(f"Pages index hackathon and lab ItemList URLs must be absolute HTTP(S): {bad_lab_urls}")
        check_content_usage_policy(issues, lab_list, "Pages index hackathon and lab ItemList")
        check_global_citation(issues, lab_list, index_data, "Pages index hackathon and lab ItemList")
        check_ownership_metadata(issues, lab_list, index_data, "Pages index hackathon and lab ItemList")
        check_structured_data_provenance(issues, lab_list, index_data, "Pages index hackathon and lab ItemList")
    project_awards = awards_by_project(index_data)
    for project in index_data.get("featuredProjects", []):
        if not isinstance(project, dict):
            continue
        expected_project_id = f"{project.get('caseStudy')}#project"
        project_node = jsonld_node_by_id.get(expected_project_id)
        if not project_node or "CreativeWork" not in node_type_set(project_node):
            issues.append(f"Pages index inline JSON-LD missing featured project CreativeWork: {project.get('name')}")
            continue
        if project_node.get("mainEntityOfPage") != project.get("caseStudy"):
            issues.append(f"Pages index featured project mainEntityOfPage drift: {project.get('name')}")
        check_publisher_metadata(issues, project_node, index_data, f"Pages index featured project {project.get('name')}")
        expected_image = expected_project_image(project)
        if not expected_image:
            issues.append(f"Pages index cannot resolve featured project cover image: {project.get('name')}")
            continue
        if project_node.get("image", {}).get("@id") != expected_image["@id"]:
            issues.append(f"Pages index featured project image ref drift: {project.get('name')}")
        if project_node.get("thumbnailUrl") != expected_image["url"]:
            issues.append(f"Pages index featured project thumbnailUrl drift: {project.get('name')}")
        expected_awards = project_awards.get(str(project.get("name", "")), [])
        if expected_awards and project_node.get("award") != expected_awards:
            issues.append(f"Pages index featured project award drift: {project.get('name')}")
        if not expected_awards and "award" in project_node:
            issues.append(f"Pages index featured project unexpected award: {project.get('name')}")
        check_content_usage_policy(issues, project_node, f"Pages index featured project {project.get('name')}")
        check_global_citation(issues, project_node, index_data, f"Pages index featured project {project.get('name')}")
        check_ownership_metadata(issues, project_node, index_data, f"Pages index featured project {project.get('name')}")
        check_structured_data_provenance(issues, project_node, index_data, f"Pages index featured project {project.get('name')}")
        image_node = jsonld_node_by_id.get(expected_image["@id"])
        if not image_node or "ImageObject" not in node_type_set(image_node):
            issues.append(f"Pages index inline JSON-LD missing featured project ImageObject: {project.get('name')}")
            continue
        if image_node.get("contentUrl") != expected_image["url"]:
            issues.append(f"Pages index featured project image contentUrl drift: {project.get('name')}")
        if image_node.get("encodingFormat") != expected_image["encodingFormat"]:
            issues.append(f"Pages index featured project image encodingFormat drift: {project.get('name')}")
        if image_node.get("description") != project_image_description(project):
            issues.append(f"Pages index featured project image description drift: {project.get('name')}")
        if image_node.get("abstract") != image_node.get("description"):
            issues.append(f"Pages index featured project image abstract drift: {project.get('name')}")
        for key in ("contentSize", "sha256"):
            if image_node.get(key) != expected_image[key]:
                issues.append(f"Pages index featured project image {key} drift: {project.get('name')}")
        check_image_rights(issues, image_node, index_data, f"Pages index featured project image {project.get('name')}")
        if image_node.get("about", {}).get("@id") != expected_project_id:
            issues.append(f"Pages index featured project image about drift: {project.get('name')}")
    for project in index_data.get("hackathonLab", []):
        if not isinstance(project, dict):
            continue
        expected_project_id = lab_project_id(project)
        project_node = jsonld_node_by_id.get(expected_project_id)
        if not project_node or "CreativeWork" not in node_type_set(project_node):
            issues.append(f"Pages index inline JSON-LD missing hackathon/lab CreativeWork: {project.get('name')}")
            continue
        expected_url = lab_project_url(project)
        if project_node.get("url") != expected_url:
            issues.append(f"Pages index hackathon/lab project url drift: {project.get('name')}")
        if project_node.get("mainEntityOfPage") != expected_url:
            issues.append(f"Pages index hackathon/lab project mainEntityOfPage drift: {project.get('name')}")
        if project_node.get("description") != project.get("focus"):
            issues.append(f"Pages index hackathon/lab project description drift: {project.get('name')}")
        if project_node.get("creator", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append(f"Pages index hackathon/lab project creator drift: {project.get('name')}")
        if project_node.get("author", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append(f"Pages index hackathon/lab project author drift: {project.get('name')}")
        check_publisher_metadata(issues, project_node, index_data, f"Pages index hackathon/lab project {project.get('name')}")
        expected_parent = "https://www.marksiazon.dev/#website" if project.get("caseStudy") else "https://github.com/Iron-Mark/Iron-Mark#website"
        if project_node.get("isPartOf", {}).get("@id") != expected_parent:
            issues.append(f"Pages index hackathon/lab project isPartOf drift: {project.get('name')}")
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
            issues.append(f"Pages index hackathon/lab project sameAs drift: {project.get('name')}")
        if project_node.get("genre") != "Hackathon and lab project":
            issues.append(f"Pages index hackathon/lab project genre drift: {project.get('name')}")
        check_content_usage_policy(issues, project_node, f"Pages index hackathon/lab project {project.get('name')}")
        check_global_citation(issues, project_node, index_data, f"Pages index hackathon/lab project {project.get('name')}")
        check_ownership_metadata(issues, project_node, index_data, f"Pages index hackathon/lab project {project.get('name')}")
        check_structured_data_provenance(issues, project_node, index_data, f"Pages index hackathon/lab project {project.get('name')}")
    machine_readable = index_data.get("machineReadable", {})
    pages_for_downloads = machine_readable.get("pages", {}) if isinstance(machine_readable, dict) else {}
    if isinstance(pages_for_downloads, dict):
        for item in machine_downloads(pages_for_downloads, repo_sources):
            download = jsonld_node_by_id.get(download_id(item["key"]))
            if not download or "DataDownload" not in node_type_set(download):
                issues.append(f"Pages index inline JSON-LD missing DataDownload: {item['key']}")
                continue
            expected_download_source = pages_rewrite_public_source(item.get("sourceUrl", ""))
            if download.get("isBasedOn") != expected_download_source:
                issues.append(f"Pages index DataDownload isBasedOn drift: {item['key']}")
            if download.get("description") != download_description(download.get("name", ""), item["encoding"]):
                issues.append(f"Pages index DataDownload description drift: {item['key']}")
            if download.get("abstract") != download.get("description"):
                issues.append(f"Pages index DataDownload abstract drift: {item['key']}")
            expected_integrity = download_integrity_metadata(item["key"], index_data)
            for integrity_key in ("contentSize", "sha256"):
                if expected_integrity:
                    if download.get(integrity_key) != expected_integrity[integrity_key]:
                        issues.append(f"Pages index DataDownload {integrity_key} drift: {item['key']}")
                elif integrity_key in download:
                    issues.append(f"Pages index DataDownload unexpected {integrity_key}: {item['key']}")
            if download.get("inLanguage") != "en":
                issues.append(f"Pages index DataDownload inLanguage must be en: {item['key']}")
            check_content_usage_policy(issues, download, f"Pages index DataDownload {item['key']}")
            check_global_citation(issues, download, index_data, f"Pages index DataDownload {item['key']}")
            check_publisher_metadata(issues, download, index_data, f"Pages index DataDownload {item['key']}")
            check_ownership_metadata(issues, download, index_data, f"Pages index DataDownload {item['key']}")
            check_structured_data_provenance(issues, download, index_data, f"Pages index DataDownload {item['key']}")
    if f'<link rel="author" href="{PAGES_BASE}/humans.txt"/>' not in index_text:
        issues.append("Pages index missing author link to humans.txt")
    if '<link rel="me" href="https://github.com/Iron-Mark"/>' not in index_text:
        issues.append("Pages index missing rel=me identity link")

    if index_data.get("contentRoot") != "./":
        issues.append("Pages llms-index.json contentRoot must be ./")
    machine_readable = index_data.get("machineReadable", {})
    repo = machine_readable.get("repo", {})
    pages = machine_readable.get("pages", {})
    portfolio = machine_readable.get("portfolio", {})
    if not str(repo.get("llmsIndexJson", "")).startswith("https://github.com/Iron-Mark/Iron-Mark/blob/main/"):
        issues.append("Pages llms-index.json must preserve machineReadable.repo source URLs")
    expected_pages = {
        "home": f"{PAGES_BASE}/",
        "llmsTxt": f"{PAGES_BASE}/llms.txt",
        "llmsFullTxt": f"{PAGES_BASE}/llms-full.txt",
        "llmsIndexJson": f"{PAGES_BASE}/llms-index.json",
        "llmsCtxFullTxt": f"{PAGES_BASE}/llms-ctx-full.txt",
        "faqMd": f"{PAGES_BASE}/FAQ.md",
        "recruiterMd": f"{PAGES_BASE}/RECRUITER.md",
        "proofMd": f"{PAGES_BASE}/PROOF.md",
        "stackMd": f"{PAGES_BASE}/STACK.md",
        "profileMd": f"{PAGES_BASE}/PROFILE.md",
        "readmeMd": f"{PAGES_BASE}/README.md",
        "howToCiteMd": f"{PAGES_BASE}/HOW-TO-CITE.md",
        "licenseMd": f"{PAGES_BASE}/LICENSE.md",
        "citationCff": f"{PAGES_BASE}/CITATION.cff",
        "schemaPerson": f"{PAGES_BASE}/schema/person.jsonld",
        "schemaFaq": f"{PAGES_BASE}/schema/faq.jsonld",
        "schemaIndex": f"{PAGES_BASE}/schema/llms-index.schema.json",
        "humansTxt": f"{PAGES_BASE}/humans.txt",
        "sitemap": f"{PAGES_BASE}/sitemap.xml",
        "robots": f"{PAGES_BASE}/robots.txt",
    }
    for key, expected in expected_pages.items():
        if pages.get(key) != expected:
            issues.append(f"Pages llms-index.json machineReadable.pages.{key} must be {expected}")
    required_alternate_head_links = (
        ("application/rss+xml", portfolio.get("rss", "")),
        ("application/feed+json", portfolio.get("jsonFeed", "")),
        ("application/json", expected_pages["llmsIndexJson"]),
        ("text/plain", expected_pages["llmsTxt"]),
        ("text/plain", expected_pages["llmsFullTxt"]),
        ("text/plain", expected_pages["llmsCtxFullTxt"]),
        ("text/markdown", expected_pages["faqMd"]),
        ("text/markdown", expected_pages["recruiterMd"]),
        ("text/markdown", expected_pages["proofMd"]),
        ("text/markdown", f"{PAGES_BASE}/LAB.md"),
        ("text/html", f"{PAGES_BASE}/lab/"),
        ("text/markdown", expected_pages["stackMd"]),
        ("text/markdown", expected_pages["profileMd"]),
        ("text/markdown", expected_pages["readmeMd"]),
        ("text/markdown", expected_pages["howToCiteMd"]),
        ("text/markdown", expected_pages["licenseMd"]),
        ("text/plain", expected_pages["citationCff"]),
        ("text/plain", expected_pages["humansTxt"]),
        ("application/ld+json", expected_pages["schemaPerson"]),
        ("application/ld+json", expected_pages["schemaFaq"]),
        ("application/schema+json", expected_pages["schemaIndex"]),
    )
    required_head_links = {
        f'<link rel="alternate" type="{content_type}" href="{href}"/>'
        for content_type, href in required_alternate_head_links
    }
    required_head_links.update(
        {
            f'<link rel="license" href="{expected_pages["licenseMd"]}"/>',
            f'<link rel="sitemap" type="application/xml" href="{expected_pages["sitemap"]}"/>',
        }
    )
    for tag in required_head_links:
        if tag not in index_text:
            issues.append(f"Pages index missing absolute head resource link: {tag}")
    lab_text = (artifact / "lab" / "index.html").read_text(encoding="utf-8") if (artifact / "lab" / "index.html").exists() else ""
    for tag in (
        f'<link rel="alternate" type="application/rss+xml" href="{portfolio.get("rss", "")}"/>',
        f'<link rel="alternate" type="application/feed+json" href="{portfolio.get("jsonFeed", "")}"/>',
    ):
        if tag not in lab_text:
            issues.append(f"Pages lab page missing feed link: {tag}")

    robots_text = (artifact / "robots.txt").read_text(encoding="utf-8")
    if "Allow: /public/" in robots_text:
        issues.append("Pages robots.txt still references /public/")
    if f"Sitemap: {PAGES_BASE}/sitemap.xml" not in robots_text:
        issues.append("Pages robots.txt missing Pages sitemap directive")
    if "raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/sitemap.xml" in robots_text:
        issues.append("Pages robots.txt must not point at the raw GitHub sitemap")

    sitemap_path = artifact / "sitemap.xml"
    try:
        sitemap_text = sitemap_path.read_text(encoding="utf-8")
        if f'xmlns:image="{IMAGE_SITEMAP_NS}"' not in sitemap_text:
            issues.append("Pages sitemap missing Google image sitemap namespace")
        sitemap = ET.parse(sitemap_path)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "image": IMAGE_SITEMAP_NS}
        locs = [loc.text or "" for loc in sitemap.findall(".//sm:loc", ns)]
        root_url = next(
            (
                url
                for url in sitemap.findall(".//sm:url", ns)
                if url.findtext("sm:loc", default="", namespaces=ns) == f"{PAGES_BASE}/"
            ),
            None,
        )
        root_images = root_url.findall("image:image", ns) if root_url is not None else []
        if not root_images:
            issues.append("Pages sitemap root URL missing primary image entry")
        else:
            root_image_locs = [image.findtext("image:loc", default="", namespaces=ns) for image in root_images]
            if root_image_locs != [PAGES_SOCIAL_IMAGE]:
                issues.append("Pages sitemap primary image loc drift")
        readme_url = next(
            (
                url
                for url in sitemap.findall(".//sm:url", ns)
                if url.findtext("sm:loc", default="", namespaces=ns) == f"{PAGES_BASE}/README.md"
            ),
            None,
        )
        readme_images = readme_url.findall("image:image", ns) if readme_url is not None else []
        readme_image_locs = [image.findtext("image:loc", default="", namespaces=ns) for image in readme_images]
        expected_project_images = featured_project_cover_urls()
        if readme_image_locs != expected_project_images:
            issues.append("Pages sitemap README.md image entries must match featured project cover assets")
        for image in root_images + readme_images:
            deprecated_image_tags = [
                tag
                for tag in ("caption", "geo_location", "title", "license")
                if image.find(f"image:{tag}", ns) is not None
            ]
            if deprecated_image_tags:
                issues.append(f"Pages sitemap must not use deprecated image tags: {deprecated_image_tags}")
    except Exception as exc:
        issues.append(f"invalid Pages sitemap.xml: {exc}")
        locs = []
    required_locs = {
        f"{PAGES_BASE}/",
        f"{PAGES_BASE}/llms.txt",
        f"{PAGES_BASE}/llms-index.json",
        f"{PAGES_BASE}/FAQ.md",
        f"{PAGES_BASE}/RECRUITER.md",
        f"{PAGES_BASE}/PROOF.md",
        f"{PAGES_BASE}/lab/",
        f"{PAGES_BASE}/LAB.md",
        f"{PAGES_BASE}/STACK.md",
        f"{PAGES_BASE}/PROFILE.md",
        f"{PAGES_BASE}/README.md",
        f"{PAGES_BASE}/HOW-TO-CITE.md",
        f"{PAGES_BASE}/LICENSE.md",
        f"{PAGES_BASE}/CITATION.cff",
        f"{PAGES_BASE}/schema/person.jsonld",
        f"{PAGES_BASE}/schema/faq.jsonld",
        f"{PAGES_BASE}/schema/llms-index.schema.json",
        f"{PAGES_BASE}/humans.txt",
        f"{PAGES_BASE}/robots.txt",
    }
    missing_locs = sorted(required_locs - set(locs))
    if missing_locs:
        issues.append(f"Pages sitemap missing required loc(s): {missing_locs}")
    for loc in locs:
        parsed = urlparse(loc)
        if parsed.netloc != PAGES_HOST or not parsed.path.startswith("/Iron-Mark/"):
            issues.append(f"Pages sitemap contains non-Pages URL: {loc}")

    for path in sorted(artifact.rglob("*")):
        if not path.is_file() or (path.suffix not in TEXT_SUFFIXES and path.name != "llms-index.json"):
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(artifact)
        for target in extract_local_links(path, text):
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(artifact)
            except ValueError:
                issues.append(f"{rel}: local link escapes Pages artifact: {target}")
                continue
            if not resolved.exists():
                issues.append(f"{rel}: missing Pages local link target: {target}")
    return issues


def main() -> int:
    artifact = build_temp_artifact()
    issues = validate_artifact(artifact)
    if issues:
        print(f"validate_pages_mirror.py: FAIL ({len(issues)} issue(s))")
        for issue in issues:
            print(f"  ERROR {issue}")
        return 1
    print(f"validate_pages_mirror.py: OK ({artifact})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
