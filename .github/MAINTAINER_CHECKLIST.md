# Maintainer checklist

Internal checklist for refreshing production branch settings, Pages, stats, and portfolio mirrors. Keep this file out of `README.md`; the profile README is production-facing.

## Required live maintenance

- [x] **Branch workflow:** develop on `dev`; merge `dev` -> `main` through a PR after validation
- [x] **Branch protection:** `main` requires PR + `validate` status check; force pushes/deletion disabled
- [x] **GitHub Pages:** Settings -> Pages -> Source **GitHub Actions**
- [x] **Run workflow:** Deploy GitHub Pages mirror
- [x] **Verify Pages mirror:** https://iron-mark.github.io/Iron-Mark/llms.txt returns content
- [ ] **Run workflow:** Update GitHub Stats (workflow now stages generated widgets on `dev`; merge to `main` by PR)
- [x] **Portfolio mirror:** paste [`src/portfolio-sync/marksiazon-dev-llms-snippet.md`](../src/portfolio-sync/marksiazon-dev-llms-snippet.md) into marksiazon.dev `llms.txt` (includes Person/FAQ JSON-LD links)
- [x] **Verify portfolio mirror:** `python3 src/scripts/check_portfolio_mirror.py`

## Optional polish

- [ ] Repo About + topics
- [ ] Social preview image
- [ ] Pin 6 profile repos
- [ ] LinkedIn headline sync
- [ ] **MCP local:** `pip install -e src/mcp-server/` and `python3 src/scripts/test_mcp_server.py`
- [ ] **MCP HTTP:** `docker compose -f src/mcp-server/docker-compose.yml up`
- [ ] **Wikidata:** follow `public/schema/WIKIDATA.md`
- [ ] **Cursor MCP:** copy `src/mcp-server/mcp-config.example.json`

## Automatic on `main`

| Workflow | When |
|----------|------|
| Validate index | Every PR/push |
| Generate schema graphs | Every PR/push via Validate index |
| MCP e2e | MCP or index changes |
| Bump index dates | Index file changes on `main` |
| Link QA | Monthly (1st, 08:00 UTC) |
| Update GitHub Stats | Daily 06:00 UTC to `dev`; release through PR |
| Deploy Pages | Push to `main` |

## Quick verify commands

```bash
python3 src/scripts/validate_index.py
python3 src/scripts/validate_pages_mirror.py
python3 src/scripts/link_qa.py
python3 src/scripts/check_portfolio_mirror.py
curl -sI https://iron-mark.github.io/Iron-Mark/llms.txt | head -3
```

## Layout reference

See [docs/STRUCTURE.md](../docs/STRUCTURE.md) and setup details in [REPO_SETUP.md](REPO_SETUP.md).
