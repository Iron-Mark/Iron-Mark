# GitHub repo & profile setup (manual)

Run these once after merging to `main`. The cloud agent token cannot edit repo settings or user pins — **you** run these locally with `gh` auth as @Iron-Mark.

> **Skipped (optional):** repo About/topics, social preview image, and pin 6 repos — not required for index/MCP/AEO functionality.

## 1. Repository About & topics *(optional — skip if redundant)*

<details>
<summary>Only if you want extra GitHub search discoverability</summary>

```bash
gh repo edit Iron-Mark/Iron-Mark \
  --description "Product designer & full-stack developer (@Iron-Mark) — proof-backed AI, mobile & Web3 portfolio index. Philippines · llms.txt · STACK.md" \
  --add-topic product-design \
  --add-topic full-stack \
  --add-topic react \
  --add-topic nextjs \
  --add-topic flutter \
  --add-topic web3 \
  --add-topic portfolio \
  --add-topic ui-ux \
  --add-topic philippines \
  --add-topic llms-txt \
  --add-topic aeo
```

Remove stale topics if needed: `config`, `github-config`, `readme-template` (Settings → Topics).

</details>

## 2. Social preview image *(optional — skip if redundant)*

<details>
<summary>Only for branded link previews on social shares</summary>

**Settings → General → Social preview → Upload**

Use `assets/brand/banner.gif` (or a static 1280×640 PNG export) so link shares look on-brand.

</details>

## 3. Pin 6 repositories *(optional — skip if redundant)*

<details>
<summary>Profile pin alignment with Featured Work</summary>

Suggested alignment with Featured Work + lab:

1. `Iron-Mark/Iron-Mark` (this index)
2. HireProof repo (or primary HireProof org repo)
3. `Iron-Mark/qwen-ui-lab`
4. `UMakLumen/ResQLinkWeb` or team ResQLink repo
5. Stellaroid / PalengkePay team repo (`polsalarm/PalengkePay-Pro`) or `Iron-Mark/Hackathon-LexInsights`
6. `ACSADians/kudlit-app` or BaybayInscribe-related repo

Pick the six with strongest proof + recent activity.

</details>

## 4. Refresh GitHub stats widgets

After merge to `main`, run **Actions → Update GitHub Stats → Run workflow** (or wait for daily 06:00 UTC cron).

Regenerates `assets/github/stats.svg`, `top-langs.svg`, `activity-graph.svg`, `streak.svg`.

```bash
gh workflow run "Update GitHub Stats"   # after workflow exists on main
```

## 5. GitHub Pages

**Settings → Pages → Build and deployment → Source: GitHub Actions**

Then run workflow **Deploy GitHub Pages mirror** once. Live at:

https://iron-mark.github.io/Iron-Mark/

## 6. Profile README visibility

If README does not show on https://github.com/Iron-Mark:

- Repo must be **public**, named exactly `Iron-Mark`
- `README.md` on **default branch** (`main`)
- Click **Share to profile** on the repo page if prompted

## 7. Portfolio mirror (marksiazon.dev)

Copy block from [src/portfolio-sync/marksiazon-dev-append.md](../src/portfolio-sync/marksiazon-dev-append.md) into portfolio `llms.txt` and footer. Add FAQ cross-link table from [src/portfolio-sync/faq-crosslinks.md](../src/portfolio-sync/faq-crosslinks.md).

Verify with:

```bash
python3 src/scripts/check_portfolio_mirror.py
```

## 9. Wikidata entity (optional, Phase 4)

Follow [schema/WIKIDATA.md](../schema/WIKIDATA.md) to create a Wikidata item. After you receive a Q-id, add it to `schema/person.jsonld` and `llms-index.json` → `identifiers.wikidata`.

## 10. Optional MCP server (local agents)

For Cursor / Claude Desktop agent access to profile tools and resources:

```bash
pip install -e src/mcp-server/
python3 src/scripts/test_mcp_server.py
```

Config: [src/mcp-server/mcp-config.example.json](../src/mcp-server/mcp-config.example.json) · Docs: [src/mcp-server/README.md](../src/mcp-server/README.md)

## 8. LinkedIn headline sync *(optional)*

Match README one-liner:

> Product Design Engineer & Full-Stack Developer | Proof-backed AI, mobile & Web3 | Philippines & remote
