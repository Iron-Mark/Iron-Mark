#!/usr/bin/env python3
"""Derive Iron-Mark's narrative content from the live canonical portfolio feed.

Fetches https://www.marksiazon.dev/llms-index.json (the portfolio feed - a
different document from this repo's own llms-index.json), and:

  (a) rewrites marker-delimited regions in public/FAQ.md, public/PROOF.md,
      and public/RECRUITER.md with content rendered from the feed;
  (b) updates only entity.name, entity.sameAs, entity.description, and the
      availability key in this repo's llms-index.json (entity.@id is
      intentionally left untouched - migrating it is a later, separate
      concern, not handled here);
  (c) writes a normalized snapshot of the feed (src/data/portfolio-feed
      .snapshot.json by default) with a fetchedAt timestamp, for staleness
      tracking and for --check to diff against without a network call.

Marker format (exact, one pair per section, section in {faq, proof,
recruiter}):

    <!-- BEGIN DERIVED: <section> (from https://www.marksiazon.dev/llms-index.json - do not hand-edit) -->
    ...generated content...
    <!-- END DERIVED: <section> -->

Everything outside a marker pair is left byte-for-byte untouched. Re-running
the script against the same feed is idempotent (the derived region is always
fully regenerated from source data, never patched in place).

--check mode does not fetch anything: it loads the already-committed snapshot,
re-derives what the marker regions and llms-index.json entity/availability
keys *should* contain, and diffs that against what is actually on disk. Any
mismatch (e.g. a hand-edit inside a derived region) exits 1. This is meant to
be wired into CI so hand-drift inside derived regions fails validation. If no
snapshot exists yet, --check exits 0 with a warning (nothing to compare
against).

Staleness budget: if fetching the live feed fails, the script falls back to
the last-good snapshot (leaving all files untouched):
  - no snapshot on disk, or the snapshot's fetchedAt is more than 7 days old
    -> exit 2 and print a "::error::" line (GitHub Actions annotation);
  - snapshot exists and fetchedAt is within the 7-day budget -> exit 0 and
    print a "::warning::" line; nothing on disk is touched (the previous
    derive already reflects the last-good fetch).

No third-party dependencies (stdlib only: urllib, json, re, argparse), to
match this repo's other src/scripts/*.py. The `jsonschema` package is not
available in this repo's environments, so the feed is validated structurally
(required keys present, correct Python types) in validate_feed_structure()
rather than against the full JSON Schema at
https://www.marksiazon.dev/schema/llms-index.schema.json.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_FEED_URL = "https://www.marksiazon.dev/llms-index.json"
# The marker text always cites the canonical feed URL, regardless of which
# source (--feed-url or --feed-file) actually produced the data in a given
# run - the marker documents provenance of the *content*, not the CLI call.
MARKER_SOURCE_URL = "https://www.marksiazon.dev/llms-index.json"

DEFAULT_SNAPSHOT = ROOT / "src" / "data" / "portfolio-feed.snapshot.json"
DEFAULT_FAQ_MD = ROOT / "public" / "FAQ.md"
DEFAULT_PROOF_MD = ROOT / "public" / "PROOF.md"
DEFAULT_RECRUITER_MD = ROOT / "public" / "RECRUITER.md"
DEFAULT_INDEX_JSON = ROOT / "llms-index.json"

STALENESS_BUDGET_DAYS = 7

# feed availability keys that get written into this repo's availability
# object as-is. Any repo-authored availability subkey not in this set (e.g.
# status, focus, engagement, location, areaServed, remote, contact,
# recruiterBrief) is left untouched.
DERIVED_AVAILABILITY_KEYS = ("headline", "summary", "firstMessage", "note", "workScope")

# faq[] items render into FAQ.md's derived region when any of their
# audiences intersects this set. "project:*" audiences are deliberately
# excluded (those belong to per-project pages, not this repo).
FAQ_HOME_AUDIENCES = {"home", "recruiter", "contact"}


class FeedValidationError(Exception):
    """Raised when the fetched/loaded feed is missing required keys or has
    the wrong shape for the parts of it this script consumes."""


class MarkerNotFoundError(Exception):
    """Raised when a target markdown file has no BEGIN/END marker pair for
    the requested section."""


# --------------------------------------------------------------------------
# Feed loading + structural validation
# --------------------------------------------------------------------------


def fetch_feed(feed_url: str | None, feed_file: str | None) -> dict[str, Any]:
    """Load the feed JSON from a local file (if given) or over HTTP.

    Raises FileNotFoundError / OSError / urllib errors / json.JSONDecodeError
    on failure - callers are expected to catch broadly and treat any of
    these as a fetch failure for staleness-budget purposes.
    """
    if feed_file:
        text = Path(feed_file).read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(feed_url, timeout=30) as response:  # noqa: S310
            text = response.read().decode("utf-8")
    return json.loads(text)


def _require_string_fields(obj: Any, keys: tuple[str, ...], path: str, issues: list[str]) -> None:
    for key in keys:
        if not isinstance(obj.get(key), str):
            issues.append(f"{path}.{key} must be a string")


def validate_feed_structure(feed: Any) -> list[str]:
    """Structurally validate the subset of the feed this script consumes.

    Returns a list of human-readable issue strings (empty if valid). This is
    NOT full JSON-Schema validation against llms-index.schema.json -
    jsonschema isn't available in this repo's environments - just required
    keys + basic type checks.
    """
    issues: list[str] = []
    if not isinstance(feed, dict):
        return ["feed root must be a JSON object"]

    entity = feed.get("entity")
    if not isinstance(entity, dict):
        issues.append("entity must be an object")
    else:
        _require_string_fields(entity, ("name", "summary"), "entity", issues)
        if not isinstance(entity.get("sameAs"), list):
            issues.append("entity.sameAs must be an array")

    availability = feed.get("availability")
    if not isinstance(availability, dict):
        issues.append("availability must be an object")
    else:
        _require_string_fields(
            availability, ("headline", "summary", "firstMessage", "note"), "availability", issues
        )
        if not isinstance(availability.get("workScope"), list):
            issues.append("availability.workScope must be an array")

    projects = feed.get("projects")
    if not isinstance(projects, list):
        issues.append("projects must be an array")
    else:
        for index, project in enumerate(projects):
            path = f"projects[{index}]"
            if not isinstance(project, dict):
                issues.append(f"{path} must be an object")
                continue
            _require_string_fields(
                project, ("slug", "title", "role", "status", "canonicalUrl"), path, issues
            )

    faq = feed.get("faq")
    if not isinstance(faq, list):
        issues.append("faq must be an array")
    else:
        for index, item in enumerate(faq):
            path = f"faq[{index}]"
            if not isinstance(item, dict):
                issues.append(f"{path} must be an object")
                continue
            _require_string_fields(item, ("id", "question", "answer"), path, issues)
            if not isinstance(item.get("audiences"), list):
                issues.append(f"{path}.audiences must be an array")

    proof = feed.get("proof")
    if not isinstance(proof, dict):
        issues.append("proof must be an object")
    else:
        gates = proof.get("gates")
        if not isinstance(gates, list):
            issues.append("proof.gates must be an array")
        else:
            for index, gate in enumerate(gates):
                path = f"proof.gates[{index}]"
                if not isinstance(gate, dict):
                    issues.append(f"{path} must be an object")
                    continue
                _require_string_fields(gate, ("label", "owner", "status"), path, issues)

        by_project = proof.get("byProject")
        if not isinstance(by_project, dict):
            issues.append("proof.byProject must be an object")
        else:
            for slug, links in by_project.items():
                path = f"proof.byProject.{slug}"
                if not isinstance(links, list):
                    issues.append(f"{path} must be an array")
                    continue
                for index, link in enumerate(links):
                    if not isinstance(link, dict) or not isinstance(
                        link.get("label"), str
                    ) or not isinstance(link.get("href"), str):
                        issues.append(f"{path}[{index}] must have string label and href")

    return issues


def normalize_feed(feed: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of feed with volatile fields stripped so the
    snapshot only changes when meaningful content changes.

    pointers.generatedAt is a build identifier on the live site (not a
    timestamp of narrative content), so it is excluded from the stored/
    compared snapshot.
    """
    normalized = copy.deepcopy(feed)
    pointers = normalized.get("pointers")
    if isinstance(pointers, dict):
        pointers.pop("generatedAt", None)
    return normalized


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def home_faq_items(feed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in feed.get("faq", [])
        if isinstance(item, dict) and set(item.get("audiences", [])) & FAQ_HOME_AUDIENCES
    ]


def recruiter_faq_items(feed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in feed.get("faq", [])
        if isinstance(item, dict) and "recruiter" in item.get("audiences", [])
    ]


def render_faq_body(feed: dict[str, Any]) -> str:
    blocks = [f"## {item['question']}\n\n{item['answer']}" for item in home_faq_items(feed)]
    return "\n\n".join(blocks)


def render_proof_body(feed: dict[str, Any]) -> str:
    projects_by_slug = {
        project["slug"]: project
        for project in feed.get("projects", [])
        if isinstance(project, dict) and "slug" in project
    }
    proof = feed.get("proof", {})

    lines = ["### Proof gates", "", "| Label | Owner | Status |", "|-------|-------|--------|"]
    for gate in proof.get("gates", []):
        lines.append(f"| {gate['label']} | {gate['owner']} | {gate['status']} |")

    lines.append("")
    lines.append("### Proof by project")

    by_project = proof.get("byProject", {})
    for slug in sorted(by_project):
        links = by_project[slug]
        project = projects_by_slug.get(slug, {})
        title = project.get("title", slug)
        canonical_url = project.get("canonicalUrl", "")
        heading = f"#### {title}" + (f" ({canonical_url})" if canonical_url else "")
        lines.append("")
        lines.append(heading)
        lines.append("")
        for link in links:
            lines.append(f"- [{link['label']}]({link['href']})")

    return "\n".join(lines)


def render_recruiter_body(feed: dict[str, Any]) -> str:
    availability = feed.get("availability", {})
    lines = ["### Availability", ""]
    lines.append(f"**{availability.get('headline', '')}**")
    lines.append("")
    lines.append(availability.get("summary", ""))
    lines.append("")
    lines.append(f"First message: {availability.get('firstMessage', '')}")
    lines.append("")
    lines.append(f"Note: {availability.get('note', '')}")
    lines.append("")
    lines.append(f"Work scope: {', '.join(availability.get('workScope', []))}")

    lines.append("")
    lines.append("### Recruiter FAQ")
    for item in recruiter_faq_items(feed):
        lines.append("")
        lines.append(f"## {item['question']}")
        lines.append("")
        lines.append(item["answer"])

    lines.append("")
    lines.append("### Projects")
    lines.append("")
    lines.append("| Project | Role | Status | Link |")
    lines.append("|---------|------|--------|------|")
    for project in feed.get("projects", []):
        lines.append(
            "| {title} | {role} | {status} | {canonicalUrl} |".format(
                title=project.get("title", ""),
                role=project.get("role", ""),
                status=project.get("status", ""),
                canonicalUrl=project.get("canonicalUrl", ""),
            )
        )

    return "\n".join(lines)


def derived_body(section: str, feed: dict[str, Any]) -> str:
    if section == "faq":
        return render_faq_body(feed)
    if section == "proof":
        return render_proof_body(feed)
    if section == "recruiter":
        return render_recruiter_body(feed)
    raise ValueError(f"Unknown derived section: {section!r}")


# --------------------------------------------------------------------------
# Marker region replacement
# --------------------------------------------------------------------------


def _marker_pattern(section: str) -> re.Pattern[str]:
    begin = re.escape(
        f"<!-- BEGIN DERIVED: {section} (from {MARKER_SOURCE_URL} - do not hand-edit) -->"
    )
    end = re.escape(f"<!-- END DERIVED: {section} -->")
    return re.compile(f"({begin})(.*?)({end})", re.DOTALL)


def replace_derived_region(text: str, section: str, body: str) -> str:
    """Replace the content between the section's BEGIN/END markers with
    `body`, leaving everything else in `text` byte-for-byte untouched.

    Always fully regenerates the region (never patches in place), so
    repeated calls with the same `body` are idempotent.
    """
    pattern = _marker_pattern(section)
    match = pattern.search(text)
    if not match:
        raise MarkerNotFoundError(
            f"No 'DERIVED: {section}' marker pair found. Add:\n"
            f"  <!-- BEGIN DERIVED: {section} (from {MARKER_SOURCE_URL} - do not hand-edit) -->\n"
            f"  <!-- END DERIVED: {section} -->\n"
            "before running derive_from_portfolio.py."
        )
    replacement = f"{match.group(1)}\n\n{body}\n\n{match.group(3)}"
    return text[: match.start()] + replacement + text[match.end() :]


# --------------------------------------------------------------------------
# llms-index.json entity/availability update
# --------------------------------------------------------------------------


def apply_entity_and_availability(index_data: dict[str, Any], feed: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of index_data with entity.name/sameAs/description and
    the derived availability subkeys overwritten from feed.

    entity.@id is intentionally left untouched, along with every other
    entity/availability subkey not named here - those stay repo-authored.
    """
    result = copy.deepcopy(index_data)

    entity = result.setdefault("entity", {})
    feed_entity = feed.get("entity", {})
    if "name" in feed_entity:
        entity["name"] = feed_entity["name"]
    if "sameAs" in feed_entity:
        entity["sameAs"] = feed_entity["sameAs"]
    if "summary" in feed_entity:
        entity["description"] = feed_entity["summary"]

    availability = result.setdefault("availability", {})
    feed_availability = feed.get("availability", {})
    for key in DERIVED_AVAILABILITY_KEYS:
        if key in feed_availability:
            availability[key] = feed_availability[key]

    return result


# --------------------------------------------------------------------------
# Output building (shared by derive + --check)
# --------------------------------------------------------------------------


def build_outputs(feed: dict[str, Any], paths: dict[str, Path]) -> dict[str, str]:
    """Return {path-string: new full file content} for the three markdown
    files' derived regions plus llms-index.json, computed from `feed` and
    each file's *current on-disk* content (so text outside markers is
    preserved exactly)."""
    outputs: dict[str, str] = {}

    for section, key in (("faq", "faq_md"), ("proof", "proof_md"), ("recruiter", "recruiter_md")):
        path = paths[key]
        text = path.read_text(encoding="utf-8")
        body = derived_body(section, feed)
        outputs[str(path)] = replace_derived_region(text, section, body)

    index_path = paths["index_json"]
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    updated_index = apply_entity_and_availability(index_data, feed)
    outputs[str(index_path)] = json.dumps(updated_index, indent=2, ensure_ascii=False) + "\n"

    return outputs


def write_outputs(outputs: dict[str, str]) -> None:
    for path_str, content in outputs.items():
        Path(path_str).write_text(content, encoding="utf-8", newline="\n")


def diff_outputs(feed: dict[str, Any], paths: dict[str, Path]) -> list[str]:
    """Return the list of path strings whose current on-disk content differs
    from what deriving `feed` would produce."""
    outputs = build_outputs(feed, paths)
    diffs = []
    for path_str, expected in outputs.items():
        actual = Path(path_str).read_text(encoding="utf-8")
        if actual != expected:
            diffs.append(path_str)
    return diffs


# --------------------------------------------------------------------------
# Snapshot + staleness
# --------------------------------------------------------------------------


def load_snapshot(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def snapshot_is_stale(fetched_at: str, now: datetime) -> bool:
    try:
        fetched_dt = datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError):
        return True
    if fetched_dt.tzinfo is None:
        fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
    return (now - fetched_dt) > timedelta(days=STALENESS_BUDGET_DAYS)


def write_snapshot(snapshot_path: Path, normalized_feed: dict[str, Any], fetched_at: str) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fetchedAt": fetched_at, "feed": normalized_feed}
    snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------
# CLI orchestration
# --------------------------------------------------------------------------


def run_derive(
    feed_url: str | None,
    feed_file: str | None,
    snapshot_path: Path,
    paths: dict[str, Path],
) -> int:
    existing_snapshot = load_snapshot(snapshot_path)
    now = datetime.now(timezone.utc)

    try:
        feed = fetch_feed(feed_url, feed_file)
        issues = validate_feed_structure(feed)
        if issues:
            raise FeedValidationError("; ".join(issues))
    except Exception as exc:  # noqa: BLE001 - any load/validate failure triggers the staleness fallback
        return _handle_fetch_failure(exc, existing_snapshot, now)

    normalized_feed = normalize_feed(feed)
    outputs = build_outputs(normalized_feed, paths)
    write_outputs(outputs)
    fetched_at = now.isoformat()
    write_snapshot(snapshot_path, normalized_feed, fetched_at)
    print(f"derive_from_portfolio: derived ok fetchedAt={fetched_at}")
    return 0


def _handle_fetch_failure(
    exc: Exception, existing_snapshot: dict[str, Any] | None, now: datetime
) -> int:
    if existing_snapshot is None:
        print(
            f"::error::derive_from_portfolio: feed fetch failed and no snapshot exists "
            f"to fall back on: {exc}"
        )
        return 2

    fetched_at = existing_snapshot.get("fetchedAt", "")
    if snapshot_is_stale(fetched_at, now):
        print(
            f"::error::derive_from_portfolio: feed fetch failed ({exc}) and the "
            f"snapshot is older than {STALENESS_BUDGET_DAYS} days (fetchedAt={fetched_at!r})"
        )
        return 2

    print(
        f"::warning::derive_from_portfolio: feed fetch failed ({exc}); keeping last-good "
        f"snapshot from {fetched_at}"
    )
    return 0


def run_check(snapshot_path: Path, paths: dict[str, Path]) -> int:
    snapshot = load_snapshot(snapshot_path)
    if snapshot is None:
        print(
            "::warning::derive_from_portfolio: no snapshot found at "
            f"{snapshot_path}; skipping derived-region check"
        )
        return 0

    feed = snapshot.get("feed", {})
    diffs = diff_outputs(feed, paths)
    if diffs:
        print("::error::derive_from_portfolio: derived content out of sync with committed snapshot:")
        for path_str in diffs:
            print(f"  - {path_str}")
        return 1

    print("derive_from_portfolio: check ok, derived regions match committed snapshot")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--feed-url", default=DEFAULT_FEED_URL, help="Live feed URL to fetch (ignored if --feed-file is given).")
    parser.add_argument("--feed-file", default=None, help="Local feed JSON file to use instead of --feed-url (offline/fixture use).")
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="Path to the committed feed snapshot.")
    parser.add_argument("--check", action="store_true", help="Derive from the committed snapshot and diff against disk; exit 1 on any drift.")
    parser.add_argument("--faq-md", default=str(DEFAULT_FAQ_MD), help=argparse.SUPPRESS)
    parser.add_argument("--proof-md", default=str(DEFAULT_PROOF_MD), help=argparse.SUPPRESS)
    parser.add_argument("--recruiter-md", default=str(DEFAULT_RECRUITER_MD), help=argparse.SUPPRESS)
    parser.add_argument("--index-json", default=str(DEFAULT_INDEX_JSON), help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    paths = {
        "faq_md": Path(args.faq_md),
        "proof_md": Path(args.proof_md),
        "recruiter_md": Path(args.recruiter_md),
        "index_json": Path(args.index_json),
    }
    snapshot_path = Path(args.snapshot)

    if args.check:
        return run_check(snapshot_path, paths)
    return run_derive(args.feed_url, args.feed_file, snapshot_path, paths)


if __name__ == "__main__":
    sys.exit(main())
