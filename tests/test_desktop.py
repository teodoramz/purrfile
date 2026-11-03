import re
import xml.dom.minidom
from dataclasses import replace
from datetime import date, timedelta

from helpers import calendar, repo, snapshot, teodor

from purrfile.desktop import HEIGHT, WIDTH, ZONES, _layout, render_desktop
from purrfile.lines import JOKES, github_line
from purrfile.stats import compute_stats
from purrfile.svgtext import text_width

DAY = date(2026, 11, 3)


def render(snap=None, **kw):
    snap = snap or teodor()
    return render_desktop(snap, compute_stats(snap), kw.pop("day", DAY), **kw)


def text_of(node) -> str:
    if node.nodeType == node.TEXT_NODE:
        return node.data
    return "".join(text_of(c) for c in node.childNodes)


def group(doc, cls):
    return [g for g in doc.getElementsByTagName("g") if g.getAttribute("class") == cls]


def test_valid_svg_without_scripts_or_external_urls():
    svg = render()
    doc = xml.dom.minidom.parseString(svg)
    root = doc.documentElement
    assert root.getAttribute("viewBox") == f"0 0 {WIDTH} {HEIGHT}" == "0 0 720 330"
    assert "<script" not in svg
    assert re.findall(r"https?://[^\"' ]+", svg) == ["http://www.w3.org/2000/svg"]


def test_deterministic_per_day():
    assert render() == render()
    assert render() != render(day=DAY + timedelta(days=1))


def test_shows_profile_and_pinned_repos():
    svg = render()
    assert "about_me.txt" in svg
    assert "Teodor Amzuloiu" in svg
    assert "Bucharest" in svg
    layout = _layout(teodor(), compute_stats(teodor()), DAY, "Mochi", ())
    pinned = {r.name for r in teodor().pinned}
    assert 3 <= len(layout.icons) <= 4
    assert {i.repo for i in layout.icons} <= pinned


def test_four_bubbles_first_is_github_line():
    doc = xml.dom.minidom.parseString(render())
    bubbles = [group(doc, f"pf-b{i}") for i in range(4)]
    assert all(len(b) == 1 for b in bubbles)
    assert not group(doc, "pf-b4")
    rows = [t for t in bubbles[0][0].getElementsByTagName("tspan") if t.hasAttribute("dy")]
    first = " ".join(text_of(row) for row in rows)
    assert first == github_line(compute_stats(teodor())).replace("**", "")


def test_bubbles_stay_in_cat_zone():
    layout = _layout(teodor(), compute_stats(teodor()), DAY, "Mochi", ())
    for b in layout.bubbles:
        assert b.x >= ZONES["cat"][0]
        assert b.x + b.w <= 716
        assert b.y >= 10
        assert b.y + b.h <= 200


def test_long_text_stays_inside_boxes():
    long_repo = "a-really-long-repository-name-x" + "y" * 9
    assert len(long_repo) == 40
    snap = replace(
        teodor(),
        bio="Security engineer who writes " * 6,
        pinned=tuple(repo(long_repo) for _ in range(1)) + teodor().pinned[:3],
    )
    extra = ("Extra " * 34).strip()
    for d in range(5):
        layout = _layout(snap, compute_stats(snap), DAY + timedelta(days=d), "Mochi", (extra,))
        for box in layout.text_boxes():
            for line in box.lines:
                width = sum(text_width(t, box.size, bold=b, mono=box.mono) for t, b in line)
                assert width <= box.w + 0.01, (box.name, line)
        assert layout.notepad.y + layout.notepad.h <= 285
        for icon in layout.icons:
            assert icon.x + icon.w <= ZONES["icons"][1]


def test_special_characters_escaped():
    snap = replace(teodor(), bio='<b>&"hi"</b>', name="A & B")
    svg = render(snap)
    xml.dom.minidom.parseString(svg)
    assert "&lt;b&gt;&amp;&quot;hi&quot;&lt;/b&gt;" in svg


def test_sparse_snapshot_renders():
    snap = snapshot(days={}, repos=(), pinned=(), name=None, bio=None, location=None)
    svg = render_desktop(snap, compute_stats(snap), DAY)
    xml.dom.minidom.parseString(svg)
    layout = _layout(snap, compute_stats(snap), DAY, "Mochi", ())
    assert layout.icons == []
    assert layout.asleep
    assert layout.cat_stage == "kitten"
    assert "someone" in svg  # falls back to the login


def test_falls_back_to_recent_repos_without_pins():
    repos = [repo(f"r{i}", f"2026-10-{10 + i}T00:00:00Z") for i in range(8)]
    snap = snapshot(days=calendar(DAY - timedelta(days=10), [1] * 10), repos=repos, pinned=())
    layout = _layout(snap, compute_stats(snap), DAY, "Mochi", ())
    assert {i.repo for i in layout.icons} <= {f"r{i}" for i in range(2, 8)}


def test_sleeps_after_a_quiet_week():
    snap = replace(teodor(), days={**teodor().days, **{DAY - timedelta(days=i): 0 for i in range(1, 9)}})
    assert _layout(snap, compute_stats(snap), DAY, "Mochi", ()).asleep
    assert not _layout(teodor(), compute_stats(teodor()), DAY, "Mochi", ()).asleep


def test_cat_name_and_extra_lines():
    svg = render(cat_name="Byte", extra_jokes=("my own line",))
    assert "Byte" in svg
    jokes_seen = set()
    for d in range(30):
        layout = _layout(teodor(), compute_stats(teodor()), DAY + timedelta(days=d), "Mochi", ("my own line",))
        jokes_seen.update(layout.lines[1:])
    assert "my own line" in jokes_seen
    assert jokes_seen <= set(JOKES) | {"my own line"}


def test_bubbles_shrink_to_their_text_and_hug_the_right():
    layout = _layout(teodor(), compute_stats(teodor()), DAY, "Mochi", ("Short.",))
    for b in layout.bubbles:
        widest = max(sum(text_width(t, b.text.size, bold=x) for t, x in line) for line in b.text.lines)
        assert b.w <= widest + 2 * 12 + 0.01
        assert abs((b.x + b.w) - 712) < 0.01


def test_icon_labels_use_up_to_three_lines_without_reaching_the_next_row():
    from purrfile.desktop import ICON_ROWS
    snap = replace(teodor(), pinned=tuple(repo(n) for n in ("quake3-docker-compose",) * 4))
    layout = _layout(snap, compute_stats(snap), DAY, "Mochi", ())
    first = layout.icons[0].label
    assert ["".join(t for t, _ in line) for line in first.lines] == ["quake3-", "docker-", "compose"]
    for icon in layout.icons:
        if icon.y == ICON_ROWS[0]:
            last_baseline = icon.label.y + (len(icon.label.lines) - 1) * icon.label.line_height
            assert last_baseline + 4 <= ICON_ROWS[1]
