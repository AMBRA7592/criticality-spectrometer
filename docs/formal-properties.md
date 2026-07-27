# Formal properties of the v0.1 model contract

This note records bounded properties of the implemented deterministic model
contract. It does not claim equivalent results for arbitrary dynamic fault-tree
formalisms, probabilistic reliability models, capacity models, or startup
feasibility.

## Definitions

Let `P` be the finite set of declared nodes, `v` the node removed for a sweep,
and `A(tau)` the alternatives whose activation time is at most `tau`. For a
functioning set `X`, let `T_tau(X)` retain exactly the nodes in `X` whose
declared dependency is satisfied in `X` under `A(tau)`. Nodes without a
dependency are retained.

The cascade starts at `X_0 = P \ {v}` and applies synchronous rounds:

`X_(k+1) = T_tau(X_k)`.

This is the continuity interpretation implemented by `_cascade`: the system is
already operating, then nodes are removed until the greatest surviving fixed
point is reached.

## 1. Finite termination

`T_tau(X)` is a subset of `X`, so the sequence is deflationary. Every non-final
round removes at least one node. Since `X_0` contains at most `|P| - 1` nodes,
there can be at most `|P| - 1` nonempty removal rounds before a fixed point is
reached.

Implementation link: `cascade._cascade` collects every node that fails against
the set frozen at the start of a round, removes the nonempty collection, and
stops when that collection is empty. The loop guard is deliberately looser than
the mathematical bound. `test_finite_termination_bound_is_attainable` exercises
a chain that reaches the bound.

## 2. Declaration-order independence

For fixed `X` and `A(tau)`, dependency satisfaction is a function of set
membership, not iteration order. A synchronous round therefore removes the same
set of nodes regardless of declaration order. Induction gives the same set in
every subsequent round and the same final fixed point.

Implementation link: `_cascade` evaluates all dependencies against the
unchanged `functioning` set and mutates that set only after the complete round.
`test_round_membership_and_fixed_point_ignore_declaration_order` permutes a
branching model and compares round-membership sets and final functioning sets.
The display order of nodes within a round may still follow model declaration
order; that presentation detail is not part of the proposition.

## 3. Horizon monotonicity

If `tau_1 <= tau_2`, then `A(tau_1)` is a subset of `A(tau_2)`. Adding an
alternative can only make a requirement group easier to satisfy. Starting from
the same `X_0`, induction over synchronous rounds therefore gives a surviving
fixed point at `tau_1` that is a subset of the surviving fixed point at
`tau_2`.

Both implemented outcomes are monotone in functioning nodes and activated
edges: adding allowed nodes or edges cannot remove a reachable sink or an
ordered path. Mission survival therefore cannot decrease with `tau`. Removal
impact is `baseline - survival`, so impact cannot increase when the intact
baseline is constant. `run_sweep` explicitly rejects non-positive or
non-constant baselines.

Implementation link: `_active_substitutes` uses `activation_time <= tau`;
`run_sweep` checks the baseline before computing curves. The activation test and
the shipped-model parameterization exercise both functioning-set and impact
monotonicity.

## 4. Activation breakpoints

Between consecutive declared activation times, `A(tau)` is unchanged. The
cascade operator, its fixed point, and the induced outcome graph are therefore
unchanged. Curves are piecewise constant and can change only when `tau` reaches
a declared activation time.

Implementation link: `default_horizons` returns zero plus the distinct
activation times. `test_horizon_monotonicity_and_activation_breakpoint` checks
equal results on both sides of the sole breakpoint and a change exactly at it.

## 5. OR-relaxation upper bound

The implemented OR relaxation preserves nodes, requirement groups,
alternatives, and outcome definitions while replacing each dependency's `AND`
combination with `OR`. Any dependency satisfied under the declared logic is
therefore also satisfied under the relaxed logic. Induction over cascade rounds
gives a declared functioning set contained in the relaxed functioning set.

The induced outcome edges are otherwise identical at a fixed horizon, so
declared served sinks are a subset of relaxed served sinks for both supported
outcome types. Thus `S_OR - S_AND` is nonnegative.

Implementation link: `compare.or_relax` changes only each dependency's logic.
The shipped-model parameterization checks functioning-set containment,
served-sink containment, and nonnegative survival differences across all nodes
and declared horizons.

## Scope of the audit

The arguments rely on four enforced contract properties:

1. the node set is finite;
2. cascades only remove functioning nodes;
3. increasing the horizon only activates alternatives;
4. outcome service is monotone in functioning nodes and induced edges.

Changing the contract to include capacity competition, resource consumption,
deactivating alternatives, probabilistic state, or non-monotone outcome rules
would require new proofs.
