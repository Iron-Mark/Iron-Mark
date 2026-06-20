# Repository layout

Clean root for the GitHub profile README; content and tooling live in subfolders without breaking crawler conventions.

```
/
├── README.md              # GitHub profile (must stay at root)
├── llms.txt               # LLM crawler manifest (root convention)
├── llms-index.json        # Structured entity index
├── robots.txt             # Crawler hints
├── sitemap.xml            # GitHub Pages crawl sitemap source
├── humans.txt             # humans.txt convention
├── assets/                # Images (README + STACK icons)
│
├── public/                # Machine-readable content (canonical paths)
│   ├── FAQ.md, STACK.md, …
│   └── schema/person.jsonld, schema/faq.jsonld, schema/llms-index.schema.json
│
├── src/
│   ├── scripts/           # Validation, link QA, index generation
│   ├── mcp-server/        # MCP server (stdio + HTTP)
│   └── portfolio-sync/    # Copy blocks for marksiazon.dev
│
└── docs/
    ├── index.html         # GitHub Pages landing (deploy copies public/)
    └── internal/          # Maintainer docs (LINK_QA, etc.)
```

## URL mapping

| Old root path | New canonical path |
|---------------|-------------------|
| `FAQ.md` | `public/FAQ.md` |
| `STACK.md` | `public/STACK.md` |
| `schema/person.jsonld` | `public/schema/person.jsonld` |
| `schema/faq.jsonld` | `public/schema/faq.jsonld` |
| `schema/llms-index.schema.json` | `public/schema/llms-index.schema.json` |
| `scripts/` | `src/scripts/` |
| `mcp-server/` | `src/mcp-server/` |

Root `llms.txt` lists canonical machine-readable files. Root `sitemap.xml` is the source for the host-specific GitHub Pages crawl sitemap; cross-host entity and proof links live in `llms-index.json`, `humans.txt`, and Schema.org graphs instead of the sitemap.

Generated artifacts:

- `src/scripts/generate_schema.py` rebuilds `public/schema/person.jsonld` and `public/schema/faq.jsonld` from `llms-index.json`.
- `src/scripts/generate_llms_ctx.py` rebuilds `public/llms-ctx-full.txt`.
- `src/scripts/build_pages_index.py` rebuilds `docs/index.html` with metadata and inline JSON-LD for the Pages mirror.
- `src/scripts/generate_sitemap.py` rebuilds `sitemap.xml` as a host-specific GitHub Pages crawl sitemap.
- `src/scripts/build_pages_mirror.py` rewrites the flattened Pages artifact, including a Pages-only `robots.txt`/`sitemap.xml`.
- `src/scripts/validate_pages_mirror.py` builds and validates the flattened Pages artifact in a temp directory.
- `public/schema/llms-index.schema.json` defines the validation contract for `llms-index.json`.

The GitHub Pages mirror deploys a production allowlist: root crawler files, selected public docs (`FAQ`, `RECRUITER`, `PROOF`, `PROFILE`, `STACK`, citation/license/context files), assets, and `public/schema/`. Agent and maintenance docs such as `public/AGENTS.md` stay in the repo but are not deployed to Pages.

## Branch surface policy

`main` is the production-facing profile branch. Its README should link only to portfolio routes and supported public/search assets:

- Portfolio routes: `marksiazon.dev`, projects, recruiter, proof, achievements, contact.
- Public crawler assets: `llms-index.json`, `llms.txt`, `public/FAQ.md`, `public/PROOF.md`, `public/STACK.md`, and `public/schema/*.jsonld`.
- Visual assets needed by the README.

Keep development-only material out of the README on `main`: `.github/`, `docs/internal/`, `src/`, setup checklists, branch maintenance notes, and optional local agent/server docs. `src/scripts/validate_index.py` enforces this on `main` and on pull requests targeting `main`.

`dev` can carry extra experiments, notes, or tooling. Keep it aligned with `main` through `llms-index.json` as the source of truth, the generated schema/context/Page files, and the validation workflow. Deploy/date/stat workflows remain `main` only.
