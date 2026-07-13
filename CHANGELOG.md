# Changelog

All notable changes to this project are documented here.

## [0.1.0] — 2026-07-14

First public release: the instrument extracted from the AI-compute case study.

### Added
- Domain-agnostic engine with no case-specific entities.
- Model schema (`schema/model.schema.json`), validated at load via
  `importlib.resources` so it resolves from source or installed wheel.
- Typed dependencies with stable requirement-group IDs (`{id, any_of}`).
- Group-targeted, time-stamped alternatives (`{target, requirement_id,
  replacement, activation_time}`); a substitute satisfies only its identified
  group.
- Continuity cascade semantics: start from the intact operational set, shrink to
  the greatest surviving fixed point. Intact cycles continue.
- `served_sinks` outcome (sinks reachable from >= 1 source), with
  `ordered_served_sinks` variant.
- Adaptation-horizon sweep producing per-node impact curves; default horizons
  are tau=0 plus every distinct activation time.
- Constant-valid-baseline enforcement (`BaselineError`).
- Conservative classification: none / persistent / fully_adaptable /
  partially_adaptable.
- AND/OR redundancy-illusion measure reported as the direct survival gap
  `S_OR - S_AND` (>= 0), with OR relaxation preserving group IDs so targeted
  alternatives stay attached.
- CLI: `criticality-spectrometer run|validate`.
- Named modules: `classify`, `compare`, `report`.
- Canonical synthetic fixture with hand-verifiable expected curves.
- Audited 52-node AI-compute worked example with three mission models, parity
  analysis, evidence ledger, frozen source manifest, and deterministic builder.
- Reproducible README curve figure generated from the committed worked-example
  results.
- 56 semantic, CLI, packaging, and empirical-parity regression tests.
- Wheel-install acceptance gate and case-free-engine check in CI.

### Not included (deferred)
- k-of-n logic, capacity/throughput constraints, phase-transition detection,
  curve clustering, source-sink pair diagnostics, startup-feasibility analysis,
  policy scoring. See `docs/nonclaims.md`.
