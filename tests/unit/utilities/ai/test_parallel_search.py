"""Parallel research selection and real SDK HTTP protocol tests; no external services."""

import asyncio
import json
from importlib.metadata import PackageNotFoundError
from unittest.mock import Mock, patch

import httpx2
import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_research_configuration(monkeypatch):
    for name in ("CONTENT_RESEARCH_PROVIDER", "PERPLEXITY_API_KEY", "RESEARCH_VIA_PROXY",
                 "CONTENT_RESEARCH_ENABLED", "NEWSLETTER_RESEARCH_ENABLED", "POST_RESEARCH_ENABLED",
                 "COMMENT_RESEARCH_ENABLED", "PARALLEL_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(("settings", "provider"), [
    ({}, "parallel"), ({"PERPLEXITY_API_KEY": "   "}, "parallel"),
    ({"CONTENT_RESEARCH_PROVIDER": "  "}, "parallel"),
    ({"PERPLEXITY_API_KEY": "test-key"}, "perplexity"),
    ({"RESEARCH_VIA_PROXY": "true"}, "perplexity"),
    ({"RESEARCH_VIA_PROXY": "false"}, "parallel"),
    ({"CONTENT_RESEARCH_PROVIDER": " PARALLEL ", "PERPLEXITY_API_KEY": "test-key",
      "RESEARCH_VIA_PROXY": "true"}, "parallel"),
    ({"CONTENT_RESEARCH_PROVIDER": "perplexity"}, "perplexity"),
])
def test_provider_selection_preserves_configured_choices(monkeypatch, settings, provider):
    from cqc_lem.utilities.ai import content_research as cr

    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    assert cr.research_provider() == provider


def test_invalid_provider_returns_empty_without_a_fallback(monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr

    monkeypatch.setenv("CONTENT_RESEARCH_PROVIDER", "paralell")
    with patch.object(cr, "_research_parallel") as parallel, patch.object(cr, "_research_direct") as direct, \
            patch.object(cr, "proxy_route_open") as proxy, patch.object(cr, "log_warning") as warning:
        assert cr.research_topic("AI", content_type="post") == {"findings": "", "sources": []}
    parallel.assert_not_called()
    direct.assert_not_called()
    proxy.assert_not_called()
    warning.assert_called_once()


@pytest.mark.parametrize("settings, subject, kind", [
    ({"CONTENT_RESEARCH_ENABLED": "false"}, "AI", "post"),
    ({"POST_RESEARCH_ENABLED": "false"}, "AI", "post"),
    ({"NEWSLETTER_RESEARCH_ENABLED": "false"}, "AI", "newsletter"),
    ({}, "AI", "comment"), ({}, " ", "post"),
])
def test_disable_gates_run_before_provider_resolution(monkeypatch, settings, subject, kind):
    from cqc_lem.utilities.ai import content_research as cr

    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    with patch.object(cr, "research_provider") as resolver:
        assert cr.research_topic(subject, content_type=kind) == {"findings": "", "sources": []}
    resolver.assert_not_called()


def test_per_user_comment_gate_runs_before_resolver(monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr

    monkeypatch.setenv("COMMENT_RESEARCH_ENABLED", "true")
    with patch.object(cr, "flag_enabled", return_value=False) as flag, \
            patch.object(cr, "research_provider") as resolver:
        assert cr.research_topic("AI", content_type="comment", user_id=23) == {"findings": "", "sources": []}
    flag.assert_called_once_with(cr.COMMENT_RESEARCH, user_id=23)
    resolver.assert_not_called()


def test_parallel_default_uses_sdk_handshake_search_and_source_excerpts(parallel_transport, monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr

    monkeypatch.setenv("PARALLEL_API_KEY", "must-not-be-used")
    result = cr.research_topic("AI adoption", content_type="post", max_sources=1)
    assert result == {"findings": "Source: Research report\nURL: https://example.org/report\n"
                                  "A 2026 survey found 42% adoption.",
                      "sources": [{"url": "https://example.org/report"}]}
    messages = [json.loads(r.content) for r in parallel_transport.requests if r.method == "POST"]
    assert [m["method"] for m in messages] == ["initialize", "notifications/initialized", "tools/list", "tools/call"]
    arguments = messages[-1]["params"]["arguments"]
    assert "AI adoption" in arguments["objective"]
    assert arguments["search_queries"] == ["AI adoption"]
    assert "session_id" not in arguments
    assert "model_name" not in arguments
    for request in parallel_transport.requests:
        assert str(request.url) == "https://search.parallel.ai/mcp"
        assert request.headers["user-agent"].startswith("linkedin-engagement-manager")
        assert "github.com/christopherqueenconsulting/linkedin_engagement_manager" in request.headers["user-agent"]
        assert "authorization" not in request.headers
        assert 0 < request.extensions["timeout"]["read"] <= 30


@pytest.mark.parametrize("text_only", [False, True])
def test_result_cap_dedup_and_urls_are_checked(parallel_transport, text_only):
    from cqc_lem.utilities.ai import content_research as cr

    parallel_transport.text_only = text_only
    parallel_transport.result = {"results": [
        {"url": "https://", "excerpts": ["bad host"]},
        {"url": "javascript:alert(1)", "excerpts": ["bad scheme"]},
        {"url": "https://user:secret@example.org", "excerpts": ["credentials"]},
        {"url": "https://example.org/\nprivate", "excerpts": ["control char"]},
        {"url": "https://example.org/sp ace", "excerpts": ["whitespace"]},
        {"url": "https://example.org:invalid", "excerpts": ["bad port"]},
        {"url": "https://example.org:0", "excerpts": ["zero port"]},
        {"url": "https://example.org/\\private", "excerpts": ["backslash"]},
        {"url": "https://empty.org", "excerpts": [None, " ", 3]},
        {"title": "One", "url": "https://one.org", "excerpts": ["First.", 3, "Second."]},
        {"url": "https://one.org", "excerpts": ["Duplicate."]},
        {"url": "http://two.org", "excerpts": ["Third."]},
        {"url": "https://three.org", "excerpts": ["Beyond cap."]},
    ]}
    result = cr.research_topic("AI", max_sources=2)
    assert result == {"findings": "Source: One\nURL: https://one.org\nFirst.\nSecond.\n\n"
                                  "Source: http://two.org\nURL: http://two.org\nThird.",
                      "sources": [{"url": "https://one.org"}, {"url": "http://two.org"}]}


@pytest.mark.parametrize("result", [{}, {"results": None}, {"results": "bad"}, {"results": [None, 3, {}]},
                                    "unit-test fixture: not JSON", "[]", {"results": []}])
def test_malformed_or_empty_results_are_empty(parallel_transport, result):
    from cqc_lem.utilities.ai import content_research as cr

    parallel_transport.result = result
    assert cr.research_topic("AI") == {"findings": "", "sources": []}


@pytest.mark.parametrize("max_sources", [0, -1])
def test_zero_source_budget_skips_network(parallel_transport, max_sources):
    from cqc_lem.utilities.ai import content_research as cr

    assert cr.research_topic("AI", max_sources=max_sources) == {"findings": "", "sources": []}
    assert parallel_transport.requests == []


@pytest.mark.parametrize("failure", ["tool", "http", "timeout"])
def test_parallel_failure_returns_empty_without_provider_fallback(parallel_transport, failure):
    from cqc_lem.utilities.ai import content_research as cr

    if failure == "tool":
        parallel_transport.tool_error = True
    elif failure == "http":
        parallel_transport.status = 503
    else:
        parallel_transport.exception = httpx2.ReadTimeout("unit-test fixture: timeout")
    with patch.object(cr, "_research_direct") as direct, patch.object(cr, "proxy_route_open") as proxy, \
            patch.object(cr, "log_warning") as warning:
        assert cr.research_topic("AI") == {"findings": "", "sources": []}
    direct.assert_not_called()
    proxy.assert_not_called()
    warning.assert_called_once()


def test_overall_timeout_cancels_a_stalled_transport(parallel_transport, monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr, parallel_search

    parallel_transport.stall_method = "tools/call"
    monkeypatch.setattr(parallel_search, "SEARCH_TIMEOUT_SECONDS", 0.05)
    with patch.object(cr, "_research_direct") as direct:
        assert cr.research_topic("AI") == {"findings": "", "sources": []}
    direct.assert_not_called()
    assert parallel_transport.started.is_set()


def test_cancellation_propagates_out_of_research_topic(monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr

    parallel = Mock(side_effect=asyncio.CancelledError)
    monkeypatch.setattr(cr, "_research_parallel", parallel)
    with pytest.raises(asyncio.CancelledError):
        cr.research_topic("AI")


@pytest.mark.asyncio
async def test_async_cancellation_closes_sdk_transport(parallel_transport):
    from cqc_lem.utilities.ai import parallel_search

    parallel_transport.stall_method = "tools/call"
    task = asyncio.create_task(parallel_search._bounded_search("brief", "AI", 5))
    await asyncio.wait_for(parallel_transport.started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    methods = [json.loads(r.content)["method"] for r in parallel_transport.requests if r.method == "POST"]
    assert methods.count("tools/call") == 1
    assert methods[-1] == "notifications/cancelled"


def test_missing_search_tool_returns_empty_without_dispatch(parallel_transport):
    from cqc_lem.utilities.ai import content_research as cr

    parallel_transport.omit_search = True
    assert cr.research_topic("AI") == {"findings": "", "sources": []}
    assert all(json.loads(r.content)["method"] != "tools/call"
               for r in parallel_transport.requests if r.method == "POST")


def test_source_checkout_version_and_excerpt_size_are_bounded(parallel_transport, monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr, parallel_search

    monkeypatch.setattr(parallel_search, "version", Mock(side_effect=PackageNotFoundError))
    parallel_transport.result = {"results": [{"url": "https://example.org", "excerpts": ["x" * 10_000]}]}
    result = cr.research_topic("AI")
    initialize = json.loads(parallel_transport.requests[0].content)
    assert initialize["params"]["clientInfo"]["version"] == "source"
    assert result["findings"].endswith("x" * 3000)
    assert len(result["findings"]) < 3100
    assert result["sources"] == [{"url": "https://example.org"}]


def test_explicit_parallel_overrides_existing_perplexity_and_proxy_settings(parallel_transport, monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr

    monkeypatch.setenv("CONTENT_RESEARCH_PROVIDER", "parallel")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    monkeypatch.setenv("RESEARCH_VIA_PROXY", "true")
    with patch.object(cr, "_research_direct") as direct, patch.object(cr, "proxy_route_open") as proxy:
        assert cr.research_topic("AI")["sources"] == [{"url": "https://example.org/report"}]
    direct.assert_not_called()
    proxy.assert_not_called()


def test_explicit_perplexity_failure_never_switches_to_parallel(parallel_transport, monkeypatch):
    from cqc_lem.utilities.ai import content_research as cr

    monkeypatch.setenv("CONTENT_RESEARCH_PROVIDER", "perplexity")
    with patch.object(cr, "_research_direct", side_effect=RuntimeError("unit-test fixture: no key")):
        assert cr.research_topic("AI") == {"findings": "", "sources": []}
    assert parallel_transport.requests == []
