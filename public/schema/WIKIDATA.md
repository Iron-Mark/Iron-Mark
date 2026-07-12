# Wikidata entity - Mark Siazon

No Wikidata item exists yet for Mark Siazon (@Iron-Mark). Re-verified 2026-07-09 via the entity search API (empty `search` array):

```text
https://www.wikidata.org/w/api.php?action=wbsearchentities&search=Mark%20Siazon&language=en&format=json
```

Creating the item requires a logged-in Wikidata editor account. Do not add a fake Q-id to this repo.

## Before creation

1. Search https://www.wikidata.org/w/index.php?search=Mark+Siazon and confirm there is still no duplicate for the product designer / full-stack developer behind `Iron-Mark` and `marksiazon.dev`.
2. Use proof URLs from [PROOF.md](../PROOF.md), [ENTITY.md](ENTITY.md), and [llms-index.json](../llms-index.json) as references.

## Verified Q-ids and properties (checked 2026-07-09)

| Item / property | Id | Notes |
|-----------------|----|-------|
| human | Q5 | P31 value |
| Philippines | Q928 | P27 value |
| University of Makati | Q7895659 | P69 value (public university) |
| web developer | Q6859454 | P106 value |
| user experience designer | Q68200826 | P106 value |
| instance of | P31 | |
| country of citizenship | P27 | |
| occupation | P106 | |
| educated at | P69 | |
| official website | P856 | |
| GitHub username | P2037 | |
| LinkedIn personal profile ID | P6634 | |
| reference URL | P854 | use as `S854` in QuickStatements |
| retrieved | P813 | use as `S813` in QuickStatements |

## QuickStatements draft

Paste at https://quickstatements.toolforge.org . `Len`/`Den`/`Aen` = English label/description/alias; `S854` = reference URL; `S813` = retrieved date; `LAST` = the item just created. Review each line before running.

### Core (identity only, lowest deletion risk)

```text
CREATE
LAST|Len|"Mark Siazon"
LAST|Den|"product designer and full-stack developer from the Philippines"
LAST|Aen|"Iron-Mark"
LAST|Aen|"mark-siazon"
LAST|P31|Q5
LAST|P856|"https://www.marksiazon.dev"|S854|"https://www.marksiazon.dev"|S813|+2026-07-09T00:00:00Z/11
LAST|P2037|"Iron-Mark"|S854|"https://github.com/Iron-Mark"|S813|+2026-07-09T00:00:00Z/11
LAST|P6634|"mark-siazon"|S854|"https://www.linkedin.com/in/mark-siazon/"|S813|+2026-07-09T00:00:00Z/11
```

### Optional (add only where the reference URL actually states the fact)

```text
LAST|P27|Q928|S854|"https://www.marksiazon.dev"
LAST|P106|Q6859454|S854|"https://www.marksiazon.dev"
LAST|P106|Q68200826|S854|"https://www.marksiazon.dev"
LAST|P69|Q7895659|S854|"<a page that explicitly states you studied at UMak>"
```

Optional gender statement (self-identification): `LAST|P21|Q6581097` (male) or `LAST|P21|Q6581072` (female). Occupation "product designer" has no clean Wikidata item, so web developer + user experience designer stand in.

## Caveats

- **Deletion risk.** Wikidata can delete items about living people that lack public, independent sourcing. The InfotechOlympics awards and multiple external profiles help; if the item is challenged, cite https://www.marksiazon.dev/achievements . Items backed only by self-published sources are the ones most often nominated.
- **P69 (educated at).** Mark is a University of Makati graduate, but Wikidata wants a source that states this. Point `S854` at a page that actually declares the education (LinkedIn education section or an About page), not the competition page, which only proves the contest.

## SameAs / external identity URLs

Use as reference or external-identifier links where appropriate:

```text
https://www.marksiazon.dev
https://github.com/Iron-Mark
https://github.com/mark-siazon
https://github.com/Iron-Mark/Iron-Mark
https://www.linkedin.com/in/mark-siazon/
https://www.frontendmentor.io/profile/Iron-Mark
```

## After creation

1. Note the new Q-id, for example `Q123456789`.
2. Update `llms-index.json`:
   - `identifiers.wikidata` (the Q-id or its full URL)
   - add `https://www.wikidata.org/wiki/Q...` to `entity.sameAs`
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
5. Run `python3 src/scripts/validate_index.py`, then open a `dev` -> `main` PR.
