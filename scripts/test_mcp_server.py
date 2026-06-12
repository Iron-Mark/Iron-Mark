#!/usr/bin/env python3
"""End-to-end smoke test for iron-mark-profile MCP server (stdio)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[1]
MCP_DIR = REPO / "mcp-server"


async def run_e2e() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MCP_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "iron_mark_profile.server"],
        cwd=str(MCP_DIR),
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo is not None
            assert "iron-mark-profile" in (init.serverInfo.name or "")

            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            required_tools = {
                "get_profile_summary",
                "search_faq",
                "list_projects",
                "get_project",
                "get_proof",
                "get_citation_guide",
            }
            missing = required_tools - tool_names
            if missing:
                raise AssertionError(f"Missing tools: {missing}")

            resources = await session.list_resources()
            uris = {str(r.uri) for r in resources.resources}
            for uri in (
                "profile://llms-index.json",
                "profile://faq.md",
                "profile://recruiter.md",
            ):
                if uri not in uris:
                    raise AssertionError(f"Missing resource: {uri}")

            templates = await session.list_resource_templates()
            if not any("project" in t.uriTemplate for t in templates.resourceTemplates):
                raise AssertionError("Missing project resource template")

            prompts = await session.list_prompts()
            if not any(p.name == "evaluate_for_role" for p in prompts.prompts):
                raise AssertionError("Missing evaluate_for_role prompt")

            summary = await session.call_tool("get_profile_summary", {})
            if summary.isError:
                raise AssertionError(f"get_profile_summary error: {summary.content}")

            faq = await session.call_tool("search_faq", {"query": "HireProof", "limit": 2})
            if faq.isError:
                raise AssertionError(f"search_faq error: {faq.content}")

            project = await session.call_tool("get_project", {"slug_or_name": "resqlink"})
            if project.isError:
                raise AssertionError(f"get_project error: {project.content}")

            proof = await session.call_tool("get_proof", {})
            if proof.isError:
                raise AssertionError(f"get_proof error: {proof.content}")

            faq_res = await session.read_resource("profile://faq.md")
            if not faq_res.contents or not faq_res.contents[0].text:
                raise AssertionError("read_resource faq.md returned empty")

            proj_res = await session.read_resource("profile://project/hireproof")
            if not proj_res.contents or "HireProof" not in (proj_res.contents[0].text or ""):
                raise AssertionError("read_resource project/hireproof invalid")

            prompt = await session.get_prompt("evaluate_for_role", {"role": "product designer"})
            if not prompt.messages:
                raise AssertionError("evaluate_for_role prompt empty")

    print("test_mcp_server: e2e OK")
    print(f"  tools={len(tool_names)} resources={len(uris)} prompts=1")


def main() -> int:
    try:
        asyncio.run(run_e2e())
        return 0
    except Exception as e:
        print(f"test_mcp_server: FAIL — {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
