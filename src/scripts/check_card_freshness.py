from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone


# Per-card staleness budgets in days.
#
# The failure this guards against is a SILENT freeze. When GitHub's GraphQL
# returns RESOURCE_LIMITS_EXCEEDED - a recurring condition on this account -
# the keep-last-good guards in update-github-stats.yml restore the previously
# committed card and the workflow still reports success. The published numbers
# then stop moving with nothing failing anywhere, which is invisible until
# somebody happens to look at the profile.
#
# Budgets come from the observed cadence on dev (2026-07): stats,
# activity-graph, and streak commit every day, while top-langs only changes
# when the language mix shifts and was legitimately unchanged for four days.
# For calibration, the streak.svg corruption introduced on 2026-07-21 left that
# card frozen for six days - a three-day budget surfaces that on day three.
CARD_MAX_AGE_DAYS: dict[str, int] = {
    "assets/github/stats.svg": 3,
    "assets/github/activity-graph.svg": 3,
    "assets/github/streak.svg": 3,
    "assets/github/top-langs.svg": 14,
}


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp, accepting the trailing 'Z' the API returns."""
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def stale_cards(
    now: datetime, last_commits: dict[str, str | None]
) -> list[tuple[str, float, int]]:
    """Return (path, age_days, budget_days) for every card past its budget.

    A card with no recorded commit date counts as stale: either the path is
    wrong or it has never been published, and both need a human.
    """
    findings: list[tuple[str, float, int]] = []

    for path, budget in sorted(CARD_MAX_AGE_DAYS.items()):
        raw = last_commits.get(path)
        if not raw:
            findings.append((path, float("inf"), budget))
            continue

        age = (now - parse_iso(raw)) / timedelta(days=1)
        if age > budget:
            findings.append((path, age, budget))

    return findings


def main(argv: list[str]) -> int:
    """Exit 1 when any card has outlived its staleness budget.

    Takes `path=<iso-timestamp>` pairs, so the workflow can feed it the last
    commit date of each card straight from the API, plus an optional
    `--now=<iso-timestamp>` for deterministic testing.
    """
    now = datetime.now(timezone.utc)
    last_commits: dict[str, str | None] = {}

    for argument in argv[1:]:
        if argument.startswith("--now="):
            now = parse_iso(argument.split("=", 1)[1])
            continue
        path, _, timestamp = argument.partition("=")
        last_commits[path.strip()] = timestamp.strip() or None

    findings = stale_cards(now, last_commits)
    if not findings:
        print(
            f"check_card_freshness: all {len(CARD_MAX_AGE_DAYS)} cards refreshed "
            "within their budgets."
        )
        return 0

    for path, age, budget in findings:
        age_text = "never published" if age == float("inf") else f"{age:.1f} days old"
        print(
            f"::error::{path} has stopped refreshing ({age_text}, budget {budget} "
            "days). The card generator is most likely erroring and the "
            "keep-last-good guard is republishing the previous card, so the "
            "profile numbers are frozen."
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
