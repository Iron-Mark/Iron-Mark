#!/usr/bin/env python3
"""Build and validate the GitHub Pages mirror artifact in a temp directory."""

from __future__ import annotations

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
    download_id,
    lab_project_id,
    lab_project_url,
    machine_downloads,
    slugify,
    unique_compact,
)

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
PUBLIC = ROOT / "public"
PAGES_BASE = "https://iron-mark.github.io/Iron-Mark"
GITHUB_BLOB = "https://github.com/Iron-Mark/Iron-Mark/blob/main"
PAGES_HOST = "iron-mark.github.io"
PAGES_SITE_NAME = "Mark Siazon Profile Index"
PAGES_SITE_ALTERNATE_NAMES = {"Iron-Mark Profile Index", "Mark Siazon GitHub Profile Index"}
PAGES_SOCIAL_IMAGE = f"{PAGES_BASE}/assets/brand/mark-siazon-product-design-full-stack-profile-banner.webp"
SOCIAL_IMAGE_ALT = "Mark Siazon product design and full-stack development profile banner"
SOCIAL_IMAGE_WIDTH = 400
SOCIAL_IMAGE_HEIGHT = 225
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


def pages_rewrite_public_source(source: str) -> str:
    replacements = (
        (f"{GITHUB_BLOB}/public/schema/", f"{PAGES_BASE}/schema/"),
        (f"{GITHUB_BLOB}/public/", f"{PAGES_BASE}/"),
    )
    for prefix, replacement in replacements:
        if source.startswith(prefix):
            return source.replace(prefix, replacement, 1)
    return source


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
    check_ownership_metadata(issues, node, index_data, label)
    check_structured_data_provenance(issues, node, index_data, label)


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
    primary_image = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#primary-image"), None)
    if not primary_image or "ImageObject" not in node_type_set(primary_image):
        issues.append("Pages index inline JSON-LD missing primary ImageObject node")
    else:
        check_image_rights(issues, primary_image, index_data, "Pages index primary ImageObject")
    if '"@type": "ContactAction"' not in index_text:
        issues.append("Pages index inline JSON-LD missing hiring ContactAction")
    if '"@type": "EntryPoint"' not in index_text:
        issues.append("Pages index inline JSON-LD missing hiring ContactAction EntryPoint")
    if "https://www.marksiazon.dev/contact" not in "\n".join(jsonld_scripts):
        issues.append("Pages index inline JSON-LD missing contact URL")
    if "Knowledge Graph" not in index_text:
        issues.append("Pages index missing visible Knowledge Graph section")
    for selector in expected_pages_speakable_selectors(index_data):
        if selector.startswith("#") and f'id="{selector[1:]}"' not in index_text:
            issues.append(f"Pages index missing speakable selector target: {selector}")
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
        if tag not in index_text:
            issues.append(f"Pages index missing social image metadata: {tag}")
    if f'<meta property="og:locale" content="{OPEN_GRAPH_LOCALE}"/>' not in index_text:
        issues.append("Pages index missing Open Graph locale metadata")
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
    profile_page = next((node for node in parsed_jsonld_nodes if node.get("@id") == "https://github.com/Iron-Mark/Iron-Mark#profilepage"), None)
    if not profile_page or "ProfilePage" not in node_type_set(profile_page):
        issues.append("Pages index inline JSON-LD missing GitHub ProfilePage")
    else:
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
        check_review_metadata(issues, pages_page, index_data, "Pages index CollectionPage")
        check_content_usage_policy(issues, pages_page, "Pages index CollectionPage")
        check_global_citation(issues, pages_page, index_data, "Pages index CollectionPage")
        check_ownership_metadata(issues, pages_page, index_data, "Pages index CollectionPage")
        check_spatial_coverage(issues, pages_page, index_data, "Pages index CollectionPage")
        check_structured_data_provenance(issues, pages_page, index_data, "Pages index CollectionPage")
        check_expected_mentions(issues, pages_page, index_data, "Pages index CollectionPage")
    data_catalog = next((node for node in parsed_jsonld_nodes if node.get("@id") == f"{PAGES_BASE}/#data-catalog"), None)
    if not data_catalog or "DataCatalog" not in node_type_set(data_catalog):
        issues.append("Pages index inline JSON-LD missing DataCatalog")
    else:
        if data_catalog.get("isBasedOn") != expected_based_on:
            issues.append("Pages index DataCatalog isBasedOn drift")
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
        if dataset.get("variableMeasured") != expected_dataset_measurements(index_data):
            issues.append("Pages index inline Dataset variableMeasured drift")
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
        check_content_usage_policy(issues, faq_page, "Pages index FAQPage")
        check_global_citation(issues, faq_page, index_data, "Pages index FAQPage")
        check_review_metadata(issues, faq_page, index_data, "Pages index FAQPage")
        check_ownership_metadata(issues, faq_page, index_data, "Pages index FAQPage")
        check_spatial_coverage(issues, faq_page, index_data, "Pages index FAQPage")
        check_structured_data_provenance(issues, faq_page, index_data, "Pages index FAQPage")
    for node in parsed_jsonld_nodes:
        node_types = node_type_set(node)
        if "Question" in node_types:
            check_structured_data_provenance(issues, node, index_data, f"Pages index Question {node.get('name')}")
            answer = node.get("acceptedAnswer", {})
            if isinstance(answer, dict):
                check_structured_data_provenance(issues, answer, index_data, f"Pages index Answer {node.get('name')}")
    jsonld_node_by_id = {str(node.get("@id", "")): node for node in parsed_jsonld_nodes}
    featured_list = jsonld_node_by_id.get(f"{GITHUB_BLOB}/llms-index.json#featured-projects")
    if not featured_list or "ItemList" not in node_type_set(featured_list):
        issues.append("Pages index inline JSON-LD missing featured projects ItemList")
    else:
        featured_projects = index_data.get("featuredProjects", [])
        if not isinstance(featured_projects, list):
            featured_projects = []
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
        check_ownership_metadata(issues, featured_list, index_data, "Pages index featured projects ItemList")
    lab_list = jsonld_node_by_id.get(f"{GITHUB_BLOB}/llms-index.json#hackathon-lab")
    if not lab_list or "ItemList" not in node_type_set(lab_list):
        issues.append("Pages index inline JSON-LD missing hackathon and lab ItemList")
    else:
        lab_projects = index_data.get("hackathonLab", [])
        if not isinstance(lab_projects, list):
            lab_projects = []
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
        check_ownership_metadata(issues, lab_list, index_data, "Pages index hackathon and lab ItemList")
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
            check_content_usage_policy(issues, download, f"Pages index DataDownload {item['key']}")
            check_global_citation(issues, download, index_data, f"Pages index DataDownload {item['key']}")
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
