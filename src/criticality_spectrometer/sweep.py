"""
The adaptation-horizon sweep.

For each node v and horizon tau:
    I_v(tau) = baseline(tau) - served_sinks_after_removing_v(tau)

Impact is against the intact baseline at the same horizon. The default sweep
uses tau=0 and every distinct activation time (the curve is piecewise constant
and only changes there).

Requires a valid, constant baseline across horizons: intact mission capability
must not change with tau. If it does, the model is ill-posed for the removal
instrument and run_sweep raises. (Adaptation should reduce the impact of
removals, not change what the intact system delivers.)

OR gap is reported as the direct survival gap S_OR - S_AND (>= 0), the
redundancy illusion: how much more the naive OR reading thinks survives.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import Model, Dependency, RequirementGroup
from .cascade import functioning_nodes
from .outcome import count_outcome, baseline_outcome
from .classify import classify as _classify
from .compare import or_relax as _or_relax


class BaselineError(ValueError):
    """Raised when the intact baseline is invalid or non-constant across horizons."""


@dataclass
class NodeCurve:
    node: str
    horizons: list[float]
    impact: list[int]
    shape: str

    def as_dict(self) -> dict:
        return {"node": self.node, "horizons": self.horizons, "impact": self.impact, "shape": self.shape}


@dataclass
class SweepResult:
    horizons: list[float]
    baseline: int
    curves: dict[str, NodeCurve]
    or_survival_gap: dict[str, list[int]] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "horizons": self.horizons,
            "baseline": self.baseline,
            "curves": {n: c.as_dict() for n, c in self.curves.items()},
            "or_survival_gap": self.or_survival_gap,
        }


def default_horizons(model: Model) -> list[float]:
    taus = {0.0}
    for alt in model.alternatives:
        taus.add(float(alt.activation_time))
    return sorted(taus)


def _check_constant_baseline(model: Model, taus: list[float]) -> int:
    values = {tau: baseline_outcome(model, tau) for tau in taus}
    b0 = values[taus[0]]
    if b0 <= 0:
        raise BaselineError(f"Intact baseline is {b0} (<= 0); model delivers no mission capability.")
    if any(v != b0 for v in values.values()):
        raise BaselineError(
            f"Intact baseline varies across horizons: {values}. "
            "The removal instrument requires constant intact mission capability."
        )
    return b0


def run_sweep(model: Model, horizons: list[float] | None = None, compute_or_gap: bool = True) -> SweepResult:
    taus = horizons if horizons is not None else (model.horizons or default_horizons(model))
    if not taus:
        taus = default_horizons(model)
    taus = sorted(taus)

    baseline = _check_constant_baseline(model, taus)

    # Sweep EVERY node (no silent exclusions).
    candidates = list(model.nodes)

    curves: dict[str, NodeCurve] = {}
    for node in candidates:
        impact = []
        for tau in taus:
            fn = functioning_nodes(model, {node}, tau)
            impact.append(baseline - count_outcome(model, fn, tau))
        curves[node] = NodeCurve(node=node, horizons=list(taus), impact=impact, shape=_classify(impact))

    or_survival_gap: dict[str, list[int]] = {}
    if compute_or_gap:
        relaxed = _or_relax(model)
        for node in candidates:
            row = []
            for tau in taus:
                fn_and = functioning_nodes(model, {node}, tau)
                s_and = count_outcome(model, fn_and, tau)
                fn_or = functioning_nodes(relaxed, {node}, tau)
                s_or = count_outcome(relaxed, fn_or, tau)
                row.append(s_or - s_and)
            or_survival_gap[node] = row

    return SweepResult(horizons=list(taus), baseline=baseline, curves=curves, or_survival_gap=or_survival_gap)
