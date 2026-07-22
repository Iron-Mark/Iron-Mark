#!/usr/bin/env python3
"""Unit tests for derive_from_portfolio.py.

Runs entirely offline against the fixtures in src/data/test-fixtures/. Never
hits the network - fetch failure is simulated with a nonexistent --feed-file
path instead of mocking urllib.

Invoke with: python -m unittest src.scripts.test_derive_from_portfolio -v
"""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.scripts import derive_from_portfolio as derive

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "src" / "data" / "test-fixtures"


class DeriveTestCase(unittest.TestCase):
    """Base case that copies fixtures into a scratch dir so tests never mutate
    the checked-in fixtures or the real repo files."""

    def setUp(self) -> None:
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.work_dir = Path(self._tmp_ctx.name)

        self.feed_path = self.work_dir / "feed-sample.json"
        self.faq_path = self.work_dir / "faq-fixture.md"
        self.proof_path = self.work_dir / "proof-fixture.md"
        self.recruiter_path = self.work_dir / "recruiter-fixture.md"
        self.index_path = self.work_dir / "index-fixture.json"
        self.snapshot_path = self.work_dir / "portfolio-feed.snapshot.json"

        shutil.copy(FIXTURES / "feed-sample.json", self.feed_path)
        shutil.copy(FIXTURES / "faq-fixture.md", self.faq_path)
        shutil.copy(FIXTURES / "proof-fixture.md", self.proof_path)
        shutil.copy(FIXTURES / "recruiter-fixture.md", self.recruiter_path)
        shutil.copy(FIXTURES / "index-fixture.json", self.index_path)

    def tearDown(self) -> None:
        self._tmp_ctx.cleanup()

    def run_main(self, *extra_args: str) -> int:
        args = [
            "--feed-file", str(self.feed_path),
            "--snapshot", str(self.snapshot_path),
            "--faq-md", str(self.faq_path),
            "--proof-md", str(self.proof_path),
            "--recruiter-md", str(self.recruiter_path),
            "--index-json", str(self.index_path),
            *extra_args,
        ]
        return derive.main(args)

    def run_check(self) -> int:
        return self.run_main("--check")


class DeriveRegionTests(DeriveTestCase):
    def test_derive_exits_zero(self) -> None:
        self.assertEqual(self.run_main(), 0)

    def test_faq_marker_region_replaced_and_outside_text_untouched(self) -> None:
        self.run_main()
        text = self.faq_path.read_text(encoding="utf-8")

        self.assertIn("# Fixture FAQ", text)
        self.assertIn("Intro paragraph that must stay untouched by the deriver.", text)
        self.assertIn("## Repo-specific question", text)
        self.assertIn(
            "This answer stays outside the derived region and must not be touched.",
            text,
        )

        # Home/recruiter/contact-audience questions render inside the region.
        self.assertIn("## Home question one?", text)
        self.assertIn("Home answer one.", text)
        self.assertIn("## Home question two?", text)
        self.assertIn("## Recruiter question one?", text)
        self.assertIn("## Contact question one?", text)

        # project:x-only audience must NOT render into the faq section.
        self.assertNotIn("Alpha-only question?", text)

        begin = (
            "<!-- BEGIN DERIVED: faq (from https://www.marksiazon.dev/"
            "llms-index.json - do not hand-edit) -->"
        )
        end = "<!-- END DERIVED: faq -->"
        self.assertIn(begin, text)
        self.assertIn(end, text)
        self.assertLess(text.index(begin), text.index(end))

    def test_proof_marker_region_replaced_and_outside_text_untouched(self) -> None:
        self.run_main()
        text = self.proof_path.read_text(encoding="utf-8")

        self.assertIn(
            "Repo-authored identity table that must stay untouched by the deriver.",
            text,
        )
        self.assertIn("| Fixture claim | Fixture proof link |", text)
        self.assertIn("## Repo-authored footer", text)

        self.assertIn("Fixture gate one", text)
        self.assertIn("QA", text)
        self.assertIn("Alpha Project", text)
        self.assertIn("https://alpha.example.test", text)
        self.assertIn("Beta Project", text)
        self.assertIn("https://github.com/example/beta", text)

    def test_recruiter_marker_region_replaced_and_outside_text_untouched(self) -> None:
        self.run_main()
        text = self.recruiter_path.read_text(encoding="utf-8")

        self.assertIn(
            "Repo-authored framing paragraph that must stay untouched by the deriver.",
            text,
        )
        self.assertIn("## Contact", text)
        self.assertIn(
            "Repo-authored contact section stays outside the derived region and must not be touched.",
            text,
        )

        self.assertIn("Open for test opportunities", text)
        self.assertIn("Fixture QA", text)
        self.assertIn("Test automation", text)
        # Recruiter section renders only recruiter-audience FAQ answers.
        self.assertIn("Recruiter question one?", text)
        self.assertIn("Recruiter question two?", text)
        self.assertNotIn("Contact question one?", text)
        # Projects list.
        self.assertIn("Alpha Project", text)
        self.assertIn("Test engineer", text)
        self.assertIn("Beta Project", text)

    def test_idempotent_run_twice_identical(self) -> None:
        self.run_main()
        faq_after_first = self.faq_path.read_text(encoding="utf-8")
        proof_after_first = self.proof_path.read_text(encoding="utf-8")
        recruiter_after_first = self.recruiter_path.read_text(encoding="utf-8")
        index_after_first = self.index_path.read_text(encoding="utf-8")
        snapshot_after_first = json.loads(self.snapshot_path.read_text(encoding="utf-8"))

        self.run_main()
        self.assertEqual(faq_after_first, self.faq_path.read_text(encoding="utf-8"))
        self.assertEqual(proof_after_first, self.proof_path.read_text(encoding="utf-8"))
        self.assertEqual(recruiter_after_first, self.recruiter_path.read_text(encoding="utf-8"))
        self.assertEqual(index_after_first, self.index_path.read_text(encoding="utf-8"))

        snapshot_after_second = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot_after_first["feed"], snapshot_after_second["feed"])


class IndexUpdateTests(DeriveTestCase):
    def test_entity_and_availability_updated_id_untouched(self) -> None:
        self.run_main()
        data = json.loads(self.index_path.read_text(encoding="utf-8"))

        entity = data["entity"]
        self.assertEqual(entity["name"], "Test Person")
        self.assertEqual(
            entity["description"],
            "Test summary sentence for the derived entity description.",
        )
        self.assertEqual(
            entity["sameAs"],
            [
                "https://github.com/test-person",
                "https://www.linkedin.com/in/test-person/",
            ],
        )
        # @id is explicitly NOT derived (Phase 5 concern).
        self.assertEqual(entity["@id"], "https://example.test/#person")
        # Repo-authored entity subkeys stay untouched.
        self.assertEqual(entity["alternateName"], ["OldAlt"])
        self.assertEqual(entity["jobTitle"], ["Old Title"])
        self.assertEqual(entity["email"], "old@example.test")

        availability = data["availability"]
        self.assertEqual(availability["headline"], "Open for test opportunities")
        self.assertEqual(availability["summary"], "Best fit: test roles and fixture QA.")
        self.assertEqual(
            availability["firstMessage"], "Share the fixture scenario you want reviewed."
        )
        self.assertEqual(availability["note"], "This is fixture data only; do not contact.")
        self.assertEqual(availability["workScope"], ["Fixture QA", "Test automation"])
        # Repo-authored availability subkeys (not present in feed) stay untouched.
        self.assertEqual(availability["status"], "open")
        self.assertEqual(availability["focus"], ["old focus"])
        self.assertEqual(availability["engagement"], ["contract"])
        self.assertEqual(availability["location"], "Nowhere")
        self.assertEqual(availability["areaServed"], ["Nowhere"])
        self.assertEqual(availability["remote"], True)
        self.assertEqual(availability["contact"], "https://example.test/contact")
        self.assertEqual(availability["recruiterBrief"], "https://example.test/recruiter")

        # Unrelated top-level keys stay untouched.
        self.assertEqual(data["otherRepoAuthoredKey"], "must remain untouched")
        self.assertEqual(data["updated"], "2026-01-01")


class SnapshotTests(DeriveTestCase):
    def test_snapshot_written_normalized_without_generated_at(self) -> None:
        self.run_main()
        snapshot = json.loads(self.snapshot_path.read_text(encoding="utf-8"))

        self.assertIn("fetchedAt", snapshot)
        self.assertIn("feed", snapshot)
        self.assertNotIn("generatedAt", snapshot["feed"].get("pointers", {}))
        # Other pointer fields survive normalization.
        self.assertEqual(snapshot["feed"]["pointers"]["site"], "https://example.test")
        # fetchedAt must be a parseable ISO-8601 timestamp.
        datetime.fromisoformat(snapshot["fetchedAt"])


class ByteDeterminismTests(DeriveTestCase):
    def test_derived_md_files_have_lf_line_endings_only(self) -> None:
        """Verify byte-level determinism: derived markdown files contain only
        LF line endings (\\n), never CRLF (\\r\\n), even when run on Windows."""
        self.run_main()

        # Check all three derived markdown files for carriage returns.
        for path in [self.faq_path, self.proof_path, self.recruiter_path]:
            with self.subTest(file=path.name):
                raw_bytes = path.read_bytes()
                # Assert no carriage returns are present in the raw bytes.
                self.assertNotIn(b"\r", raw_bytes,
                    f"{path.name} contains CRLF or CR line endings, violating "
                    "cross-platform byte determinism")


class CheckModeTests(DeriveTestCase):
    def test_check_passes_after_derive(self) -> None:
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.run_check(), 0)

    def test_check_fails_after_hand_edit_inside_region(self) -> None:
        self.run_main()
        self.assertEqual(self.run_check(), 0)

        text = self.faq_path.read_text(encoding="utf-8")
        hand_edited = text.replace("Home answer one.", "HAND-EDITED ANSWER, DO NOT TRUST")
        self.assertNotEqual(text, hand_edited)
        self.faq_path.write_text(hand_edited, encoding="utf-8")

        self.assertEqual(self.run_check(), 1)

    def test_check_fails_when_entity_hand_edited(self) -> None:
        self.run_main()
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        data["entity"]["description"] = "Hand-edited, should not match snapshot"
        self.index_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        self.assertEqual(self.run_check(), 1)

    def test_check_warns_and_exits_zero_without_snapshot(self) -> None:
        # No derive has run yet, so no snapshot file exists.
        self.assertFalse(self.snapshot_path.exists())
        self.assertEqual(self.run_check(), 0)


class StalenessTests(DeriveTestCase):
    def _write_snapshot(self, fetched_at: str) -> None:
        feed = json.loads(self.feed_path.read_text(encoding="utf-8"))
        normalized = derive.normalize_feed(feed)
        self.snapshot_path.write_text(
            json.dumps({"fetchedAt": fetched_at, "feed": normalized}, indent=2) + "\n",
            encoding="utf-8",
        )

    def _missing_feed_args(self) -> list[str]:
        missing_feed = self.work_dir / "does-not-exist.json"
        return [
            "--feed-file", str(missing_feed),
            "--snapshot", str(self.snapshot_path),
            "--faq-md", str(self.faq_path),
            "--proof-md", str(self.proof_path),
            "--recruiter-md", str(self.recruiter_path),
            "--index-json", str(self.index_path),
        ]

    def test_fetch_failure_with_no_snapshot_exits_two(self) -> None:
        self.assertFalse(self.snapshot_path.exists())
        exit_code = derive.main(self._missing_feed_args())
        self.assertEqual(exit_code, 2)

    def test_fetch_failure_with_stale_snapshot_exits_two(self) -> None:
        stale = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        self._write_snapshot(stale)
        exit_code = derive.main(self._missing_feed_args())
        self.assertEqual(exit_code, 2)

    def test_fetch_failure_with_fresh_snapshot_keeps_last_good_exits_zero(self) -> None:
        fresh = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self._write_snapshot(fresh)
        before = self.snapshot_path.read_text(encoding="utf-8")

        exit_code = derive.main(self._missing_feed_args())

        self.assertEqual(exit_code, 0)
        # Last-good snapshot is kept as-is (not overwritten with empty/partial data).
        self.assertEqual(before, self.snapshot_path.read_text(encoding="utf-8"))


class FeedValidationTests(unittest.TestCase):
    def test_valid_fixture_feed_has_no_issues(self) -> None:
        feed = json.loads((FIXTURES / "feed-sample.json").read_text(encoding="utf-8"))
        self.assertEqual(derive.validate_feed_structure(feed), [])

    def test_missing_required_key_reported(self) -> None:
        feed = json.loads((FIXTURES / "feed-sample.json").read_text(encoding="utf-8"))
        del feed["availability"]["headline"]
        issues = derive.validate_feed_structure(feed)
        self.assertTrue(any("availability.headline" in issue for issue in issues))

    def test_wrong_type_reported(self) -> None:
        feed = json.loads((FIXTURES / "feed-sample.json").read_text(encoding="utf-8"))
        feed["entity"]["sameAs"] = "not-a-list"
        issues = derive.validate_feed_structure(feed)
        self.assertTrue(any("entity.sameAs" in issue for issue in issues))


class AeoAnswerSnippetTests(DeriveTestCase):
    """Finding A: aeo.answerSnippets entries that overlap the feed-derived
    FAQ.md region must stay in sync with the feed, or a portfolio wording
    change eventually breaks validate_index.py's verbatim check."""

    def test_overlapping_snippet_synced_non_overlapping_untouched(self) -> None:
        self.run_main()
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        snippets = {item["question"]: item for item in data["aeo"]["answerSnippets"]}

        overlapping = snippets["Home question one?"]
        self.assertEqual(overlapping["answer"], "Home answer one.")
        # sources are repo-authored and must never be touched by derive.
        self.assertEqual(overlapping["sources"], ["https://example.test/faq"])

        untouched = snippets["Repo-only question?"]
        self.assertEqual(
            untouched["answer"],
            "This answer is entirely repo-authored and must never change.",
        )
        self.assertEqual(untouched["sources"], ["https://example.test/repo-only"])

    def test_feed_answer_change_propagates_and_stays_verbatim_in_faq(self) -> None:
        feed = json.loads(self.feed_path.read_text(encoding="utf-8"))
        for item in feed["faq"]:
            if item["question"] == "Home question one?":
                item["answer"] = "Home answer one, now reworded by the portfolio."
        self.feed_path.write_text(json.dumps(feed), encoding="utf-8")

        self.assertEqual(self.run_main(), 0)

        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        snippets = {item["question"]: item for item in data["aeo"]["answerSnippets"]}
        updated_answer = snippets["Home question one?"]["answer"]
        self.assertEqual(updated_answer, "Home answer one, now reworded by the portfolio.")

        # validate-style verbatim check (mirrors validate_index.py's
        # check_aeo_coverage): every answerSnippet answer must appear
        # byte-for-byte inside the visible FAQ.md text.
        faq_text = self.faq_path.read_text(encoding="utf-8")
        self.assertIn(updated_answer, faq_text)


class ValidationErrorRoutingTests(DeriveTestCase):
    """Finding B: a fetched-but-contract-invalid feed must fail loudly and
    immediately (exit 2), never absorbed by the staleness fallback - even
    when a perfectly fresh last-good snapshot exists."""

    def _args_for(self, feed_path: Path) -> list[str]:
        return [
            "--feed-file", str(feed_path),
            "--snapshot", str(self.snapshot_path),
            "--faq-md", str(self.faq_path),
            "--proof-md", str(self.proof_path),
            "--recruiter-md", str(self.recruiter_path),
            "--index-json", str(self.index_path),
        ]

    def _write_fresh_snapshot(self) -> str:
        feed = json.loads(self.feed_path.read_text(encoding="utf-8"))
        normalized = derive.normalize_feed(feed)
        fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        payload = json.dumps({"fetchedAt": fresh, "feed": normalized}, indent=2) + "\n"
        self.snapshot_path.write_text(payload, encoding="utf-8")
        return payload

    def test_structurally_invalid_feed_exits_two_immediately_even_with_fresh_snapshot(self) -> None:
        before = self._write_fresh_snapshot()

        invalid_feed = json.loads(self.feed_path.read_text(encoding="utf-8"))
        del invalid_feed["availability"]["headline"]
        invalid_path = self.work_dir / "invalid-feed.json"
        invalid_path.write_text(json.dumps(invalid_feed), encoding="utf-8")

        exit_code = derive.main(self._args_for(invalid_path))

        self.assertEqual(exit_code, 2)
        # Nothing was overwritten - not even the (fresh, otherwise-usable)
        # snapshot - because this is not routed through the fallback.
        self.assertEqual(before, self.snapshot_path.read_text(encoding="utf-8"))

    def test_network_style_fetch_failure_still_uses_staleness_fallback(self) -> None:
        # Sanity check that splitting the two failure modes didn't disturb
        # the other one: a genuine fetch failure must still use the
        # staleness budget as before.
        self._write_fresh_snapshot()
        missing_feed = self.work_dir / "does-not-exist.json"

        exit_code = derive.main(self._args_for(missing_feed))

        self.assertEqual(exit_code, 0)


class MarkerBreakoutTests(DeriveTestCase):
    """Finding C: feed content that contains literal marker comment text
    must never corrupt the marker structure, and a file that is already
    corrupted must fail loudly rather than silently guessing."""

    def _use_hostile_feed(self) -> None:
        shutil.copy(FIXTURES / "feed-hostile.json", self.feed_path)

    def test_marker_bearing_feed_content_stays_idempotent(self) -> None:
        self._use_hostile_feed()

        self.assertEqual(self.run_main(), 0)
        faq_after_first = self.faq_path.read_text(encoding="utf-8")

        real_begin = (
            "<!-- BEGIN DERIVED: faq (from https://www.marksiazon.dev/"
            "llms-index.json - do not hand-edit) -->"
        )
        real_end = "<!-- END DERIVED: faq -->"
        # Exactly one real marker pair remains - the injected text did not
        # create extra ones.
        self.assertEqual(faq_after_first.count(real_begin), 1)
        self.assertEqual(faq_after_first.count(real_end), 1)
        self.assertLess(faq_after_first.index(real_begin), faq_after_first.index(real_end))
        # The injected marker text survived, but neutralized (entity-escaped).
        self.assertIn("&lt;!-- BEGIN DERIVED: faq", faq_after_first)
        self.assertIn("&lt;!-- END DERIVED: faq", faq_after_first)
        self.assertIn("injected text", faq_after_first)

        # aeo.answerSnippets stays in verbatim sync even for hostile content.
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        snippet_answer = next(
            item["answer"]
            for item in data["aeo"]["answerSnippets"]
            if item["question"] == "Home question one?"
        )
        self.assertIn(snippet_answer, faq_after_first)

        self.assertEqual(self.run_main(), 0)
        faq_after_second = self.faq_path.read_text(encoding="utf-8")
        self.assertEqual(faq_after_first, faq_after_second)

    def test_pre_corrupted_file_fails_loudly(self) -> None:
        # Simulate a file that is already corrupted (e.g. from an
        # injection before this fix existed): two BEGIN markers for the
        # same section.
        text = self.faq_path.read_text(encoding="utf-8")
        begin = (
            "<!-- BEGIN DERIVED: faq (from https://www.marksiazon.dev/"
            "llms-index.json - do not hand-edit) -->"
        )
        corrupted = text.replace(begin, begin + "\n" + begin, 1)
        self.assertNotEqual(text, corrupted)
        self.faq_path.write_text(corrupted, encoding="utf-8")

        with self.assertRaises(derive.MarkerCorruptionError):
            self.run_main()


class MarkdownInjectionTests(DeriveTestCase):
    """Finding D: feed strings placed into markdown tables/headings must be
    escaped, or a stray '|' or newline corrupts the surrounding table."""

    def test_hostile_feed_strings_do_not_corrupt_tables_or_headings(self) -> None:
        shutil.copy(FIXTURES / "feed-hostile.json", self.feed_path)

        self.assertEqual(self.run_main(), 0)
        proof_text = self.proof_path.read_text(encoding="utf-8")

        # Pipe in a table cell is escaped, not a new column; newline is
        # collapsed, not a broken row.
        self.assertIn("| Gate \\| With Pipe | QA | Open |", proof_text)
        self.assertNotIn("Gate | With Pipe |", proof_text)

        # A newline in a heading-line value is collapsed to a single line
        # (pipes are left alone here - only table cells need pipe-escaping;
        # a literal '|' in a heading doesn't corrupt anything).
        self.assertIn(
            "#### Hostile | Title With Newline (https://example.test/projects/hostile-project)",
            proof_text,
        )
        self.assertNotIn("Hostile | Title\nWith Newline", proof_text)


class FeedUnchangedSkipTests(DeriveTestCase):
    """Finding E: an unchanged feed must not churn the snapshot's fetchedAt
    on every run, or dev/main never converge on daily promotion."""

    def test_unchanged_feed_within_heartbeat_budget_skips_snapshot_write(self) -> None:
        self.run_main()
        before = self.snapshot_path.read_text(encoding="utf-8")

        exit_code = self.run_main()

        self.assertEqual(exit_code, 0)
        after = self.snapshot_path.read_text(encoding="utf-8")
        # Byte-identical: fetchedAt was NOT rewritten for an unchanged feed.
        self.assertEqual(before, after)

    def test_unchanged_feed_past_heartbeat_budget_refreshes_fetched_at_only(self) -> None:
        feed = json.loads(self.feed_path.read_text(encoding="utf-8"))
        normalized = derive.normalize_feed(feed)
        stale_heartbeat = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        self.snapshot_path.write_text(
            json.dumps({"fetchedAt": stale_heartbeat, "feed": normalized}, indent=2) + "\n",
            encoding="utf-8",
        )

        exit_code = self.run_main()

        self.assertEqual(exit_code, 0)
        after = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(after["feed"], normalized)
        self.assertNotEqual(after["fetchedAt"], stale_heartbeat)
        self.assertFalse(derive.snapshot_is_stale(after["fetchedAt"], datetime.now(timezone.utc), 1))

    def test_changed_feed_always_writes_fresh_snapshot(self) -> None:
        feed = json.loads(self.feed_path.read_text(encoding="utf-8"))
        normalized = derive.normalize_feed(feed)
        fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        old_normalized = copy.deepcopy(normalized)
        old_normalized["availability"]["headline"] = "Old headline before this run"
        self.snapshot_path.write_text(
            json.dumps({"fetchedAt": fresh, "feed": old_normalized}, indent=2) + "\n",
            encoding="utf-8",
        )

        self.run_main()

        after = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(after["feed"], normalized)
        self.assertNotEqual(after["fetchedAt"], fresh)


class CheckRobustnessTests(DeriveTestCase):
    """Finding F: --check must validate the snapshot structurally (no raw
    KeyError tracebacks) and treat a stale fetchedAt as a visible failure."""

    def test_check_fails_loudly_on_malformed_snapshot_instead_of_crashing(self) -> None:
        malformed_feed = {
            "entity": {"name": "X"},
            "availability": {"headline": "H"},
            "projects": [],
            "faq": [],
            "proof": {"gates": [{}], "byProject": {}},
        }
        payload = {"fetchedAt": datetime.now(timezone.utc).isoformat(), "feed": malformed_feed}
        self.snapshot_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        exit_code = self.run_check()

        self.assertEqual(exit_code, 1)

    def test_check_fails_on_stale_fetched_at(self) -> None:
        self.run_main()
        snapshot = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        snapshot["fetchedAt"] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        self.snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

        exit_code = self.run_check()

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
