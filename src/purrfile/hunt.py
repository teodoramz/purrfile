"""Snake Hunter: add a cat to a Platane/snk SVG that waits in the corner and pounces on the snake.

The snk file animates everything with CSS keyframes over one loop. We read the snake head's path,
pick the moment it passes closest to the cat's corner, and rewrite the loop so that:

* the cat wiggles, jumps, and lands on the head exactly at that moment,
* the snake vanishes there and the squares it had not eaten yet stay on the graph,
* the loop restarts RESTART_MS after the catch (every earlier keyframe is rescaled to the new length).

Anything unexpected raises HuntError; callers keep the original file.
"""
from __future__ import annotations

import math
import re
import xml.dom.minidom
from dataclasses import dataclass

from .sprites import CatLook, cat_svg
from .svgtext import SANS, text_block, text_width, wrap

MARKER = "purrfile-hunter"
RESTART_MS = 10_000
JUMP_MS = 600
WAIT_MS = 2_600
CELEBRATE_MS = 5_000
WINDOW = (55.0, 95.0)
GROW_UP = 88
CAT_PX = 2
CORNER_INSET = 40

BUBBLE_W, BUBBLE_PAD, BUBBLE_SIZE, BUBBLE_LH = 300, 11, 12, 16
LINES = {
    1: "It looks like a snake is eating your commits. Want me to deal with it?",
    2: "Shh… wait for it…",
    3: "GOT IT. You're welcome.",
}


class HuntError(Exception):
    """The SVG is not a snk animation we understand."""


@dataclass(frozen=True)
class HuntPlan:
    duration_ms: int
    catch_pct: float  # of the original loop
    head_xy: tuple[float, float]
    new_duration_ms: int
    saved_cells: frozenset[str]
    graph_right: float


_KEYFRAMES = re.compile(r"@keyframes ([csu]\w*)\{((?:[\d.,%]+\{[^}]*\})+)\}")


def _points(body: str) -> list[tuple[float, str]]:
    return sorted(
        (float(p.rstrip("%")), decl) for sel, decl in re.findall(r"([\d.,%]+)\{([^}]*)\}", body) for p in sel.split(",")
    )


def plan_hunt(svg: str) -> HuntPlan:
    try:
        xml.dom.minidom.parseString(svg)
    except Exception as exc:  # noqa: BLE001 - any parse failure means "not a file we can touch"
        raise HuntError(f"not a well-formed SVG: {exc}") from exc
    m = re.search(r"\.s\{[^}]*?(\d+)ms", svg)
    s0 = re.search(r"@keyframes s0\{((?:[\d.,%]+\{[^}]*\})+)\}", svg)
    cells_x = [float(x) for x in re.findall(r'<rect class="c[^"]*" x="([\d.]+)"', svg)]
    if not (m and s0 and cells_x and re.search(r"\.s\.s\d+\{", svg)):
        raise HuntError("no Platane/snk snake found (expected .s, @keyframes s0, and .c cells)")
    duration = int(m.group(1))
    head = []
    for pct, decl in _points(s0.group(1)):
        t = re.match(r"transform:translate\((-?[\d.]+)px,(-?[\d.]+)px\)", decl)
        if t:
            head.append((pct, (float(t.group(1)), float(t.group(2)))))
    graph_right = max(cells_x) + 12
    target = (graph_right - CORNER_INSET, 0.0)
    candidates = [(math.dist(xy, target), -pct, pct, xy) for pct, xy in head if WINDOW[0] <= pct <= WINDOW[1]]
    if not candidates:
        raise HuntError("the snake's path has no point inside the pounce window")
    _, _, catch, xy = min(candidates)
    saved = frozenset(
        name for name, body in _KEYFRAMES.findall(svg) if name.startswith("c") and _points(body)[0][0] > catch
    )
    new_duration = round(catch * duration / 100 + RESTART_MS)
    return HuntPlan(duration, catch, xy, new_duration, saved, graph_right)


def _rescale(svg: str, plan: HuntPlan) -> str:
    k = plan.duration_ms / plan.new_duration_ms
    catch_new = plan.catch_pct * k

    def remap(m: re.Match) -> str:
        name, pts = m.group(1), _points(m.group(2))
        if name in plan.saved_cells:
            return ""
        if name.startswith("c"):  # eaten before the catch: keep the final "eaten" state at 100%
            kept = [(p * k if p < 100 else 100.0, d) for p, d in pts if p <= plan.catch_pct or p == 100]
        else:  # snake segments and the progress bar hold their at-catch value
            at_catch = next((d for p, d in reversed(pts) if p <= plan.catch_pct), pts[0][1])
            kept = [(p * k, d) for p, d in pts if p <= plan.catch_pct] + [(catch_new, at_catch), (100.0, at_catch)]
        return f"@keyframes {name}{{" + "".join(f"{p:.3f}%{{{d}}}" for p, d in kept) + "}"

    svg = _KEYFRAMES.sub(remap, svg)
    return re.sub(rf"(?<![\d.]){plan.duration_ms}ms", f"{plan.new_duration_ms}ms", svg)


def _window(name: str, start: float, end: float) -> str:
    frames = []
    if start > 0:
        frames.append(f"0%,{max(0.0, start - 0.01):.3f}%{{opacity:0}}")
    frames.append(f"{start:.3f}%,{end:.3f}%{{opacity:1}}")
    if end < 100:
        frames.append(f"{end + 0.01:.3f}%,100%{{opacity:0}}")
    return f"@keyframes {name}{{{''.join(frames)}}}"


def _bubble(cls: str, text: str, right: float, bottom: float, tip: tuple[float, float]) -> str:
    lines = wrap(text, BUBBLE_W - 2 * BUBBLE_PAD, BUBBLE_SIZE, max_lines=2)
    widest = max(sum(text_width(t, BUBBLE_SIZE, bold=b) for t, b in row) for row in lines)
    w = min(BUBBLE_W, widest + 2 * BUBBLE_PAD)
    h = 2 * BUBBLE_PAD + len(lines) * BUBBLE_LH - (BUBBLE_LH - BUBBLE_SIZE)
    x, y = right - w, bottom - h
    base_r = x + w - 16
    base_l = base_r - 26
    return (
        f'<g class="{cls}">'
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" fill="#ffffe1" stroke="#000"/>'
        f'<path d="M{base_l:g},{bottom - 1:g} L{tip[0]:g},{tip[1]:g} L{base_r:g},{bottom - 1:g}" fill="#ffffe1" '
        f'stroke="#000" stroke-linejoin="round"/>'
        f'<rect x="{base_l + 1:g}" y="{bottom - 2.5:g}" width="{base_r - base_l - 2:g}" height="3" fill="#ffffe1"/>'
        + text_block(lines, x + BUBBLE_PAD, y + BUBBLE_PAD + BUBBLE_SIZE - 2, BUBBLE_SIZE, BUBBLE_LH,
                     f'font-family="{SANS}" fill="#000"')
        + "</g>"
    )


def hunt(svg: str, look: CatLook, joke: str) -> str:
    """Return the snk SVG with the hunter cat added. Already-hunted input comes back unchanged."""
    if MARKER in svg:
        return svg
    plan = plan_hunt(svg)
    view = re.search(r'viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    if not view:
        raise HuntError("no viewBox/width/height on the root <svg>")
    out = _rescale(svg, plan)
    D = plan.new_duration_ms
    catch = plan.catch_pct * plan.duration_ms / D
    jump, wait, celebrate = (ms / D * 100 for ms in (JUMP_MS, WAIT_MS, CELEBRATE_MS))
    lift, wait_start = catch - jump, catch - jump - wait

    cat_markup, cat_css, cat_w, cat_h = cat_svg(look, CAT_PX, asleep=False, cls="pf-h")
    spot = (plan.graph_right - 14 - cat_w, -cat_h - 4)
    hx, hy = plan.head_xy
    land = (hx + 8 - cat_w / 2, hy + 16 - cat_h)
    mid = ((spot[0] + land[0]) / 2, min(spot[1], land[1]) - 30)
    wiggle = "".join(
        f"{wait_start + i * wait / 12:.3f}%{{transform:translate({1.5 if i % 2 else -1.5}px,2px)}}" for i in range(12)
    )
    segments = re.findall(r"\.s\.(s\d+)\{", svg)
    css = (
        cat_css
        + f"@keyframes pf-hmove{{0%,{lift:.3f}%{{transform:translate({spot[0]:g}px,{spot[1]:g}px)}}"
        f"{(lift + catch) / 2:.3f}%{{transform:translate({mid[0]:g}px,{mid[1]:g}px)}}"
        f"{catch:.3f}%,100%{{transform:translate({land[0]:g}px,{land[1]:g}px)}}}}"
        f".pf-hcat{{transform:translate({spot[0]:g}px,{spot[1]:g}px);animation:pf-hmove {D}ms linear infinite}}"
        f"@keyframes pf-hwig{{0%,{wait_start:.3f}%{{transform:none}}{wiggle}{lift:.3f}%,100%{{transform:none}}}}"
        f".pf-hwig{{animation:pf-hwig {D}ms linear infinite}}"
        f"@keyframes caught{{0%,{catch:.3f}%{{opacity:1}}{catch + 0.02:.3f}%,100%{{opacity:0}}}}"
        + "".join(f".s.{n}{{animation-name:{n},caught}}" for n in segments)
        + "".join(f".c.{n}{{animation-name:none}}" for n in sorted(plan.saved_cells))
        + _window("pf-hb1", 0, wait_start - 0.1)
        + _window("pf-hb2", wait_start, catch)
        + _window("pf-hb3", catch + 0.02, catch + celebrate)
        + _window("pf-hb4", catch + celebrate + 0.02, 99.6)
        + "".join(f".pf-hb{i}{{{'' if i == 1 else 'opacity:0;'}animation:pf-hb{i} {D}ms linear infinite}}"
                  for i in range(1, 5))
    )
    right, bottom = spot[0] - 10, spot[1] - 18
    tip = (spot[0] + cat_w * 0.3, spot[1] + 4)
    texts = {**LINES, 4: joke}
    bubbles = "".join(_bubble(f"pf-hb{i}", texts[i], right, bottom, tip) for i in range(1, 5))
    cat = f'<g class="pf-hcat"><g class="pf-hwig">{cat_markup}</g></g>'
    out = out.replace("</style>", css + "</style>", 1)
    out = out[: out.rindex("</svg>")] + f'<g id="{MARKER}">{bubbles}{cat}</g></svg>'
    x, y, w, h, width, height = view.groups()
    new_root = (f'viewBox="{x} {float(y) - GROW_UP:g} {w} {float(h) + GROW_UP:g}" '
                f'width="{width}" height="{float(height) + GROW_UP:g}"')
    return out.replace(view.group(0), new_root, 1)
