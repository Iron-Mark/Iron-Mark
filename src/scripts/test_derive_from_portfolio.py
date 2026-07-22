#!/usr/bin/env python3
"""Unit tests for derive_from_portfolio.py.

Runs entirely offline against the fixtures in src/data/test-fixtures/. Never
hits the network - fetch failure is simulated with a nonexistent --feed-file
path instead of mocking urllib.

Invoke with: python -m unittest src.scripts.test_derive_from_portfolio -v
"""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
