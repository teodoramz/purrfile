"""What purrfile knows about an account: a plain, serializable snapshot of public data."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Language:
    name: str
    color: str | None
    size: int


@dataclass(frozen=True)
class Repo:
    name: str
    description: str | None = None
    pushed_at: str | None = None
    languages: tuple[Language, ...] = ()


@dataclass(frozen=True)
class Snapshot:
    login: str
    name: str | None = None
    bio: str | None = None
    location: str | None = None
    pinned: tuple[Repo, ...] = ()
    repos: tuple[Repo, ...] = ()
    #: Contributions per day, through the last complete UTC day.
    days: dict[date, int] = field(default_factory=dict)


def _repo_from_dict(d: dict) -> Repo:
    return Repo(
        name=d["name"],
        description=d.get("description"),
        pushed_at=d.get("pushed_at"),
        languages=tuple(Language(l["name"], l.get("color"), int(l.get("size", 0))) for l in d.get("languages", [])),
    )


def _repo_to_dict(r: Repo) -> dict:
    return {
        "name": r.name,
        "description": r.description,
        "pushed_at": r.pushed_at,
        "languages": [{"name": l.name, "color": l.color, "size": l.size} for l in r.languages],
    }


def snapshot_from_dict(d: dict) -> Snapshot:
    return Snapshot(
        login=d["login"],
        name=d.get("name"),
        bio=d.get("bio"),
        location=d.get("location"),
        pinned=tuple(_repo_from_dict(r) for r in d.get("pinned", [])),
        repos=tuple(_repo_from_dict(r) for r in d.get("repos", [])),
        days={date.fromisoformat(k): int(v) for k, v in d.get("days", {}).items()},
    )


def snapshot_to_dict(s: Snapshot) -> dict:
    return {
        "login": s.login,
        "name": s.name,
        "bio": s.bio,
        "location": s.location,
        "pinned": [_repo_to_dict(r) for r in s.pinned],
        "repos": [_repo_to_dict(r) for r in s.repos],
        "days": {d.isoformat(): c for d, c in sorted(s.days.items())},
    }
