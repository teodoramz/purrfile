from dataclasses import replace
from datetime import date, timedelta

import pytest

from purrfile.daily import day_rng, jokes_for_day, lines_for_day, pick_desktop_repos
from purrfile.lines import JOKES, github_line
from purrfile.stats import Stats

BASE = Stats(
    year_total=250,
    last7=0,
    current_streak_weeks=0,
    longest_streak_weeks=0,
    quiet_days=0,
    busy_threshold=5,
    latest_repo=None,
    top_languages=(),
)
DAY = date(2026, 11, 3)
ICONS = ("folder", "floppy", "terminal", "shield", "bug", "drone", "flag", "key", "lock", "chip", "globe", "paw")
POOL = ["Vulnerable-Drone-PX4-Lab", "DOS-Detection-in-SDN-Docker-Network", "heron-proxy", "Vyzus",
        "CTFd-Docker-Plugin", "quake3-docker-compose"]
SPEC_JOKES = [
    "I tried to run sudo, but I'm not in the purr-sudoers file.",
    "Phishing? I'm only interested in the kind with actual fish.",
    "I sleep 16 hours a day, so for me every day is a zero-day.",
    "I don't need a firewall. I have a fur-wall.",
    "Error 404: treats not found.",
]


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({"year_total": 495, "quiet_days": 9},
         "You're **5 contributions** away from 500 this year. I can feel myself growing!"),
        ({"year_total": 99},
         "You're **1 contribution** away from 100 this year. I can feel myself growing!"),
        ({"year_total": 1295},
         "You're **5 contributions** away from 1300 this year. Big number incoming."),
        ({"quiet_days": 9, "last7": 0},
         "It looks like you haven't committed in **9 days**. I'll just… nap on your keyboard."),
        ({"last7": 12, "busy_threshold": 5, "current_streak_weeks": 9},
         "It looks like you made **12 contributions** this week. Want me to knock your coffee off the desk to celebrate?"),
        ({"current_streak_weeks": 7, "longest_streak_weeks": 17, "last7": 2},
         "Your weekly streak is **7**. Your best is 17. No pressure."),
        ({"latest_repo": "Vyzus", "last7": 1},
         "It looks like you've been pushing to **Vyzus**. Need a hand? I only have paws."),
        ({}, "It looks like you're up to something. Want a cat on your keyboard?"),
    ],
)
def test_github_line_rules_in_order(changes, expected):
    assert github_line(replace(BASE, **changes)) == expected


def test_github_line_never_says_today():
    variants = [
        {"year_total": 495}, {"quiet_days": 9}, {"last7": 12}, {"current_streak_weeks": 7},
        {"latest_repo": "x"}, {},
    ]
    for changes in variants:
        assert "today" not in github_line(replace(BASE, **changes)).lower()


def test_milestone_rule_needs_some_contributions():
    assert "away from" not in github_line(replace(BASE, year_total=0))


def test_jokes():
    assert len(JOKES) >= 40
    assert len(set(JOKES)) == len(JOKES)
    for joke in SPEC_JOKES:
        assert joke in JOKES


def test_jokes_no_repeat_within_10_days():
    shown = [jokes_for_day(JOKES, "teodoramz", DAY + timedelta(days=d)) for d in range(30)]
    for d, today in enumerate(shown):
        for later in shown[d + 1 : d + 10]:
            assert not set(today) & set(later)


def test_jokes_for_day_count_and_stability():
    picks = jokes_for_day(JOKES, "teodoramz", DAY)
    assert len(picks) == 3 and len(set(picks)) == 3
    assert picks == jokes_for_day(JOKES, "teodoramz", DAY)


def test_same_day_same_picks():
    assert pick_desktop_repos(POOL, "teodoramz", DAY, ICONS) == pick_desktop_repos(POOL, "teodoramz", DAY, ICONS)
    assert day_rng("a", DAY, "x").random() == day_rng("a", DAY, "x").random()


def test_days_differ():
    selections = {tuple(pick_desktop_repos(POOL, "teodoramz", DAY + timedelta(days=d), ICONS)) for d in range(7)}
    assert len(selections) >= 2


def test_pick_counts():
    for d in range(20):
        picks = pick_desktop_repos(POOL, "teodoramz", DAY + timedelta(days=d), ICONS)
        assert len(picks) in (3, 4)
        assert len({icon for _, icon in picks}) == len(picks)
        assert all(name in POOL for name, _ in picks)
    assert len(pick_desktop_repos(POOL[:2], "teodoramz", DAY, ICONS)) == 2
    assert pick_desktop_repos([], "teodoramz", DAY, ICONS) == []


def test_lines_for_day_is_github_line_then_three_jokes():
    stats = replace(BASE, latest_repo="Vyzus", last7=1)
    lines = lines_for_day(stats, JOKES, "teodoramz", DAY)
    assert lines[0] == github_line(stats)
    assert lines[1:] == jokes_for_day(JOKES, "teodoramz", DAY)
