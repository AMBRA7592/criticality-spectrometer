"""
Semantic tests: canonical fixture plus standalone in-memory models.
Expected values are hand-verified from structure, with exact assertions.
"""

import os
import pytest

from criticality_spectrometer import (
    load_model, functioning_nodes, count_outcome, baseline_outcome,
    run_sweep, default_horizons, ModelError, ModelWarning, BaselineError,
    or_relax,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "examples", "canonical", "model.json")


@pytest.fixture
def model():
    return load_model(FIXTURE)


# ---------- canonical, exact ----------

def test_loads(model):
    assert model.name == "canonical"
    assert len(model.nodes) == 7


def test_baseline_constant_one(model):
    r = run_sweep(model, [0, 12, 24])
    assert r.baseline == 1


def test_default_horizons(model):
    assert default_horizons(model) == [0.0, 12.0]


def test_bottleneck_fully_adaptable_exact(model):
    r = run_sweep(model, [0, 12, 24])
    c = r.curves["bottleneck"]
    assert c.impact == [1, 0, 0]
    assert c.shape == "fully_adaptable"


def test_redundant_none_exact(model):
    r = run_sweep(model, [0, 12, 24])
    assert r.curves["redundant_1"].impact == [0, 0, 0]
    assert r.curves["redundant_1"].shape == "none"


def test_persistent_nodes_exact(model):
    r = run_sweep(model, [0, 12, 24])
    for n in ("src", "assembler", "sink"):
        assert r.curves[n].impact == [1, 1, 1]
        assert r.curves[n].shape == "persistent"


# ---------- served_sinks, not pair count ----------

def test_served_sinks_ignores_redundant_source():
    # Two sources both feed the sink. Removing one leaves the sink served.
    d = {
        "version": "0.1",
        "nodes": [{"id": "s1"}, {"id": "s2"}, {"id": "sink"}],
        "dependencies": [
            {"target": "sink", "logic": "OR", "requirements": [
                {"id": "in", "any_of": ["s1", "s2"]}
            ]}
        ],
        "outcome": {"type": "served_sinks", "sources": ["s1", "s2"], "sinks": ["sink"]},
    }
    m = load_model(d)
    r = run_sweep(m, [0])
    assert r.baseline == 1
    # Removing either source: sink still served by the other -> impact 0.
    assert r.curves["s1"].impact == [0]
    assert r.curves["s2"].impact == [0]


def test_served_sinks_counts_duplicate_sink_id_once():
    # Outcome semantics are set-based: repeating a sink id in model data must
    # not turn one served mission endpoint into two units of baseline service.
    d = {
        "version": "0.1",
        "nodes": [{"id": "src"}, {"id": "sink"}],
        "dependencies": [
            {"target": "sink", "logic": "AND", "requirements": [
                {"id": "in", "any_of": ["src"]}
            ]}
        ],
        "outcome": {
            "type": "served_sinks",
            "sources": ["src"],
            "sinks": ["sink", "sink"],
        },
    }
    m = load_model(d)
    assert baseline_outcome(m, 0) == 1
    assert run_sweep(m, [0]).baseline == 1


# ---------- group targeting isolation ----------

def test_substitute_covers_only_its_group():
    # provider appears in two groups of assembler. A substitute for group A must
    # NOT rescue group B.
    d = {
        "version": "0.1",
        "nodes": [
            {"id": "src"}, {"id": "provider"}, {"id": "other"},
            {"id": "backup"}, {"id": "assembler"}, {"id": "sink"},
        ],
        "dependencies": [
            {"target": "provider", "logic": "AND", "requirements": [{"id": "f", "any_of": ["src"]}]},
            {"target": "other", "logic": "AND", "requirements": [{"id": "f", "any_of": ["src"]}]},
            {"target": "backup", "logic": "AND", "requirements": [{"id": "f", "any_of": ["src"]}]},
            {"target": "assembler", "logic": "AND", "requirements": [
                {"id": "grpA", "any_of": ["provider"]},
                {"id": "grpB", "any_of": ["provider", "other"]}
            ]},
            {"target": "sink", "logic": "AND", "requirements": [{"id": "fin", "any_of": ["assembler"]}]},
        ],
        "alternatives": [
            {"target": "assembler", "requirement_id": "grpA", "replacement": "backup", "activation_time": 5}
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink"]},
    }
    m = load_model(d)
    # Remove provider. grpA covered by backup at tau>=5. grpB needs provider OR
    # other; other is alive, so grpB is satisfied by 'other'. So sink served at tau>=5.
    fn5 = functioning_nodes(m, {"provider"}, 5)
    assert "assembler" in fn5
    # Now remove BOTH provider and other. grpB has no live member and no substitute
    # (backup only targets grpA). Assembler must die even at tau>=5.
    fn5b = functioning_nodes(m, {"provider", "other"}, 5)
    assert "assembler" not in fn5b


# ---------- substitute needs replacement functioning ----------

def test_substitute_needs_replacement_alive(model):
    fn = functioning_nodes(model, {"bottleneck", "backup"}, 12)
    assert "assembler" not in fn


# ---------- monotonicity holds under constant baseline ----------

def test_impact_monotone_nonincreasing(model):
    r = run_sweep(model, [0, 12, 24])
    for node, c in r.curves.items():
        for i in range(len(c.impact) - 1):
            assert c.impact[i] >= c.impact[i + 1]


def test_duplicate_horizons_are_deduplicated(model):
    result = run_sweep(model, [12, 0, 12, 24, 0])
    assert result.horizons == [0, 12, 24]
    assert result.curves["bottleneck"].horizons == [0, 12, 24]


# ---------- AND survival <= OR survival ----------

def test_and_survival_le_or(model):
    relaxed = or_relax(model)
    for node in model.nodes:
        for tau in (0, 12, 24):
            s_and = count_outcome(model, functioning_nodes(model, {node}, tau), tau)
            s_or = count_outcome(relaxed, functioning_nodes(relaxed, {node}, tau), tau)
            assert s_and <= s_or


def test_or_survival_gap_at_bottleneck(model):
    r = run_sweep(model, [0, 12, 24])
    assert r.or_survival_gap["bottleneck"] == [1, 0, 0]


# ---------- non-constant baseline is rejected ----------

def test_nonconstant_baseline_rejected():
    # Construct a model whose INTACT baseline changes 1 -> 2 across horizons.
    # sink_b is only served once an alternative activates at tau=10 (its sole
    # requirement group has no live member at tau=0, but the replacement feeds
    # it at tau>=10). Intact served_sinks: {sink_a} at tau=0, {sink_a, sink_b}
    # at tau=10. That is a non-constant intact baseline and must raise.
    d = {
        "version": "0.1",
        "nodes": [
            {"id": "src"}, {"id": "sink_a"},
            {"id": "dormant"}, {"id": "waker"}, {"id": "sink_b"},
        ],
        "dependencies": [
            {"target": "sink_a", "logic": "AND", "requirements": [{"id": "a", "any_of": ["src"]}]},
            {"target": "waker", "logic": "AND", "requirements": [{"id": "w", "any_of": ["src"]}]},
            # sink_b needs 'dormant', which is never fed -> dead at tau=0.
            {"target": "dormant", "logic": "AND", "requirements": [{"id": "d", "any_of": ["sink_b"]}]},
            {"target": "sink_b", "logic": "AND", "requirements": [{"id": "b", "any_of": ["dormant"]}]},
        ],
        # At tau>=10, 'waker' can satisfy sink_b's group 'b', adding a served sink.
        "alternatives": [
            {"target": "sink_b", "requirement_id": "b", "replacement": "waker", "activation_time": 10}
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink_a", "sink_b"]},
    }
    m = load_model(d)
    with pytest.raises(BaselineError):
        run_sweep(m, [0, 10])


def test_or_relaxation_preserves_alternatives():
    # P1 regression: OR relaxation must keep group-targeted alternatives attached.
    # Here a targeted alternative is the ONLY reason the AND-aware model survives
    # after activation. The OR-relaxed model must preserve that alternative, so
    # the survival gap can never be negative.
    d = {
        "version": "0.1",
        "nodes": [
            {"id": "src"}, {"id": "primary"}, {"id": "backup"},
            {"id": "gate"}, {"id": "sink"},
        ],
        "dependencies": [
            {"target": "primary", "logic": "AND", "requirements": [{"id": "f", "any_of": ["src"]}]},
            {"target": "backup", "logic": "AND", "requirements": [{"id": "f", "any_of": ["src"]}]},
            {"target": "gate", "logic": "AND", "requirements": [{"id": "only", "any_of": ["primary"]}]},
            {"target": "sink", "logic": "AND", "requirements": [{"id": "fin", "any_of": ["gate"]}]},
        ],
        "alternatives": [
            {"target": "gate", "requirement_id": "only", "replacement": "backup", "activation_time": 6}
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink"]},
    }
    m = load_model(d)
    r = run_sweep(m, [0, 6])
    # Removing primary: at tau=0 gate dies (no backup yet) -> impact 1;
    # at tau=6 backup covers gate's 'only' group -> impact 0.
    assert r.curves["primary"].impact == [1, 0]
    # Survival gap must be >= 0 at every horizon (no detached alternative).
    for node, row in r.or_survival_gap.items():
        for g in row:
            assert g >= 0, f"negative survival gap at {node}: {row}"


def test_zero_baseline_rejected():
    d = {
        "version": "0.1",
        "nodes": [{"id": "src"}, {"id": "sink"}, {"id": "dead"}],
        "dependencies": [
            {"target": "dead", "logic": "AND", "requirements": [{"id": "imposs", "any_of": ["sink"]}]},
            {"target": "sink", "logic": "AND", "requirements": [{"id": "fin", "any_of": ["dead"]}]},
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink"]},
    }
    m = load_model(d)
    with pytest.raises(BaselineError):
        run_sweep(m, [0])


# ---------- validation ----------

def _valid():
    return {
        "version": "0.1",
        "nodes": [{"id": "a"}, {"id": "b"}],
        "dependencies": [{"target": "b", "logic": "AND", "requirements": [{"id": "g", "any_of": ["a"]}]}],
        "outcome": {"type": "served_sinks", "sources": ["a"], "sinks": ["b"]},
    }


def test_reject_unknown_reference():
    d = _valid()
    d["dependencies"][0]["requirements"][0]["any_of"] = ["ghost"]
    with pytest.raises(ModelError):
        load_model(d)


def test_reject_duplicate_ids():
    d = _valid()
    d["nodes"].append({"id": "a"})
    with pytest.raises(ModelError):
        load_model(d)


def test_reject_negative_activation_time():
    d = _valid()
    d["nodes"].append({"id": "c"})
    d["alternatives"] = [{"target": "b", "requirement_id": "g", "replacement": "c", "activation_time": -1}]
    with pytest.raises(ModelError):
        load_model(d)


def test_reject_unknown_requirement_id():
    d = _valid()
    d["nodes"].append({"id": "c"})
    d["alternatives"] = [{"target": "b", "requirement_id": "nonexistent", "replacement": "c", "activation_time": 1}]
    with pytest.raises(ModelError):
        load_model(d)


def test_reject_unexpected_top_level_property():
    d = _valid()
    d["surprise"] = 42
    with pytest.raises(ModelError):
        load_model(d)


def test_reject_negative_horizon():
    d = _valid()
    d["horizons"] = [-3]
    with pytest.raises(ModelError):
        load_model(d)


def test_reject_direct_self_requirement():
    d = _valid()
    d["dependencies"][0]["requirements"][0]["any_of"] = ["b"]
    with pytest.raises(ModelError, match="self-satisfaction"):
        load_model(d)


def test_reject_direct_self_alternative():
    d = _valid()
    d["alternatives"] = [
        {
            "target": "b",
            "requirement_id": "g",
            "replacement": "b",
            "activation_time": 1,
        }
    ]
    with pytest.raises(ModelError, match="self-satisfaction"):
        load_model(d)


def test_source_dependency_warns_but_loads():
    d = _valid()
    d["dependencies"].append(
        {
            "target": "a",
            "logic": "AND",
            "requirements": [{"id": "upstream", "any_of": ["b"]}],
        }
    )
    with pytest.warns(ModelWarning, match="reachability starting points"):
        model = load_model(d)
    assert "a" in model.dependencies


# ---------- continuity semantics for cycles ----------

def test_intact_cycle_continues():
    # a<->b mutual, both fed by src externally too. Intact: both run. This tests
    # continuity: an already-running mutually-supporting pair keeps running.
    d = {
        "version": "0.1",
        "nodes": [{"id": "src"}, {"id": "a"}, {"id": "b"}, {"id": "sink"}],
        "dependencies": [
            {"target": "a", "logic": "OR", "requirements": [{"id": "in", "any_of": ["src", "b"]}]},
            {"target": "b", "logic": "OR", "requirements": [{"id": "in", "any_of": ["src", "a"]}]},
            {"target": "sink", "logic": "AND", "requirements": [{"id": "fin", "any_of": ["a"]}]},
        ],
        "outcome": {"type": "served_sinks", "sources": ["src"], "sinks": ["sink"]},
    }
    m = load_model(d)
    assert baseline_outcome(m, 0) == 1
    # Remove src: a and b still support each other (continuity) -> sink served.
    fn = functioning_nodes(m, {"src"}, 0)
    assert "a" in fn and "b" in fn


# ---------- determinism ----------

def test_deterministic(model):
    assert run_sweep(model, [0, 12, 24]).as_dict() == run_sweep(model, [0, 12, 24]).as_dict()


def test_removed_never_functions(model):
    assert "src" not in functioning_nodes(model, {"src"}, 0)
