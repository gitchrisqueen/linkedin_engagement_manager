"""Protocol-level fixtures for the content research caller."""

import asyncio
import json
from types import SimpleNamespace

import httpx2
import pytest


@pytest.fixture
def parallel_transport(monkeypatch, _no_real_parallel_search):
    """Run the real MCP SDK against deterministic HTTP responses, without sockets."""
    from cqc_lem.utilities.ai import parallel_search

    state = SimpleNamespace(
        requests=[], result={"results": [{"title": "Research report", "url": "https://example.org/report",
                                          "excerpts": ["A 2026 survey found 42% adoption."]}]},
        tool_error=False, text_only=False, status=200, exception=None,
        omit_search=False, stall_method=None, started=asyncio.Event(),
    )
    original_client = httpx2.AsyncClient

    async def handler(request):
        state.requests.append(request)
        if state.exception:
            raise state.exception
        if state.status != 200:
            return httpx2.Response(state.status, text="unit-test fixture: research unavailable")
        if request.method == "GET":
            return httpx2.Response(405)
        if request.method == "DELETE":
            return httpx2.Response(200)
        data = json.loads(request.content)
        if "id" not in data:
            return httpx2.Response(202)
        method = data["method"]
        if method == state.stall_method:
            state.started.set()
            await asyncio.Event().wait()
        if method == "initialize":
            result = {"protocolVersion": data["params"]["protocolVersion"],
                      "capabilities": {"tools": {}},
                      "serverInfo": {"name": "parallel-test-server", "version": "1.0"}}
        elif method == "tools/list":
            result = {"tools": [{"name": "web_search", "description": "Search the web",
                                 "inputSchema": {"type": "object", "required": ["objective", "search_queries"],
                                                 "properties": {"objective": {"type": "string"},
                                                                "search_queries": {"type": "array", "items": {
                                                                    "type": "string"}}}}}]}
            if state.omit_search:
                result = {"tools": []}
        else:
            assert method == "tools/call"
            assert data["params"]["name"] == "web_search"
            text = state.result if isinstance(state.result, str) else json.dumps(state.result)
            result = {"content": [{"type": "text", "text": text}], "isError": state.tool_error}
            if not state.text_only and isinstance(state.result, dict):
                result["structuredContent"] = state.result
        return httpx2.Response(200, json={"jsonrpc": "2.0", "id": data["id"], "result": result})

    def make_client(**kwargs):
        return original_client(**kwargs, transport=httpx2.MockTransport(handler))

    monkeypatch.setattr(parallel_search.httpx2, "AsyncClient", make_client)
    return state
