# Iron-Mark Profile MCP Server

Optional [Model Context Protocol](https://modelcontextprotocol.io) server exposing Mark Siazon's GitHub profile index (`Iron-Mark/Iron-Mark`) to AI agents — tools, resources, and prompts backed by `llms-index.json`, `FAQ.md`, and related files.

## Quick start

From the **repo root**:

```bash
pip install -e mcp-server/
python3 scripts/test_mcp_server.py   # e2e smoke test
iron-mark-profile-mcp                # run server (stdio)
```

Or without install:

```bash
PYTHONPATH=mcp-server python3 -m iron_mark_profile.server
```

## Cursor

Copy [mcp-config.example.json](mcp-config.example.json) into your project or user MCP config. For this repo:

```json
{
  "mcpServers": {
    "iron-mark-profile": {
      "command": "python3",
      "args": ["-m", "iron_mark_profile.server"],
      "cwd": "${workspaceFolder}/mcp-server",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/mcp-server"
      }
    }
  }
}
```

Requires `pip install -e mcp-server/` once (or use `"command": "iron-mark-profile-mcp"` after install).

**Cursor UI:** Settings → MCP → Add server → paste the JSON above.

## Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

Install the package first: `pip install -e /path/to/Iron-Mark/mcp-server`

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
| `profile://llms-index.json` | Structured entity index |
| `profile://faq.md` | FAQ (15+ Q&A) |
| `profile://llms-ctx-full.txt` | Expanded agent context |
| `profile://recruiter.md` | In-repo recruiter brief |
| `profile://proof.md` | Claims → verification URLs |
| `profile://agents.md` | Agent instructions |
| `profile://project/{slug}` | Single project JSON |

## Prompts

- **`evaluate_for_role`** — hiring evaluation prompt with entity, FAQ hits, and flagship projects

## Data source

Reads files from the **repo root** (parent of `mcp-server/`). Run from a checked-out clone so `llms-index.json` stays in sync.

## Agent rules

- Prefer **marksiazon.dev** case studies as canonical project URLs
- Do **not** invent projects or awards not in the index
- Hiring → recruiter brief first; verification → proof matrix

See also [AGENTS.md](../AGENTS.md) in the repo root.
