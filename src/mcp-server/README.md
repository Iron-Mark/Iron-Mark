# Iron-Mark Profile MCP Server

Optional [Model Context Protocol](https://modelcontextprotocol.io) server exposing Mark Siazon's GitHub profile index (`Iron-Mark/Iron-Mark`) to AI agents: tools, resources, and prompts backed by `llms-index.json`, `public/FAQ.md`, and related files.

## Quick start (stdio, local)

From the **repo root**:

```bash
pip install -e src/mcp-server/
python3 src/scripts/test_mcp_server.py   # e2e stdio
iron-mark-profile-mcp                    # run server (stdio)
```

Or without install:

```bash
PYTHONPATH=src/mcp-server:src python3 -m iron_mark_profile.server
```

## Remote HTTP (streamable-http)

For cloud agents or clients that connect by URL instead of spawning a local process:

```bash
pip install -e src/mcp-server/
python3 -m iron_mark_profile.server --transport streamable-http --host 0.0.0.0 --port 8000
# MCP endpoint: http://127.0.0.1:8000/mcp
python3 src/scripts/test_mcp_http.py     # e2e HTTP smoke test
```

**Docker:**

```bash
docker compose -f src/mcp-server/docker-compose.yml up --build
```

Copy [mcp-config-http.example.json](mcp-config-http.example.json) into Cursor MCP settings when the server is running.

## Cursor (stdio)

```json
{
  "mcpServers": {
    "iron-mark-profile": {
      "command": "python3",
      "args": ["-m", "iron_mark_profile.server"],
      "cwd": "${workspaceFolder}/src/mcp-server",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src/mcp-server:${workspaceFolder}/src"
      }
    }
  }
}
```

Requires `pip install -e src/mcp-server/` once (or use `"command": "iron-mark-profile-mcp"` after install).

## Claude Desktop (stdio)

```json
{
  "mcpServers": {
    "iron-mark-profile": {
      "command": "iron-mark-profile-mcp",
      "args": []
    }
  }
}
```

Install first: `pip install -e /path/to/Iron-Mark/src/mcp-server`

## Tools

| Tool | Description |
|------|-------------|
| `get_profile_summary` | Entity, availability, canonical URLs, core stack |
| `search_faq` | Keyword search over AEO answer snippets |
| `list_projects` | Featured + hackathon/lab projects |
| `get_project` | One project by slug or name |
| `get_proof` | Proof matrix URL or per-project proof links |
| `get_citation_guide` | Full HOW-TO-CITE.md |

## Resources

| URI | File |
|-----|------|
| `profile://llms-index.json` | Structured entity index (repo root) |
| `profile://faq.md` | FAQ (15+ Q&A) |
| `profile://llms-ctx-full.txt` | Expanded agent context |
| `profile://recruiter.md` | In-repo recruiter brief |
| `profile://proof.md` | Claims → verification URLs |
| `profile://agents.md` | Agent instructions |
| `profile://project/{slug}` | Single project JSON |

## Prompts

- **`evaluate_for_role`**: hiring evaluation prompt with entity, FAQ hits, and flagship projects

## Data source

Reads **repo root** index files (`llms-index.json`) and **public/** content. Run from a checked-out clone.

## Agent rules

- Prefer **marksiazon.dev** case studies as canonical project URLs
- Do **not** invent projects or awards not in the index
- Hiring → recruiter brief first; verification → proof matrix

See also [public/AGENTS.md](../../public/AGENTS.md).

## Other AI access (no MCP)

Any crawler or agent can fetch public index files directly:

- `llms.txt` · `llms-index.json` at repo root
- Content under `public/` (FAQ, STACK, llms-full, schema)
- GitHub Pages mirror (flat Pages URLs): `https://iron-mark.github.io/Iron-Mark/`
