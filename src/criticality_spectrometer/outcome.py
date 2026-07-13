"""
Outcome measurement over the functioning subgraph.

served_sinks (default): number of sinks reachable from at least one source
through functioning nodes. A sink served by two sources still counts once, so
removing one redundant source does not register spurious impact.

ordered_served_sinks: a sink counts if some source reaches it via a path passing
each waypoint group in order.

Edges are induced from the model: input -> target when input appears in a
requirement group's any_of, plus activated group-targeted alternatives
(replacement -> target). No domain-specific edge list.
"""

from __future__ import annotations

from .model import Model


def induced_edges(model: Model, tau: float) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {nid: set() for nid in model.nodes}
    for target, dep in model.dependencies.items():
        for group in dep.requirements:
            for member in group.any_of:
                adj[member].add(target)
    for alt in model.alternatives:
        if alt.activation_time <= tau:
            adj[alt.replacement].add(alt.target)
    return adj


def _reachable_from(adj: dict[str, set[str]], start: str, allowed: set[str]) -> set[str]:
    if start not in allowed:
        return set()
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for v in adj.get(u, ()):
            if v in allowed and v not in seen:
                seen.add(v)
                stack.append(v)
    return seen


def _has_ordered_path(adj, source, sink, waypoints, allowed) -> bool:
    if source not in allowed or sink not in allowed:
        return False
    frontier = {source}
    for group in waypoints:
        reach: set[str] = set()
        for f in frontier:
            reach |= _reachable_from(adj, f, allowed)
        hits = reach & set(group) & allowed
        if not hits:
            return False
        frontier = hits
    reach_final: set[str] = set()
    for f in frontier:
        reach_final |= _reachable_from(adj, f, allowed)
    return sink in reach_final


def count_outcome(model: Model, functioning: set[str], tau: float) -> int:
    """Count served sinks given functioning nodes at horizon tau."""
    adj = induced_edges(model, tau)
    allowed = functioning
    o = model.outcome

    served = 0
    for sink in o.sinks:
        if sink not in allowed:
            continue
        if o.type == "served_sinks":
            reached = False
            for s in o.sources:
                if s in allowed and sink in _reachable_from(adj, s, allowed):
                    reached = True
                    break
            if reached:
                served += 1
        else:  # ordered_served_sinks
            served_flag = False
            for s in o.sources:
                if s in allowed and _has_ordered_path(adj, s, sink, o.waypoints, allowed):
                    served_flag = True
                    break
            if served_flag:
                served += 1
    return served


def baseline_outcome(model: Model, tau: float) -> int:
    from .cascade import functioning_nodes
    fn = functioning_nodes(model, removed=set(), tau=tau)
    return count_outcome(model, fn, tau)
