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

One shared engine, two views. `functioning_nodes` returns only the final set.
`cascade_trace` runs the SAME engine and additionally records, per propagation
round, which nodes fell and every requirement group that was unsatisfied when
they fell. Each round evaluates every node against the functioning set frozen
at the START of that round (synchronous update), so round membership is a
property of the model, not of node declaration order: round k contains exactly
the nodes whose dependency first fails k rounds after the removal. The greatest
fixed point of a monotone shrink is unique regardless of update order, so the
final functioning set is identical to the previous (in-round) update schedule.
Rounds are propagation stages; they are not assertions of unique causality.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Model, Dependency, Alternative, RequirementGroup


@dataclass(frozen=True)
class PendingSubstitute:
    """A substitute targeting a group but not yet active at the swept tau."""

    replacement: str
    activation_time: float


@dataclass(frozen=True)
class UnsatisfiedGroup:
    """A requirement group that was unsatisfied when its target fell.

    `members` is the group's declared any_of, none of which functioned at that
    moment. `pending_substitutes` target this group but activate only after the
    swept tau. `dead_substitutes` were active, but their replacement node was
    itself not functioning.
    """

    id: str
    members: tuple[str, ...]
    pending_substitutes: tuple[PendingSubstitute, ...]
    dead_substitutes: tuple[str, ...]


@dataclass(frozen=True)
class FallenNode:
    """A node that fell in a cascade round, with every unsatisfied group."""

    node: str
    unsatisfied: tuple[UnsatisfiedGroup, ...]


@dataclass
class CascadeTrace:
    """Full cascade record: final set plus per-round falls.

    rounds[k] holds the nodes that fell in round k+1, evaluated against the
    functioning set frozen at the start of that round.
    """

    removed: frozenset[str]
    tau: float
    functioning: set[str]
    rounds: tuple[tuple[FallenNode, ...], ...]


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


def _unsatisfied_groups(
    model: Model,
    dep: Dependency,
    functioning: set[str],
    active_subs: list[Alternative],
    tau: float,
) -> tuple[UnsatisfiedGroup, ...]:
    """Every unsatisfied group of a falling node, with substitute status."""
    out = []
    for group in dep.requirements:
        if _group_satisfied(group, dep.target, functioning, active_subs):
            continue
        pending: list[PendingSubstitute] = []
        dead: list[str] = []
        for alt in model.alternatives:
            if alt.target != dep.target or alt.requirement_id != group.id:
                continue
            if alt.activation_time <= tau:
                # Active yet the group is unsatisfied: replacement is dead.
                dead.append(alt.replacement)
            else:
                pending.append(PendingSubstitute(alt.replacement, alt.activation_time))
        out.append(
            UnsatisfiedGroup(
                id=group.id,
                members=group.any_of,
                pending_substitutes=tuple(
                    sorted(pending, key=lambda p: (p.activation_time, p.replacement))
                ),
                dead_substitutes=tuple(sorted(dead)),
            )
        )
    return tuple(out)


def _cascade(
    model: Model,
    removed: set[str],
    tau: float,
    trace: bool,
) -> tuple[set[str], list[tuple[FallenNode, ...]]]:
    """The single cascade engine behind functioning_nodes and cascade_trace."""
    active_subs = _active_substitutes(model, tau)
    functioning = model.node_ids - removed
    rounds: list[tuple[FallenNode, ...]] = []

    # Every non-final round removes at least one node, so n+1 rounds suffice.
    for _ in range(len(model.nodes) + 1):
        fallen: list[str] = []
        for nid in model.nodes:  # deterministic model order
            if nid not in functioning:
                continue
            dep = model.dependencies.get(nid)
            if dep is None:
                continue
            # Evaluated against the set frozen at the start of this round.
            if not _dependency_satisfied(dep, functioning, active_subs):
                fallen.append(nid)
        if not fallen:
            break
        if trace:
            rounds.append(
                tuple(
                    FallenNode(
                        node=nid,
                        unsatisfied=_unsatisfied_groups(
                            model, model.dependencies[nid], functioning, active_subs, tau
                        ),
                    )
                    for nid in fallen
                )
            )
        functioning -= set(fallen)

    return functioning, rounds


def functioning_nodes(model: Model, removed: set[str], tau: float) -> set[str]:
    """Greatest surviving fixed point after removals at horizon tau (continuity)."""
    functioning, _ = _cascade(model, removed, tau, trace=False)
    return functioning


def cascade_trace(model: Model, removed: set[str], tau: float) -> CascadeTrace:
    """Same engine as functioning_nodes, additionally recording every round."""
    functioning, rounds = _cascade(model, removed, tau, trace=True)
    return CascadeTrace(
        removed=frozenset(removed),
        tau=float(tau),
        functioning=functioning,
        rounds=tuple(rounds),
    )


def rescuing_substitutes(model: Model, functioning: set[str], tau: float) -> list[Alternative]:
    """Active substitutes that satisfy a group with no functioning declared member.

    For each, the target and replacement are functioning and the identified
    group's declared any_of has no functioning member — so at this tau the
    substitute is what satisfies that group. For OR-logic targets the group may
    not be the one carrying the dependency; the definition is per-group, not a
    causality claim.
    """
    out = []
    for alt in _active_substitutes(model, tau):
        if alt.target not in functioning or alt.replacement not in functioning:
            continue
        dep = model.dependencies.get(alt.target)
        if dep is None:
            continue
        group = dep.group(alt.requirement_id)
        if group is None:
            continue
        if not any(member in functioning for member in group.any_of):
            out.append(alt)
    return sorted(
        out, key=lambda a: (a.target, a.requirement_id, a.replacement, a.activation_time)
    )
