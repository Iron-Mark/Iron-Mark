# Append to marksiazon.dev `llms.txt`

Copy the block below into **marksiazon.dev** `llms.txt` under `## Canonical sources` (or create `## GitHub profile index`).

Also add to site footer / `humans.txt` if not present.

```markdown
## GitHub profile index (Iron-Mark/Iron-Mark)

- Structured entity index (JSON): https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json
- Expanded agent context: https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-ctx-full.txt
- FAQ (15+ Q&A): https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md
- Recruiter brief (repo): https://github.com/Iron-Mark/Iron-Mark/blob/main/RECRUITER.md
- Proof map (claims → URLs): https://github.com/Iron-Mark/Iron-Mark/blob/main/PROOF.md
- Tech stack (112 tools): https://github.com/Iron-Mark/Iron-Mark/blob/main/STACK.md
- LLM manifest: https://github.com/Iron-Mark/Iron-Mark/blob/main/llms.txt
- GitHub Pages mirror: https://iron-mark.github.io/Iron-Mark/
- Visual profile README: https://github.com/Iron-Mark
```

## Optional: host copies on portfolio

For true `/llms-index.json` on your domain, add redirects or static files in the portfolio repo:

| Path | Source |
|------|--------|
| `/github-index.json` | redirect to raw GitHub `llms-index.json` |
| `/github-faq.md` | redirect to raw GitHub `FAQ.md` |

Verify after deploy:

```bash
python3 scripts/check_portfolio_mirror.py
```

## FAQ cross-links (Phase 3.4)

Also copy the FAQ table from [faq-crosslinks.md](faq-crosslinks.md) into marksiazon.dev `llms.txt` and link from `/recruiter` or `/contact#faq`.
