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

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
PUBLIC = ROOT / "public"
PAGES_BASE = "https://iron-mark.github.io/Iron-Mark"
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
    if "https://iron-mark.github.io/Iron-Mark/FAQ.md#faq" not in "\n".join(jsonld_scripts):
        issues.append("Pages index inline FAQ JSON-LD must use the Pages FAQ identifier")
    if '"@type": "ImageObject"' not in index_text:
        issues.append("Pages index inline JSON-LD missing ImageObject")
    if '"primaryImageOfPage"' not in index_text:
        issues.append("Pages index inline JSON-LD missing primaryImageOfPage")
    if PAGES_SOCIAL_IMAGE not in "\n".join(jsonld_scripts):
        issues.append("Pages index inline JSON-LD missing Pages social image URL")
    if '"@type": "ContactAction"' not in index_text:
        issues.append("Pages index inline JSON-LD missing hiring ContactAction")
    if '"@type": "EntryPoint"' not in index_text:
        issues.append("Pages index inline JSON-LD missing hiring ContactAction EntryPoint")
    if "https://www.marksiazon.dev/contact" not in "\n".join(jsonld_scripts):
        issues.append("Pages index inline JSON-LD missing contact URL")
    if "Knowledge Graph" not in index_text:
        issues.append("Pages index missing visible Knowledge Graph section")
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
        missing_alternates = sorted(PAGES_SITE_ALTERNATE_NAMES - set(pages_site.get("alternateName", [])))
        if missing_alternates:
            issues.append(f"Pages index inline JSON-LD WebSite alternateName missing: {missing_alternates}")
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
    jsonld_node_by_id = {str(node.get("@id", "")): node for node in parsed_jsonld_nodes}
    for project in index_data.get("featuredProjects", []):
        if not isinstance(project, dict):
            continue
        expected_project_id = f"{project.get('caseStudy')}#project"
        project_node = jsonld_node_by_id.get(expected_project_id)
        if not project_node or "CreativeWork" not in node_type_set(project_node):
            issues.append(f"Pages index inline JSON-LD missing featured project CreativeWork: {project.get('name')}")
            continue
        expected_image = expected_project_image(project)
        if not expected_image:
            issues.append(f"Pages index cannot resolve featured project cover image: {project.get('name')}")
            continue
        if project_node.get("image", {}).get("@id") != expected_image["@id"]:
            issues.append(f"Pages index featured project image ref drift: {project.get('name')}")
        if project_node.get("thumbnailUrl") != expected_image["url"]:
            issues.append(f"Pages index featured project thumbnailUrl drift: {project.get('name')}")
        image_node = jsonld_node_by_id.get(expected_image["@id"])
        if not image_node or "ImageObject" not in node_type_set(image_node):
            issues.append(f"Pages index inline JSON-LD missing featured project ImageObject: {project.get('name')}")
            continue
        if image_node.get("contentUrl") != expected_image["url"]:
            issues.append(f"Pages index featured project image contentUrl drift: {project.get('name')}")
        if image_node.get("encodingFormat") != expected_image["encodingFormat"]:
            issues.append(f"Pages index featured project image encodingFormat drift: {project.get('name')}")
        if image_node.get("about", {}).get("@id") != expected_project_id:
            issues.append(f"Pages index featured project image about drift: {project.get('name')}")
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
