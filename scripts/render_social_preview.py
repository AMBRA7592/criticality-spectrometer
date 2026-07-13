"""Render the repository's 1280x640 GitHub social preview.

Requires Pillow. The output is deterministic for a given font installation.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "social-preview.png"

WIDTH = 1280
HEIGHT = 640
SCALE = 2

BACKGROUND = "#F7F8F6"
TEXT = "#172128"
MUTED = "#5C666D"
GRID = "#D7DCDA"
PERSISTENT = "#C9493A"
ADAPTABLE = "#087E8B"
NONE = "#646B73"

FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")


def scaled(value: int | float) -> int:
    return round(value * SCALE)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), scaled(size))


def point(x: int | float, y: int | float) -> tuple[int, int]:
    return scaled(x), scaled(y)


def line(
    draw: ImageDraw.ImageDraw,
    coordinates: list[tuple[int | float, int | float]],
    *,
    fill: str,
    width: int,
) -> None:
    draw.line([point(x, y) for x, y in coordinates], fill=fill, width=scaled(width), joint="curve")


def circle(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    *,
    radius: int,
    outline: str,
) -> None:
    draw.ellipse(
        (scaled(x - radius), scaled(y - radius), scaled(x + radius), scaled(y + radius)),
        fill=BACKGROUND,
        outline=outline,
        width=scaled(3),
    )


def render() -> Image.Image:
    image = Image.new("RGB", (scaled(WIDTH), scaled(HEIGHT)), BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = font(FONT_BOLD, 34)
    headline_font = font(FONT_BOLD, 59)
    body_font = font(FONT_REGULAR, 22)
    label_font = font(FONT_BOLD, 18)
    small_font = font(FONT_REGULAR, 15)
    footer_font = font(FONT_BOLD, 15)

    # A compact spectral mark: three measured outcomes at the same horizon.
    line(draw, [(69, 62), (69, 93)], fill=PERSISTENT, width=7)
    line(draw, [(84, 72), (84, 93)], fill=ADAPTABLE, width=7)
    line(draw, [(99, 84), (99, 93)], fill=NONE, width=7)
    draw.text(point(119, 58), "Criticality Spectrometer", fill=TEXT, font=title_font)

    draw.text(point(69, 155), "Criticality is a curve,", fill=TEXT, font=headline_font)
    draw.text(point(69, 221), "not a score.", fill=TEXT, font=headline_font)

    draw.text(
        point(72, 323),
        "Measure how node-removal impact changes\nas alternatives become available.",
        fill=MUTED,
        font=body_font,
        spacing=scaled(8),
    )

    # Method chart.
    chart_left = 755
    chart_right = 1193
    chart_top = 126
    chart_bottom = 496
    x_values = (chart_left, 948, chart_right)

    draw.text(point(chart_left, 77), "Node-removal impact", fill=TEXT, font=label_font)
    for y in (chart_top, 250, 373, chart_bottom):
        line(draw, [(chart_left, y), (chart_right, y)], fill=GRID, width=1)
    line(draw, [(chart_left, chart_top), (chart_left, chart_bottom)], fill=TEXT, width=2)
    line(draw, [(chart_left, chart_bottom), (chart_right, chart_bottom)], fill=TEXT, width=2)

    series = (
        (PERSISTENT, ((755, 174), (948, 174), (1193, 174)), "Persistent", "remains critical", 126),
        (ADAPTABLE, ((755, 238), (948, 334), (1193, 431)), "Fully adaptable", "mission recovers", 284),
        (NONE, ((755, 473), (948, 473), (1193, 473)), "No mission impact", "stays at zero", 418),
    )

    for color, coordinates, label, description, label_y in series:
        line(draw, list(coordinates), fill=color, width=5)
        for x, y in coordinates:
            circle(draw, x, y, radius=6, outline=color)
        draw.text(point(990, label_y), label, fill=color, font=label_font)
        draw.text(point(990, label_y + 24), description, fill=MUTED, font=small_font)

    for x, horizon in zip(x_values, ("0", "12", "24"), strict=True):
        draw.text(point(x - 6, 518), horizon, fill=MUTED, font=small_font)
    draw.text(point(861, 557), "Adaptation horizon (\u03c4)", fill=TEXT, font=small_font)

    line(draw, [(69, 573), (1193, 573)], fill=GRID, width=1)
    draw.text(
        point(69, 594),
        "AND/OR dependency systems  /  Python  /  MIT",
        fill=MUTED,
        font=footer_font,
    )

    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    render().save(OUTPUT, format="PNG", optimize=True)
    print(OUTPUT.relative_to(ROOT))
