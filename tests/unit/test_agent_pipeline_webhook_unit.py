"""The repo copy of the webhook unit must match what the box runs.

The installed unit binds the tunnel origin and loopback explicitly, and installing a copy that lost
either would leave a receiver that is up and unreachable (tunnel) or reported dead (watchdog).
"""

from __future__ import annotations

from pathlib import Path

UNIT = (
    Path(__file__).resolve().parents[2]
    / "scripts" / "agent-pipeline" / "v2" / "systemd" / "lem-agent-webhook.service"
)


def _exec_start() -> str:
    """Return the unit's ExecStart line."""
    return next(ln for ln in UNIT.read_text().splitlines() if ln.startswith("ExecStart="))


def test_the_unit_binds_the_tunnel_origin_and_loopback():
    """The tunnel (cloudflared) reaches the receiver on the lem_default gateway; the watchdog probes loopback."""
    line = _exec_start()
    assert "--bind 172.18.0.1:8420" in line, line
    assert "--bind 127.0.0.1:8420" in line, line


def test_both_binds_share_one_port():
    """serve() only covers several addresses with one socket when they share a port."""
    line = _exec_start()
    ports = {tok.rsplit(":", 1)[1] for tok in line.split() if tok.count(".") == 3 and ":" in tok}
    assert ports == {"8420"}, line


def test_the_unit_keeps_its_hardening():
    """Matching the box must not drop the sandbox around the internet-adjacent process."""
    body = UNIT.read_text()
    for setting in ("NoNewPrivileges=yes", "ProtectSystem=full", "MemoryMax=256M",
                    "EnvironmentFile=/etc/lem/agent-webhook.env"):
        assert setting in body, setting
