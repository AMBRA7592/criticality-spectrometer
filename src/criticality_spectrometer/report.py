"""
Report generation.

Turns a SweepResult into a deterministic JSON document or a compact text table.
JSON output is sorted and stable so runs are byte-for-byte reproducible.
"""

from __future__ import annotations

import json
from importlib import resources

from ._version import __version__
from .classify import policy_verb
from .model import MODEL_SCHEMA_VERSION, Model
from .sweep import SweepResult


RESULT_SCHEMA_VERSION = "0.1"


def _load_result_schema() -> dict:
    with resources.files("criticality_spectrometer._schema").joinpath(
        "result.schema.json"
    ).open("r", encoding="utf-8") as f:
        return json.load(f)


def instrument_block() -> dict:
    """The instrument identity stamp shared by every self-identifying document."""
    return {"name": "criticality-spectrometer", "version": __version__}


def model_block(model: Model) -> dict:
    """The model identity stamp shared by every self-identifying document."""
    return {
        "name": model.name,
        "version": model.version,
        "schema_version": MODEL_SCHEMA_VERSION,
        "sha256": model.source_sha256,
    }


def to_document(
    model: Model,
    result: SweepResult,
    include_policy: bool = False,
    compute_or_gap: bool | None = None,
) -> dict:
    """Build a deterministic, self-identifying result document."""
    if compute_or_gap is None:
        compute_or_gap = bool(result.or_survival_gap)
    doc = {
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "instrument": instrument_block(),
        "model": model_block(model),
        "run": {
            "horizons": result.horizons,
            "compute_or_gap": compute_or_gap,
            "include_policy": include_policy,
        },
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
    return doc


def to_json(model: Model, result: SweepResult, include_policy: bool = False) -> str:
    """Deterministic JSON. Keys sorted; node order sorted."""
    return json.dumps(
        to_document(model, result, include_policy=include_policy),
        indent=2,
        sort_keys=True,
    )


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
