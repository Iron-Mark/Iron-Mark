# Link QA Report

**Date:** 2026-06-10  
**Scope:** `README.md`, `llms.txt`, `llms-full.txt`, `humans.txt`, `sitemap.xml`  
**Method:** Extract unique `http`/`https`/`mailto` URLs; verify with `curl -L -I` (15s connect / 30s total timeout).

## Summary

| Metric | Count |
|--------|------:|
| Unique URLs extracted | 101 |
| HTTP/HTTPS URLs checked | 97 |
| `mailto:` links (skipped HEAD check) | 4 |
| XML namespace URI (non-navigable, skipped) | 1 |
| Fixes applied in source files | 18 |
| Remaining issues for manual review | 9 |

## Fixes applied

### README.md (13)

| Old URL | New canonical URL | Reason |
|---------|-------------------|--------|
| `https://en.bem.info/methodology/quick-start/` | `https://en.bem.info/` | 404 |
| `https://docs.anthropic.com/en/docs/claude-code/quickstart` | `https://code.claude.com/docs/en/quickstart` | 301 redirect |
| `https://docs.replit.com/getting-started/intro-replit` | `https://docs.replit.com/build/welcome` | 308 redirect |
| `https://goodtolivepodcast.com` | `https://www.goodtolivepodcast.com` | 308 redirect |
| `https://kiro.dev/docs/getting-started` | `https://kiro.dev/docs/` | 301 redirect |
| `https://movementnetwork.xyz/` | `https://www.movementnetwork.xyz/` | 308 redirect |
| `https://soliditylang.org/` | `https://www.soliditylang.org/` | 301 redirect |
| `https://tailwindcss.com/docs/installation` | `https://tailwindcss.com/docs/installation/using-vite` | 307 redirect |
| `https://v0.dev/docs` | `https://v0.app/docs` | 308 redirect |
| `https://www.freighter.app/` | `https://freighter.app/` | 301 redirect |
| `https://www.opera.com/products/minipay` | `https://minipay.to/` | 301 redirect |
| `https://phaser.io/` | `https://phaser.io/download` | 403 to bots on homepage; `/download` returns 200 |
| — | Added `rel="noopener noreferrer"` | 68 external `https` anchor tags outside GitHub Activity section |

GitHub Activity section was left unchanged per task constraints.

### llms-full.txt (5)

| Change | Reason |
|--------|--------|
| `Hackathon-Stellar-PalengkePay-Pro` → `polsalarm/PalengkePay-Pro` | Original repo 404; team repo verified 200 |
| Removed `Hackathon-MiniPay` repo line | Repo 404; no public GitHub proof listed on portfolio |
| Removed `beta.baybayinscribe.top` | DNS/connection failure (timeout) |
| Removed `KpG782/devcamp` Pulse repo | Repo 404; portfolio notes private source not advertised |
| `goodtolivepodcast.com` → `www.goodtolivepodcast.com` | 308 redirect |

## Remaining issues (manual review)

### Pre-merge 404s (8) — expected until index files land on `main`

These URLs are correct canonical targets but return **404** today because `llms.txt`, `llms-full.txt`, `humans.txt`, `robots.txt`, and `sitemap.xml` exist on branch `cursor/profile-readme-improvements-dcf2` only (`origin/main` currently has `README.md` + `assets/`).

- `https://github.com/Iron-Mark/Iron-Mark/blob/main/llms.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-full.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/humans.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/robots.txt`
- `https://github.com/Iron-Mark/Iron-Mark/blob/main/sitemap.xml`
- `https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/llms.txt`
- `https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/llms-full.txt`
- `https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/humans.txt`

**Action:** Re-run link check after merging this branch to `main`.

### Bot / anti-scrape protection (1)

- `https://www.linkedin.com/in/mark-siazon/` — returns HTTP **999** to automated HEAD requests; works in browsers.

## Verification notes

- All portfolio routes on `marksiazon.dev` returned **200**.
- All third-party project live demos (Vercel, HireProof, Stellaroid, etc.) returned **200**.
- No remaining redirect chains where source URL differs from final URL after fixes.
- `mailto:marksiazon.dev@gmail.com` present in README and index files; not modified.
