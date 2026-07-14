"""Render the repository's public visual assets.

The PNG renderer requires Pillow plus Newsreader, IBM Plex Sans, and IBM Plex
Mono in ``CRITICALITY_FONT_DIR`` (``.fonts`` by default). The SVG files remain
the editable sources and name those fonts without embedding them.
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "docs" / "brand"
SOCIAL_PNG = ROOT / "docs" / "social-preview.png"
SOCIAL_SVG = BRAND_DIR / "social-preview.svg"
MARK_PNG = BRAND_DIR / "mark-512.png"
MARK_SVG = BRAND_DIR / "mark.svg"

WIDTH = 1280
HEIGHT = 640
SCALE = 2

PAPER = "#F5F4F1"
INK = "#1E242C"
MUTED = "#636A70"
GRID = "#D8D7D2"
VERMILLION = "#C4462B"
TEAL = "#147D87"
GRAY = "#737980"

FONT_DIR = Path(os.environ.get("CRITICALITY_FONT_DIR", ROOT / ".fonts"))
NEWSREADER = FONT_DIR / "Newsreader.ttf"
PLEX_SANS = FONT_DIR / "IBMPlexSans.ttf"
PLEX_MONO = FONT_DIR / "IBMPlexMono-SemiBold.ttf"


def scaled(value: int | float) -> int:
    return round(value * SCALE)


def point(x: int | float, y: int | float) -> tuple[int, int]:
    return scaled(x), scaled(y)


def variable_font(
    path: Path,
    size: int,
    axes: list[int],
) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.name}. Set CRITICALITY_FONT_DIR to a directory "
            "containing Newsreader.ttf, IBMPlexSans.ttf, and "
            "IBMPlexMono-SemiBold.ttf."
        )
    loaded = ImageFont.truetype(str(path), scaled(size))
    loaded.set_variation_by_axes(axes)
    return loaded


def static_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.name}. Set CRITICALITY_FONT_DIR to the font directory."
        )
    return ImageFont.truetype(str(path), scaled(size))


def draw_line(
    draw: ImageDraw.ImageDraw,
    coordinates: list[tuple[int | float, int | float]],
    *,
    fill: str,
    width: int,
) -> None:
    draw.line(
        [point(x, y) for x, y in coordinates],
        fill=fill,
        width=scaled(width),
        joint="curve",
    )


def draw_mark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    stroke = max(round(size * 0.09), 3)
    segments = (
        (
            (x + size * 0.08, y + size * 0.25),
            (x + size * 0.31, y + size * 0.25),
            VERMILLION,
        ),
        (
            (x + size * 0.38, y + size * 0.25),
            (x + size * 0.61, y + size * 0.75),
            TEAL,
        ),
        (
            (x + size * 0.68, y + size * 0.75),
            (x + size * 0.92, y + size * 0.75),
            GRAY,
        ),
    )
    radius = stroke / 2
    for start, end, color in segments:
        draw_line(draw, [start, end], fill=color, width=stroke)
        for cap_x, cap_y in (start, end):
            draw.ellipse(
                (
                    scaled(cap_x - radius),
                    scaled(cap_y - radius),
                    scaled(cap_x + radius),
                    scaled(cap_y + radius),
                ),
                fill=color,
            )


def social_svg() -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640" role="img" aria-labelledby="title description">
  <title id="title">Criticality is a curve, not a score</title>
  <desc id="description">Two nodes share the same initial score. One remains critical while the other becomes fully adaptable as alternatives activate.</desc>
  <rect width="1280" height="640" fill="{PAPER}"/>
  <g fill="none" stroke-linecap="round" stroke-width="7">
    <path d="M72 76 H88" stroke="{VERMILLION}"/>
    <path d="M96 76 L112 106" stroke="{TEAL}"/>
    <path d="M120 106 H137" stroke="{GRAY}"/>
  </g>
  <text x="158" y="95" fill="{INK}" font-family="IBM Plex Sans, sans-serif" font-size="30" font-weight="600">Criticality Spectrometer</text>
  <text x="72" y="214" fill="{INK}" font-family="Newsreader, serif" font-size="72" font-weight="600">Criticality is a curve,</text>
  <text x="72" y="294" fill="{INK}" font-family="Newsreader, serif" font-size="72" font-weight="600">not a score.</text>
  <text x="75" y="390" fill="{INK}" font-family="IBM Plex Sans, sans-serif" font-size="25">Same score at &#964; = 0. Different criticality.</text>
  <g fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M760 225 H1198" stroke="{VERMILLION}" stroke-width="6"/>
    <path d="M760 225 L978 348 L1198 457" stroke="{TEAL}" stroke-width="6"/>
    <path d="M760 154 V493 H1198" stroke="{INK}" stroke-width="2"/>
    <path d="M760 225 H1198 M760 348 H1198 M760 457 H1198" stroke="{GRID}" stroke-width="1"/>
  </g>
  <circle cx="760" cy="225" r="12" fill="{PAPER}" stroke="{INK}" stroke-width="4"/>
  <circle cx="760" cy="225" r="4" fill="{INK}"/>
  <g fill="{INK}" font-family="IBM Plex Mono, monospace" font-size="14" font-weight="600" letter-spacing="1">
    <text x="760" y="132">MISSION LOSS</text>
    <text x="935" y="548">ADAPTATION HORIZON (TAU)</text>
  </g>
  <text x="1014" y="195" fill="{VERMILLION}" font-family="IBM Plex Mono, monospace" font-size="16" font-weight="600">PERSISTENT</text>
  <text x="1006" y="354" fill="{TEAL}" font-family="IBM Plex Mono, monospace" font-size="16" font-weight="600">FULLY ADAPTABLE</text>
  <g fill="{MUTED}" font-family="IBM Plex Mono, monospace" font-size="14">
    <text x="754" y="520">0</text><text x="971" y="520">12</text><text x="1188" y="520">24</text>
  </g>
  <path d="M72 571 H1208" stroke="{GRID}"/>
  <text x="72" y="605" fill="{MUTED}" font-family="IBM Plex Mono, monospace" font-size="14" font-weight="600" letter-spacing="1">AND/OR DEPENDENCY SYSTEMS  /  PYTHON  /  MIT</text>
</svg>
"""


def mark_svg() -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512" role="img" aria-labelledby="title description">
  <title id="title">Criticality Spectrometer mark</title>
  <desc id="description">Three strokes show persistent, adaptable, and no-impact criticality curves.</desc>
  <g fill="none" stroke-linecap="round" stroke-width="44">
    <path d="M62 126 H182" stroke="{VERMILLION}"/>
    <path d="M202 126 L322 386" stroke="{TEAL}"/>
    <path d="M342 386 H462" stroke="{GRAY}"/>
  </g>
</svg>
"""


def render_social_png() -> Image.Image:
    image = Image.new("RGB", (scaled(WIDTH), scaled(HEIGHT)), PAPER)
    draw = ImageDraw.Draw(image)

    display = variable_font(NEWSREADER, 72, [600, 72])
    brand = variable_font(PLEX_SANS, 30, [600, 100])
    support = variable_font(PLEX_SANS, 25, [400, 100])
    mono = static_font(PLEX_MONO, 14)
    mono_label = static_font(PLEX_MONO, 16)

    draw_mark(draw, 69, 53, 70)
    draw.text(point(158, 61), "Criticality Spectrometer", fill=INK, font=brand)
    draw.text(point(72, 143), "Criticality is a curve,", fill=INK, font=display)
    draw.text(point(72, 223), "not a score.", fill=INK, font=display)
    draw.text(
        point(75, 366),
        "Same score at \u03c4 = 0. Different criticality.",
        fill=INK,
        font=support,
    )

    chart_left = 760
    chart_right = 1198
    chart_top = 154
    chart_bottom = 493
    shared_y = 225

    for y in (shared_y, 348, 457):
        draw_line(draw, [(chart_left, y), (chart_right, y)], fill=GRID, width=1)
    draw_line(draw, [(chart_left, chart_top), (chart_left, chart_bottom)], fill=INK, width=2)
    draw_line(draw, [(chart_left, chart_bottom), (chart_right, chart_bottom)], fill=INK, width=2)

    draw_line(draw, [(760, shared_y), (1198, shared_y)], fill=VERMILLION, width=6)
    draw_line(draw, [(760, shared_y), (978, 348), (1198, 457)], fill=TEAL, width=6)

    draw.ellipse(
        (scaled(748), scaled(shared_y - 12), scaled(772), scaled(shared_y + 12)),
        fill=PAPER,
        outline=INK,
        width=scaled(4),
    )
    draw.ellipse(
        (scaled(756), scaled(shared_y - 4), scaled(764), scaled(shared_y + 4)),
        fill=INK,
    )

    draw.text(point(760, 111), "MISSION LOSS", fill=INK, font=mono)
    draw.text(point(1014, 171), "PERSISTENT", fill=VERMILLION, font=mono_label)
    draw.text(point(1006, 330), "FULLY ADAPTABLE", fill=TEAL, font=mono_label)
    for x, horizon in ((754, "0"), (971, "12"), (1188, "24")):
        draw.text(point(x, 501), horizon, fill=MUTED, font=mono)
    draw.text(point(935, 529), "ADAPTATION HORIZON (TAU)", fill=INK, font=mono)

    draw_line(draw, [(72, 571), (1208, 571)], fill=GRID, width=1)
    draw.text(
        point(72, 587),
        "AND/OR DEPENDENCY SYSTEMS  /  PYTHON  /  MIT",
        fill=MUTED,
        font=mono,
    )

    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def render_mark_png() -> Image.Image:
    image = Image.new("RGBA", (scaled(512), scaled(512)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_mark(draw, 38, 42, 436)
    return image.resize((512, 512), Image.Resampling.LANCZOS)


def write_assets() -> None:
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    SOCIAL_SVG.write_text(social_svg())
    MARK_SVG.write_text(mark_svg())
    render_social_png().save(SOCIAL_PNG, format="PNG", optimize=True)
    render_mark_png().save(MARK_PNG, format="PNG", optimize=True)
    for path in (SOCIAL_PNG, SOCIAL_SVG, MARK_PNG, MARK_SVG):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    write_assets()
