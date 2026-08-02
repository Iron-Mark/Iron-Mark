# AGENTS.md — working in this repository

Instructions for any AI coding agent (Codex, Claude Code, Cursor, Copilot,
Gemini CLI, …). Read this before making changes.

> Not to be confused with **`public/AGENTS.md`**, which is published to the web
> for AI agents *reading the profile*. This file is for agents *editing the
> repo*.

## What this repo is

Mark Siazon's GitHub **profile index** — the README rendered on the profile,
plus machine-readable discovery surfaces (`llms.txt`, `llms-index.json`,
`public/FAQ.md`, `public/PROOF.md`, schema files) and a small read-only MCP
server under `src/mcp-server/`. It is **not an application codebase**. Most
content is generated or curated data, not product code.

## Identity — read this first

`gh` on the maintainer's machine silently flips to a secondary work account.
**Always confirm the active account before any push, merge, or API write:**

```sh
gh auth status
gh auth switch --user Iron-Mark   # if it is not already Iron-Mark
```

Getting this wrong once put a work identity into three repositories' history
and required full history rewrites to remove. A CI check named
**`identity-guard`** now fails any PR whose commits carry a forbidden identity
in the author, committer, or a `Co-authored-by:`/`Signed-off-by:` trailer. Its
pattern lives in the `IDENTITY_GUARD_PATTERN` secret — **never put identity
values in repo content, workflow files, docs, or PR bodies.**

**Never add AI attribution or co-authorship trailers to commits or PRs.**
No `Co-Authored-By:` lines for the agent, no "generated with" footers.

## Branch flow

`feature → dev → main`. `main` only accepts PRs from `dev` (or the
`automation/*`, `imgbot`, `dependabot/*` branches) — enforced by
`enforce-pr-flow`. Required checks on both branches: `validate`,
`enforce-pr-flow`, `identity-guard`. `enforce_admins` is on, so an admin merge
cannot bypass a check that has not reported.

## Automation (runs unattended — do not "fix" it casually)

| Workflow | Schedule | Does |
|---|---|---|
| `update-github-stats.yml` | 06:00 UTC | Regenerates the four SVG stat cards, opens + auto-merges a PR into `dev` |
| `promote-automation-to-main.yml` | 12:00 UTC | Promotes `dev → main` when the diff is automation-owned only; otherwise promotes just the stat cards |
| `bump-index-date.yml` | daily | Freshness dates across the discovery surfaces |

`src/scripts/check_promotion_scope.py` decides whether a promotion is safe.
Its allowlist is deliberately **wider** than the crons' `git add` lines because
`daily_freshness.py` stages with `git add -A`. If you change what the crons
write, update that allowlist and its tests together.

## Verify before you claim

```sh
python3 -m unittest discover -s src/scripts -p 'test_*.py'
```

The MCP server pins `mcp>=2.0,<3`. `mcp` 2.0.0 removed
`mcp.server.fastmcp`; the successor is the in-SDK `mcp.server.MCPServer`. The
separate PyPI `fastmcp` package is third-party and is **not** the successor.

## Traps that have cost real debugging time

- **Scheduled workflows always execute the DEFAULT BRANCH's YAML**, even when
  the job checks out `dev`. A workflow fix is not live until it reaches `main`.
- **PRs opened with `GITHUB_TOKEN` never fire `pull_request` checks** (GitHub
  loop prevention), so required checks sit at "expected" forever. Automation
  must use the `STATS_TOKEN` PAT.
- **Pushing with a PAT is not enough** — `actions/checkout` persists a token as
  an `http.extraheader` that outranks the URL credential. Blank it for that
  push, or the push attributes to `github-actions[bot]` and its check runs are
  created awaiting approval:
  ```sh
  git -c http.https://github.com/.extraheader= push --force \
    "https://x-access-token:${TOKEN}@github.com/${GITHUB_REPOSITORY}.git" <branch>
  ```
- **On a `dev → main` PR, `gh pr checks` is unreliable.** It reads the head
  *commit's* rollup — and that commit is `dev`'s tip, already green from its
  dev-side PR — so a wait loop passes instantly while the new PR's own runs are
  still "expected". Retry the merge itself on the "is expected" error.
- **Comparing `dev` and `main` by commit count is meaningless** after promotion
  merges. Compare trees:
  ```sh
  gh api repos/Iron-Mark/Iron-Mark/commits/main --jq '.commit.tree.sha'
  gh api repos/Iron-Mark/Iron-Mark/commits/dev  --jq '.commit.tree.sha'
  ```
  Equal hashes mean the branches agree regardless of ahead/behind.
- **CI fails on committed absolute local paths.** Never commit a
  `C:\Users\...` path.
