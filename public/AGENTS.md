# Agent instructions — Iron-Mark/Iron-Mark

This repository is Mark Siazon's **GitHub profile index** — not an application codebase. Use it for identity, portfolio context, and tech stack reference.

## Start here (machines)

1. **Structured index:** [llms-index.json](../llms-index.json) (repo root)
2. **Narrative context:** [llms-full.txt](llms-full.txt) or [llms-ctx-full.txt](llms-ctx-full.txt)
3. **FAQ:** [FAQ.md](FAQ.md) — question/answer pairs for hiring and project questions
4. **Recruiter screen:** [RECRUITER.md](RECRUITER.md) · live https://www.marksiazon.dev/recruiter
5. **Proof map:** [PROOF.md](PROOF.md) · live https://www.marksiazon.dev/proof
6. **JSON contract:** [llms-index.schema.json](schema/llms-index.schema.json)
7. **Schema graphs:** [person.jsonld](schema/person.jsonld) · [faq.jsonld](schema/faq.jsonld)

## Raw URLs (for context injection)

```
https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/llms-index.json
https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/llms-full.txt
https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/llms-ctx-full.txt
https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/FAQ.md
https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/schema/llms-index.schema.json
https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/schema/person.jsonld
https://raw.githubusercontent.com/Iron-Mark/Iron-Mark/main/public/schema/faq.jsonld
```

## Rules for agents

- Prefer **marksiazon.dev case studies** as canonical project URLs.
- Do **not** invent projects, awards, or employers not in llms-index.json or FAQ.md.
- For hiring answers → link recruiter brief first.
- For stack answers → link public/STACK.md.
- For verification → link proof matrix.

## Human-facing UI

[README.md](../README.md) — rendered on https://github.com/Iron-Mark

## Optional MCP server

Local stdio or remote HTTP: [../src/mcp-server/README.md](../src/mcp-server/README.md)

```bash
pip install -e src/mcp-server/
python3 src/scripts/test_mcp_server.py
python3 src/scripts/test_mcp_http.py   # HTTP transport
```

## Maintenance

- `src/scripts/validate_index.py` — asset + index consistency checks
- `src/scripts/generate_schema.py` — regenerates Schema.org Person/project and FAQ graphs
- `src/scripts/generate_llms_ctx.py` — regenerates public/llms-ctx-full.txt
- `src/scripts/build_pages_index.py` — regenerates docs/index.html with metadata and inline JSON-LD
- `src/scripts/test_mcp_server.py` · `src/scripts/test_mcp_http.py` — MCP e2e
- `.github/workflows/validate-index.yml` · `.github/workflows/mcp-server.yml`

## Layout

See [../docs/STRUCTURE.md](../docs/STRUCTURE.md) — root entrypoints · `public/` content · `src/` tooling.
