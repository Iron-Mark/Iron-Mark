# Canonical entity identifiers (@id)

Use these URIs consistently across Schema.org JSON-LD, `llms-index.json`, portfolio structured data, and Wikidata `sameAs` links.

| Entity | @id | Role |
|--------|-----|------|
| **Person** | `https://www.marksiazon.dev/#mark-siazon` | Primary human entity: Mark Siazon |
| **Portfolio website** | `https://www.marksiazon.dev/#website` | Canonical portfolio site |
| **GitHub profile README** | `https://github.com/Iron-Mark/Iron-Mark#profilepage` | ProfilePage for GitHub index repo |
| **GitHub profile index site** | `https://github.com/Iron-Mark/Iron-Mark#website` | WebSite entity for the README repo |
| **GitHub Pages mirror** | `https://iron-mark.github.io/Iron-Mark/#website` | Static mirror of public source files |
| **FAQ document** | `https://github.com/Iron-Mark/Iron-Mark/blob/main/public/FAQ.md#faq` | Q&A corpus |
| **Structured index** | `https://github.com/Iron-Mark/Iron-Mark/blob/main/llms-index.json` | JSON entity + answer snippets |
| **Structured index schema** | `https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/llms-index.schema.json` | JSON Schema contract for `llms-index.json` |
| **Person schema graph** | `https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/person.jsonld` | Schema.org Person, profile, projects, and content graph |
| **FAQ schema graph** | `https://github.com/Iron-Mark/Iron-Mark/blob/main/public/schema/faq.jsonld` | Schema.org FAQPage, Question, and Answer graph |

## Rules

1. **Person `@id`** always uses the portfolio fragment `#mark-siazon`, not the GitHub URL.
2. **Portfolio** is the canonical `url` for the Person; GitHub README is a `sameAs` / `authorOf` surface.
3. After Wikidata item creation, add `https://www.wikidata.org/wiki/Q…` to Person `sameAs` in `schema/person.jsonld` and `llms-index.json` → `entity.sameAs`.
4. Do not invent Q-numbers, follow [WIKIDATA.md](WIKIDATA.md) to create the item.

## Files that must stay in sync

- `schema/person.jsonld`
- `schema/faq.jsonld`
- `schema/llms-index.schema.json`
- `llms-index.json` → `entity`, `identifiers`
- `humans.txt` → `/* ENTITY */`
- `HOW-TO-CITE.md`
- Portfolio site JSON-LD (marksiazon.dev repo)
