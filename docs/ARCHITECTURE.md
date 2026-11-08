> Legacy v1 simulator notes. For the current service, start with the root README and V2_LEARNING_PATH.md.

# Architecture

## Current executable flow

CLI → golden cases → authorized retrieval → simulated provider / fallback → response → deterministic scoring → JSON run → paired comparison → local dashboard.

`run_agent` only consumes request-side fields. Expected terms stay in `score`. Tool authorization happens in `search`. The dashboard exposes only generated local artifacts, binds to loopback, and renders dynamic text through `textContent`.

## Target production flow

Authenticated API → policy enforcement → agent orchestrator → retrieval/tools → provider gateway.

A separate evaluation control plane submits versioned jobs to durable workers. Workers persist immutable results and traces, deterministic scorers run first, and a calibrated judge adds semantic judgments. A comparison service reports uncertainty and safety gates before a human-controlled promotion step. Shadow traffic and randomized online metrics validate real outcomes.

Proposed records:

- DatasetCase: ID, version, request, tenant fixture, rubric, labels, provenance, split.
- Run: ID, dataset hash, code commit, prompt hash, provider/model version, seed, settings, timestamps.
- Trace: run/case ID, spans, tool authorization decisions, usage, retries, redacted output.
- Score: metric version, value, evidence, judge version, calibration version.
- Candidate: parent, patch, proposer version, development results, promotion decision.

Keep raw sensitive payloads in separately access-controlled storage, with short retention and deletion workflows. Sanitized traces alone should feed development and dashboards. Email replacement in this starter is not a complete redaction system.

## Extension interfaces

Provider.generate(messages, tools, deadline) → text, citations, usage, finish reason.
Judge.score(request, authorized_sources, answer, rubric) → structured dimensions and evidence.
RunStore.append(run_id, case_id, attempt_id, result) → idempotent write.
Router.choose(request_features, budget, healthy_models) → model and fallback policy.

Use dependency injection to test failure paths without network calls. Tool-level access checks must remain independent of model compliance. Add read-only tools first; writes need explicit authorization, idempotency, and auditability.

## Operational exercises

Implement a queue with backpressure; kill a worker midway through a batch; retry without duplicate charges where the provider supports idempotency; simulate provider rate limiting; observe tail latency; set maximum cost per run; test cross-tenant queries; prove deletion also removes derived traces.

The included container runs an offline demo only. It is not a deployment blueprint, authenticated service, or distributed system.
