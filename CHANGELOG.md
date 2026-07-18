# Changelog

All notable changes to this project are documented here.

## [0.1.2] — 2026-07-18

### Added
- `criticality-spectrometer example {canonical,tutorial} [--output PATH]`:
  emits a bundled example model byte-for-byte (stdout by default, refusing to
  overwrite existing files), so a pip-installed instrument runs the demo with
  no clone. Packaged copies are regression-tested byte-identical to the
  repository fixtures.
- `criticality-spectrometer explain MODEL NODE [--format text|json]`: per
  horizon, the measured impact and lost sinks, casualties grouped by cascade
  round, every unsatisfied requirement group per casualty (with pending and
  dead substitutes), active substitutes, substitutes that actually satisfy a
  group with no functioning declared member, and sinks restored relative to
  the previous horizon. JSON output is self-identifying and conforms to
  `schema/explain.schema.json` (shipped publicly and inside the wheel).
- Public API: `cascade_trace`, `CascadeTrace`, `rescuing_substitutes`,
  `served_sink_set`, `explain_document`, `explain_json`, `explain_text`.

### Changed
- The cascade fixed point is computed in synchronous rounds (each round
  evaluated against the set frozen at its start). The greatest fixed point is
  unchanged — every result is identical — but rounds surfaced by
  `cascade_trace`/`explain` are now declaration-order-invariant propagation
  stages. `functioning_nodes` and `cascade_trace` are two views of one shared
  engine, asserted equal by tests.
- `count_outcome` is now the cardinality of the single authoritative
  `served_sink_set`. Side effect: a sink id listed twice in `outcome.sinks`
  no longer double-counts (the documented "a sink counts once" reading).

## [0.1.1] — 2026-07-14

Hardening release focused on reproducible public artifacts and stricter model
validation.

### Added
- Self-identifying JSON reports with instrument version, model and result schema
  versions, model SHA-256, horizons, and run configuration.
- A result JSON Schema shipped both publicly and inside the wheel.
- One deterministic `scripts/regenerate.py` command for the AI models, parity
  ledger, complete results bundle, and README figure.
- CI regeneration/clean-diff gate and local tests for schema identity, result
  validity, and README-figure freshness.
- A narrated ten-node CI-pipeline tutorial and Python API quickstart.
- `criticality-spectrometer --version`, documented CLI exit codes, and a
  `py.typed` marker for downstream type checkers.
- Python 3.13 CI coverage.
- Release workflow (`release.yml`): tag-gated build with a tag/version match
  check and `twine check`, publishing to PyPI via OIDC trusted publishing from
  the protected `pypi` environment — no long-lived API tokens.
- PARITY Divergence 6, recording that `hpq` reads frontier-persistent through
  the rendered `purity_chemicals` liveness path — a uniform-liveness vs
  reachability-only semantics divergence from v2.5, not a translation error.

### Changed
- **Validation is stricter:** direct self-satisfaction through a requirement or
  alternative now raises `ModelError`. A source with a dependency remains valid
  but emits `ModelWarning` because sources are reachability starts, not
  automatically independent origins.
- Explicit horizons are sorted and deduplicated. Existing serialized curve
  fields are retained.
- AND-aware survival computed during the curve sweep is reused by the single
  public OR-gap implementation.
- Package and test dependencies are defined only in `pyproject.toml`.
- The provenance CI gate also fails on untracked files, and
  `scripts/regenerate.py` sweeps each model over its own declared horizons
  instead of a hardcoded list.

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
