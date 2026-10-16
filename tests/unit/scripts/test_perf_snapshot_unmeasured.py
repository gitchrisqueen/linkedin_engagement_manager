"""perf_snapshot.sh writes null, never 0, for an engagement count it could not read.

From 2026-10-08 the host cron could no longer read the DB credentials, every query came back empty,
and the `:-0` defaults wrote all-zero rows that read as real measurements ("unscored is never zero").
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "perf_snapshot.sh"

_COUNT_KEYS = {
    "d1": ("comments", "replies", "dms", "reactions", "posts"),
    "cumulative": (
        "posts_tracked", "own_reactions", "own_comments", "own_impressions",
        "engagers", "commented_posts", "followups",
    ),
}


def _run(tmp_path: Path, sudo_body: str) -> tuple[dict, str]:
    """Run the snapshot with a stub `sudo` on PATH; return the JSON line and snapshot.log."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sudo = bin_dir / "sudo"
    sudo.write_text(f"#!/usr/bin/env bash\n{sudo_body}\n", encoding="utf-8")
    sudo.chmod(0o755)
    perf = tmp_path / "perf"
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "PERF_DIR": str(perf),
        "LEM_ENV_FILE": str(tmp_path / "missing.env"),
        "LEM_ROOT": str(tmp_path),
        "HOME": os.environ.get("HOME", str(tmp_path)),
    }
    subprocess.run(["bash", str(_SCRIPT)], env=env, check=True, capture_output=True, text=True)
    lines = (perf / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    return json.loads(lines[0]), (perf / "snapshot.log").read_text(encoding="utf-8")


class TestUnreadableCountsAreNull:
    def test_unreadable_credentials_write_null_counts_and_say_why(self, tmp_path):
        row, log = _run(tmp_path, "exit 1")

        for block, keys in _COUNT_KEYS.items():
            for key in keys:
                assert row[block][key] is None, f"{block}.{key}"
        assert "DB credentials not readable" in log
        assert "snapshot written" in log

    def test_empty_query_results_write_null_counts_and_say_why(self, tmp_path):
        # Credentials read fine, but every docker exec (queries and margin) returns nothing.
        body = (
            'if [ "$2" = grep ]; then case "$4" in '
            '*USER*) echo MYSQL_USER=u;; *PASSWORD*) echo MYSQL_PASSWORD=p;; *DATABASE*) echo MYSQL_DATABASE=d;; '
            "esac; exit 0; fi\nexit 1"
        )
        row, log = _run(tmp_path, body)

        assert row["cumulative"]["posts_tracked"] is None
        assert row["d1"]["comments"] is None
        assert "queries against mysql_db returned nothing" in log

    def test_real_counts_pass_through_as_integers(self, tmp_path):
        body = (
            'if [ "$2" = grep ]; then case "$4" in '
            '*USER*) echo MYSQL_USER=u;; *PASSWORD*) echo MYSQL_PASSWORD=p;; *DATABASE*) echo MYSQL_DATABASE=d;; '
            "esac; exit 0; fi\n"
            'case "$*" in *CONCAT_WS*) echo 61,10,4,900;; *mysql*) echo 7;; *) exit 1;; esac'
        )
        row, log = _run(tmp_path, body)

        assert row["cumulative"]["posts_tracked"] == 61
        assert row["cumulative"]["own_impressions"] == 900
        assert row["cumulative"]["commented_posts"] == 7
        assert row["d1"]["comments"] == 7
        assert "unavailable" not in log.replace("margin block unavailable", "")
