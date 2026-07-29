from __future__ import annotations

import io
import re
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from src.scripts.check_card_freshness import (
    CARD_MAX_AGE_DAYS,
    main,
    parse_iso,
    stale_cards,
)


NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def fresh_dates(now: datetime = NOW) -> dict[str, str]:
    """Every card committed an hour ago."""
    stamp = now.replace(hour=11).isoformat().replace("+00:00", "Z")
    return {path: stamp for path in CARD_MAX_AGE_DAYS}


class ParseIsoTests(unittest.TestCase):
    def test_accepts_the_trailing_z_the_api_returns(self):
        self.assertEqual(
            parse_iso("2026-07-29T08:00:00Z"),
            datetime(2026, 7, 29, 8, 0, tzinfo=timezone.utc),
        )

    def test_assumes_utc_when_no_offset_is_given(self):
        self.assertEqual(
            parse_iso("2026-07-29T08:00:00"),
            datetime(2026, 7, 29, 8, 0, tzinfo=timezone.utc),
        )


class StaleCardTests(unittest.TestCase):
    def test_recently_refreshed_cards_are_not_flagged(self):
        self.assertEqual(stale_cards(NOW, fresh_dates()), [])

    def test_card_past_its_budget_is_flagged(self):
        dates = fresh_dates()
        dates["assets/github/stats.svg"] = "2026-07-25T08:00:00Z"  # 4.2 days

        findings = stale_cards(NOW, dates)

        self.assertEqual([path for path, _, _ in findings], ["assets/github/stats.svg"])

    def test_card_inside_its_budget_is_not_flagged(self):
        dates = fresh_dates()
        dates["assets/github/stats.svg"] = "2026-07-27T08:00:00Z"  # 2.2 days

        self.assertEqual(stale_cards(NOW, dates), [])

    def test_top_langs_keeps_its_longer_budget(self):
        # It legitimately went four days unchanged in July; only a much longer
        # silence means something is actually wrong.
        dates = fresh_dates()
        dates["assets/github/top-langs.svg"] = "2026-07-24T08:00:00Z"  # 5.2 days

        self.assertEqual(stale_cards(NOW, dates), [])

    def test_missing_commit_date_counts_as_stale(self):
        dates = fresh_dates()
        dates["assets/github/streak.svg"] = None

        findings = stale_cards(NOW, dates)

        self.assertEqual([path for path, _, _ in findings], ["assets/github/streak.svg"])

    def test_the_july_streak_corruption_would_have_been_caught(self):
        # streak.svg was corrupted on 2026-07-21T13:57Z and republished unchanged
        # by the keep-last-good guard until 2026-07-27. The budget elapses mid-
        # afternoon on the 24th, so the daily 08:00 run that catches it is the
        # 25th's - four mornings sooner than the manual discovery on the 29th.
        run_at = datetime(2026, 7, 25, 8, 0, tzinfo=timezone.utc)
        dates = fresh_dates(run_at)
        dates["assets/github/streak.svg"] = "2026-07-21T13:57:14Z"

        findings = stale_cards(run_at, dates)

        self.assertEqual([path for path, _, _ in findings], ["assets/github/streak.svg"])

    def test_a_freeze_is_still_within_budget_on_the_first_run(self):
        # Guards against over-tightening: one missed refresh must not alarm.
        run_at = datetime(2026, 7, 24, 8, 0, tzinfo=timezone.utc)
        dates = fresh_dates(run_at)
        dates["assets/github/streak.svg"] = "2026-07-21T13:57:14Z"

        self.assertEqual(stale_cards(run_at, dates), [])


class MainTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_all_fresh_exits_zero(self):
        argv = ["prog", f"--now={NOW.isoformat()}"] + [
            f"{path}=2026-07-29T08:00:00Z" for path in CARD_MAX_AGE_DAYS
        ]

        code, output = self.run_main(argv)

        self.assertEqual(code, 0)
        self.assertIn("within their budgets", output)

    def test_stale_card_exits_one_with_an_annotation(self):
        argv = ["prog", f"--now={NOW.isoformat()}"] + [
            f"{path}=" + ("2026-07-20T08:00:00Z" if "stats" in path else "2026-07-29T08:00:00Z")
            for path in CARD_MAX_AGE_DAYS
        ]

        code, output = self.run_main(argv)

        self.assertEqual(code, 1)
        self.assertIn("::error::assets/github/stats.svg has stopped refreshing", output)

    def test_unreported_card_exits_one(self):
        # The workflow passes every card; if one goes missing that is itself a bug.
        code, output = self.run_main(["prog", f"--now={NOW.isoformat()}"])

        self.assertEqual(code, 1)
        self.assertIn("never published", output)


class WorkflowWiringTests(unittest.TestCase):
    def test_every_generated_card_has_a_budget(self):
        workflow = Path(".github/workflows/update-github-stats.yml").read_text(
            encoding="utf-8"
        )
        staged: set[str] = set()
        for line in workflow.splitlines():
            match = re.search(r"^\s*git add (.+)$", line)
            if match:
                staged.update(match.group(1).split())

        self.assertEqual(staged, set(CARD_MAX_AGE_DAYS))


if __name__ == "__main__":
    unittest.main()
