"""The prod compose file list resolves the same way everywhere (2026-10-20 grid-orphan outage).

An `up -d cloudflared` run with base + prod only treated the Selenium grid as orphans and removed
the hub, the nine chrome nodes and the debug node. scripts/lib/compose_files.sh gives rollback.sh
and scripts/compose.sh the list deploy.sh resolves inline; these tests hold the two together.
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY = (REPO_ROOT / "scripts" / "deploy.sh").read_text()
LIB = REPO_ROOT / "scripts" / "lib" / "compose_files.sh"


def _deploy_compose(env_file: Path) -> str:
    """Run deploy.sh's own env_value() and topology block, and print the COMPOSE it builds."""
    env_value = DEPLOY[DEPLOY.index("env_value() {"):DEPLOY.index("\n}\n", DEPLOY.index("env_value() {")) + 3]
    start = DEPLOY.index('SELENIUM_TOPOLOGY="${SELENIUM_TOPOLOGY:-')
    block = DEPLOY[start:DEPLOY.index("esac", start) + len("esac")]
    script = f'log() {{ :; }}\nENV_FILE="{env_file}"\n{env_value}\n{block}\necho "$COMPOSE"\n'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True,
                          env={"PATH": "/usr/bin:/bin"}).stdout.strip()


def _lib_compose(env_file: Path) -> str:
    script = f'. "{LIB}"\nlem_compose_cmd "$(lem_selenium_topology "{env_file}")"\n'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True,
                          env={"PATH": "/usr/bin:/bin"}).stdout.strip()


@pytest.mark.parametrize("line", [
    "",                                          # unset: the documented default
    "SELENIUM_TOPOLOGY=grid",
    "SELENIUM_TOPOLOGY=standalone",
    "SELENIUM_TOPOLOGY=Standalone",
    "SELENIUM_TOPOLOGY='standalone' # rollback",
    "SELENIUM_TOPOLOGY=grdi",                    # a typo takes grid, as deploy.sh does
])
def test_lib_matches_deploy(tmp_path, line):
    env_file = tmp_path / ".env"
    env_file.write_text(f"OTHER=1\n{line}\n")

    assert _lib_compose(env_file) == _deploy_compose(env_file)


def test_grid_is_in_the_default_list(tmp_path):
    assert _lib_compose(tmp_path / "missing.env").endswith("-f docker-compose.grid.yml")


def test_a_missing_env_file_still_resolves(tmp_path):
    assert _lib_compose(tmp_path / "missing.env") == _deploy_compose(tmp_path / "missing.env")


@pytest.mark.parametrize("script", ["rollback.sh", "compose.sh"])
def test_scripts_build_their_command_from_the_lib(script):
    """A hand-typed `-f` list is how the grid got left out; these two must not carry one."""
    src = (REPO_ROOT / "scripts" / script).read_text()

    assert 'scripts/lib/compose_files.sh"' in src
    assert "lem_compose_cmd" in src
    assert "docker compose -f" not in src
