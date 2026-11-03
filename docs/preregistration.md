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
| X | Cross-lingual (exploratory) | `hi`/`gu` query over English passages. With the English-passage rule below this equals R3 for `hi`/`gu`, so it is no longer run separately | Exploratory |

R3 and R4 count both failure directions: answering with the old value (stale) and applying the new value where the question asks about the old period (too new). Questions about past periods are exploratory.

Mitigations (§7 below gives the tests):

| Code | Mitigation | Applied to |
|---|---|---|
| M-a1 | Date-stamped prompt: today's date, plus an instruction to answer with the rule in force today | R1 (confirmatory), R3 (secondary) |
| M-a2 | Validity-statement prompt: each passage states the period it applies to | R1, R3 (secondary) |
| M-b | Conflict-checker agent: drafts an answer, checks it against the retrieved current rule, re-answers on disagreement | R1 (confirmatory), R3 (secondary) |
| M-c | Version-filtered retrieval: keeps only chunks whose effective window contains the as-of date | R1 (confirmatory) |
| — | Robustness: dates missing or wrong in the metadata, for M-a2 and M-c | Exploratory |

**Passage language (decided 2026-11-03 from the dev baseline).** In the first dev baseline, Hindi and Gujarati questions in R3 mostly received English passages (the old version often has no hi/gu source), while R1 and R2 received same-language passages, and 52 of 56 X prompts were identical to R3. That confounded the language comparison with the documents shown. Confirmatory conditions (R0–R4) therefore use English passages for every question language (`doc_language: english`), so H2 changes only the question language. Same-language passages where they exist are an exploratory run (`doc_language: native`, `configs/experiments/dev-native.yaml`).

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
- **Judge validation:** a human labels a stratified sample of answers, with the automatic label hidden. The sample covers languages and conditions, and favours answers the judge decided (about two thirds), with the rest decided by the matcher so the matcher is checked too. Report Cohen's κ and accuracy of the automatic label against the human label, separately for judge-decided and matcher-decided answers.
  - **Settled 2026-11-01 (draft, before any test run):** the project has one human labeller, so human-vs-human κ cannot be reported and this is a stated limitation. Calibration now uses about 45 labelled dev answers (`policydrift label-sheet`, `label-agree`), not 200. A larger validation sample drawn from the test-split answers is **OPEN** (proposed: 100 answers, labelled after the final run).
  - **Dev calibration result (2026-11-03):** 45 dev answers labelled by the single labeller. The automatic label matched the human label on all 45 (30 judge-decided, 15 matcher-decided; κ = 1.0). Weak evidence: 38 of 45 labels are `current`, only 3 `outdated`, 2 `other` and 2 `refusal`, and the sample had several duplicate answers. It shows no systematic scorer fault, not that the rare classes are scored well. Next time `pick_sample` drops duplicate answers and over-samples rare labels.
  - **OPEN:** confirm the κ target. Proposed: κ ≥ 0.80. If the target is missed, everything the judge decided is labelled by humans instead. Answers the judge cannot parse are labelled `unresolved` and reported, never silently dropped.

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
- **Model list (draft 2026-11-01; freeze before any test-split run):** `openai/gpt-oss-20b` (small, open-weight, Groq), `gemini-3.1-flash-lite` and `gemini-2.5-flash-lite` (small, closed, Gemini). `qwen/qwen3.8-27b` was dropped on 2026-11-03: Groq's free tier rate-limited it so hard that 476 dev calls took hours, which would make the test run impractical. Groq's free text models are only gpt-oss-120b (the judge), gpt-oss-20b, gpt-oss-safeguard-20b, qwen and allam-2-7b, so the other two answerers are Gemini models; a weakness is that two of three share one provider and one model family's training lineage. `gemini-3.8-flash` is registered but not in the baseline because of its free-tier rate limits. The judge is `openai/gpt-oss-120b`, which is not one of the answering models. Exact model IDs and the versions each response reports are logged in `runs/<run_id>/run.json`. Free-tier availability changes, so a model that disappears before the final run is replaced and the change is logged here.
- **Token budget (draft 2026-11-02, from dev):** answers are requested with `max_tokens` 2048. In the dev baseline 84 of 476 `gpt-oss-20b` calls (18%) returned nothing visible because hidden reasoning used the whole budget (`finish_reason=length`). Such a call is retried once with 8192 tokens (`retry_max_tokens`); the budget used is logged per answer. An answer still empty after that is `missing` and excluded, as in §10.
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

### Benchmark freeze (milestone 2e)

The test split was written and checksummed on 2026-11-01, before any model was run on any benchmark item.

| Field | Value |
|---|---|
| Split unit | scheme (all facts of a scheme go to one side), seed 20261101, see `data/benchmark/split.json` |
| Test | 57 items, 28 facts, schemes: gst, income-tax-new-regime, kcc-miss, msp-kharif, msp-rabi, nmmss, scss-mis |
| Dev | 28 items, 14 facts, schemes: capital-gains, pm-mudra, pm-svanidhi, pmay-urban, pmuy-subsidy, rural-employment-guarantee |
| Test file SHA-256 | `9f708605dc265c6a1edf14b866d0a92815eb31284bccc20ae5e86be2196dc526` (`data/benchmark/test/items.jsonl`; record in `FROZEN.json`) |
| Built from commit | `de09501ac71ac5184fedb835fe14f585e1a541b2` |
| Confirmatory test items | 56 of 57. Excluded from confirmatory analysis and reported separately: `tds-rent-threshold/scenario` (reviewer flag: section 194-IB vs 194-I). The unconfirmed PMUY refills fact fell in the dev split. |
| Known limits at freeze | One reviewer for all three languages; Gujarati has no second check; old values for several facts are only restated (GST, capital gains, income-tax thresholds, KCC collateral-free limit, MIS limits); kharif MSP items expire about May-Jun 2027; hi/gu source documents are missing for the MSP, tds and KCC-v2 facts, so those reach hi/gu questions only through the cross-lingual condition. |

The "items per language" OPEN item above is settled as: all verified test items. The power check on dev discordance rates is still open.

## Deviation log

Every change after the freeze is appended here with date, what changed, why, and whether it was made before or after seeing test-split results.

| Date | Change | Reason | Before/after seeing test results |
|---|---|---|---|
