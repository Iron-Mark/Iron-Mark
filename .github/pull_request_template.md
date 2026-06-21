## Production gate

- [ ] This PR targets `main` only from `dev` or a short-lived branch based on `dev`.
- [ ] Production-facing README links stay limited to portfolio routes, public crawler assets, and visual assets.
- [ ] Development-only docs/tools (`.github/`, `docs/internal/`, `src/`, setup notes, MCP docs) are not linked from production surfaces.

## Generated artifacts

- [ ] `llms-index.json` is the source of truth for profile facts changed in this PR.
- [ ] Generated schema/context/Pages/sitemap/portfolio-sync files are updated when `llms-index.json` changes.
- [ ] Local validation was run where available, or CI is expected to be the validation source.

## Verification

- [ ] `Validate index` passes.
- [ ] MCP e2e is expected to pass when MCP, `public/`, scripts, or index files change.
- [ ] GitHub Pages and portfolio mirrors are verified after merge when production content changes.
