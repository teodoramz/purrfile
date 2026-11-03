"""The Retro Desktop: an original retro-style desktop header with the cat in its own corner.

Layout is computed first (`_layout`, pure geometry and wrapped text) and drawn second, so tests can
check that every text fits its box and that the bubble never leaves the cat's zone.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from .daily import lines_for_day, pick_desktop_repos
from .icons import ICON_NAMES, icon_svg
from .lines import JOKES
from .snapshot import Snapshot
from .sprites import CatLook, _mix, cat_look, cat_svg
from .stats import Stats
from .svgtext import MONO, SANS, Line, esc, text_block, text_width, wrap

WIDTH, HEIGHT, TASKBAR = 720, 330, 30
ZONES = {"icons": (0, 210), "notepad": (215, 470), "cat": (480, 720)}

ICON_COLS = (8, 108)
ICON_ROWS = (12, 100, 188)
ICON_BOX_W = 96
ICON_PX = 3
LABEL_SIZE, LABEL_LH = 11, 13

NOTE_X, NOTE_Y, NOTE_W = 215, 20, 255
NOTE_TITLE_H, NOTE_PAD = 22, 10
NOTE_SIZE, NOTE_LH = 12, 16
NOTE_MAX_BOTTOM = 285

BUBBLE_X, BUBBLE_W, BUBBLE_BOTTOM, BUBBLE_TOP_MIN = 488, 224, 200, 10
BUBBLE_PAD, BUBBLE_SIZE, BUBBLE_LH = 12, 13, 17
BUBBLE_SECONDS = 5
CAT_PX, CAT_RIGHT, CAT_FEET = 4, 700, 296
QUIET_DAYS_ASLEEP = 7
RECENT_FALLBACK = 6


@dataclass
class TextBox:
    name: str
    x: float
    y: float  # first baseline
    w: float  # widest a line may be
    lines: list[Line]
    size: float
    line_height: float
    mono: bool = False


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float


@dataclass
class Icon:
    repo: str
    icon: str
    x: float
    y: float
    w: float
    label: TextBox


@dataclass
class Bubble(Rect):
    text: TextBox | None = None


@dataclass
class Layout:
    login: str
    icons: list[Icon]
    notepad: Rect
    notepad_text: TextBox
    bubbles: list[Bubble]
    lines: list[str]
    look: CatLook
    cat_stage: str
    asleep: bool
    cat: Rect
    sky: float
    tray: TextBox
    task_items: list[TextBox] = field(default_factory=list)

    def text_boxes(self) -> list[TextBox]:
        return ([i.label for i in self.icons] + [self.notepad_text] + [b.text for b in self.bubbles if b.text]
                + [self.tray] + self.task_items)


def _repo_pool(snap: Snapshot) -> list[str]:
    if snap.pinned:
        return [r.name for r in snap.pinned]
    recent = sorted((r for r in snap.repos if r.pushed_at), key=lambda r: r.pushed_at, reverse=True)
    return [r.name for r in recent[:RECENT_FALLBACK]]


def _layout(snap: Snapshot, stats: Stats, day: date, cat_name: str, extra_jokes: Sequence[str]) -> Layout:
    # Icons: two columns, row-major.
    icons = []
    for i, (repo, icon) in enumerate(pick_desktop_repos(_repo_pool(snap), snap.login, day, ICON_NAMES)):
        x, y = ICON_COLS[i % 2], ICON_ROWS[i // 2]
        label = TextBox(
            f"label:{repo}", x + ICON_BOX_W / 2, y + 12 * ICON_PX + 14, ICON_BOX_W - 4,
            wrap(repo, ICON_BOX_W - 4, LABEL_SIZE, max_lines=3, markup=False, break_after="-_."), LABEL_SIZE, LABEL_LH,
        )
        icons.append(Icon(repo, icon, x, y, ICON_BOX_W, label))

    # Notepad: about_me.txt
    inner = NOTE_W - 2 * NOTE_PAD
    note_lines: list[Line] = []

    def add(text: str, max_lines: int):
        note_lines.extend(wrap(text, inner, NOTE_SIZE, mono=True, max_lines=max_lines, markup=False, break_after="-_"))

    add(snap.name or snap.login, 1)
    if snap.bio:
        add(snap.bio, 3)
    if snap.location:
        add(f"location: {snap.location}", 1)
    tail = []
    if stats.latest_repo:
        tail.append((f"currently hacking on: {stats.latest_repo}", 2))
    if stats.top_languages:
        tail.append((f"favourite food: {stats.top_languages[0].name}", 1))
    if tail:
        note_lines.append([])
        for text, n in tail:
            add(text, n)
    body_top = NOTE_Y + NOTE_TITLE_H + NOTE_PAD
    note_h = NOTE_TITLE_H + 2 * NOTE_PAD + len(note_lines) * NOTE_LH
    notepad = Rect(NOTE_X, NOTE_Y, NOTE_W, min(note_h, NOTE_MAX_BOTTOM - NOTE_Y))
    notepad_text = TextBox("notepad", NOTE_X + NOTE_PAD, body_top + NOTE_SIZE - 1, inner, note_lines, NOTE_SIZE,
                           NOTE_LH, mono=True)

    # The cat and its bubbles.
    look = cat_look(stats)
    asleep = stats.quiet_days >= QUIET_DAYS_ASLEEP or stats.year_total == 0
    _, _, cat_w, cat_h = cat_svg(look, CAT_PX, asleep, "pf")
    cat = Rect(CAT_RIGHT - cat_w, CAT_FEET - cat_h, cat_w, cat_h)
    lines = lines_for_day(stats, tuple(JOKES) + tuple(extra_jokes), snap.login, day)
    max_bubble_lines = math.floor((BUBBLE_BOTTOM - BUBBLE_TOP_MIN - 2 * BUBBLE_PAD + (BUBBLE_LH - BUBBLE_SIZE)) / BUBBLE_LH)
    bubbles = []
    for i, line in enumerate(lines):
        wrapped = wrap(line, BUBBLE_W - 2 * BUBBLE_PAD, BUBBLE_SIZE, max_lines=max_bubble_lines)
        widest = max((sum(text_width(t, BUBBLE_SIZE, bold=b) for t, b in row) for row in wrapped), default=0)
        w = min(BUBBLE_W, widest + 2 * BUBBLE_PAD)
        x = BUBBLE_X + BUBBLE_W - w  # hug the right edge, above the cat
        h = 2 * BUBBLE_PAD + len(wrapped) * BUBBLE_LH - (BUBBLE_LH - BUBBLE_SIZE)
        y = BUBBLE_BOTTOM - h
        text = TextBox(f"bubble{i}", x + BUBBLE_PAD, y + BUBBLE_PAD + BUBBLE_SIZE - 2,
                       w - 2 * BUBBLE_PAD, wrapped, BUBBLE_SIZE, BUBBLE_LH)
        bubbles.append(Bubble(x, y, w, h, text))

    # Taskbar.
    task_y = HEIGHT - TASKBAR
    tray_text = f"{stats.current_streak_weeks}w streak · {stats.year_total} this year · {day.strftime('%b %d')}"
    tray_w = text_width(tray_text, 11)
    tray = TextBox("tray", WIDTH - 12 - tray_w, task_y + 19, tray_w, [[(tray_text, False)]], 11, 13)
    items = []
    x = 94
    for label, max_w in (("about_me.txt", 110), (cat_name, 110)):
        lines_ = wrap(label, max_w, 11, max_lines=1, markup=False)
        w = sum(text_width(t, 11) for t, _ in lines_[0]) if lines_ else 0
        items.append(TextBox(f"task:{label}", x + 8, task_y + 19, max_w, lines_, 11, 13))
        x += w + 26
    sky = min(1.0, stats.last7 / max(1, stats.busy_threshold))
    return Layout(snap.login, icons, notepad, notepad_text, bubbles, lines, look, look.stage, asleep, cat, sky,
                  tray, items)


def _bubble_css(count: int) -> str:
    total = count * BUBBLE_SECONDS
    css = []
    for i in range(count):
        start, end = 100 * i / count, 100 * (i + 1) / count
        frames = []
        if start > 0:
            frames.append(f"0%,{start - 0.01:.2f}%{{opacity:0}}")
        frames.append(f"{start:.2f}%,{end - 1.5:.2f}%{{opacity:1}}")
        frames.append(f"{end - 1:.2f}%,100%{{opacity:0}}")
        css.append(f"@keyframes pf-bk{i}{{{''.join(frames)}}}"
                   f".pf-b{i}{{{'' if i == 0 else 'opacity:0;'}animation:pf-bk{i} {total}s linear infinite}}")
    return "".join(css)


def _stars(login: str) -> str:
    rng = random.Random(f"{login}:stars")
    return "".join(
        f'<rect x="{rng.randrange(0, WIDTH)}" y="{rng.randrange(0, 160)}" width="2" height="2" fill="#fff"/>'
        for _ in range(42)
    )


def _window_buttons(right: float, y: float) -> str:
    out = []
    for i, glyph in enumerate(("_", "□", "×")):
        x = right - 18 * (3 - i)
        fill = "#d9462b" if glyph == "×" else "#2f6fe0"
        out.append(f'<rect x="{x}" y="{y}" width="15" height="15" rx="3" fill="{fill}" stroke="#fff"/>'
                   f'<text x="{x + 7.5}" y="{y + 11.5}" text-anchor="middle" font-family="{SANS}" font-size="10" '
                   f'font-weight="bold" fill="#fff">{glyph}</text>')
    return "".join(out)


def _bubble(b: Bubble, i: int, cat: Rect) -> str:
    tip_x, tip_y = cat.x + cat.w * 0.45, cat.y + 6
    base_r = max(b.x + 34, b.x + b.w - 50)
    base_l = max(b.x + 10, base_r - 24)
    bottom = b.y + b.h
    return (
        f'<g class="pf-b{i}">'
        f'<rect x="{b.x}" y="{b.y:g}" width="{b.w}" height="{b.h:g}" rx="10" fill="#ffffe1" stroke="#000"/>'
        f'<path d="M{base_l:g},{bottom - 1:g} L{tip_x:g},{tip_y:g} L{base_r:g},{bottom - 1:g}" fill="#ffffe1" '
        f'stroke="#000" stroke-linejoin="round"/>'
        f'<rect x="{base_l + 1:g}" y="{bottom - 2.5:g}" width="{base_r - base_l - 2:g}" height="3" fill="#ffffe1"/>'
        + text_block(b.text.lines, b.text.x, b.text.y, b.text.size, b.text.line_height, f'font-family="{SANS}" fill="#000"')
        + "</g>"
    )


def render_desktop(snap: Snapshot, stats: Stats, day: date, cat_name: str = "Mochi",
                   extra_jokes: Sequence[str] = ()) -> str:
    lay = _layout(snap, stats, day, cat_name, extra_jokes)
    cat_markup, cat_css, _, _ = cat_svg(lay.look, CAT_PX, lay.asleep, "pf")
    sky_top = _mix("#152347", "#3a5a9a", lay.sky)
    sky_bottom = _mix("#8a4a7c", "#f2a65a", lay.sky)
    task_y = HEIGHT - TASKBAR
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'role="img" aria-label="{esc(cat_name)} the cat on a tiny retro desktop">',
        f"<title>{esc(cat_name)} the cat on a tiny retro desktop</title>",
        "<defs>",
        f'<linearGradient id="pf-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky_top}"/>'
        f'<stop offset="1" stop-color="{sky_bottom}"/></linearGradient>',
        '<linearGradient id="pf-title" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f6fe0"/>'
        '<stop offset="1" stop-color="#1a46b0"/></linearGradient>',
        '<linearGradient id="pf-task" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3168d5"/>'
        '<stop offset="1" stop-color="#1941a5"/></linearGradient>',
        '<linearGradient id="pf-start" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3c9a3c"/>'
        '<stop offset="1" stop-color="#267a26"/></linearGradient>',
        '<linearGradient id="pf-tray" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1290e9"/>'
        '<stop offset="1" stop-color="#0f7fd6"/></linearGradient>',
        f'<clipPath id="pf-clip"><rect width="{WIDTH}" height="{HEIGHT}" rx="8"/></clipPath>',
        "</defs>",
        f"<style>{cat_css}{_bubble_css(len(lay.bubbles))}</style>",
        '<g clip-path="url(#pf-clip)">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#pf-sky)"/>',
        f'<g opacity="{0.85 - 0.6 * lay.sky:.2f}">{_stars(lay.login)}</g>',
        '<ellipse cx="170" cy="330" rx="300" ry="112" fill="#2a5a3a"/>',
        '<ellipse cx="610" cy="345" rx="340" ry="150" fill="#1f4a30"/>',
    ]
    # Icons with shadowed labels.
    for icon in lay.icons:
        parts.append(icon_svg(icon.icon, icon.x + (icon.w - 12 * ICON_PX) / 2, icon.y, ICON_PX))
        lb = icon.label
        for dx, fill in ((1, "#000"), (0, "#fff")):
            parts.append(text_block(lb.lines, lb.x + dx, lb.y + dx, lb.size, lb.line_height,
                                    f'font-family="{SANS}" text-anchor="middle" fill="{fill}"'))
    # Notepad.
    n = lay.notepad
    parts += [
        f'<rect x="{n.x + 3}" y="{n.y + 4}" width="{n.w}" height="{n.h:g}" rx="6" fill="#000" opacity="0.35"/>',
        f'<rect x="{n.x}" y="{n.y}" width="{n.w}" height="{n.h:g}" rx="6" fill="#fff" stroke="#0a246a"/>',
        f'<path d="M{n.x},{n.y + NOTE_TITLE_H} V{n.y + 6} Q{n.x},{n.y} {n.x + 6},{n.y} H{n.x + n.w - 6} '
        f'Q{n.x + n.w},{n.y} {n.x + n.w},{n.y + 6} V{n.y + NOTE_TITLE_H} Z" fill="url(#pf-title)"/>',
        f'<text x="{n.x + 8}" y="{n.y + 15}" font-family="{SANS}" font-size="11" font-weight="bold" fill="#fff">'
        "about_me.txt - Notepad</text>",
        _window_buttons(n.x + n.w - 3, n.y + 3),
    ]
    t = lay.notepad_text
    parts.append(text_block(t.lines, t.x, t.y, t.size, t.line_height, f'font-family="{MONO}" fill="#000"'))
    # Bubbles, then the cat.
    parts += [_bubble(b, i, lay.cat) for i, b in enumerate(lay.bubbles)]
    parts.append(f'<g transform="translate({lay.cat.x:g},{lay.cat.y:g})">{cat_markup}</g>')
    # Taskbar.
    parts += [
        f'<rect x="0" y="{task_y}" width="{WIDTH}" height="{TASKBAR}" fill="url(#pf-task)"/>',
        f'<path d="M0,{task_y} H70 Q84,{task_y} 84,{task_y + 15} Q84,{task_y + 30} 70,{task_y + 30} H0 Z" '
        'fill="url(#pf-start)"/>',
        icon_svg("paw", 10, task_y + 6, 1.5),
        f'<text x="32" y="{task_y + 20}" font-family="{SANS}" font-size="14" font-style="italic" font-weight="bold" '
        'fill="#fff">start</text>',
    ]
    for item in lay.task_items:
        w = sum(text_width(s, item.size) for s, _ in item.lines[0]) + 16 if item.lines else 16
        parts.append(f'<rect x="{item.x - 8:g}" y="{task_y + 4}" width="{w:g}" height="22" rx="3" fill="#3c81f3" '
                     'stroke="#1d4fb8"/>')
        parts.append(text_block(item.lines, item.x, item.y, item.size, item.line_height,
                                f'font-family="{SANS}" fill="#fff"'))
    tr = lay.tray
    parts += [
        f'<rect x="{tr.x - 10:g}" y="{task_y}" width="{WIDTH - tr.x + 10:g}" height="{TASKBAR}" fill="url(#pf-tray)"/>',
        text_block(tr.lines, tr.x, tr.y, tr.size, tr.line_height, f'font-family="{SANS}" fill="#fff"'),
        "</g>",
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="8" fill="none" stroke="#0a246a"/>',
        "</svg>",
    ]
    return "".join(parts)
