"""Small builders shared by the tests."""
from datetime import date, timedelta
import json
from pathlib import Path

from purrfile.snapshot import Language, Repo, Snapshot, snapshot_from_dict

FIXTURES = Path(__file__).parent / "fixtures"


def teodor() -> Snapshot:
    return snapshot_from_dict(json.loads((FIXTURES / "teodor-snapshot.json").read_text()))


def calendar(start: date, counts: list[int]) -> dict[date, int]:
    return {start + timedelta(days=i): c for i, c in enumerate(counts)}


def snapshot(days=None, repos=(), pinned=(), name="Cat Owner", bio="bio", location="Somewhere") -> Snapshot:
    return Snapshot(
        login="someone",
        name=name,
        bio=bio,
        location=location,
        pinned=tuple(pinned),
        repos=tuple(repos),
        days=dict(days or {}),
    )


def repo(name, pushed_at=None, langs=(), description=None) -> Repo:
    return Repo(
        name=name,
        description=description,
        pushed_at=pushed_at,
        languages=tuple(Language(n, c, s) for n, c, s in langs),
    )
