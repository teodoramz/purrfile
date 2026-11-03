import xml.dom.minidom
from dataclasses import replace

from purrfile.icons import ICON_NAMES, ICONS, icon_svg
from purrfile.snapshot import Language
from purrfile.sprites import SPRITES, cat_look, cat_svg, luminance, stage_for
from purrfile.stats import Stats

STATS = Stats(500, 0, 0, 0, 0, 5, None, ())
PY_GO = (Language("Python", "#3572A5", 10), Language("Go", "#00ADD8", 5))


def parses(fragment: str):
    return xml.dom.minidom.parseString(f'<svg xmlns="http://www.w3.org/2000/svg">{fragment}</svg>')


def rgb(hex_color):
    return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))


def test_stage_boundaries():
    assert stage_for(0) == "kitten"
    assert stage_for(99) == "kitten"
    assert stage_for(100) == "young"
    assert stage_for(499) == "young"
    assert stage_for(500) == "grown"


def test_cat_look_from_languages():
    look = cat_look(replace(STATS, top_languages=PY_GO))
    assert look.stage == "grown"
    assert look.fur != look.stripes
    r, g, b = rgb(look.fur)
    assert b > r
    assert 0.18 <= luminance(look.fur) <= 0.70
    assert look.eyes == "#f2c935"


def test_cat_look_without_languages():
    look = cat_look(STATS)
    assert look.fur == "#9aa3b5"
    assert look.stripes == "#6b7387"


def test_cat_look_clamps_very_dark_and_very_light_languages():
    dark = cat_look(replace(STATS, top_languages=(Language("PowerShell", "#012456", 1),)))
    light = cat_look(replace(STATS, top_languages=(Language("JavaScript", "#f1e05a", 1),)))
    assert 0.18 <= luminance(dark.fur) <= 0.70
    assert 0.18 <= luminance(light.fur) <= 0.70


def test_stripes_stay_distinct_from_similar_fur():
    look = cat_look(replace(STATS, top_languages=(Language("Python", "#3572A5", 2), Language("TypeScript", "#3178c6", 1))))
    assert abs(luminance(look.fur) - luminance(look.stripes)) >= 0.08


def test_sprite_rows_are_rectangular():
    for stage, frames in SPRITES.items():
        for name, rows in frames.items():
            assert len({len(r) for r in rows}) == 1, (stage, name)


def test_cat_svg_awake_and_asleep():
    look = cat_look(STATS)
    markup, css, w, h = cat_svg(look, 4, asleep=False, cls="t")
    parses(markup)
    assert w == 21 * 4 and h == 20 * 4
    assert "Z" not in markup
    assert "@keyframes" in css
    asleep, _, _, _ = cat_svg(look, 4, asleep=True, cls="t")
    parses(asleep)
    assert "Z" in asleep


def test_cat_sizes_grow_with_stage():
    sizes = [cat_svg(replace(cat_look(STATS), stage=s), 4, False, "t")[2] for s in ("kitten", "young", "grown")]
    assert sizes[0] < sizes[1] < sizes[2]


def test_icons():
    assert len(ICON_NAMES) >= 10
    assert set(ICON_NAMES) >= {"folder", "floppy", "terminal", "shield", "bug", "drone", "flag", "key", "lock",
                               "chip", "globe", "paw"}
    for name, (rows, palette) in ICONS.items():
        assert len(rows) == 12, name
        assert all(len(r) == 12 for r in rows), name
        assert set("".join(rows)) <= set(palette) | {"."}, name
        parses(icon_svg(name, 10, 10, 3))
