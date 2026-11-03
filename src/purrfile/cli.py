"""Command line: `python3 -m purrfile collect|desktop|hunt|run`.

`run` is what the GitHub Action calls. It never fails the workflow: every problem becomes a
`::warning::` and the files it could not produce are left exactly as they were.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from . import __version__
from . import collect as _collect
from .daily import jokes_for_day
from .desktop import render_desktop
from .hunt import HuntError, hunt
from .lines import JOKES
from .snapshot import Snapshot, snapshot_from_dict, snapshot_to_dict
from .sprites import cat_look
from .stats import compute_stats


def warn(message: str) -> None:
    print(f"::warning::purrfile: {message}", flush=True)


def write_atomic(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, mode)  # mkstemp creates 0600; keep the file's usual permissions
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load_extra_lines(path: str | None) -> list[str]:
    if not path:
        return []
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        warn(f"extra lines file {path!r} not read ({exc.strerror or exc}); using the built-in lines only")
        return []
    return [line.strip() for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")]


def _today(value: str | None) -> date:
    return date.fromisoformat(value) if value else datetime.now(timezone.utc).date()


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def _load_snapshot(path: str) -> Snapshot:
    return snapshot_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _hunt_file(path: Path, snap: Snapshot, day: date, extra: list[str]) -> None:
    stats = compute_stats(snap)
    joke = jokes_for_day(tuple(JOKES) + tuple(extra), snap.login, day, count=1)[0]
    text = path.read_text(encoding="utf-8")
    new = hunt(text, cat_look(stats), joke)
    if new != text:
        write_atomic(path, new)


def _cmd_collect(args) -> int:
    snap = _collect.fetch_snapshot(args.login, _token(), _today(args.date))
    text = json.dumps(snapshot_to_dict(snap), indent=1)
    if args.output:
        write_atomic(Path(args.output), text)
    else:
        print(text)
    return 0


def _cmd_desktop(args) -> int:
    snap = _load_snapshot(args.snapshot)
    svg = render_desktop(snap, compute_stats(snap), _today(args.date), args.cat_name, load_extra_lines(args.extra_lines))
    write_atomic(Path(args.output), svg)
    return 0


def _cmd_hunt(args) -> int:
    snap = _load_snapshot(args.snapshot)
    extra = load_extra_lines(args.extra_lines)
    failed = 0
    for name in args.svg:
        try:
            _hunt_file(Path(name), snap, _today(args.date), extra)
        except (HuntError, OSError) as exc:
            print(f"error: {name}: {exc} (left unchanged)", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


def _cmd_run(args) -> int:
    day = _today(args.date)
    try:
        snap = _collect.fetch_snapshot(args.login, _token(), day)
    except Exception as exc:  # noqa: BLE001 - nothing may fail the workflow
        warn(f"could not collect {args.login}'s data ({exc}); keeping yesterday's images")
        return 0
    extra = load_extra_lines(args.extra_lines)
    if args.desktop:
        try:
            svg = render_desktop(snap, compute_stats(snap), day, args.cat_name or "Mochi", extra)
            write_atomic(Path(args.desktop), svg)
            print(f"purrfile: drew the desktop into {args.desktop}")
        except Exception as exc:  # noqa: BLE001
            warn(f"could not draw the desktop ({exc}); {args.desktop} left unchanged")
    for name in (args.snake or "").split():
        try:
            _hunt_file(Path(name), snap, day, extra)
            print(f"purrfile: added the hunter cat to {name}")
        except Exception as exc:  # noqa: BLE001
            warn(f"could not add the hunter to {name} ({exc}); the snake is left unchanged")
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="purrfile", description="A pixel cat for your GitHub profile.")
    p.add_argument("--version", action="version", version=f"purrfile {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("collect", help="collect an account's public data into a snapshot (token: GITHUB_TOKEN)")
    c.add_argument("login")
    c.add_argument("--output", help="write the snapshot here instead of standard output")
    c.add_argument("--date", help="UTC date, YYYY-MM-DD (default: today)")
    c.set_defaults(func=_cmd_collect)

    d = sub.add_parser("desktop", help="draw the retro desktop from a snapshot")
    d.add_argument("snapshot")
    d.add_argument("--output", required=True)
    d.add_argument("--date")
    d.add_argument("--cat-name", default="Mochi")
    d.add_argument("--extra-lines", default="")
    d.set_defaults(func=_cmd_desktop)

    h = sub.add_parser("hunt", help="add the hunter cat to Platane/snk SVGs, in place")
    h.add_argument("snapshot")
    h.add_argument("svg", nargs="+")
    h.add_argument("--date")
    h.add_argument("--extra-lines", default="")
    h.set_defaults(func=_cmd_hunt)

    r = sub.add_parser("run", help="collect, draw the desktop, and hunt the snakes (what the Action runs)")
    r.add_argument("--login", required=True)
    r.add_argument("--desktop", default="", help="where to write the desktop SVG (empty: skip)")
    r.add_argument("--snake", default="", help="space-separated snk SVGs to add the hunter to (empty: skip)")
    r.add_argument("--cat-name", default="Mochi")
    r.add_argument("--extra-lines", default="")
    r.add_argument("--date")
    r.set_defaults(func=_cmd_run)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.func(args)
    except (_collect.CollectError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
