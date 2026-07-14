"""
AND/OR comparison — the redundancy-illusion measure.

For a model, compare survival under the true AND/OR dependencies against survival
under the OR-relaxed model (every dependency's logic set to OR, groups and IDs
preserved so targeted alternatives stay attached).

    or_survival_gap_v(tau) = S_OR(tau) - S_AND(tau)   (>= 0)

A positive gap is the redundancy illusion: under naive OR reachability the node
looks substitutable, but under the true requirements it is not.
"""

from __future__ import annotations

from dataclasses import replace

from .cascade import functioning_nodes
from .model import Model
from .outcome import count_outcome


def or_relax(model: Model) -> Model:
    """OR relaxation: set every dependency's logic to OR, preserving groups/IDs
    so group-targeted alternatives remain attached."""
    new_deps = {
        target: replace(dep, logic="OR")
        for target, dep in model.dependencies.items()
    }
    return replace(model, dependencies=new_deps)


def survival_gap(
    model: Model,
    node: str,
    taus: list[float],
    *,
    and_survival: list[int] | None = None,
    relaxed_model: Model | None = None,
) -> list[int]:
    """S_OR - S_AND for one node across horizons.

    Callers that already computed AND-aware survival may pass it to avoid a
    duplicate cascade. A shared relaxed model similarly avoids rebuilding the
    same OR relaxation for every node.
    """
    relaxed = relaxed_model or or_relax(model)
    if and_survival is None:
        and_survival = [
            count_outcome(model, functioning_nodes(model, {node}, tau), tau)
            for tau in taus
        ]
    if len(and_survival) != len(taus):
        raise ValueError("and_survival must have one value per horizon")
    row = []
    for tau, s_and in zip(taus, and_survival):
        s_or = count_outcome(relaxed, functioning_nodes(relaxed, {node}, tau), tau)
        row.append(s_or - s_and)
    return row
