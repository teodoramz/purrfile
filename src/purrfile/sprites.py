"""The cat: original pixel art, colored from the account's languages, sized by its contributions."""
from __future__ import annotations

from dataclasses import dataclass

from .stats import Stats
from .svgtext import SANS

DEFAULT_FUR = "#9aa3b5"
DEFAULT_STRIPES = "#6b7387"
EYES = "#f2c935"
OUTLINE = "#141a26"
PINK = "#f29bb0"
WHITE = "#ffffff"
FUR_LUMINANCE = (0.18, 0.70)
MIN_STRIPE_CONTRAST = 0.08

# K outline, F fur, D stripes, L belly, P pink, E eyes, W eye shine. Rows listed in EYES_AT blink.
SPRITES: dict[str, dict[str, tuple[str, ...]]] = {
    "grown": {
        "open": (
            ".K.............K.....", ".KK...........KK.....", ".KPK.........KPK.....", ".KPFK.......KFPK.....",
            ".KFFFKKKKKKKFFFK.....", "KFFFFFDFFFDFFFFFK....", "KFFFFFFDFDFFFFFFK....", "KFFWEFFFFFFFWEFFK....",
            "KFFEEFFFFFFFEEFFK....", "KFFFFFLLPLLFFFFFK....", ".KFFFFLLKLLFFFFK.....", "..KFFFFFFFFFFFK....K.",
            "...KFFFLLLFFFK....KFK", "..KFFFLLLLLFFFK...KFK", "..KFFFLLLLLFFFK...KDK", ".KFFFFLLLLLFFFFK..KFK",
            ".KFFDFLLLLLFDFFK.KDK.", ".KFFKFFLLLFFKFFFFK...", ".KLLLKKKKKKKLLLKKK...", "..KKK.......KKK......",
        ),
        "shut": ("KFFFFFFFFFFFFFFFK....", "KFKKKFFFFFFFKKKFK...."),
    },
    "kitten": {
        "open": (
            ".K.........K...", ".KK.......KK...", ".KPK.....KPK...", "KFFFKKKKKFFFK..", "KFFFFDFDFFFFK..",
            "KFWEFFFFFWEFK..", "KFEEFFFFFEEFK..", "KFFFFLPLFFFFK..", ".KFFFLKLFFFK...", "..KFFFFFFFK..K.",
            "..KFLLLLLFK.KFK", ".KFFLLLLLFFKFK.", ".KLLKKKKKLLKK..", "..KK.....KK....",
        ),
        "shut": ("KFFFFFFFFFFFK..", "KFKKFFFFFKKFK.."),
    },
}
SPRITES["young"] = SPRITES["grown"]
EYES_AT = {"grown": 7, "young": 7, "kitten": 5}
STAGE_SCALE = {"kitten": 1.0, "young": 0.8, "grown": 1.0}


@dataclass(frozen=True)
class CatLook:
    stage: str
    fur: str
    stripes: str
    belly: str
    eyes: str = EYES
    outline: str = OUTLINE
    pink: str = PINK


def stage_for(year_total: int) -> str:
    if year_total < 100:
        return "kitten"
    if year_total < 500:
        return "young"
    return "grown"


def _rgb(c: str) -> tuple[float, float, float]:
    return tuple(int(c[i : i + 2], 16) / 255 for i in (1, 3, 5))


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, v)) * 255):02x}" for v in rgb)


def _mix(a: str, b: str, t: float) -> str:
    return _hex(tuple(x * (1 - t) + y * t for x, y in zip(_rgb(a), _rgb(b))))


def luminance(c: str) -> float:
    def lin(v):
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in _rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _clamp_luminance(c: str, low: float, high: float) -> str:
    for _ in range(40):
        lum = luminance(c)
        if lum < low:
            c = _mix(c, WHITE, 0.08)
        elif lum > high:
            c = _mix(c, "#000000", 0.08)
        else:
            break
    return c


def cat_look(stats: Stats) -> CatLook:
    langs = [l for l in stats.top_languages if l.color]
    if not langs:
        fur, stripes = DEFAULT_FUR, DEFAULT_STRIPES
    else:
        fur = _clamp_luminance(_mix(langs[0].color, DEFAULT_FUR, 0.45), *FUR_LUMINANCE)
        stripes = langs[1].color if len(langs) > 1 else _mix(fur, "#000000", 0.25)
        toward = "#000000" if luminance(fur) > 0.3 else WHITE
        for _ in range(20):
            if abs(luminance(fur) - luminance(stripes)) >= MIN_STRIPE_CONTRAST:
                break
            stripes = _mix(stripes, toward, 0.12)
    return CatLook(stage=stage_for(stats.year_total), fur=fur, stripes=stripes, belly=_mix(fur, WHITE, 0.75))


def pixel_rects(rows, palette: dict[str, str], px: float, y0: int = 0) -> str:
    """One <rect> per horizontal run of a color; '.' (or anything not in the palette) is transparent."""
    out = []
    for y, row in enumerate(rows, start=y0):
        x = 0
        while x < len(row):
            ch = row[x]
            run = 1
            while x + run < len(row) and row[x + run] == ch:
                run += 1
            if ch in palette:
                out.append(
                    f'<rect x="{x * px:g}" y="{y * px:g}" width="{run * px + 0.02:g}" height="{px + 0.02:g}" fill="{palette[ch]}"/>'
                )
            x += run
    return "".join(out)


def cat_svg(look: CatLook, px: float, asleep: bool, cls: str) -> tuple[str, str, float, float]:
    """The cat drawn at (0, 0). Returns (markup, css, width, height); classes start with `cls`."""
    frames = SPRITES[look.stage]
    rows = frames["open"]
    px = px * STAGE_SCALE[look.stage]
    width, height = len(rows[0]) * px, len(rows) * px
    palette = {"K": look.outline, "F": look.fur, "D": look.stripes, "L": look.belly, "P": look.pink,
               "E": look.eyes, "W": WHITE}
    eye_row = EYES_AT[look.stage]
    body = [r if i not in (eye_row, eye_row + 1) else "" for i, r in enumerate(rows)]
    open_eyes = pixel_rects(rows[eye_row : eye_row + 2], palette, px, y0=eye_row)
    shut_eyes = pixel_rects(frames["shut"], palette, px, y0=eye_row)
    css = (
        f"@keyframes {cls}-bob{{50%{{transform:translateY({px * 0.5:g}px)}}}}"
        f".{cls}-bob{{animation:{cls}-bob 1.6s steps(1) infinite}}"
    )
    if asleep:
        size = max(9.0, px * 3.2)
        eyes = shut_eyes
        zzz = "".join(
            f'<text class="{cls}-z" style="animation-delay:{delay}s" x="{width * 0.72:g}" y="{-px:g}" '
            f'font-family="{SANS}" font-size="{size * scale:g}" font-weight="bold" fill="#8b8bf0">{letter}</text>'
            for letter, delay, scale in (("z", 0, 0.8), ("Z", 1.1, 1.0))
        )
        css += (
            f"@keyframes {cls}-zz{{0%{{opacity:0;transform:translate(0,0)}}30%{{opacity:1}}"
            f"100%{{opacity:0;transform:translate({px * 3:g}px,{-px * 5:g}px)}}}}"
            f".{cls}-z{{opacity:0;animation:{cls}-zz 2.2s linear infinite}}"
        )
    else:
        zzz = ""
        eyes = f'<g class="{cls}-eo">{open_eyes}</g><g class="{cls}-es">{shut_eyes}</g>'
        css += (
            f"@keyframes {cls}-bo{{0%,93%{{opacity:1}}94%,98%{{opacity:0}}99%,100%{{opacity:1}}}}"
            f"@keyframes {cls}-bs{{0%,93%{{opacity:0}}94%,98%{{opacity:1}}99%,100%{{opacity:0}}}}"
            f".{cls}-eo{{animation:{cls}-bo 3.2s steps(1) infinite}}"
            f".{cls}-es{{opacity:0;animation:{cls}-bs 3.2s steps(1) infinite}}"
        )
    markup = (
        f'<g class="{cls}-bob" shape-rendering="crispEdges">{pixel_rects(body, palette, px)}{eyes}</g>{zzz}'
    )
    return markup, css, width, height
