"""Collect an account's public data with one GitHub GraphQL query."""
from __future__ import annotations

import json
import urllib.request
from datetime import date

from .snapshot import Language, Repo, Snapshot

API = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    name
    bio
    location
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes { ... on Repository { name description pushedAt primaryLanguage { name color } } }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name
        description
        pushedAt
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
    contributionsCollection { contributionCalendar { weeks { contributionDays { date contributionCount } } } }
  }
}
""".strip()


class CollectError(Exception):
    """The account's data could not be collected."""


def parse_response(data: dict, today: date) -> Snapshot:
    """Turn a GraphQL response into a Snapshot. Days on or after `today` (still in progress) are dropped."""
    user = (data.get("data") or {}).get("user")
    if not user:
        raise CollectError("GitHub returned no such user")

    def pinned(node: dict) -> Repo:
        lang = node.get("primaryLanguage")
        return Repo(node["name"], node.get("description"), node.get("pushedAt"),
                    (Language(lang["name"], lang.get("color"), 0),) if lang else ())

    def repo(node: dict) -> Repo:
        edges = (node.get("languages") or {}).get("edges") or []
        langs = tuple(Language(e["node"]["name"], e["node"].get("color"), int(e["size"])) for e in edges)
        return Repo(node["name"], node.get("description"), node.get("pushedAt"), langs)

    days = {}
    weeks = (((user.get("contributionsCollection") or {}).get("contributionCalendar") or {}).get("weeks")) or []
    for week in weeks:
        for day in week.get("contributionDays") or []:
            d = date.fromisoformat(day["date"])
            if d < today:
                days[d] = int(day["contributionCount"])
    return Snapshot(
        login=user["login"],
        name=user.get("name"),
        bio=user.get("bio"),
        location=user.get("location"),
        pinned=tuple(pinned(n) for n in (user.get("pinnedItems") or {}).get("nodes") or [] if n and "name" in n),
        repos=tuple(repo(n) for n in (user.get("repositories") or {}).get("nodes") or [] if n),
        days=days,
    )


def fetch_snapshot(login: str, token: str, today: date, urlopen=urllib.request.urlopen) -> Snapshot:
    if not token:
        raise CollectError("no GitHub token (set GITHUB_TOKEN; in Actions the built-in token is enough)")
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        API,
        data=body,
        method="POST",
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "purrfile"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read())
    except Exception as exc:  # noqa: BLE001 - network, HTTP and JSON failures all mean "no data today"
        raise CollectError(f"GitHub request failed: {exc}") from exc
    if data.get("errors"):
        raise CollectError("GitHub GraphQL error: " + "; ".join(e.get("message", "?") for e in data["errors"]))
    return parse_response(data, today)
