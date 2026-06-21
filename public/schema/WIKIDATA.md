# Wikidata entity - Mark Siazon

No Wikidata item exists yet for Mark Siazon (@Iron-Mark) as of 2026-06-21.

Verified with Wikidata entity search:

```text
https://www.wikidata.org/w/api.php?action=wbsearchentities&search=Mark%20Siazon&language=en&format=json
```

The API returned an empty `search` array. Creating the item still requires a logged-in Wikidata editor account; do not add a fake Q-id to this repo.

## Before Creation

1. Search https://www.wikidata.org/w/index.php?search=Mark+Siazon.
2. Confirm there is no duplicate for the product designer / full-stack developer behind `Iron-Mark` and `marksiazon.dev`.
3. Use proof URLs from [PROOF.md](../PROOF.md), [ENTITY.md](ENTITY.md), and [llms-index.json](../../llms-index.json).

## Labels

| Language | Field | Value |
|----------|-------|-------|
| en | label | Mark Siazon |
| en | description | product designer and full-stack developer from the Philippines |

## Conservative Statements

Only add statements you can verify from public sources.

| Property | Value |
|----------|-------|
| P31 (instance of) | human (Q5) |
| P27 (country of citizenship) | Philippines (Q928), only if self-identification is acceptable for the item |
| P856 (official website) | `https://www.marksiazon.dev` |
| P2037 (GitHub username) | `Iron-Mark` |
| P6634 (LinkedIn personal profile ID) | `mark-siazon` |

Avoid adding education, employer, awards, or occupation Q-items unless each claim has a source suitable for Wikidata.

## SameAs / External Identity URLs

Use these as source links or external references where appropriate:

```text
https://www.marksiazon.dev
https://github.com/Iron-Mark
https://github.com/mark-siazon
https://github.com/Iron-Mark/Iron-Mark
https://www.linkedin.com/in/mark-siazon/
https://www.frontendmentor.io/profile/Iron-Mark
```

## QuickStatements Draft

Review each statement before running it. Replace nothing with a Q-id before the item exists; `LAST` refers to the newly created item.

```text
CREATE
LAST|Len|"Mark Siazon"
LAST|Den|"product designer and full-stack developer from the Philippines"
LAST|P31|Q5
LAST|P856|"https://www.marksiazon.dev"
LAST|P2037|"Iron-Mark"
LAST|P6634|"mark-siazon"
```

## After Creation

1. Note the new Q-id, for example `Q123456789`.
2. Update `llms-index.json`:
   - `identifiers.wikidata`
   - `entity.sameAs`
3. Regenerate schema/context artifacts:
   ```bash
   python3 src/scripts/generate_schema.py
   python3 src/scripts/generate_llms_ctx.py
   python3 src/scripts/build_pages_index.py
   python3 src/scripts/generate_sitemap.py
   python3 src/scripts/generate_portfolio_sync.py
   python3 src/scripts/bump_index_dates.py
   ```
4. Update the portfolio site JSON-LD / `llms.txt` mirror.
5. Run validation and open `dev` -> `main` PR.
