# Pre-registration: Stale by Default

- **Project:** PolicyDrift
- **Working title:** Stale by Default: Measuring and Mitigating Outdated-Rule Answers in Multilingual Policy RAG Agents
- **Hypotheses recorded:** 2026-10-28, before any data collection, benchmark construction or model runs. The git commit that adds this file is the timestamp.
- **Status:** hypotheses frozen. The operationalisation below is still open and must be completed and frozen before any Phase 3 run touches the test split.

## Research question

When government rules change (scholarships, welfare schemes, subsidy limits, tax slabs), do LLM-based RAG agents answer from the CURRENT retrieved rule, or fall back to OUTDATED rules memorised during training? Does this get worse in Hindi and Gujarati than in English? Which mitigations fix it?

## Hypotheses (verbatim; do not edit)

- **H1.** Even with the current rule retrieved, models give outdated answers at a measurable rate.
- **H2.** The outdated-answer rate is higher for Hindi and Gujarati queries than English.
- **H3.** Mitigations (date-stamped prompts, a conflict-checker agent, version-filtered retrieval) reduce the rate, with different cost/latency tradeoffs.

## Operationalisation (to complete before Phase 3; frozen after)

Each item must be filled in, committed and recorded under "Freeze" below before the first test-split run.

1. **Unit of analysis:** e.g. one (benchmark item × model × condition × seed) answer.
2. **Primary outcome:** outdated-answer rate = share of answers labelled `outdated` among all answers. The labels are `current`, `outdated`, `other` and `refusal`. Define the denominator, including how `refusal` and `other` are treated.
3. **Labelling procedure:** rule-based matching first; an LLM judge only for items the rules cannot decide. State the target agreement with human labels and the sample size used to measure it.
4. **H1 decision rule:** the condition it applies to (current version retrieved), and what counts as "measurable". For example, the lower bound of the 95% CI is above a stated threshold.
5. **H2 decision rule:** the comparison (Hindi vs English and Gujarati vs English on paired items), the test (e.g. McNemar on item pairs, or a mixed-effects logistic model with item and model random effects), and the direction (one- or two-sided).
6. **H3 decision rule:** each mitigation compared with the matching baseline on the same items, the paired test, and how cost (tokens) and latency are reported.
7. **Alpha and multiplicity:** significance level and correction method (e.g. Holm across the H2/H3 comparisons).
8. **Models, conditions and seeds:** the fixed list, chosen before any test-split run.
9. **Exclusion rules:** e.g. API errors after N retries, or items flagged invalid during human verification. Exclusions are decided on the dev split, or before results are seen.
10. **Stopping rule / sample size:** number of items per language, and the reasoning for it.

## Freeze

| Field | Value |
|---|---|
| Operationalisation frozen on | _not yet_ |
| Commit hash | _not yet_ |
| External registration (optional, e.g. OSF / AsPredicted) | _not yet_ |

## Deviation log

Every change after the freeze is appended here with date, what changed, why, and whether it was made before or after seeing test-split results.

| Date | Change | Reason | Before/after seeing test results |
|---|---|---|---|
