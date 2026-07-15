"""Tests for the shared cascade trace and the explain reports.

The load-bearing property: cascade_trace and functioning_nodes are two views of
ONE engine, so their final sets are identical by construction — asserted here
across models, removals, and horizons anyway, per the approved design. Rounds
are synchronous propagation stages and therefore invariant under node
declaration order.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema
import pytest

from criticality_spectrometer import (
    load_model,
    functioning_nodes,
    cascade_trace,
    run_sweep,
    explain_document,
    explain_json,
    explain_text,
    ModelError,
    BaselineError,
    EXPLAIN_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = str(ROOT / "examples" / "canonical" / "model.json")
FRONTIER = str(ROOT / "examples" / "ai_compute" / "model_frontier_stack.json")


@pytest.fixture(scope="module")
def canonical():
    return load_model(CANONICAL)


@pytest.fixture(scope="module")
def frontier():
    return load_model(FRONTIER)


# ---------- one engine, two views ----------

def test_trace_and_functioning_nodes_agree_canonical(canonical):
    for node in canonical.nodes:
        for tau in (0, 12, 24):
            trace = cascade_trace(canonical, {node}, tau)
            assert trace.functioning == functioning_nodes(canonical, {node}, tau)


def test_trace_and_functioning_nodes_agree_frontier(frontier):
    for node in frontier.nodes:
        for tau in (0, 12, 24):
            trace = cascade_trace(frontier, {node}, tau)
            assert trace.functioning == functioning_nodes(frontier, {node}, tau)


def test_trace_rounds_partition_the_fallen(canonical):
    trace = cascade_trace(canonical, {"bottleneck"}, 0)
    fallen = [f.node for fell in trace.rounds for f in fell]
    assert len(fallen) == len(set(fallen))
    expected_fallen = canonical.node_ids - {"bottleneck"} - trace.functioning
    assert set(fallen) == expected_fallen


# ---------- rounds are propagation stages, not declaration-order artifacts ----------

def _chain_model(order):
    return load_model({
        "version": "0.1",
        "nodes": [{"id": n} for n in order],
        "dependencies": [
            {"target": "a", "logic": "AND", "requirements": [{"id": "in", "any_of": ["root"]}]},
            {"target": "b", "logic": "AND", "requirements": [{"id": "in", "any_of": ["a"]}]},
            {"target": "c", "logic": "AND", "requirements": [{"id": "in", "any_of": ["b"]}]},
        ],
        "outcome": {"type": "served_sinks", "sources": ["root"], "sinks": ["c"]},
    })


def test_chain_rounds_are_declaration_order_invariant():
    forward = _chain_model(["root", "a", "b", "c"])
    reverse = _chain_model(["c", "b", "a", "root"])
    for model in (forward, reverse):
        trace = cascade_trace(model, {"root"}, 0)
        rounds = [[f.node for f in fell] for fell in trace.rounds]
        assert rounds == [["a"], ["b"], ["c"]], rounds


# ---------- canonical explanations, exact ----------

def test_bottleneck_explanation_exact(canonical):
    doc = explain_document(canonical, "bottleneck", [0, 12, 24])
    assert doc["impact"] == [1, 0, 0]
    assert doc["shape"] == "fully_adaptable"
    assert doc["baseline"] == 1

    tau0, tau12, tau24 = doc["horizons"]

    assert tau0["lost_sinks"] == ["sink"]
    assert tau0["restored_sinks"] == []
    assert [(c["round"], [n["node"] for n in c["nodes"]]) for c in tau0["casualties"]] == [
        (1, ["assembler"]),
        (2, ["sink"]),
    ]
    assembler_groups = tau0["casualties"][0]["nodes"][0]["unsatisfied_groups"]
    assert assembler_groups == [{
        "id": "stage_bottleneck",
        "members": ["bottleneck"],
        "pending_substitutes": [{"replacement": "backup", "activation_time": 12.0}],
        "dead_substitutes": [],
    }]
    assert tau0["rescuing_substitutes"] == []

    assert tau12["impact"] == 0
    assert tau12["lost_sinks"] == []
    assert tau12["restored_sinks"] == ["sink"]
    assert tau12["casualties"] == []
    assert [s["replacement"] for s in tau12["rescuing_substitutes"]] == ["backup"]

    assert tau24["restored_sinks"] == []


def test_none_shape_explanation_reports_nothing_invented(canonical):
    doc = explain_document(canonical, "redundant_1", [0, 12, 24])
    assert doc["impact"] == [0, 0, 0]
    assert doc["shape"] == "none"
    for block in doc["horizons"]:
        assert block["lost_sinks"] == []
        assert block["casualties"] == []


def test_explain_impact_matches_run_sweep_everywhere(canonical):
    sweep = run_sweep(canonical, [0, 12, 24])
    for node in canonical.nodes:
        doc = explain_document(canonical, node, [0, 12, 24])
        assert doc["impact"] == sweep.curves[node].impact, node
        assert doc["shape"] == sweep.curves[node].shape, node


# ---------- substitute status in the trace ----------

def test_dead_substitute_recorded_when_replacement_removed(canonical):
    trace = cascade_trace(canonical, {"bottleneck", "backup"}, 12)
    assert "assembler" not in trace.functioning
    fallen = {f.node: f for fell in trace.rounds for f in fell}
    groups = {g.id: g for g in fallen["assembler"].unsatisfied}
    assert groups["stage_bottleneck"].dead_substitutes == ("backup",)
    assert groups["stage_bottleneck"].pending_substitutes == ()


# ---------- AI case spot checks ----------

def test_tsmc_explanation_on_stack(frontier):
    doc = explain_document(frontier, "tsmc_advanced", [0, 12, 24])
    assert doc["impact"] == [4, 0, 0]
    tau0, tau12, _ = doc["horizons"]
    assert len(tau0["lost_sinks"]) == 4
    round1 = tau0["casualties"][0]
    assert round1["round"] == 1
    cowos = [n for n in round1["nodes"] if n["node"] == "cowos"]
    assert cowos, "cowos must fall in round one"
    fab_input = [g for g in cowos[0]["unsatisfied_groups"] if g["id"] == "fab_input"]
    assert fab_input
    pending = {p["replacement"] for p in fab_input[0]["pending_substitutes"]}
    assert pending == {"samsung_foundry", "intel_foundry"}
    assert len(tau12["restored_sinks"]) == 4
    rescuers = {(s["replacement"], s["target"]) for s in tau12["rescuing_substitutes"]}
    assert ("samsung_foundry", "cowos") in rescuers
    assert ("intel_foundry", "cowos") in rescuers


def test_persistent_node_never_restores(frontier):
    doc = explain_document(frontier, "asml_euv", [0, 12, 24])
    assert doc["shape"] == "persistent"
    for block in doc["horizons"]:
        assert block["restored_sinks"] == []
        assert len(block["lost_sinks"]) == 4


def test_casualties_without_impact_are_reported(frontier):
    # Removing germanium fells optical_xcvr yet de-serves no sink: the report
    # must state both facts rather than equate casualties with impact.
    doc = explain_document(frontier, "germanium", [0, 12, 24])
    assert doc["impact"] == [0, 0, 0]
    tau0 = doc["horizons"][0]
    assert tau0["lost_sinks"] == []
    fallen = [n["node"] for c in tau0["casualties"] for n in c["nodes"]]
    assert "optical_xcvr" in fallen


# ---------- document contract ----------

def test_explain_document_validates_against_schema(canonical, frontier):
    schema = json.loads((ROOT / "schema" / "explain.schema.json").read_text())
    for model, node in ((canonical, "bottleneck"), (canonical, "redundant_1"),
                        (frontier, "tsmc_advanced"), (frontier, "germanium")):
        jsonschema.validate(explain_document(model, node, [0, 12, 24]), schema)


def test_explain_schema_version_matches_document(canonical):
    doc = explain_document(canonical, "bottleneck", [0])
    assert doc["explain_schema_version"] == EXPLAIN_SCHEMA_VERSION


def test_explain_is_deterministic(canonical):
    a = explain_json(canonical, "bottleneck", [0, 12, 24])
    b = explain_json(canonical, "bottleneck", [0, 12, 24])
    assert a == b
    rendered = explain_text(explain_document(canonical, "bottleneck", [0, 12, 24]))
    assert rendered == explain_text(explain_document(canonical, "bottleneck", [0, 12, 24]))


def test_explain_unknown_node_rejected(canonical):
    with pytest.raises(ModelError, match="not a declared node"):
        explain_document(canonical, "ghost", [0])


def test_explain_zero_baseline_rejected():
    m = load_model({
        "version": "0.1",
        "nodes": [{"id": "src"}, {"id": "sink"}, {"id": "dead"}],
        "dependencies": [
            {"target": "dead", "logic": "AND", "requirements": [{"id": "imposs", "any_of": ["sink"]}]},
            {"target": "sink", "logic": "AND", "requirements": [{"id": "fin", "any_of": ["dead"]}]},
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink"]},
    })
    with pytest.raises(BaselineError):
        explain_document(m, "src", [0])
