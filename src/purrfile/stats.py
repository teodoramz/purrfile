"""Numbers derived from a snapshot. Pure: no clock, no I/O."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from .snapshot import Language, Snapshot

IGNORED_LANGUAGES = frozenset({"HTML", "CSS", "Jupyter Notebook", "Dockerfile", "Makefile", "Shell"})
BUSY_FLOOR = 5
BUSY_PERCENTILE = 0.9


@dataclass(frozen=True)
class Stats:
    year_total: int
    last7: int
    current_streak_weeks: int
    longest_streak_weeks: int
    quiet_days: int
    busy_threshold: int
    latest_repo: str | None
    top_languages: tuple[Language, ...]


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _weeks(days: dict[date, int]) -> list[tuple[date, int, bool]]:
    """(monday, total, complete) for every Mon-Sun week the calendar touches, oldest first."""
    if not days:
        return []
    first, last = min(days), max(days)
    weeks = []
    monday = _monday(first)
    while monday <= last:
        total = sum(days.get(monday + timedelta(days=i), 0) for i in range(7))
        complete = monday + timedelta(days=6) <= last
        weeks.append((monday, total, complete))
        monday += timedelta(days=7)
    return weeks


def _streaks(weeks: list[tuple[date, int, bool]]) -> tuple[int, int]:
    longest = run = 0
    for _, total, _ in weeks:
        run = run + 1 if total > 0 else 0
        longest = max(longest, run)
    current = 0
    tail = list(weeks)
    # The week still in progress only counts once it has activity; it cannot break a streak.
    if tail and not tail[-1][2] and tail[-1][1] == 0:
        tail.pop()
    for _, total, _ in reversed(tail):
        if total == 0:
            break
        current += 1
    return current, longest


def _busy_threshold(weeks: list[tuple[date, int, bool]]) -> int:
    complete = sorted(total for _, total, done in weeks if done)
    if not complete:
        return BUSY_FLOOR
    rank = math.ceil(BUSY_PERCENTILE * len(complete))
    return max(BUSY_FLOOR, complete[rank - 1])


def _top_languages(snap: Snapshot) -> tuple[Language, ...]:
    """Languages ranked by how many repos use them, then by bytes.

    Counting repos keeps one huge repo (vendored or generated code) from deciding the cat.
    """
    sizes: dict[str, int] = {}
    repo_counts: dict[str, int] = {}
    colors: dict[str, str | None] = {}
    for repo in snap.repos:
        for lang in repo.languages:
            if lang.name in IGNORED_LANGUAGES:
                continue
            sizes[lang.name] = sizes.get(lang.name, 0) + lang.size
            repo_counts[lang.name] = repo_counts.get(lang.name, 0) + 1
            colors.setdefault(lang.name, lang.color)
    ranked = sorted(sizes.items(), key=lambda kv: (-repo_counts[kv[0]], -kv[1], kv[0]))
    return tuple(Language(name, colors[name], size) for name, size in ranked if size > 0)


def compute_stats(snap: Snapshot) -> Stats:
    days = snap.days
    weeks = _weeks(days)
    current, longest = _streaks(weeks)
    quiet = 0
    if days and any(days.values()):
        for d in sorted(days, reverse=True):
            if days[d]:
                break
            quiet += 1
    elif days:
        quiet = len(days)
    last = max(days) if days else None
    last7 = sum(c for d, c in days.items() if last and last - d < timedelta(days=7))
    pushed = [r for r in snap.repos if r.pushed_at]
    latest = max(pushed, key=lambda r: r.pushed_at).name if pushed else None
    return Stats(
        year_total=sum(days.values()),
        last7=last7,
        current_streak_weeks=current,
        longest_streak_weeks=longest,
        quiet_days=quiet,
        busy_threshold=_busy_threshold(weeks),
        latest_repo=latest,
        top_languages=_top_languages(snap),
    )
