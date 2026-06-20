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
PROJECT_IMAGE_EXTENSIONS = (
    (".webp", "image/webp"),
    (".png", "image/png"),
    (".svg", "image/svg+xml"),
)


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


def lab_project_url(project: dict[str, Any]) -> str:
    return str(project.get("caseStudy") or project.get("demo") or project.get("live") or project.get("repo") or "")


def lab_project_id(project: dict[str, Any]) -> str:
    return f"{lab_project_url(project)}#project"


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
            }
    return None


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


def spatial_coverage(data: dict[str, Any]) -> list[str]:
    return list(data.get("availability", {}).get("areaServed", []))


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
    spatial: list[str] | None = None,
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
        "citation": citations or [],
        **({"spatialCoverage": spatial} if spatial else {}),
        **(usage_policy or {}),
        **(ownership or {}),
        **(sd_provenance or {}),
    }


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

    knows_about = data.get("coreStack", []) + data.get("seo", {}).get("primaryKeywords", [])
    dataset_keywords = unique_compact(
        data.get("seo", {}).get("primaryKeywords", [])
        + data.get("seo", {}).get("geoTargets", [])
        + area_served
    )
    snippets = data.get("aeo", {}).get("answerSnippets", [])
    sd_provenance = structured_data_provenance(data)
    usage_policy = content_usage_policy(data)
    image_rights_metadata = image_rights(data)
    citations = citation_targets(data)
    project_awards = awards_by_project(data)
    ownership = ownership_metadata(data)
    review = review_metadata(data)
    spatial = spatial_coverage(data)

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
            "mainEntityOfPage": [ref(profile_page_id), ref(portfolio_site_id), ref(pages_page_id)],
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
            "mainEntity": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(github_site_id),
            "dateModified": updated,
            "primaryImageOfPage": ref(pages_image_id),
            "thumbnailUrl": PAGES_IMAGE,
            "spatialCoverage": spatial,
            "mentions": mentioned_entities,
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
            "isBasedOn": data["canonical"]["githubProfileReadme"],
            "dateModified": updated,
            "image": ref(pages_image_id),
            "spatialCoverage": spatial,
            "mentions": mentioned_entities,
            "potentialAction": ref(contact_action_id),
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
            "isBasedOn": repo["llmsIndexJson"],
            "isPartOf": ref(pages_site_id),
            "about": ref(person_id),
            "mainEntity": ref(person_id),
            "breadcrumb": ref(pages_breadcrumb_id),
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
            **image_rights_metadata,
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
            "isBasedOn": repo["llmsIndexJson"],
            "publisher": ref(person_id),
            "about": ref(person_id),
            "dataset": ref(pages_dataset_id),
            "inLanguage": "en",
            "dateModified": updated,
            "spatialCoverage": spatial,
            "mentions": mentioned_entities,
            "citation": citations,
            **usage_policy,
            **ownership,
            **sd_provenance,
        },
        {
            "@type": "Dataset",
            "@id": pages_dataset_id,
            "name": "Mark Siazon machine-readable profile dataset",
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
            "creator": ref(person_id),
            "publisher": ref(person_id),
            "about": ref(person_id),
            "inLanguage": "en",
            "dateModified": updated,
            "license": data.get("license"),
            "keywords": dataset_keywords,
            "citation": citations,
            "spatialCoverage": area_served,
            "variableMeasured": dataset_variable_measurements(data, area_served, downloads),
            "includedInDataCatalog": ref(pages_catalog_id),
            "mentions": mentioned_entities,
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
            "isBasedOn": repo["faqMd"],
            "dateModified": updated,
            "author": ref(person_id),
            "about": ref(person_id),
            "isPartOf": ref(github_site_id),
            "spatialCoverage": spatial,
            "citation": citations,
            "mainEntity": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
            **usage_policy,
            **review,
            **ownership,
            **sd_provenance,
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
            **ownership,
        },
        {
            "@type": "ItemList",
            "@id": f"{GITHUB_BLOB}/llms-index.json#hackathon-lab",
            "name": "Mark Siazon hackathon and lab projects",
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "numberOfItems": len(data.get("hackathonLab", [])),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "item": ref(lab_project_id(project)),
                }
                for index, project in enumerate(data.get("hackathonLab", []), start=1)
                if lab_project_url(project)
            ],
            **ownership,
        },
    ]

    for focus, offer_id, service_id in zip(availability.get("focus", []), offer_ids, service_ids, strict=False):
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
            "creator": ref(person_id),
            "author": ref(person_id),
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
                    "url": image["url"],
                    "contentUrl": image["url"],
                    "encodingFormat": image["encodingFormat"],
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
                "creator": ref(person_id),
                "author": ref(person_id),
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
            "url": entity["url"],
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "name": "Mark Siazon Frequently Asked Questions",
            "url": repo["faqMd"],
            "isBasedOn": repo["faqMd"],
            "dateModified": data["updated"],
            "author": ref(person_id),
            "about": ref(person_id),
            "inLanguage": "en",
            "spatialCoverage": spatial,
            "citation": citations,
            "mainEntity": [ref(faq_question_id(faq_id, item["question"])) for item in snippets],
            **usage_policy,
            **review,
            **ownership,
            **sd_provenance,
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
                **sd_provenance,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "@id": f"{question_id}-answer",
                    "text": item["answer"],
                    "author": ref(person_id),
                    "about": ref(person_id),
                    "inLanguage": "en",
                    "dateModified": data["updated"],
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
