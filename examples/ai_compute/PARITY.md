# AI case port — parity analysis

The v2.5 AI-compute study is ported onto the frozen v0.1 instrument as three
mission models. This records which v2.5 findings survive the cleaner instrument.
Divergence is data, not failure: the instrument counts **served sinks** (a sink
counts once if reached), whereas v2.5 counted source→sink **pairs** (max 16 or
20). Absolute numbers therefore differ; the shapes and classifications are the
comparison of record.

Every translation decision is in `parity_ledger.json` (tagged
preserved/changed/unsupported/new). External evidence for nodes, edges, and
activation assumptions is in `evidence_ledger.json`. Committed engine output is
in `results.json` and is regression-tested in `tests/test_ai_case.py`.

## Missions

- **`model_topology.json`** — `served_sinks`: any source reaches the sink.
- **`model_frontier_stack.json`** — PRIMARY. `ordered_served_sinks` through the
  full v2.5 stack: advanced fab → CoWoS → server → cloud. This is v2.5's primary
  frontier metric.
- **`model_frontier_fab_only.json`** — SECONDARY. `ordered_served_sinks` through
  an advanced fab only. This is v2.5's `fab_only` sensitivity metric.

## What was preserved

- All 52 nodes verbatim, including `china_design`.
- Every fab's AND dependencies **including `wafers:{si_wafers}`** and the four
  `si_wafers → fab` edges. ASML optics+source; CoWoS fab+hbm+substrate. Strict
  predecessors into an AND node that are not in a declared v2.5 group (e.g.
  `copper_foil → cowos`) are NOT rendered as dependencies — v2.5 does not cascade
  them — and the dropped edges are logged `unsupported` (see Divergence 5).
- The full 151-edge v2.5 inventory (129 strict) is frozen in `v2_5_manifest.json`
  (with the v2.5 source sha256) and checked for exact set-equality against the
  builder by `test_edge_manifest_parity`. The three thresholds map to activation
  times 0/12/24; a strict edge is always-on, a degraded/loose-only edge becomes a
  targeted alternative (22 alternatives, including the six Samsung/Intel design
  substitutes). Four strict edges from two upstream node families (`copper_foil→
  cowos/osat_ase/osat_amkor`, `fluorochemistry→photoresists`) are present in the
  inventory but NOT rendered as dependencies — see Divergence 5.

## Ground-truth comparison (primary stack mission)

v2.5 stack impacts are pair counts (of 16); the port's are served-sink counts
(of 4). The classification is what must match.

| Node | v2.5 stack (S/D/L) | v2.5 shape | port impact | port shape | verdict |
|---|---|---|---|---|---|
| ASML / Zeiss / TRUMPF | 16/16/16 | frontier-flat | [4,4,4] | persistent | **matches** |
| ABF substrate | 16/16/16 | frontier-flat | [4,4,4] | persistent | **matches** |
| CoWoS | positive/…/… | frontier-flat | [4,4,4] | persistent | **matches** |
| silicon wafers | 16/16/16 | frontier-flat | [4,4,4] | persistent | **matches** |
| photoresists / slurries / gases / 11N chem / ultrapure water | 16/16/16 | frontier-flat | [4,4,4] | persistent | **matches** |
| TSMC advanced | 16/0/0 | frontier-declining | [4,0,0] | fully_adaptable | **matches** |
| germanium | 0/0/0 | none | [0,0,0] | none | **matches** |

All seven v2.5 hard acceptance tests (positive strict frontier-stack impact for
ABF, CoWoS, si_wafers, ASML; ASML flat and matched by Zeiss/TRUMPF) hold under
the port.

## Headline finding: SURVIVES

The EUV corridor (ASML, Zeiss, TRUMPF) is **frontier-persistent** `[4,4,4]` on
the primary stack — removing any one drops all four frontier-served sinks at
every horizon. The generic engine reproduces v2.5's irreducibility result with
no case-specific logic. ABF, CoWoS, and silicon wafers are also frontier-
persistent, and TSMC is frontier-declining `[4,0,0]`, all matching v2.5.

## Divergence 1: topology mission — upstream nodes zero, clouds/sinks can bite — EXPLAINED

Under `served_sinks`, every *upstream supply-chain* node (ASML, ABF, wafers,
fabs, chemistry, germanium, copper_foil, fluorochemistry) has topology impact
`[0,0,0]`: all four sinks have non-fab routes (e.g. rare_earths→vertiv→cloud→API),
so no upstream removal de-serves a sink. This is not "every node is zero" — six
downstream nodes are nonzero: the four sinks (removing a sink de-serves itself)
plus Azure `[1,0,0]` and GCP `[1,1,0]` (each uniquely routes one sink at strict
before cloud alternatives activate). See `results.json`.

v2.5's topology figures (e.g. 4/20, si_wafers 8/20) were pair counts; a sink
losing some of its source-paths still counts as served here. The point stands:
sink-level topological redundancy among upstream nodes is total, and the frontier
stack is the instrument that carries the signal. The topology and stack missions
together reproduce v2.5's core thesis — topological redundancy and frontier
capability diverge.

## Divergence 2: fab_only vs stack for ABF and CoWoS — MATCHES v2.5

On the SECONDARY `fab_only` mission, ABF and CoWoS are `[0,0,0]`: a bare
source→fab→sink path bypasses packaging, so neither gates it. On the PRIMARY
stack mission they are `[4,4,4]` because the stack forces the CoWoS waypoint.
This matches v2.5's ABF/CoWoS acceptance results (ABF fab_only 0/16, stack
16/16/16) and is the reason the primary metric is the stack, not fab_only. (An
earlier port used fab_only as if it were primary and wrongly reported ABF as
non-critical.)

## Divergence 3: TSMC on the two frontier metrics — EXPLAINED

On the primary stack, TSMC is `[4,0,0]` (matches v2.5 16/0/0): at strict, CoWoS's
`fab_input` group is satisfied only by TSMC (Samsung/Intel reach CoWoS via the
degraded edge at τ=12), so removing TSMC breaks the stack until alternatives
activate. On `fab_only`, TSMC is `[0,0,0]` because Samsung/Intel provide bare fab
paths and their design requirement could not be deferred to τ=12 — the
`served_sinks`/alternative contract adds satisfiers over time but cannot make a
baseline requirement absent until a horizon without a present satisfier, and the
schema forbids an empty group. This design-deferral limitation is logged as a
`changed` entry. It affects only the fab_only sensitivity metric; the primary
stack reproduces v2.5's TSMC curve correctly.

## Divergence 4: germanium zero on frontier — MATCHES v2.5

Germanium is `[0,0,0]` on both frontier missions: it feeds optical transceivers
and fiber optics, never the sub-5nm logic path. Matches v2.5 exactly. (Its v2.5
topology 4/4/4 was pure self-pair loss, which `served_sinks` correctly ignores.)

## Divergence 5: copper_foil and fluorochemistry not rendered — MATCHES v2.5

v2.5's cascade disables a node only if it is an explicit `AND_DEPS` key; every
other node is reachability-only. Four strict edges from two upstream node families
feed nodes that v2.5 does not cascade: `copper_foil→cowos`, `copper_foil→osat_ase`,
and `copper_foil→osat_amkor` (copper is not in the declared groups of any of those
targets) and `fluorochemistry→photoresists` (photoresists is not an `AND_DEPS`
key). v2.5 reports both `copper_foil` and `fluorochemistry` at 0/0/0 on every
metric.

The frozen v0.1 engine has a single edge mechanism: an edge is in the reachability
graph iff it is a dependency `any_of` member or an alternative, and *any* rendered
dependency also imposes a liveness cascade. There is no connectivity-only relation.
So these edges cannot be rendered without fabricating criticality — which an
earlier port did, reporting `copper_foil` as frontier-persistent `[4,4,4]` via an
auxiliary AND group, and making `photoresists` wrongly depend on `fluorochemistry`.

All four edges are therefore left unrendered and logged `unsupported` in
`parity_ledger.json`. `copper_foil` and `fluorochemistry` are now correctly
`[0,0,0]`, matching v2.5. Their downstream targets stay reachable/satisfiable via
other rendered paths (cowos via its own groups; photoresists via being an `any_of`
member of every fab's `resist` group), so no source→sink path is lost and no
load-bearing curve changes. This is a v0.1 expressiveness limitation, not a v2.5
disagreement.

## Open extension

v2.5 flagged that adding AND-dependencies to the OSAT layer would likely surface
ABF on the fab_only metric too (OSAT also needs ABF substrate). That extension is
not in this port; ABF's fab_only `[0,0,0]` reflects the current OR-modeling of
OSATs and is noted as open, not as a contradiction with v2.5.

## Verdict

The load-bearing finding — the EUV corridor is irreducible for frontier
inference, with ABF, CoWoS, silicon wafers, and the chemistry inputs also
frontier-critical, and TSMC frontier-declining — survives the cleaner instrument
on the primary stack mission and matches all seven of v2.5's hard acceptance
tests. The port reproduces those named results; it does not claim bit-identical
behaviour on every node, because the generic dependency semantics differ from
v2.5 in two logged, non-load-bearing ways: (a) the τ-12 design-deferral boundary,
which affects only the secondary fab_only metric, and (b) four connectivity-only
edges from two upstream node families (`copper_foil`, `fluorochemistry`) that v0.1
cannot render without fabricating criticality, left unrendered so both nodes
correctly read `[0,0,0]`. No model was tuned to recover a headline.
