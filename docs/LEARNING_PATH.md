> Legacy v1 simulator notes. For the current service, start with the root README and V2_LEARNING_PATH.md.

# Learning path

Use each milestone as a small pull request. Keep a decision log recording the hypothesis, result, tradeoff, and next step. Timeline is flexible; budget roughly one focused week per milestone.

## 1. Understand the baseline

Run the demo and tests. Follow one request from the CLI through retrieval, provider, scorer, and JSON artifact. Explain why missing a second fact lowers coverage and why safety gates quality to zero.

Deliverable: a diagram and a failure taxonomy. Acceptance: reproduce an incomplete answer, attack response, abstention, and provider fallback without changing expected labels.

## 2. Make the dataset credible

Write at least 50 development scenarios across task summaries, deadlines, ownership, conflicting documents, stale facts, ambiguous requests, no-answer questions, and malicious source text. Have another person independently author hidden scenarios. Separate tenants, entities, and templates across splits. Define inclusion rules, label rationale, severity, and dataset versioning.

Deliverable: dataset card. Acceptance: duplicate detection, schema validation, split-overlap report, and per-category results. Keep hidden data out of any prompt-generation input.

## 3. Add real providers

Implement a provider protocol accepting messages, authorized retrieved documents, a timeout, and an output schema. Add adapters for two providers using their current official documentation. Read keys from environment variables and never commit them. Replace `fact` shortcuts with real source `body` content. Record model identifier, usage, prompt version, retry count, finish reason, and trace ID.

Deliverable: a real answer with source IDs. Acceptance: mock tests for timeout, rate limiting, invalid JSON, transient failure, and exhausted fallback. Bound retries and total deadline. Track actual token usage and label price assumptions with their date. Never silently mix simulated and live results.

## 4. Build and calibrate a judge

Create a rubric for groundedness, completeness, usefulness, and refusal appropriateness. Require structured scores and short evidence references. Blind the judge to provider identity, randomize answer order, and repeat reversed-order comparisons. Treat answer text as untrusted input. Keep judge credentials and tools inaccessible to evaluated agents.

Deliverable: a double-labeled calibration set with adjudication. Acceptance: agreement/confusion matrices, false-pass and false-fail rates with uncertainty, and documented disagreement examples. Judge confidence is not statistical confidence. Keep deterministic security gates alongside judge scores.

## 5. Benchmark and route

Benchmark multiple models on the same cases with repeated samples, concurrency caps, and fixed request budgets. Report quality by category, p50/p95 latency, token cost, errors, and fallback rate. Build a Pareto frontier and route only from information available at request time.

Deliverable: routing decision record. Acceptance: lower expected cost at a prespecified quality floor on independent data; outage drills preserve the request deadline. Do not route using expected answers or test category labels.

## 6. Implement actual self-improvement

Build a proposer that receives sanitized development failures and suggests a versioned prompt patch. Bound candidates, iterations, time, and spend. Reject changes that weaken tool permissions or safety gates. Run each candidate on development cases, retain artifacts for every attempt, and freeze the winner before one hidden evaluation.

Deliverable: candidate lineage and reproducible promotion report. Acceptance: no hidden examples in proposer inputs, no safety regressions, rollback support, and human approval before serving users. Repeated adaptive searches can overfit the development set.

## 7. Production and online evaluation

Add an authenticated API, tenant authorization from verified identity, durable run storage, queue workers, idempotent jobs, and telemetry. Containerize workers and define resource limits, readiness, graceful shutdown, and restricted secret access. Add retention/deletion policies and audit trails. Build shadow evaluation before a randomized rollout.

Deliverable: architecture review plus a load/failure test. Acceptance: scoped tenant access, bounded queues, recovery from worker interruption, trace correlation, and an A/B plan with a primary metric, guardrails, minimum detectable effect, sample-size reasoning, and stopping rules. Online outcomes include task completion and edits, not just judge scores.

## Portfolio discussion

Explain a regression caught by your system, a judge disagreement you resolved, why a routing tradeoff was justified, how you prevented hidden-data leakage, and what you would refuse to infer from a small sample. Use measured results from your extensions; do not present the synthetic simulator as production model performance.
