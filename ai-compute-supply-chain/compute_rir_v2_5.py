#!/usr/bin/env python3
"""
Compute Dependency Algebra: Substitutability Curve Analysis — V2.5
==================================================================
Changes from V2.4:
  1. Silicon wafers added as explicit fab AND-dependency + edges.
  2. Frontier metric redefined as ordered end-to-end stack:
     source → advanced_fab → cowos → server → cloud → sink
     (was: source → advanced_fab → sink, ignoring packaging)
  3. Audit block with hard acceptance tests.
  4. Sensitivity comparison: fab-only frontier vs stack frontier.

Author: Amadeus Brandes
Date: April 2026
Resolution: 52 nodes
"""

import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CHART = os.path.join(SCRIPT_DIR, 'euv_corridor_v2_5.png')
OUT_JSON  = os.path.join(SCRIPT_DIR, 'rir_v2_5.json')

# ============================================================
# NODE DEFINITIONS (52 nodes)
# ============================================================

nodes = {
    # --- Sources: Raw Resources ---
    'hpq':              {'name': 'High-Purity Quartz (Spruce Pine)',     'layer': -2, 'cat': 'raw'},
    'si_wafers':        {'name': 'Silicon Wafers (Shin-Etsu/Sumco)',     'layer': -2, 'cat': 'raw'},
    'rare_earths':      {'name': 'Rare Earth Elements',                  'layer': -2, 'cat': 'raw'},
    'germanium':        {'name': 'Germanium',                            'layer': -2, 'cat': 'raw'},
    'ultrapure_water':  {'name': 'Ultrapure Water',                      'layer': -2, 'cat': 'raw'},

    # --- Chemistry & Materials ---
    'photoresists':     {'name': 'Photoresists (JSR/TOK/Fujifilm)',      'layer': 0,  'cat': 'chem'},
    'cmp_slurries':     {'name': 'CMP Slurries',                         'layer': 0,  'cat': 'chem'},
    'specialty_gases':  {'name': 'Specialty Gases (Ne, F₂)',             'layer': 0,  'cat': 'chem'},
    'abf_substrate':    {'name': 'ABF Substrate (Ajinomoto)',            'layer': 0,  'cat': 'chem'},
    'copper_foil':      {'name': 'Copper Foil',                          'layer': 0,  'cat': 'chem'},
    'glass_fiber':      {'name': 'Glass Fiber',                          'layer': 0,  'cat': 'chem'},
    'fluorochemistry':  {'name': 'Fluorochemistry (EUV resists)',        'layer': -1, 'cat': 'chem'},
    'purity_chemicals': {'name': '11N Purity Chemicals',                 'layer': -1, 'cat': 'chem'},

    # --- Equipment ---
    'asml_euv':         {'name': 'ASML EUV Lithography',                 'layer': 2,  'cat': 'equip'},
    'zeiss_optics':     {'name': 'Zeiss EUV Optics',                     'layer': 2,  'cat': 'equip'},
    'trumpf_source':    {'name': 'TRUMPF EUV Light Source',              'layer': 2,  'cat': 'equip'},
    'applied_mat':      {'name': 'Applied Materials (Deposition/Etch)',   'layer': 2,  'cat': 'equip'},
    'lam_kla':          {'name': 'Lam Research / KLA (Etch/Metrology)',   'layer': 2,  'cat': 'equip'},

    # --- Design & IP ---
    'nvidia_gpu':       {'name': 'Nvidia GPU Design',                    'layer': 1,  'cat': 'design'},
    'eda_software':     {'name': 'EDA Software (Synopsys/Cadence)',      'layer': 1,  'cat': 'design'},
    'arm_ip':           {'name': 'ARM Processor IP',                     'layer': 1,  'cat': 'design'},
    'broadcom_asic':    {'name': 'Broadcom Custom ASIC Design',          'layer': 1,  'cat': 'design'},
    # v2.4: Chinese/domestic design ecosystem (HiSilicon, UNISOC, etc.)
    'china_design':     {'name': 'Chinese Design Ecosystem',             'layer': 1,  'cat': 'design'},

    # --- Fabrication ---
    'tsmc_advanced':    {'name': 'TSMC Advanced Logic (sub-5nm)',        'layer': 3,  'cat': 'fab'},
    'samsung_foundry':  {'name': 'Samsung Foundry',                      'layer': 3,  'cat': 'fab'},
    'intel_foundry':    {'name': 'Intel Foundry',                        'layer': 3,  'cat': 'fab'},
    'smic_mature':      {'name': 'SMIC (Mature Nodes)',                  'layer': 3,  'cat': 'fab'},

    # --- Memory ---
    'sk_hynix_hbm':    {'name': 'SK Hynix HBM',                         'layer': 4,  'cat': 'mem'},
    'samsung_hbm':     {'name': 'Samsung HBM',                           'layer': 4,  'cat': 'mem'},
    'micron_hbm':      {'name': 'Micron DRAM/HBM',                       'layer': 4,  'cat': 'mem'},

    # --- Packaging & Test ---
    'cowos':            {'name': 'Advanced 2.5D Packaging',              'layer': 3,  'cat': 'pkg'},
    'osat_ase':         {'name': 'OSAT ASE/SPIL',                        'layer': 3,  'cat': 'pkg'},
    'osat_amkor':       {'name': 'OSAT Amkor',                           'layer': 3,  'cat': 'pkg'},

    # --- Networking ---
    'net_silicon':      {'name': 'Networking Silicon (Broadcom/Marvell)','layer': 1,  'cat': 'net'},
    'optical_xcvr':     {'name': 'Optical Transceivers (Coherent)',      'layer': 4,  'cat': 'net'},
    'fiber_optic':      {'name': 'Fiber Optic Cable (Corning)',          'layer': 4,  'cat': 'net'},

    # --- Server Integration ---
    'foxconn':          {'name': 'Foxconn (Hon Hai)',                     'layer': 5,  'cat': 'srv'},
    'quanta':           {'name': 'Quanta Computer',                       'layer': 5,  'cat': 'srv'},
    'wistron':          {'name': 'Wistron / Inventec',                    'layer': 5,  'cat': 'srv'},
    'supermicro':       {'name': 'Super Micro Computer',                  'layer': 5,  'cat': 'srv'},
    'dell_hpe':         {'name': 'Dell / HPE',                            'layer': 5,  'cat': 'srv'},
    'vertiv':           {'name': 'Vertiv (Power/Thermal)',                'layer': 5,  'cat': 'srv'},
    'schneider':        {'name': 'Schneider Electric (Power/Thermal)',    'layer': 5,  'cat': 'srv'},
    'eaton':            {'name': 'Eaton (Power Distribution)',            'layer': 5,  'cat': 'srv'},

    # --- Cloud ---
    'aws':              {'name': 'AWS',                                   'layer': 5,  'cat': 'cloud'},
    'azure':            {'name': 'Microsoft Azure',                       'layer': 5,  'cat': 'cloud'},
    'gcp':              {'name': 'Google Cloud Platform',                 'layer': 5,  'cat': 'cloud'},
    'oracle_cloud':     {'name': 'Oracle Cloud',                          'layer': 5,  'cat': 'cloud'},

    # --- Inference Endpoints ---
    'openai_api':       {'name': 'OpenAI API',                            'layer': 6,  'cat': 'api'},
    'anthropic_api':    {'name': 'Anthropic API',                         'layer': 6,  'cat': 'api'},
    'gemini_api':       {'name': 'Google Gemini API',                     'layer': 6,  'cat': 'api'},
    'meta_llama':       {'name': 'Meta Llama (Self-Hosted)',              'layer': 6,  'cat': 'api'},
}

SOURCES = ['hpq', 'si_wafers', 'rare_earths', 'germanium', 'ultrapure_water']
SINKS   = ['openai_api', 'anthropic_api', 'gemini_api', 'meta_llama']
ADVANCED_FABS = ['tsmc_advanced', 'samsung_foundry', 'intel_foundry']

# ============================================================
# AND-DEPENDENCY DEFINITIONS — V2.5
# ============================================================
# Design requirements are now PER-FAB inside AND_DEPS.
# No more blanket FAB_NODES design check.
# SMIC explicitly requires china_design (stated assumption).
# Western fabs require at least one Western design input.

WESTERN_DESIGN = {'nvidia_gpu', 'broadcom_asic', 'net_silicon'}

AND_DEPS = {
    'tsmc_advanced': {
        'euv':        {'asml_euv'},
        'etch':       {'applied_mat', 'lam_kla'},
        'resist':     {'photoresists'},
        'slurry':     {'cmp_slurries'},
        'gases':      {'specialty_gases'},
        'chemicals':  {'purity_chemicals'},
        'water':      {'ultrapure_water'},
        'wafers':     {'si_wafers'},                        # v2.5: explicit
        'design':     WESTERN_DESIGN,
    },
    'samsung_foundry': {
        'euv':        {'asml_euv'},
        'etch':       {'applied_mat', 'lam_kla'},
        'resist':     {'photoresists'},
        'slurry':     {'cmp_slurries'},
        'gases':      {'specialty_gases'},
        'chemicals':  {'purity_chemicals'},
        'water':      {'ultrapure_water'},
        'wafers':     {'si_wafers'},                        # v2.5: explicit
        'design':     WESTERN_DESIGN,
    },
    'intel_foundry': {
        'euv':        {'asml_euv'},
        'etch':       {'applied_mat', 'lam_kla'},
        'resist':     {'photoresists'},
        'slurry':     {'cmp_slurries'},
        'gases':      {'specialty_gases'},
        'chemicals':  {'purity_chemicals'},
        'water':      {'ultrapure_water'},
        'wafers':     {'si_wafers'},                        # v2.5: explicit
        'design':     WESTERN_DESIGN,
    },
    'smic_mature': {
        # No EUV (export controlled)
        'etch':       {'applied_mat', 'lam_kla'},
        'resist':     {'photoresists'},
        'slurry':     {'cmp_slurries'},
        'gases':      {'specialty_gases'},
        'chemicals':  {'purity_chemicals'},
        'water':      {'ultrapure_water'},
        'wafers':     {'si_wafers'},                        # v2.5: explicit
        'design':     {'china_design'},
    },
    'asml_euv': {
        'optics':     {'zeiss_optics'},
        'source':     {'trumpf_source'},
    },
    'cowos': {
        'fab_input':  {'tsmc_advanced', 'samsung_foundry', 'intel_foundry'},
        'hbm':        {'sk_hynix_hbm', 'samsung_hbm', 'micron_hbm'},
        'substrate':  {'abf_substrate'},
    },
}

# ============================================================
# EDGES
# ============================================================

edges_all = [
    # ===================== STRICT =====================
    ('hpq', 'si_wafers', 'strict'),
    ('hpq', 'glass_fiber', 'strict'),
    ('hpq', 'purity_chemicals', 'strict'),
    ('rare_earths', 'specialty_gases', 'strict'),
    ('rare_earths', 'vertiv', 'strict'),
    ('rare_earths', 'schneider', 'strict'),
    ('germanium', 'optical_xcvr', 'strict'),
    ('germanium', 'fiber_optic', 'strict'),
    ('ultrapure_water', 'tsmc_advanced', 'strict'),
    ('ultrapure_water', 'samsung_foundry', 'strict'),
    ('ultrapure_water', 'intel_foundry', 'strict'),
    ('ultrapure_water', 'smic_mature', 'strict'),
    # v2.5: silicon wafers as fab prerequisite
    ('si_wafers', 'tsmc_advanced', 'strict'),
    ('si_wafers', 'samsung_foundry', 'strict'),
    ('si_wafers', 'intel_foundry', 'strict'),
    ('si_wafers', 'smic_mature', 'strict'),
    ('fluorochemistry', 'photoresists', 'strict'),

    # CHEM → FAB
    ('photoresists', 'tsmc_advanced', 'strict'),
    ('photoresists', 'samsung_foundry', 'strict'),
    ('photoresists', 'intel_foundry', 'strict'),
    ('photoresists', 'smic_mature', 'strict'),
    ('cmp_slurries', 'tsmc_advanced', 'strict'),
    ('cmp_slurries', 'samsung_foundry', 'strict'),
    ('cmp_slurries', 'intel_foundry', 'strict'),
    ('cmp_slurries', 'smic_mature', 'strict'),
    ('specialty_gases', 'tsmc_advanced', 'strict'),
    ('specialty_gases', 'samsung_foundry', 'strict'),
    ('specialty_gases', 'intel_foundry', 'strict'),
    ('specialty_gases', 'smic_mature', 'strict'),
    ('purity_chemicals', 'tsmc_advanced', 'strict'),
    ('purity_chemicals', 'samsung_foundry', 'strict'),
    ('purity_chemicals', 'intel_foundry', 'strict'),
    ('purity_chemicals', 'smic_mature', 'strict'),

    # CHEM → PKG
    ('abf_substrate', 'cowos', 'strict'),
    ('abf_substrate', 'osat_ase', 'strict'),
    ('abf_substrate', 'osat_amkor', 'strict'),
    ('copper_foil', 'cowos', 'strict'),
    ('copper_foil', 'osat_ase', 'strict'),
    ('copper_foil', 'osat_amkor', 'strict'),

    # EUV corridor
    ('zeiss_optics', 'asml_euv', 'strict'),
    ('trumpf_source', 'asml_euv', 'strict'),

    # EQUIP → FAB
    ('asml_euv', 'tsmc_advanced', 'strict'),
    ('asml_euv', 'samsung_foundry', 'strict'),
    ('asml_euv', 'intel_foundry', 'strict'),
    ('applied_mat', 'tsmc_advanced', 'strict'),
    ('applied_mat', 'samsung_foundry', 'strict'),
    ('applied_mat', 'intel_foundry', 'strict'),
    ('applied_mat', 'smic_mature', 'strict'),
    ('lam_kla', 'tsmc_advanced', 'strict'),
    ('lam_kla', 'samsung_foundry', 'strict'),
    ('lam_kla', 'intel_foundry', 'strict'),
    ('lam_kla', 'smic_mature', 'strict'),

    # DESIGN → FAB
    ('eda_software', 'nvidia_gpu', 'strict'),
    ('eda_software', 'broadcom_asic', 'strict'),
    ('eda_software', 'net_silicon', 'strict'),
    ('arm_ip', 'broadcom_asic', 'strict'),
    ('arm_ip', 'net_silicon', 'strict'),
    ('nvidia_gpu', 'tsmc_advanced', 'strict'),
    ('broadcom_asic', 'tsmc_advanced', 'strict'),
    ('net_silicon', 'tsmc_advanced', 'strict'),
    # v2.5: Chinese design ecosystem feeds SMIC
    ('china_design', 'smic_mature', 'strict'),

    # FAB → PKG
    ('tsmc_advanced', 'cowos', 'strict'),
    ('tsmc_advanced', 'osat_ase', 'strict'),
    ('tsmc_advanced', 'osat_amkor', 'strict'),
    ('samsung_foundry', 'osat_ase', 'strict'),
    ('samsung_foundry', 'osat_amkor', 'strict'),
    ('intel_foundry', 'osat_ase', 'strict'),
    ('intel_foundry', 'osat_amkor', 'strict'),

    # MEM
    ('si_wafers', 'sk_hynix_hbm', 'strict'),
    ('si_wafers', 'samsung_hbm', 'strict'),
    ('si_wafers', 'micron_hbm', 'strict'),
    ('sk_hynix_hbm', 'cowos', 'strict'),
    ('samsung_hbm', 'cowos', 'strict'),
    ('micron_hbm', 'cowos', 'strict'),
    ('sk_hynix_hbm', 'osat_ase', 'strict'),
    ('samsung_hbm', 'osat_ase', 'strict'),
    ('micron_hbm', 'osat_ase', 'strict'),

    # NET
    ('glass_fiber', 'fiber_optic', 'strict'),

    # PKG → SRV
    ('cowos', 'foxconn', 'strict'),
    ('cowos', 'quanta', 'strict'),
    ('cowos', 'supermicro', 'strict'),
    ('osat_ase', 'foxconn', 'strict'),
    ('osat_ase', 'quanta', 'strict'),
    ('osat_ase', 'wistron', 'strict'),
    ('osat_ase', 'supermicro', 'strict'),
    ('osat_ase', 'dell_hpe', 'strict'),
    ('osat_amkor', 'foxconn', 'strict'),
    ('osat_amkor', 'quanta', 'strict'),
    ('osat_amkor', 'dell_hpe', 'strict'),

    # NET → SRV
    ('optical_xcvr', 'foxconn', 'strict'),
    ('optical_xcvr', 'quanta', 'strict'),
    ('optical_xcvr', 'supermicro', 'strict'),
    ('fiber_optic', 'foxconn', 'strict'),
    ('fiber_optic', 'quanta', 'strict'),

    # POWER → CLOUD
    ('vertiv', 'aws', 'strict'),
    ('vertiv', 'azure', 'strict'),
    ('vertiv', 'gcp', 'strict'),
    ('vertiv', 'oracle_cloud', 'strict'),
    ('schneider', 'aws', 'strict'),
    ('schneider', 'azure', 'strict'),
    ('schneider', 'gcp', 'strict'),
    ('schneider', 'oracle_cloud', 'strict'),
    ('eaton', 'aws', 'strict'),
    ('eaton', 'azure', 'strict'),
    ('eaton', 'gcp', 'strict'),

    # SRV → CLOUD
    ('foxconn', 'aws', 'strict'),
    ('foxconn', 'azure', 'strict'),
    ('foxconn', 'gcp', 'strict'),
    ('quanta', 'aws', 'strict'),
    ('quanta', 'azure', 'strict'),
    ('quanta', 'gcp', 'strict'),
    ('quanta', 'oracle_cloud', 'strict'),
    ('wistron', 'azure', 'strict'),
    ('wistron', 'oracle_cloud', 'strict'),
    ('supermicro', 'aws', 'strict'),
    ('supermicro', 'azure', 'strict'),
    ('supermicro', 'gcp', 'strict'),
    ('supermicro', 'oracle_cloud', 'strict'),
    ('dell_hpe', 'aws', 'strict'),
    ('dell_hpe', 'azure', 'strict'),
    ('dell_hpe', 'oracle_cloud', 'strict'),

    # CLOUD → API
    ('azure', 'openai_api', 'strict'),
    ('aws', 'anthropic_api', 'strict'),
    ('gcp', 'anthropic_api', 'strict'),
    ('gcp', 'gemini_api', 'strict'),
    ('aws', 'meta_llama', 'strict'),
    ('azure', 'meta_llama', 'strict'),
    ('gcp', 'meta_llama', 'strict'),
    ('oracle_cloud', 'meta_llama', 'strict'),

    # ===================== DEGRADED =====================
    ('nvidia_gpu', 'samsung_foundry', 'degraded'),
    ('nvidia_gpu', 'intel_foundry', 'degraded'),
    ('broadcom_asic', 'samsung_foundry', 'degraded'),
    ('broadcom_asic', 'intel_foundry', 'degraded'),
    ('net_silicon', 'samsung_foundry', 'degraded'),
    ('net_silicon', 'intel_foundry', 'degraded'),
    ('samsung_foundry', 'cowos', 'degraded'),
    ('intel_foundry', 'cowos', 'degraded'),
    ('micron_hbm', 'osat_amkor', 'degraded'),
    ('azure', 'anthropic_api', 'degraded'),
    ('oracle_cloud', 'openai_api', 'degraded'),
    ('aws', 'openai_api', 'degraded'),
    ('gcp', 'openai_api', 'degraded'),
    ('osat_amkor', 'wistron', 'degraded'),
    ('osat_amkor', 'supermicro', 'degraded'),
    ('eaton', 'oracle_cloud', 'degraded'),

    # ===================== LOOSE =====================
    ('smic_mature', 'osat_ase', 'loose'),
    ('smic_mature', 'osat_amkor', 'loose'),
    ('oracle_cloud', 'anthropic_api', 'loose'),
    ('oracle_cloud', 'gemini_api', 'loose'),
    ('aws', 'gemini_api', 'loose'),
    ('azure', 'gemini_api', 'loose'),
]


# ============================================================
# COMPUTATION ENGINE
# ============================================================

THRESHOLDS = ['strict', 'degraded', 'loose']
THRESHOLD_LABELS = {
    'strict':   'Strict (0-3 mo)',
    'degraded': 'Degraded (12 mo)',
    'loose':    'Loose (24 mo)',
}

def build_graph(threshold_level):
    G = nx.DiGraph()
    G.add_nodes_from(nodes.keys())
    include = set()
    for t in THRESHOLDS:
        include.add(t)
        if t == threshold_level:
            break
    for (u, v, t) in edges_all:
        if t in include:
            G.add_edge(u, v)
    return G


def check_and_deps(G, node):
    """Check if node has all required AND-dependency categories satisfied.
    v2.5: Design requirements are inside AND_DEPS per-fab. No blanket check."""
    if node not in AND_DEPS:
        return True
    predecessors = set(G.predecessors(node))
    for cat_name, cat_nodes in AND_DEPS[node].items():
        if not predecessors.intersection(cat_nodes):
            return False
    return True


def remove_node_cascade(G_orig, node_to_remove):
    """Remove node, then cascade AND-dependency failures."""
    G = G_orig.copy()
    G.remove_node(node_to_remove)

    changed = True
    iterations = 0
    while changed and iterations < 30:
        changed = False
        iterations += 1
        for dep_node in AND_DEPS:
            if dep_node not in G or dep_node == node_to_remove:
                continue
            if not check_and_deps(G, dep_node):
                successors = list(G.successors(dep_node))
                if successors:
                    for s in successors:
                        G.remove_edge(dep_node, s)
                    changed = True
    return G


def compute_betti_1(G):
    Gu = G.to_undirected()
    return Gu.number_of_edges() - Gu.number_of_nodes() + nx.number_connected_components(Gu)


def count_reachable(G, sources, sinks):
    return sum(1 for s in sources for t in sinks
               if s in G and t in G and nx.has_path(G, s, t))


def compute_impacts(G, sources, sinks):
    """AND-aware node removal impact. v2.5: symmetric formula + source decomposition.
    For source nodes, reports both total impact and cascade-only impact
    (excluding the trivial loss of that source's own pairs)."""
    baseline = count_reachable(G, sources, sinks)
    impact = {}
    source_decomp = {}  # {node: {'self_loss': N, 'cascade_loss': N}}
    skip = set(sinks)
    for node in G.nodes():
        if node in skip:
            continue
        G_red = remove_node_cascade(G, node)
        remaining = count_reachable(G_red, sources, sinks)
        impact[node] = baseline - remaining

        # Source decomposition
        if node in sources:
            # Self-loss: pairs that originated from this source
            self_loss = sum(1 for t in sinks if nx.has_path(G, node, t))
            # Cascade loss: impact on OTHER sources' pairs
            other_sources = [s for s in sources if s != node]
            other_baseline = count_reachable(G, other_sources, sinks)
            other_remaining = count_reachable(G_red, other_sources, sinks)
            cascade_loss = other_baseline - other_remaining
            source_decomp[node] = {
                'self_loss': self_loss,
                'cascade_loss': cascade_loss,
                'total': self_loss + cascade_loss,
            }

    return impact, baseline, source_decomp


# ============================================================
# FRONTIER METRICS — V2.5
# ============================================================
# Two frontier definitions for sensitivity comparison:
#   fab_only:  source → advanced_fab → sink (v2.5 definition)
#   stack:     source → advanced_fab → cowos → server → cloud → sink (v2.5)

FRONTIER_PKGS = {'cowos'}
SRV_NODES = {'foxconn', 'quanta', 'wistron', 'supermicro', 'dell_hpe'}
CLOUD_NODES = {'aws', 'azure', 'gcp', 'oracle_cloud'}


def count_frontier_fab_only(graph, sources, sinks, advanced_fabs):
    """V2.5 definition: source → advanced_fab → sink."""
    count = 0
    for s in sources:
        for t in sinks:
            if s not in graph or t not in graph:
                continue
            for fab in advanced_fabs:
                if fab not in graph:
                    continue
                if nx.has_path(graph, s, fab) and nx.has_path(graph, fab, t):
                    count += 1
                    break
    return count


def count_frontier_stack(graph, sources, sinks, advanced_fabs):
    """V2.5 definition: source → advanced_fab → cowos → server → cloud → sink.
    Ordered anchor test. CoWoS AND-deps (fab + HBM + ABF) are enforced
    by the cascade logic, so if HBM or ABF is removed, CoWoS outgoing
    edges are already gone before this check runs."""
    count = 0
    for s in sources:
        for t in sinks:
            if s not in graph or t not in graph:
                continue
            found = False
            for fab in advanced_fabs:
                if fab not in graph:
                    continue
                if not nx.has_path(graph, s, fab):
                    continue
                for pkg in FRONTIER_PKGS:
                    if pkg not in graph:
                        continue
                    if not nx.has_path(graph, fab, pkg):
                        continue
                    for srv in SRV_NODES:
                        if srv not in graph:
                            continue
                        if not nx.has_path(graph, pkg, srv):
                            continue
                        for cld in CLOUD_NODES:
                            if cld not in graph:
                                continue
                            if not nx.has_path(graph, srv, cld):
                                continue
                            if nx.has_path(graph, cld, t):
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                count += 1
    return count


def compute_frontier_impact(G_orig, node_to_remove, sources, sinks,
                            advanced_fabs, metric='stack'):
    """Compute frontier impact using specified metric."""
    G = G_orig.copy()
    counter = count_frontier_stack if metric == 'stack' else count_frontier_fab_only
    baseline = counter(G, sources, sinks, advanced_fabs)
    G_red = remove_node_cascade(G, node_to_remove)
    remaining = counter(G_red, sources, sinks, advanced_fabs)
    return baseline - remaining, baseline


# ============================================================
# RUN
# ============================================================

print("=" * 72)
print("AI COMPUTE SUPPLY CHAIN — V2.5")
print("=" * 72)
print(f"Nodes: {len(nodes)}  |  Sources: {len(SOURCES)}  |  Sinks: {len(SINKS)}")
print(f"CHANGES FROM V2.4:")
print(f"  1. Silicon wafers added as fab AND-dependency + edges")
print(f"  2. Frontier = ordered stack: src→fab→cowos→srv→cloud→sink")
print(f"  3. Sensitivity: fab-only vs stack frontier")
print()

results = {}

for threshold in THRESHOLDS:
    G = build_graph(threshold)
    edge_count = G.number_of_edges()
    beta_1 = compute_betti_1(G)

    print(f"Computing {THRESHOLD_LABELS[threshold]}...")

    # Topology impact
    impact, baseline, source_decomp = compute_impacts(G, SOURCES, SINKS)

    # Frontier impact — both metrics
    frontier_stack = {}
    frontier_fab = {}
    stack_baseline = None
    fab_baseline = None
    skip = set(SINKS)
    for node in G.nodes():
        if node in skip:
            continue
        fi_s, fb_s = compute_frontier_impact(G, node, SOURCES, SINKS, ADVANCED_FABS, 'stack')
        fi_f, fb_f = compute_frontier_impact(G, node, SOURCES, SINKS, ADVANCED_FABS, 'fab_only')
        frontier_stack[node] = fi_s
        frontier_fab[node] = fi_f
        if stack_baseline is None:
            stack_baseline = fb_s
            fab_baseline = fb_f

    # Frontier source decomposition
    frontier_source_decomp = {}
    for src in SOURCES:
        # Self: frontier pairs originating from this source
        self_frontier = count_frontier_stack(G, [src], SINKS, ADVANCED_FABS)
        # After removal: frontier pairs from OTHER sources
        G_red = remove_node_cascade(G, src)
        other_sources = [s for s in SOURCES if s != src]
        other_before = count_frontier_stack(G, other_sources, SINKS, ADVANCED_FABS)
        other_after = count_frontier_stack(G_red, other_sources, SINKS, ADVANCED_FABS)
        frontier_source_decomp[src] = {
            'self_loss': self_frontier,
            'cascade_loss': other_before - other_after,
        }

    results[threshold] = {
        'edges': edge_count,
        'beta_1': beta_1,
        'baseline': baseline,
        'impact': impact,
        'frontier_stack': frontier_stack,
        'frontier_fab': frontier_fab,
        'stack_baseline': stack_baseline,
        'fab_baseline': fab_baseline,
        'source_decomp': source_decomp,
        'frontier_source_decomp': frontier_source_decomp,
    }

    print(f"\n--- {THRESHOLD_LABELS[threshold]} ---")
    print(f"  Edges: {edge_count}  |  β₁: {beta_1}  |  Topo reachable: {baseline}/20")
    print(f"  Frontier stack baseline: {stack_baseline}  |  Frontier fab-only baseline: {fab_baseline}")

    sorted_impact = sorted(
        [(n, impact.get(n, 0), frontier_stack.get(n, 0), frontier_fab.get(n, 0))
         for n in set(list(impact.keys()) + list(frontier_stack.keys()))
         if impact.get(n, 0) > 0 or frontier_stack.get(n, 0) > 0],
        key=lambda x: -(x[1] + x[2]),
    )

    if sorted_impact:
        print(f"\n  {'Node':<45s} {'Topo':>5s} {'FrStack':>8s} {'FrFab':>7s} {'SrcDecomp (topo)':>18s} {'SrcDecomp (front)':>20s}")
        print(f"  {'-'*45} {'-'*5} {'-'*8} {'-'*7} {'-'*18} {'-'*20}")
        for node, ti, fs, ff in sorted_impact[:20]:
            sd = source_decomp.get(node)
            sd_str = f"s={sd['self_loss']} c={sd['cascade_loss']}" if sd else ""
            fsd = frontier_source_decomp.get(node)
            fsd_str = f"s={fsd['self_loss']} c={fsd['cascade_loss']}" if fsd else ""
            euv = " ◄EUV" if node in ('asml_euv', 'zeiss_optics', 'trumpf_source') else ""
            print(f"  {nodes[node]['name']:<45s} {ti:>3d}/20 {fs:>4d}/{stack_baseline} {ff:>3d}/{fab_baseline} {sd_str:>18s} {fsd_str:>20s}{euv}")
    print()


# ============================================================
# AUDIT BLOCK — HARD ACCEPTANCE TESTS
# ============================================================

print("=" * 72)
print("ACCEPTANCE TESTS")
print("=" * 72)

audit_nodes = ['asml_euv', 'zeiss_optics', 'trumpf_source', 'cowos',
               'abf_substrate', 'si_wafers', 'ultrapure_water', 'tsmc_advanced']

audit_pass = True
tests = []

for node in audit_nodes:
    topo_vals = [results[t]['impact'].get(node, 0) for t in THRESHOLDS]
    stack_vals = [results[t]['frontier_stack'].get(node, 0) for t in THRESHOLDS]
    fab_vals = [results[t]['frontier_fab'].get(node, 0) for t in THRESHOLDS]
    sd = results['strict']['source_decomp'].get(node)

    topo_str = '/'.join(str(v) for v in topo_vals)
    stack_str = '/'.join(str(v) for v in stack_vals)
    fab_str = '/'.join(str(v) for v in fab_vals)
    sd_str = f"self={sd['self_loss']} casc={sd['cascade_loss']}" if sd else "n/a"

    print(f"\n  {nodes[node]['name']}")
    print(f"    Topo S/D/L:       {topo_str}")
    print(f"    FrStack S/D/L:    {stack_str}")
    print(f"    FrFab S/D/L:      {fab_str}")
    print(f"    Source decomp:    {sd_str}")

# Hard tests
def test(name, condition):
    global audit_pass
    status = "PASS" if condition else "FAIL"
    if not condition:
        audit_pass = False
    tests.append((name, status))
    print(f"  [{status}] {name}")

print(f"\n  Hard acceptance tests:")

# ABF must reduce frontier-stack
abf_stack = [results[t]['frontier_stack'].get('abf_substrate', 0) for t in THRESHOLDS]
test("ABF removal reduces frontier-stack at strict", abf_stack[0] > 0)

# CoWoS must reduce frontier-stack
cowos_stack = [results[t]['frontier_stack'].get('cowos', 0) for t in THRESHOLDS]
test("CoWoS removal reduces frontier-stack at strict", cowos_stack[0] > 0)

# si_wafers must reduce frontier-stack
sw_stack = [results[t]['frontier_stack'].get('si_wafers', 0) for t in THRESHOLDS]
test("si_wafers removal reduces frontier-stack at strict", sw_stack[0] > 0)

# ASML must reduce frontier-stack
asml_stack = [results[t]['frontier_stack'].get('asml_euv', 0) for t in THRESHOLDS]
test("ASML removal reduces frontier-stack at strict", asml_stack[0] > 0)
test("ASML frontier-stack is flat (invariant S==L)", asml_stack[0] == asml_stack[-1] and asml_stack[0] > 0)

# Zeiss and TRUMPF should match ASML pattern
zeiss_stack = [results[t]['frontier_stack'].get('zeiss_optics', 0) for t in THRESHOLDS]
trumpf_stack = [results[t]['frontier_stack'].get('trumpf_source', 0) for t in THRESHOLDS]
test("Zeiss frontier-stack matches ASML", zeiss_stack == asml_stack)
test("TRUMPF frontier-stack matches ASML", trumpf_stack == asml_stack)

print(f"\n  {'='*50}")
print(f"  AUDIT RESULT: {'ALL TESTS PASSED' if audit_pass else 'SOME TESTS FAILED'}")
print(f"  {'='*50}")


# ============================================================
# SENSITIVITY: FAB-ONLY vs STACK FRONTIER
# ============================================================

print(f"\n{'='*72}")
print("SENSITIVITY: fab-only frontier vs stack frontier")
print(f"{'='*72}")
print(f"\n{'Node':<45s} {'FabOnly S/D/L':>14s} {'Stack S/D/L':>14s} {'Changed?':>10s}")
print(f"{'-'*45} {'-'*14} {'-'*14} {'-'*10}")

nodes_to_compare = set()
for t in THRESHOLDS:
    for n in results[t]['frontier_stack']:
        if results[t]['frontier_stack'].get(n, 0) > 0 or results[t]['frontier_fab'].get(n, 0) > 0:
            nodes_to_compare.add(n)

for node in sorted(nodes_to_compare,
                    key=lambda n: max(results['strict']['frontier_stack'].get(n, 0),
                                      results['strict']['frontier_fab'].get(n, 0)),
                    reverse=True):
    fab_vals = [results[t]['frontier_fab'].get(node, 0) for t in THRESHOLDS]
    stack_vals = [results[t]['frontier_stack'].get(node, 0) for t in THRESHOLDS]
    fab_str = '/'.join(f"{v:>2d}" for v in fab_vals)
    stack_str = '/'.join(f"{v:>2d}" for v in stack_vals)
    changed = "YES" if fab_vals != stack_vals else "no"
    print(f"  {nodes[node]['name']:<43s} {fab_str:>14s} {stack_str:>14s} {changed:>10s}")


# ============================================================
# CLASSIFY CURVE SHAPES — DUAL TAXONOMY
# ============================================================

all_nodes_with_impact = set()
for t in THRESHOLDS:
    for n, d in results[t]['impact'].items():
        if d > 0:
            all_nodes_with_impact.add(n)
    for n, d in results[t]['frontier_stack'].items():
        if d > 0:
            all_nodes_with_impact.add(n)

def classify_topo(node):
    vals = [results[t]['impact'].get(node, 0) for t in THRESHOLDS]
    if all(v > 0 for v in vals) and vals[0] == vals[-1]:
        return 'flat-critical'
    elif vals[0] > 0 and vals[-1] == 0:
        return 'declining'
    elif vals[0] > 0:
        return 'partially-declining'
    else:
        return 'none'

def classify_frontier(node):
    vals = [results[t]['frontier_stack'].get(node, 0) for t in THRESHOLDS]
    if all(v > 0 for v in vals) and vals[0] == vals[-1]:
        return 'frontier-flat'
    elif vals[0] > 0 and vals[-1] == 0:
        return 'frontier-declining'
    elif vals[0] > 0:
        return 'frontier-partial'
    else:
        return 'none'

topo_types = {n: classify_topo(n) for n in all_nodes_with_impact}
frontier_types = {n: classify_frontier(n) for n in all_nodes_with_impact}

print("\n" + "=" * 72)
print("DUAL TAXONOMY: TOPOLOGY × FRONTIER")
print("=" * 72)

print(f"\n{'Node':<50s} {'Topo S→D→L':>12s} {'Front S→D→L':>14s} {'Topo':>18s} {'Frontier':>18s}")
print(f"{'-'*50} {'-'*12} {'-'*14} {'-'*18} {'-'*18}")

for node in sorted(all_nodes_with_impact,
                    key=lambda n: (results['strict']['impact'].get(n, 0) +
                                   results['strict']['frontier_stack'].get(n, 0)),
                    reverse=True):
    topo_vals = [results[t]['impact'].get(node, 0) for t in THRESHOLDS]
    front_vals = [results[t]['frontier_stack'].get(node, 0) for t in THRESHOLDS]
    topo_str = '/'.join(f"{v:>2d}" for v in topo_vals)
    front_str = '/'.join(f"{v:>2d}" for v in front_vals)
    print(f"  {nodes[node]['name']:<48s} {topo_str:>12s} {front_str:>14s} {topo_types[node]:>18s} {frontier_types[node]:>18s}")


# ============================================================
# ROBUSTNESS TABLE
# ============================================================

ROBUSTNESS = {
    'asml_euv':        ('A', 'Robust single-entity',  'Sole EUV lithography; no alternative technology',          'Viable non-EUV lithography'),
    'zeiss_optics':    ('A', 'Robust single-entity',  'Sole EUV optics at picometer precision',                   'Second optics supplier qualified'),
    'trumpf_source':   ('A', 'Robust single-entity',  'Sole high-power EUV light source',                         'Second light source supplier'),
    'photoresists':    ('C', 'Resolution-sensitive',   'Aggregates JSR/TOK/Shin-Etsu/Fujifilm',                    'Split to supplier-level nodes'),
    'cmp_slurries':    ('C', 'Resolution-sensitive',   'Aggregates Cabot/Fujimi/DuPont',                            'Split to supplier-level nodes'),
    'specialty_gases': ('C', 'Resolution-sensitive',   'Aggregates neon + fluorine suppliers',                      'Split to supplier-level nodes'),
    'purity_chemicals':('C', 'Resolution-sensitive',   'Aggregates multiple 11N producers',                         'Split to supplier-level nodes'),
    'hpq':             ('C', 'Model-dependent',        'No degraded edges for alt quartz',                          'Add degraded alternative-quartz edges'),
    'si_wafers':       ('C', 'Resolution-sensitive',   'Aggregates Shin-Etsu/Sumco/Siltronic/SK Siltron',           'Split to supplier-level nodes'),
    'rare_earths':     ('C', 'Threshold-sensitive',    'China ~60-70% but alternatives exist',                      'Add degraded non-China supply edges'),
    'germanium':       ('C', 'Threshold-sensitive',    'China ~60% but Canadian/Belgian sources exist',              'Add degraded non-China supply edges'),
    'ultrapure_water': ('C', 'Resolution-sensitive',   'Locally produced at every fab; not a single source',         'Split to site-level nodes'),
    'china_design':    ('C', 'Structural assumption',  'SMIC design ecosystem assumed available at all thresholds',  'Challenge SMIC design availability'),
    'abf_substrate':   ('A', 'Robust single-entity',  'Ajinomoto ~95% market share in advanced ABF film',           'Second ABF supplier qualified at scale'),
    'cowos':           ('A', 'Robust single-entity',  'TSMC-origin 2.5D packaging; no equivalent at scale',         'Samsung/Intel advanced packaging at parity'),
}

print(f"\n{'='*72}")
print("ROBUSTNESS REGISTER")
print(f"{'='*72}")
print(f"\n{'Node':<42s} {'Tier':>4s}  {'Topo':>8s}  {'Frontier':>10s}  {'Confidence'}")
print(f"{'-'*42} {'-'*4}  {'-'*8}  {'-'*10}  {'-'*24}")

for node in sorted(all_nodes_with_impact,
                    key=lambda n: ROBUSTNESS.get(n, ('Z',))[0]):
    if topo_types.get(node) in ('flat-critical', 'partially-declining') or \
       frontier_types.get(node) in ('frontier-flat', 'frontier-partial'):
        r = ROBUSTNESS.get(node, ('?', 'Unclassified', '', ''))
        print(f"  {nodes[node]['name']:<40s} {r[0]:>4s}  {topo_types[node]:>8s}  {frontier_types[node]:>10s}  {r[1]}")


# ============================================================
# CHART: DUAL TAXONOMY — TOPOLOGY × FRONTIER (REWRITTEN)
# ============================================================

# Collect nodes to plot — group by combined type for layered rendering
plot_nodes = sorted(all_nodes_with_impact,
                    key=lambda n: max(results['strict']['impact'].get(n, 0),
                                      results['strict']['frontier_stack'].get(n, 0)),
                    reverse=True)[:15]

type_colors = {
    'topo-declining + frontier-flat': '#ff6644',
    'topo-flat + frontier-flat':      '#ff4444',
    'frontier-only':                   '#be95ff',
    'declining':                       '#ffd93d',
    'source-only':                     '#8b949e',
}

def get_combined_type(node):
    tt = topo_types.get(node, 'none')
    ft = frontier_types.get(node, 'none')
    if tt == 'declining' and ft == 'frontier-flat':
        return 'topo-declining + frontier-flat'
    elif tt == 'flat-critical' and ft == 'frontier-flat':
        return 'topo-flat + frontier-flat'
    elif tt == 'none' and ft == 'frontier-flat':
        return 'frontier-only'
    elif tt == 'flat-critical' and ft == 'none':
        return 'source-only'
    else:
        return 'declining'

combined_types = {n: get_combined_type(n) for n in plot_nodes}

# --- Figure layout: wider, more vertical space ---
fig = plt.figure(figsize=(28, 12))
fig.patch.set_facecolor('#0d1117')

# Four panels with proper margins
ax_topo  = fig.add_axes([0.04, 0.10, 0.27, 0.72])
ax_front = fig.add_axes([0.36, 0.10, 0.27, 0.72])
ax_tax   = fig.add_axes([0.68, 0.42, 0.30, 0.50])
ax_map   = fig.add_axes([0.68, 0.04, 0.30, 0.34])

fig.text(0.34, 0.96, 'AI Compute Supply Chain: Topology vs Frontier Impact',
         ha='center', color='white', fontsize=16, fontweight='bold')
fig.text(0.34, 0.925, '52 nodes · AND-dependency cascades · Ordered frontier stack · 3 substitutability thresholds',
         ha='center', color='#8b949e', fontsize=10)
fig.text(0.965, 0.96, 'v2.5', ha='right', color='#30363d', fontsize=9)

x_pos = np.array([0, 1, 2])

# --- Jitter helper for overlapping lines ---
def get_jitter(node, node_list, vals, all_vals_map, scale=0.15):
    """Compute small vertical offset for lines sharing the same value."""
    key = tuple(vals)
    same = [n for n in node_list if tuple(all_vals_map[n]) == key]
    if len(same) <= 1:
        return [0, 0, 0]
    idx = same.index(node)
    spread = np.linspace(-scale * (len(same)-1)/2, scale * (len(same)-1)/2, len(same))
    return [spread[idx]] * 3

# --- Precompute all values for jitter ---
topo_vals_map = {}
front_vals_map = {}
for node in plot_nodes:
    topo_vals_map[node] = [results[t]['impact'].get(node, 0) for t in THRESHOLDS]
    front_vals_map[node] = [results[t]['frontier_stack'].get(node, 0) for t in THRESHOLDS]

# Line style assignments for overlapping groups
line_styles = ['-', '--', '-.', ':']
def get_line_style(node, node_list, vals_map):
    key = tuple(vals_map[node])
    same = [n for n in node_list if tuple(vals_map[n]) == key]
    if len(same) <= 1:
        return '-'
    idx = same.index(node)
    return line_styles[idx % len(line_styles)]

# --- LEFT PANEL: Topology Impact ---
ax = ax_topo
ax.set_facecolor('#161b22')

# Draw lines — grouped by trajectory
topo_groups = {}
for node in plot_nodes:
    vals = tuple(topo_vals_map[node])
    ctype = combined_types.get(node, 'declining')
    key = (vals, ctype)
    if key not in topo_groups:
        topo_groups[key] = []
    topo_groups[key].append(node)

for (vals, ctype), members in topo_groups.items():
    if max(vals) == 0:
        continue
    color = type_colors.get(ctype, '#8b949e')
    lw = 3.0 if len(members) > 2 else 2.0
    alpha = 1.0 if 'flat' in ctype or ctype == 'topo-declining + frontier-flat' else 0.7
    ax.plot(x_pos, list(vals), '-', color=color, linewidth=lw, alpha=alpha,
            markersize=6, marker='o')

ax.set_xticks(x_pos)
ax.set_xticklabels(['Strict\n(0–3 mo)', 'Degraded\n(12 mo)', 'Loose\n(24 mo)'],
                    color='white', fontsize=9)
ax.set_ylabel('Source–Sink Pairs Disconnected (of 20)', color='white', fontsize=10)
ax.set_title('Topology Impact', color='white', fontsize=13, fontweight='bold', pad=12)
ax.tick_params(colors='white')
ax.set_ylim(-0.5, 10)
ax.set_xlim(-0.2, 2.2)
ax.axhline(y=0, color='#30363d', linewidth=0.5)
for spine in ax.spines.values():
    spine.set_color('#30363d')

# Annotations — label grouped lines directly
ax.annotate('Si wafers (8/8/8)', xy=(2, 8), xytext=(2.05, 9),
            color='#ff4444', fontsize=7.5, fontweight='bold',
            arrowprops=dict(arrowstyle='-', color='#ff4444', lw=0.5))
ax.annotate('Azure/GCP\n(5→0)', xy=(0.1, 5), xytext=(-0.15, 7),
            color='#ffd93d', fontsize=7, ha='center',
            arrowprops=dict(arrowstyle='-', color='#ffd93d', lw=0.5))
ax.annotate('Chemistry (4/4/4)', xy=(2, 4), xytext=(2.05, 5),
            color='#ff4444', fontsize=7.5,
            arrowprops=dict(arrowstyle='-', color='#ff4444', lw=0.5))
ax.annotate('EUV corridor\n(4/4→0)', xy=(2, 0), xytext=(1.5, 1.8),
            color='#ff6644', fontsize=7.5, fontweight='bold',
            arrowprops=dict(arrowstyle='-', color='#ff6644', lw=0.5))
ax.annotate('ABF, Adv. Pkg\n(invisible: 0/0/0)', xy=(1, 0), xytext=(0.1, 1.8),
            color='#be95ff', fontsize=7, fontstyle='italic')

# --- CENTER PANEL: Frontier Impact ---
ax = ax_front
ax.set_facecolor('#161b22')

# Group by unique trajectory rather than plotting every node
frontier_groups = {}
for node in plot_nodes:
    vals = tuple(front_vals_map[node])
    ctype = combined_types.get(node, 'declining')
    key = (vals, ctype)
    if key not in frontier_groups:
        frontier_groups[key] = []
    frontier_groups[key].append(node)

# Draw grouped lines
group_draw_order = sorted(frontier_groups.keys(),
                          key=lambda k: (max(k[0]), k[0][0]), reverse=True)

for (vals, ctype), members in frontier_groups.items():
    if max(vals) == 0:
        continue
    color = type_colors.get(ctype, '#8b949e')
    lw = 3.0 if len(members) > 2 else 2.0
    alpha = 1.0 if 'flat' in ctype or ctype == 'frontier-only' else 0.7
    ls = '-' if 'flat' in ctype or ctype == 'frontier-only' else '-'
    ax.plot(x_pos, list(vals), ls, color=color, linewidth=lw, alpha=alpha,
            markersize=6, marker='o')

ax.set_xticks(x_pos)
ax.set_xticklabels(['Strict\n(0–3 mo)', 'Degraded\n(12 mo)', 'Loose\n(24 mo)'],
                    color='white', fontsize=9)
ax.set_ylabel('Frontier Pairs Disconnected (of 16)', color='white', fontsize=10)
ax.set_title('Frontier-Stack Impact', color='white', fontsize=13, fontweight='bold', pad=12)
ax.tick_params(colors='white')
ax.set_ylim(-0.5, 19)
ax.set_xlim(-0.2, 2.2)
ax.axhline(y=0, color='#30363d', linewidth=0.5)
for spine in ax.spines.values():
    spine.set_color('#30363d')

# Direct annotations for frontier panel
# Count how many nodes at 16/16/16 per color
n_euv = sum(1 for n in plot_nodes if combined_types.get(n) == 'topo-declining + frontier-flat'
            and front_vals_map[n] == [16,16,16])
n_chem = sum(1 for n in plot_nodes if combined_types.get(n) == 'topo-flat + frontier-flat'
             and front_vals_map[n] == [16,16,16])
n_fonly = sum(1 for n in plot_nodes if combined_types.get(n) == 'frontier-only'
              and front_vals_map[n] == [16,16,16])

ax.annotate(f'Flat at 16/16: EUV corridor ({n_euv})\n'
            f'+ chemistry/wafers ({n_chem}) + ABF/pkg ({n_fonly})',
            xy=(2, 16), xytext=(0.3, 18.2),
            color='white', fontsize=7.5, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#30363d'),
            arrowprops=dict(arrowstyle='->', color='white', lw=0.8))
ax.annotate('TSMC (16→0)', xy=(1.5, 4), xytext=(1.7, 3),
            color='#ffd93d', fontsize=7.5,
            arrowprops=dict(arrowstyle='-', color='#ffd93d', lw=0.5))
ax.annotate('HPQ, Rare Earths (4)', xy=(2, 4), xytext=(2.05, 5.5),
            color='#ff4444', fontsize=7,
            arrowprops=dict(arrowstyle='-', color='#ff4444', lw=0.5))
ax.annotate('Germanium (0)', xy=(1, 0), xytext=(0.2, 1.0),
            color='#8b949e', fontsize=7, fontstyle='italic',
            arrowprops=dict(arrowstyle='-', color='#8b949e', lw=0.5))

# --- RIGHT TOP: Taxonomy table ---
ax = ax_tax
ax.set_facecolor('#0d1117')
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

y = 9.8
ax.text(0.1, y, 'DUAL TAXONOMY', color='white', fontsize=12, fontweight='bold')
y -= 0.15
ax.plot([0.1, 9.9], [y, y], color='#30363d', linewidth=0.5)

categories = [
    ('topo-declining + frontier-flat', '#ff6644', 'FRONTIER-CRITICAL',
     'Topology-declining · Frontier-flat',
     ['ASML EUV Lithography', 'Zeiss EUV Optics', 'TRUMPF EUV Light Source'],
     ['4/4/0', '4/4/0', '4/4/0'],
     ['16/16/16', '16/16/16', '16/16/16']),
    ('frontier-only', '#be95ff', 'FRONTIER-ONLY',
     'Topology-invisible · Frontier-flat',
     ['ABF Substrate (Ajinomoto)', 'Advanced 2.5D Packaging'],
     ['0/0/0', '0/0/0'],
     ['16/16/16', '16/16/16']),
    ('topo-flat + frontier-flat', '#ff4444', 'FULL FLAT-CRITICAL',
     'Topology-flat · Frontier-flat',
     ['Si Wafers', 'Photoresists', 'CMP Slurries', 'Specialty Gases'],
     ['8/8/8', '4/4/4', '4/4/4', '4/4/4'],
     ['16/16/16', '16/16/16', '16/16/16', '16/16/16']),
    ('declining', '#ffd93d', 'DECLINING',
     'Both metrics decline',
     ['TSMC Advanced Logic'],
     ['4/0/0'],
     ['16/0/0']),
]

for ctype_key, color, title, subtitle, members, topos, fronts in categories:
    y -= 0.45
    ax.add_patch(plt.Rectangle((0.1, y-0.05), 0.25, 0.25,
                 facecolor=color, edgecolor='none'))
    ax.text(0.55, y, title, color=color, fontsize=8.5, fontweight='bold', va='center')
    y -= 0.28
    ax.text(0.55, y, subtitle, color='#6b7280', fontsize=6.5, va='center')
    y -= 0.05
    # Column headers
    y -= 0.25
    ax.text(0.7, y, 'Node', color='#4a5568', fontsize=5.5)
    ax.text(7.2, y, 'Topo', color='#4a5568', fontsize=5.5, ha='right')
    ax.text(9.5, y, 'Frontier', color='#4a5568', fontsize=5.5, ha='right')
    for name, topo, front in zip(members, topos, fronts):
        y -= 0.25
        ax.text(0.7, y, name, color='white', fontsize=6.5, va='center')
        ax.text(7.2, y, topo, color='#8b949e', fontsize=6.5, ha='right', va='center',
                fontfamily='monospace')
        ax.text(9.5, y, front, color=color, fontsize=6.5, ha='right', va='center',
                fontfamily='monospace', fontweight='bold')
    y -= 0.15
    ax.plot([0.5, 9.5], [y, y], color='#1e2530', linewidth=0.3)

# --- RIGHT BOTTOM: Map ---
ax = ax_map
ax.set_facecolor('#0d1117')
ax.set_xlim(2, 14)
ax.set_ylim(47.5, 53)
ax.axis('off')

# Country shapes with visible borders
nl_x = [3.4, 7.2, 7.0, 5.9, 3.6, 3.4]
nl_y = [51.4, 53.4, 52.0, 51.0, 51.4, 51.4]
ax.fill(nl_x, nl_y, color='#1a2332', alpha=0.6)
ax.plot(nl_x, nl_y, color='#4a5568', linewidth=1.2)

de_x = [6.0, 7.2, 7.5, 9.0, 10.0, 12.0, 13.5, 14.5, 14.0, 12.5, 12.0, 10.0, 9.0, 7.5, 6.0, 6.0]
de_y = [51.0, 53.4, 53.8, 54.8, 54.0, 54.0, 52.5, 51.0, 49.0, 47.5, 47.7, 47.5, 47.5, 47.6, 49.5, 51.0]
ax.fill(de_x, de_y, color='#1a2332', alpha=0.4)
ax.plot(de_x, de_y, color='#4a5568', linewidth=1.2)

# Country labels
ax.text(4.5, 52.5, 'NL', color='#4a5568', fontsize=11, fontstyle='italic', fontweight='bold')
ax.text(11.0, 50.5, 'DE', color='#4a5568', fontsize=11, fontstyle='italic', fontweight='bold')

# Corridor dashed line
corridor_lons = [5.41, 9.07, 10.10]
corridor_lats = [51.42, 48.83, 48.79]
ax.plot(corridor_lons, corridor_lats, '--', color='#ff6644', linewidth=2.5, alpha=0.5, zorder=5)

# City markers and labels — offset to avoid overlap
locations = [
    ('Veldhoven', 'ASML', 5.41, 51.42, 14, 6),
    ('Ditzingen', 'TRUMPF', 9.07, 48.83, -85, 12),
    ('Oberkochen', 'Zeiss', 10.10, 48.79, 14, -8),
]
for city, company, lon, lat, dx, dy in locations:
    ax.plot(lon, lat, 'o', color='#ff6644', markersize=10, zorder=10,
            markeredgecolor='white', markeredgewidth=1.5)
    ax.annotate(f'{city}\n({company})', (lon, lat), textcoords="offset points",
                xytext=(dx, dy), color='white', fontsize=7.5, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.25', facecolor='#0d1117',
                         edgecolor='#ff6644', alpha=0.95),
                arrowprops=dict(arrowstyle='-', color='#ff6644', lw=0.8),
                zorder=11)

# Distance label — positioned cleanly off the line
ax.text(6.8, 50.5, '~480 km', color='#ff6644', fontsize=11,
        fontweight='bold', fontstyle='italic', ha='center',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d1117',
                  edgecolor='#ff6644', alpha=0.9))

ax.set_title('The EUV Corridor', color='#ff6644', fontsize=11, fontweight='bold', pad=8)

plt.savefig(OUT_CHART, dpi=200, bbox_inches='tight', facecolor='#0d1117')
plt.close()
print(f"Chart: {OUT_CHART}")


# ============================================================
# SAVE JSON
# ============================================================

output = {
    'metadata': {
        'version': '2.5',
        'nodes': len(nodes),
        'changes': [
            'v2.4: Fab design deps per-fab (SMIC gets china_design node)',
            'v2.5: Silicon wafers added as explicit fab AND-dependency + edges',
            'v2.5: Frontier redefined as ordered stack (src→fab→pkg→srv→cloud→sink)',
            'v2.5: Sensitivity comparison: fab-only vs stack frontier',
            'v2.5: ABF substrate and advanced packaging now surface as frontier-flat',
        ],
    },
}

for t in THRESHOLDS:
    r = results[t]
    output[t] = {
        'edges': r['edges'],
        'beta_1': r['beta_1'],
        'reachable_pairs': r['baseline'],
        'frontier_stack_baseline': r['stack_baseline'],
        'frontier_fab_baseline': r['fab_baseline'],
        'critical_nodes': [
            {
                'node': n,
                'name': nodes[n]['name'],
                'topo_disconnected': d,
                'frontier_stack_disconnected': r['frontier_stack'].get(n, 0),
                'frontier_fab_disconnected': r['frontier_fab'].get(n, 0),
                'topo_type': topo_types.get(n, 'none'),
                'frontier_type': frontier_types.get(n, 'none'),
                'robustness_tier': ROBUSTNESS.get(n, ('?',))[0],
                'robustness_label': ROBUSTNESS.get(n, ('?', 'Unclassified'))[1],
                'source_decomp': r['source_decomp'].get(n),
                'frontier_source_decomp': r['frontier_source_decomp'].get(n),
            }
            for n, d in sorted(r['impact'].items(), key=lambda x: -x[1])
            if d > 0 or r['frontier_stack'].get(n, 0) > 0
        ]
    }

with open(OUT_JSON, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n{'='*72}")
print("V2.5 COMPLETE")
print(f"{'='*72}")
print(f"Data: {OUT_JSON}")
