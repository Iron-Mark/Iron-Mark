# Append to marksiazon.dev `llms.txt`

Use the **complete ready-to-paste block**:

→ **[marksiazon-dev-llms-snippet.md](marksiazon-dev-llms-snippet.md)** (index links + FAQ cross-link table)

Also add to site footer / portfolio `humans.txt` if not present.

## Optional: host copies on portfolio

| Path | Source |
|------|--------|
| `/github-index.json` | redirect to raw GitHub `llms-index.json` |
| `/github-faq.md` | redirect to raw GitHub `public/FAQ.md` |

## Verify after deploy

```bash
python3 src/scripts/check_portfolio_mirror.py
```

See also [faq-crosslinks.md](faq-crosslinks.md) for the FAQ table in isolation.
