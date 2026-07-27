"""Executable witnesses for the bounded formal properties in docs/method.md.

The tests connect the proof arguments to the implementation. They are not a
substitute for the proofs in docs/formal-properties.md.
"""

from pathlib import Path

import pytest

from criticality_spectrometer import (
    cascade_trace,
    count_outcome,
    default_horizons,
    functioning_nodes,
    load_model,
    or_relax,
    run_sweep,
    served_sink_set,
)


ROOT = Path(__file__).resolve().parent.parent
MODEL_PATHS = (
    ROOT / "examples" / "canonical" / "model.json",
    ROOT / "examples" / "tutorial" / "model.json",
    ROOT / "examples" / "ai_compute" / "model_topology.json",
    ROOT / "examples" / "ai_compute" / "model_frontier_fab_only.json",
    ROOT / "examples" / "ai_compute" / "model_frontier_stack.json",
    ROOT / "examples" / "kubernetes" / "model_declared.json",
    ROOT / "examples" / "kubernetes" / "model.json",
)


def _chain_model(order):
    return load_model({
        "version": "0.1",
        "nodes": [{"id": node} for node in order],
        "dependencies": [
            {
                "target": "a",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["root"]}],
            },
            {
                "target": "b",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["a"]}],
            },
            {
                "target": "c",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["b"]}],
            },
            {
                "target": "sink",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["c"]}],
            },
        ],
        "outcome": {
            "type": "served_sinks",
            "sources": ["root"],
            "sinks": ["sink"],
        },
    })


def _branch_model(order):
    return load_model({
        "version": "0.1",
        "nodes": [{"id": node} for node in order],
        "dependencies": [
            {
                "target": "left",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["root"]}],
            },
            {
                "target": "right",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["root"]}],
            },
            {
                "target": "join",
                "logic": "AND",
                "requirements": [
                    {"id": "left", "any_of": ["left"]},
                    {"id": "right", "any_of": ["right"]},
                ],
            },
            {
                "target": "sink",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["join"]}],
            },
        ],
        "outcome": {
            "type": "served_sinks",
            "sources": ["root"],
            "sinks": ["sink"],
        },
    })


def _activation_model():
    return load_model({
        "version": "0.1",
        "nodes": [
            {"id": "source"},
            {"id": "primary"},
            {"id": "backup"},
            {"id": "gate"},
            {"id": "sink"},
        ],
        "dependencies": [
            {
                "target": "primary",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["source"]}],
            },
            {
                "target": "backup",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["source"]}],
            },
            {
                "target": "gate",
                "logic": "AND",
                "requirements": [{"id": "capability", "any_of": ["primary"]}],
            },
            {
                "target": "sink",
                "logic": "AND",
                "requirements": [{"id": "input", "any_of": ["gate"]}],
            },
        ],
        "alternatives": [{
            "target": "gate",
            "requirement_id": "capability",
            "replacement": "backup",
            "activation_time": 5,
        }],
        "outcome": {
            "type": "served_sinks",
            "sources": ["source"],
            "sinks": ["sink"],
        },
    })


def test_finite_termination_bound_is_attainable():
    model = _chain_model(["root", "a", "b", "c", "sink"])
    trace = cascade_trace(model, {"root"}, 0)

    assert len(trace.rounds) == len(model.nodes) - 1
    assert all(round_ for round_ in trace.rounds)
    assert [fallen.node for round_ in trace.rounds for fallen in round_] == [
        "a", "b", "c", "sink"
    ]


def test_round_membership_and_fixed_point_ignore_declaration_order():
    forward = _branch_model(["root", "left", "right", "join", "sink"])
    reverse = _branch_model(["sink", "join", "right", "left", "root"])

    traces = [cascade_trace(model, {"root"}, 0) for model in (forward, reverse)]
    round_memberships = [
        [frozenset(fallen.node for fallen in round_) for round_ in trace.rounds]
        for trace in traces
    ]

    assert round_memberships[0] == round_memberships[1]
    assert traces[0].functioning == traces[1].functioning


def test_horizon_monotonicity_and_activation_breakpoint():
    model = _activation_model()
    before = [0, 1, 4.999]
    after = [5, 5.001, 100]

    before_sets = [functioning_nodes(model, {"primary"}, tau) for tau in before]
    after_sets = [functioning_nodes(model, {"primary"}, tau) for tau in after]

    assert all(nodes == before_sets[0] for nodes in before_sets)
    assert all(nodes == after_sets[0] for nodes in after_sets)
    assert before_sets[0] < after_sets[0]

    result = run_sweep(model, before + after)
    assert result.curves["primary"].impact == [1, 1, 1, 0, 0, 0]


@pytest.mark.parametrize("path", MODEL_PATHS, ids=lambda path: path.parent.name + "/" + path.name)
def test_shipped_models_obey_horizon_and_or_relaxation_bounds(path):
    model = load_model(str(path))
    horizons = model.horizons or default_horizons(model)
    relaxed = or_relax(model)

    for removed in model.nodes:
        previous = None
        for tau in horizons:
            declared = functioning_nodes(model, {removed}, tau)
            relaxed_nodes = functioning_nodes(relaxed, {removed}, tau)

            if previous is not None:
                assert previous <= declared
            previous = declared

            assert declared <= relaxed_nodes
            assert served_sink_set(model, declared, tau) <= served_sink_set(
                relaxed, relaxed_nodes, tau
            )
            assert count_outcome(model, declared, tau) <= count_outcome(
                relaxed, relaxed_nodes, tau
            )
