# The semiconductor chokepoints getting the most attention have the lowest frontier AI impact

*A dual-metric substitutability curve analysis of the AI compute supply chain*

*Amadeus Brandes · April 2026*

---

Two results from a 52-node dependency graph of the AI compute supply chain:

**Germanium has zero frontier AI impact.** China's germanium export restriction in 2023 was widely covered as a semiconductor countermove. In a graph with AND-dependency cascades and two reachability metrics, germanium scores 0/0/0 in frontier impact and zero cascade. It feeds optical transceivers and fiber — networking infrastructure, not the compute path. Germanium has SiGe applications in RF/analog, but these are not in the sub-5nm digital logic path for frontier inference. The restriction may be well-calibrated for its actual targets (defense infrared optics, telecom), but the widespread framing as a frontier semiconductor move does not hold structurally.

**ABF substrate scores identically to ASML in frontier criticality.** Both disrupt 16 of 16 frontier pairs, invariant across all substitution timelines. But ABF substrate scores 0/0/0 in standard topological analysis — it is invisible to any conventional supply chain dependency model. Ajinomoto holds approximately 95% of the advanced ABF film market. It is not discussed in the same breath as ASML. This model says it should be.

These two findings come from a single structural observation: in the AI compute supply chain, "a path exists" and "a capable path exists" are different questions, and they identify different chokepoints.

## Method

The analysis builds a directed graph covering raw materials (high-purity quartz, silicon wafers, rare earths, germanium, ultrapure water) through to inference endpoints (OpenAI, Anthropic, Google Gemini, Meta Llama). Edges represent supply relationships at three substitutability thresholds: *strict* (0–3 months), *degraded* (12 months), and *loose* (24 months).

The model captures AND-dependencies: a fab needs photoresists *and* slurries *and* gases *and* chemicals *and* water *and* wafers *and* lithography *and* a chip design simultaneously. ASML needs Zeiss optics *and* TRUMPF light sources. Advanced 2.5D packaging needs fab output *and* HBM *and* ABF substrate. Design requirements are fab-specific: Western fabs require the Western design stack; SMIC requires the Chinese design ecosystem, modeled as an explicit node.

Two metrics are computed for each node removal at each threshold:

**Topology impact**: source-to-sink pairs disconnected (out of 20). Counts whether *any* path survives, including mature-node SMIC paths.

**Frontier-stack impact**: pairs that lose their ordered end-to-end frontier path — source → advanced fab → advanced packaging → server → cloud → sink — out of 16 frontier-reachable pairs. Because advanced packaging has AND-dependencies on fab output, HBM, and ABF substrate, removing any of these breaks the frontier stack even if the topology survives through non-frontier routes.

For source nodes, both metrics are decomposed into self-pair loss (trivial: removing a source removes its own pairs) and cascade loss (structural: does the removal cascade to affect other sources' paths).

## The full taxonomy

The dual metric produces four categories:

**Frontier-critical (topology-declining, frontier-flat).** ASML, Zeiss SMT, and TRUMPF show topology 4/4/0 — at 24 months, SMIC provides alternative topological routes. Frontier-stack 16/16/16 — invariant. No alternative for sub-5nm inference at any timescale. These three companies sit within 480 km of each other in Western Europe. The constraint is physical: picometer-precision optics with no alternative technology.

**Frontier-only (topology-invisible, frontier-flat).** ABF substrate and advanced 2.5D packaging show zero topology impact but frontier-stack 16/16/16. Invisible to any topology-only analysis. Surfaced only by the ordered-stack metric.

**Full flat-critical (topology-flat, frontier-flat).** Photoresists, CMP slurries, specialty gases, purity chemicals, ultrapure water, and silicon wafers. Topology 4/4/4 (silicon wafers 8/8/8 due to dual-path cascade through logic and memory), frontier-stack 16/16/16. Removal disables all fabs including SMIC. Category nodes aggregating multiple suppliers; splitting to supplier level would likely convert from flat to declining.

**Declining (both metrics decline).** TSMC (4/0/0 topology, 16/0/0 frontier), cloud providers, server assemblers. Compensable within 12–24 months.

## Where the ranking inverts

The hierarchy this model produces runs opposite to where policy attention currently sits:

*At the top* — ASML/Zeiss/TRUMPF and ABF substrate. Identical frontier scores (16/16/16), both irreplaceable at any timescale. The first receives extensive coverage. The second does not.

*In the middle* — Silicon wafers. Higher topology impact than ASML (8 vs 4) due to dual-path cascade through logic and memory supply chains. The only source node with frontier cascade greater than zero besides ultrapure water. Discussed in industry but not with the urgency the cascade math suggests.

*At the bottom, despite receiving the most geopolitical attention* — Germanium and rare earths. Germanium: frontier 0/0/0, cascade zero. Rare earths: frontier self=4, cascade=0. They matter for networking and power infrastructure, not for frontier inference.

## Sensitivity

The v2.4 frontier definition (source → advanced fab → sink) and the v2.5 stack definition (source → advanced fab → packaging → server → cloud → sink) produce identical results for all nodes except two: ABF substrate and advanced 2.5D packaging, which shift from 0/0/0 to 16/16/16. The stack definition surfaces exactly two additional nodes without disturbing any other classification.

## Version history

v2.3 classified ASML/Zeiss/TRUMPF as topology-flat-critical. This was an artifact: SMIC silently failed a blanket design-predecessor check. v2.4 corrected this with per-fab design requirements. v2.5 adds silicon wafers as a fab prerequisite and redefines frontier as an ordered stack, surfacing ABF and packaging as frontier-flat.

## Caveats

The robustness tiers are an analyst-assigned judgment register, not computed by the algorithm. AND-dependencies cover fabs, ASML, and advanced packaging only; server, networking, power/thermal, and cloud use OR-semantics. Category nodes aggregate multiple suppliers. HPQ lacks degraded alternative-quartz edges. The frontier-stack metric is a more realistic proxy than fab-only reachability but is not a complete end-to-end capability model. The model captures structural dependencies, not temporal buffers — installed EUV machines continue operating if ASML goes offline.

---

*Methodology: 52-node directed graph (v2.5), 129–151 edges. AND-cascade with per-fab design requirements, per-chemical-class inputs, wafer prerequisites, and advanced packaging AND-deps. Two metrics: topology (20 pairs) and frontier-stack (16 pairs). Source nodes decomposed into self-pair and cascade loss. Code, edge list, and results at [repo]. Prior work: Arulselvan et al. 2009, Snyder et al. 2016, UVA NSDPI 2025. The dual topology/frontier taxonomy is, to our knowledge, a novel contribution.*
