"""The day's choices. "Random" is seeded by (login, UTC date): reruns on one day agree, the next day differs."""
from __future__ import annotations

import random
from datetime import date
from typing import Sequence

from .lines import github_line
from .stats import Stats


def day_rng(login: str, day: date, purpose: str) -> random.Random:
    return random.Random(f"{login}:{day.isoformat()}:{purpose}")


def pick_desktop_repos(pool: Sequence[str], login: str, day: date, icon_names: Sequence[str]) -> list[tuple[str, str]]:
    """3 or 4 repos from the pool (all of them if fewer), each with a distinct random icon."""
    if not pool:
        return []
    rng = day_rng(login, day, "repos")
    count = min(rng.choice((3, 4)), len(pool))
    repos = rng.sample(list(pool), count)
    icons = rng.sample(list(icon_names), count)
    return list(zip(repos, icons))


def jokes_for_day(jokes: Sequence[str], login: str, day: date, count: int = 3) -> list[str]:
    """Walk a fixed per-account order of the jokes, `count` a day.

    A joke comes back only after len(jokes) / count days, at least 13 days with the built-in list.
    """
    if not jokes:
        return []
    order = list(dict.fromkeys(jokes))
    random.Random(f"{login}:jokes").shuffle(order)
    start = count * day.toordinal()
    return [order[(start + i) % len(order)] for i in range(min(count, len(order)))]


def lines_for_day(stats: Stats, jokes: Sequence[str], login: str, day: date) -> list[str]:
    return [github_line(stats), *jokes_for_day(jokes, login, day)]
