from __future__ import annotations

import unittest
from pathlib import Path

from src.scripts.generate_activity_graph import contribution_color, render_svg


class ContributionColorTests(unittest.TestCase):
    def test_fixed_thresholds_do_not_recolor_old_days(self) -> None:
        self.assertEqual(contribution_color(0), "#161B22")
        self.assertEqual(contribution_color(1), "#3B1D5A")
        self.assertEqual(contribution_color(3), "#5B21B6")
        self.assertEqual(contribution_color(6), "#7C3AED")
        self.assertEqual(contribution_color(10), "#A78BFA")


class RenderSvgTests(unittest.TestCase):
    def test_renders_static_accessible_calendar(self) -> None:
        calendar = {
            "totalContributions": 4,
            "weeks": [
                {
                    "contributionDays": [
                        {"date": "2026-08-30", "contributionCount": 0, "weekday": 0},
                        {"date": "2026-08-31", "contributionCount": 4, "weekday": 1},
                    ]
                }
            ],
        }

        svg = render_svg("Iron-Mark", calendar)

        self.assertIn('aria-labelledby="activity-title activity-desc"', svg)
        self.assertIn("4 contributions during the last year", svg)
        self.assertIn("2026-08-31: 4 contributions", svg)
        self.assertNotIn("<script", svg)
        self.assertNotIn("javascript:", svg)

    def test_escapes_untrusted_login_text(self) -> None:
        svg = render_svg('<script>alert("x")</script>', {"totalContributions": 0, "weeks": []})

        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)


class WorkflowWiringTests(unittest.TestCase):
    def test_workflow_uses_github_native_generator(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github/workflows/update-github-stats.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("src/scripts/generate_activity_graph.py", workflow)
        self.assertNotIn("github-readme-activity-graph.vercel.app/graph", workflow)


if __name__ == "__main__":
    unittest.main()
