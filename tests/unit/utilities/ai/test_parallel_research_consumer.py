"""Scripted writer tests keep the real research resolver and MCP transport in the path."""

from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


def test_anonymous_search_excerpts_reach_industry_news_writer(monkeypatch, parallel_transport):
    """The normal post writer consumes research from SDK tool dispatch without credentials."""
    from cqc_lem.utilities.ai import ai_helper

    for name in ("CONTENT_RESEARCH_PROVIDER", "PERPLEXITY_API_KEY", "RESEARCH_VIA_PROXY",
                 "CONTENT_RESEARCH_ENABLED", "POST_RESEARCH_ENABLED", "PARALLEL_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    parallel_transport.result = {"results": [{
        "title": "Example research institute",
        "url": "https://example.org/research",
        "excerpts": ["Example Institute reports a 2026 improvement in AI reliability."],
    }]}
    profile = MagicMock()
    profile.model_dump_json.return_value = '{"full_name": "Jane", "job_title": "CTO"}'
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="A grounded draft."))]
    ai = "cqc_lem.utilities.ai.ai_helper"
    with patch(f"{ai}.get_industries_of_profile_from_ai", return_value="Technology"), \
            patch(f"{ai}.search_recent_news") as google_news, \
            patch(f"{ai}._call_llm", return_value=response) as writer:
        ai_helper.get_industry_news_post_from_ai(
            profile, "awareness", prefs={"focus_topics": ["AI reliability"]}, post_id=7)

    content = writer.call_args.kwargs["messages"][1]["content"]
    prompt = content[0]["text"] if isinstance(content, list) else content
    assert "Example Institute reports a 2026 improvement" in prompt
    assert "https://example.org/research" in prompt
    google_news.assert_not_called()
    assert parallel_transport.requests
