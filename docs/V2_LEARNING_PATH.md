# Build toward a production platform

1. **Service fundamentals:** run the API and worker; submit duplicate requests; kill a worker; observe lease recovery. Read `store.py`, then explain at-least-once execution and fencing.
2. **Agent quality:** inspect `retrieve` and `score`; add conflicting-source and time-sensitive cases; demonstrate why lexical retrieval and phrase matching fail. Replace retrieval with a measured search baseline while retaining pre-filter authorization.
3. **Real providers:** use your account's model IDs; evaluate identical cases with repeats; inspect usage, failures and latency. Add transport fault tests. Record reproducible model revisions and pricing assumptions separately.
4. **Judge calibration:** independently label representative responses; run the calibration utility; add confidence intervals and category slices; test adversarial output and order bias. Establish a false-pass tolerance before using semantic scores in promotions.
5. **Statistical experiments:** expand to independently authored clusters; run a power analysis for a practical effect. Evaluate per-category regressions and multiplicity. Treat the 20-cluster threshold as a minimum guard only.
6. **Self-improvement:** run one proposer experiment; review its lineage and failed cases; extend to a capped search with explicit token/cost budgets. Freeze candidates before independently authored holdout evaluation.
7. **Serving gateway:** create a separate latency/cost-aware router; declare fallback policies and record every attempt. Keep benchmark model identity stable. Add circuit breakers, budget accounting and timeout propagation.
8. **Distributed operations:** migrate the store to PostgreSQL; implement versioned migrations, queue fairness and tenant quotas; add traces/metrics and cancellation propagation. Demonstrate recovery and backup restoration under fault injection.
9. **Online outcomes:** add shadow evaluation, randomized workspace assignment and user-task completion metrics. Prespecify experiment stopping rules and privacy retention. Compare offline improvement with real outcomes.

For each milestone, produce a small implementation change, a meaningful failure test, measured results, and a decision record. Use the original introductory docs for background, but follow the v2 README for the executable service.
