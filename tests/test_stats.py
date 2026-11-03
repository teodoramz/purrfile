from datetime import date

from helpers import calendar, repo, snapshot, teodor

from purrfile.snapshot import snapshot_from_dict, snapshot_to_dict
from purrfile.stats import IGNORED_LANGUAGES, compute_stats

MON_OCT_5 = date(2026, 10, 5)


def four_weeks(week4_sunday: int) -> dict:
    #        Mon Tue Wed Thu Fri Sat Sun
    week1 = [0, 3, 0, 0, 0, 0, 0]
    week2 = [0, 0, 0, 0, 0, 0, 0]
    week3 = [1, 0, 0, 0, 2, 0, 0]
    week4 = [0, 0, 0, 0, 0, 0, week4_sunday]
    return calendar(MON_OCT_5, week1 + week2 + week3 + week4)


def test_round_trip():
    s = teodor()
    assert snapshot_from_dict(snapshot_to_dict(s)) == s


def test_streaks_and_totals():
    stats = compute_stats(snapshot(days=four_weeks(5)))
    assert stats.year_total == 11
    assert stats.last7 == 5
    assert stats.current_streak_weeks == 2
    assert stats.longest_streak_weeks == 2
    assert stats.quiet_days == 0


def test_quiet_days():
    stats = compute_stats(snapshot(days=four_weeks(0)))
    assert stats.quiet_days == 9
    assert stats.current_streak_weeks == 0
    assert stats.longest_streak_weeks == 1


def test_current_streak_counts_unfinished_week_only_when_active():
    # Ends on a Wednesday with no activity yet this week: the streak runs from last week.
    days = calendar(MON_OCT_5, [1] + [0] * 6 + [0, 2] + [0] * 5 + [0, 0, 0])
    stats = compute_stats(snapshot(days=days))
    assert stats.current_streak_weeks == 2


def test_empty_calendar():
    stats = compute_stats(snapshot(days={}))
    assert stats.year_total == 0
    assert stats.last7 == 0
    assert stats.current_streak_weeks == 0
    assert stats.longest_streak_weeks == 0
    assert stats.quiet_days == 0
    assert stats.latest_repo is None
    assert stats.top_languages == ()


def test_top_languages_ignore_markup():
    repos = [
        repo("site", "2026-01-01T00:00:00Z", [("HTML", "#e34c26", 9000), ("Python", "#3572A5", 200)]),
        repo("tool", "2026-02-01T00:00:00Z", [("Python", "#3572A5", 300), ("Go", "#00ADD8", 300)]),
    ]
    stats = compute_stats(snapshot(repos=repos))
    assert [lang.name for lang in stats.top_languages] == ["Python", "Go"]
    assert stats.top_languages[0].size == 500
    assert "HTML" in IGNORED_LANGUAGES


def test_language_used_in_more_repos_beats_one_huge_repo():
    repos = [
        repo("big", None, [("TypeScript", "#3178c6", 1_000_000)]),
        repo("a", None, [("Python", "#3572A5", 100)]),
        repo("b", None, [("Python", "#3572A5", 100), ("Shell", "#89e051", 50)]),
    ]
    names = [lang.name for lang in compute_stats(snapshot(repos=repos)).top_languages]
    assert names == ["Python", "TypeScript"]


def test_latest_repo_is_most_recently_pushed():
    repos = [repo("old", "2025-01-01T00:00:00Z"), repo("new", "2026-10-30T10:00:00Z"), repo("never", None)]
    assert compute_stats(snapshot(repos=repos)).latest_repo == "new"


def test_busy_threshold_floor():
    days = calendar(MON_OCT_5, [1, 0, 0, 0, 0, 0, 1] * 8)
    assert compute_stats(snapshot(days=days)).busy_threshold == 5


def test_busy_threshold_is_90th_percentile_of_complete_weeks():
    weekly = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    counts = []
    for total in weekly:
        counts += [total, 0, 0, 0, 0, 0, 0]
    stats = compute_stats(snapshot(days=calendar(MON_OCT_5, counts)))
    assert stats.busy_threshold == 18


def test_teodor_fixture_numbers():
    stats = compute_stats(teodor())
    assert stats.year_total == 495
    assert stats.top_languages[0].name == "Python"
    assert stats.latest_repo == "Vyzus"
