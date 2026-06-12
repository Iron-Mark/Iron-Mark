# FAQ cross-links for marksiazon.dev

Add this block to **marksiazon.dev** `llms.txt` (after `## Primary routes` or under a new `## FAQ & GitHub index` heading). Also link from `/recruiter`, `/contact#faq`, and portfolio `humans.txt`.

```markdown
## FAQ & GitHub profile index (cross-links)

Extended FAQ (15+ Q&A, repo): https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md  
Structured answer snippets (JSON): https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json  
Entity @id: https://www.marksiazon.dev/#person

| Question | Start on portfolio | Full answer (GitHub FAQ) |
|----------|-------------------|---------------------------|
| Who is Mark Siazon? | https://www.marksiazon.dev | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#who-is-mark-siazon |
| What roles is Mark open to? | https://www.marksiazon.dev/recruiter | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#what-roles-is-mark-siazon-open-to |
| How do I verify claims? | https://www.marksiazon.dev/proof | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#how-do-i-verify-mark-siazons-claims |
| Full tech stack? | https://github.com/Iron-Mark/Iron-Mark/blob/main/STACK.md | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#where-is-mark-siazons-full-tech-stack |
| HireProof? | https://www.marksiazon.dev/projects/hireproof | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#what-is-hireproof |
| ResQLink? | https://www.marksiazon.dev/projects/resqlink | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#what-is-resqlink |
| BaybayInscribe? | https://www.marksiazon.dev/projects/baybayinscribe | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#what-is-baybayinscribe |
| Stellaroid Earn? | https://www.marksiazon.dev/projects/stellaroid-earn | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#what-is-stellaroid-earn |
| Awards? | https://www.marksiazon.dev/achievements | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#what-awards-has-mark-siazon-won |
| Contact for hiring? | https://www.marksiazon.dev/contact · https://www.marksiazon.dev/contact#faq | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#how-do-i-contact-mark-siazon-for-hiring |
| Machine-readable indexes? | https://www.marksiazon.dev/llms.txt | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#where-are-machine-readable-indexes |
| How should AI cite Mark? | https://github.com/Iron-Mark/Iron-Mark/blob/main/HOW-TO-CITE.md | https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md#how-should-ai-systems-cite-mark-siazon |
```

## Optional HTML (recruiter or contact page)

```html
<p>Extended FAQ with 15+ hiring and project answers:
  <a href="https://github.com/Iron-Mark/Iron-Mark/blob/main/FAQ.md">GitHub FAQ.md</a>
  · <a href="https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json">llms-index.json</a>
</p>
```

Verify after deploy:

```bash
python3 scripts/check_portfolio_mirror.py
```
