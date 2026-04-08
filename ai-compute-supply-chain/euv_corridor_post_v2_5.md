# Topology and frontier capability are not the same thing

*A dual-metric substitutability curve analysis of the AI compute supply chain*

*Amadeus Brandes · April 2026*

---

The physical infrastructure behind AI inference spans 13 countries and involves dozens of companies at every layer. In 2026, the five largest Western hyperscalers (Amazon, Alphabet, Meta, Microsoft, Oracle) are projected to spend over $650 billion in combined capital expenditure, the majority directed at AI infrastructure. The supply chain appears richly redundant.

A graph analysis with two impact metrics reveals that topological redundancy and frontier inference capability are not the same thing. Nodes exist that are topologically compensable — alternative paths survive their removal — but frontier-irreplaceable: no path capable of sub-5nm inference survives. That gap between topology and frontier is the finding.

## Method

The analysis uses a 52-node directed graph covering raw materials (high-purity quartz, silicon wafers, rare earths, germanium, ultrapure water) through to inference endpoints (OpenAI, Anthropic, Google Gemini, Meta Llama). Edges represent supply relationships at three substitutability thresholds: *strict* (drop-in replacement within 3 months), *degraded* (12 months), and *loose* (24 months).

The model captures AND-dependencies: a fab needs photoresists *and* slurries *and* gases *and* chemicals *and* water *and* wafers *and* lithography *and* a chip design simultaneously. ASML needs Zeiss optics *and* TRUMPF light sources. Advanced 2.5D packaging needs fab output *and* HBM *and* ABF substrate. Design requirements are fab-specific: Western fabs require the Western design stack; SMIC requires the Chinese design ecosystem, modeled as an explicit node.

Two metrics are computed for each node removal at each threshold:

**Topology impact**: source-to-sink pairs disconnected (out of 20). Counts whether *any* path survives, including mature-node SMIC paths.

**Frontier-stack impact**: pairs that lose their ordered end-to-end frontier path — source → advanced fab → advanced packaging → server → cloud → sink — out of 16 frontier-reachable pairs. Because advanced packaging has AND-dependencies on fab output, HBM, and ABF substrate, removing any of these breaks the frontier stack even if the topology survives through non-frontier routes.

For source nodes, both metrics are decomposed into self-pair loss (trivial: removing a source removes its own pairs) and cascade loss (structural: does the removal cascade to affect other sources' paths).

## Results

Four categories emerge from the dual taxonomy.

**Frontier-critical (topology-declining, frontier-flat).** ASML, Zeiss SMT, and TRUMPF show topology impact of 4/4/0 — at 24 months, SMIC provides an alternative topological route. Their frontier-stack impact is 16/16/16 — invariant. No alternative exists for sub-5nm inference at any timescale. These three companies sit within 480 km of each other in Western Europe (Veldhoven, Ditzingen, Oberkochen). The constraint is physical: picometer-precision optics with no alternative technology.

**Frontier-only (topology-invisible, frontier-flat).** ABF substrate (Ajinomoto) and advanced 2.5D packaging show zero topology impact at all thresholds but frontier-stack impact of 16/16/16. These nodes are invisible to any topology-only analysis. The frontier-stack metric surfaces them because the ordered path requires advanced packaging, which has AND-dependencies on ABF substrate. Ajinomoto holds approximately 95% of the advanced ABF film market.

**Full flat-critical (topology-flat, frontier-flat).** Photoresists, CMP slurries, specialty gases, purity chemicals, and ultrapure water show topology impact of 4/4/4 and frontier-stack impact of 16/16/16. Silicon wafers show a higher topology impact of 8/8/8 (self=4 plus cascade=4, because wafer removal cascades to disable fabs via AND-dependency) and frontier-stack 16/16/16. Their removal disables all fabs including SMIC. These are category nodes aggregating multiple suppliers; splitting them to supplier level would likely convert them from flat to declining.

**Declining (both metrics decline).** TSMC shows 4/0/0 topology and 16/0/0 frontier — compensated by Samsung and Intel at degraded threshold. Cloud providers show similar declining patterns.

## Source decomposition

The frontier source decomposition distinguishes real structural cascade from trivial self-pair loss:

- **Silicon wafers**: frontier self=4, cascade=12. Removing wafers cascades to kill all fabs via AND-dependency — a genuine structural chokepoint.
- **Ultrapure water**: frontier self=4, cascade=12. Same cascade mechanism.
- **HPQ and rare earths**: frontier self=4, cascade=0. No downstream fab cascade. Their frontier impact is entirely self-pair loss.
- **Germanium**: frontier self=0, cascade=0. Does not reach frontier paths at all.

## Sensitivity: fab-only vs stack frontier

The v2.4 frontier definition (source → advanced fab → sink) and the v2.5 stack definition (source → advanced fab → packaging → server → cloud → sink) produce identical results for all nodes except two: ABF substrate and advanced 2.5D packaging, which shift from 0/0/0 to 16/16/16. The stack definition surfaces exactly two additional nodes — the packaging layer — without disturbing any other classification. This is a disciplined extension, not a wholesale revision.

## The EUV corridor

The EUV corridor occupies a position unique in the graph: topology-declining but frontier-flat. It is compensable at the 24-month horizon in topology (SMIC exists) but irreplaceable for frontier inference at any timescale (SMIC cannot run sub-5nm models). A supply chain analysis using only topological reachability would classify the EUV corridor as manageable. The frontier-stack metric reveals it is not.

ABF substrate and advanced 2.5D packaging share the frontier-flat property but through a different mechanism: they are topology-invisible (removing them doesn't disconnect any source-sink pair) but frontier-critical (they sit on every ordered frontier path). These nodes are undetectable without the end-to-end stack definition.

## Version history

v2.3 classified ASML/Zeiss/TRUMPF as topology-flat-critical. This was an artifact: all fabs including SMIC were required to have a Western design predecessor, but no such edge existed for SMIC. v2.4 corrected this with per-fab design requirements and a Chinese design ecosystem node. v2.5 adds silicon wafers as a fab prerequisite and redefines frontier as an ordered end-to-end stack, surfacing ABF and packaging as frontier-flat.

## Caveats

The robustness tiers (A: robust single-entity, C: resolution/threshold/model-sensitive) are an analyst-assigned judgment register layered on top of the computed taxonomy. They are not generated by the algorithm.

AND-dependencies cover fabs, ASML, and advanced packaging. Server integration, networking, power/thermal, and cloud availability are modeled as ordinary reachability, not joint requirements. Extending AND-semantics to these layers may surface additional critical nodes.

Category nodes (photoresists, slurries, etc.) aggregate multiple suppliers. Splitting to supplier level would likely convert them from flat to declining. HPQ lacks degraded alternative-quartz edges; its topology-flat status is model-dependent.

If design-to-foundry edges for Nvidia/Broadcom are moved from degraded to loose, TSMC re-enters the frontier-flat set. TSMC's classification depends on a single threshold judgment about foundry re-qualification timelines.

The model captures structural dependencies, not temporal buffers. Installed EUV machines continue operating if ASML goes offline. The finding applies to new capacity and replacement equipment.

---

*Methodology: 52-node directed graph (v2.5), 129–151 edges. AND-cascade with per-fab design requirements, per-chemical-class inputs, wafer prerequisites, and advanced packaging AND-deps. Two metrics: topology (20 pairs) and frontier-stack (16 pairs, ordered: source → advanced fab → packaging → server → cloud → sink). Source nodes decomposed into self-pair and cascade loss for both metrics. Sensitivity comparison between fab-only and stack frontier definitions. Code, edge list, and results at [repo]. Prior work: Arulselvan et al. 2009, Snyder et al. 2016, UVA NSDPI 2025. The dual topology/frontier taxonomy and ordered-stack frontier definition are, to our knowledge, novel contributions.*
