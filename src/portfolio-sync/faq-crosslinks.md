See [marksiazon-dev-llms-snippet.md](marksiazon-dev-llms-snippet.md) for the complete paste block.

```markdown
## FAQ and GitHub profile index cross-links

Extended FAQ (15+ Q&A, repo): https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md  
Structured answer snippets: https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json
FAQ schema (JSON-LD): https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/faq.jsonld
Entity @id: https://www.marksiazon.dev/#person

| Question | Start on portfolio/source | Full answer (GitHub FAQ) |
|----------|---------------------------|---------------------------|
| Who is Mark Siazon? | https://www.marksiazon.dev | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#who-is-mark-siazon |
| What roles is Mark Siazon open to? | https://www.marksiazon.dev/recruiter / https://www.marksiazon.dev/contact | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-roles-is-mark-siazon-open-to |
| Where is Mark Siazon's full tech stack? | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/STACK.md | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#where-is-mark-siazons-full-tech-stack |
| How do I verify Mark Siazon's claims? | https://www.marksiazon.dev/proof / https://www.marksiazon.dev/projects | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#how-do-i-verify-mark-siazons-claims |
| What is HireProof? | https://www.marksiazon.dev/projects/hireproof | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-hireproof |
| What is ResQLink? | https://www.marksiazon.dev/projects/resqlink / https://www.marksiazon.dev/achievements | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-resqlink |
| What is BaybayInscribe? | https://www.marksiazon.dev/projects/baybayinscribe / https://www.marksiazon.dev/achievements | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-baybayinscribe |
| What is Stellaroid Earn? | https://www.marksiazon.dev/projects/stellaroid-earn | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-is-stellaroid-earn |
| What hackathon and lab projects does Mark maintain? | https://www.marksiazon.dev/lab | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-hackathon-and-lab-projects-does-mark-maintain |
| Is Mark Siazon a designer or a developer? | https://www.marksiazon.dev/recruiter / https://www.marksiazon.dev | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#is-mark-siazon-a-designer-or-a-developer |
| What awards has Mark Siazon won? | https://www.marksiazon.dev/achievements / https://www.marksiazon.dev/projects/stellaroid-earn | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-awards-has-mark-siazon-won |
| How should Mark Siazon be cited? | https://www.marksiazon.dev/recruiter / https://www.marksiazon.dev/proof | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#how-should-mark-siazon-be-cited |
| Where are source and index files? | https://www.marksiazon.dev/llms.txt | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#where-are-source-and-index-files |
| What geographic markets does Mark serve? | https://www.marksiazon.dev/recruiter / https://www.marksiazon.dev/contact | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#what-geographic-markets-does-mark-serve |
| How do I contact Mark Siazon for hiring? | https://www.marksiazon.dev/recruiter / https://www.marksiazon.dev/contact | https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#how-do-i-contact-mark-siazon-for-hiring |
```

## Optional HTML (recruiter or contact page)

```html
<p>Extended FAQ with 15+ hiring and project answers:
  <a href="https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md">GitHub FAQ.md</a>
  / <a href="https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json">llms-index.json</a>
</p>
```

Verify live mirror:

```bash
python3 src/scripts/check_portfolio_mirror.py
```
