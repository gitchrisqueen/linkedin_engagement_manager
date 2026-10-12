"""Regression tests for the backup-freshness check in scripts/stack_watchdog.sh (#1090)."""

import json
import os
import re
import subprocess
import time
from pathlib import Path

import pytest

WATCHDOG_SH = Path(__file__).resolve().parents[3] / "scripts" / "stack_watchdog.sh"


def _touch(tmp_path: Path, pattern: str, age_hours: float, size_bytes: int = 2048) -> Path:
    """Create a file with the given name pattern, mtime and size."""
    f = tmp_path / pattern
    f.write_bytes(b"x" * size_bytes)
    mtime = time.time() - (age_hours * 3600)
    os.utime(f, (mtime, mtime))
    return f


def _run(tmp_path: Path, bash_code: str) -> subprocess.CompletedProcess[str]:
    """Source stack_watchdog.sh with a fake state/env dir and run bash_code."""
    env = os.environ.copy()
    env["LEM_DIR"] = str(tmp_path)
    env["LEM_ENV_FILE"] = str(tmp_path / ".env")
    env["WATCHDOG_STATE_DIR"] = str(tmp_path / "state")
    env["WATCHDOG_BACKUP_AGE_HOURS"] = "48"
    env["WATCHDOG_SH"] = str(WATCHDOG_SH)

    # A minimal .env so env_value never falls through to a real /opt/lem/.env.
    (tmp_path / ".env").write_text("POSTHOG_API_KEY=\n", encoding="utf-8")

    return subprocess.run(
        ["bash", "-c", bash_code],
        capture_output=True,
        text=True,
        env=env,
    )


class TestBackupFreshness:
    def test_fresh_db_backup_is_not_down(self, tmp_path: Path) -> None:
        backups = tmp_path / "backups"
        backups.mkdir()
        (tmp_path / ".env").write_text(f"BACKUP_DIR={backups}\n", encoding="utf-8")
        _touch(backups, "db-20260808-030001.sql.gz", age_hours=12)

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=0" in result.stdout

    def test_stale_db_backup_is_reported_down(self, tmp_path: Path) -> None:
        backups = tmp_path / "backups"
        backups.mkdir()
        (tmp_path / ".env").write_text(f"BACKUP_DIR={backups}\n", encoding="utf-8")
        _touch(backups, "db-20260806-030001.sql.gz", age_hours=50)

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=1" in result.stdout
        assert "backup:db:stale:" in result.stdout

    def test_missing_db_backup_is_reported_down(self, tmp_path: Path) -> None:
        backups = tmp_path / "backups"
        backups.mkdir()
        (tmp_path / ".env").write_text(f"BACKUP_DIR={backups}\n", encoding="utf-8")

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=1" in result.stdout
        assert "backup:db:missing" in result.stdout

    def test_fresh_but_empty_db_backup_is_reported_down(self, tmp_path: Path) -> None:
        """A dump that failed still leaves a valid, FRESH 20-byte .gz — age alone would pass it."""
        backups = tmp_path / "backups"
        backups.mkdir()
        (tmp_path / ".env").write_text(f"BACKUP_DIR={backups}\n", encoding="utf-8")
        _touch(backups, "db-20260808-030001.sql.gz", age_hours=1, size_bytes=20)

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=1" in result.stdout
        assert "backup:db:empty:20b" in result.stdout

    def test_missing_backup_directory_is_reported_down(self, tmp_path: Path) -> None:
        """No backups directory at all is the same fault as no dump inside one."""
        (tmp_path / ".env").write_text(
            f"BACKUP_DIR={tmp_path / 'nope'}\n", encoding="utf-8"
        )

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=1" in result.stdout
        assert "backup:db:missing" in result.stdout

    def test_stale_chrome_profile_backup_warns_but_is_not_down(self, tmp_path: Path) -> None:
        """A decommissioned chrome-profile volume must not alert forever — cookies live in the DB."""
        backups = tmp_path / "backups"
        backups.mkdir()
        (tmp_path / ".env").write_text(f"BACKUP_DIR={backups}\n", encoding="utf-8")
        _touch(backups, "db-20260808-030001.sql.gz", age_hours=12)
        _touch(backups, "chrome-profile-20260806-030001.tar.gz", age_hours=50, size_bytes=500)

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=0" in result.stdout
        assert "50h old" in result.stdout

    def test_missing_chrome_profile_backup_is_not_down(self, tmp_path: Path) -> None:
        backups = tmp_path / "backups"
        backups.mkdir()
        (tmp_path / ".env").write_text(f"BACKUP_DIR={backups}\n", encoding="utf-8")
        _touch(backups, "db-20260808-030001.sql.gz", age_hours=12)

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=0" in result.stdout
        assert "chrome-profile" not in result.stdout

    def test_tiny_chrome_profile_archive_logs_warning(self, tmp_path: Path) -> None:
        backups = tmp_path / "backups"
        backups.mkdir()
        (tmp_path / ".env").write_text(f"BACKUP_DIR={backups}\n", encoding="utf-8")
        _touch(backups, "db-20260808-030001.sql.gz", age_hours=12)
        _touch(backups, "chrome-profile-20260808-030001.tar.gz", age_hours=12, size_bytes=87)

        result = _run(
            tmp_path,
            'source "$WATCHDOG_SH"; check_backup_freshness',
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "only 87 bytes" in result.stdout
        assert "cookies now live encrypted in the database" in result.stdout
        assert "down=0" not in result.stdout  # not a down event


class TestTunnelOrigins:
    """The tunnel-origin check (`check_tunnel_origins`).

    The fault it exists for: cloudflared running and green while every request it forwards is
    dropped at the origin. A ufw rule pinned to a container IP stopped matching after cloudflared
    was handed a new one, and GitHub webhook deliveries timed out for fifteen days with nothing red.
    """

    @staticmethod
    def _fake_docker(tmp_path: Path, *, status: str, logs: str, logs_rc: int = 0) -> Path:
        """A `docker` stub on PATH — the cloudflared image has no shell, so the real check reads logs."""
        bindir = tmp_path / "bin"
        bindir.mkdir(exist_ok=True)
        stub = bindir / "docker"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "inspect" ]]; then\n'
            f'  printf "%s\\n" {status!r}\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "logs" ]]; then\n'
            f"  cat <<'LOGEOF'\n{logs}\nLOGEOF\n"
            f"  exit {logs_rc}\n"
            "fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        return bindir

    def _run_check(self, tmp_path: Path, bindir: Path, extra: str = "") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["LEM_DIR"] = str(tmp_path)
        env["LEM_ENV_FILE"] = str(tmp_path / ".env")
        env["WATCHDOG_STATE_DIR"] = str(tmp_path / "state")
        env["WATCHDOG_SH"] = str(WATCHDOG_SH)
        env["PATH"] = f"{bindir}:{env['PATH']}"
        (tmp_path / ".env").write_text("POSTHOG_API_KEY=\n", encoding="utf-8")
        return subprocess.run(
            [
                "bash",
                "-c",
                f'source "$WATCHDOG_SH"; {extra} check_tunnel_origins; '
                'echo "down=${#down[@]}"; echo "recovered=${#recovered[@]}"; '
                'printf "%s\\n" "${down[@]}"',
            ],
            capture_output=True,
            text=True,
            env=env,
        )

    ERRORS = "\n".join(
        'ERR error="Unable to reach the origin service. The service may be down or it may not be '
        'responding to traffic from cloudflared: dial tcp 172.18.0.1:8420: i/o timeout" '
        "connIndex=0 ingressRule=5 originService=http://172.18.0.1:8420"
        for _ in range(6)
    )

    def test_healthy_tunnel_is_not_down(self, tmp_path: Path) -> None:
        bindir = self._fake_docker(tmp_path, status="running", logs="INF Registered tunnel connection")
        result = self._run_check(tmp_path, bindir)
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=0" in result.stdout

    def test_errors_under_threshold_are_not_down(self, tmp_path: Path) -> None:
        one = self.ERRORS.split("\n")[0]
        bindir = self._fake_docker(tmp_path, status="running", logs=one)
        result = self._run_check(tmp_path, bindir)
        assert "down=0" in result.stdout

    def test_first_sighting_starts_a_grace_window_and_does_not_alert(self, tmp_path: Path) -> None:
        """A deploy recreates an origin container; the first burst of errors must not page."""
        bindir = self._fake_docker(tmp_path, status="running", logs=self.ERRORS)
        result = self._run_check(tmp_path, bindir)
        assert "down=0" in result.stdout
        assert "starting grace window" in result.stdout
        assert (tmp_path / "state" / "tunnel-origin.down").exists()

    def test_still_failing_past_grace_is_reported_down_and_names_the_origin(self, tmp_path: Path) -> None:
        bindir = self._fake_docker(tmp_path, status="running", logs=self.ERRORS)
        state = tmp_path / "state"
        state.mkdir(exist_ok=True)
        # First seen well outside the grace window.
        (state / "tunnel-origin.down").write_text(f"{int(time.time()) - 9999} http://172.18.0.1:8420\n")

        result = self._run_check(tmp_path, bindir)
        assert "down=1" in result.stdout
        # The alert must name the origin, so it points at the rule to fix, not at "the tunnel".
        assert "tunnel-origin:http://172.18.0.1:8420" in result.stdout

    def test_recovery_clears_the_marker(self, tmp_path: Path) -> None:
        bindir = self._fake_docker(tmp_path, status="running", logs="INF Registered tunnel connection")
        state = tmp_path / "state"
        state.mkdir(exist_ok=True)
        marker = state / "tunnel-origin.down"
        marker.write_text(f"{int(time.time()) - 9999} http://172.18.0.1:8420\n")

        result = self._run_check(tmp_path, bindir)
        assert "down=0" in result.stdout
        assert "recovered=1" in result.stdout
        assert not marker.exists()

    def test_missing_container_is_unreadable_not_a_fault(self, tmp_path: Path) -> None:
        """Absence of Docker is not evidence of an outage — it must never alert."""
        bindir = tmp_path / "bin"
        bindir.mkdir(exist_ok=True)
        stub = bindir / "docker"
        stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
        stub.chmod(0o755)

        result = self._run_check(tmp_path, bindir)
        assert "down=0" in result.stdout
        assert "skipping tunnel origin check" in result.stdout

    def test_stopped_container_is_left_to_check_services(self, tmp_path: Path) -> None:
        """One incident, one row: check_services already reports a container that is not running."""
        bindir = self._fake_docker(tmp_path, status="exited", logs=self.ERRORS)
        result = self._run_check(tmp_path, bindir)
        assert "down=0" in result.stdout


class TestAlertEmailResolution:
    """Recipient resolution (`resolve_alert_email`, #1804).

    `WATCHDOG_ALERT_EMAIL=you@example.com` — a copy-pasted placeholder from docs/install-script
    sample text — silently disabled alerting for an unknown length of time: `${TO:-fallback}` only
    ever catches empty, never garbage, so the placeholder beat the correct `COST_ALERT_EMAIL` sitting
    three lines below it in the same `.env`.
    """

    def _resolve(
        self, tmp_path: Path, env_contents: str, extra_env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("WATCHDOG_ALERT_EMAIL", None)
        env["LEM_DIR"] = str(tmp_path)
        env["LEM_ENV_FILE"] = str(tmp_path / ".env")
        env["WATCHDOG_STATE_DIR"] = str(tmp_path / "state")
        env["WATCHDOG_SH"] = str(WATCHDOG_SH)
        env.update(extra_env or {})
        (tmp_path / ".env").write_text(env_contents, encoding="utf-8")
        return subprocess.run(
            ["bash", "-c", 'source "$WATCHDOG_SH"; resolve_alert_email'],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_valid_configured_value_wins(self, tmp_path: Path) -> None:
        result = self._resolve(tmp_path, "WATCHDOG_ALERT_EMAIL=ops@realcompany.com\n")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "ops@realcompany.com"
        assert "ERROR" not in result.stderr + result.stdout

    def test_placeholder_is_rejected_and_falls_through_to_cost_alert_email(self, tmp_path: Path) -> None:
        result = self._resolve(
            tmp_path,
            "WATCHDOG_ALERT_EMAIL=you@example.com\nCOST_ALERT_EMAIL=finance@realcompany.com\n",
        )
        assert result.returncode == 0, result.stderr
        # Every call site does `TO="$(resolve_alert_email)"` — stdout IS the resolved recipient, so
        # it must be the address alone, never an ERROR line mixed in (that corrupts the "to" address
        # SendGrid receives instead of just being visible).
        assert result.stdout.strip() == "finance@realcompany.com"
        # Discarding a configured-but-bad value is still logged loudly (to stderr, so it reaches the
        # journal without landing in the captured recipient), not silently ignored.
        assert "ERROR" in result.stderr
        assert "you@example.com" in result.stderr

    def test_changeme_placeholder_is_also_rejected(self, tmp_path: Path) -> None:
        result = self._resolve(
            tmp_path,
            "WATCHDOG_ALERT_EMAIL=changeme@realcompany.com\nCOST_ALERT_EMAIL=finance@realcompany.com\n",
        )
        assert result.stdout.strip().splitlines()[-1] == "finance@realcompany.com"

    def test_empty_value_falls_through(self, tmp_path: Path) -> None:
        result = self._resolve(tmp_path, "WATCHDOG_ALERT_EMAIL=\nCOST_ALERT_EMAIL=finance@realcompany.com\n")
        assert result.stdout.strip().splitlines()[-1] == "finance@realcompany.com"

    def test_placeholder_cost_alert_email_also_falls_through_to_terminal_default(self, tmp_path: Path) -> None:
        result = self._resolve(
            tmp_path,
            "WATCHDOG_ALERT_EMAIL=you@example.com\nCOST_ALERT_EMAIL=billing@example.org\n",
        )
        assert result.stdout.strip() == "christopher.queen@gmail.com"
        assert result.stderr.count("ERROR") == 2  # both discards logged, on stderr

    def test_nothing_configured_terminates_in_a_real_address(self, tmp_path: Path) -> None:
        result = self._resolve(tmp_path, "")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().splitlines()[-1] == "christopher.queen@gmail.com"

    def test_process_env_var_overrides_env_file(self, tmp_path: Path) -> None:
        result = self._resolve(
            tmp_path,
            "WATCHDOG_ALERT_EMAIL=fromfile@realcompany.com\n",
            extra_env={"WATCHDOG_ALERT_EMAIL": "fromenv@realcompany.com"},
        )
        assert result.stdout.strip().splitlines()[-1] == "fromenv@realcompany.com"


class TestOffsiteBackupFreshness:
    """The off-host copy alerts only once BACKUP_REMOTE is set (docs/offsite-backups.md)."""

    _CHECK = (
        'printf "%s\\n" "$ENV_LINE" > "$LEM_ENV_FILE"; source "$WATCHDOG_SH"; '
        'check_backup_freshness; echo "down=${#down[@]}"; printf "%s\\n" "${down[@]}"'
    )

    def _check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, env_line: str
    ) -> subprocess.CompletedProcess[str]:
        backups = tmp_path / "backups"
        backups.mkdir(exist_ok=True)
        _touch(backups, "db-20261010-030001.sql.gz", age_hours=12)
        # _run rewrites the .env, so the line under test is written from inside the bash run.
        monkeypatch.setenv("ENV_LINE", env_line)
        return _run(tmp_path, self._CHECK)

    def test_unset_remote_never_alerts_without_a_marker(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = self._check(tmp_path, monkeypatch, "POSTHOG_API_KEY=")
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=0" in result.stdout

    def test_set_remote_with_no_marker_is_reported_down(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = self._check(tmp_path, monkeypatch, "BACKUP_REMOTE=lem-offsite:")
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=1" in result.stdout
        assert "backup:offsite:missing" in result.stdout

    def test_set_remote_with_a_fresh_marker_is_not_down(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "backups").mkdir()
        _touch(tmp_path / "backups", ".offsite-last-ok", age_hours=12)
        result = self._check(tmp_path, monkeypatch, "BACKUP_REMOTE=lem-offsite:")
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=0" in result.stdout

    def test_set_remote_with_a_stale_marker_is_reported_down(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "backups").mkdir()
        _touch(tmp_path / "backups", ".offsite-last-ok", age_hours=50)
        result = self._check(tmp_path, monkeypatch, "BACKUP_REMOTE=lem-offsite:")
        assert result.returncode == 0, result.stderr + result.stdout
        assert "down=1" in result.stdout
        assert "backup:offsite:stale:50h" in result.stdout


class TestAlertDedupe:
    """Email dedupe, the local event log and the SendGrid payload (`report`).

    One outage used to send an identical email on every 5-minute run while it lasted. Each test
    drives `report` with a fixed `down`/`recovered` set, a fake clock and a `curl` stub that records
    every payload it is handed, so "how many emails" is a line count rather than an inference.
    """

    DOWN = "tunnel-origin:http://172.18.0.1:8420:6in600s"
    T0 = 1_800_000_000

    @staticmethod
    def _bindir(tmp_path: Path) -> Path:
        """A `curl` stub that appends each `-d` payload (compact JSON, one line) to $CURL_LOG."""
        bindir = tmp_path / "bin"
        bindir.mkdir(exist_ok=True)
        stub = bindir / "curl"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'prev=""\n'
            'for a in "$@"; do\n'
            '  if [[ "$prev" == "-d" ]]; then printf "%s\\n" "$a" >> "$CURL_LOG"; fi\n'
            '  prev="$a"\n'
            "done\n"
            "exit 0\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        return bindir

    def _report(
        self,
        tmp_path: Path,
        *,
        now: int,
        down: list[str] | None = None,
        recovered: list[str] | None = None,
        pre: str = "",
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        for var in ("WATCHDOG_ALERT_EMAIL", "WATCHDOG_REMINDER_SECONDS", "WATCHDOG_EVENT_FILE"):
            env.pop(var, None)
        env["LEM_DIR"] = str(tmp_path)
        env["LEM_ENV_FILE"] = str(tmp_path / ".env")
        env["WATCHDOG_STATE_DIR"] = str(tmp_path / "state")
        env["WATCHDOG_SH"] = str(WATCHDOG_SH)
        env["CURL_LOG"] = str(tmp_path / "curl.log")
        env["FAKE_NOW"] = str(now)
        env["PATH"] = f"{self._bindir(tmp_path)}:{env['PATH']}"
        env.update(extra_env or {})
        (tmp_path / ".env").write_text(
            "POSTHOG_API_KEY=\nSENDGRID_API_KEY=sg-test\nSENDGRID_FROM_EMAIL=alerts@realcompany.com\n"
            "WATCHDOG_ALERT_EMAIL=ops@realcompany.com\n",
            encoding="utf-8",
        )
        down_arr = " ".join(f"'{d}'" for d in (down or []))
        rec_arr = " ".join(f"'{r}'" for r in (recovered or []))
        return subprocess.run(
            [
                "bash",
                "-c",
                'source "$WATCHDOG_SH"; now() { echo "$FAKE_NOW"; }; '
                f"down=({down_arr}); recovered=({rec_arr}); {pre} report",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

    @staticmethod
    def _emails(tmp_path: Path) -> list[dict]:
        log = tmp_path / "curl.log"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]

    @staticmethod
    def _events(tmp_path: Path) -> list[dict]:
        f = tmp_path / "state" / "events.jsonl"
        if not f.exists():
            return []
        return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line]

    def test_first_down_emails_once_and_writes_a_down_event(self, tmp_path: Path) -> None:
        result = self._report(tmp_path, down=[self.DOWN], now=self.T0)
        assert result.returncode == 1, result.stderr + result.stdout

        emails = self._emails(tmp_path)
        assert len(emails) == 1
        assert emails[0]["subject"].startswith("[LEM] stack watchdog DOWN:")

        events = self._events(tmp_path)
        assert len(events) == 1
        event = events[0]
        assert set(event) == {"ts", "check", "host", "state", "detail"}
        assert event["check"] == "tunnel-origin"
        assert event["state"] == "DOWN"
        assert event["detail"] == self.DOWN
        assert event["host"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", event["ts"])
        # Readable by a non-root account.
        assert ((tmp_path / "state" / "events.jsonl").stat().st_mode & 0o777) == 0o644

    def test_second_run_within_the_reminder_interval_sends_nothing(self, tmp_path: Path) -> None:
        self._report(tmp_path, down=[self.DOWN], now=self.T0)
        # Same check, different token (the error count moved), five minutes later.
        result = self._report(
            tmp_path, down=["tunnel-origin:http://172.18.0.1:8420:9in600s"], now=self.T0 + 300
        )
        assert result.returncode == 1, result.stderr + result.stdout
        assert len(self._emails(tmp_path)) == 1
        assert len(self._events(tmp_path)) == 1

    def test_run_after_the_reminder_interval_sends_one_reminder(self, tmp_path: Path) -> None:
        self._report(tmp_path, down=[self.DOWN], now=self.T0)
        self._report(tmp_path, down=[self.DOWN], now=self.T0 + 300)
        result = self._report(tmp_path, down=[self.DOWN], now=self.T0 + 3600)
        assert result.returncode == 1, result.stderr + result.stdout
        # The reminder resets the clock: the very next run is quiet again.
        self._report(tmp_path, down=[self.DOWN], now=self.T0 + 3900)

        emails = self._emails(tmp_path)
        assert len(emails) == 2
        assert emails[1]["subject"].startswith("[LEM] stack watchdog STILL DOWN:")
        assert [e["state"] for e in self._events(tmp_path)] == ["DOWN", "DOWN"]

    def test_reminder_interval_is_configurable(self, tmp_path: Path) -> None:
        extra = {"WATCHDOG_REMINDER_SECONDS": "600"}
        self._report(tmp_path, down=[self.DOWN], now=self.T0, extra_env=extra)
        self._report(tmp_path, down=[self.DOWN], now=self.T0 + 300, extra_env=extra)
        self._report(tmp_path, down=[self.DOWN], now=self.T0 + 600, extra_env=extra)
        assert len(self._emails(tmp_path)) == 2

    def test_clearing_writes_recovered_and_sends_one_recovered_email(self, tmp_path: Path) -> None:
        self._report(tmp_path, down=[self.DOWN], now=self.T0)
        result = self._report(tmp_path, recovered=["tunnel-origin"], now=self.T0 + 900)
        assert result.returncode == 0, result.stderr + result.stdout
        # Nothing left to say: the run after a recovery is silent.
        self._report(tmp_path, now=self.T0 + 1200)

        emails = self._emails(tmp_path)
        assert len(emails) == 2
        assert emails[1]["subject"].startswith("[LEM] stack watchdog RECOVERED:")
        events = self._events(tmp_path)
        assert [(e["check"], e["state"]) for e in events] == [
            ("tunnel-origin", "DOWN"),
            ("tunnel-origin", "RECOVERED"),
        ]

    def test_a_check_that_clears_without_a_recovered_token_still_recovers(self, tmp_path: Path) -> None:
        """A backup check never reports `recovered`; it simply stops being down."""
        self._report(tmp_path, down=["backup:db:stale:50h"], now=self.T0)
        self._report(tmp_path, now=self.T0 + 300)
        events = self._events(tmp_path)
        assert [(e["check"], e["state"]) for e in events] == [
            ("backup-db", "DOWN"),
            ("backup-db", "RECOVERED"),
        ]
        assert len(self._emails(tmp_path)) == 2

    def test_an_unreadable_check_is_not_recovered(self, tmp_path: Path) -> None:
        """A skipped tunnel check is not evidence of recovery; its alert state must survive."""
        self._report(tmp_path, down=[self.DOWN], now=self.T0)
        result = self._report(tmp_path, pre="unknown=(tunnel-origin);", now=self.T0 + 300)
        assert result.returncode == 0, result.stderr + result.stdout
        assert [e["state"] for e in self._events(tmp_path)] == ["DOWN"]
        assert len(self._emails(tmp_path)) == 1
        assert (tmp_path / "state" / "alert-tunnel-origin.state").exists()

    def test_failed_send_is_retried_next_run(self, tmp_path: Path) -> None:
        """An undelivered DOWN email must not be mistaken for a delivered one and suppressed."""
        failing = tmp_path / "failbin"
        failing.mkdir()
        (failing / "curl").write_text("#!/usr/bin/env bash\nexit 22\n", encoding="utf-8")
        (failing / "curl").chmod(0o755)
        env = os.environ.copy()
        result = self._report(
            tmp_path, down=[self.DOWN], now=self.T0, extra_env={"PATH": f"{failing}:{env['PATH']}"}
        )
        assert "WARN: SendGrid send failed" in result.stdout
        self._report(tmp_path, down=[self.DOWN], now=self.T0 + 300)
        emails = self._emails(tmp_path)
        assert len(emails) == 1
        assert emails[0]["subject"].startswith("[LEM] stack watchdog DOWN:")
        # Still one DOWN event: the retry is an email, not a new state change.
        assert len(self._events(tmp_path)) == 1

    def test_event_file_write_failure_does_not_change_the_exit_code(self, tmp_path: Path) -> None:
        # A directory where the file should be: every append fails.
        blocked = tmp_path / "blocked"
        blocked.mkdir()
        result = self._report(
            tmp_path, down=[self.DOWN], now=self.T0, extra_env={"WATCHDOG_EVENT_FILE": str(blocked)}
        )
        assert result.returncode == 1, result.stderr + result.stdout
        assert "WARN: could not append to event file" in result.stdout
        assert len(self._emails(tmp_path)) == 1

    def test_event_file_is_capped(self, tmp_path: Path) -> None:
        state = tmp_path / "state"
        state.mkdir()
        (state / "events.jsonl").write_text('{"old":1}\n' * 2000, encoding="utf-8")
        self._report(tmp_path, down=[self.DOWN], now=self.T0)
        lines = (state / "events.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2000
        assert json.loads(lines[-1])["state"] == "DOWN"

    def test_payload_disables_click_tracking_and_stays_plain_text(self, tmp_path: Path) -> None:
        self._report(tmp_path, down=[self.DOWN], now=self.T0)
        payload = self._emails(tmp_path)[0]
        assert payload["tracking_settings"] == {"click_tracking": {"enable": False, "enable_text": False}}
        assert [c["type"] for c in payload["content"]] == ["text/plain"]

    def test_heal_emails_once_and_writes_a_healed_event(self, tmp_path: Path) -> None:
        result = self._report(tmp_path, pre="healed=(celery_beat);", now=self.T0)
        assert result.returncode == 0, result.stderr + result.stdout
        emails = self._emails(tmp_path)
        assert len(emails) == 1
        assert emails[0]["subject"].startswith("[LEM] stack watchdog AUTO-STARTED:")
        assert [(e["check"], e["state"]) for e in self._events(tmp_path)] == [("celery_beat", "HEALED")]

    def test_nothing_down_sends_nothing(self, tmp_path: Path) -> None:
        result = self._report(tmp_path, now=self.T0)
        assert result.returncode == 0, result.stderr + result.stdout
        assert self._emails(tmp_path) == []
        assert self._events(tmp_path) == []
