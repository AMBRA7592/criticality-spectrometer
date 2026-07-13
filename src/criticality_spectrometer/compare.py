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

from .model import Model
from .cascade import functioning_nodes
from .outcome import count_outcome


def or_relax(model: Model) -> Model:
    """OR relaxation: set every dependency's logic to OR, preserving groups/IDs
    so group-targeted alternatives remain attached."""
    new_deps = {
        target: replace(dep, logic="OR")
        for target, dep in model.dependencies.items()
    }
    return replace(model, dependencies=new_deps)


def survival_gap(model: Model, node: str, taus: list[float]) -> list[int]:
    """S_OR - S_AND for one node across horizons."""
    relaxed = or_relax(model)
    row = []
    for tau in taus:
        s_and = count_outcome(model, functioning_nodes(model, {node}, tau), tau)
        s_or = count_outcome(relaxed, functioning_nodes(relaxed, {node}, tau), tau)
        row.append(s_or - s_and)
    return row
