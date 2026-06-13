# Post-merge checklist

Run once after merging [PR #1](https://github.com/Iron-Mark/Iron-Mark/pull/1) to `main`.

## Required (go live)

- [ ] **Merge PR #1** → `main`
- [ ] **GitHub Pages:** Settings → Pages → Source **GitHub Actions**
- [ ] **Run workflow:** Deploy GitHub Pages mirror
- [ ] **Verify Pages:** https://iron-mark.github.io/Iron-Mark/llms.txt returns content
- [ ] **Run workflow:** Update GitHub Stats (once)
- [ ] **Portfolio mirror:** paste [`src/portfolio-sync/marksiazon-dev-llms-snippet.md`](../src/portfolio-sync/marksiazon-dev-llms-snippet.md) into marksiazon.dev `llms.txt`
- [ ] **Verify mirror:** `python3 src/scripts/check_portfolio_mirror.py`

## Skipped (optional — not required)

- [ ] Repo About + topics
- [ ] Social preview image
- [ ] Pin 6 profile repos
- [ ] LinkedIn headline sync

## Optional polish

- [ ] **MCP local:** `pip install -e src/mcp-server/` · `python3 src/scripts/test_mcp_server.py`
- [ ] **MCP HTTP:** `docker compose -f src/mcp-server/docker-compose.yml up`
- [ ] **Wikidata:** follow `public/schema/WIKIDATA.md`
- [ ] **Cursor MCP:** copy `src/mcp-server/mcp-config.example.json`

## Automatic (no action after merge)

| Workflow | When |
|----------|------|
| Validate index | Every PR/push |
| MCP e2e | MCP or index changes |
| Bump index dates | Index file changes on `main` |
| Link QA | Monthly (1st, 08:00 UTC) |
| Update GitHub Stats | Daily 06:00 UTC |
| Deploy Pages | Push to `main` (after Pages enabled) |

## Quick verify commands

```bash
python3 src/scripts/validate_index.py
python3 src/scripts/link_qa.py
python3 src/scripts/check_portfolio_mirror.py   # after portfolio update
curl -sI https://iron-mark.github.io/Iron-Mark/llms.txt | head -3
```

## Layout reference

See [docs/STRUCTURE.md](../docs/STRUCTURE.md) · setup details in [REPO_SETUP.md](REPO_SETUP.md)
