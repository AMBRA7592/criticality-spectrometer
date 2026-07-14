"""Render the README's deterministic curve figure from committed results."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "examples" / "ai_compute" / "results.json"
OUTPUT = ROOT / "docs" / "criticality-curves.svg"

WIDTH = 1200
HEIGHT = 600
PLOT_LEFT = 105
PLOT_RIGHT = 950
PLOT_TOP = 105
PLOT_BOTTOM = 465

SERIES = (
    ("asml_euv", "ASML EUV", "persistent", "#C9493A"),
    ("tsmc_advanced", "TSMC advanced", "fully adaptable", "#087E8B"),
    ("germanium", "Germanium", "none", "#646B73"),
)


def x_position(index: int, count: int) -> float:
    return PLOT_LEFT + index * (PLOT_RIGHT - PLOT_LEFT) / (count - 1)


def y_position(value: float, maximum: float) -> float:
    return PLOT_BOTTOM - value * (PLOT_BOTTOM - PLOT_TOP) / maximum


def render() -> str:
    results = json.loads(RESULTS.read_text())["reports"]["frontier_stack"]
    horizons = results["run"]["horizons"]
    curves = results["nodes"]
    maximum = max(results["baseline"], 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">',
        '<title id="title">Criticality curves across adaptation horizons</title>',
        '<desc id="description">ASML EUV remains critical, TSMC advanced becomes adaptable, and germanium has no impact on the selected mission.</desc>',
        '<rect width="1200" height="600" fill="#F7F8F6"/>',
        '<text x="70" y="54" fill="#172128" font-family="system-ui, sans-serif" font-size="30" font-weight="700">One network, three criticality shapes</text>',
        '<text x="70" y="83" fill="#566068" font-family="system-ui, sans-serif" font-size="16">Node-removal impact on the ordered frontier mission as alternatives activate</text>',
    ]

    for tick in range(maximum + 1):
        y = y_position(tick, maximum)
        parts.append(f'<line x1="{PLOT_LEFT}" y1="{y:.1f}" x2="{PLOT_RIGHT}" y2="{y:.1f}" stroke="#D8DCD8" stroke-width="1"/>')
        parts.append(f'<text x="82" y="{y + 6:.1f}" text-anchor="end" fill="#566068" font-family="system-ui, sans-serif" font-size="15">{tick}</text>')

    parts.extend(
        [
            f'<line x1="{PLOT_LEFT}" y1="{PLOT_TOP}" x2="{PLOT_LEFT}" y2="{PLOT_BOTTOM}" stroke="#172128" stroke-width="2"/>',
            f'<line x1="{PLOT_LEFT}" y1="{PLOT_BOTTOM}" x2="{PLOT_RIGHT}" y2="{PLOT_BOTTOM}" stroke="#172128" stroke-width="2"/>',
            '<text x="26" y="290" transform="rotate(-90 26 290)" text-anchor="middle" fill="#172128" font-family="system-ui, sans-serif" font-size="16" font-weight="600">Mission loss</text>',
            f'<text x="{(PLOT_LEFT + PLOT_RIGHT) / 2:.1f}" y="545" text-anchor="middle" fill="#172128" font-family="system-ui, sans-serif" font-size="16" font-weight="600">Adaptation horizon (tau)</text>',
        ]
    )

    for index, horizon in enumerate(horizons):
        x = x_position(index, len(horizons))
        parts.append(f'<line x1="{x:.1f}" y1="{PLOT_BOTTOM}" x2="{x:.1f}" y2="{PLOT_BOTTOM + 8}" stroke="#172128" stroke-width="2"/>')
        parts.append(f'<text x="{x:.1f}" y="{PLOT_BOTTOM + 34}" text-anchor="middle" fill="#172128" font-family="system-ui, sans-serif" font-size="16">{html.escape(str(horizon))}</text>')

    label_offsets = {"asml_euv": -18, "tsmc_advanced": 28, "germanium": -18}
    for node_id, label, shape, color in SERIES:
        values = curves[node_id]["impact"]
        points = " ".join(
            f"{x_position(index, len(horizons)):.1f},{y_position(value, maximum):.1f}"
            for index, value in enumerate(values)
        )
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
        for index, value in enumerate(values):
            parts.append(f'<circle cx="{x_position(index, len(horizons)):.1f}" cy="{y_position(value, maximum):.1f}" r="7" fill="#F7F8F6" stroke="{color}" stroke-width="4"/>')
        last_y = y_position(values[-1], maximum) + label_offsets[node_id]
        parts.append(f'<line x1="{PLOT_RIGHT + 10}" y1="{y_position(values[-1], maximum):.1f}" x2="{PLOT_RIGHT + 28}" y2="{last_y:.1f}" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{PLOT_RIGHT + 36}" y="{last_y - 3:.1f}" fill="{color}" font-family="system-ui, sans-serif" font-size="16" font-weight="700">{html.escape(label)}</text>')
        parts.append(f'<text x="{PLOT_RIGHT + 36}" y="{last_y + 17:.1f}" fill="#566068" font-family="system-ui, sans-serif" font-size="13">{html.escape(shape)}</text>')

    parts.append('<text x="70" y="582" fill="#737B80" font-family="system-ui, sans-serif" font-size="12">Illustrative output from examples/ai_compute/model_frontier_stack.json; values are model-dependent.</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render())
    print(OUTPUT.relative_to(ROOT))
