from __future__ import annotations

import io
import re
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from src.scripts.check_promotion_scope import (
    AUTOMATION_PATHS,
    PROFILE_CARD_PATHS,
    foreign_paths,
    main,
    normalize,
)


WORKFLOWS = Path(".github/workflows")


def staged_paths(workflow: str) -> set[str]:
    """Extract the paths a workflow stages via `git add`."""
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    staged: set[str] = set()
    for line in text.splitlines():
        match = re.search(r"^\s*git add (.+)$", line)
        if match:
            staged.update(match.group(1).split())
    return staged


class NormalizeTests(unittest.TestCase):
    def test_strips_blanks_and_whitespace(self):
        self.assertEqual(normalize([" robots.txt ", "", "   "]), ["robots.txt"])

    def test_deduplicates_and_sorts(self):
        self.assertEqual(
            normalize(["sitemap.xml", "robots.txt", "sitemap.xml"]),
            ["robots.txt", "sitemap.xml"],
        )


class ForeignPathTests(unittest.TestCase):
    def test_empty_diff_has_no_foreign_paths(self):
        self.assertEqual(foreign_paths([]), [])

    def test_all_automation_paths_are_owned(self):
        self.assertEqual(foreign_paths(sorted(AUTOMATION_PATHS)), [])

    def test_human_change_is_foreign(self):
        self.assertEqual(foreign_paths(["README.md"]), ["README.md"])

    def test_mixed_diff_reports_only_the_human_change(self):
        self.assertEqual(
            foreign_paths(["llms-index.json", "src/mcp-server/server.py"]),
            ["src/mcp-server/server.py"],
        )

    def test_prefix_near_miss_is_not_treated_as_automation_owned(self):
        # A directory-prefix rule would wrongly accept both of these.
        self.assertEqual(
            foreign_paths(["assets/github-notes.md", "assets/github/stats.svg.bak"]),
            ["assets/github-notes.md", "assets/github/stats.svg.bak"],
        )

    def test_workflow_file_edits_are_foreign(self):
        # Changing the automation itself must still go through review.
        self.assertEqual(
            foreign_paths([".github/workflows/bump-index-date.yml"]),
            [".github/workflows/bump-index-date.yml"],
        )


class ExitCodeTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_automation_only_diff_exits_zero(self):
        code, output = self.run_main(["prog", "llms-index.json", "robots.txt"])
        self.assertEqual(code, 0)
        self.assertIn("safe to promote", output)

    def test_human_change_exits_one_and_names_the_path(self):
        code, output = self.run_main(["prog", "llms-index.json", "README.md"])
        self.assertEqual(code, 1)
        self.assertIn("README.md", output)
        self.assertNotIn("llms-index.json", output)

    def test_empty_diff_exits_zero(self):
        code, output = self.run_main(["prog", "  "])
        self.assertEqual(code, 0)
        self.assertIn("no differences", output)


class WorkflowDriftTests(unittest.TestCase):
    """The allowlist must track what the crons actually commit.

    Without this, adding a file to a cron's `git add` would silently stop
    unattended promotion (the new path would read as a human change) and the
    profile would quietly go stale again.

    The assertion is a subset check rather than equality because
    daily_freshness.py stages with `git add -A`, so the freshness commit
    carries more than the workflow names explicitly.
    """

    def test_every_staged_path_is_allowlisted(self):
        staged = staged_paths("update-github-stats.yml") | staged_paths(
            "bump-index-date.yml"
        )
        self.assertTrue(staged, "expected both workflows to stage files")
        missing = sorted(staged - set(AUTOMATION_PATHS))
        self.assertEqual(
            missing,
            [],
            "these paths are staged by a cron but missing from AUTOMATION_PATHS",
        )

    def test_git_add_dash_a_extras_are_covered(self):
        # daily_freshness.py's `git add -A` sweeps these in even though
        # bump-index-date.yml never names them; they were observed in the
        # bot's own freshness commits.
        for path in ("llms.txt", "public/PROFILE.md"):
            self.assertIn(path, AUTOMATION_PATHS)

    def test_freshness_pipeline_still_stages_everything(self):
        # If this ever stops being true the comment above (and the two extra
        # entries) should be revisited.
        source = Path("src/scripts/daily_freshness.py").read_text(encoding="utf-8")
        self.assertIn('_git("add", "-A")', source)




class ProfileCardTests(unittest.TestCase):
    """The cards-only fallback keeps the visible profile fresh while a full
    promotion waits for review, so its path list has to stay honest."""

    def test_cards_are_a_subset_of_automation_owned_paths(self):
        self.assertEqual(sorted(set(PROFILE_CARD_PATHS) - AUTOMATION_PATHS), [])

    def test_cards_match_what_the_stats_cron_stages(self):
        # The fallback promotes exactly the cards that workflow produces; if it
        # ever generates a fifth card, this fails instead of silently leaving
        # the new one stranded on dev.
        self.assertEqual(
            set(PROFILE_CARD_PATHS),
            staged_paths("update-github-stats.yml"),
        )

    def test_print_cards_emits_one_path_per_line(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["prog", "--print-cards"])

        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().split(), list(PROFILE_CARD_PATHS))

    def test_print_cards_is_not_confused_with_a_changed_path(self):
        # Guard the argv branch: "--print-cards" must never be scanned as a diff.
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main(["prog", "--print-cards"])
        self.assertNotIn("automation-owned", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
