"""
Curve explanation.

`explain` turns one node's impact curve into an inspectable record: per horizon,
the measured mission impact and lost sinks, casualties grouped by cascade round,
every unsatisfied requirement group for each casualty, the active substitutes,
the substitutes that actually satisfy a group that would otherwise fail, and the
sinks restored relative to the previous horizon.

Everything here is derived from the shared engine: cascade rounds come from
`cascade_trace` (the same algorithm as `functioning_nodes`), served sinks from
`served_sink_set` (the same implementation `count_outcome` counts), horizons and
baseline checks from the sweep. This module evaluates no dependency logic of
its own.

Rounds are propagation stages — "direct" means a dependency that failed in
round one, "downstream" means later rounds. They are not assertions of unique
causality; every unsatisfied group is reported, not a chosen root cause.
"""

from __future__ import annotations

import json

from .cascade import cascade_trace, functioning_nodes, rescuing_substitutes
from .classify import classify
from .model import Model, ModelError, Alternative
from .outcome import served_sink_set
from .report import instrument_block, model_block
from .sweep import default_horizons, _check_constant_baseline


EXPLAIN_SCHEMA_VERSION = "0.1"


def _substitute_entry(alt: Alternative) -> dict:
    return {
        "target": alt.target,
        "requirement_id": alt.requirement_id,
        "replacement": alt.replacement,
        "activation_time": alt.activation_time,
    }


def explain_document(model: Model, node: str, horizons: list[float] | None = None) -> dict:
    """Build a deterministic, self-identifying explanation document."""
    if node not in model.nodes:
        raise ModelError(f"explain target {node!r} is not a declared node.")

    taus = horizons if horizons is not None else (model.horizons or default_horizons(model))
    if not taus:
        taus = default_horizons(model)
    taus = sorted(set(taus))

    baseline = _check_constant_baseline(model, taus)

    per_horizon = []
    impact_curve: list[int] = []
    previous_lost: frozenset[str] | None = None
    for tau in taus:
        # Baseline served set at the same tau; under a valid constant baseline
        # these sets are nested and equal, but diffing per-tau assumes nothing.
        intact = served_sink_set(model, functioning_nodes(model, set(), tau), tau)
        trace = cascade_trace(model, {node}, tau)
        served = served_sink_set(model, trace.functioning, tau)
        impact = baseline - len(served)
        impact_curve.append(impact)

        lost = frozenset(intact - served)
        restored = sorted(previous_lost - lost) if previous_lost is not None else []
        previous_lost = lost

        casualties = []
        for round_index, fallen in enumerate(trace.rounds, start=1):
            casualties.append(
                {
                    "round": round_index,
                    "nodes": [
                        {
                            "node": f.node,
                            "unsatisfied_groups": [
                                {
                                    "id": g.id,
                                    "members": list(g.members),
                                    "pending_substitutes": [
                                        {
                                            "replacement": p.replacement,
                                            "activation_time": p.activation_time,
                                        }
                                        for p in g.pending_substitutes
                                    ],
                                    "dead_substitutes": list(g.dead_substitutes),
                                }
                                for g in f.unsatisfied
                            ],
                        }
                        for f in fallen
                    ],
                }
            )

        active = sorted(
            (a for a in model.alternatives if a.activation_time <= tau),
            key=lambda a: (a.target, a.requirement_id, a.replacement, a.activation_time),
        )
        per_horizon.append(
            {
                "tau": tau,
                "impact": impact,
                "lost_sinks": sorted(lost),
                "restored_sinks": restored,
                "casualties": casualties,
                "active_substitutes": [_substitute_entry(a) for a in active],
                "rescuing_substitutes": [
                    _substitute_entry(a)
                    for a in rescuing_substitutes(model, trace.functioning, tau)
                ],
            }
        )

    return {
        "explain_schema_version": EXPLAIN_SCHEMA_VERSION,
        "instrument": instrument_block(),
        "model": model_block(model),
        "run": {"node": node, "horizons": list(taus)},
        "baseline": baseline,
        "impact": impact_curve,
        "shape": classify(impact_curve),
        "horizons": per_horizon,
    }


def explain_json(model: Model, node: str, horizons: list[float] | None = None) -> str:
    """Deterministic JSON explanation. Keys sorted."""
    return json.dumps(explain_document(model, node, horizons), indent=2, sort_keys=True)


def _render_group(group: dict) -> str:
    parts = [f"members: {', '.join(group['members'])}"]
    if group["pending_substitutes"]:
        parts.append(
            "pending: "
            + ", ".join(
                f"{p['replacement']}@{p['activation_time']:g}"
                for p in group["pending_substitutes"]
            )
        )
    if group["dead_substitutes"]:
        parts.append("active substitute dead: " + ", ".join(group["dead_substitutes"]))
    return f"{group['id']} ({'; '.join(parts)})"


def _render_substitute(entry: dict) -> str:
    return (
        f"{entry['replacement']} -> {entry['target']}.{entry['requirement_id']}"
        f" @{entry['activation_time']:g}"
    )


def explain_text(document: dict) -> str:
    """Compact human-readable rendering of an explanation document."""
    model = document["model"]
    run = document["run"]
    lines = [
        f"Criticality Spectrometer — explain {run['node']!r} in "
        f"{model['name'] or 'model'} (v{model['version']})",
        f"impact {document['impact']}   shape {document['shape']}   "
        f"baseline {document['baseline']}",
    ]
    for block in document["horizons"]:
        lines.append("")
        header = f"tau={block['tau']:g}   impact {block['impact']}"
        header += "   lost sinks: " + (", ".join(block["lost_sinks"]) or "none")
        if block["restored_sinks"]:
            header += "   restored: " + ", ".join(block["restored_sinks"])
        lines.append(header)
        if block["casualties"]:
            for round_block in block["casualties"]:
                for fallen in round_block["nodes"]:
                    groups = "; ".join(
                        _render_group(g) for g in fallen["unsatisfied_groups"]
                    )
                    lines.append(
                        f"  round {round_block['round']}: {fallen['node']}"
                        f" — unsatisfied: {groups}"
                    )
        else:
            lines.append("  no casualties")
        active = block["active_substitutes"]
        rescuing = block["rescuing_substitutes"]
        lines.append(
            "  active substitutes: "
            + (", ".join(_render_substitute(a) for a in active) or "none")
        )
        lines.append(
            "  rescuing substitutes: "
            + (", ".join(_render_substitute(a) for a in rescuing) or "none")
        )
    return "\n".join(lines)
