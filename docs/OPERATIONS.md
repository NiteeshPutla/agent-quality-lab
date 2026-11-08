# Operations and design decisions

## Deployment scope

API and worker are separate processes sharing a local SQLite database. WAL and BEGIN IMMEDIATE serialize queue mutations. Start additional workers only on the same host and local filesystem; migrate the store to PostgreSQL with row locks before multi-host deployment. The store schema is version 1, installed idempotently; future schema upgrades require explicit migration scripts. Container images and CI are provided, but container execution must be validated on a Docker-equipped host.

## Recovery and consistency

A worker claims a run with a unique owner token and a 120-second lease. Heartbeats renew every 10 seconds; provider retry chains have a 60-second deadline. Case results use (run, case, sample) uniqueness. A replacement resumes persisted cases. Writes and completion check ownership, state, and lease. Three abandoned claims exhaust recovery and fail the run. Explicit provider/schema errors fail immediately. Cancellation prevents subsequent writes; an in-flight network call may finish or incur cost before the next heartbeat.

The external provider call and database commit cannot be atomic: a crash between them may repeat a paid call. This is at-least-once execution with idempotent result persistence, not exactly-once billing. Use bounded request budgets and reconcile provider billing independently.

## Security and privacy

Tokens map to tenant identity on the server; caller-supplied tenant fields are rejected. Tokens must contain at least 24 characters, should be randomly generated and rotated, and must travel over TLS outside localhost. Per-document readers are checked before retrieval. Evaluation users can run predefined fixtures within their tenant; this is not a general impersonation API. API tokens are coarse tenant credentials, not user roles/OIDC.

Run snapshots contain synthetic source documents and labels for reproducibility. Results retain answer hashes, source IDs, scores, latency and usage, not raw answers or judge rationale. Request logs omit bodies and tokens. Database/backup encryption and retention must be established before ingesting real data. Hashes do not anonymize low-entropy secrets. Do not expose the local dashboard directly to the internet; add TLS, OIDC, rate limits, request-size controls and role-based access for a shared deployment.

## Evaluation integrity

The run snapshots its selected tenant/split and fingerprints the dataset, prompt, code and scorer. Comparison requires matched datasets, splits, repeats, judge configuration and result sets. Samples are aggregated within clusters; bootstrap resampling uses independent clusters. Safety regression blocks promotion regardless of mean improvement. The minimum-cluster gate blocks small demos from passing. Unchanged or overlapping intervals remain inconclusive.

Scorers check answer terms, abstention and expected citations. They do not prove entailment. The optional judge adds semantic scores but requires external human calibration. A judge error fails the run; partial results cannot pass comparison. The prompt improvement command changes a prompt string only; it cannot edit authorization code or worker behavior. Its candidate is evaluated once on dev and does not inspect holdout.

## Monitoring and response

Use `/health/live` for liveness and `/health/ready` for configured authentication/database access. Readiness does not prove worker health. Inspect queued age and running leases through authenticated run APIs/database; add alerts for growing queue age, exhausted claims, provider failure rates, tail latency, and token volume. HTTP logs contain request IDs, status and elapsed time. Worker failure logs contain run ID and exception class only.

For a failed run, inspect its error type, check worker credentials/connectivity, then submit a new run with a new idempotency key. For a stuck worker, restart it and allow lease expiry. Back up SQLite using its online backup API or a clean shutdown; copying only the main file while WAL is active can lose data. Restore and verify a backup in a separate environment before relying on it.

## Remaining production gates

Run authenticated live smoke tests, load and soak tests, restore drills, dependency vulnerability scans, abuse testing, independent security review, and dataset/judge validation. Adopt secret management and TLS; implement retention/deletion, RBAC and resource quotas. Choose operational SLOs from actual measurements. No production uptime, compliance certification or scalability claims have been established by this project.
