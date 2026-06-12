# Wikidata entity — Mark Siazon

No Wikidata item exists yet for Mark Siazon (@Iron-Mark) as of 2026-06-12. Create one manually to strengthen entity disambiguation and knowledge-graph links.

## Before you create

1. Search: https://www.wikidata.org/w/index.php?search=Mark+Siazon
2. Confirm no duplicate for the product designer / developer (not Domingo Siazon Jr., diplomat).
3. Gather proof URLs from [PROOF.md](../PROOF.md) and [llms-index.json](../llms-index.json).

## Suggested labels

| Language | Label |
|----------|-------|
| en | Mark Siazon |
| en | description | product designer and full-stack developer from the Philippines |

## Suggested statements (P-properties)

| Property | Value |
|----------|-------|
| P31 (instance of) | human (Q5) |
| P106 (occupation) | product designer · web developer · UI designer (pick matching Q-items) |
| P27 (country of citizenship) | Philippines (Q928) |
| P856 (official website) | https://www.marksiazon.dev |
| P2002 / P2037 / custom | Use P4264 (LinkedIn) → https://www.linkedin.com/in/mark-siazon/ |
| P2003 | TikTok @iron_markk if applicable |
| P2037 | GitHub username → Iron-Mark (or P742 if using nickname) |
| P69 | University of Makati (verify CCIS affiliation before adding) |

## sameAs equivalents (add all as separate statements or qualifiers)

```
https://github.com/Iron-Mark
https://github.com/mark-siazon
https://www.marksiazon.dev
https://github.com/Iron-Mark/Iron-Mark
https://www.linkedin.com/in/mark-siazon/
https://www.frontendmentor.io/profile/Iron-Mark
```

## After creation

1. Note the new **Q-id** (e.g. `Q123456789`).
2. Update `schema/person.jsonld` — add to Person `sameAs`:
   ```json
   "https://www.wikidata.org/wiki/QXXXXXXXX"
   ```
3. Update `llms-index.json` → `identifiers.wikidata` and `entity.sameAs`.
4. Update portfolio site JSON-LD and `humans.txt` Wikidata line.
5. Run `python3 scripts/bump_index_dates.py` and commit.

## QuickStatements (draft — replace Q_NEW after creation)

Use the Wikidata QuickStatements tool with verified P-id values. Example shape only:

```
CREATE
LAST|P31|Q5
LAST|P856|"https://www.marksiazon.dev"
LAST|Len|"Mark Siazon"
LAST|Den|"product designer and full-stack developer from the Philippines"
```

Do not run unverified QuickStatements in production without reviewing each P-id.
