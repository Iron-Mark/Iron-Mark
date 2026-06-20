#!/usr/bin/env python3
"""Generate Schema.org JSON-LD graphs from llms-index.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "public"
SCHEMA = PUBLIC / "schema"
INDEX = ROOT / "llms-index.json"

GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
PAGES = "https://iron-mark.github.io/Iron-Mark"
PAGES_SITE_NAME = "Mark Siazon Profile Index"
PAGES_SITE_ALTERNATE_NAMES = ["Iron-Mark Profile Index", "Mark Siazon GitHub Profile Index"]
PAGES_IMAGE = f"{PAGES}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.webp"
IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
IMAGE_WIDTH = 400
IMAGE_HEIGHT = 225
PROFILE_LANGUAGE = {"@type": "Language", "name": "English", "alternateName": "en"}


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


def project_id(project: dict[str, Any]) -> str:
    return f"{project['caseStudy']}#project"


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
) -> dict[str, Any]:
    return {
        "@type": "CreativeWork",
        "@id": node_id,
        "name": name,
        "url": url,
        "encodingFormat": encoding,
        "description": description,
        "author": ref(person_id),
        "about": ref(person_id),
        "inLanguage": "en",
        "dateModified": date_modified,
        "license": license_url,
        "isAccessibleForFree": True,
    }


def download_id(key: str) -> str:
    return f"{PAGES}/#download-{slugify(key)}"


def machine_downloads(pages: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"key": "llms-index-json", "name": "Structured entity index", "url": pages["llmsIndexJson"], "encoding": "application/json"},
        {"key": "llms-txt", "name": "LLM manifest", "url": pages["llmsTxt"], "encoding": "text/plain"},
        {"key": "llms-full-txt", "name": "Full LLM context", "url": pages["llmsFullTxt"], "encoding": "text/plain"},
        {"key": "llms-ctx-full-txt", "name": "Expanded generated agent context", "url": pages["llmsCtxFullTxt"], "encoding": "text/plain"},
        {"key": "faq-md", "name": "FAQ question and answer corpus", "url": pages["faqMd"], "encoding": "text/markdown"},
        {"key": "recruiter-md", "name": "Recruiter brief", "url": pages["recruiterMd"], "encoding": "text/markdown"},
        {"key": "proof-md", "name": "Claim verification map", "url": pages["proofMd"], "encoding": "text/markdown"},
        {"key": "stack-md", "name": "Full stack reference", "url": pages["stackMd"], "encoding": "text/markdown"},
        {"key": "profile-md", "name": "Structured profile summary", "url": pages["profileMd"], "encoding": "text/markdown"},
        {"key": "readme-md", "name": "Machine-readable mirror README", "url": pages["readmeMd"], "encoding": "text/markdown"},
        {"key": "how-to-cite-md", "name": "Citation guide", "url": pages["howToCiteMd"], "encoding": "text/markdown"},
        {"key": "license-md", "name": "Content license", "url": pages["licenseMd"], "encoding": "text/markdown"},
        {"key": "citation-cff", "name": "Citation File Format metadata", "url": pages["citationCff"], "encoding": "text/plain"},
        {"key": "person-jsonld", "name": "Schema.org Person graph", "url": pages["schemaPerson"], "encoding": "application/ld+json"},
        {"key": "faq-jsonld", "name": "Schema.org FAQ graph", "url": pages["schemaFaq"], "encoding": "application/ld+json"},
        {"key": "schema-json", "name": "llms-index JSON Schema contract", "url": pages["schemaIndex"], "encoding": "application/schema+json"},
        {"key": "humans-txt", "name": "Humans and entity credits", "url": pages["humansTxt"], "encoding": "text/plain"},
        {"key": "sitemap-xml", "name": "GitHub Pages sitemap", "url": pages["sitemap"], "encoding": "application/xml"},
        {"key": "robots-txt", "name": "GitHub Pages robots hints", "url": pages["robots"], "encoding": "text/plain"},
    ]


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
    portfolio_site_id = ids["portfolioWebsite"]
    contact_action_id = fragment_id(person_id, "contact-action")
    contact_entry_id = fragment_id(person_id, "contact-entrypoint")
    faq_id = ids["faqDocument"]
    updated = data["updated"]
    availability = data.get("availability", {})
    area_served = availability.get("areaServed") or data.get("seo", {}).get("geoSignals", {}).get("serviceRegions", [])
    area_nodes = area_served_nodes(area_served)
    offer_ids = [fragment_id(person_id, f"offer-{slugify(focus)}") for focus in availability.get("focus", [])]
    downloads = machine_downloads(pages)

    knows_about = data.get("coreStack", []) + data.get("seo", {}).get("primaryKeywords", [])
    dataset_keywords = unique_compact(
        data.get("seo", {}).get("primaryKeywords", [])
        + data.get("seo", {}).get("geoTargets", [])
        + area_served
    )
    snippets = data.get("aeo", {}).get("answerSnippets", [])

    graph: list[dict[str, Any]] = [
        {
            "@type": "Person",
            "@id": person_id,
            "name": entity["name"],
            "alternateName": entity.get("alternateName", []),
            "jobTitle": entity.get("jobTitle", []),
            "description": entity["description"],
            "url": entity["url"],
            "image": ref(pages_image_id),
            "email": f"mailto:{entity['email']}" if not entity["email"].startswith("mailto:") else entity["email"],
            "address": entity.get("address"),
            "sameAs": entity.get("sameAs", []),
            "knowsAbout": knows_about,
            "knowsLanguage": [PROFILE_LANGUAGE],
            "award": [achievement["title"] for achievement in data.get("achievements", []) if achievement.get("title")],
            "contactPoint": [
                {
                    "@type": "ContactPoint",
                    "@id": fragment_id(person_id, "hiring-contact"),
                    "contactType": "hiring",
                    "email": f"mailto:{entity['email']}" if not entity["email"].startswith("mailto:") else entity["email"],
                    "url": availability.get("contact", entity["url"]),
                    "areaServed": area_nodes,
                    "availableLanguage": ["en"],
                }
            ],
            "makesOffer": [ref(offer_id) for offer_id in offer_ids],
            "hasOccupation": [
                {
                    "@type": "Occupation",
                    "name": title,
                    "occupationLocation": {
                        "@type": "Country",
                        "name": "Philippines",
                    },
                }
                for title in entity.get("jobTitle", [])
            ],
            "workLocation": [
                {"@type": "Country", "name": "Philippines"},
                {"@type": "AdministrativeArea", "name": "Southeast Asia"},
                {"@type": "VirtualLocation", "name": "Remote global"},
            ],
            "mainEntityOfPage": [ref(profile_page_id), ref(portfolio_site_id)],
            "potentialAction": ref(contact_action_id),
            "subjectOf": [
                ref(f"{GITHUB_BLOB}/llms-index.json#creativework"),
                ref(f"{GITHUB_BLOB}/public/FAQ.md#creativework"),
                ref(f"{GITHUB_BLOB}/public/PROOF.md#creativework"),
                ref(f"{GITHUB_BLOB}/public/RECRUITER.md#creativework"),
                ref(f"{GITHUB_BLOB}/public/schema/llms-index.schema.json#creativework"),
                ref(schema["person"]),
                ref(schema["faq"]),
                ref(schema["index"]),
            ],
        },
        {
            "@type": "OfferCatalog",
            "@id": fragment_id(person_id, "services"),
            "name": "Mark Siazon services and availability",
            "url": availability.get("recruiterBrief", entity["url"]),
            "itemListElement": [ref(offer_id) for offer_id in offer_ids],
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
            "image": ref(pages_image_id),
            "potentialAction": ref(contact_action_id),
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
            "image": ref(pages_image_id),
            "potentialAction": ref(contact_action_id),
        },
        {
            "@type": "ProfilePage",
            "@id": profile_page_id,
            "url": data["canonical"]["githubProfileReadme"],
            "name": "Mark Siazon GitHub profile README",
            "mainEntity": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(github_site_id),
            "dateModified": updated,
            "primaryImageOfPage": ref(pages_image_id),
            "thumbnailUrl": PAGES_IMAGE,
            "potentialAction": ref(contact_action_id),
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
            "image": ref(pages_image_id),
            "potentialAction": ref(contact_action_id),
        },
        {
            "@type": "CollectionPage",
            "@id": pages_page_id,
            "url": pages["home"],
            "name": PAGES_SITE_NAME,
            "alternateName": PAGES_SITE_ALTERNATE_NAMES,
            "description": "Crawlable GitHub Pages mirror for Mark Siazon machine-readable profile indexes, FAQ, proof map, recruiter brief, and Schema.org JSON-LD.",
            "isPartOf": ref(pages_site_id),
            "about": ref(person_id),
            "mainEntity": ref(person_id),
            "breadcrumb": ref(pages_breadcrumb_id),
            "dateModified": updated,
            "inLanguage": "en",
            "primaryImageOfPage": ref(pages_image_id),
            "thumbnailUrl": PAGES_IMAGE,
            "potentialAction": ref(contact_action_id),
            "hasPart": [
                ref(pages_catalog_id),
                ref(pages_dataset_id),
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
            ],
        },
        {
            "@type": "ContactAction",
            "@id": contact_action_id,
            "name": "Contact Mark Siazon for hiring",
            "description": "Contact path for product design, full-stack engineering, AI workflow, mobile, and Web3 proof work.",
            "target": ref(contact_entry_id),
            "recipient": ref(person_id),
            "about": ref(person_id),
            "object": ref(person_id),
        },
        {
            "@type": "EntryPoint",
            "@id": contact_entry_id,
            "urlTemplate": availability.get("contact", entity["url"]),
            "inLanguage": "en",
            "actionPlatform": [
                "https://schema.org/DesktopWebPlatform",
                "https://schema.org/MobileWebPlatform",
            ],
        },
        {
            "@type": "ImageObject",
            "@id": pages_image_id,
            "name": IMAGE_ALT,
            "caption": IMAGE_ALT,
            "url": PAGES_IMAGE,
            "contentUrl": PAGES_IMAGE,
            "encodingFormat": "image/webp",
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
            "inLanguage": "en",
            "dateModified": updated,
            "creator": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(pages_page_id),
            "representativeOfPage": True,
        },
        {
            "@type": "DataCatalog",
            "@id": pages_catalog_id,
            "name": "Mark Siazon machine-readable profile catalog",
            "url": pages["home"],
            "description": "Catalog of crawlable machine-readable profile, FAQ, proof, and schema files for Mark Siazon.",
            "publisher": ref(person_id),
            "about": ref(person_id),
            "dataset": ref(pages_dataset_id),
            "inLanguage": "en",
            "dateModified": updated,
        },
        {
            "@type": "Dataset",
            "@id": pages_dataset_id,
            "name": "Mark Siazon machine-readable profile dataset",
            "url": pages["llmsIndexJson"],
            "description": "Machine-readable entity, project, proof, FAQ, AEO, SEO, GEO, citation, and schema files mirrored on GitHub Pages.",
            "creator": ref(person_id),
            "publisher": ref(person_id),
            "about": ref(person_id),
            "inLanguage": "en",
            "dateModified": updated,
            "license": data.get("license"),
            "keywords": dataset_keywords,
            "includedInDataCatalog": ref(pages_catalog_id),
            "isAccessibleForFree": True,
            "distribution": [ref(download_id(item["key"])) for item in downloads],
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
                    "name": "GitHub Profile Index",
                    "item": pages["home"],
                },
            ],
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "name": "Mark Siazon Frequently Asked Questions",
            "url": repo["faqMd"],
            "dateModified": updated,
            "author": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(github_site_id),
            "mainEntity": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
        },
        {
            "@type": "ItemList",
            "@id": f"{GITHUB_BLOB}/llms-index.json#featured-projects",
            "name": "Mark Siazon featured projects",
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "numberOfItems": len(data.get("featuredProjects", [])),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "item": ref(project_id(project)),
                }
                for index, project in enumerate(data.get("featuredProjects", []), start=1)
            ],
        },
    ]

    for focus, offer_id in zip(availability.get("focus", []), offer_ids, strict=False):
        service_id = fragment_id(person_id, f"service-{slugify(focus)}")
        graph.extend(
            [
                {
                    "@type": "Offer",
                    "@id": offer_id,
                    "name": f"{focus} availability",
                    "category": focus,
                    "url": availability.get("recruiterBrief", entity["url"]),
                    "availability": "https://schema.org/InStock" if availability.get("status") == "open" else "https://schema.org/LimitedAvailability",
                    "areaServed": area_nodes,
                    "offeredBy": ref(person_id),
                    "itemOffered": ref(service_id),
                },
                {
                    "@type": "Service",
                    "@id": service_id,
                    "name": focus,
                    "serviceType": focus,
                    "provider": ref(person_id),
                    "url": availability.get("recruiterBrief", entity["url"]),
                    "areaServed": area_nodes,
                    "audience": {
                        "@type": "Audience",
                        "audienceType": "recruiters, founders, product teams, and engineering teams",
                    },
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
                "dateModified": updated,
                "license": data.get("license"),
                "isAccessibleForFree": True,
                "isPartOf": ref(pages_dataset_id),
                "about": ref(person_id),
            }
        )

    for project in data.get("featuredProjects", []):
        graph.append(
            {
                "@type": "CreativeWork",
                "@id": project_id(project),
                "name": project["name"],
                "url": project["caseStudy"],
                "description": project.get("focus", ""),
                "creator": ref(person_id),
                "author": ref(person_id),
                "about": ref(person_id),
                "isPartOf": ref(portfolio_site_id),
                "inLanguage": "en",
                "dateModified": updated,
                "isAccessibleForFree": True,
                "sameAs": compact([project.get("live"), project.get("repo"), project.get("model")]),
                "keywords": compact([project.get("slug"), project.get("focus")]),
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

    graph: list[dict[str, Any]] = [
        {
            "@type": "Person",
            "@id": person_id,
            "name": entity["name"],
            "url": entity["url"],
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "name": "Mark Siazon Frequently Asked Questions",
            "url": repo["faqMd"],
            "dateModified": data["updated"],
            "author": ref(person_id),
            "about": ref(person_id),
            "inLanguage": "en",
            "mainEntity": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
        },
    ]

    for item in snippets:
        question_id = faq_question_id(faq_id, item["question"])
        graph.append(
            {
                "@type": "Question",
                "@id": question_id,
                "name": item["question"],
                "url": question_id,
                "about": ref(person_id),
                "inLanguage": "en",
                "dateModified": data["updated"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "@id": f"{question_id}-answer",
                    "text": item["answer"],
                    "author": ref(person_id),
                    "about": ref(person_id),
                    "inLanguage": "en",
                    "dateModified": data["updated"],
                    "citation": item.get("sources", []),
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
