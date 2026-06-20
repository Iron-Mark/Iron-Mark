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
from build_pages_mirror import featured_project_cover_urls, project_cover_asset
from generate_schema import (
    DATASET_DATE_PUBLISHED,
    PROVIDE_SERVICE_BUSINESS_FUNCTION,
    SERVICE_PROVIDER_MOBILITY,
    dataset_alternate_names,
    dataset_measurement_techniques,
    dataset_temporal_coverage,
    download_description,
    download_id,
    download_integrity_metadata,
    faq_item_identifier,
    faq_question_id,
    featured_projects_list_description,
    lab_projects_list_description,
    lab_project_id,
    lab_project_url,
    machine_downloads,
    offer_description,
    pages_section_id,
    pages_section_nav_item_id,
    pages_section_navigation_id,
    pages_section_relation_ids,
    pages_section_specs,
    primary_image_description,
    profile_keywords,
    project_image_description,
    service_audience,
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
        and language.get("alternateName") == "en"
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
    expected = availability.get("areaServed", [])
    if node.get("spatialCoverage") != expected:
        issues.append(f"{label} spatialCoverage drift")


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
            json.loads((artifact / json_name).read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(f"invalid JSON in Pages artifact {json_name}: {exc}")
    try:
        index_data = json.loads((artifact / "llms-index.json").read_text(encoding="utf-8"))
    except Exception:
        index_data = {}
    for name in ("llms.txt", "humans.txt", "robots.txt"):
        path = artifact / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        non_ascii = sorted({f"U+{ord(char):04X}" for char in text if ord(char) > 127})
        if non_ascii:
            issues.append(f"Pages {name} must stay ASCII-only for plain-text crawler compatibility: {non_ascii}")
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
    for script in jsonld_scripts:
        try:
            jsonld = json.loads(script)
            public_url_values.extend(repo_public_url_values(jsonld))
            parsed_jsonld_nodes.extend(jsonld_nodes(jsonld))
        except json.JSONDecodeError:
            issues.append("Pages index contains invalid inline JSON-LD")
    if public_url_values:
        issues.append(f"Pages index inline JSON-LD must use Pages URLs for deployed public files: {public_url_values}")
    for node in parsed_jsonld_nodes:
        check_creativework_abstract(issues, node, f"Pages index {node.get('@id', node.get('name', 'node'))}")
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
    contact_entry = next(
        (node for node in parsed_jsonld_nodes if node.get("@id") == "https://www.marksiazon.dev/#contact-entrypoint"),
        None,
    )
    if not contact_entry or "EntryPoint" not in node_type_set(contact_entry):
        issues.append("Pages index inline JSON-LD missing contact EntryPoint node")
    else:
        if contact_entry.get("name") != "Mark Siazon contact form entry point":
            issues.append("Pages index contact EntryPoint name drift")
        if (
            contact_entry.get("description")
            != "Web entry point for Mark Siazon hiring contact and recruiter inquiries."
        ):
            issues.append("Pages index contact EntryPoint description drift")
        if contact_entry.get("urlTemplate") != availability.get("contact"):
            issues.append("Pages index contact EntryPoint urlTemplate drift")
        if contact_entry.get("contentType") != "text/html":
            issues.append("Pages index contact EntryPoint contentType must be text/html")
        if contact_entry.get("httpMethod") != "GET":
            issues.append("Pages index contact EntryPoint httpMethod must be GET")
        if contact_entry.get("inLanguage") != "en":
            issues.append("Pages index contact EntryPoint inLanguage must be en")
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
    elif f"{PAGES_BASE}/#webpage" not in ref_ids(person.get("mainEntityOfPage")):
        issues.append("Pages index inline JSON-LD Person mainEntityOfPage missing Pages CollectionPage")
    person_nodes = [
        node
        for node in parsed_jsonld_nodes
        if node.get("@id") == "https://www.marksiazon.dev/#person" and "Person" in node_type_set(node)
    ]
    for person_node in person_nodes:
        check_person_identity_resolution(issues, person_node, index_data, "Pages index Person")
    pages_topic_set_id = topic_term_set_id()
    if person and pages_topic_set_id not in ref_ids(person.get("knowsAbout")):
        issues.append("Pages index Person knowsAbout missing topic taxonomy")
    if person:
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
        if offer_catalog.get("inLanguage") != "en":
            issues.append("Pages index OfferCatalog inLanguage must be en")
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
        if service_channel.get("serviceUrl") != availability.get("contact"):
            issues.append("Pages index ServiceChannel serviceUrl drift")
        if "en" not in service_channel.get("availableLanguage", []):
            issues.append("Pages index ServiceChannel availableLanguage must include en")
        missing_channel_services = sorted(expected_service_ids - ref_ids(service_channel.get("providesService")))
        if missing_channel_services:
            issues.append(f"Pages index ServiceChannel providesService missing: {missing_channel_services}")
        if service_channel.get("about", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index ServiceChannel about drift")
        if service_channel.get("dateModified") != index_data.get("updated"):
            issues.append("Pages index ServiceChannel dateModified drift")
    for focus in focus_items:
        offer_id = f"https://www.marksiazon.dev/#offer-{slugify(str(focus))}"
        service_id = f"https://www.marksiazon.dev/#service-{slugify(str(focus))}"
        offer = next((node for node in parsed_jsonld_nodes if node.get("@id") == offer_id), None)
        if not offer or "Offer" not in node_type_set(offer):
            issues.append(f"Pages index missing Offer node: {offer_id}")
        else:
            if offer.get("identifier") != service_focus_identifier(str(focus), "offer"):
                issues.append(f"Pages index Offer identifier drift: {focus}")
            if offer.get("description") != offer_description(index_data, str(focus)):
                issues.append(f"Pages index Offer description drift: {focus}")
            if offer.get("mainEntityOfPage") != availability.get("recruiterBrief"):
                issues.append(f"Pages index Offer mainEntityOfPage drift: {focus}")
            if offer.get("itemOffered", {}).get("@id") != service_id:
                issues.append(f"Pages index Offer itemOffered drift: {focus}")
            if offer.get("businessFunction") != PROVIDE_SERVICE_BUSINESS_FUNCTION:
                issues.append(f"Pages index Offer businessFunction drift: {focus}")
            if offer.get("seller", {}).get("@id") != "https://www.marksiazon.dev/#person":
                issues.append(f"Pages index Offer seller drift: {focus}")
            area_served = set(availability.get("areaServed", []))
            missing_eligible_region = sorted(area_served - area_names(offer.get("eligibleRegion")))
            if missing_eligible_region:
                issues.append(f"Pages index Offer eligibleRegion missing for {focus}: {missing_eligible_region}")
        service = next((node for node in parsed_jsonld_nodes if node.get("@id") == service_id), None)
        if not service or "Service" not in node_type_set(service):
            issues.append(f"Pages index missing Service node: {service_id}")
        else:
            if service.get("identifier") != service_focus_identifier(str(focus), "service"):
                issues.append(f"Pages index Service identifier drift: {focus}")
            if service.get("description") != service_description(index_data, str(focus)):
                issues.append(f"Pages index Service description drift: {focus}")
            if service.get("mainEntityOfPage") != availability.get("recruiterBrief"):
                issues.append(f"Pages index Service mainEntityOfPage drift: {focus}")
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
        check_review_metadata(issues, profile_page, index_data, "Pages index GitHub ProfilePage")
        check_spatial_coverage(issues, profile_page, index_data, "Pages index GitHub ProfilePage")
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
        if data_catalog.get("isBasedOn") != expected_based_on:
            issues.append("Pages index DataCatalog isBasedOn drift")
        if data_catalog.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index DataCatalog keywords drift")
        if data_catalog.get("creator", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index DataCatalog creator drift")
        if data_catalog.get("datePublished") != DATASET_DATE_PUBLISHED:
            issues.append("Pages index DataCatalog datePublished drift")
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
        if dataset.get("spatialCoverage") != area_served:
            issues.append("Pages index inline Dataset spatialCoverage drift")
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
    faq_page = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/FAQ.md#faq"), None)
    if not faq_page or "FAQPage" not in node_type_set(faq_page):
        issues.append("Pages index inline JSON-LD missing FAQPage")
    else:
        if faq_page.get("isBasedOn") != f"{PAGES_BASE}/FAQ.md":
            issues.append("Pages index FAQPage isBasedOn drift")
        if faq_page.get("inLanguage") != "en":
            issues.append("Pages index FAQPage inLanguage must be en")
        if faq_page.get("author", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index FAQPage author drift")
        if faq_page.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
            issues.append("Pages index FAQPage publisher drift")
        if faq_page.get("keywords") != profile_keywords(index_data):
            issues.append("Pages index FAQPage keywords drift")
        if faq_page.get("isAccessibleForFree") is not True:
            issues.append("Pages index FAQPage must be isAccessibleForFree")
        expected_question_ids = {
            faq_question_id(f"{PAGES_BASE}/FAQ.md#faq", str(item.get("question", "")))
            for item in index_data.get("aeo", {}).get("answerSnippets", [])
            if isinstance(item, dict)
        }
        missing_has_part = sorted(expected_question_ids - ref_ids(faq_page.get("hasPart")))
        if missing_has_part:
            issues.append(f"Pages index FAQPage hasPart missing questions: {missing_has_part}")
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
    for node in parsed_jsonld_nodes:
        node_types = node_type_set(node)
        if "Question" in node_types:
            question_id = str(node.get("@id", ""))
            question_name = str(node.get("name", ""))
            if node.get("url") != question_id:
                issues.append(f"Pages index Question url drift: {node.get('name')}")
            if node.get("identifier") != faq_item_identifier(question_id, "question"):
                issues.append(f"Pages index Question identifier drift: {node.get('name')}")
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
            if isinstance(answer, dict):
                answer_id = f"{question_id}-answer"
                if answer.get("url") != answer_id:
                    issues.append(f"Pages index Answer url drift: {node.get('name')}")
                if answer.get("identifier") != faq_item_identifier(answer_id, "answer"):
                    issues.append(f"Pages index Answer identifier drift: {node.get('name')}")
                if answer.get("publisher", {}).get("@id") != "https://www.marksiazon.dev/#person":
                    issues.append(f"Pages index Answer publisher drift: {node.get('name')}")
                if answer.get("isPartOf", {}).get("@id") != f"{PAGES_BASE}/FAQ.md#faq":
                    issues.append(f"Pages index Answer isPartOf drift: {node.get('name')}")
                if answer.get("parentItem", {}).get("@id") != question_id:
                    issues.append(f"Pages index Answer parentItem drift: {node.get('name')}")
                if answer.get("isAccessibleForFree") is not True:
                    issues.append(f"Pages index Answer must be isAccessibleForFree: {node.get('name')}")
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
        missing_featured_ids = sorted(expected_featured_ids - item_list_ref_ids(featured_list.get("itemListElement")))
        if missing_featured_ids:
            issues.append(f"Pages index featured projects ItemList missing: {missing_featured_ids}")
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
        missing_lab_ids = sorted(expected_lab_ids - item_list_ref_ids(lab_list.get("itemListElement")))
        if missing_lab_ids:
            issues.append(f"Pages index hackathon and lab ItemList missing: {missing_lab_ids}")
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
    if '<link rel="author" href="humans.txt"/>' not in index_text:
        issues.append("Pages index missing author link to humans.txt")
    if '<link rel="me" href="https://github.com/Iron-Mark"/>' not in index_text:
        issues.append("Pages index missing rel=me identity link")

    if index_data.get("contentRoot") != "./":
        issues.append("Pages llms-index.json contentRoot must be ./")
    machine_readable = index_data.get("machineReadable", {})
    repo = machine_readable.get("repo", {})
    pages = machine_readable.get("pages", {})
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
