#!/usr/bin/env python3
"""Single driver for the daily freshness pipeline: derive -> bump dates ->
regenerate derived files to a fixpoint -> validate.

.github/workflows/bump-index-date.yml invokes this as ONE step, so the
pipeline's actual behavior (step order, the regeneration fixpoint loop, and
which scripts it calls) lives here - in this repo's normal source tree on
`dev` - instead of being embedded directly in the workflow YAML.

Why this matters: GitHub Actions always runs a *scheduled* workflow's YAML
from the repository's default branch (main here), even though
bump-index-date.yml explicitly checks out `ref: dev` for the rest of the
job. Before this driver existed, the regeneration fixpoint loop lived
directly in the workflow YAML - so on a scheduled run, that loop's *shape*
(which scripts it calls, how many passes, in what order) always came from
main's frozen copy of the YAML, while the individual scripts it invoked
came from dev's checkout. A change to the pipeline's shape made only on dev
would silently not take effect on the schedule until promoted to main,
while a change to a script's behavior would take effect immediately - an
easy trap, and exactly the kind of main-yml-vs-dev-scripts mismatch that
made a previous incident possible.

Consolidating the pipeline body into this script means the workflow YAML
only needs a single `python3 src/scripts/daily_freshness.py` invocation;
the pipeline's actual shape now always reflects dev's checked-out copy of
*this file*, matching the checked-out scripts it calls. (The YAML file
itself is still always main's copy on a schedule - see the comment at the
top of bump-index-date.yml - but there is now almost nothing left in it
for that distinction to matter for.)

Must be run from a git working tree at the repository root: the
regeneration fixpoint loop shells out to `git diff` / `git add` to detect
stability, the same way the loop it replaces did.

Exit code is the first non-zero exit code encountered, in step order.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "src" / "scripts"

REGEN_SCRIPTS: tuple[Path, ...] = (
    SCRIPTS / "generate_llms_ctx.py",
    SCRIPTS / "generate_sitemap.py",
    SCRIPTS / "generate_schema.py",
    SCRIPTS / "build_pages_index.py",
    SCRIPTS / "generate_portfolio_sync.py",
)

# Bumped dates change the manifest files, which shifts the sha256 hashes
# embedded in person.jsonld and docs/index.html, so a single regeneration
# pass is not always a fixpoint. Cap the number of passes so a genuine
# oscillation (a bug where two scripts keep re-triggering each other)
# fails loudly instead of looping forever.
MAX_REGEN_PASSES = 5


def _run(script: Path) -> int:
    return subprocess.run([sys.executable, str(script)], cwd=ROOT).returncode


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT)


def _tree_is_clean() -> bool:
    return _git("diff", "--quiet").returncode == 0


def step_derive() -> int:
    return _run(SCRIPTS / "derive_from_portfolio.py")


def step_bump_dates() -> int:
    return _run(SCRIPTS / "bump_index_dates.py")


def step_regenerate_to_fixpoint() -> int:
    """Regenerate derived files until the tree is stable."""
    for pass_number in range(1, MAX_REGEN_PASSES + 1):
        for script in REGEN_SCRIPTS:
            exit_code = _run(script)
            if exit_code != 0:
                return exit_code
        if _tree_is_clean():
            print(f"daily_freshness: derived files stable after pass {pass_number}.")
            return 0
        _git("add", "-A")
    print(
        "::error::daily_freshness: derived files did not reach a fixpoint after "
        f"{MAX_REGEN_PASSES} passes."
    )
    return 1


def step_validate() -> int:
    return _run(SCRIPTS / "validate_index.py")


def main() -> int:
    steps: tuple[tuple[str, object], ...] = (
        ("derive", step_derive),
        ("bump dates", step_bump_dates),
        ("regenerate to fixpoint", step_regenerate_to_fixpoint),
        ("validate", step_validate),
    )
    for name, step in steps:
        exit_code = step()  # type: ignore[operator]
        if exit_code != 0:
            print(f"::error::daily_freshness: step '{name}' failed with exit code {exit_code}")
            return exit_code
    print("daily_freshness: pipeline completed ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
