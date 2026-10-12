"""The orphan sweep terminates ONLY what a finished lane left behind in its worktree.

Every test runs against a fake /proc tree under `tmp_path` with an injected kill function, so no
real process is ever inspected or signalled.
"""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts" / "agent-pipeline" / "v2"))

from lemd import daemon, db, dispatch, orphans  # noqa: E402

pytestmark = pytest.mark.unit

UID = 1000
DAEMON = 500


class FakeProc:
    """A writable fake /proc whose kill function removes TERM-obedient processes."""

    def __init__(self, root: Path) -> None:
        self.root = root / "proc"
        self.root.mkdir()
        self.signals: list[tuple[int, int]] = []
        self.ignores_term: set[int] = set()

    def add(self, pid: int, *, ppid: int, cwd: str | None, uid: int = UID,
            argv: tuple[str, ...] = ("cmd",), start: int = 100, readable: bool = True,
            comm: str = "x y") -> None:
        d = self.root / str(pid)
        d.mkdir()
        if not readable:
            return  # an entry with no status/stat: what a vanished or foreign pid looks like
        (d / "status").write_text(f"Name:\tx\nPPid:\t{ppid}\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
        fields = ["S", str(ppid)] + ["0"] * 17 + [str(start)]
        (d / "stat").write_text(f"{pid} ({comm}) " + " ".join(fields) + "\n")
        (d / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
        if cwd is not None:
            os.symlink(cwd, d / "cwd")

    def kill(self, pid: int, sig: int) -> None:
        self.signals.append((pid, sig))
        if sig == signal.SIGKILL or pid not in self.ignores_term:
            for f in (self.root / str(pid)).iterdir():
                f.unlink()
            (self.root / str(pid)).rmdir()

    def sweep(self, **kw):
        kw.setdefault("self_pid", DAEMON)
        kw.setdefault("uid", UID)
        clock = iter(range(0, 1000))
        return orphans.sweep(proc_root=self.root, kill=self.kill, sleep=lambda s: None,
                             clock=lambda: next(clock), **kw)


@pytest.fixture
def world(tmp_path: Path):
    work = tmp_path.resolve() / "base" / "work"
    lane = work / "feature" / "claude-issue-1"
    other = work / "feature" / "claude-issue-2"
    for d in (lane, other):
        d.mkdir(parents=True)
        (d / ".git").write_text("gitdir: elsewhere\n")   # what marks a worktree root
    fp = FakeProc(tmp_path)
    fp.add(1, ppid=0, cwd="/")
    fp.add(400, ppid=1, cwd="/")                       # systemd-ish parent of the daemon
    fp.add(DAEMON, ppid=400, cwd=str(tmp_path / "base"))
    return fp, work, lane, other


def test_kills_only_orphans_inside_the_lane_worktree(world) -> None:
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd=str(lane), argv=("pytest", "-n", "8"))     # orphaned master
    fp.add(11, ppid=10, cwd=str(lane))                                 # its xdist worker
    fp.add(12, ppid=1, cwd=str(lane / "src"))                          # orphan in a subdir
    fp.add(20, ppid=1, cwd=str(other))                                 # other worktree
    fp.add(30, ppid=1, cwd="/tmp")                                     # outside work/
    fp.add(31, ppid=1, cwd=str(lane) + "-sibling")                     # prefix, not inside
    fp.add(40, ppid=1, cwd=str(lane), uid=UID + 1)                     # foreign uid
    res = fp.sweep(roots=[lane])
    assert sorted(res.terminated) == [10, 11, 12]
    assert res.killed == []
    assert {p for p, _ in fp.signals} == {10, 11, 12}


def test_argv_path_inside_worktree_counts(world) -> None:
    """The measured `timeout 180 graft build <wt>` ran from the base dir, not the worktree."""
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd="/srv/base", argv=("timeout", "180", "graft", "build", str(lane)))
    assert fp.sweep(roots=[lane]).terminated == [10]


def test_live_lane_and_interactive_shell_are_never_orphans(world) -> None:
    fp, work, lane, other = world
    fp.add(60, ppid=DAEMON, cwd="/srv/base", argv=("agent_run.sh",))   # lane root, outside wt
    fp.add(61, ppid=60, cwd=str(lane))                                 # the agent
    fp.add(62, ppid=61, cwd=str(lane))                                 # its tool, still parented
    fp.add(70, ppid=1, cwd="/home/u")                                  # tmux server
    fp.add(71, ppid=70, cwd=str(lane))                                 # a human shell in work/
    assert fp.sweep(roots=[work]).terminated == []


def test_never_the_daemon_or_its_ancestors(world) -> None:
    fp, work, lane, other = world
    # Even if the daemon and its parent somehow sat inside the worktree, they are untouchable.
    for f in (fp.root / str(DAEMON)).iterdir():
        f.unlink()
    (fp.root / str(DAEMON)).rmdir()
    for f in (fp.root / "400").iterdir():
        f.unlink()
    (fp.root / "400").rmdir()
    fp.add(400, ppid=1, cwd=str(lane))
    fp.add(DAEMON, ppid=400, cwd=str(lane))
    assert fp.sweep(roots=[lane]).terminated == []
    assert fp.signals == []


def test_protected_pid_descendants_are_spared(world) -> None:
    fp, work, lane, other = world
    fp.add(80, ppid=1, cwd=str(lane))
    fp.add(81, ppid=80, cwd=str(lane))
    assert fp.sweep(roots=[lane], lanes=[orphans.LiveLane(80)]).terminated == []


def test_term_then_kill_after_grace(world) -> None:
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd=str(lane))
    fp.add(11, ppid=1, cwd=str(lane))
    fp.ignores_term.add(11)
    res = fp.sweep(roots=[lane], grace=5)
    assert sorted(res.terminated) == [10, 11]
    assert res.killed == [11]
    assert fp.signals == [(10, signal.SIGTERM), (11, signal.SIGTERM), (11, signal.SIGKILL)]


def test_recycled_pid_is_not_killed(world, monkeypatch) -> None:
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd=str(lane), start=100)
    fp.ignores_term.add(10)
    real_kill = fp.kill

    def kill_then_recycle(pid: int, sig: int) -> None:
        real_kill(pid, sig)
        if sig == signal.SIGTERM:  # the pid exits and a new process takes it
            for f in (fp.root / "10").iterdir():
                f.unlink()
            (fp.root / "10").rmdir()
            fp.add(10, ppid=1, cwd=str(lane), start=999)

    fp.kill = kill_then_recycle
    res = fp.sweep(roots=[lane])
    assert res.killed == []
    assert fp.signals == [(10, signal.SIGTERM)]


def test_unreadable_entries_are_skipped(world) -> None:
    fp, work, lane, other = world
    fp.add(90, ppid=1, cwd=None, readable=False)        # no status at all
    fp.add(91, ppid=1, cwd=None)                        # cwd unreadable, argv harmless
    fp.add(92, ppid=93, cwd=str(lane))                  # parent 93 unreadable -> not provable
    fp.add(93, ppid=1, cwd=None, readable=False)
    (fp.root / "self").mkdir()                          # non-numeric entries ignored
    assert fp.sweep(roots=[lane]).terminated == []


def test_missing_proc_root_fails_open(tmp_path: Path) -> None:
    res = orphans.sweep(roots=[tmp_path], proc_root=tmp_path / "nope",
                        kill=lambda p, s: pytest.fail("signalled"), self_pid=1, uid=UID)
    assert res.terminated == []


def test_kill_raising_unexpectedly_fails_open(world) -> None:
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd=str(lane))

    def boom(pid: int, sig: int) -> None:
        raise RuntimeError("nope")

    fp.kill = boom
    assert fp.sweep(roots=[lane]).terminated == []


def test_idle_sweep_excludes_active_worktrees(world) -> None:
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd=str(lane))
    fp.add(20, ppid=1, cwd=str(other))
    res = fp.sweep(roots=[work], exclude_roots=[lane])
    assert res.terminated == [20]


def test_logs_one_info_line_without_command_lines(world, caplog) -> None:
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd=str(lane), argv=("tool", "--token=SECRET"), comm="pytest")
    fp.add(11, ppid=1, cwd="/srv", argv=("timeout", str(lane), "--key=HIDDEN"), comm="timeout")
    with caplog.at_level("INFO", logger="lemd.orphans"):
        fp.sweep(roots=[lane], reason="after x")
    lines = [r.getMessage() for r in caplog.records]
    assert len(lines) == 1
    line = lines[0]
    assert "pids=[10, 11]" in line
    assert f"10:pytest:cwd:{lane}" in line and f"11:timeout:argv:{lane}" in line
    assert "SECRET" not in line and "HIDDEN" not in line and "--token" not in line


def test_detached_same_uid_process_in_unowned_tree_is_terminated(world) -> None:
    """The real boundary: a nohup/setsid job left under work/ is swept once no lane owns the tree."""
    fp, work, lane, other = world
    fp.add(50, ppid=1, cwd=str(other), argv=("nohup", "python", "serve.py"))
    res = fp.sweep(roots=[work], exclude_roots=[lane], lanes=[], work_root=work,
                   require_placement=True, match_argv=False)
    assert res.terminated == [50]


def test_idle_sweep_ignores_argv_only_matches(world) -> None:
    fp, work, lane, other = world
    fp.add(10, ppid=1, cwd="/srv/base", argv=("timeout", "180", "graft", "build", str(other)))
    assert fp.sweep(roots=[work], work_root=work, match_argv=False).terminated == []
    assert fp.sweep(roots=[other], match_argv=True).terminated == [10]


def test_tree_of_a_live_lanes_descendant_is_excluded(world) -> None:
    fp, work, lane, other = world
    fp.add(60, ppid=DAEMON, cwd="/srv/base")              # lane root, branch unknown
    fp.add(61, ppid=60, cwd=str(lane / "src"))            # its agent, inside `lane`
    fp.add(70, ppid=1, cwd=str(lane))                     # escaped tool of the LIVE lane
    fp.add(71, ppid=1, cwd=str(other))                    # a real orphan elsewhere
    res = fp.sweep(roots=[work], lanes=[orphans.LiveLane(60, must_place=True)], work_root=work,
                   require_placement=True, match_argv=False)
    assert res.terminated == [71]


def test_unplaced_live_lane_skips_the_idle_sweep(world) -> None:
    fp, work, lane, other = world
    fp.add(60, ppid=DAEMON, cwd="/srv/base")              # still creating its worktree
    fp.add(71, ppid=1, cwd=str(other))
    res = fp.sweep(roots=[work], lanes=[orphans.LiveLane(60, must_place=True)], work_root=work,
                   require_placement=True, match_argv=False)
    assert res.skipped == "unplaced_lane" and fp.signals == []
    # A lane that need not be placed (gh pool) does not hold the sweep back.
    res = fp.sweep(roots=[work], lanes=[orphans.LiveLane(60)], work_root=work,
                   require_placement=True, match_argv=False)
    assert res.terminated == [71]


# --------------------------------------------------------------------------- supervisor wiring

class _Cfg:
    def __init__(self, base: Path, orphan_sweep: bool = True) -> None:
        self.base = base
        self.repo = base
        self.slug = "o/r"
        self.max_agents = 2
        self.gh_slots = 2
        self.orphan_sweep = orphan_sweep


class _DoneProc:
    pid = 4242

    def poll(self) -> int:
        return 0


class _Running:
    def __init__(self, pid: int) -> None:
        self.pid = pid

    def poll(self):
        return None


def _sup(tmp_path: Path, monkeypatch, **cfg) -> tuple[dispatch.Supervisor, list[dict]]:
    monkeypatch.delenv("WORKROOT", raising=False)
    sup = dispatch.Supervisor(_Cfg(tmp_path, **cfg), db.connect(tmp_path / "q.db"))
    calls: list[dict] = []
    sup.orphan_sweep = lambda **kw: calls.append(kw)
    return sup, calls


def _child(branch: str | None, pool: str = "agent", proc=None) -> dispatch.Child:
    return dispatch.Child(proc=proc or _DoneProc(), pool=pool, mode="start", kind="issue", number=1,
                          item_id=None, run_id=None, deadline=0, started=0, branch=branch)


def test_reap_sweeps_the_finished_lanes_worktree(tmp_path: Path, monkeypatch) -> None:
    sup, calls = _sup(tmp_path, monkeypatch)
    sup.children.append(_child("feature/claude-issue-1"))
    sup.reap()
    assert len(calls) == 1
    assert calls[0]["roots"] == [tmp_path.resolve() / "work" / "feature" / "claude-issue-1"]
    assert calls[0]["match_argv"] is True


def test_reap_skips_unknown_branch_gh_pool_and_escaping_branch(tmp_path: Path, monkeypatch) -> None:
    sup, calls = _sup(tmp_path, monkeypatch)
    sup.children += [_child(None), _child("x", pool="gh"), _child("../../etc")]
    sup.reap()
    assert calls == []


def test_idle_sweep_excludes_running_lanes_and_respects_v1(tmp_path: Path, monkeypatch) -> None:
    sup, calls = _sup(tmp_path, monkeypatch)
    sup.children += [_child("feature/claude-issue-2", proc=_Running(777)),
                     _child(None, proc=_Running(778)), _child(None, pool="gh", proc=_Running(779))]
    sup.sweep_idle_orphans(v1_busy=1)
    assert calls == []
    sup.sweep_idle_orphans()
    work = tmp_path.resolve() / "work"
    assert calls[0]["roots"] == [work]
    assert calls[0]["exclude_roots"] == [work / "feature" / "claude-issue-2"]
    assert calls[0]["require_placement"] is True and calls[0]["match_argv"] is False
    assert calls[0]["lanes"] == [orphans.LiveLane(777, False), orphans.LiveLane(778, True),
                                 orphans.LiveLane(779, False)]


def _fake_world_sup(tmp_path: Path, monkeypatch, fp: FakeProc) -> dispatch.Supervisor:
    sup, _ = _sup(tmp_path / "base", monkeypatch)
    sup.orphan_sweep = fp.sweep
    return sup


def _live_lane_world(world):
    fp, work, lane, other = world
    b = work / "b"
    b.mkdir()
    (b / ".git").write_text("gitdir: x\n")
    fp.add(60, ppid=DAEMON, cwd="/srv/base")              # agent_run.sh, branch unknown to us
    fp.add(61, ppid=60, cwd=str(b))                       # the agent, working in work/b
    fp.add(70, ppid=1, cwd=str(b))                        # escaped in a new session, lane LIVE
    fp.add(71, ppid=1, cwd=str(other))                    # a genuine orphan, proves the sweep ran
    return fp


def test_live_branchless_child_protects_its_tree(world, tmp_path: Path, monkeypatch) -> None:
    fp = _live_lane_world(world)
    sup = _fake_world_sup(tmp_path, monkeypatch, fp)
    sup.children.append(_child(None, proc=_Running(60)))
    sup.sweep_idle_orphans()
    assert [p for p, _ in fp.signals] == [71]


def test_adopted_run_row_protects_its_tree(world, tmp_path: Path, monkeypatch) -> None:
    fp = _live_lane_world(world)
    sup = _fake_world_sup(tmp_path, monkeypatch, fp)
    assert sup.children == []
    sup.conn.execute("INSERT INTO runs (item_id, mode, pid, pid_start, started_at) "
                     "VALUES (NULL, 'start', 60, 'x', 0)")
    monkeypatch.setattr(dispatch.db, "pid_alive", lambda pid, start: pid == 60)
    sup.sweep_idle_orphans()
    assert [p for p, _ in fp.signals] == [71]


def test_unreadable_run_table_skips_both_sweeps(tmp_path: Path, monkeypatch, caplog) -> None:
    sup, calls = _sup(tmp_path, monkeypatch)

    class _Broken:
        def execute(self, *a, **k):
            raise RuntimeError("database is locked")

    sup.conn = _Broken()
    with caplog.at_level("WARNING", logger="lemd.dispatch"):
        sup._sweep_lane(_child("feature/claude-issue-1"))
        sup.sweep_idle_orphans()
    assert calls == []
    assert sum("orphan sweep skipped" in r.getMessage() for r in caplog.records) == 2


def test_env_off_switch_stops_both_call_sites(tmp_path: Path, monkeypatch) -> None:
    sup, calls = _sup(tmp_path, monkeypatch, orphan_sweep=False)
    sup._sweep_lane(_child("feature/claude-issue-1"))
    sup.sweep_idle_orphans()
    assert calls == []


def test_sentinel_off_switch_stops_both_call_sites(tmp_path: Path, monkeypatch) -> None:
    sup, calls = _sup(tmp_path, monkeypatch)
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / dispatch.ORPHAN_SWEEP_OFF).touch()
    sup._sweep_lane(_child("feature/claude-issue-1"))
    sup.sweep_idle_orphans()
    assert calls == []
    (tmp_path / "state" / dispatch.ORPHAN_SWEEP_OFF).unlink()
    sup.sweep_idle_orphans()
    assert len(calls) == 1


def test_config_reads_the_env_switch(tmp_path: Path, monkeypatch) -> None:
    from lemd.config import load

    monkeypatch.delenv("LEMD_ORPHAN_SWEEP", raising=False)
    assert load(tmp_path).orphan_sweep is True
    monkeypatch.setenv("LEMD_ORPHAN_SWEEP", "0")
    assert load(tmp_path).orphan_sweep is False


def test_daemon_tick_sweeps_unless_shadow_or_off(monkeypatch) -> None:
    calls: list[int] = []

    class _Sup:
        enabled = True

        def orphan_sweep_enabled(self) -> bool:
            return self.enabled

        def v1_slots_busy(self) -> int:
            return 0

        def sweep_idle_orphans(self, *, v1_busy: int) -> None:
            calls.append(v1_busy)

    class _C:
        shadow = False

    d = daemon.Daemon.__new__(daemon.Daemon)
    d.sup, d.cfg = _Sup(), _C()
    d.sweep_orphans()
    assert calls == [0]
    d.sup.enabled = False
    d.sweep_orphans()
    assert calls == [0]
    d.sup.enabled = True
    d.cfg.shadow = True
    d.sweep_orphans()
    assert calls == [0]
