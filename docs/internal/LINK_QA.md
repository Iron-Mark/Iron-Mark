# Link QA Report

**Last run:** 2026-06-13  
**Script:** `src/scripts/link_qa.py`  
**Scope:** external URLs in `README.md`, `public/STACK.md`, `public/FAQ.md`, `public/RECRUITER.md`, `llms.txt`, `public/llms-full.txt`, `public/schema/llms-index.schema.json`, `public/schema/person.jsonld`, `public/schema/faq.jsonld`, `humans.txt`, `sitemap.xml`, `docs/index.html`; local relative links in production-facing markdown docs.

## Latest result

| Metric | Count |
|--------|------:|
| URLs checked | 105 |
| Issues | **0** |
| Local blob verify | GitHub `public/*` paths checked on disk |
| Pre-Pages skip | `iron-mark.github.io` until Pages enabled |

Run locally:

```bash
python3 src/scripts/link_qa.py
```

## CI

- **PR/push local links:** `.github/workflows/validate-index.yml` runs `python3 src/scripts/link_qa.py --local-only`
- **Monthly:** `.github/workflows/link-qa-monthly.yml` (opens issue on failure)
- **Portfolio mirror:** `src/scripts/check_portfolio_mirror.py` (run after marksiazon.dev update)

## Known non-failures

| URL type | Behavior |
|----------|----------|
| LinkedIn / TikTok | Skipped (bot block 403/999) |
| `iron-mark.github.io/*` | Skipped until GitHub Pages enabled |
| GitHub `public/*` blob URLs | Verified via local file existence |

## History

| Date | Notes |
|------|-------|
| 2026-06-13 | Layout refactor `public/` + `src/`; 105 URLs, 0 issues |
| 2026-06-20 | Added Schema.org Person/FAQ JSON-LD and Pages index coverage |
| 2026-06-12 | Phase 1 automation; local blob check for pre-merge files |
| 2026-06-10 | Initial audit post stack split |

## Manual audit notes (2026-06-10)

- All portfolio routes on marksiazon.dev returned 200
- All STACK.md external doc links OK
- All README `assets/` paths resolve on disk
