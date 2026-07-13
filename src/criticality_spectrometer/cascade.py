"""
Deterministic cascade propagation with continuity semantics.

The spectrometer asks: after removing a node from an ALREADY-OPERATING system,
what continues to function? This is continuity, not startup feasibility. So we
start from the intact operational set (all present nodes functioning) and shrink
to the greatest surviving fixed point: iteratively remove any node whose
dependency is unsatisfied, until stable.

A node functions iff it is present and its dependency (if any) is satisfied.

A requirement group is satisfied iff:
  - a declared any_of member is functioning, OR
  - a targeted substitute applies: an alternative whose (target, requirement_id)
    identifies THIS group, whose activation_time <= tau, and whose replacement
    node is functioning.

Group targeting is by stable requirement id, so a substitute satisfies exactly
one group even if the same provider node appears in several groups.

Continuity vs cycles: a mutually-supporting cycle that is intact at start
remains functioning unless a removal breaks it. This is the correct continuity
reading (the cycle was already running). Startup feasibility is a separate
question, out of scope for the removal instrument.
"""

from __future__ import annotations

from .model import Model, Dependency, Alternative, RequirementGroup


def _active_substitutes(model: Model, tau: float) -> list[Alternative]:
    return [a for a in model.alternatives if a.activation_time <= tau]


def _group_satisfied(
    group: RequirementGroup,
    target: str,
    functioning: set[str],
    active_subs: list[Alternative],
) -> bool:
    if any(member in functioning for member in group.any_of):
        return True
    for alt in active_subs:
        if alt.target == target and alt.requirement_id == group.id:
            if alt.replacement in functioning:
                return True
    return False


def _dependency_satisfied(
    dep: Dependency,
    functioning: set[str],
    active_subs: list[Alternative],
) -> bool:
    if dep.logic == "AND":
        return all(_group_satisfied(g, dep.target, functioning, active_subs) for g in dep.requirements)
    return any(_group_satisfied(g, dep.target, functioning, active_subs) for g in dep.requirements)


def functioning_nodes(model: Model, removed: set[str], tau: float) -> set[str]:
    """Greatest surviving fixed point after removals at horizon tau (continuity)."""
    active_subs = _active_substitutes(model, tau)
    functioning = model.node_ids - removed

    changed = True
    max_iter = len(model.nodes) + 1
    iterations = 0
    while changed and iterations < max_iter:
        changed = False
        iterations += 1
        for nid in list(functioning):
            dep = model.dependencies.get(nid)
            if dep is None:
                continue
            if not _dependency_satisfied(dep, functioning, active_subs):
                functioning.discard(nid)
                changed = True

    return functioning
