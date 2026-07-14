#!/usr/bin/env python3
"""
Port the v2.5 AI compute graph onto the frozen v0.1 schema.

Produces THREE mission models:
  - model_topology.json          served_sinks: any source reaches sink
  - model_frontier_stack.json    PRIMARY: source -> advanced_fab -> cowos ->
                                  server -> cloud -> sink (v2.5 stack metric)
  - model_frontier_fab_only.json SECONDARY: source -> advanced_fab -> sink
                                  (v2.5 sensitivity metric)

Every translation decision is logged to parity_ledger.json with a tag:
preserved / changed / unsupported / new. Evidence citations live separately in
evidence_ledger.json.

Thresholds -> activation_times: strict=0, degraded=12, loose=24. A strict edge
is always-on. A degraded/loose-only edge becomes a targeted alternative.

Run from anywhere: output goes next to this file.
"""

import json
from pathlib import Path

OUTDIR = Path(__file__).resolve().parent

LEDGER = []
def log(tag, item, note):
    LEDGER.append({"tag": tag, "item": item, "note": note})

# ---------------------------------------------------------------
# v2.5 structure (verbatim from compute_rir_v2_5.py, hand-verified)
# ---------------------------------------------------------------
SOURCES = ['hpq', 'si_wafers', 'rare_earths', 'germanium', 'ultrapure_water']
SINKS = ['openai_api', 'anthropic_api', 'gemini_api', 'meta_llama']
ADVANCED_FABS = ['tsmc_advanced', 'samsung_foundry', 'intel_foundry']
WESTERN_DESIGN = ['nvidia_gpu', 'broadcom_asic', 'net_silicon']
FRONTIER_PKGS = ['cowos']
SRV_NODES = ['foxconn', 'quanta', 'wistron', 'supermicro', 'dell_hpe']
CLOUD_NODES = ['aws', 'azure', 'gcp', 'oracle_cloud']

NODE_NAMES = {
    'hpq': 'High-Purity Quartz (Spruce Pine)', 'si_wafers': 'Silicon Wafers (Shin-Etsu/Sumco)',
    'rare_earths': 'Rare Earth Elements', 'germanium': 'Germanium', 'ultrapure_water': 'Ultrapure Water',
    'photoresists': 'Photoresists (JSR/TOK/Fujifilm)', 'cmp_slurries': 'CMP Slurries',
    'specialty_gases': 'Specialty Gases (Ne, F2)', 'abf_substrate': 'ABF Substrate (Ajinomoto)',
    'copper_foil': 'Copper Foil', 'glass_fiber': 'Glass Fiber', 'fluorochemistry': 'Fluorochemistry (EUV resists)',
    'purity_chemicals': '11N Purity Chemicals', 'asml_euv': 'ASML EUV Lithography',
    'zeiss_optics': 'Zeiss EUV Optics', 'trumpf_source': 'TRUMPF EUV Light Source',
    'applied_mat': 'Applied Materials (Deposition/Etch)', 'lam_kla': 'Lam Research / KLA (Etch/Metrology)',
    'nvidia_gpu': 'Nvidia GPU Design', 'eda_software': 'EDA Software (Synopsys/Cadence)',
    'arm_ip': 'ARM Processor IP', 'broadcom_asic': 'Broadcom Custom ASIC Design',
    'china_design': 'Chinese Design Ecosystem', 'tsmc_advanced': 'TSMC Advanced Logic (sub-5nm)',
    'samsung_foundry': 'Samsung Foundry', 'intel_foundry': 'Intel Foundry', 'smic_mature': 'SMIC (Mature Nodes)',
    'sk_hynix_hbm': 'SK Hynix HBM', 'samsung_hbm': 'Samsung HBM', 'micron_hbm': 'Micron DRAM/HBM',
    'cowos': 'CoWoS Advanced Packaging (TSMC)', 'osat_ase': 'OSAT ASE/SPIL', 'osat_amkor': 'OSAT Amkor',
    'net_silicon': 'Networking Silicon (Broadcom/Marvell)', 'optical_xcvr': 'Optical Transceivers (Coherent)',
    'fiber_optic': 'Fiber Optic Cable (Corning)', 'foxconn': 'Foxconn (Hon Hai)', 'quanta': 'Quanta Computer',
    'wistron': 'Wistron / Inventec', 'supermicro': 'Super Micro Computer', 'dell_hpe': 'Dell / HPE',
    'vertiv': 'Vertiv (Power/Thermal)', 'schneider': 'Schneider Electric (Power/Thermal)',
    'eaton': 'Eaton (Power Distribution)', 'aws': 'AWS', 'azure': 'Microsoft Azure',
    'gcp': 'Google Cloud Platform', 'oracle_cloud': 'Oracle Cloud', 'openai_api': 'OpenAI API',
    'anthropic_api': 'Anthropic API', 'gemini_api': 'Google Gemini API', 'meta_llama': 'Meta Llama (Self-Hosted)',
}

# v2.5 AND_DEPS (verbatim, INCLUDING the wafers group the earlier port dropped)
AND_DEPS = {
    'tsmc_advanced': {'euv': ['asml_euv'], 'etch': ['applied_mat', 'lam_kla'], 'resist': ['photoresists'],
        'slurry': ['cmp_slurries'], 'gases': ['specialty_gases'], 'chemicals': ['purity_chemicals'],
        'water': ['ultrapure_water'], 'wafers': ['si_wafers'], 'design': WESTERN_DESIGN},
    'samsung_foundry': {'euv': ['asml_euv'], 'etch': ['applied_mat', 'lam_kla'], 'resist': ['photoresists'],
        'slurry': ['cmp_slurries'], 'gases': ['specialty_gases'], 'chemicals': ['purity_chemicals'],
        'water': ['ultrapure_water'], 'wafers': ['si_wafers'], 'design': WESTERN_DESIGN},
    'intel_foundry': {'euv': ['asml_euv'], 'etch': ['applied_mat', 'lam_kla'], 'resist': ['photoresists'],
        'slurry': ['cmp_slurries'], 'gases': ['specialty_gases'], 'chemicals': ['purity_chemicals'],
        'water': ['ultrapure_water'], 'wafers': ['si_wafers'], 'design': WESTERN_DESIGN},
    'smic_mature': {'etch': ['applied_mat', 'lam_kla'], 'resist': ['photoresists'], 'slurry': ['cmp_slurries'],
        'gases': ['specialty_gases'], 'chemicals': ['purity_chemicals'], 'water': ['ultrapure_water'],
        'wafers': ['si_wafers'], 'design': ['china_design']},
    'asml_euv': {'optics': ['zeiss_optics'], 'source': ['trumpf_source']},
    'cowos': {'fab_input': ['tsmc_advanced', 'samsung_foundry', 'intel_foundry'],
        'hbm': ['sk_hynix_hbm', 'samsung_hbm', 'micron_hbm'], 'substrate': ['abf_substrate']},
}

# Full v2.5 edge list (u, v, threshold) — 151 edges, verbatim
EDGES = [
    ('hpq','si_wafers','strict'),('hpq','glass_fiber','strict'),('hpq','purity_chemicals','strict'),
    ('rare_earths','specialty_gases','strict'),('rare_earths','vertiv','strict'),('rare_earths','schneider','strict'),
    ('germanium','optical_xcvr','strict'),('germanium','fiber_optic','strict'),
    ('ultrapure_water','tsmc_advanced','strict'),('ultrapure_water','samsung_foundry','strict'),
    ('ultrapure_water','intel_foundry','strict'),('ultrapure_water','smic_mature','strict'),
    ('fluorochemistry','photoresists','strict'),
    # v2.5: silicon wafers as fab prerequisite
    ('si_wafers','tsmc_advanced','strict'),('si_wafers','samsung_foundry','strict'),
    ('si_wafers','intel_foundry','strict'),('si_wafers','smic_mature','strict'),
    ('photoresists','tsmc_advanced','strict'),('photoresists','samsung_foundry','strict'),
    ('photoresists','intel_foundry','strict'),('photoresists','smic_mature','strict'),
    ('cmp_slurries','tsmc_advanced','strict'),('cmp_slurries','samsung_foundry','strict'),
    ('cmp_slurries','intel_foundry','strict'),('cmp_slurries','smic_mature','strict'),
    ('specialty_gases','tsmc_advanced','strict'),('specialty_gases','samsung_foundry','strict'),
    ('specialty_gases','intel_foundry','strict'),('specialty_gases','smic_mature','strict'),
    ('purity_chemicals','tsmc_advanced','strict'),('purity_chemicals','samsung_foundry','strict'),
    ('purity_chemicals','intel_foundry','strict'),('purity_chemicals','smic_mature','strict'),
    ('abf_substrate','cowos','strict'),('abf_substrate','osat_ase','strict'),('abf_substrate','osat_amkor','strict'),
    ('copper_foil','cowos','strict'),('copper_foil','osat_ase','strict'),('copper_foil','osat_amkor','strict'),
    ('zeiss_optics','asml_euv','strict'),('trumpf_source','asml_euv','strict'),
    ('asml_euv','tsmc_advanced','strict'),('asml_euv','samsung_foundry','strict'),('asml_euv','intel_foundry','strict'),
    ('applied_mat','tsmc_advanced','strict'),('applied_mat','samsung_foundry','strict'),
    ('applied_mat','intel_foundry','strict'),('applied_mat','smic_mature','strict'),
    ('lam_kla','tsmc_advanced','strict'),('lam_kla','samsung_foundry','strict'),
    ('lam_kla','intel_foundry','strict'),('lam_kla','smic_mature','strict'),
    ('eda_software','nvidia_gpu','strict'),('eda_software','broadcom_asic','strict'),('eda_software','net_silicon','strict'),
    ('arm_ip','broadcom_asic','strict'),('arm_ip','net_silicon','strict'),
    ('nvidia_gpu','tsmc_advanced','strict'),('broadcom_asic','tsmc_advanced','strict'),('net_silicon','tsmc_advanced','strict'),
    ('china_design','smic_mature','strict'),
    ('tsmc_advanced','cowos','strict'),('tsmc_advanced','osat_ase','strict'),('tsmc_advanced','osat_amkor','strict'),
    ('samsung_foundry','osat_ase','strict'),('samsung_foundry','osat_amkor','strict'),
    ('intel_foundry','osat_ase','strict'),('intel_foundry','osat_amkor','strict'),
    ('si_wafers','sk_hynix_hbm','strict'),('si_wafers','samsung_hbm','strict'),('si_wafers','micron_hbm','strict'),
    ('sk_hynix_hbm','cowos','strict'),('samsung_hbm','cowos','strict'),('micron_hbm','cowos','strict'),
    ('sk_hynix_hbm','osat_ase','strict'),('samsung_hbm','osat_ase','strict'),('micron_hbm','osat_ase','strict'),
    ('glass_fiber','fiber_optic','strict'),
    ('cowos','foxconn','strict'),('cowos','quanta','strict'),('cowos','supermicro','strict'),
    ('osat_ase','foxconn','strict'),('osat_ase','quanta','strict'),('osat_ase','wistron','strict'),
    ('osat_ase','supermicro','strict'),('osat_ase','dell_hpe','strict'),
    ('osat_amkor','foxconn','strict'),('osat_amkor','quanta','strict'),('osat_amkor','dell_hpe','strict'),
    ('optical_xcvr','foxconn','strict'),('optical_xcvr','quanta','strict'),('optical_xcvr','supermicro','strict'),
    ('fiber_optic','foxconn','strict'),('fiber_optic','quanta','strict'),
    ('vertiv','aws','strict'),('vertiv','azure','strict'),('vertiv','gcp','strict'),('vertiv','oracle_cloud','strict'),
    ('schneider','aws','strict'),('schneider','azure','strict'),('schneider','gcp','strict'),('schneider','oracle_cloud','strict'),
    ('eaton','aws','strict'),('eaton','azure','strict'),('eaton','gcp','strict'),
    ('foxconn','aws','strict'),('foxconn','azure','strict'),('foxconn','gcp','strict'),
    ('quanta','aws','strict'),('quanta','azure','strict'),('quanta','gcp','strict'),('quanta','oracle_cloud','strict'),
    ('wistron','azure','strict'),('wistron','oracle_cloud','strict'),
    ('supermicro','aws','strict'),('supermicro','azure','strict'),('supermicro','gcp','strict'),('supermicro','oracle_cloud','strict'),
    ('dell_hpe','aws','strict'),('dell_hpe','azure','strict'),('dell_hpe','oracle_cloud','strict'),
    ('azure','openai_api','strict'),('aws','anthropic_api','strict'),('gcp','anthropic_api','strict'),
    ('gcp','gemini_api','strict'),('aws','meta_llama','strict'),('azure','meta_llama','strict'),
    ('gcp','meta_llama','strict'),('oracle_cloud','meta_llama','strict'),
    # degraded
    ('nvidia_gpu','samsung_foundry','degraded'),('nvidia_gpu','intel_foundry','degraded'),
    ('broadcom_asic','samsung_foundry','degraded'),('broadcom_asic','intel_foundry','degraded'),
    ('net_silicon','samsung_foundry','degraded'),('net_silicon','intel_foundry','degraded'),
    ('samsung_foundry','cowos','degraded'),('intel_foundry','cowos','degraded'),
    ('micron_hbm','osat_amkor','degraded'),
    ('azure','anthropic_api','degraded'),('oracle_cloud','openai_api','degraded'),
    ('aws','openai_api','degraded'),('gcp','openai_api','degraded'),
    ('osat_amkor','wistron','degraded'),('osat_amkor','supermicro','degraded'),('eaton','oracle_cloud','degraded'),
    # loose
    ('smic_mature','osat_ase','loose'),('smic_mature','osat_amkor','loose'),
    ('oracle_cloud','anthropic_api','loose'),('oracle_cloud','gemini_api','loose'),
    ('aws','gemini_api','loose'),('azure','gemini_api','loose'),
]

TAU = {'strict': 0, 'degraded': 12, 'loose': 24}
ALL_NODES = set(NODE_NAMES.keys())

log("preserved", "node set", "All 52 v2.5 nodes verbatim including china_design.")
log("preserved", "wafers group", "Restored: every fab AND_DEPS includes wafers:{si_wafers}, and the four si_wafers->fab strict edges. (Dropped in the prior port; this is P1 fix #1.)")
log("preserved", "AND_DEPS", "Per-fab euv/etch/resist/slurry/gases/chemicals/water/wafers/design; ASML optics+source; CoWoS fab+hbm+substrate as identified groups.")
log("changed", "thresholds->activation_time", "strict/degraded/loose -> tau 0/12/24; strict edge always-on; degraded/loose-only edge becomes a targeted alternative.")

def preds_at(levels):
    m = {}
    for (u, v, t) in EDGES:
        if t in levels:
            m.setdefault(v, set()).add(u)
    return m

strict_preds = preds_at({'strict'})

# v2.5 cascade fidelity: v2.5's check_and_deps cascades a node ONLY if it is an
# AND_DEPS key. Every other node "passes through" (reachability-only, no liveness
# cascade). The frozen v0.1 engine has one edge mechanism: an edge exists in the
# reachability graph iff it is a dependency any_of membership or an alternative,
# and ANY rendered dependency also imposes a liveness cascade. So a pure
# connectivity edge cannot be rendered without also creating a cascade.
#
# Four v2.5 strict edges from two upstream node families are pure connectivity that
# v2.5 does NOT cascade, and rendering them fabricates criticality (verified against
# the v2.5 source, which reports both families at 0/0/0 on every metric):
#   - copper_foil -> cowos, copper_foil -> osat_ase, copper_foil -> osat_amkor
#     (copper_foil is not in any declared AND group of those targets)
#   - fluorochemistry -> photoresists  (photoresists is not an AND_DEPS key)
# These are NOT rendered as dependencies. Their downstream targets stay
# reachable/satisfiable via other rendered paths (cowos via its fab_input/hbm/
# substrate groups; photoresists via being an any_of member of every fab's resist
# group), so no source->sink path is lost. Each dropped strict edge is logged
# `unsupported` because v0.1 has no connectivity-only relation.
#
# This set is explicit and verified against v2.5 output, not auto-derived, to avoid
# over-dropping load-bearing downstream nodes (e.g. osat_amkor, which is an
# alternative target and must keep its dependency).
NON_CASCADING_UPSTREAM = {'copper_foil', 'fluorochemistry'}

AND_KEYS = set(AND_DEPS.keys())

dependencies = {}
group_membership = {}

for node in sorted(ALL_NODES):
    # Outcome sources are independent origins in the v2.5 case. Preserve their
    # incoming edges in the parity inventory, but do not render dependencies for
    # them; the hpq->si_wafers disposition below records that translation.
    if node in SOURCES:
        continue
    if node in AND_DEPS:
        groups, gm = [], {}
        sp = strict_preds.get(node, set())
        for gid, members in AND_DEPS[node].items():
            strict_members = [m for m in members if m in sp]
            if not strict_members:
                strict_members = list(members)
                log("changed", f"{node}.{gid} group",
                    f"No strict edge satisfies {node}'s '{gid}' (arrives via degraded/loose). "
                    f"Modeled as tau-0 satisfiable by {strict_members}; the served_sinks/alternative "
                    f"contract cannot defer a baseline requirement without a present satisfier.")
            groups.append({"id": gid, "any_of": strict_members})
            for m in strict_members:
                gm[m] = gid
        # Strict predecessors of an AND node NOT in a declared v2.5 group (e.g.
        # copper_foil->cowos) are deliberately not added; v2.5 ignores them and
        # rendering them (as an aux AND group) previously fabricated criticality.
        dependencies[node] = {"logic": "AND", "requirements": groups}
        group_membership[node] = gm
    else:
        sp = sorted(p for p in strict_preds.get(node, set())
                    if p not in NON_CASCADING_UPSTREAM)
        if not sp:
            continue
        dependencies[node] = {"logic": "OR", "requirements": [{"id": "in", "any_of": sp}]}
        group_membership[node] = {m: "in" for m in sp}

# Log the dropped upstream connectivity edges as unsupported.
for (u, v, t) in EDGES:
    if t == 'strict' and u in NON_CASCADING_UPSTREAM:
        log("unsupported", f"edge {u}->{v} @strict",
            f"v2.5 has this strict edge but does not cascade {u} (it is a non-load-bearing "
            f"upstream input; v2.5 reports {u} at 0/0/0). v0.1 has no connectivity-only "
            f"relation, so the edge is not rendered and {u} is correctly non-critical. "
            f"{v} stays reachable/satisfiable via its rendered groups, so no source->sink "
            f"path is lost.")
# Also log copper_foil->cowos specifically as the corrected P1 (it is covered above,
# but call it out for the audit trail).
log("changed", "copper_foil aux-group removed",
    "Prior port rendered copper_foil as an auxiliary AND group of cowos, making it "
    "mandatory and fabricating copper_foil frontier-persistence [4,4,4]. v2.5 reports "
    "copper_foil 0/0/0. The aux group is removed; copper_foil is now correctly [0,0,0].")

# NOTE: si_wafers is a SOURCE but also has hpq->si_wafers strict edge. In v2.5 the
# outcome sources include si_wafers as an independent origin, so si_wafers has no
# dependency (a source is always available). We PRESERVE the hpq->si_wafers edge in
# the edge inventory for parity accounting but do NOT make si_wafers depend on hpq,
# matching v2.5 where sources are independent origins.
log("changed", "hpq->si_wafers edge",
    "Present in v2.5 edge list but si_wafers is a declared source (independent origin). "
    "Edge retained in inventory for parity count; not rendered as a dependency, matching v2.5 "
    "source semantics. This is the only strict edge unrendered for SOURCE-SEMANTICS reasons; "
    "the copper_foil and fluorochemistry strict edges are also intentionally unrendered, but for "
    "a different reason (non-cascading upstream connectivity), and are logged 'unsupported'.")

alternatives = []
for (u, v, t) in EDGES:
    if t == 'strict':
        continue
    at = TAU[t]
    gm = group_membership.get(v, {})
    gid = gm.get(u)
    if gid is None:
        if v in AND_DEPS:
            if u in WESTERN_DESIGN: gid = 'design'
            elif u in ('samsung_foundry','intel_foundry') and v == 'cowos': gid = 'fab_input'
            elif u == 'micron_hbm' and v == 'cowos': gid = 'hbm'
            else: gid = None
        else:
            gid = 'in'
    if gid is None:
        log("unsupported", f"edge {u}->{v} @{t}", "Could not map to a requirement group; skipped.")
        continue
    # Log EVERY alternative individually (the earlier ledger omitted the six
    # Samsung/Intel design alternatives). If u already satisfies gid at tau-0
    # (design members promoted by the empty-group fallback), flag it redundant.
    redundant = gm.get(u) == gid
    note = f"{u} added as timed substitute into group '{gid}' of {v} (was {t} edge)."
    if redundant:
        note += (" NOTE: redundant — this node already satisfies the group at tau-0 "
                 "via the empty-group fallback; retained for edge parity.")
    log("new", f"alt {u}->{v} @tau{at}", note)
    alternatives.append({"target": v, "requirement_id": gid, "replacement": u,
                         "activation_time": at, "source": f"v2.5 {t} edge {u}->{v}"})

# dedupe
seen, uniq = set(), []
for a in alternatives:
    k = (a['target'], a['requirement_id'], a['replacement'], a['activation_time'])
    if k not in seen:
        seen.add(k); uniq.append(a)
alternatives = uniq
log("new", "alternatives total", f"{len(alternatives)} timed alternatives generated from degraded/loose edges "
    f"(includes the six Samsung/Intel design alternatives).")

node_list = [{"id": n, "label": NODE_NAMES[n],
              "type": ("source" if n in SOURCES else "sink" if n in SINKS else "internal")}
             for n in sorted(ALL_NODES)]
dep_list = [{"target": t, "logic": d["logic"], "requirements": d["requirements"]}
            for t, d in sorted(dependencies.items())]

def base(name, desc, outcome):
    return {"version": "0.1", "name": name, "description": desc,
            "nodes": node_list, "dependencies": dep_list, "alternatives": alternatives,
            "outcome": outcome, "horizons": [0, 12, 24]}

# Mission 1: topology
topo = base("ai_compute_topology",
    "AI compute supply chain, topology mission: a sink is served if ANY source reaches it (SMIC mature paths count).",
    {"type": "served_sinks", "sources": SOURCES, "sinks": SINKS})

# Mission 2 (PRIMARY): frontier stack — source -> adv fab -> cowos -> server -> cloud -> sink
log("changed", "frontier stack -> ordered waypoints",
    "v2.5 PRIMARY frontier metric (src->adv_fab->cowos->server->cloud->sink) expressed as "
    "ordered_served_sinks with four waypoint groups: [advanced_fabs], [cowos], [servers], [clouds].")
stack = base("ai_compute_frontier_stack",
    "AI compute, PRIMARY frontier mission: a sink counts only if reached via advanced fab -> CoWoS -> server -> cloud. Matches v2.5 stack metric.",
    {"type": "ordered_served_sinks", "sources": SOURCES, "sinks": SINKS,
     "waypoints": [ADVANCED_FABS, FRONTIER_PKGS, SRV_NODES, CLOUD_NODES]})

# Mission 3 (SECONDARY): frontier fab-only
log("changed", "frontier fab_only -> single waypoint",
    "v2.5 SECONDARY sensitivity metric (src->adv_fab->sink) expressed as ordered_served_sinks with one waypoint group [advanced_fabs].")
fab_only = base("ai_compute_frontier_fab_only",
    "AI compute, SECONDARY frontier mission: a sink counts if reached via any advanced fab (no packaging/server/cloud constraint). Matches v2.5 fab_only sensitivity metric.",
    {"type": "ordered_served_sinks", "sources": SOURCES, "sinks": SINKS, "waypoints": [ADVANCED_FABS]})

for fname, model in [("model_topology.json", topo),
                     ("model_frontier_stack.json", stack),
                     ("model_frontier_fab_only.json", fab_only)]:
    (OUTDIR / fname).write_text(json.dumps(model, indent=2))
(OUTDIR / "parity_ledger.json").write_text(json.dumps(LEDGER, indent=2))

# Edge parity accounting
strict_edges = [(u,v) for (u,v,t) in EDGES if t=='strict']
print(f"nodes: {len(node_list)}  deps: {len(dep_list)}  alternatives: {len(alternatives)}")
print(f"total v2.5 edges: {len(EDGES)}  strict: {len(strict_edges)}  ledger: {len(LEDGER)}")
print("wrote model_topology.json, model_frontier_stack.json, model_frontier_fab_only.json, parity_ledger.json")
