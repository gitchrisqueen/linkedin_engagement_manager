"""Unit tests for apply_proxy (Selenium egress proxy wiring)."""

import pytest
from unittest.mock import MagicMock

from cqc_lem.utilities.selenium_util import apply_proxy

pytestmark = pytest.mark.unit


def _args(options):
    return [c.args[0] for c in options.add_argument.call_args_list]


def test_plain_host_port():
    opts = MagicMock()
    apply_proxy(opts, "http://10.0.0.5:8080")
    assert "--proxy-server=http://10.0.0.5:8080" in _args(opts)


def test_socks_scheme_preserved():
    opts = MagicMock()
    apply_proxy(opts, "socks5://exit.local:1080")
    assert "--proxy-server=socks5://exit.local:1080" in _args(opts)


def test_inline_credentials_stripped_from_proxy_server():
    opts = MagicMock()
    apply_proxy(opts, "http://user:secret@host.example:3128")
    # creds must NOT appear in the --proxy-server arg
    proxy_args = [a for a in _args(opts) if a.startswith("--proxy-server")]
    assert proxy_args == ["--proxy-server=http://host.example:3128"]
    assert all("secret" not in a for a in _args(opts))


def test_invalid_url_no_host_is_ignored():
    opts = MagicMock()
    apply_proxy(opts, "not-a-url")
    assert not any(a.startswith("--proxy-server") for a in _args(opts))


def test_default_scheme_when_missing():
    opts = MagicMock()
    apply_proxy(opts, "//bare.host:9000")
    assert "--proxy-server=http://bare.host:9000" in _args(opts)
