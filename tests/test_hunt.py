import re
import xml.dom.minidom

import pytest
from helpers import FIXTURES, teodor

from purrfile.hunt import CELEBRATE_MS, MARKER, HuntError, hunt, plan_hunt
from purrfile.sprites import cat_look
from purrfile.stats import compute_stats

DARK = (FIXTURES / "snk-dark.svg").read_text()
LIGHT = (FIXTURES / "snk-light.svg").read_text()
LOOK = cat_look(compute_stats(teodor()))
JOKE = "Phishing? I'm only interested in the kind with actual fish."


def keyframes(svg: str, name: str) -> list[tuple[float, str]]:
    body = re.search(r"@keyframes " + re.escape(name) + r"\{((?:[^{}]*\{[^}]*\})*)\}", svg).group(1)
    out = []
    for sel, decl in re.findall(r"([\d.,%]+)\{([^}]*)\}", body):
        out += [(float(p.rstrip("%")), decl) for p in sel.split(",")]
    return sorted(out)


def opacity_at(frames, pct):
    value = None
    for p, decl in frames:
        if p <= pct + 1e-9:
            value = float(re.search(r"opacity:([\d.]+)", decl).group(1))
    return value


def test_plan_hunt_on_the_real_snake():
    plan = plan_hunt(DARK)
    assert plan.duration_ms == 55500
    assert plan.catch_pct == pytest.approx(68.11, abs=0.01)
    assert plan.head_xy == (816.0, 0.0)
    assert plan.new_duration_ms == pytest.approx(47801, abs=1)
    assert len(plan.saved_cells) == 22


@pytest.mark.parametrize("source", [DARK, LIGHT], ids=["dark", "light"])
def test_hunt_output(source):
    out = hunt(source, LOOK, JOKE)
    xml.dom.minidom.parseString(out)
    assert all(float(p) <= 100.0001 for p in re.findall(r"([\d.]+)%", out))
    assert "47801ms" in out
    assert "55500ms" not in out
    assert "GOT IT. You&apos;re welcome." in out or "GOT IT. You're welcome." in out
    assert "saved" not in out.lower()
    assert "Phishing?" in out and "actual fish." in out
    assert f'id="{MARKER}"' in out
    words = " ".join(re.sub(r"<[^>]+>", " ", out[out.index(MARKER):]).split())
    assert "It looks like a snake is eating your commits. Want me to deal with it?" in words
    assert "Shh… wait for it…" in words
    assert JOKE in words


def test_viewbox_grows_upward_only():
    out = hunt(DARK, LOOK, JOKE)
    before = re.search(r'viewBox="([^"]+)" width="(\d+)" height="(\d+)"', DARK).groups()
    after = re.search(r'viewBox="([^"]+)" width="(\d+)" height="(\d+)"', out).groups()
    bx, by, bw, bh = map(float, before[0].split())
    ax, ay, aw, ah = map(float, after[0].split())
    assert (ax, aw) == (bx, bw) and after[1] == before[1]
    assert ay == by - 88 and ah == bh + 88 and int(after[2]) == int(before[2]) + 88


def test_idempotent():
    once = hunt(DARK, LOOK, JOKE)
    assert hunt(once, LOOK, JOKE) == once


def test_foreign_svg_raises():
    with pytest.raises(HuntError):
        hunt("<svg xmlns='http://www.w3.org/2000/svg'/>", LOOK, JOKE)
    with pytest.raises(HuntError):
        hunt(DARK[: len(DARK) // 3], LOOK, JOKE)


def test_timeline_in_browser_terms():
    plan = plan_hunt(DARK)
    out = hunt(DARK, LOOK, JOKE)
    catch = plan.catch_pct * plan.duration_ms / plan.new_duration_ms
    caught = keyframes(out, "caught")
    assert opacity_at(caught, catch) == 1
    assert opacity_at(caught, catch + 0.05) == 0
    celebrate = CELEBRATE_MS / plan.new_duration_ms * 100
    b3, b4 = keyframes(out, "pf-hb3"), keyframes(out, "pf-hb4")
    assert opacity_at(b3, catch - 0.5) == 0
    assert opacity_at(b3, catch + 0.5) == 1
    assert opacity_at(b3, catch + celebrate - 0.5) == 1
    assert opacity_at(b3, catch + celebrate + 0.5) == 0
    assert opacity_at(b4, catch + celebrate + 0.5) == 1
    assert opacity_at(b4, 99.0) == 1


def test_cells_eaten_after_the_catch_stay():
    plan = plan_hunt(DARK)
    out = hunt(DARK, LOOK, JOKE)
    for name in plan.saved_cells:
        assert f".c.{name}{{animation-name:none}}" in out
        assert f"@keyframes {name}{{" not in out
