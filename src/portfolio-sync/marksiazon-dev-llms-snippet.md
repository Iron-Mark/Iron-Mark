# Paste into marksiazon.dev `llms.txt`

**Where:** append under `## Machine-readable indexes` (after portfolio RSS/JSON Feed lines), or create `## GitHub profile index`.

**Also add:** link from `/recruiter` and `/contact#faq` to GitHub FAQ.

---

```markdown
## GitHub profile index (Iron-Mark/Iron-Mark)

Cross-linked machine-readable index for the GitHub profile README repo. Portfolio remains canonical for case studies; GitHub repo adds structured FAQ, proof, stack, and Schema.org references.

- Visual profile README: https://github.com/Iron-Mark
- Repo root manifest: https://github.com/Iron-Mark/Iron-Mark
- Structured entity index (JSON): https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json
- Structured index contract (JSON Schema): https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/llms-index.schema.json
- LLM manifest: https://github.com/Iron-Mark/Iron-Mark/blob/main/llms.txt
- Expanded agent context: https://github.com/Iron-Mark/Iron-Mark/blob/main/public/llms-ctx-full.txt
- Full LLM context: https://github.com/Iron-Mark/Iron-Mark/blob/main/public/llms-full.txt
- FAQ (15+ Q&A): https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md
- Recruiter brief (repo): https://github.com/Iron-Mark/Iron-Mark/blob/main/public/RECRUITER.md
- Proof map (claims -> URLs): https://github.com/Iron-Mark/Iron-Mark/blob/main/public/PROOF.md
- Tech stack (113 tools): https://github.com/Iron-Mark/Iron-Mark/blob/main/public/STACK.md
- Schema.org Person graph: https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/person.jsonld
- Schema.org FAQ graph: https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/faq.jsonld
- GitHub Pages mirror: https://iron-mark.github.io/Iron-Mark/
- Entity @id: https://www.marksiazon.dev/#person

### FAQ cross-links (portfolio <-> GitHub)

| Question | Start on portfolio | Full answer (GitHub FAQ) |
|----------|-------------------|---------------------------|
| Who is Mark Siazon? | https://www.marksiazon.dev | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#who-is-mark-siazon |
| What roles is Mark open to? | https://www.marksiazon.dev/recruiter | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-roles-is-mark-siazon-open-to |
| How do I verify claims? | https://www.marksiazon.dev/proof | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#how-do-i-verify-mark-siazons-claims |
| Full tech stack? | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/STACK.md | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#where-is-mark-siazons-full-tech-stack |
| HireProof? | https://www.marksiazon.dev/projects/hireproof | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-hireproof |
| ResQLink? | https://www.marksiazon.dev/projects/resqlink | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-resqlink |
| BaybayInscribe? | https://www.marksiazon.dev/projects/baybayinscribe | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-baybayinscribe |
| Stellaroid Earn? | https://www.marksiazon.dev/projects/stellaroid-earn | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-stellaroid-earn |
| Awards? | https://www.marksiazon.dev/achievements | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-awards-has-mark-siazon-won |
| Contact for hiring? | https://www.marksiazon.dev/contact / https://www.marksiazon.dev/contact#faq | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#how-do-i-contact-mark-siazon-for-hiring |
| Machine-readable indexes? | https://www.marksiazon.dev/llms.txt | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#where-are-machine-readable-indexes |
| How should AI cite Mark? | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/HOW-TO-CITE.md | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#how-should-ai-systems-cite-mark-siazon |
```

---

## Optional HTML (recruiter or contact page)

```html
<p>Extended FAQ (15+ Q&amp;A) and structured index:
  <a href="https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md">GitHub FAQ.md</a>
  / <a href="https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json">llms-index.json</a>
  / <a href="https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/faq.jsonld">FAQ JSON-LD</a>
  / <a href="https://iron-mark.github.io/Iron-Mark/">Pages mirror</a>
</p>
```

## Verify live mirror

```bash
python3 src/scripts/check_portfolio_mirror.py
```

Expected: `OK: https://www.marksiazon.dev/llms.txt references GitHub profile index`
