# Repository layout

Clean root for the GitHub profile README; content and tooling live in subfolders without breaking crawler conventions.

```
/
├── README.md              # GitHub profile (must stay at root)
├── llms.txt               # LLM crawler manifest (root convention)
├── llms-index.json        # Structured entity index
├── robots.txt             # Crawler hints
├── sitemap.xml            # URL index for SEO/AEO
├── humans.txt             # humans.txt convention
├── assets/                # Images (README + STACK icons)
│
├── public/                # Machine-readable content (canonical paths)
│   ├── FAQ.md, STACK.md, …
│   └── schema/
│
├── src/
│   ├── scripts/           # Validation, link QA, index generation
│   ├── mcp-server/        # MCP server (stdio + HTTP)
│   └── src/portfolio-sync/    # Copy blocks for marksiazon.dev
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
| `scripts/` | `src/scripts/` |
| `mcp-server/` | `src/mcp-server/` |

Root `llms.txt` and `sitemap.xml` list `public/` paths for crawlers.
