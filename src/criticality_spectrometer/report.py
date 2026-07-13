"""
Report generation.

Turns a SweepResult into a deterministic JSON document or a compact text table.
JSON output is sorted and stable so runs are byte-for-byte reproducible.
"""

from __future__ import annotations

import json

from .model import Model
from .sweep import SweepResult
from .classify import policy_verb


def to_json(model: Model, result: SweepResult, include_policy: bool = False) -> str:
    """Deterministic JSON. Keys sorted; node order sorted."""
    doc = {
        "model": {"name": model.name, "version": model.version},
        "horizons": result.horizons,
        "baseline": result.baseline,
        "nodes": {},
    }
    for node in sorted(result.curves):
        c = result.curves[node]
        entry = {
            "impact": c.impact,
            "shape": c.shape,
            "or_survival_gap": result.or_survival_gap.get(node, []),
        }
        if include_policy:
            entry["policy_verb"] = policy_verb(c.shape)
        doc["nodes"][node] = entry
    return json.dumps(doc, indent=2, sort_keys=True)


def to_text(model: Model, result: SweepResult, include_policy: bool = False) -> str:
    """Compact human-readable table."""
    lines = []
    title = model.name or "model"
    lines.append(f"Criticality Spectrometer — {title} (v{model.version})")
    lines.append(f"horizons: {result.horizons}   baseline: {result.baseline}")
    lines.append("")
    header = f"{'node':<24} {'impact':<20} {'shape':<20} {'OR gap':<16}"
    if include_policy:
        header += " policy"
    lines.append(header)
    lines.append("-" * len(header))
    for node in sorted(result.curves):
        c = result.curves[node]
        gap = result.or_survival_gap.get(node, [])
        row = f"{node:<24} {str(c.impact):<20} {c.shape:<20} {str(gap):<16}"
        if include_policy:
            row += f" {policy_verb(c.shape)}"
        lines.append(row)
    return "\n".join(lines)
