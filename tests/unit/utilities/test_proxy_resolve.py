"""Unit tests for proxy resolution (zero-setup, country-based)."""

import pytest

from cqc_lem.utilities.proxy import resolve_proxy

pytestmark = pytest.mark.unit


def test_explicit_override_wins(monkeypatch):
    monkeypatch.setenv("REGION_PROXIES", '{"US":"http://region:3128"}')
    monkeypatch.setenv("PROXY_URL", "http://global:3128")
    assert resolve_proxy("http://explicit:8080", "US") == "http://explicit:8080"


def test_region_matched_by_country(monkeypatch):
    monkeypatch.setenv("REGION_PROXIES", '{"US":"http://us:3128","GB":"http://gb:3128"}')
    assert resolve_proxy(None, "GB") == "http://gb:3128"
    assert resolve_proxy(None, "us") == "http://us:3128"  # case-insensitive


def test_region_default_when_country_unmapped(monkeypatch):
    monkeypatch.setenv("REGION_PROXIES", '{"US":"http://us:3128","DEFAULT":"http://def:3128"}')
    assert resolve_proxy(None, "FR") == "http://def:3128"


def test_falls_back_to_global_proxy_url(monkeypatch):
    monkeypatch.delenv("REGION_PROXIES", raising=False)
    monkeypatch.setenv("PROXY_URL", "http://global:3128")
    assert resolve_proxy(None, "FR") == "http://global:3128"


def test_none_when_nothing_configured(monkeypatch):
    monkeypatch.delenv("REGION_PROXIES", raising=False)
    monkeypatch.delenv("PROXY_URL", raising=False)
    assert resolve_proxy(None, "US") is None


def test_no_country_no_default_falls_through(monkeypatch):
    monkeypatch.setenv("REGION_PROXIES", '{"US":"http://us:3128"}')
    monkeypatch.delenv("PROXY_URL", raising=False)
    assert resolve_proxy(None, None) is None


def test_malformed_region_json_is_ignored(monkeypatch):
    monkeypatch.setenv("REGION_PROXIES", "{not json")
    monkeypatch.setenv("PROXY_URL", "http://global:3128")
    assert resolve_proxy(None, "US") == "http://global:3128"
