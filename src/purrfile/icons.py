"""Original 12x12 pixel icons for the desktop. Pixel art, not emoji, so every viewer sees the same thing."""
from __future__ import annotations

from .sprites import pixel_rects

K = "#1b1f2a"

ICONS: dict[str, tuple[tuple[str, ...], dict[str, str]]] = {
    "folder": ((
        "............", ".KKKK.......", "KYYYYK......", "KYYYYKKKKKK.", "KyyyyyyyyyyK", "KYYYYYYYYYYK",
        "KYYYYYYYYYYK", "KYYYYYYYYYYK", "KYYYYYYYYYYK", "KYYYYYYYYYYK", ".KKKKKKKKKK.", "............",
    ), {"K": K, "Y": "#f2c94c", "y": "#d9a521"}),
    "floppy": ((
        "KKKKKKKKKKK.", "KBBSSSSSBBBK", "KBBSSDSSBBBK", "KBBSSDSSBBBK", "KBBSSSSSBBBK", "KBBBBBBBBBBK",
        "KBLLLLLLLLBK", "KBLLLLLLLLBK", "KBLDDDDDDLBK", "KBLLLLLLLLBK", "KBLLLLLLLLBK", "KKKKKKKKKKKK",
    ), {"K": K, "B": "#3b6fd4", "S": "#c9ced8", "L": "#f4f4f4", "D": "#1d3f85"}),
    "terminal": ((
        "KKKKKKKKKKKK", "KGGGGGGGGGGK", "KGNNNNNNNNGK", "KGNgNNNNNNGK", "KGNNgNNNNNGK", "KGNgNNNNNNGK",
        "KGNNNNgggNGK", "KGNNNNNNNNGK", "KGGGGGGGGGGK", "KKKKKKKKKKKK", "....KGGK....", "..KKKKKKKK..",
    ), {"K": K, "G": "#c9ced8", "N": "#0b0f14", "g": "#3fb950"}),
    "shield": ((
        "KKKKKKKKKKKK", "KSSSSSsssssK", "KSSSSSssssWK", "KSSSSSsssWWK", "KSWSSSssWWsK", "KSWWSSsWWssK",
        ".KSWWWWsssK.", "..KSWWsssK..", "..KSSSsssK..", "...KSSssK...", "....KSsK....", ".....KK.....",
    ), {"K": K, "S": "#3b8eea", "s": "#2563c4", "W": "#ffffff"}),
    "bug": ((
        "..K......K..", "...K....K...", "....KKKK....", "...KWKKWK...", "K..KKKKKK..K", ".KKRRRRRRKK.",
        "...RRRKRRR..", "KKKRRRKRRRKK", "...RRRKRRR..", ".KKRRRKRRRKK", "...KRRKRRK..", "....KKKKK...",
    ), {"K": K, "R": "#e5534b", "W": "#ffffff"}),
    "drone": ((
        "KKKK....KKKK", ".KK......KK.", "..K......K..", "..KKKKKKKK..", "...KGGGGK...", "..KGGBBGGK..",
        "..KGGGGGGK..", "...KKKKKK...", "..K..RR..K..", ".KK......KK.", "KKKK....KKKK", "............",
    ), {"K": K, "G": "#8b95a7", "B": "#3b8eea", "R": "#e5534b"}),
    "flag": ((
        ".K..........", ".KRRRRRR....", ".KRRRRRRRR..", ".KRRRRRRRRR.", ".KRRRRRRRR..", ".KRRRRRR....",
        ".K..........", ".K..........", ".K..........", ".K..........", "KKK.........", "KKK.........",
    ), {"K": K, "R": "#e5534b"}),
    "key": ((
        "............", "..KKKK......", ".KYYYYK.....", "KYY..YYK....", "KYY..YYKKKKK", "KYY..YYYYYYK",
        "KYY..YYKYKYK", ".KYYYYK.K.K.", "..KKKK......", "............", "............", "............",
    ), {"K": K, "Y": "#f2c94c"}),
    "lock": ((
        "....KKKK....", "...KGGGGK...", "..KGK..KGK..", "..KGK..KGK..", "..KGK..KGK..", ".KKKKKKKKKK.",
        ".KYYYYYYYYK.", ".KYYYKKYYYK.", ".KYYYKKYYYK.", ".KYYYYYYYYK.", ".KYYYYYYYYK.", ".KKKKKKKKKK.",
    ), {"K": K, "G": "#c9ced8", "Y": "#f2c94c"}),
    "chip": ((
        "...P.P.P.P..", "..KKKKKKKK..", "PPKCCCCCCKPP", "..KCggggCK..", "PPKCgCCgCKPP", "..KCgCCgCK..",
        "PPKCggggCKPP", "..KCCCCCCK..", "PPKCCCCCCKPP", "..KKKKKKKK..", "...P.P.P.P..", "............",
    ), {"K": K, "C": "#2b3340", "g": "#3fb950", "P": "#c9ced8"}),
    "globe": ((
        "....KKKK....", "..KKBBGBKK..", ".KBBGGGBBBK.", ".KBGGGGBBBK.", "KBBBGGBBBGBK", "KBBBBGBBGGBK",
        "KBBBBBBGGGBK", "KBGGBBBBGBBK", ".KBGGGBBBBK.", ".KBBGBBBBBK.", "..KKBBBBKK..", "....KKKK....",
    ), {"K": K, "B": "#3b8eea", "G": "#3fb950"}),
    "paw": ((
        "..KK.KK.KK..", ".KPPKPPKPPK.", ".KPPKPPKPPK.", "..KK.KK.KK..", "............", "...KKKKKK...",
        "..KPPPPPPK..", ".KPPPPPPPPK.", ".KPPPPPPPPK.", ".KPPPPPPPPK.", "..KPPKKPPK..", "...KK..KK...",
    ), {"K": K, "P": "#f29bb0"}),
}
ICON_NAMES: tuple[str, ...] = tuple(ICONS)


def icon_svg(name: str, x: float, y: float, px: float) -> str:
    rows, palette = ICONS[name]
    return f'<g transform="translate({x:g},{y:g})" shape-rendering="crispEdges">{pixel_rects(rows, palette, px)}</g>'
