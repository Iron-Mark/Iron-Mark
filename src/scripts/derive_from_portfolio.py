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
  (b2) keeps this repo's aeo.answerSnippets entries in sync with the
      subset of feed FAQ items that also render into FAQ.md's derived
      region (matched by question). validate_index.py's check_aeo_coverage
      requires every answerSnippet answer to appear verbatim in FAQ.md, so
      once part of FAQ.md is feed-derived, the overlapping answerSnippets
      must be feed-derived too, or a portfolio wording change breaks that
      check. sources and every non-overlapping (repo-authored) snippet are
      left untouched;
  (c) writes a normalized snapshot of the feed (src/data/portfolio-feed
      .snapshot.json by default) with a fetchedAt timestamp, for staleness
      tracking and for --check to diff against without a network call. If
      the feed's content is unchanged from the committed snapshot, the
      snapshot is left alone (fetchedAt is not churned every run) unless
      it has gone quiet for SNAPSHOT_HEARTBEAT_DAYS, in which case
      fetchedAt alone is refreshed as a heartbeat.

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

Staleness budget: this only applies to genuine fetch failures (network/IO/
JSON-decode errors) - if the feed fetches fine but fails structural
validation (a contract break), that is never treated as transient: it
prints the issues and exits 2 immediately, regardless of how fresh the
last-good snapshot is. For genuine fetch failures, the script falls back to
the last-good snapshot (leaving all files untouched):
  - no snapshot on disk, or the snapshot's fetchedAt is more than 7 days old
    -> exit 2 and print a "::error::" line (GitHub Actions annotation);
  - snapshot exists and fetchedAt is within the 7-day budget -> exit 0 and
    print a "::warning::" line; nothing on disk is touched (the previous
    derive already reflects the last-good fetch).

--check additionally treats a stale committed snapshot as a hard failure:
if the snapshot is structurally invalid, or its fetchedAt is more than 7
days old, --check prints a clear "::error::" and exits 1, converting a
silently-stalled daily pipeline into a visible CI failure.

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

# If the committed snapshot's feed is byte-identical to a freshly fetched
# feed, run_derive skips rewriting the snapshot (so fetchedAt doesn't churn
# on every run for no content reason - see run_derive). But if the snapshot
# hasn't been touched in this many days, fetchedAt is refreshed anyway as a
# heartbeat, so staleness tracking never drifts from "the pipeline is
# actually still running fine, it just has nothing new to say."
SNAPSHOT_HEARTBEAT_DAYS = 3

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
    """Return a deep copy of feed with volatile fields stripped, so
    equality-comparing two normalized feeds reflects meaningful content
    changes only.

    pointers.generatedAt is a build identifier on the live site (not a
    timestamp of narrative content), so it is excluded here. This is what
    lets run_derive tell "the feed actually changed" apart from "the feed
    is the same but the live site rebuilt" - the comparison that decides
    whether the committed snapshot's `feed` key gets rewritten at all (see
    SNAPSHOT_HEARTBEAT_DAYS). Note that normalize_feed only controls the
    `feed` key: the snapshot's `fetchedAt` key is a separate concern and
    may still be refreshed on an unchanged feed, as a heartbeat.
    """
    normalized = copy.deepcopy(feed)
    pointers = normalized.get("pointers")
    if isinstance(pointers, dict):
        pointers.pop("generatedAt", None)
    return normalized


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def escape_md_table_cell(value: Any) -> str:
    """Escape a feed-sourced value for safe embedding in a markdown table
    cell.

    A literal '|' would be parsed as a new column boundary (corrupting
    every column after it), and an embedded newline would terminate the
    row early - so pipes are backslash-escaped and internal whitespace
    (including newlines) is collapsed to single spaces.
    """
    text = value if isinstance(value, str) else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("|", "\\|")


def escape_md_heading_text(value: Any) -> str:
    """Escape a feed-sourced value for safe embedding in a markdown ATX
    heading line (or other single-line construct).

    A literal newline would terminate the line and let injected content
    become new markdown structure of its own (headings, tables, etc.), so
    internal whitespace is collapsed to single spaces.
    """
    text = value if isinstance(value, str) else str(value)
    return re.sub(r"\s+", " ", text).strip()


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
    blocks = [
        f"## {escape_md_heading_text(item['question'])}\n\n{item['answer']}"
        for item in home_faq_items(feed)
    ]
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
        label = escape_md_table_cell(gate["label"])
        owner = escape_md_table_cell(gate["owner"])
        status = escape_md_table_cell(gate["status"])
        lines.append(f"| {label} | {owner} | {status} |")

    lines.append("")
    lines.append("### Proof by project")

    by_project = proof.get("byProject", {})
    for slug in sorted(by_project):
        links = by_project[slug]
        project = projects_by_slug.get(slug, {})
        title = escape_md_heading_text(project.get("title", slug))
        canonical_url = escape_md_heading_text(project.get("canonicalUrl", ""))
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
        lines.append(f"## {escape_md_heading_text(item['question'])}")
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
                title=escape_md_table_cell(project.get("title", "")),
                role=escape_md_table_cell(project.get("role", "")),
                status=escape_md_table_cell(project.get("status", "")),
                canonicalUrl=escape_md_table_cell(project.get("canonicalUrl", "")),
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


class MarkerCorruptionError(Exception):
    """Raised when a target file has more than one BEGIN or END marker for
    a section, or an END marker appears before its BEGIN - both signs the
    file has already been corrupted (e.g. by a marker-breakout injection
    from before body sanitization existed, or a hand-edit gone wrong).
    Refuses to guess which pair is the "real" one."""


def _marker_literals(section: str) -> tuple[str, str]:
    begin = f"<!-- BEGIN DERIVED: {section} (from {MARKER_SOURCE_URL} - do not hand-edit) -->"
    end = f"<!-- END DERIVED: {section} -->"
    return begin, end


def _marker_pattern(section: str) -> re.Pattern[str]:
    begin, end = _marker_literals(section)
    return re.compile(f"({re.escape(begin)})(.*?)({re.escape(end)})", re.DOTALL)


def _assert_single_marker_pair(text: str, section: str) -> None:
    """Guard against a target file that is already corrupted before we
    even start: more than one BEGIN or END marker for `section`, or an END
    that appears before its BEGIN. A file with NO markers at all is not
    corruption (that's a new file that hasn't had markers added yet) and
    is left to replace_derived_region's MarkerNotFoundError instead.
    """
    begin, end = _marker_literals(section)
    begin_count = text.count(begin)
    end_count = text.count(end)
    if begin_count == 0 and end_count == 0:
        return
    if begin_count != 1 or end_count != 1:
        raise MarkerCorruptionError(
            f"Expected exactly one BEGIN and one END 'DERIVED: {section}' marker, "
            f"found {begin_count} BEGIN and {end_count} END. The file may already be "
            "corrupted (e.g. by injected marker text from a previous run); refusing "
            "to guess which pair is real."
        )
    if text.index(begin) > text.index(end):
        raise MarkerCorruptionError(
            f"'DERIVED: {section}' END marker appears before its BEGIN marker - the "
            "file is corrupted."
        )


_MARKER_TEXT_BREAKOUT_PATTERN = re.compile(r"<!--(\s*(?:BEGIN|END)\s+DERIVED:)")


def sanitize_marker_breakout(text: str) -> str:
    """Neutralize any literal '<!-- BEGIN DERIVED:' / '<!-- END DERIVED:'
    text found inside feed-sourced content before it is written into a
    target file.

    Without this, feed content that happens to contain that exact text
    (accidentally or adversarially) would be indistinguishable from a real
    marker boundary the next time this script parses the file - corrupting
    it compoundingly on every subsequent run. The HTML entity escape for
    '<' makes the sequence inert both as an HTML comment and as a literal
    string match for _marker_pattern()/_marker_literals().
    """
    return _MARKER_TEXT_BREAKOUT_PATTERN.sub(r"&lt;!--\1", text)


def replace_derived_region(text: str, section: str, body: str) -> str:
    """Replace the content between the section's BEGIN/END markers with
    `body`, leaving everything else in `text` byte-for-byte untouched.

    Always fully regenerates the region (never patches in place), so
    repeated calls with the same `body` are idempotent. `body` is
    sanitized against marker breakout before insertion (see
    sanitize_marker_breakout), and `text` is checked for pre-existing
    marker corruption before any replacement is attempted (see
    _assert_single_marker_pair).
    """
    _assert_single_marker_pair(text, section)
    pattern = _marker_pattern(section)
    match = pattern.search(text)
    if not match:
        raise MarkerNotFoundError(
            f"No 'DERIVED: {section}' marker pair found. Add:\n"
            f"  <!-- BEGIN DERIVED: {section} (from {MARKER_SOURCE_URL} - do not hand-edit) -->\n"
            f"  <!-- END DERIVED: {section} -->\n"
            "before running derive_from_portfolio.py."
        )
    safe_body = sanitize_marker_breakout(body)
    replacement = f"{match.group(1)}\n\n{safe_body}\n\n{match.group(3)}"
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


def apply_aeo_answer_snippets(index_data: dict[str, Any], feed: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of index_data with aeo.answerSnippets entries that
    overlap the feed-derived FAQ.md region kept in sync with the feed.

    aeo.answerSnippets is otherwise hand-authored, but validate_index.py's
    check_aeo_coverage requires every snippet's `answer` to appear
    verbatim in FAQ.md. Now that part of FAQ.md's visible text is rendered
    from the portfolio feed (render_faq_body), any answerSnippet that
    duplicates one of those feed FAQ items must be re-derived from the
    same feed on every run, or the next portfolio wording change breaks
    that verbatim check.

    Overlap is detected by matching an existing snippet's `question`
    against the `question` of one of home_faq_items(feed) - the same feed
    items render_faq_body() renders into FAQ.md's derived region. When
    matched, both `question` and `answer` are overwritten from the feed
    item, put through the exact same transforms render_faq_body applies
    (heading-line escaping for the question, marker-breakout sanitization
    for both), so the snippet stays byte-for-byte identical to what
    actually ends up in FAQ.md. `sources` and every non-overlapping
    (repo-authored) snippet are left untouched.
    """
    result = copy.deepcopy(index_data)
    aeo = result.get("aeo")
    if not isinstance(aeo, dict):
        return result
    snippets = aeo.get("answerSnippets")
    if not isinstance(snippets, list):
        return result

    feed_items_by_question = {
        item["question"]: item
        for item in home_faq_items(feed)
        if isinstance(item, dict) and isinstance(item.get("question"), str)
    }

    for snippet in snippets:
        if not isinstance(snippet, dict):
            continue
        feed_item = feed_items_by_question.get(snippet.get("question"))
        if feed_item is None:
            continue
        snippet["question"] = sanitize_marker_breakout(escape_md_heading_text(feed_item["question"]))
        snippet["answer"] = sanitize_marker_breakout(feed_item["answer"])

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
    updated_index = apply_aeo_answer_snippets(updated_index, feed)
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


def snapshot_is_stale(fetched_at: str, now: datetime, budget_days: int = STALENESS_BUDGET_DAYS) -> bool:
    try:
        fetched_dt = datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError):
        return True
    if fetched_dt.tzinfo is None:
        fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
    return (now - fetched_dt) > timedelta(days=budget_days)


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
    except Exception as exc:  # noqa: BLE001 - network/IO/JSON-decode failures are transient, so
        # (and only these) go through the staleness fallback below.
        return _handle_fetch_failure(exc, existing_snapshot, now)

    issues = validate_feed_structure(feed)
    if issues:
        # The feed fetched fine but violates the contract this script
        # relies on. This is deliberately NOT routed through
        # _handle_fetch_failure/the staleness fallback above: a fetched-
        # but-invalid feed means something upstream broke the contract,
        # which is never transient and must fail loudly and immediately -
        # even if the last-good snapshot is well within its budget.
        error = FeedValidationError("; ".join(issues))
        print(f"::error::derive_from_portfolio: fetched feed failed structural validation: {error}")
        for issue in issues:
            print(f"  - {issue}")
        return 2

    normalized_feed = normalize_feed(feed)
    outputs = build_outputs(normalized_feed, paths)
    write_outputs(outputs)
    fetched_at = now.isoformat()

    existing_feed = existing_snapshot.get("feed") if existing_snapshot else None
    if existing_feed == normalized_feed:
        # Content is unchanged from the committed snapshot: rewriting it
        # anyway would only churn fetchedAt, which turns every dev->main
        # promotion into a fetchedAt-only bot PR that never lets dev and
        # main converge. Skip the write entirely, unless the snapshot has
        # gone quiet long enough that fetchedAt itself needs a heartbeat
        # refresh so staleness tracking stays honest.
        existing_fetched_at = existing_snapshot.get("fetchedAt", "") if existing_snapshot else ""
        if not snapshot_is_stale(existing_fetched_at, now, SNAPSHOT_HEARTBEAT_DAYS):
            print(f"derive_from_portfolio: feed unchanged; keeping fetchedAt={existing_fetched_at}")
            return 0
        write_snapshot(snapshot_path, normalized_feed, fetched_at)
        print(f"derive_from_portfolio: feed unchanged; heartbeat fetchedAt={fetched_at}")
        return 0

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
    issues = validate_feed_structure(feed)
    if issues:
        # A malformed snapshot used to surface as an uncaught KeyError deep
        # inside diff_outputs()/render_*_body() - a confusing traceback
        # instead of an actionable message. Validate structurally first so
        # this fails clearly and predictably.
        print(
            "::error::derive_from_portfolio: --check found a structurally invalid "
            f"committed snapshot at {snapshot_path}:"
        )
        for issue in issues:
            print(f"  - {issue}")
        return 1

    fetched_at = snapshot.get("fetchedAt", "")
    now = datetime.now(timezone.utc)
    if snapshot_is_stale(fetched_at, now):
        # A snapshot that never gets refreshed (the daily derive pipeline
        # silently stalled - e.g. a broken cron, a permanently-failing
        # fetch that never gets loud) would otherwise pass --check forever
        # as long as nothing else drifts. Surface it instead.
        print(
            "::error::derive_from_portfolio: --check found the committed snapshot's "
            f"fetchedAt={fetched_at!r} is older than {STALENESS_BUDGET_DAYS} days - the "
            "daily derive pipeline appears to have stalled"
        )
        return 1

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
