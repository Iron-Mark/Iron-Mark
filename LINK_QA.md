# Link QA Report

**Date:** 2026-06-10 (updated post stack split + BaybayInscribe swap)  
**Scope:** `README.md`, `STACK.md`, `llms.txt`, `llms-full.txt`, `humans.txt`, `sitemap.xml`, `LICENSE.md`  
**Method:** Extract unique `http`/`https`/`mailto` URLs; verify with `curl -L -I` (15s timeout, parallel checks).

## Summary

| Metric | Count |
|--------|------:|
| Unique URLs extracted | 86 |
| HTTP/HTTPS URLs checked | 86 |
| Passing (2xx/3xx) | 78 |
| Pre-merge 404s (branch not on `main` yet) | 6 |
| Bot / anti-scrape (LinkedIn, TikTok) | 2 |
| Broken external links | **0** |
| STACK.md external doc links (32) | **32/32 OK** |

## Changes since last audit

| Fix | Files |
|-----|-------|
| Added `STACK.md` to audit scope | 32 third-party doc links verified |
| Removed duplicate BaybayInscribe from Hackathon table | `README.md`, `llms.txt`, `llms-full.txt` |
| Aligned qwen-ui-lab canonical URL to portfolio case study | `README.md`, `llms.txt`, `llms-full.txt` |
| Restored grouped tool keyword list in `llms-full.txt` | points to STACK.md for icons + doc links |

## Remaining issues (manual review)

### Pre-merge 404s (6) — expected until branch merges to `main`

These URLs are correct canonical targets but return **404** today because index files exist on branch `cursor/profile-readme-improvements-dcf2` only:

- `https://github.com/Iron-Mark/Iron-Mark/blob/main/STACK.md`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/llms.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-full.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/humans.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/robots.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/sitemap.xml`

**Action:** Re-run link check after merging to `main`.

### Bot / anti-scrape protection (2)

- `https://www.linkedin.com/in/mark-siazon/` — HTTP **999** to automated HEAD requests; works in browsers.
- `https://www.tiktok.com/@iron_markk` — HTTP **403** to automated HEAD requests; works in browsers.

## Verification notes

- All portfolio routes on `marksiazon.dev` returned **200** (including `/projects/qwen-ui-lab`, `/projects/baybayinscribe`).
- All third-party project live demos (Vercel, HireProof, Stellaroid, qwen-ui-lab, etc.) returned **200**.
- All `STACK.md` getting-started / doc links returned **200**.
- All relative `assets/` paths in `README.md` and `STACK.md` resolve on disk (0 missing files).
- `mailto:marksiazon.dev@gmail.com` present in README and index files; not modified.
