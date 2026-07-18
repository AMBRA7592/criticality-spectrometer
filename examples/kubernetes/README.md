# Example 2: Kubernetes Bookinfo

This worked example asks a narrow question: does endpoint redundancy declared
by a Kubernetes Service imply redundancy on the traffic path that actually
served a request?

It compares two views of Istio's public Bookinfo application using the frozen
v0.1 model contract. No Kubernetes-specific logic exists under `src/`.

## Evidence boundary

The example has two authoritative source artifacts:

- [`sources/declared_inventory.json`](sources/declared_inventory.json) is a
  normalized inventory of a pinned Istio `release-1.24` revision. It records
  Kubernetes Service selectors, Istio subsets and all-v1 routes, application
  call sites, upstream paths, and SHA-256 hashes.
- [`sources/observed_request.json`](sources/observed_request.json) is a bounded,
  normalized excerpt of one publicly reported Bookinfo request. Three HTTP 200
  records share one request ID and identify `productpage-v1`, `details-v1`, and
  `reviews-v1`. The original report remains at the cited GitHub issue.

The repository did **not** operate the cluster that produced the request log.
The observation is externally reported and reproducibly normalized here; it is
not an independently repeated experiment. Caller edges are inferred by
correlating the shared request ID with the pinned application call sites.
The upstream SHA-256 values are provenance records: local tests pin their form,
but CI does not fetch Istio and independently re-hash those external files.

## Mission

The selected mission is one complete book page containing both details and
reviews. That completeness rule is a modeling assumption, not a Kubernetes or
Istio guarantee. The outcome starts at `client_request` and counts the
`complete_book_page` sink once.

## Two models

[`model_declared.json`](model_declared.json) is the **selector view**. The
Kubernetes `reviews` Service selector admits all three deployed review versions,
so `reviews_v1`, `reviews_v2`, and `reviews_v3` are immediate OR alternatives.

[`model.json`](model.json) is the **observed route view**. The bounded request
selected `reviews_v1`, consistent with the pinned all-v1 traffic policy. It
therefore begins with `reviews_v1` as the active endpoint. `reviews_v2` is
already deployed and defined as a valid subset, but changing traffic to it is
modeled as an alternative that activates at five minutes.

## Adaptation assumption

Five minutes is an explicit scenario value for an operator route change. It is
not measured recovery time and is not claimed to be representative of
Kubernetes operations. Change it and regenerate to test a different scenario.

## Result

The two views give the same node two different curves:

| model view | `reviews_v1` impact | shape |
|---|---:|---|
| Service selector | `[0, 0]` | `none` |
| observed all-v1 route | `[1, 0]` | `fully_adaptable` |

The selector view treats endpoint membership as immediate redundancy. The
observed route view says that the endpoint serving the request is initially
mission-critical, but an operator can restore the modeled mission by routing to
an already-deployed version.

This does not prove either view is universally correct. It demonstrates why a
static count of deployed endpoints cannot by itself answer the adaptation-time
question.

Inspect the mechanism directly:

```bash
criticality-spectrometer explain examples/kubernetes/model.json reviews_v1
```

At `tau=0`, the trace records `reviews_service`, `productpage_v1`, and
`complete_book_page` failing in three propagation rounds. At `tau=5`,
`reviews_v2` is identified as the substitute that restores the sink. The
committed JSON explanation is
[`explanations/reviews_v1.json`](explanations/reviews_v1.json).

## Rebuild

```bash
python examples/kubernetes/build_bookinfo_case.py
pytest -q tests/test_kubernetes_case.py
```

The builder runs from any working directory and emits byte-identical models,
the evidence ledger, complete self-identifying reports, and the explanation.
The repository-wide `python scripts/regenerate.py` command includes this case,
and CI rejects stale generated artifacts.

## Non-claims

- One request is not a frequency estimate or a complete workload profile.
- The example does not benchmark Kubernetes, Istio, failover, latency, health
  checks, capacity, retries, or availability.
- A Service selector identifies eligible endpoints; it does not prove that all
  endpoints served traffic in the observed request.
- The five-minute route change is a scenario assumption.
- `complete_book_page` is a selected mission definition, not an application SLO.
- The result is an external-validity probe for the model contract, not a claim
  of general Kubernetes reliability analysis.

The claim-to-evidence mapping is in
[`evidence_ledger.json`](evidence_ledger.json).
