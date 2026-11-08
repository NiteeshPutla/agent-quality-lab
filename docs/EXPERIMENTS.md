> Legacy v1 simulator notes. For the current service, start with the root README and V2_LEARNING_PATH.md.

# Experiment protocol

Before collecting results, write a hypothesis, target population, sampling unit, primary metric, safety guardrails, practical margin, budget, and decision rule. Freeze dataset and prompt versions. Keep comparable provider parameters and record model revisions.

The starter comparison computes candidate-minus-baseline quality per case and resamples matched cases with a fixed seed. A 95% bootstrap interval wholly below minus the margin signals regression; wholly above the margin signals improvement; everything else is inconclusive. Inconclusive does not establish equivalence. The demo selects by development mean and safety only; its selection is a teaching heuristic, not a significance-based promotion rule.

For real stochastic models, collect repeated responses within each scenario and use a hierarchical/clustered analysis with scenario as the unit. Correlated paraphrases must remain in the same cluster. Report uncertainty for category slices. Correct for multiple comparisons or prespecify a small number of decisions. Never repeatedly peek and stop when a result looks favorable.

## Judge calibration

1. Sample representative successes and difficult failures, with enough security and refusal cases.
2. Have two humans independently apply the same anchored rubric.
3. Adjudicate disagreements and retain original annotations.
4. Compare judge versus adjudicated labels per dimension and category.
5. Inspect false passes, false failures, order effects, verbosity bias, and self-preference.
6. Lock a calibration version and recheck when judge models or prompts change.

Useful reports include agreement, confusion matrices, precision/recall for unacceptable answers, and uncertainty intervals. Ordinal score agreement may use weighted kappa. Explain rubric ambiguity before assuming every disagreement is model error.

## Online experiment template

Hypothesis: a routing policy reduces cost while preserving task success.
Randomization: user or workspace, chosen to prevent cross-condition contamination.
Primary outcome: completed intended task within a specified window.
Guardrails: permission violations, unsupported claims, error rate, latency, cost.
Plan: define minimum effect, sample-size assumptions, experiment duration, and sequential-testing policy before launch. Keep offline judge scores as diagnostics; do not assume they equal user value.
