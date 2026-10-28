# Pre-registration: Stale by Default

- **Project:** PolicyDrift
- **Working title:** Stale by Default: Measuring and Mitigating Outdated-Rule Answers in Multilingual Policy RAG Agents
- **Hypotheses recorded:** 2026-10-28, before any data collection, benchmark construction or model runs. The git commit that adds this file is the timestamp.
- **Status:** hypotheses frozen. The operationalisation below is a **draft**. It includes the framing accepted on 2026-10-28 (see [related_work.md §7](related_work.md#7-differentiation-recommended-changes)). Items marked **OPEN** still need a decision. The whole section is frozen before any Phase 3 run touches the test split.

## Research question

When government rules change (scholarships, welfare schemes, subsidy limits, tax slabs), do LLM-based RAG agents answer from the CURRENT retrieved rule, or fall back to OUTDATED rules memorised during training? Does this get worse in Hindi and Gujarati than in English? Which mitigations fix it?

## Hypotheses (verbatim; do not edit)

- **H1.** Even with the current rule retrieved, models give outdated answers at a measurable rate.
- **H2.** The outdated-answer rate is higher for Hindi and Gujarati queries than English.
- **H3.** Mitigations (date-stamped prompts, a conflict-checker agent, version-filtered retrieval) reduce the rate, with different cost/latency tradeoffs.

## Operationalisation (draft; frozen before Phase 3)

Every item must be final, committed and recorded under "Freeze" below before the first test-split run. **Confirmatory** analyses test H1–H3 as written. **Exploratory** analyses are reported as such and are never used to claim support for a hypothesis.

### 1. Unit of analysis
One answer = one benchmark item × language × model × condition. A benchmark item is one rule fact that changed between an old and a current version, asked in `en`, `hi` and `gu`, so items are paired across languages.

### 2. Conditions

Retrieval conditions:

| Code | Condition | What the model sees | Role |
|---|---|---|---|
| R0 | No retrieval | Question only | Knowledge probe (§3) and baseline |
| R1 | Standard RAG | Top-k chunks from the full multi-version store, with no version filter | Realistic baseline; H3 baseline |
| R2 | Current only | Top-k chunks from the current version only | H1 (confirmatory) |
| R3 | Both versions, dates shown | Matched chunks from the old and current versions, each labelled with its effective dates | H1 (confirmatory) |
| R4 | Both versions, dates hidden | As R3, without effective-date labels | Exploratory: do models use date metadata? |
| X | Cross-lingual | `hi`/`gu` query against an English-only official source vs a same-language source, where one exists | Exploratory |

R3 and R4 count both failure directions: answering with the old value (stale) and applying the new value where the question asks about the old period (too new). Questions about past periods are exploratory.

Mitigations (§7 below gives the tests):

| Code | Mitigation | Applied to |
|---|---|---|
| M-a1 | Date-stamped prompt: today's date, plus an instruction to answer with the rule in force today | R1 (confirmatory), R3 (secondary) |
| M-a2 | Validity-statement prompt: each passage states the period it applies to | R1, R3 (secondary) |
| M-b | Conflict-checker agent: drafts an answer, checks it against the retrieved current rule, re-answers on disagreement | R1 (confirmatory), R3 (secondary) |
| M-c | Version-filtered retrieval: keeps only chunks whose effective window contains the as-of date | R1 (confirmatory) |
| — | Robustness: dates missing or wrong in the metadata, for M-a2 and M-c | Exploratory |

Retrieval settings stay fixed across conditions: k, chunking, passage order (current-first and old-first, counterbalanced in R3/R4) and the embedding model.

### 3. Knowledge state (closed-book probe)
Each model's R0 answer to each item is labelled `knows_old`, `knows_current` or `neither`, using the same scorer as §4. This is recorded before any RAG condition is scored.
- **Confirmatory H1 analysis:** all items.
- **Secondary H1 analysis:** the outdated rate among `knows_old` items only. This is the direct test of "falls back to memorised rules".
- **Exploratory stratification:**
  - whether the rule changed before or after the model's stated knowledge cutoff
  - fact type: amount, income limit, age, date/deadline, categorical eligibility

### 4. Outcome and labelling
- **Labels:** each answer is labelled `current`, `outdated`, `other` or `refusal`.
- **Primary outcome:** outdated-answer rate = `outdated` / all answers. `refusal` and `other` stay in the denominator.
- **Sensitivity analysis:** the same rate with refusals excluded.
- **Scoring order:**
  1. A deterministic matcher normalises numbers, covering lakh/crore, Devanagari and Gujarati digits, units and dates, then compares the answer with the old and current values of the item.
  2. An LLM judge sees only answers the matcher cannot decide. It is framed as a *matching* task ("which of these values does the answer state, if any?"), so it needs no knowledge of the rule.
- **Judge validation:** humans double-label a stratified sample of judged answers. The sample covers languages and conditions, at least 200 answers. Report Cohen's κ for judge vs human and for human vs human.
  - **OPEN:** confirm the κ target. Proposed: κ ≥ 0.80. If the target is missed, everything the judge decided is labelled by humans instead.

### 5. H1 decision rule (confirmatory)
H1 is tested separately in R2 and R3, on outdated rates pooled across models and languages. The 95% CI comes from a cluster bootstrap over items, with 10,000 resamples. H1 is supported in a condition if the CI's lower bound is above the threshold *τ* after Holm correction across the two conditions. Per-model and per-language rates are reported alongside.
- **OPEN:** choose *τ*. Proposed: τ = 2%. In English with only up-to-date evidence, Stale-Document Poisoning found models failed to follow it in about 0–3% of trials. A 2% threshold separates a real effect from scorer noise without assuming a large one.

### 6. H2 decision rule (confirmatory)
- **Model:** mixed-effects logistic regression of the outdated outcome on language, condition (R2/R3) and model as fixed effects, plus a random intercept per item. Fitted on R2 + R3 answers.
- **Contrasts:** `hi` > `en` and `gu` > `en`, each one-sided, because H2 states a direction. Holm correction across the two.
- **Also reported:** two-sided 95% CIs on odds ratios and rate differences, plus per-pair exact McNemar tests as a robustness check.
- If the model fails to converge, the pre-specified fallback is exact McNemar on paired item × model outcomes, with Holm correction.

### 7. H3 decision rule (confirmatory)
- **Tests:** each of M-a1, M-b and M-c is compared with R1 on the same items, models and languages, using an exact McNemar test on the binary outdated outcome. Each test is one-sided (a reduction) and Holm-corrected across the three. Effect sizes are paired rate differences with 95% paired-bootstrap CIs.
- **Cost:** mean prompt and completion tokens per answer, and LLM calls per answer.
- **Latency:** median and p90 wall-clock time per answer, measured only on uncached calls. Cache hits are excluded, and run timestamps are logged so free-tier load can be inspected.
- "Different tradeoffs" is described, not tested: the report shows accuracy, outdated rate, tokens and latency per mitigation as a table and a Pareto plot.

### 8. Alpha and multiplicity
α = 0.05. Holm correction is applied within each hypothesis family: H1 (2 tests), H2 (2 tests) and H3 (3 tests). Exploratory analyses get no correction and are labelled exploratory.

### 9. Models, decoding and seeds
- **OPEN (decide in Phase 3, before any test-split run):** the model list. At least three free-tier models, including at least one small open-weight model, because small models were more affected in prior work. Record exact model IDs and versions.
- **Decoding:** temperature 0, with a fixed seed where the API supports one. Nondeterminism is estimated by re-running a 10% subsample three times and reported.

### 10. Splits, exclusions and sample size
- **Splits:** dev/test are fixed in Phase 2. All prompt, mitigation and judge development uses dev only.
- **Exclusions decided before results:**
  - items flagged invalid during human verification
  - items whose official sources turn out to be ambiguous
  - answers missing after 5 retries, which are recorded as `missing` and are not refusals
- **Sample size:** all verified test items. There is no optional stopping.
  - **OPEN:** the target number of items per language, set in Phase 2 after a power check on dev-split discordance rates.

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
