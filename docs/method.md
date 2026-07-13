# Method

The Criticality Spectrometer measures how the impact of removing a node changes
as alternatives become available over an adaptation horizon, in a system with
typed (AND/OR) dependencies.

## Objects

A **model** is nodes, dependencies, alternatives, and an outcome.

- **Node**: an id plus optional descriptive metadata. The engine assigns no
  meaning to node types beyond the outcome's source/sink lists.
- **Dependency**: a rule `target requires <requirement groups> under <AND|OR>`.
  Each group has a stable `id` and an `any_of` list of interchangeable inputs
  (satisfied if any one functions). AND requires every group; OR requires at
  least one.
- **Alternative**: a group-targeted, time-stamped substitute. `the requirement
  group identified by (target, requirement_id) may be satisfied by replacement
  once tau >= activation_time, while replacement functions`. A substitute
  satisfies **only** that one identified group — so if the same provider node
  appears in several groups, a substitute for one group does not rescue another.
- **Outcome**: what loss is measured. `served_sinks` (default): sinks reachable
  from at least one source. `ordered_served_sinks`: served via a path passing an
  ordered waypoint sequence.

## Functioning (continuity semantics)

The instrument asks about continuity after removal from an already-operating
system, not startup feasibility. So functioning starts from the intact
operational set (all present nodes) and shrinks to the greatest surviving fixed
point: iteratively remove any node whose dependency is unsatisfied, until stable.

A requirement group is satisfied iff a declared `any_of` member functions, or a
targeted substitute for that group is active (tau reached) with its replacement
functioning.

Consequence for cycles: a mutually-supporting cycle that is intact at start
keeps running unless a removal breaks it. This is the correct continuity reading
— the cycle was already operating. Startup feasibility is a separate question,
out of scope for the removal instrument.

## Outcome: served sinks

`served_sinks` counts sinks reachable from at least one source. A sink served by
two sources counts once, so removing one redundant source registers no spurious
impact. (A source-sink pair count is a connectivity-diversity diagnostic, not
the mission-survival measure, and is deferred.)

## Baseline: valid and constant

The intact baseline must be positive and constant across horizons. Adaptation
reduces the impact of removals; it must not change what the intact system
delivers. If the intact baseline varies with tau, the model is ill-posed for the
removal instrument and `run_sweep` raises `BaselineError`. Under a constant
valid baseline, impact is non-increasing in tau.

## Impact and the curve

For node v at horizon tau:

    I_v(tau) = baseline - served_sinks_after_removing_v(tau)

Impact is against the intact baseline. The curve is piecewise constant and
changes only at activation times, so the default sweep evaluates tau=0 and every
distinct activation time. Every node is swept — no silent exclusions.

## Classification (conservative)

- **none** — zero impact at every horizon
- **persistent** — the same positive impact at every horizon (all values equal)
- **fully_adaptable** — positive at tau=0, zero by the last horizon
- **partially_adaptable** — declines but is not flat and not fully to zero

No phase-transition claims in v0.1.

## The AND/OR gap (redundancy illusion)

OR relaxation flattens each dependency into "satisfied if any declared input
functions" — the maximally permissive reading and the correct upper bound on
survival. AND-aware survival never exceeds OR-relaxed survival. The gap is
reported as the direct survival difference:

    or_survival_gap_v(tau) = S_OR(tau) - S_AND(tau)   (>= 0)

A positive gap is the redundancy illusion: under naive OR reachability the node
looks substitutable, but under the true AND requirements it is not.

## What v0.1 does not do

k-of-n logic, capacity/throughput constraints, phase-transition detection,
curve clustering, source-sink pair diagnostics, startup-feasibility analysis,
and policy scoring are out of scope. See `nonclaims.md`.
