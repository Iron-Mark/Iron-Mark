#!/usr/bin/env python3
"""Generate a static contribution graph from GitHub's own GraphQL API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from html import escape
from pathlib import Path
from typing import Any, Callable


GRAPHQL_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            weekday
          }
        }
      }
    }
  }
}
"""

COLORS = ("#161B22", "#3B1D5A", "#5B21B6", "#7C3AED", "#A78BFA")


def contribution_color(count: int) -> str:
    if count <= 0:
        return COLORS[0]
    if count <= 2:
        return COLORS[1]
    if count <= 5:
        return COLORS[2]
    if count <= 9:
        return COLORS[3]
    return COLORS[4]


def fetch_calendar(
    login: str,
    token: str,
    *,
    attempts: int = 3,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    """Fetch a contribution calendar, retrying only transient request failures."""
    payload = json.dumps({"query": QUERY, "variables": {"login": login}}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Iron-Mark-profile-automation",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with opener(request, timeout=20) as response:  # noqa: S310
                result = json.loads(response.read().decode("utf-8"))
            if result.get("errors"):
                raise RuntimeError(f"GitHub GraphQL errors: {result['errors']}")
            calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            if not isinstance(calendar.get("weeks"), list):
                raise RuntimeError("GitHub response did not contain contribution weeks")
            return calendar
        except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)

    raise RuntimeError(f"GitHub contribution calendar failed after {attempts} attempts: {last_error}")


def render_svg(login: str, calendar: dict[str, Any]) -> str:
    """Render GitHub contribution-calendar data as a safe, static SVG."""
    weeks = calendar.get("weeks", [])
    total = int(calendar.get("totalContributions", 0))
    width = 820
    height = 168
    left = 42
    top = 47
    cell = 10
    gap = 3
    step = cell + gap
    safe_login = escape(login)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="activity-title activity-desc">',
        f'  <title id="activity-title">{safe_login} contribution activity</title>',
        f'  <desc id="activity-desc">{total} contributions during the last year, generated from the GitHub GraphQL API.</desc>',
        '  <rect width="100%" height="100%" rx="8" fill="#0B0F14"/>',
        f'  <text x="16" y="24" fill="#E5E7EB" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="600">{safe_login} contribution activity</text>',
        f'  <text x="804" y="24" fill="#A78BFA" font-family="Segoe UI,Arial,sans-serif" font-size="12" text-anchor="end">{total} contributions</text>',
    ]

    month_labels: list[tuple[int, str]] = []
    previous_month = ""
    for week_index, week in enumerate(weeks):
        days = week.get("contributionDays", []) if isinstance(week, dict) else []
        if days:
            date = str(days[0].get("date", ""))
            month = date[5:7] if len(date) >= 7 else ""
            if month and month != previous_month:
                month_name = (
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                )[int(month) - 1]
                month_labels.append((week_index, month_name))
                previous_month = month

        for day in days:
            weekday = int(day.get("weekday", 0))
            count = max(0, int(day.get("contributionCount", 0)))
            date = escape(str(day.get("date", "unknown date")))
            x = left + week_index * step
            y = top + weekday * step
            noun = "contribution" if count == 1 else "contributions"
            lines.extend(
                [
                    f'  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{contribution_color(count)}">',
                    f'    <title>{date}: {count} {noun}</title>',
                    "  </rect>",
                ]
            )

    for week_index, label in month_labels:
        x = left + week_index * step
        if x <= width - 35:
            lines.append(
                f'  <text x="{x}" y="40" fill="#9CA3AF" font-family="Segoe UI,Arial,sans-serif" font-size="9">{label}</text>'
            )

    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = top + weekday * step + 8
        lines.append(
            f'  <text x="34" y="{y}" fill="#6B7280" font-family="Segoe UI,Arial,sans-serif" font-size="8" text-anchor="end">{label}</text>'
        )

    lines.extend(
        [
            '  <text x="640" y="155" fill="#6B7280" font-family="Segoe UI,Arial,sans-serif" font-size="9">Less</text>',
            *[
                f'  <rect x="{668 + index * 14}" y="147" width="10" height="10" rx="2" fill="{color}"/>'
                for index, color in enumerate(COLORS)
            ],
            '  <text x="804" y="155" fill="#6B7280" font-family="Segoe UI,Arial,sans-serif" font-size="9" text-anchor="end">More</text>',
            "</svg>",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", default="Iron-Mark")
    parser.add_argument("--output", required=True)
    parser.add_argument("--input-json", help="Offline contributionCalendar JSON for tests/debugging")
    args = parser.parse_args(argv)

    if args.input_json:
        calendar = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            print("::error::GH_TOKEN or GITHUB_TOKEN is required", file=sys.stderr)
            return 2
        try:
            calendar = fetch_calendar(args.login, token)
        except RuntimeError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1

    Path(args.output).write_text(render_svg(args.login, calendar), encoding="utf-8", newline="\n")
    print(f"Wrote {args.output} from GitHub's contribution calendar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
