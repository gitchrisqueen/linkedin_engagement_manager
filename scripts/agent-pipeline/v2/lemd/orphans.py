"""Orphan sweep: terminate processes a finished lane left behind in its worktree.

`dispatch` starts every lane in its own process group and enforces deadlines with `killpg`. That is
not enough on its own: tools inside a lane (an agent's shell tool, `timeout`) start commands in NEW
sessions or process groups, so they escape the group. Lane tool processes started that way (a
`pytest -n 8` and its workers, a `timeout … graft build`) outlived their lanes as orphans inside the
daemon's cgroup and held enough memory to throttle the other services in that cgroup.

A process is swept only when ALL of these hold:

* same real uid as the daemon;
* it "belongs" to a target root — its cwd (or, in the post-lane sweep only, an absolute path in its
  argv) resolves inside one of `roots` and inside none of the excluded trees;
* it is an ORPHAN TREE: walking its ppid chain up to init, EVERY process on the way also belongs.
  A live lane always has an ancestor outside its worktree (the action script runs in the pipeline
  base), so a running lane's own processes never qualify;
* it is not the daemon, an ancestor of the daemon, or a descendant of a live lane.

Excluded trees are the worktrees of live lanes: the ones the supervisor knows by branch, plus every
tree in which a DESCENDANT of a live lane currently has its cwd (computed from the same snapshot), so a
lane whose branch was resolved inside the action, or a run adopted after a daemon restart, is still
protected. When a live agent lane cannot be placed that way the idle sweep does nothing that pass.

The boundary this does NOT draw: the daemon runs as the operator's uid, so ANY detached same-uid
process (`nohup`, `setsid`, `disown`, a background job that outlived its session, a tmux/screen
server started from there) whose cwd is under `work/` WILL be terminated once no lane owns that tree.
`work/` belongs to the daemon alone; interactive work goes in `.claude/worktrees/`.

Fails OPEN: an entry that cannot be read is skipped, never guessed at, and nothing here raises.
TERM, a bounded grace, then KILL — and both signals re-check the process start time first, so a
recycled pid is never signalled.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

LOG = logging.getLogger("lemd.orphans")

#: Default grace between TERM and KILL. Long enough for pytest to tear down its workers, short
#: enough that a sweep never stalls the daemon loop for long.
GRACE_SECONDS = 10.0
#: Upper bound on processes signalled by one sweep, and on any ppid walk. A sweep that finds more
#: than this is better finished on the next pass than allowed to run unbounded.
MAX_TARGETS = 256
MAX_DEPTH = 64


@dataclass(frozen=True)
class LiveLane:
    """A run still in flight. A `must_place` lane must be located in `work/` before an idle sweep."""

    pid: int
    must_place: bool = False


@dataclass(frozen=True)
class _Proc:
    pid: int
    ppid: int
    uid: int
    start: str
    comm: str
    cwd: str | None
    argv: tuple[str, ...]


@dataclass
class SweepResult:
    """What one sweep did. `skipped` names why nothing was attempted, when that is the case."""

    terminated: list[int] = field(default_factory=list)
    killed: list[int] = field(default_factory=list)
    skipped: str = ""

    @property
    def count(self) -> int:
        """How many processes were signalled at all."""
        return len(self.terminated)


def _read_proc(proc_root: Path, pid: int) -> _Proc | None:
    """One /proc entry, or None when any required field is unreadable."""
    base = proc_root / str(pid)
    try:
        status = (base / "status").read_text()
        stat = (base / "stat").read_text()
    except OSError:
        return None
    ppid = uid = None
    for line in status.splitlines():
        if line.startswith("PPid:"):
            ppid = int(line.split()[1])
        elif line.startswith("Uid:"):
            uid = int(line.split()[1])
    # comm sits in parentheses and may contain spaces; starttime is field 22, the 20th after it.
    try:
        head, tail = stat.rsplit(")", 1)
        comm = head.split("(", 1)[1]
        start = tail.split()[19]
    except IndexError:
        return None
    if ppid is None or uid is None:
        return None
    try:
        cwd: str | None = os.readlink(base / "cwd")
    except OSError:
        cwd = None
    try:
        raw = (base / "cmdline").read_bytes()
        argv = tuple(a.decode("utf-8", "replace") for a in raw.split(b"\0") if a)
    except OSError:
        argv = ()
    return _Proc(pid=pid, ppid=ppid, uid=uid, start=start, comm=comm, cwd=cwd, argv=argv)


def snapshot(proc_root: Path) -> dict[int, _Proc]:
    """Every readable process under `proc_root`. Unreadable entries are skipped."""
    procs: dict[int, _Proc] = {}
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return procs
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            proc = _read_proc(proc_root, int(entry.name))
        except (OSError, ValueError):
            proc = None
        if proc is not None:
            procs[proc.pid] = proc
    return procs


def _inside(path: str, root: Path) -> bool:
    """True when `path` is `root` or below it. Lexical on normalised absolute paths."""
    p = os.path.normpath(path)
    r = os.path.normpath(str(root))
    return p == r or p.startswith(r.rstrip("/") + "/")


def _match(proc: _Proc, roots: list[Path], exclude: list[Path],
           match_argv: bool) -> tuple[str, Path] | None:
    """`(how, root)` when the process belongs to a target root, else None."""
    paths = [("cwd", proc.cwd)] if proc.cwd else []
    if match_argv:
        paths += [("argv", a) for a in proc.argv if a.startswith("/")]
    for how, path in paths:
        if any(_inside(path, e) for e in exclude):
            continue
        for r in roots:
            if _inside(path, r):
                return how, r
    return None


def _ancestors(procs: dict[int, _Proc], pid: int) -> set[int]:
    out: set[int] = set()
    cur = procs.get(pid)
    for _ in range(MAX_DEPTH):
        if cur is None or cur.ppid in (0, cur.pid):
            break
        out.add(cur.ppid)
        cur = procs.get(cur.ppid)
    return out


def _descendants(procs: dict[int, _Proc], pids: set[int]) -> set[int]:
    """`pids` plus every process whose ppid chain reaches one of them."""
    out = set()
    for pid in procs:
        if pid in pids or _ancestors(procs, pid) & pids:
            out.add(pid)
    return out


def _tree_root(cwd: str, work_root: Path, is_tree_root: Callable[[Path], bool]) -> Path | None:
    """The worktree directory under `work_root` containing `cwd`, or None when none is found."""
    if not _inside(cwd, work_root) or os.path.normpath(cwd) == os.path.normpath(str(work_root)):
        return None
    cur = Path(os.path.normpath(cwd))
    root = Path(os.path.normpath(str(work_root)))
    for _ in range(MAX_DEPTH):
        if cur == root or root not in cur.parents:
            return None
        try:
            if is_tree_root(cur):
                return cur
        except OSError:
            return None
        cur = cur.parent
    return None


def _has_git(path: Path) -> bool:
    return (path / ".git").exists()


def live_trees(procs: dict[int, _Proc], lanes: Iterable[LiveLane], work_root: Path,
               is_tree_root: Callable[[Path], bool] = _has_git) -> tuple[set[Path], list[int]]:
    """Worktrees live lanes' descendants are working in, and the `must_place` lanes not found."""
    trees: set[Path] = set()
    unplaced: list[int] = []
    for lane in lanes:
        placed = False
        for pid in _descendants(procs, {lane.pid}):
            cwd = procs[pid].cwd
            tree = _tree_root(cwd, work_root, is_tree_root) if cwd else None
            if tree is not None:
                trees.add(tree)
                placed = True
        if lane.must_place and not placed:
            unplaced.append(lane.pid)
    return trees, unplaced


def find_orphans(procs: dict[int, _Proc], *, roots: Iterable[Path],
                 exclude_roots: Iterable[Path] = (), protect_pids: Iterable[int] = (),
                 self_pid: int, uid: int,
                 match_argv: bool = True) -> list[tuple[int, str, Path]]:
    """`(pid, how, root)` for each process safe to terminate under the module docstring's rules."""
    roots = [Path(r) for r in roots]
    exclude = [Path(e) for e in exclude_roots]
    if not roots:
        return []
    never = {0, 1, self_pid} | _ancestors(procs, self_pid)
    protect = set(protect_pids) | {self_pid}
    found: list[tuple[int, str, Path]] = []
    for pid, proc in sorted(procs.items()):
        if pid in never or proc.uid != uid:
            continue
        hit = _match(proc, roots, exclude, match_argv)
        if hit is None:
            continue
        ok = False
        cur = proc
        for _ in range(MAX_DEPTH):
            if cur.pid in protect or cur.pid in never or cur.uid != uid:
                break
            if _match(cur, roots, exclude, match_argv) is None:
                break
            if cur.ppid in (0, 1):
                ok = True
                break
            parent = procs.get(cur.ppid)
            if parent is None:
                break  # parent unreadable or mid-exit: not provably an orphan, next pass decides
            cur = parent
        if ok:
            found.append((pid, hit[0], hit[1]))
        if len(found) >= MAX_TARGETS:
            break
    return found


def sweep(*, roots: Iterable[Path], exclude_roots: Iterable[Path] = (),
          lanes: Iterable[LiveLane] = (), work_root: Path | None = None,
          require_placement: bool = False, match_argv: bool = True, reason: str = "",
          proc_root: Path = Path("/proc"),
          kill: Callable[[int, int], None] = os.kill,
          sleep: Callable[[float], None] = time.sleep,
          clock: Callable[[], float] = time.monotonic,
          is_tree_root: Callable[[Path], bool] = _has_git,
          grace: float = GRACE_SECONDS,
          self_pid: int | None = None, uid: int | None = None) -> SweepResult:
    """Find orphans under `roots`, TERM them, wait up to `grace`, KILL survivors.

    `lanes` are the runs still in flight: their descendants are never signalled, and every
    `work_root` tree one of them is working in is excluded. With `require_placement`, a
    `must_place` lane that cannot be located makes the whole sweep a no-op.

    Never raises. Logs one INFO line when anything was signalled: per pid its comm (from
    /proc/<pid>/stat), whether cwd or argv matched, and the root — never the command line.
    """
    result = SweepResult()
    try:
        self_pid = os.getpid() if self_pid is None else self_pid
        uid = os.getuid() if uid is None else uid
        lanes = list(lanes)
        procs = snapshot(proc_root)
        exclude = [Path(e) for e in exclude_roots]
        if work_root is not None:
            trees, unplaced = live_trees(procs, lanes, work_root, is_tree_root)
            exclude += sorted(trees)
            if require_placement and unplaced:
                # Expected while a lane is still creating its worktree: DEBUG, not a warning.
                LOG.debug("orphan sweep (%s) skipped: live lane(s) %s not placed in a worktree",
                          reason, unplaced)
                result.skipped = "unplaced_lane"
                return result
        targets = find_orphans(procs, roots=roots, exclude_roots=exclude,
                               protect_pids=_descendants(procs, {lane.pid for lane in lanes}),
                               self_pid=self_pid, uid=uid, match_argv=match_argv)
        if not targets:
            return result
        starts = {pid: procs[pid].start for pid, _, _ in targets}

        def same(pid: int) -> bool:
            cur = _read_proc(proc_root, pid)
            return cur is not None and cur.start == starts[pid]

        detail = []
        for pid, how, root in targets:
            if not same(pid):
                continue
            try:
                kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                continue
            result.terminated.append(pid)
            detail.append(f"{pid}:{procs[pid].comm}:{how}:{root}")
        deadline = clock() + grace
        alive = [p for p in result.terminated if same(p)]
        while alive and clock() < deadline:
            sleep(0.5)
            alive = [p for p in alive if same(p)]
        for pid in alive:
            try:
                kill(pid, signal.SIGKILL)
                result.killed.append(pid)
            except (ProcessLookupError, PermissionError):
                continue
        if result.terminated:
            LOG.info("orphan sweep%s: terminated %d process(es) pids=%s killed_after_grace=%s "
                     "detail=[%s]", f" ({reason})" if reason else "", result.count,
                     result.terminated, result.killed, ", ".join(detail))
    except Exception as exc:  # noqa: BLE001 - housekeeping must never take the daemon down
        LOG.warning("orphan sweep failed open: %s", exc)
    return result
