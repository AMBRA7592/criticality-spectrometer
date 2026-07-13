"""Regression tests for the AI-compute worked example.

These assert the v2.5 -> v0.1 translation and the key curves against values
computed from the actual v2.5 source. They exist because an earlier port dropped
the wafer dependencies and implemented the secondary frontier metric as if it
were primary; both errors passed silently because no test exercised the AI case.
"""
import json
from pathlib import Path

import pytest

from criticality_spectrometer import load_model, run_sweep

AI = Path(__file__).resolve().parent.parent / "examples" / "ai_compute"


@pytest.fixture(scope="module")
def models():
    return {name: load_model(str(AI / f"model_{name}.json"))
            for name in ("topology", "frontier_stack", "frontier_fab_only")}


@pytest.fixture(scope="module")
def sweeps(models):
    return {k: run_sweep(m, [0, 12, 24]) for k, m in models.items()}


# ---- translation fidelity -------------------------------------------------

def test_node_count_is_52(models):
    for m in models.values():
        assert len(m.nodes) == 52


def test_all_fabs_have_wafer_dependency(models):
    """v2.5 gives every fab a wafers:{si_wafers} group. The earlier port dropped
    this; assert it is present so the regression cannot recur."""
    m = models["frontier_stack"]
    deps = m.dependencies
    for fab in ("tsmc_advanced", "samsung_foundry", "intel_foundry", "smic_mature"):
        groups = {r.id: r.any_of for r in deps[fab].requirements}
        assert "wafers" in groups, f"{fab} missing wafers group"
        assert "si_wafers" in groups["wafers"]


def test_si_wafers_to_fab_edges_present(models):
    """The four si_wafers->fab strict edges must be represented (as wafer group
    membership). Removing si_wafers must therefore disable fabs on the stack."""
    r = run_sweep(models["frontier_stack"], [0, 12, 24])
    assert r.curves["si_wafers"].impact == [4, 4, 4]


def test_copper_foil_not_critical(sweeps):
    """copper_foil->cowos is a strict v2.5 edge, but v2.5 does NOT cascade it
    (copper_foil is not in cowos's declared AND groups; v2.5 reports 0/0/0). An
    earlier port rendered it as an auxiliary AND group of cowos, fabricating
    copper_foil frontier-persistence [4,4,4]. This asserts the corrected curve:
    copper_foil must be non-critical on every mission, matching v2.5."""
    for mission in ("frontier_stack", "frontier_fab_only", "topology"):
        c = sweeps[mission].curves["copper_foil"]
        assert c.impact == [0, 0, 0], f"{mission}: copper_foil {c.impact}"
        assert c.shape == "none"


def test_copper_foil_edge_logged_unsupported():
    """The dropped copper_foil connectivity edge must be logged, not silently
    omitted: v0.1 has no connectivity-only relation."""
    ledger = json.loads((AI / "parity_ledger.json").read_text())
    copper = [e for e in ledger
              if e["tag"] == "unsupported" and "copper_foil" in e["item"]]
    assert copper, "copper_foil dropped edge not logged as unsupported"


def test_fluorochemistry_not_critical(sweeps):
    """fluorochemistry->photoresists is a strict v2.5 edge into a non-AND_DEPS
    node; v2.5 does not cascade it (reports 0/0/0). Rendering it as an OR-liveness
    dependency wrongly made photoresists depend on it and fluorochemistry critical.
    Asserts the corrected curve. photoresists itself stays critical via the fab
    resist groups (tested separately)."""
    for mission in ("frontier_stack", "frontier_fab_only", "topology"):
        c = sweeps[mission].curves["fluorochemistry"]
        assert c.impact == [0, 0, 0], f"{mission}: fluorochemistry {c.impact}"


def test_alternatives_count(models):
    """22 timed alternatives from degraded/loose edges, including the six
    Samsung/Intel design alternatives the earlier ledger omitted."""
    m = models["topology"]
    assert len(m.alternatives) == 22
    design_alts = [a for a in m.alternatives
                   if a.requirement_id == "design"
                   and a.target in ("samsung_foundry", "intel_foundry")]
    assert len(design_alts) == 6


def test_stack_mission_has_four_waypoint_groups(models):
    """The PRIMARY frontier mission must encode the full stack:
    adv_fab -> cowos -> server -> cloud. A single-waypoint (fab-only) model is
    the SECONDARY metric and must not masquerade as primary."""
    m = models["frontier_stack"]
    wp = m.outcome.waypoints
    assert len(wp) == 4
    assert set(wp[0]) == {"tsmc_advanced", "samsung_foundry", "intel_foundry"}
    assert set(wp[1]) == {"cowos"}
    assert set(wp[2]) == {"foxconn", "quanta", "wistron", "supermicro", "dell_hpe"}
    assert set(wp[3]) == {"aws", "azure", "gcp", "oracle_cloud"}


def test_fab_only_mission_has_one_waypoint(models):
    m = models["frontier_fab_only"]
    assert len(m.outcome.waypoints) == 1


# ---- key curves vs v2.5 ground truth --------------------------------------
# v2.5 stack values (16 pairs) scale to served_sinks (4 sinks). The SHAPES and
# the persistent/declining/none classifications must match.

def test_euv_corridor_frontier_persistent(sweeps):
    """v2.5: ASML/Zeiss/TRUMPF frontier-stack 16/16/16 (flat). Here: [4,4,4]."""
    r = sweeps["frontier_stack"]
    for n in ("asml_euv", "zeiss_optics", "trumpf_source"):
        assert r.curves[n].impact == [4, 4, 4]
        assert r.curves[n].shape == "persistent"


def test_abf_frontier_persistent_on_stack(sweeps):
    """v2.5: ABF frontier-stack 16/16/16 (0 on fab_only). The earlier port used
    fab_only and wrongly reported ABF as [0,0,0]."""
    assert sweeps["frontier_stack"].curves["abf_substrate"].impact == [4, 4, 4]
    assert sweeps["frontier_fab_only"].curves["abf_substrate"].impact == [0, 0, 0]


def test_cowos_frontier_persistent_on_stack(sweeps):
    assert sweeps["frontier_stack"].curves["cowos"].impact == [4, 4, 4]


def test_tsmc_frontier_declining_on_stack(sweeps):
    """v2.5: TSMC frontier-stack 16/0/0 (declining). Here: [4,0,0]
    fully_adaptable. The earlier port reported [0,0,0] because the stack was
    missing; this test locks in the corrected behaviour."""
    c = sweeps["frontier_stack"].curves["tsmc_advanced"]
    assert c.impact == [4, 0, 0]
    assert c.shape == "fully_adaptable"


def test_germanium_zero_on_frontier(sweeps):
    """v2.5: germanium frontier 0/0/0 (feeds optics, not logic)."""
    assert sweeps["frontier_stack"].curves["germanium"].impact == [0, 0, 0]
    assert sweeps["frontier_fab_only"].curves["germanium"].impact == [0, 0, 0]


def test_chemistry_frontier_persistent(sweeps):
    r = sweeps["frontier_stack"]
    for n in ("photoresists", "cmp_slurries", "specialty_gases",
              "purity_chemicals", "ultrapure_water"):
        assert r.curves[n].impact == [4, 4, 4], n


def test_topology_upstream_nodes_zero_clouds_can_bite(sweeps):
    """Under served_sinks, selected UPSTREAM supply-chain nodes are [0,0,0]: all
    sinks have non-fab routes, so no upstream removal de-serves a sink. But
    downstream cloud/sink removals CAN reduce service. This documents both facts
    precisely (an earlier PARITY claim that 'every node is [0,0,0]' was wrong:
    the four sinks plus Azure and GCP are nonzero)."""
    r = sweeps["topology"]
    # Upstream nodes: zero.
    for n in ("asml_euv", "abf_substrate", "si_wafers", "tsmc_advanced",
              "germanium", "photoresists", "copper_foil", "fluorochemistry"):
        assert r.curves[n].impact == [0, 0, 0], f"{n} {r.curves[n].impact}"
    # Cloud/sink nodes: can reduce service (removing a sink de-serves itself;
    # Azure/GCP removal can drop a sink they uniquely route at strict).
    nonzero = {n for n, c in r.curves.items() if any(v != 0 for v in c.impact)}
    assert "azure" in nonzero and "gcp" in nonzero
    for sink in ("openai_api", "anthropic_api", "gemini_api", "meta_llama"):
        assert sink in nonzero


def test_committed_results_match(sweeps):
    """results.json must match a fresh run (guards against stale committed data)."""
    committed = json.loads((AI / "results.json").read_text())
    for name, r in sweeps.items():
        for node, cur in r.curves.items():
            exp = committed[name]["curves"][node]
            assert exp["impact"] == cur.impact, f"{name}/{node}"
            assert exp["shape"] == cur.shape, f"{name}/{node}"


# ---- edge parity vs frozen v2.5 manifest ----------------------------------

def _builder_edges():
    """Extract the EDGES literal from the builder without executing module-level
    file-path code."""
    import re
    src = (AI / "build_ai_case.py").read_text()
    m = re.search(r'^EDGES = \[.*?^\]', src, re.DOTALL | re.MULTILINE)
    ns = {}
    exec(m.group(0), ns)
    return {tuple(e) for e in ns["EDGES"]}


def test_edge_manifest_parity():
    """The builder's complete edge inventory must equal the frozen v2.5 manifest
    exactly (set equality, both directions). This is the complete-parity test:
    other tests check counts and selected edges but never the full 151-edge set.

    Provenance caveat: this compares two artifacts frozen in THIS repo (the
    builder's EDGES literal and v2_5_manifest.json). It does NOT reach the
    upstream v2.5 source, which is not shipped here. The manifest records that
    source's sha256 (test_manifest_source_hash_present) so a reviewer can verify
    provenance externally by hashing their copy of compute_rir_v2_5.py against it;
    CI cannot detect an upstream change on its own."""
    manifest = json.loads((AI / "v2_5_manifest.json").read_text())
    manifest_edges = {tuple(e) for e in manifest["edges"]}
    builder_edges = _builder_edges()
    assert manifest["edge_count"] == 151
    assert manifest["strict_count"] == 129
    missing = manifest_edges - builder_edges   # in v2.5, absent from builder
    extra = builder_edges - manifest_edges      # in builder, not in v2.5
    assert not missing, f"edges in v2.5 manifest missing from builder: {sorted(missing)}"
    assert not extra, f"edges in builder not in v2.5 manifest: {sorted(extra)}"


def test_every_strict_edge_rendered_or_dispositioned(models):
    """Completeness: every strict manifest edge must be either (a) rendered as a
    dependency any_of membership, or (b) explicitly dispositioned in the parity
    ledger (unsupported drop, or the hpq->si_wafers source-semantics changed
    entry). No strict edge may vanish silently. Degraded/loose edges are covered
    by alternatives and checked elsewhere."""
    import re
    manifest = json.loads((AI / "v2_5_manifest.json").read_text())
    strict = [(u, v) for (u, v, t) in
              ((e[0], e[1], e[2]) for e in manifest["edges"]) if t == "strict"]

    m = models["frontier_stack"]
    rendered = set()
    for target, dep in m.dependencies.items():
        for g in dep.requirements:
            for mem in g.any_of:
                rendered.add((mem, target))

    ledger = json.loads((AI / "parity_ledger.json").read_text())
    unsupported = set()
    for e in ledger:
        mm = re.match(r"edge (\S+)->(\S+) @strict", e["item"])
        if mm and e["tag"] == "unsupported":
            unsupported.add((mm.group(1), mm.group(2)))

    # hpq->si_wafers is intentionally not rendered (si_wafers is a source, an
    # independent origin) and must be dispositioned by a 'changed' ledger entry
    # that names the edge. Derive the exemption from that entry rather than
    # hardcoding a skip, so deleting the ledger entry fails this test.
    changed_hpq = [e for e in ledger if e["tag"] == "changed"
                   and "hpq" in e["item"] and "si_wafers" in e["item"]]
    assert changed_hpq, ("hpq->si_wafers is unrendered but has no 'changed' ledger "
                         "entry dispositioning it")
    source_semantics_exempt = {("hpq", "si_wafers")}

    undispositioned = []
    for (u, v) in strict:
        if (u, v) in rendered:
            continue
        if (u, v) in unsupported:
            continue
        if (u, v) in source_semantics_exempt:
            continue
        undispositioned.append((u, v))
    assert not undispositioned, f"strict edges neither rendered nor logged: {undispositioned}"


def test_manifest_source_hash_present():
    """The manifest must record the sha256 of the v2.5 source it was derived from,
    so a reviewer can verify provenance externally. This checks the field is a
    well-formed sha256; it cannot verify the upstream source here (not shipped)."""
    manifest = json.loads((AI / "v2_5_manifest.json").read_text())
    h = manifest.get("v2_5_source_sha256", "")
    assert isinstance(h, str) and len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
