#!/usr/bin/env python3
"""End-to-end smoke test for iron-mark-profile MCP server (streamable HTTP)."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

REPO = Path(__file__).resolve().parents[2]
MCP_DIR = REPO / "src" / "mcp-server"
PORT = int(os.environ.get("MCP_TEST_PORT", "8765"))
URL = f"http://127.0.0.1:{PORT}/mcp"


async def run_http_e2e() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(MCP_DIR) + os.pathsep + str(REPO / "src") + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "iron_mark_profile.server",
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=str(MCP_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 15
        last_err: Exception | None = None
        while time.time() < deadline:
            if proc.poll() is not None:
                err = proc.stderr.read().decode() if proc.stderr else ""
                raise RuntimeError(f"HTTP MCP server exited early: {err}")
            try:
                async with streamable_http_client(URL) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        if not any(t.name == "search_faq" for t in tools.tools):
                            raise AssertionError("search_faq tool missing over HTTP")
                        faq = await session.call_tool("search_faq", {"query": "ResQLink", "limit": 1})
                        if faq.isError:
                            raise AssertionError(f"search_faq HTTP error: {faq.content}")
                        res = await session.read_resource("profile://llms-index.json")
                        if not res.contents or "Mark Siazon" not in (res.contents[0].text or ""):
                            raise AssertionError("llms-index resource invalid over HTTP")
                        print("test_mcp_http: e2e OK (streamable-http)")
                        print(f"  url={URL} tools={len(tools.tools)}")
                        return
            except AssertionError:
                raise
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.35)
        raise TimeoutError(f"MCP HTTP server not ready at {URL}: {last_err}")
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    try:
        asyncio.run(run_http_e2e())
        return 0
    except Exception as e:
        print(f"test_mcp_http: FAIL — {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
