# Landing-page clarity evaluation: README.md

First-time-visitor comprehension audit of the repository landing page (`README.md` as of
branch `claude/landing-page-clarity-eval-6htgwk`, 2026-07-19). The brief: report what a
qualified but time-pressed professional actually understands from the page, in what order,
and where they lose the thread — with no outside knowledge, no charity toward gaps, and
every claim tied to a specific on-page element. Stated and inferred are kept separate
throughout.

**Reading scope.** I read: `README.md` in full; the repository root file listing (visible
to any GitHub visitor); and the visible text labels inside the hero image
`docs/criticality-curves.svg` (no SVG renderer was available, so I extracted the labels a
visitor would see rendered). I verified that all 25 files/links the README references
exist — existence only, none opened. I did **not** read `docs/method.md`,
`docs/tutorial.md`, `docs/nonclaims.md`, the schemas, the examples, any source code, the
CHANGELOG, or GitHub-side chrome (About blurb, stars). Nothing outside the page informed
this evaluation.

**Fold assumption.** "Above the fold" = logo, title, tagline, badge row, and the
full-width hero chart. A full-width image almost certainly pushes the opening paragraph
below the fold on a typical laptop; where its visibility would change a finding, that is
noted.

---

## 1. First 30 seconds (above the fold only)

In my own words: this is a Python package that takes a model of a system made of
interdependent parts, simulates each part failing, and charts how badly the overall goal
is hurt as a function of how quickly a backup can come online — separating parts that are
permanently fatal to lose from parts that stop being risky once a stand-in arrives fast
enough.

Sentence to a colleague: *"It's a Python tool that knocks out each component of a modeled
system and plots how much of the outcome you lose depending on how fast a backup
activates — so you can tell real single points of failure from ones a quick failover
retires."*

That sentence is constructible above the fold, which is a genuine strength — the tagline
("**Find single points of failure, measure their mission-level blast radius, and see
which risks a fast-enough substitute or failover can retire.**") plus the chart's axes
("Mission loss" vs. "Adaptation horizon (tau)") carry it.

What's missing up top, and it matters:

- **What kind of system, and what I must supply.** The tagline's registers point three
  ways at once — "mission" (defense/space), "blast radius" (SRE slang), "failover" (IT
  ops) — and the only concrete nouns above the fold are the chart's curve labels: "ASML
  EUV," "TSMC advanced," "Germanium." A hurried visitor's first evidence says
  *semiconductor supply-chain tool*. The page corrects this only two-thirds down ("the
  engine contains no semiconductor-specific entities"), which a skimmer never reaches.
- **The chart subtitle is jargon-first**: "Node-removal impact on the ordered frontier
  mission as alternatives activate." "Ordered frontier mission" is triple-stacked,
  undefined term — above the fold.
- Nothing above the fold says the input is a **hand-written model** rather than something
  the tool discovers.

## 2. Full-read restatement

**(a) What it does.** You author a JSON model: nodes, requirement groups combined with
AND/OR logic, substitutes targeted at a specific requirement group with an activation
time, and one designated "mission outcome" (`served_sinks` or `ordered_served_sinks`).
The tool removes each node in turn, sweeps a time axis (tau = when substitutes become
available), and reports per node an impact curve (mission loss at each horizon) plus a
shape class — `persistent`, `fully_adaptable`, `partially_adaptable`, or `none`. A second
command, `explain`, decomposes any curve into per-horizon causes: lost/restored sinks,
cascade rounds, unsatisfied requirement groups, and which substitute rescues what. CLI
and Python API; JSON outputs conform to published schemas and embed the model's SHA-256.

**(b) The one thing a similar tool wouldn't do.** Derivable, and the page states it
directly in its comparison table: centrality and critical-node detection return a
*scalar* about graph position or disconnection; this returns "mission loss across
adaptation horizons under explicit requirements" as a "**curve and shape class**." In
plain terms: criticality as a *function of how fast you can bring an alternative online*,
not a static score — so it can distinguish "single point of failure forever" from
"single point of failure until the backup activates at tau=12."

## 3. Stated vs. inferred (the gap map)

| The page states | I had to infer / guess |
|---|---|
| "performs fault-tree-style AND/OR dependency analysis with a time-to-substitute dimension" | What a **"mission"** concretely is. Never defined; best available gloss is indirect ("one mission outcome: `served_sinks` or `ordered_served_sinks`"), which itself leans on the undefined term "sink." I inferred: sink = terminal node whose being served constitutes the outcome. |
| "It is not a probabilistic fault-tree solver: it does not estimate failure rates, MTBF, or minimal cut sets" | **What "impact"/"mission loss" counts.** Text curves show `[1, 0]`; the hero chart's y-axis runs 0–4. I first assumed "fraction of mission lost" and the chart falsified that — so it's presumably a count (of unserved sinks? ordered stages?). The scale/unit is stated nowhere. That felt-pull to assume a scale is exactly the gap. |
| "removes each modeled component, sweeps the time at which substitutes become available, and records mission loss at every horizon" | **That the user hand-authors the model.** Stated only negatively, in the second-to-last section ("It does not infer dependencies, estimate activation times"). I inferred the real workflow — you must already know every dependency and encode it as JSON — and its cost. |
| The four shape classes with behavior + interpretation (table under "What the instrument returns") | **What "OR gap" is** — a column in the very first output a visitor sees (`node  impact  shape  OR gap`). Never defined anywhere on the page. I could not even produce a confident guess. |
| Model contract: nodes; requirement groups with AND/OR; substitutes with activation time; one mission outcome | **What tau's units are** and which horizons the curves sample. Canonical curve `[1, 0, 0]` has three entries but the text names only tau=0 and tau=12; the API example prints `[1, 0]` (two). Inferred: per-model sampled horizons. Units: unitless ticks in canonical, "five minutes" in Kubernetes — inferred to be model-defined. |
| Exit codes: 0 success, 2 invalid input/model, 3 "the model failed the positive, constant-baseline requirement" | **What the "positive, constant-baseline requirement" is.** Inferred: the intact model must yield a positive, time-constant outcome for comparison. |
| "alpha research instrument with a canonical fixture and two bounded worked domains" | **What the "prior case study" is** ("reproduces the prior case study's seven named acceptance tests"). No name, link, or citation anywhere on the page. I inferred some earlier published analysis exists; a reader cannot identify it from the page. |
| "The example is an application, not cross-domain validation"; "an external-validity probe, not broad validation" | **What "casualties" means** ("casualties grouped by cascade round") — inferred the equipment-failure sense, not people, from context. Costs a beat. |
| Comparison table: centrality → scalar; critical-node detection → scalar/set; this → curve + shape class | **What "connectivity-only edges" are** (named as a missing feature in Scope). No definition; I could only guess it means mere-links-without-requirements, so I cannot weigh the limitation. |
| "the engine contains no semiconductor-specific entities" | **Who the tool is for.** No sentence on the page names an audience; I assembled one from the examples' vocabulary (see §5). |

## 4. Where comprehension breaks

Exact points, in page order:

1. **Tagline: "mission-level blast radius."** First use of "mission," never defined on
   the page. Combined with "failover" and "blast radius," the tagline mixes three
   professional dialects, so the domain stays ambiguous through the entire fold.
2. **Hero chart subtitle: "Node-removal impact on the ordered frontier mission as
   alternatives activate."** "Ordered frontier mission" is undefined jargon in the
   page's most prominent visual; its only echo is "the primary ordered frontier stack"
   much later, also undefined. ("Frontier" of what is never said.)
3. **Hero y-axis "Mission loss" 0–4 vs. every in-text curve being 0/1.** The impact
   scale is never stated; the two data displays a reader meets first appear mutually
   inconsistent until you invent the explanation yourself (see gap map).
4. **"Its bottleneck has impact `1` at `tau=0` and `0` after its backup activates at
   `tau=12`"** (§Run it in 60 seconds). First body-text use of `tau`; the only
   name-to-concept binding is the chart's axis label "Adaptation horizon (tau)," which a
   skimmer won't have read. Units absent.
5. **The demo output block: `node  impact  shape  OR gap`.** "OR gap" — the fourth
   column of the page's very first output — is never defined. Also `[1, 0, 0]`: three
   values, two named horizons. The first artifact the tool shows a new user contains a
   column the page never explains.
6. **§Explain a curve: "lost and restored sinks, casualties grouped by cascade round,
   every unsatisfied requirement group."** Three first-use terms in one clause ("sink,"
   "casualty," "cascade round"). The follow-up hedge "Rounds are propagation stages, not
   unique-causality claims" wards off a misreading the page never set up, so it reads as
   an answer to a question the visitor hasn't formed.
7. **"`3` means the model failed the positive, constant-baseline requirement"** —
   undefined term presented as if standard.
8. **§Worked example (AI compute): "Three missions separate topology, an advanced-fab
   path, and the primary ordered frontier stack."** Garden-path sentence — "separate"
   parses as adjective before verb; required a re-read. Then: **"reproduces the prior
   case study's seven named acceptance tests at the shape level"** — the page's biggest
   dangling reference (which case study? where?), immediately followed by "over the
   specified horizons" (specified where?).
9. **§Worked example (Kubernetes): "compares endpoint redundancy declared by an Istio
   Bookinfo Kubernetes Service with the route observed for one bounded request."** Dense
   but recoverable on a second pass — except "one bounded request" (bounded how?) and the
   closing sentence **"Those rounds preserve the declared `productpage` Service layer,"**
   which I could not confidently parse even on a third read (preserve = don't cascade
   into? keep satisfied?).
10. **§Scope: "The current model contract also lacks connectivity-only edges."** A
    limitation stated in a term the page never defines, so its severity can't be judged.

**Assumed prior knowledge** a target reader may not have: fault-tree AND/OR gates;
network centrality (invoked as the comparison class); Kubernetes/Istio vocabulary
(Service, selector, endpoint, route, `productpage`); semiconductor supply-chain actors
(ASML, EUV, TSMC, germanium); what an "acceptance test" or "evidence ledger" is.

**Where it does *not* break** (calibration — these are genuinely clear):

- The **negative-space sentence sits in paragraph one**: "It is not a probabilistic
  fault-tree solver: it does not estimate failure rates, MTBF, or minimal cut sets."
  This kills the most likely expert misreading immediately. Rare and well done.
- The **on-ramp is real**: `pip install criticality-spectrometer`, two copy-pasteable
  commands, "the 60-second demo needs no clone," expected output shown, stable exit
  codes, `--version`. A visitor can act within a minute of deciding to.
- The **shape-class table** is self-contained: each label gets curve behavior plus
  interpretation, capped by "These labels describe model output. They are not policy
  recommendations or empirical claims by themselves."
- The **comparison table** does honest positioning work in three rows.
- **All 25 on-page links resolve** — no dead references (existence verified only).

## 5. Who it's for — and who bounces

**Earned by the page** (from its vocabulary and examples, not from charity):

- **Reliability / mission-assurance / systems engineers** who already think in fault
  trees and can hand-author models — addressed by "fault-tree-style AND/OR dependency
  analysis," requirement groups, mission outcomes, and the commit-level rigor (schemas,
  SHA-256, stable exit codes).
- **SRE / platform engineers auditing failover adequacy** — addressed by "failover,"
  "blast radius," the Bookinfo worked example, and the tutorial's "ten-node CI pipeline."
- **Research-leaning risk analysts** (supply-chain concentration, strategic
  dependencies) — addressed by the AI-compute example, "evidence ledger," DOI badge,
  `CITATION.cff`, and the "external-validity probe" register. The page's overall voice —
  "alpha research instrument," non-claims doc — fits this reader best.

**Who lands, expects relevance, and leaves:**

- **The SRE who wants discovery.** The page's own draw ("single points of failure,"
  Kubernetes example) attracts an engineer hoping to point a tool at a live cluster or
  dependency graph and get SPOFs found automatically. The disqualifier — "It does not
  infer dependencies, estimate activation times" — is real and honest, but it sits in
  §Scope, the second-to-last section. They spend the whole page before learning the tool
  starts *after* the hardest part (knowing your dependencies) is done by hand.
- **The quantitative-risk engineer** (PRA/FTA practitioner) bounces at paragraph one —
  but that is a *designed*, healthy bounce; the page spends its first "is not" precisely
  on them.
- **The semiconductor-policy reader** drawn in by the ASML/TSMC hero chart finds an
  alpha instrument whose AI-compute case is "an application, not cross-domain
  validation" with no empirical claims — the hero image promises more domain payload
  than the Scope section lets it deliver.

## 6. The value question

The page does establish a concrete action: **given a system you can enumerate as
components with AND/OR requirements and candidate backups, you can compute, per
component, the deadline by which its backup must activate for the outcome to survive
that component's loss — and get a per-horizon trace of exactly which requirement groups
fail and which substitute rescues them.** Grounded in: the tagline ("see which risks a
fast-enough substitute or failover can retire"), the bullet "Does apparent redundancy
preserve the required capability, or only a path?", the canonical demo (backup at
tau=12 zeroes the bottleneck's impact), and the Bookinfo case (declared three-version
redundancy vs. an observed route where recovery takes a modeled five minutes). That
declared-vs-effective-redundancy check, with a time deadline attached, is something a
redundancy checklist or a centrality score does not give you.

The unstated cost of the action (found only by inference, per §3): you must already know
and hand-encode every dependency and activation time yourself.

## 7. Credible or hand-wavy?

Reads as **credible, tilting over-hedged** — the page spends more words disclaiming than
most projects spend claiming.

Trust signals, specifically: the paragraph-one "is not" list (failure rates, MTBF,
minimal cut sets); CI/PyPI/Release/DOI badges; machine-readable contracts
("[`schema/result.schema.json`]", "model SHA-256"); documented stable exit codes; a
"seven-node, hand-verifiable fixture"; runnable verification for both worked examples
(`pytest -q tests/test_ai_case.py`); and unusually precise self-limitation — "alpha
research instrument," "an application, not cross-domain validation," "one externally
reported request … an external-validity probe, not broad validation," "labels the
five-minute adaptation time as an assumption," plus a dedicated non-claims document.
No vague superlatives appear anywhere on the page.

Two wobbles: **"reproduces the prior case study's seven named acceptance tests"** is the
page's one unverifiable-as-written claim — a reproduction asserted against a target the
page never identifies; and artifacts named "Evidence ledger" / "Frozen source manifest"
assert rigor a visitor must take on faith from the link text (I did not open them). The
hero chart, to its credit, self-deflates: "Illustrative output …; values are
model-dependent."

## 8. The bounce line

A qualified visitor bounces because the page never plainly says — anywhere a skimmer
will look — what a "mission" is, what the impact numbers count, or that the input is a
small hand-written JSON model, so between "ordered frontier mission," `tau`, and an
"OR gap" column, they cannot tell within a minute whether this instrument can be pointed
at *their* system or what it would cost to try.

**One-line fix.** Directly under the tagline, add two plain sentences: "You hand-write a
small JSON model — components, AND/OR requirement groups, substitutes with activation
times. The tool removes each component and charts mission loss (unserved end-outcomes,
'sinks') against the time tau at which substitutes come online."
