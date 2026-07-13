# Non-claims

What this instrument does **not** assert, in v0.1.

- **Not a capacity model.** It measures whether a capable path survives, not
  whether it can deliver enough throughput. A node can be non-critical here and
  still be capacity-binding in reality. Capacity is future work.

- **Not phase-transition detection.** The curve is evaluated at a few horizons.
  Calling a shape a "phase transition" requires resolution and a formal
  detection criterion that v0.1 does not have.

- **Not a policy theorem.** The interpretation layer (persistent → protect,
  fully_adaptable → enable alternatives, partially_adaptable → invest and
  bridge) is a reading, not a proved result.

- **Not an empirical claim about any specific system.** The engine is generic.
  Any empirical conclusion belongs to a specific model instance and is only as
  good as that instance's evidence ledger.

- **Not a substitute for domain expertise.** Activation times, dependency
  structure, and outcome definition are modeling choices. The instrument makes
  those choices explicit and testable; it does not supply them.

- **Not centrality.** Criticality here is mission-relative response-curve shape
  under removal, not a static graph-centrality score.

- **Keyword separation is a smoke test, not a proof.** The engine is checked to
  contain no case-specific tokens, and tests instantiate unrelated in-memory
  fixtures. Neither proves generality; a second real domain (v0.2) is what
  earns that claim.
