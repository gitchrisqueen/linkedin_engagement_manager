"""Anonymous Parallel Search MCP excerpts for the shared content research layer."""

import asyncio
import json
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from urllib.parse import urlsplit

import httpx2
from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client

SEARCH_URL = "https://search.parallel.ai/mcp"
USER_AGENT = (
    "linkedin-engagement-manager "
    "(+https://github.com/christopherqueenconsulting/linkedin_engagement_manager)"
)
SEARCH_TIMEOUT_SECONDS = 25
_REQUEST_TIMEOUT_SECONDS = 20
_MAX_EXCERPT_CHARS = 3000


def _valid_source_url(value: Any) -> bool:
    if not isinstance(value, str) or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    if "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None and parsed.port != 0)
    except ValueError:
        return False


def _result_payload(result: types.CallToolResult) -> dict:
    if result.is_error:
        detail = " ".join(part.text for part in result.content if isinstance(part, types.TextContent))
        raise RuntimeError(f"Parallel search failed: {detail}")
    if isinstance(result.structured_content, dict):
        return result.structured_content
    for part in result.content:
        if not isinstance(part, types.TextContent):
            continue
        try:
            payload = json.loads(part.text)
        except (ValueError, TypeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _source_excerpts(result: types.CallToolResult, max_sources: int) -> dict:
    payload = _result_payload(result)
    results = payload.get("results")
    findings: list[str] = []
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in results if isinstance(results, list) else []:
        if len(sources) >= max_sources:
            break
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not _valid_source_url(url) or url in seen:
            continue
        excerpts = item.get("excerpts")
        text = "\n".join(value.strip() for value in excerpts if isinstance(value, str) and value.strip()) \
            if isinstance(excerpts, list) else ""
        if not text:
            continue
        title = item.get("title")
        title = title.strip() if isinstance(title, str) and title.strip() else url
        findings.append(f"Source: {title}\nURL: {url}\n{text[:_MAX_EXCERPT_CHARS]}")
        sources.append({"url": url})
        seen.add(url)
    return {"findings": "\n\n".join(findings), "sources": sources}


async def _search(query: str, subject: str, max_sources: int) -> dict:
    try:
        client_version = version("linkedin-engagement-manager")
    except PackageNotFoundError:
        client_version = "source"
    async with httpx2.AsyncClient(headers={"User-Agent": USER_AGENT},
                                 timeout=_REQUEST_TIMEOUT_SECONDS, auth=None) as http:
        async with streamable_http_client(SEARCH_URL, http_client=http) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=_REQUEST_TIMEOUT_SECONDS,
                                     client_info=types.Implementation(
                                         name="linkedin-engagement-manager", version=client_version)) as session:
                await session.initialize()
                tools = await session.list_tools()
                if not any(tool.name == "web_search" for tool in tools.tools):
                    raise RuntimeError("Parallel Search MCP did not advertise web_search")
                result = await session.call_tool("web_search", {"objective": query, "search_queries": [subject]})
                return _source_excerpts(result, max_sources)


async def _bounded_search(query: str, subject: str, max_sources: int) -> dict:
    async with asyncio.timeout(SEARCH_TIMEOUT_SECONDS):
        return await _search(query, subject, max_sources)


def search_parallel(query: str, subject: str, max_sources: int = 5) -> dict:
    """Search once through MCP and return source-labelled excerpts, without another model call.

    Args:
        query: The shared research brief, including audience and freshness guidance.
        subject: The content topic used as a concise search query.
        max_sources: Upper bound on distinct sources and their excerpt blocks.

    Returns:
        The shared findings/sources contract; empty when no usable excerpts exist.

    Raises:
        Exception: Transport, protocol or tool failure, for the research layer to handle.
    """
    limit = max(0, int(max_sources))
    if not limit:
        return {"findings": "", "sources": []}
    return asyncio.run(_bounded_search(query, subject, limit))
