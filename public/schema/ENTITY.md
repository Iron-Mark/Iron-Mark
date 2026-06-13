# Canonical entity identifiers (@id)

Use these URIs consistently across Schema.org JSON-LD, `llms-index.json`, portfolio structured data, and Wikidata `sameAs` links.

| Entity | @id | Role |
|--------|-----|------|
| **Person** | `https://www.marksiazon.dev/#person` | Primary human entity — Mark Siazon |
| **Portfolio website** | `https://www.marksiazon.dev/#website` | Canonical portfolio site |
| **GitHub profile README** | `https://github.com/Iron-Mark/Iron-Mark#profilepage` | ProfilePage for GitHub index repo |
| **GitHub profile index site** | `https://github.com/Iron-Mark/Iron-Mark#website` | WebSite entity for the README repo |
| **GitHub Pages mirror** | `https://iron-mark.github.io/Iron-Mark/#website` | Static mirror of machine-readable files |
| **FAQ document** | `https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#faq` | AEO Q&A corpus |
| **Structured index** | `https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json` | JSON entity + answer snippets |

## Rules

1. **Person `@id`** always uses the portfolio fragment `#person`, not the GitHub URL.
2. **Portfolio** is the canonical `url` for the Person; GitHub README is a `sameAs` / `authorOf` surface.
3. After Wikidata item creation, add `https://www.wikidata.org/wiki/Q…` to Person `sameAs` in `schema/person.jsonld` and `llms-index.json` → `entity.sameAs`.
4. Do not invent Q-numbers — follow [WIKIDATA.md](WIKIDATA.md) to create the item.

## Files that must stay in sync

- `schema/person.jsonld`
- `llms-index.json` → `entity`, `identifiers`
- `humans.txt` → `/* ENTITY */`
- `HOW-TO-CITE.md`
- Portfolio site JSON-LD (marksiazon.dev repo)
