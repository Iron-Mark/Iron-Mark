from __future__ import annotations

import sys


# Every path the two daily automation workflows can commit. This is an
# exact-match set rather than a list of directory prefixes on purpose: a
# prefix rule such as "assets/github" would also accept a hand-written
# "assets/github-notes.md" and silently promote human work to main.
#
# Note the list is WIDER than the workflows' `git add` lines: daily_freshness.py
# stages with `git add -A` inside its regeneration fixpoint loop, so the
# freshness commit also carries files the workflow never names explicitly
# (llms.txt and public/PROFILE.md, both rewritten by bump_index_dates.py).
# Omitting those would make every promotion look human-owned and quietly
# disable this automation, which is exactly how the profile went stale before.
#
# test_check_promotion_scope.py asserts the `git add` lines stay a subset of
# this set, so extending a cron without listing the new file here fails CI.
AUTOMATION_PATHS = frozenset(
    {
        # .github/workflows/update-github-stats.yml
        "assets/github/stats.svg",
        "assets/github/top-langs.svg",
        "assets/github/activity-graph.svg",
        "assets/github/streak.svg",
        # .github/workflows/bump-index-date.yml
        "llms-index.json",
        "robots.txt",
        "sitemap.xml",
        "public/FAQ.md",
        "public/PROOF.md",
        "public/RECRUITER.md",
        "src/data/portfolio-feed.snapshot.json",
        "public/llms-full.txt",
        "public/llms-ctx-full.txt",
        "public/schema/llms-index.schema.json",
        "public/schema/person.jsonld",
        "public/schema/faq.jsonld",
        "docs/index.html",
        "src/portfolio-sync/marksiazon-dev-llms-snippet.md",
        "src/portfolio-sync/faq-crosslinks.md",
        # Swept in by daily_freshness.py's `git add -A` (see note above).
        "llms.txt",
        "public/PROFILE.md",
    }
)


# What the rendered GitHub profile actually shows. These four SVGs are
# self-contained - nothing is generated from them and no other tracked file
# embeds their contents - so they can be promoted to main on their own without
# leaving it internally inconsistent. That makes them a safe fallback when a
# full promotion is blocked by human work waiting on dev, which would otherwise
# freeze the visible profile numbers for as long as that work takes.
PROFILE_CARD_PATHS = (
    "assets/github/stats.svg",
    "assets/github/top-langs.svg",
    "assets/github/activity-graph.svg",
    "assets/github/streak.svg",
)


def normalize(paths) -> list[str]:
    """Drop blank entries and surrounding whitespace, de-duplicated + sorted."""
    return sorted({path.strip() for path in paths if path.strip()})


def foreign_paths(paths) -> list[str]:
    """Return the changed paths that the daily automation does not own."""
    return sorted(set(normalize(paths)) - AUTOMATION_PATHS)


def main(argv: list[str]) -> int:
    """Exit 0 when every changed path is automation-owned, 1 otherwise.

    Reads paths from argv, or from stdin (one per line) when none are given,
    so the workflow can pipe `git diff --name-only` straight in.

    `--print-cards` instead emits the profile card paths, which the workflow
    uses for its cards-only fallback promotion.
    """
    args = argv[1:]
    if args and args[0] == "--print-cards":
        for path in PROFILE_CARD_PATHS:
            print(path)
        return 0

    raw = args if args else sys.stdin.read().splitlines()
    changed = normalize(raw)
    if not changed:
        print("check_promotion_scope: no differences between main and dev.")
        return 0

    foreign = foreign_paths(changed)
    if foreign:
        print(
            "check_promotion_scope: dev carries changes automation does not own, "
            "so the promotion belongs to manual review:"
        )
        for path in foreign:
            print(f"  - {path}")
        return 1

    print(
        f"check_promotion_scope: all {len(changed)} changed path(s) are "
        "automation-owned; safe to promote unattended."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
