#!/usr/bin/env python3
"""Generate Schema.org JSON-LD graphs from llms-index.json."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from build_pages_mirror import (
    rewrite_github_public_urls,
    rewrite_llms_index,
    rewrite_relative_public_paths,
    rewrite_repo_only_paths,
    rewrite_robots,
    rewrite_sitemap,
)

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "public"
SCHEMA = PUBLIC / "schema"
INDEX = ROOT / "llms-index.json"

GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
PAGES = "https://iron-mark.github.io/Iron-Mark"
PAGES_SITE_NAME = "Mark Siazon Profile Index"
PAGES_SITE_ALTERNATE_NAMES = ["Iron-Mark Profile Index", "Mark Siazon GitHub Profile Index"]
PAGES_IMAGE = f"{PAGES}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.png"
PAGES_IMAGE_ASSET = ROOT / "assets" / "brand" / "mark-siazon-product-design-full-stack-profile-banner.png"
IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 675
CONTENT_LANGUAGE = "en"
PROFILE_LANGUAGE = {"@type": "Language", "name": "English", "alternateName": CONTENT_LANGUAGE}
PROVIDE_SERVICE_BUSINESS_FUNCTION = "http://purl.org/goodrelations/v1#ProvideService"
DATASET_DATE_PUBLISHED = "2026-06-13"
SERVICE_PROVIDER_MOBILITY = "dynamic"
PROJECT_IMAGE_EXTENSIONS = (
    (".webp", "image/webp"),
    (".png", "image/png"),
    (".svg", "image/svg+xml"),
)
DOWNLOAD_SOURCE_PATHS = {
    "llms-index-json": ROOT / "llms-index.json",
    "llms-txt": ROOT / "llms.txt",
    "llms-full-txt": PUBLIC / "llms-full.txt",
    "llms-ctx-full-txt": PUBLIC / "llms-ctx-full.txt",
    "faq-md": PUBLIC / "FAQ.md",
    "recruiter-md": PUBLIC / "RECRUITER.md",
    "proof-md": PUBLIC / "PROOF.md",
    "stack-md": PUBLIC / "STACK.md",
    "profile-md": PUBLIC / "PROFILE.md",
    "readme-md": PUBLIC / "README.md",
    "how-to-cite-md": PUBLIC / "HOW-TO-CITE.md",
    "license-md": PUBLIC / "LICENSE.md",
    "citation-cff": PUBLIC / "CITATION.cff",
    "faq-jsonld": SCHEMA / "faq.jsonld",
    "schema-json": SCHEMA / "llms-index.schema.json",
    "humans-txt": ROOT / "humans.txt",
    "sitemap-xml": ROOT / "sitemap.xml",
    "robots-txt": ROOT / "robots.txt",
}


def content_language() -> str:
    return CONTENT_LANGUAGE


def available_languages() -> list[str]:
    return [content_language()]


def person_languages() -> list[dict[str, str]]:
    return [PROFILE_LANGUAGE]


def ref(node_id: str) -> dict[str, str]:
    return {"@id": node_id}


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value


def faq_question_id(faq_id: str, question: str) -> str:
    faq_url = faq_id.split("#", 1)[0]
    return f"{faq_url}#{slugify(question)}"


def faq_item_identifier(item_id: str, kind: str) -> dict[str, str]:
    return {
        "@type": "PropertyValue",
        "propertyID": f"Iron-Mark FAQ {kind}",
        "value": item_id.rsplit("#", 1)[-1],
        "url": item_id,
    }


def faq_document_identifier(faq_id: str) -> dict[str, str]:
    return {
        "@type": "PropertyValue",
        "propertyID": "Iron-Mark FAQ document",
        "value": "mark-siazon-frequently-asked-questions",
        "url": faq_id,
    }


def project_id(project: dict[str, Any]) -> str:
    return f"{project['caseStudy']}#project"


def lab_project_url(project: dict[str, Any]) -> str:
    return str(project.get("caseStudy") or project.get("demo") or project.get("live") or project.get("repo") or "")


def lab_project_id(project: dict[str, Any]) -> str:
    return f"{lab_project_url(project)}#project"


def file_integrity_metadata(path: Path) -> dict[str, str]:
    if path.suffix.lower() == ".svg":
        data = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    else:
        data = path.read_bytes()
    return {
        "contentSize": f"{len(data)} bytes",
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def project_image_info(project: dict[str, Any]) -> dict[str, str] | None:
    slug = str(project.get("slug", ""))
    if not slug:
        return None
    for suffix, encoding in PROJECT_IMAGE_EXTENSIONS:
        path = ROOT / "assets" / "projects" / slug / f"cover{suffix}"
        if path.exists():
            url = f"{PAGES}/assets/projects/{slug}/cover{suffix}"
            return {
                "@id": f"{url}#image",
                "url": url,
                "encodingFormat": encoding,
                **file_integrity_metadata(path),
            }
    return None


def primary_image_description() -> str:
    return IMAGE_ALT


def project_image_description(project: dict[str, Any]) -> str:
    name = str(project.get("name", "")).strip()
    focus = str(project.get("focus", "")).strip()
    if name and focus:
        return f"{name} project cover image for {focus}."
    if name:
        return f"{name} project cover image."
    return "Project cover image."


def _human_join(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def service_description(data: dict[str, Any], focus: str) -> str:
    availability = data.get("availability", {})
    regions = _human_join([str(value) for value in availability.get("areaServed", []) if value])
    engagements = _human_join([str(value) for value in availability.get("engagement", []) if value])
    region_text = f" for {regions}" if regions else ""
    engagement_text = f" through {engagements} work" if engagements else ""
    return f"Mark Siazon {focus} service{region_text}{engagement_text}."


def offer_description(data: dict[str, Any], focus: str) -> str:
    availability = data.get("availability", {})
    status = "Open" if availability.get("status") == "open" else "Limited"
    regions = _human_join([str(value) for value in availability.get("areaServed", []) if value])
    region_text = f" across {regions}" if regions else ""
    return f"{status} availability for Mark Siazon {focus} service{region_text}."


def offer_availability(data: dict[str, Any]) -> str:
    if data.get("availability", {}).get("status") == "open":
        return "https://schema.org/InStock"
    return "https://schema.org/LimitedAvailability"


def featured_projects_list_description(data: dict[str, Any]) -> str:
    count = len(data.get("featuredProjects", []))
    return f"Ordered list of {count} featured Mark Siazon project case studies for proof-backed product, AI, mobile, Web3, and client web work."


def lab_projects_list_description(data: dict[str, Any]) -> str:
    count = len(data.get("hackathonLab", []))
    return f"Ordered list of {count} Mark Siazon hackathon and lab projects with demos, repositories, or case studies."


def profile_keywords(data: dict[str, Any]) -> list[str]:
    availability = data.get("availability", {})
    area_served = availability.get("areaServed") or data.get("seo", {}).get("geoSignals", {}).get("serviceRegions", [])
    return unique_compact(
        data.get("seo", {}).get("primaryKeywords", [])
        + data.get("seo", {}).get("geoTargets", [])
        + area_served
    )


def image_rights(data: dict[str, Any]) -> dict[str, Any]:
    entity = data["entity"]
    pages = data["machineReadable"]["pages"]
    availability = data.get("availability", {})
    return {
        "license": pages["licenseMd"],
        "usageInfo": pages["licenseMd"],
        "acquireLicensePage": availability.get("contact", entity["url"]),
        "creditText": entity["name"],
        "copyrightNotice": f"Copyright {entity['name']}",
        "creator": {
            "@type": "Person",
            "@id": entity["@id"],
            "name": entity["name"],
            "url": entity["url"],
        },
        "publisher": ref(entity["@id"]),
        **ownership_metadata(data),
        **structured_data_provenance(data),
    }


def content_usage_policy(data: dict[str, Any]) -> dict[str, str]:
    repo = data["machineReadable"]["repo"]
    return {
        "usageInfo": repo["howToCiteMd"],
        "publishingPrinciples": repo["proofMd"],
    }


def structured_data_provenance(data: dict[str, Any]) -> dict[str, Any]:
    entity = data["entity"]
    return {
        "sdPublisher": {
            "@type": "Person",
            "@id": entity["@id"],
            "name": entity["name"],
            "url": entity["url"],
        },
        "sdDatePublished": data["updated"],
        "sdLicense": data.get("license"),
    }


def ownership_metadata(data: dict[str, Any]) -> dict[str, Any]:
    entity = data["entity"]
    return {
        "accountablePerson": ref(entity["@id"]),
        "copyrightHolder": ref(entity["@id"]),
        "copyrightYear": int(str(data["updated"])[:4]),
    }


def review_metadata(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "reviewedBy": ref(data["entity"]["@id"]),
        "lastReviewed": data["updated"],
    }


def profile_disambiguating_description(data: dict[str, Any]) -> str:
    entity = data["entity"]
    return (
        f"{entity['name']} is the Philippines-based product designer and full-stack developer "
        "behind the Iron-Mark GitHub profile, marksiazon.dev portfolio, and proof-backed AI, "
        "mobile, Web3, and client web case studies."
    )


def person_core_identity(data: dict[str, Any]) -> dict[str, Any]:
    entity = data["entity"]
    return {
        "name": entity["name"],
        "alternateName": entity.get("alternateName", []),
        "jobTitle": entity.get("jobTitle", []),
        "description": entity["description"],
        "url": entity["url"],
        "address": entity.get("address"),
    }


def person_identifiers(data: dict[str, Any]) -> list[dict[str, str]]:
    entity = data["entity"]
    canonical = data["canonical"]
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
            "value": entity["url"],
            "url": entity["url"],
        },
        {
            "@type": "PropertyValue",
            "propertyID": "GitHub profile repository",
            "value": "Iron-Mark/Iron-Mark",
            "url": canonical["githubProfileReadme"],
        },
    ]


def spatial_coverage(data: dict[str, Any]) -> list[dict[str, str]]:
    return area_served_nodes(list(data.get("availability", {}).get("areaServed", [])))


def dataset_variable_measurements(
    data: dict[str, Any],
    area_served: list[str],
    downloads: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "@type": "PropertyValue",
            "name": "Person entity identifier",
            "value": data["entity"]["@id"],
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
            "value": len(downloads),
        },
    ]


def dataset_alternate_names(data: dict[str, Any]) -> list[str]:
    entity = data["entity"]
    return unique_compact(
        [
            f"{entity['name']} structured profile dataset",
            "Iron-Mark profile index",
            "Iron-Mark llms-index.json",
            "Mark Siazon machine-readable discovery dataset",
        ]
    )


def dataset_measurement_techniques() -> list[str]:
    return [
        "Generated from llms-index.json, public Markdown files, and Schema.org JSON-LD graph output.",
        "Computed byte-size and SHA-256 integrity metadata from the GitHub Pages mirror output.",
    ]


def dataset_temporal_coverage(data: dict[str, Any]) -> str:
    return f"{DATASET_DATE_PUBLISHED}/{data['updated']}"


def service_focus_identifier(focus: str, kind: str) -> dict[str, str]:
    return {
        "@type": "PropertyValue",
        "propertyID": f"Iron-Mark {kind} focus",
        "name": focus,
        "value": slugify(focus),
    }


def service_audience() -> dict[str, str]:
    return {
        "@type": "Audience",
        "audienceType": "recruiters, founders, product teams, and engineering teams",
    }


def contact_action_platforms() -> list[str]:
    return [
        "https://schema.org/DesktopWebPlatform",
        "https://schema.org/MobileWebPlatform",
    ]


def contact_action_name() -> str:
    return "Contact Mark Siazon for hiring"


def contact_action_description() -> str:
    return "Contact path for product design, full-stack engineering, AI workflow, mobile, and Web3 proof work."


def contact_entry_name() -> str:
    return "Mark Siazon contact form entry point"


def contact_entry_description() -> str:
    return "Web entry point for Mark Siazon hiring contact and recruiter inquiries."


def contact_entry_content_type() -> str:
    return "text/html"


def contact_entry_http_method() -> str:
    return "GET"


def service_channel_name() -> str:
    return "Mark Siazon hiring service channel"


def service_channel_description() -> str:
    return "Web contact channel for product design, full-stack engineering, AI workflow, mobile, and Web3 proof work."


def person_occupations(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "@type": "Occupation",
            "name": title,
            "occupationLocation": {
                "@type": "Country",
                "name": "Philippines",
            },
        }
        for title in data.get("entity", {}).get("jobTitle", [])
    ]


def person_work_locations(data: dict[str, Any]) -> list[dict[str, str]]:
    return spatial_coverage(data)


def person_email(data: dict[str, Any]) -> str:
    email = data["entity"]["email"]
    return email if email.startswith("mailto:") else f"mailto:{email}"


def person_hiring_contact(data: dict[str, Any]) -> dict[str, Any]:
    entity = data["entity"]
    availability = data.get("availability", {})
    return {
        "@type": "ContactPoint",
        "@id": fragment_id(entity["@id"], "hiring-contact"),
        "contactType": "hiring",
        "email": person_email(data),
        "url": availability.get("contact", entity["url"]),
        "areaServed": spatial_coverage(data),
        "availableLanguage": available_languages(),
    }


def person_main_entity_pages(data: dict[str, Any]) -> list[dict[str, str]]:
    ids = data["identifiers"]
    return [
        ref(ids["githubProfilePage"]),
        ref(ids["portfolioWebsite"]),
        ref(f"{PAGES}/#webpage"),
    ]


def person_knows_about(data: dict[str, Any]) -> list[str | dict[str, str]]:
    topic_terms = topic_term_values(data)
    return (
        unique_compact(data.get("coreStack", []) + data.get("seo", {}).get("primaryKeywords", []))
        + [ref(topic_term_id(term)) for term in topic_terms]
        + [ref(topic_term_set_id())]
    )


def person_subjects(data: dict[str, Any]) -> list[dict[str, str]]:
    schema = data["schema"]
    return [
        ref(f"{GITHUB_BLOB}/llms-index.json#creativework"),
        ref(f"{GITHUB_BLOB}/public/FAQ.md#creativework"),
        ref(f"{GITHUB_BLOB}/public/PROOF.md#creativework"),
        ref(f"{GITHUB_BLOB}/public/RECRUITER.md#creativework"),
        ref(f"{GITHUB_BLOB}/public/schema/llms-index.schema.json#creativework"),
        ref(schema["person"]),
        ref(schema["faq"]),
        ref(schema["index"]),
    ]


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


def pages_speakable_selectors(data: dict[str, Any]) -> list[str]:
    selectors = ["#profile-summary"]
    for item in data.get("aeo", {}).get("answerSnippets", [])[:3]:
        question = item.get("question")
        if isinstance(question, str) and question:
            selectors.append(f"#{answer_dom_id(question)}")
    return selectors


def pages_speakable_spec(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "@type": "SpeakableSpecification",
        "@id": f"{PAGES}/#speakable",
        "cssSelector": pages_speakable_selectors(data),
    }


def pages_section_id(fragment: str) -> str:
    return f"{PAGES}/#{fragment}"


def pages_section_navigation_id() -> str:
    return f"{PAGES}/#section-navigation"


def pages_section_nav_item_id(fragment: str) -> str:
    return f"{PAGES}/#nav-{fragment}"


def pages_section_specs(data: dict[str, Any]) -> list[dict[str, str]]:
    entity = data.get("entity", {})
    availability = data.get("availability", {})
    seo = data.get("seo", {})
    aeo = data.get("aeo", {})
    featured = data.get("featuredProjects", [])
    triples = data.get("triples", [])
    machine_readable = data.get("machineReadable", {})
    pages = machine_readable.get("pages", {}) if isinstance(machine_readable, dict) else {}

    role_text = ", ".join(entity.get("jobTitle", []))
    focus_text = ", ".join(availability.get("focus", []))
    area_text = ", ".join(availability.get("areaServed", []))
    project_text = "; ".join(
        f"{project.get('name', 'Project')}: {project.get('focus', 'featured work')}"
        for project in featured
        if isinstance(project, dict)
    )
    topic_text = ", ".join(
        unique_compact(
            seo.get("primaryKeywords", [])
            + seo.get("geoTargets", [])
            + availability.get("areaServed", [])
        )
    )
    triple_text = "; ".join(
        " | ".join(triple)
        for triple in triples
        if isinstance(triple, list) and len(triple) == 3 and all(isinstance(part, str) for part in triple)
    )
    start_files = unique_compact(
        [
            pages.get("llmsIndexJson"),
            pages.get("llmsCtxFullTxt"),
            pages.get("faqMd"),
            pages.get("recruiterMd"),
            pages.get("proofMd"),
            pages.get("llmsTxt"),
            pages.get("schemaIndex"),
            pages.get("schemaPerson"),
            pages.get("schemaFaq"),
        ]
    )
    citation_text = "; ".join(citation_targets(data))

    return [
        {
            "fragment": "profile-facts",
            "heading": "Profile Facts",
            "name": "Mark Siazon profile facts",
            "description": "Visible profile facts for Mark Siazon name, roles, availability, service geography, contact, and recruiter brief.",
            "text": (
                f"{entity.get('name', 'Mark Siazon')}; roles: {role_text}; "
                f"availability: {availability.get('status', 'open')}; focus: {focus_text}; "
                f"location: {availability.get('location', 'Philippines')}; serves: {area_text}."
            ),
        },
        {
            "fragment": "featured-work",
            "heading": "Featured Work",
            "name": "Mark Siazon featured work",
            "description": "Visible featured project list for Mark Siazon proof-backed product, AI, mobile, Web3, and client web work.",
            "text": project_text,
        },
        {
            "fragment": "answer-corpus",
            "heading": "Answer Corpus",
            "name": "Mark Siazon answer corpus",
            "description": "Visible question and answer corpus for Mark Siazon hiring, projects, stack, verification, geography, and citation.",
            "text": (
                f"{len(aeo.get('answerSnippets', []))} answer snippets covering hiring, projects, "
                "stack, verification, geography, and citation."
            ),
        },
        {
            "fragment": "geo-topic-signals",
            "heading": "Geo And Topic Signals",
            "name": "Mark Siazon geo and topic signals",
            "description": "Visible search topics and service regions for Mark Siazon AEO, SEO, and GEO discovery.",
            "text": topic_text,
        },
        {
            "fragment": "knowledge-graph",
            "heading": "Knowledge Graph",
            "name": "Mark Siazon knowledge graph",
            "description": "Visible subject-predicate-object facts for Mark Siazon identity, service geography, and project relationships.",
            "text": triple_text,
        },
        {
            "fragment": "start-here",
            "heading": "Start Here",
            "name": "Mark Siazon machine-readable starting points",
            "description": "Visible entry links to Mark Siazon structured profile, answer, proof, recruiter, LLM, and Schema.org files.",
            "text": "; ".join(start_files),
        },
        {
            "fragment": "citation",
            "heading": "Citation",
            "name": "Mark Siazon citation guidance",
            "description": "Visible citation order and verification boundaries for Mark Siazon public profile facts.",
            "text": f"Preferred citation order: {citation_text}.",
        },
    ]


def pages_section_relation_ids(data: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    entity = data.get("entity", {})
    person_id = entity.get("@id", "")
    machine_readable = data.get("machineReadable", {})
    repo = machine_readable.get("repo", {}) if isinstance(machine_readable, dict) else {}
    pages = machine_readable.get("pages", {}) if isinstance(machine_readable, dict) else {}
    availability = data.get("availability", {})
    focus_items = availability.get("focus", []) if isinstance(availability, dict) else []
    featured_projects = data.get("featuredProjects", [])
    lab_projects = data.get("hackathonLab", [])

    pages_catalog_id = f"{PAGES}/#data-catalog"
    pages_dataset_id = f"{PAGES}/#machine-readable-dataset"
    pages_topic_set_id = topic_term_set_id()
    faq_id = data.get("identifiers", {}).get("faqDocument", "")
    contact_action_id = fragment_id(person_id, "contact-action")
    contact_entry_id = fragment_id(person_id, "contact-entrypoint")
    service_channel_id = fragment_id(person_id, "hiring-service-channel")
    services_catalog_id = fragment_id(person_id, "services")
    offer_ids = [fragment_id(person_id, f"offer-{slugify(str(focus))}") for focus in focus_items]
    service_ids = [fragment_id(person_id, f"service-{slugify(str(focus))}") for focus in focus_items]
    featured_list_id = f"{GITHUB_BLOB}/llms-index.json#featured-projects"
    lab_list_id = f"{GITHUB_BLOB}/llms-index.json#hackathon-lab"
    featured_project_ids = [
        project_id(project)
        for project in featured_projects
        if isinstance(project, dict) and project.get("caseStudy")
    ]
    lab_project_ids = [
        lab_project_id(project)
        for project in lab_projects
        if isinstance(project, dict) and lab_project_url(project)
    ]
    topic_ids = [topic_term_id(term) for term in topic_term_values(data)]
    download_ids = {
        item["key"]: download_id(item["key"])
        for item in machine_downloads(pages, repo)
        if item.get("key")
    }

    def downloads(*keys: str) -> list[str]:
        return [download_ids[key] for key in keys if key in download_ids]

    return {
        "profile-facts": {
            "mentions": unique_compact(
                [
                    services_catalog_id,
                    contact_action_id,
                    contact_entry_id,
                    service_channel_id,
                    *offer_ids,
                    *service_ids,
                ]
            )
        },
        "featured-work": {
            "hasPart": unique_compact([featured_list_id, *featured_project_ids])
        },
        "answer-corpus": {
            "hasPart": unique_compact([faq_id])
        },
        "geo-topic-signals": {
            "hasPart": unique_compact([pages_topic_set_id, *topic_ids])
        },
        "knowledge-graph": {
            "mentions": unique_compact(
                [
                    featured_list_id,
                    lab_list_id,
                    services_catalog_id,
                    *service_ids,
                    *featured_project_ids,
                    *lab_project_ids,
                    pages_topic_set_id,
                ]
            )
        },
        "start-here": {
            "hasPart": unique_compact(
                [
                    pages_catalog_id,
                    pages_dataset_id,
                    *downloads(
                        "llms-index-json",
                        "llms-ctx-full-txt",
                        "faq-md",
                        "recruiter-md",
                        "proof-md",
                        "llms-txt",
                        "schema-json",
                        "person-jsonld",
                        "faq-jsonld",
                    ),
                ]
            )
        },
        "citation": {
            "hasPart": downloads("how-to-cite-md", "proof-md", "citation-cff")
        },
    }


def profile_page_part_ids(data: dict[str, Any]) -> list[str]:
    entity = data.get("entity", {})
    person_id = entity.get("@id", "")
    machine_readable = data.get("machineReadable", {})
    repo = machine_readable.get("repo", {}) if isinstance(machine_readable, dict) else {}
    identifiers = data.get("identifiers", {})

    return unique_compact(
        [
            fragment_id(person_id, "services"),
            f"{GITHUB_BLOB}/llms-index.json#featured-projects",
            f"{GITHUB_BLOB}/llms-index.json#hackathon-lab",
            identifiers.get("faqDocument", ""),
            repo.get("llmsIndexJson", ""),
            repo.get("llmsTxt", ""),
            repo.get("llmsFullTxt", ""),
            repo.get("llmsCtxFullTxt", ""),
            repo.get("faqMd", ""),
            repo.get("recruiterMd", ""),
            repo.get("proofMd", ""),
            repo.get("profileMd", ""),
            repo.get("stackMd", ""),
            repo.get("howToCiteMd", ""),
            repo.get("citationCff", ""),
            repo.get("schemaPerson", ""),
            repo.get("schemaFaq", ""),
            repo.get("schemaIndex", ""),
        ]
    )


def topic_term_values(data: dict[str, Any]) -> list[str]:
    return unique_compact(
        data.get("seo", {}).get("primaryKeywords", [])
        + data.get("availability", {}).get("focus", [])
        + data.get("seo", {}).get("geoTargets", [])
    )


def topic_term_set_id() -> str:
    return f"{PAGES}/#topic-taxonomy"


def topic_term_id(value: str) -> str:
    return f"{PAGES}/#term-{slugify(value)}"


def topic_term_description(data: dict[str, Any], value: str) -> str:
    if value in data.get("seo", {}).get("geoTargets", []):
        return f"Geographic service target for the Mark Siazon profile index: {value}."
    if value in data.get("availability", {}).get("focus", []):
        return f"Service focus for Mark Siazon hiring and collaboration discovery: {value}."
    return f"Primary search and answer-engine topic for the Mark Siazon profile index: {value}."


def citation_targets(data: dict[str, Any]) -> list[str]:
    repo = data["machineReadable"]["repo"]
    return unique_compact(
        data.get("aeo", {}).get("preferredCitationOrder", [])
        + [
            repo.get("howToCiteMd"),
            repo.get("citationCff"),
        ]
    )


def compact(values: list[str | None]) -> list[str]:
    return [value for value in values if value]


def unique_compact(values: list[str | None]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in compact(values):
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


def schema_url(path: str) -> str:
    return f"{GITHUB_BLOB}/{path}"


def fragment_id(base_id: str, fragment: str) -> str:
    return f"{base_id.split('#', 1)[0]}#{fragment}"


def area_served_nodes(regions: list[str]) -> list[dict[str, str]]:
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


def content_work(
    node_id: str,
    name: str,
    url: str,
    encoding: str,
    description: str,
    person_id: str,
    date_modified: str,
    license_url: str,
    sd_provenance: dict[str, Any] | None = None,
    citations: list[str] | None = None,
    usage_policy: dict[str, str] | None = None,
    ownership: dict[str, Any] | None = None,
    spatial: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "@type": "CreativeWork",
        "@id": node_id,
        "name": name,
        "url": url,
        "encodingFormat": encoding,
        "description": description,
        "abstract": description,
        "author": ref(person_id),
        "about": ref(person_id),
        "inLanguage": "en",
        "dateModified": date_modified,
        "license": license_url,
        "isAccessibleForFree": True,
        "publisher": ref(person_id),
        "citation": citations or [],
        **({"spatialCoverage": spatial} if spatial else {}),
        **(usage_policy or {}),
        **(ownership or {}),
        **(sd_provenance or {}),
    }


def serialized_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def text_integrity_metadata(text: str) -> dict[str, str]:
    data = text.encode("utf-8")
    return {
        "contentSize": f"{len(data)} bytes",
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def pages_mirror_text(text: str, source_path: Path) -> str:
    if source_path.name == "llms-index.json":
        return rewrite_llms_index(text)

    updated = rewrite_github_public_urls(text)
    updated = rewrite_relative_public_paths(updated, source_path)
    updated = rewrite_repo_only_paths(updated)
    if source_path.name == "robots.txt":
        updated = rewrite_robots(updated)
    if source_path.name == "sitemap.xml":
        updated = rewrite_sitemap(updated)
    return updated


def download_integrity_metadata(key: str, data: dict[str, Any]) -> dict[str, str]:
    if key == "person-jsonld":
        return {}
    source_path = DOWNLOAD_SOURCE_PATHS.get(key)
    if not source_path:
        return {}
    if key == "faq-jsonld":
        text = serialized_json(build_faq_graph(data))
    else:
        text = source_path.read_text(encoding="utf-8")
    return text_integrity_metadata(pages_mirror_text(text, source_path))


def download_id(key: str) -> str:
    return f"{PAGES}/#download-{slugify(key)}"


def machine_downloads(pages: dict[str, str], repo: dict[str, str] | None = None) -> list[dict[str, str]]:
    rows = [
        ("llms-index-json", "Structured entity index", "llmsIndexJson", "application/json"),
        ("llms-txt", "LLM manifest", "llmsTxt", "text/plain"),
        ("llms-full-txt", "Full LLM context", "llmsFullTxt", "text/plain"),
        ("llms-ctx-full-txt", "Expanded generated agent context", "llmsCtxFullTxt", "text/plain"),
        ("faq-md", "FAQ question and answer corpus", "faqMd", "text/markdown"),
        ("recruiter-md", "Recruiter brief", "recruiterMd", "text/markdown"),
        ("proof-md", "Claim verification map", "proofMd", "text/markdown"),
        ("stack-md", "Full stack reference", "stackMd", "text/markdown"),
        ("profile-md", "Structured profile summary", "profileMd", "text/markdown"),
        ("readme-md", "Machine-readable mirror README", "readmeMd", "text/markdown"),
        ("how-to-cite-md", "Citation guide", "howToCiteMd", "text/markdown"),
        ("license-md", "Content license", "licenseMd", "text/markdown"),
        ("citation-cff", "Citation File Format metadata", "citationCff", "text/plain"),
        ("person-jsonld", "Schema.org Person graph", "schemaPerson", "application/ld+json"),
        ("faq-jsonld", "Schema.org FAQ graph", "schemaFaq", "application/ld+json"),
        ("schema-json", "llms-index JSON Schema contract", "schemaIndex", "application/schema+json"),
        ("humans-txt", "Humans and entity credits", "humansTxt", "text/plain"),
        ("sitemap-xml", "GitHub Pages sitemap", "sitemap", "application/xml"),
        ("robots-txt", "GitHub Pages robots hints", "robots", "text/plain"),
    ]
    downloads: list[dict[str, str]] = []
    for key, name, source_key, encoding in rows:
        item = {"key": key, "name": name, "url": pages[source_key], "encoding": encoding}
        if repo and repo.get(source_key):
            item["sourceUrl"] = repo[source_key]
        downloads.append(item)
    return downloads


def download_description(name: str, encoding: str) -> str:
    return f"Downloadable {name} file for the Mark Siazon profile index, encoded as {encoding}."


def data_catalog_name() -> str:
    return "Mark Siazon machine-readable profile catalog"


def data_catalog_description() -> str:
    return "Catalog of crawlable machine-readable profile, FAQ, proof, and schema files for Mark Siazon."


def build_person_graph(data: dict[str, Any]) -> dict[str, Any]:
    entity = data["entity"]
    ids = data["identifiers"]
    repo = data["machineReadable"]["repo"]
    pages = data["machineReadable"]["pages"]
    schema = data["schema"]
    person_id = entity["@id"]
    github_site_id = ids["githubProfileIndex"]
    profile_page_id = ids["githubProfilePage"]
    pages_site_id = ids["githubPagesMirror"]
    pages_page_id = f"{PAGES}/#webpage"
    pages_breadcrumb_id = f"{PAGES}/#breadcrumb"
    pages_catalog_id = f"{PAGES}/#data-catalog"
    pages_dataset_id = f"{PAGES}/#machine-readable-dataset"
    pages_image_id = f"{PAGES}/#primary-image"
    pages_main_content_id = f"{PAGES}/#main-content"
    pages_section_nav_id = pages_section_navigation_id()
    pages_topic_set_id = topic_term_set_id()
    portfolio_site_id = ids["portfolioWebsite"]
    contact_action_id = fragment_id(person_id, "contact-action")
    contact_entry_id = fragment_id(person_id, "contact-entrypoint")
    service_channel_id = fragment_id(person_id, "hiring-service-channel")
    faq_id = ids["faqDocument"]
    updated = data["updated"]
    availability = data.get("availability", {})
    area_served = availability.get("areaServed") or data.get("seo", {}).get("geoSignals", {}).get("serviceRegions", [])
    area_nodes = area_served_nodes(area_served)
    offer_ids = [fragment_id(person_id, f"offer-{slugify(focus)}") for focus in availability.get("focus", [])]
    service_ids = [fragment_id(person_id, f"service-{slugify(focus)}") for focus in availability.get("focus", [])]
    downloads = machine_downloads(pages, repo)
    mentioned_entities = (
        [
            ref(f"{GITHUB_BLOB}/llms-index.json#featured-projects"),
            ref(f"{GITHUB_BLOB}/llms-index.json#hackathon-lab"),
            ref(fragment_id(person_id, "services")),
        ]
        + [ref(service_id) for service_id in service_ids]
        + [ref(project_id(project)) for project in data.get("featuredProjects", [])]
        + [ref(lab_project_id(project)) for project in data.get("hackathonLab", []) if lab_project_url(project)]
    )

    topic_terms = topic_term_values(data)
    keywords = profile_keywords(data)
    snippets = data.get("aeo", {}).get("answerSnippets", [])
    sd_provenance = structured_data_provenance(data)
    usage_policy = content_usage_policy(data)
    image_rights_metadata = image_rights(data)
    citations = citation_targets(data)
    project_awards = awards_by_project(data)
    ownership = ownership_metadata(data)
    review = review_metadata(data)
    spatial = spatial_coverage(data)
    page_sections = pages_section_specs(data)
    page_section_relations = pages_section_relation_ids(data)
    page_section_refs = [ref(pages_section_id(section["fragment"])) for section in page_sections]
    page_section_nav_refs = [ref(pages_section_nav_item_id(section["fragment"])) for section in page_sections]

    graph: list[dict[str, Any]] = [
        {
            "@type": "Person",
            "@id": person_id,
            "name": entity["name"],
            "alternateName": entity.get("alternateName", []),
            "jobTitle": entity.get("jobTitle", []),
            "description": entity["description"],
            "disambiguatingDescription": profile_disambiguating_description(data),
            "identifier": person_identifiers(data),
            "url": entity["url"],
            "image": ref(pages_image_id),
            "email": person_email(data),
            "address": entity.get("address"),
            "sameAs": entity.get("sameAs", []),
            "knowsAbout": person_knows_about(data),
            "knowsLanguage": person_languages(),
            "award": [achievement["title"] for achievement in data.get("achievements", []) if achievement.get("title")],
            "contactPoint": [person_hiring_contact(data)],
            "hasOfferCatalog": ref(fragment_id(person_id, "services")),
            "makesOffer": [ref(offer_id) for offer_id in offer_ids],
            "hasOccupation": person_occupations(data),
            "workLocation": person_work_locations(data),
            "mainEntityOfPage": person_main_entity_pages(data),
            "potentialAction": ref(contact_action_id),
            "subjectOf": person_subjects(data),
        },
        {
            "@type": "OfferCatalog",
            "@id": fragment_id(person_id, "services"),
            "name": "Mark Siazon services and availability",
            "description": "Service catalog for Mark Siazon product design, full-stack engineering, AI workflow, mobile, and Web3 proof work.",
            "url": availability.get("recruiterBrief", entity["url"]),
            "identifier": {
                "@type": "PropertyValue",
                "propertyID": "Iron-Mark service catalog",
                "value": slugify("Mark Siazon services and availability"),
            },
            "mainEntityOfPage": availability.get("recruiterBrief", entity["url"]),
            "about": ref(person_id),
            "inLanguage": content_language(),
            "dateModified": updated,
            "isAccessibleForFree": True,
            "numberOfItems": len(offer_ids),
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "name": focus,
                    "item": ref(offer_id),
                }
                for index, (focus, offer_id) in enumerate(
                    zip(availability.get("focus", []), offer_ids, strict=False),
                    start=1,
                )
            ],
        },
        {
            "@type": "WebSite",
            "@id": portfolio_site_id,
            "name": "Mark Siazon Portfolio",
            "url": data["canonical"]["portfolio"],
            "author": ref(person_id),
            "publisher": ref(person_id),
            "inLanguage": "en",
            "about": ref(person_id),
            "description": "Proof-backed portfolio for product design, full-stack development, AI, mobile, and Web3 case studies.",
            "abstract": "Proof-backed portfolio for product design, full-stack development, AI, mobile, and Web3 case studies.",
            "keywords": keywords,
            "image": ref(pages_image_id),
            "spatialCoverage": spatial,
            "mentions": mentioned_entities,
            "potentialAction": ref(contact_action_id),
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "WebSite",
            "@id": github_site_id,
            "name": "Mark Siazon GitHub Profile Index",
            "url": data["canonical"]["githubProfileReadme"],
            "author": ref(person_id),
            "publisher": ref(person_id),
            "inLanguage": "en",
            "about": ref(person_id),
            "description": "GitHub profile README with machine-readable portfolio indexes, FAQ, Schema.org graphs, proof map, and tech stack reference.",
            "abstract": "GitHub profile README with machine-readable portfolio indexes, FAQ, Schema.org graphs, proof map, and tech stack reference.",
            "keywords": keywords,
            "image": ref(pages_image_id),
            "spatialCoverage": spatial,
            "mentions": mentioned_entities,
            "potentialAction": ref(contact_action_id),
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "ProfilePage",
            "@id": profile_page_id,
            "url": data["canonical"]["githubProfileReadme"],
            "name": "Mark Siazon GitHub profile README",
            "description": "Public GitHub profile README for Mark Siazon with proof-backed portfolio links and machine-readable discovery files.",
            "abstract": "Public GitHub profile README for Mark Siazon with proof-backed portfolio links and machine-readable discovery files.",
            "keywords": keywords,
            "inLanguage": "en",
            "author": ref(person_id),
            "publisher": ref(person_id),
            "mainEntity": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(github_site_id),
            "dateModified": updated,
            "primaryImageOfPage": ref(pages_image_id),
            "thumbnailUrl": PAGES_IMAGE,
            "spatialCoverage": spatial,
            "mentions": mentioned_entities,
            "hasPart": [ref(part_id) for part_id in profile_page_part_ids(data)],
            "significantLink": profile_significant_links(data),
            "relatedLink": profile_related_links(data),
            "potentialAction": ref(contact_action_id),
            **usage_policy,
            **review,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "WebSite",
            "@id": pages_site_id,
            "name": PAGES_SITE_NAME,
            "alternateName": PAGES_SITE_ALTERNATE_NAMES,
            "url": f"{PAGES}/",
            "author": ref(person_id),
            "publisher": ref(person_id),
            "inLanguage": "en",
            "about": ref(person_id),
            "description": "Static mirror of llms-index.json, FAQ.md, Schema.org JSON-LD, and related machine-readable profile files.",
            "abstract": "Static mirror of llms-index.json, FAQ.md, Schema.org JSON-LD, and related machine-readable profile files.",
            "keywords": keywords,
            "isBasedOn": data["canonical"]["githubProfileReadme"],
            "dateModified": updated,
            "image": ref(pages_image_id),
            "spatialCoverage": spatial,
            "mentions": mentioned_entities,
            "significantLink": pages_significant_links(data),
            "relatedLink": pages_related_links(data),
            "potentialAction": ref(contact_action_id),
            "hasPart": [
                ref(pages_page_id),
                ref(pages_catalog_id),
                ref(pages_dataset_id),
                ref(pages_main_content_id),
                ref(pages_section_nav_id),
                ref(pages_topic_set_id),
            ],
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "CollectionPage",
            "@id": pages_page_id,
            "url": pages["home"],
            "name": PAGES_SITE_NAME,
            "alternateName": PAGES_SITE_ALTERNATE_NAMES,
            "description": "Crawlable GitHub Pages mirror for Mark Siazon machine-readable profile indexes, FAQ, proof map, recruiter brief, and Schema.org JSON-LD.",
            "abstract": "Crawlable GitHub Pages mirror for Mark Siazon machine-readable profile indexes, FAQ, proof map, recruiter brief, and Schema.org JSON-LD.",
            "keywords": keywords,
            "isBasedOn": repo["llmsIndexJson"],
            "isPartOf": ref(pages_site_id),
            "about": ref(person_id),
            "mainEntity": ref(person_id),
            "author": ref(person_id),
            "publisher": ref(person_id),
            "breadcrumb": ref(pages_breadcrumb_id),
            "mainContentOfPage": ref(pages_main_content_id),
            "dateModified": updated,
            "inLanguage": "en",
            "primaryImageOfPage": ref(pages_image_id),
            "thumbnailUrl": PAGES_IMAGE,
            "spatialCoverage": spatial,
            "speakable": pages_speakable_spec(data),
            "mentions": mentioned_entities,
            "significantLink": pages_significant_links(data),
            "relatedLink": pages_related_links(data),
            "potentialAction": ref(contact_action_id),
            "citation": citations,
            **usage_policy,
            **review,
            **ownership,
            **sd_provenance,
            "hasPart": [
                ref(pages_catalog_id),
                ref(pages_dataset_id),
                ref(pages_main_content_id),
                ref(pages_section_nav_id),
                *page_section_refs,
                ref(pages["llmsIndexJson"]),
                ref(pages["llmsTxt"]),
                ref(pages["llmsCtxFullTxt"]),
                ref(pages["faqMd"]),
                ref(pages["recruiterMd"]),
                ref(pages["proofMd"]),
                ref(pages["stackMd"]),
                ref(pages["profileMd"]),
                ref(pages["readmeMd"]),
                ref(pages["howToCiteMd"]),
                ref(pages["licenseMd"]),
                ref(pages["citationCff"]),
                ref(pages["schemaPerson"]),
                ref(pages["schemaFaq"]),
                ref(pages["schemaIndex"]),
                ref(pages["humansTxt"]),
                ref(pages["sitemap"]),
                ref(pages["robots"]),
                ref(pages_topic_set_id),
            ],
        },
        {
            "@type": "ContactAction",
            "@id": contact_action_id,
            "name": contact_action_name(),
            "description": contact_action_description(),
            "target": ref(contact_entry_id),
            "recipient": ref(person_id),
            "about": ref(person_id),
            "object": ref(person_id),
        },
        {
            "@type": "WebPageElement",
            "@id": pages_main_content_id,
            "name": "Mark Siazon profile index main content",
            "url": f"{pages['home']}#main-content",
            "description": "Primary visible content for Mark Siazon profile facts, featured work, answer corpus, geo signals, knowledge graph, and citation links.",
            "abstract": "Primary visible content for Mark Siazon profile facts, featured work, answer corpus, geo signals, knowledge graph, and citation links.",
            "text": entity["description"],
            "about": ref(person_id),
            "isPartOf": ref(pages_page_id),
            "inLanguage": "en",
            "dateModified": updated,
            "isAccessibleForFree": True,
            "citation": citations,
            "hasPart": [ref(pages_section_nav_id), *page_section_refs],
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "SiteNavigationElement",
            "@id": pages_section_nav_id,
            "name": "Mark Siazon profile index section navigation",
            "url": f"{pages['home']}#section-navigation",
            "description": "Visible section navigation for the Mark Siazon profile index.",
            "abstract": "Visible section navigation for the Mark Siazon profile index.",
            "about": ref(person_id),
            "isPartOf": ref(pages_page_id),
            "inLanguage": "en",
            "dateModified": updated,
            "isAccessibleForFree": True,
            "citation": citations,
            "hasPart": page_section_nav_refs,
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "EntryPoint",
            "@id": contact_entry_id,
            "name": contact_entry_name(),
            "description": contact_entry_description(),
            "urlTemplate": availability.get("contact", entity["url"]),
            "contentType": contact_entry_content_type(),
            "httpMethod": contact_entry_http_method(),
            "inLanguage": content_language(),
            "actionPlatform": contact_action_platforms(),
        },
        {
            "@type": "ServiceChannel",
            "@id": service_channel_id,
            "name": service_channel_name(),
            "description": service_channel_description(),
            "serviceUrl": availability.get("contact", entity["url"]),
            "availableLanguage": available_languages(),
            "providesService": [ref(service_id) for service_id in service_ids],
            "about": ref(person_id),
            "dateModified": updated,
        },
        {
            "@type": "ImageObject",
            "@id": pages_image_id,
            "name": IMAGE_ALT,
            "caption": IMAGE_ALT,
            "description": primary_image_description(),
            "abstract": primary_image_description(),
            "url": PAGES_IMAGE,
            "contentUrl": PAGES_IMAGE,
            "encodingFormat": "image/png",
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
            **file_integrity_metadata(PAGES_IMAGE_ASSET),
            "inLanguage": "en",
            "dateModified": updated,
            **image_rights_metadata,
            "about": ref(person_id),
            "isPartOf": ref(pages_page_id),
            "representativeOfPage": True,
        },
        {
            "@type": "DataCatalog",
            "@id": pages_catalog_id,
            "name": data_catalog_name(),
            "url": pages["home"],
            "description": data_catalog_description(),
            "abstract": data_catalog_description(),
            "keywords": keywords,
            "isBasedOn": repo["llmsIndexJson"],
            "creator": ref(person_id),
            "publisher": ref(person_id),
            "about": ref(person_id),
            "dataset": ref(pages_dataset_id),
            "inLanguage": "en",
            "datePublished": DATASET_DATE_PUBLISHED,
            "dateModified": updated,
            "license": data.get("license"),
            "spatialCoverage": spatial,
            "temporalCoverage": dataset_temporal_coverage(data),
            "measurementTechnique": dataset_measurement_techniques(),
            "mentions": mentioned_entities,
            "isAccessibleForFree": True,
            "citation": citations,
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "Dataset",
            "@id": pages_dataset_id,
            "name": "Mark Siazon machine-readable profile dataset",
            "alternateName": dataset_alternate_names(data),
            "url": pages["llmsIndexJson"],
            "identifier": [
                {
                    "@type": "PropertyValue",
                    "propertyID": "GitHub repository",
                    "value": "Iron-Mark/Iron-Mark",
                },
                {
                    "@type": "PropertyValue",
                    "propertyID": "GitHub Pages dataset",
                    "value": pages_dataset_id,
                },
            ],
            "sameAs": repo["llmsIndexJson"],
            "isBasedOn": repo["llmsIndexJson"],
            "version": updated,
            "description": "Machine-readable entity, project, proof, FAQ, AEO, SEO, GEO, citation, and schema files mirrored on GitHub Pages.",
            "abstract": "Machine-readable entity, project, proof, FAQ, AEO, SEO, GEO, citation, and schema files mirrored on GitHub Pages.",
            "creator": ref(person_id),
            "publisher": ref(person_id),
            "inLanguage": "en",
            "datePublished": DATASET_DATE_PUBLISHED,
            "dateModified": updated,
            "license": data.get("license"),
            "keywords": keywords,
            "citation": citations,
            "spatialCoverage": spatial,
            "temporalCoverage": dataset_temporal_coverage(data),
            "measurementTechnique": dataset_measurement_techniques(),
            "variableMeasured": dataset_variable_measurements(data, area_served, downloads),
            "includedInDataCatalog": ref(pages_catalog_id),
            "mentions": mentioned_entities,
            "about": [ref(person_id), ref(pages_topic_set_id)],
            "isAccessibleForFree": True,
            "distribution": [ref(download_id(item["key"])) for item in downloads],
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "BreadcrumbList",
            "@id": pages_breadcrumb_id,
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Mark Siazon Portfolio",
                    "item": data["canonical"]["portfolio"],
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": PAGES_SITE_NAME,
                    "item": pages["home"],
                },
            ],
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "name": "Mark Siazon Frequently Asked Questions",
            "url": repo["faqMd"],
            "identifier": faq_document_identifier(faq_id),
            "description": "Question and answer corpus for Mark Siazon hiring, projects, stack, verification, geography, and citation.",
            "abstract": "Question and answer corpus for Mark Siazon hiring, projects, stack, verification, geography, and citation.",
            "keywords": keywords,
            "inLanguage": content_language(),
            "isBasedOn": repo["faqMd"],
            "dateModified": updated,
            "author": ref(person_id),
            "publisher": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(github_site_id),
            "isAccessibleForFree": True,
            "spatialCoverage": spatial,
            "citation": citations,
            "mainEntity": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
            "hasPart": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
            **usage_policy,
            **review,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "DefinedTermSet",
            "@id": pages_topic_set_id,
            "name": "Mark Siazon profile topic taxonomy",
            "description": "Controlled topic, service, and geography terms used by the Mark Siazon profile index.",
            "url": pages["home"],
            "inLanguage": "en",
            "dateModified": updated,
            "about": ref(person_id),
            "isPartOf": ref(pages_site_id),
            "hasDefinedTerm": [ref(topic_term_id(term)) for term in topic_terms],
            "isAccessibleForFree": True,
            "citation": citations,
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": ["ItemList", "CreativeWork"],
            "@id": f"{GITHUB_BLOB}/llms-index.json#featured-projects",
            "name": "Mark Siazon featured projects",
            "description": featured_projects_list_description(data),
            "abstract": featured_projects_list_description(data),
            "about": ref(person_id),
            "publisher": ref(person_id),
            "isPartOf": ref(f"{GITHUB_BLOB}/llms-index.json#creativework"),
            "inLanguage": "en",
            "dateModified": updated,
            "isAccessibleForFree": True,
            "citation": citations,
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "numberOfItems": len(data.get("featuredProjects", [])),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "url": project["caseStudy"],
                    "item": ref(project_id(project)),
                }
                for index, project in enumerate(data.get("featuredProjects", []), start=1)
            ],
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": ["ItemList", "CreativeWork"],
            "@id": f"{GITHUB_BLOB}/llms-index.json#hackathon-lab",
            "name": "Mark Siazon hackathon and lab projects",
            "description": lab_projects_list_description(data),
            "abstract": lab_projects_list_description(data),
            "about": ref(person_id),
            "publisher": ref(person_id),
            "isPartOf": ref(f"{GITHUB_BLOB}/llms-index.json#creativework"),
            "inLanguage": "en",
            "dateModified": updated,
            "isAccessibleForFree": True,
            "citation": citations,
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "numberOfItems": len(data.get("hackathonLab", [])),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "url": lab_project_url(project),
                    "item": ref(lab_project_id(project)),
                }
                for index, project in enumerate(data.get("hackathonLab", []), start=1)
                if lab_project_url(project)
            ],
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
    ]

    for position, section in enumerate(page_sections, start=1):
        description = section["description"]
        relations = page_section_relations.get(section["fragment"], {})
        graph.append(
            {
                "@type": "WebPageElement",
                "@id": pages_section_id(section["fragment"]),
                "name": section["name"],
                "url": f"{pages['home']}#{section['fragment']}",
                "description": description,
                "abstract": description,
                "text": section["text"],
                "about": ref(person_id),
                "isPartOf": ref(pages_page_id),
                "inLanguage": "en",
                "dateModified": updated,
                "isAccessibleForFree": True,
                "citation": citations,
                **(
                    {"hasPart": [ref(node_id) for node_id in relations["hasPart"]]}
                    if relations.get("hasPart")
                    else {}
                ),
                **(
                    {"mentions": [ref(node_id) for node_id in relations["mentions"]]}
                    if relations.get("mentions")
                    else {}
                ),
                **usage_policy,
                **ownership,
                **sd_provenance,
            }
        )
        graph.append(
            {
                "@type": "SiteNavigationElement",
                "@id": pages_section_nav_item_id(section["fragment"]),
                "name": section["heading"],
                "url": f"{pages['home']}#{section['fragment']}",
                "description": description,
                "abstract": description,
                "about": ref(pages_section_id(section["fragment"])),
                "isPartOf": ref(pages_section_nav_id),
                "position": position,
                "inLanguage": "en",
                "dateModified": updated,
                "isAccessibleForFree": True,
                **ownership,
            }
        )

    for term in topic_terms:
        graph.append(
            {
                "@type": "DefinedTerm",
                "@id": topic_term_id(term),
                "name": term,
                "termCode": slugify(term),
                "description": topic_term_description(data, term),
                "url": topic_term_id(term),
                "inDefinedTermSet": ref(pages_topic_set_id),
                "inLanguage": "en",
                "dateModified": updated,
                "about": ref(person_id),
            }
        )

    for focus, offer_id, service_id in zip(availability.get("focus", []), offer_ids, service_ids, strict=False):
        graph.extend(
            [
                {
                    "@type": "Offer",
                    "@id": offer_id,
                    "name": f"{focus} availability",
                    "category": focus,
                    "identifier": service_focus_identifier(focus, "offer"),
                    "description": offer_description(data, focus),
                    "url": availability.get("recruiterBrief", entity["url"]),
                    "mainEntityOfPage": availability.get("recruiterBrief", entity["url"]),
                    "availability": offer_availability(data),
                    "areaServed": area_nodes,
                    "eligibleRegion": area_nodes,
                    "businessFunction": PROVIDE_SERVICE_BUSINESS_FUNCTION,
                    "offeredBy": ref(person_id),
                    "seller": ref(person_id),
                    "itemOffered": ref(service_id),
                },
                {
                    "@type": "Service",
                    "@id": service_id,
                    "name": focus,
                    "serviceType": focus,
                    "identifier": service_focus_identifier(focus, "service"),
                    "description": service_description(data, focus),
                    "provider": ref(person_id),
                    "offers": ref(offer_id),
                    "url": availability.get("recruiterBrief", entity["url"]),
                    "mainEntityOfPage": availability.get("recruiterBrief", entity["url"]),
                    "availableChannel": ref(service_channel_id),
                    "areaServed": area_nodes,
                    "providerMobility": SERVICE_PROVIDER_MOBILITY,
                    "audience": service_audience(),
                    "serviceAudience": service_audience(),
                },
            ]
        )

    for item in downloads:
        graph.append(
            {
                "@type": "DataDownload",
                "@id": download_id(item["key"]),
                "name": item["name"],
                "url": item["url"],
                "contentUrl": item["url"],
                "encodingFormat": item["encoding"],
                "description": download_description(item["name"], item["encoding"]),
                "abstract": download_description(item["name"], item["encoding"]),
                **download_integrity_metadata(item["key"], data),
                "inLanguage": "en",
                "dateModified": updated,
                "license": data.get("license"),
                "isAccessibleForFree": True,
                "isPartOf": ref(pages_dataset_id),
                "about": ref(person_id),
                "publisher": ref(person_id),
                "citation": citations,
                **({"isBasedOn": item["sourceUrl"]} if item.get("sourceUrl") else {}),
                **usage_policy,
                **ownership,
                **sd_provenance,
            }
        )

    for project in data.get("featuredProjects", []):
        image = project_image_info(project)
        project_node = {
            "@type": "CreativeWork",
            "@id": project_id(project),
            "name": project["name"],
            "url": project["caseStudy"],
            "mainEntityOfPage": project["caseStudy"],
            "description": project.get("focus", ""),
            "abstract": project.get("focus", ""),
            "creator": ref(person_id),
            "author": ref(person_id),
            "publisher": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(portfolio_site_id),
            "inLanguage": "en",
            "dateModified": updated,
            "isAccessibleForFree": True,
            "sameAs": compact([project.get("live"), project.get("repo"), project.get("model")]),
            "keywords": compact([project.get("slug"), project.get("focus")]),
            "citation": citations,
            **usage_policy,
            **ownership,
            **sd_provenance,
        }
        awards = project_awards.get(project["name"], [])
        if awards:
            project_node["award"] = awards
        if image:
            project_node["image"] = ref(image["@id"])
            project_node["thumbnailUrl"] = image["url"]
        graph.append(project_node)
        if image:
            graph.append(
                {
                    "@type": "ImageObject",
                    "@id": image["@id"],
                    "name": f"{project['name']} project cover image",
                    "caption": f"{project['name']} project cover image",
                    "description": project_image_description(project),
                    "abstract": project_image_description(project),
                    "url": image["url"],
                    "contentUrl": image["url"],
                    "encodingFormat": image["encodingFormat"],
                    "contentSize": image["contentSize"],
                    "sha256": image["sha256"],
                    "inLanguage": "en",
                    "dateModified": updated,
                    **image_rights_metadata,
                    "about": ref(project_id(project)),
                    "isPartOf": ref(project_id(project)),
                }
            )

    for project in data.get("hackathonLab", []):
        url = lab_project_url(project)
        if not url:
            continue
        same_as = [
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
            if value != url
        ]
        graph.append(
            {
                "@type": "CreativeWork",
                "@id": lab_project_id(project),
                "name": project["name"],
                "url": url,
                "mainEntityOfPage": url,
                "description": project.get("focus", "Hackathon and lab project maintained by Mark Siazon."),
                "abstract": project.get("focus", "Hackathon and lab project maintained by Mark Siazon."),
                "creator": ref(person_id),
                "author": ref(person_id),
                "publisher": ref(person_id),
                "about": ref(person_id),
                "isPartOf": ref(portfolio_site_id if project.get("caseStudy") else github_site_id),
                "inLanguage": "en",
                "dateModified": updated,
                "isAccessibleForFree": True,
                "sameAs": same_as,
                "keywords": compact([slugify(project.get("name", "")), project.get("focus")]),
                "genre": "Hackathon and lab project",
                "citation": citations,
                **usage_policy,
                **ownership,
                **sd_provenance,
            }
        )

    graph.extend(
        [
            content_work(
                f"{GITHUB_BLOB}/llms-index.json#creativework",
                "llms-index.json structured entity index",
                repo["llmsIndexJson"],
                "application/json",
                "Structured entity, project, FAQ, SEO, AEO, GEO, and citation index for Mark Siazon.",
                person_id,
                updated,
                data.get("license"),
                sd_provenance,
                citations,
                usage_policy,
                ownership,
                spatial,
            ),
            content_work(
                f"{GITHUB_BLOB}/public/FAQ.md#creativework",
                "Mark Siazon FAQ",
                repo["faqMd"],
                "text/markdown",
                "Visible question and answer corpus for hiring, projects, verification, and citation.",
                person_id,
                updated,
                data.get("license"),
                sd_provenance,
                citations,
                usage_policy,
                ownership,
                spatial,
            ),
            content_work(
                f"{GITHUB_BLOB}/public/PROOF.md#creativework",
                "Mark Siazon proof map",
                repo["proofMd"],
                "text/markdown",
                "Claims mapped to public verification URLs and proof boundaries.",
                person_id,
                updated,
                data.get("license"),
                sd_provenance,
                citations,
                usage_policy,
                ownership,
                spatial,
            ),
            content_work(
                f"{GITHUB_BLOB}/public/RECRUITER.md#creativework",
                "Mark Siazon recruiter brief",
                repo["recruiterMd"],
                "text/markdown",
                "Recruiter-first role fit, verified achievements, stack summary, and contact paths.",
                person_id,
                updated,
                data.get("license"),
                sd_provenance,
                citations,
                usage_policy,
                ownership,
                spatial,
            ),
            content_work(
                f"{GITHUB_BLOB}/public/STACK.md#creativework",
                "Mark Siazon stack reference",
                repo["stackMd"],
                "text/markdown",
                "Full 113-tool stack reference grouped by domain.",
                person_id,
                updated,
                data.get("license"),
                sd_provenance,
                citations,
                usage_policy,
                ownership,
                spatial,
            ),
            content_work(
                f"{GITHUB_BLOB}/public/schema/llms-index.schema.json#creativework",
                "llms-index.json schema contract",
                repo["schemaIndex"],
                "application/schema+json",
                "JSON Schema contract for the structured entity, proof, SEO, AEO, GEO, and citation index.",
                person_id,
                updated,
                data.get("license"),
                sd_provenance,
                citations,
                usage_policy,
                ownership,
                spatial,
            ),
        ]
    )

    return {"@context": "https://schema.org", "@graph": graph}


def build_faq_graph(data: dict[str, Any]) -> dict[str, Any]:
    entity = data["entity"]
    ids = data["identifiers"]
    repo = data["machineReadable"]["repo"]
    faq_id = ids["faqDocument"]
    person_id = entity["@id"]
    snippets = data.get("aeo", {}).get("answerSnippets", [])
    sd_provenance = structured_data_provenance(data)
    usage_policy = content_usage_policy(data)
    citations = citation_targets(data)
    ownership = ownership_metadata(data)
    review = review_metadata(data)
    spatial = spatial_coverage(data)

    graph: list[dict[str, Any]] = [
        {
            "@type": "Person",
            "@id": person_id,
            "name": entity["name"],
            "description": entity["description"],
            "disambiguatingDescription": profile_disambiguating_description(data),
            "identifier": person_identifiers(data),
            "sameAs": entity.get("sameAs", []),
            "image": ref(f"{PAGES}/#primary-image"),
            "knowsLanguage": person_languages(),
            "url": entity["url"],
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "name": "Mark Siazon Frequently Asked Questions",
            "url": repo["faqMd"],
            "identifier": faq_document_identifier(faq_id),
            "description": "Question and answer corpus for Mark Siazon hiring, projects, stack, verification, geography, and citation.",
            "abstract": "Question and answer corpus for Mark Siazon hiring, projects, stack, verification, geography, and citation.",
            "keywords": profile_keywords(data),
            "isBasedOn": repo["faqMd"],
            "dateModified": data["updated"],
            "author": ref(person_id),
            "publisher": ref(person_id),
            "about": ref(person_id),
            "inLanguage": content_language(),
            "isAccessibleForFree": True,
            "spatialCoverage": spatial,
            "citation": citations,
            "mainEntity": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
            "hasPart": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
            **usage_policy,
            **review,
            **ownership,
            **sd_provenance,
        },
    ]

    for item in snippets:
        question_id = faq_question_id(faq_id, item["question"])
        answer_id = f"{question_id}-answer"
        graph.append(
            {
                "@type": "Question",
                "@id": question_id,
                "name": item["question"],
                "url": question_id,
                "identifier": faq_item_identifier(question_id, "question"),
                "author": ref(person_id),
                "publisher": ref(person_id),
                "about": ref(person_id),
                "isPartOf": ref(faq_id),
                "parentItem": ref(faq_id),
                "answerCount": 1,
                "inLanguage": content_language(),
                "dateModified": data["updated"],
                "isAccessibleForFree": True,
                "citation": item.get("sources", []),
                **usage_policy,
                **sd_provenance,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "@id": answer_id,
                    "url": answer_id,
                    "identifier": faq_item_identifier(answer_id, "answer"),
                    "text": item["answer"],
                    "author": ref(person_id),
                    "publisher": ref(person_id),
                    "about": ref(person_id),
                    "isPartOf": ref(faq_id),
                    "parentItem": ref(question_id),
                    "inLanguage": content_language(),
                    "dateModified": data["updated"],
                    "isAccessibleForFree": True,
                    **usage_policy,
                    "citation": item.get("sources", []),
                    **sd_provenance,
                },
            }
        )

    return {"@context": "https://schema.org", "@graph": graph}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}")


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    SCHEMA.mkdir(parents=True, exist_ok=True)
    write_json(SCHEMA / "person.jsonld", build_person_graph(data))
    write_json(SCHEMA / "faq.jsonld", build_faq_graph(data))


if __name__ == "__main__":
    main()
