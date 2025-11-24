import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from agents.mcp import MCPServerStreamableHttp


GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


def _get_github_pat() -> str:
    token = os.getenv("GITHUB_MCP_PAT")
    if not token:
        raise RuntimeError(
            "GITHUB_MCP_PAT is not set. "
            "Create a GitHub PAT with appropriate scopes and export it."
        )
    return token


@asynccontextmanager
async def github_mcp_server() -> AsyncIterator[MCPServerStreamableHttp]:
    """
    Context manager that yields a configured MCP server instance for GitHub.

    Uses Streamable HTTP transport to connect to the hosted GitHub MCP server.
    """
    token = _get_github_pat()

    server = MCPServerStreamableHttp(
        name="github",
        params={
            "url": GITHUB_MCP_URL,
            "headers": {
                "Authorization": f"Bearer {token}",
                # You can add extra headers if GitHub exposes more options later.
            },
            "timeout": 15,
        },
        cache_tools_list=True,
        max_retry_attempts=3,
    )

    async with server:
        yield server