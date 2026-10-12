"""Orphan sweep: terminate processes a finished lane left behind in its worktree.

`dispatch` starts every lane in its own process group and enforces deadlines with `killpg`. That is
not enough on its own: tools inside a lane (an agent's shell tool, `timeout`) start commands in NEW
sessions or process groups, so they escape the group. Measured: a lane's `pytest -n 8` and a
`timeout 180 graft build` outlived their lanes as orphans (PPID 1) for one to two days inside the
daemon's cgroup, holding ~2.4 GB, which pushed the service slice past its memory ceiling and
throttled every service in it.

A process is swept only when ALL of these hold — each rule exists because a weaker one would let
the sweep reach something it must not:

* same real uid as the daemon;
* it "belongs" to a target root — its cwd, or an absolute path in its argv, resolves inside one of
  `roots` and inside none of `exclude_roots` (the worktrees of lanes still running);
* it is an ORPHAN TREE: walking its ppid chain up to init, EVERY process on the way also belongs.
  A live lane always has an ancestor outside its worktree (the action script runs in the pipeline
  base), and so does an interactive shell, so neither can ever qualify;
* it is not the daemon, an ancestor of the daemon, or a descendant of a protected pid (a running
  child of the supervisor).

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
#: Upper bound on processes signalled by one sweep, and on the ppid walk. A sweep that finds more
#: than this is better finished on the next pass than allowed to run unbounded.
MAX_TARGETS = 256
MAX_DEPTH = 64


@dataclass(frozen=True)
class _Proc:
    pid: int
    ppid: int
    uid: int
    start: str
    cwd: str | None
    argv: tuple[str, ...]


@dataclass
class SweepResult:
    """What one sweep did."""

    terminated: list[int] = field(default_factory=list)
    killed: list[int] = field(default_factory=list)

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
    # Field 22 (starttime) counted after the comm field, whose parentheses may contain spaces.
    try:
        start = stat.rsplit(")", 1)[1].split()[19]
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
    return _Proc(pid=pid, ppid=ppid, uid=uid, start=start, cwd=cwd, argv=argv)


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


def _belongs(proc: _Proc, roots: list[Path], exclude: list[Path]) -> bool:
    paths = [proc.cwd] if proc.cwd else []
    paths += [a for a in proc.argv if a.startswith("/")]
    for path in paths:
        if any(_inside(path, r) for r in roots) and not any(_inside(path, e) for e in exclude):
            return True
    return False


def _ancestors(procs: dict[int, _Proc], pid: int) -> set[int]:
    out: set[int] = set()
    cur = procs.get(pid)
    for _ in range(MAX_DEPTH):
        if cur is None or cur.ppid in (0, cur.pid):
            break
        out.add(cur.ppid)
        cur = procs.get(cur.ppid)
    return out


def find_orphans(procs: dict[int, _Proc], *, roots: Iterable[Path],
                 exclude_roots: Iterable[Path] = (), protect_pids: Iterable[int] = (),
                 self_pid: int, uid: int) -> list[int]:
    """Pids that are safe to terminate under the rules in the module docstring."""
    roots = [Path(r) for r in roots]
    exclude = [Path(e) for e in exclude_roots]
    if not roots:
        return []
    never = {0, 1, self_pid} | _ancestors(procs, self_pid)
    protect = set(protect_pids) | {self_pid}
    found: list[int] = []
    for pid, proc in sorted(procs.items()):
        if pid in never or proc.uid != uid or not _belongs(proc, roots, exclude):
            continue
        ok = False
        cur = proc
        for _ in range(MAX_DEPTH):
            if cur.pid in protect or cur.pid in never or cur.uid != uid:
                break
            if not _belongs(cur, roots, exclude):
                break
            if cur.ppid in (0, 1):
                ok = True
                break
            parent = procs.get(cur.ppid)
            if parent is None:
                break  # parent unreadable or mid-exit: not provably an orphan, next pass decides
            cur = parent
        if ok:
            found.append(pid)
        if len(found) >= MAX_TARGETS:
            break
    return found


def sweep(*, roots: Iterable[Path], exclude_roots: Iterable[Path] = (),
          protect_pids: Iterable[int] = (), reason: str = "",
          proc_root: Path = Path("/proc"),
          kill: Callable[[int, int], None] = os.kill,
          sleep: Callable[[float], None] = time.sleep,
          clock: Callable[[], float] = time.monotonic,
          grace: float = GRACE_SECONDS,
          self_pid: int | None = None, uid: int | None = None) -> SweepResult:
    """Find orphans under `roots`, TERM them, wait up to `grace`, KILL survivors.

    Never raises. Logs one INFO line (count + pids, never command lines) when anything was signalled.
    """
    result = SweepResult()
    try:
        self_pid = os.getpid() if self_pid is None else self_pid
        uid = os.getuid() if uid is None else uid
        procs = snapshot(proc_root)
        targets = find_orphans(procs, roots=roots, exclude_roots=exclude_roots,
                               protect_pids=protect_pids, self_pid=self_pid, uid=uid)
        if not targets:
            return result
        starts = {pid: procs[pid].start for pid in targets}

        def same(pid: int) -> bool:
            cur = _read_proc(proc_root, pid)
            return cur is not None and cur.start == starts[pid]

        for pid in targets:
            if not same(pid):
                continue
            try:
                kill(pid, signal.SIGTERM)
                result.terminated.append(pid)
            except (ProcessLookupError, PermissionError):
                continue
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
            LOG.info("orphan sweep%s: terminated %d process(es) pids=%s killed_after_grace=%s",
                     f" ({reason})" if reason else "", result.count, result.terminated,
                     result.killed)
    except Exception as exc:  # noqa: BLE001 - housekeeping must never take the daemon down
        LOG.warning("orphan sweep failed open: %s", exc)
    return result
