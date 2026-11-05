# Phase 4 dev results (draft, 2026-11-05, revision 3)

Dev split only (28 items x en/hi/gu = 84 answers per model, R1 = standard top-k over the whole store, English passages for every question language). Nothing here was run on the test split. These are tuning-stage numbers, not confirmatory results.

Revision 2 follows an external review of revision 1. Changes: the gpt-oss-20b baseline was completed (it had covered only 72 of the 84 slots and none of the hard SVANidhi items, which made it look like a 3% "floor case"; the true rate is 17%), full label distributions and per-language splits were added, a cluster-aware interval was added, the residual stale answers under M-b were inspected, and the M-c missing/wrong-dates robustness run was done.

The outdated rate below counts an answer as outdated when its label is `outdated`; it is computed on **matched answers** (both arms produced an answer). "Fixed" = outdated in the baseline, not outdated with the mitigation; "broke" = the reverse.

## 1. Headline (matched answers, R1)

| Mitigation | Model | n | Baseline | Mitigation | Fixed | Broke | Calls/answer |
|---|---|---|---|---|---|---|---|
| M-a1 date-stamped prompt | gemini-3.1-flash-lite | 79 | 13% | 13% | 0 | 0 | 1.0 |
| M-a1 | gemini-3.5-flash-lite | 84 | 19% | 18% | 1 | 0 | 1.0 |
| M-a1 | gpt-oss-20b | 84 | 17% | 19% | 0 | 2 | 1.0 |
| M-a2 validity statement | gemini-3.1-flash-lite | 79 | 13% | 11% | 2 | 1 | 1.0 |
| M-a2 | gemini-3.5-flash-lite | 84 | 19% | 18% | 1 | 0 | 1.0 |
| M-b conflict checker | gemini-3.1-flash-lite | 79 | 13% | 8% | 4 | 0 | 2.1 |
| M-b | gemini-3.5-flash-lite | 84 | 19% | 11% | 7 | 0 | 2.1 |
| M-b | gpt-oss-20b | 84 | 17% | 10% | 6 | 0 | 2.2 |
| M-c version filter | gemini-3.1-flash-lite | 79 | 13% | 0% | 10 | 0 | 1.0 |
| M-c | gemini-3.5-flash-lite | 84 | 19% | 0% | 16 | 0 | 1.0 |
| M-c | gpt-oss-20b | 84 | 17% | 0% | 14 | 0 | 1.0 |

Tokens per answer, baseline: 792 (3.1), 839 (3.5), 1040 (gpt-oss-20b). M-b uses about 2.4 to 2.5 times that; M-a1, M-a2 and M-c use about 1.0 to 1.2 times. Latency is not reported: recorded values mix cached calls with free-tier waits. Phase 5 computes it from uncached calls only.

## 2. Cluster-aware effect (pooled over models, descriptive)

Bootstrap over the 14 facts (the real cluster: each fact appears in 2 question styles x 3 languages x 3 models), 5000 resamples. Exact McNemar on answer pairs is shown for reference only, since answers are not independent.

| Mitigation | n | Change in outdated rate | 95% CI over facts | Fixed / broke |
|---|---|---|---|---|
| M-a1 | 247 | +0.4 pts | [-1.2, +2.4] | 1 / 2 |
| M-a2 | 163 | -1.2 pts | [-5.5, +1.8] | 3 / 1 |
| M-b | 247 | -6.9 pts | [-14.5, -0.8] | 17 / 0 |
| M-c | 247 | -16.2 pts | [-35.1, -1.6] | 40 / 0 |

Pooled baseline 16% (40 of 247). The pooled figures are descriptive; the three models share items. The M-a1 and M-a2 intervals include zero but are also narrow around it, so "no effect larger than a few points on dev" is supported, "no effect at all" is not.

## 3. Full label distribution (all 84 slots per arm)

Not-outdated is not the same as correct, and abstaining lowers the outdated rate. Counts of current / outdated / refusal / other / missing:

| Arm | gemini-3.1 | gemini-3.5 | gpt-oss-20b |
|---|---|---|---|
| Baseline R1 | 64 / 10 / 3 / 2 / 5 | 62 / 16 / 4 / 2 / 0 | 63 / 14 / 2 / 5 / 0 |
| M-a1 | 64 / 15 / 3 / 2 / 0 | 63 / 15 / 4 / 2 / 0 | 64 / 16 / 2 / 2 / 0 |
| M-a2 | 66 / 14 / 3 / 1 / 0 | 63 / 15 / 4 / 2 / 0 | not run |
| M-b | 67 / 9 / 7 / 0 / 1 | 65 / 9 / 9 / 1 / 0 | 68 / 8 / 8 / 0 / 0 |
| M-c | 72 / 0 / 11 / 1 / 0 | 73 / 0 / 11 / 0 / 0 | 72 / 0 / 11 / 1 / 0 |

(The gemini-3.1 baseline has 5 missing slots, which is why its unmatched baseline shows 10 outdated of 79; the 15 under M-a1 is unmatched over 84.)

- **Abstention is part of the mechanism.** Refusals rise from 2 to 4 at baseline to 11 under M-c and 7 to 9 under M-b. M-c converts roughly 8 stale answers per model into refusals, because for some questions only the old-version chunk was retrieved and the filter removes it. Current-correct answers also rise (62-64 to 72-73 under M-c), so M-c is not just abstaining, but 11 of 84 questions go unanswered. A fair report of M-c is "0% outdated, 13% refusals".
- **Wrong-but-not-old answers ("other") are rare in these runs** (0 to 5 per arm) but are invisible in an outdated-only table, so the label distribution should be in the paper.

## 4. Per language (matched, outdated baseline -> mitigation)

| | en | hi | gu |
|---|---|---|---|
| M-c, gemini-3.1 | 6 -> 0 of 28 | 2 -> 0 of 25 | 2 -> 0 of 26 |
| M-c, gemini-3.5 | 7 -> 0 of 28 | 5 -> 0 of 28 | 4 -> 0 of 28 |
| M-c, gpt-oss-20b | 6 -> 0 of 28 | 4 -> 0 of 28 | 4 -> 0 of 28 |
| M-b, gemini-3.1 | 6 -> 4 of 28 | 2 -> 1 of 25 | 2 -> 1 of 26 |
| M-b, gemini-3.5 | 7 -> 3 of 28 | 5 -> 3 of 28 | 4 -> 3 of 28 |
| M-b, gpt-oss-20b | 6 -> 3 of 28 | 4 -> 3 of 28 | 4 -> 2 of 28 |

M-c behaves the same in all three languages. M-b helps in all three, with the largest drop in English; counts are too small to say more. Note the baseline is not worse in hi/gu than in en (6, 2, 2 and 7, 5, 4 and 6, 4, 4): on dev, H2 is not supported, as already recorded.

## 5. Residual stale answers under M-b: a retrieval problem

All 26 stale answers that remain under M-b (across the three models) come from the two SVANidhi loan facts, and in **all 26 the current-version chunk was not in the retrieved context** (`context_has_current = false`). The checker saw only old-version passages, judged the draft consistent with them (22 of 26) or revised to another old-version value (4), so no downstream step could have fixed these. The same holds at baseline: of 40 stale baseline R1 answers (10, 16 and 14), only 2 had the current chunk in context.

Consequence for interpreting H1: in plain R1, staleness on this benchmark is overwhelmingly a **retrieval failure** (the current rule was not retrieved), not the model overriding a retrieved current rule with memorised numbers. H1 as pre-registered concerns the latter and is tested in R2 and R3, where the current chunk is guaranteed present (dev: R2 about 0% outdated, R3 21 to 27%). The paper must keep these two failure modes separate, and the SVANidhi retrieval miss (current chunk ranked below k=4 for these questions) is a documented limitation of the e5-base retriever, to be stated rather than tuned on the test split.

## 6. M-c robustness to wrong or missing dates (exploratory, dev, two Gemini models)

M-c with deliberately corrupted effective dates (hash-chosen chunks, seed 20261101; `date_corruption` in the config):

| Dates | Model | Outdated | Refusal | Current |
|---|---|---|---|---|
| intact | gemini-3.1 / 3.5 | 0 / 0 | 11 / 11 | 72 / 73 |
| 50% of chunks lose both dates | gemini-3.1 | 5 | 12 | 67 |
| | gemini-3.5 | 6 | 12 | 66 |
| 25% of chunks have the window inverted | gemini-3.1 | 0 | 20 | 63 |
| | gemini-3.5 | 0 | 21 | 63 |

(Baseline outdated: 10 and 16.) Missing dates degrade M-c gracefully: it keeps about half of its gain, since undated chunks pass the filter. Inverted dates remove the stale answers but also hide current evidence, so refusals nearly double (11 to 20-21) and correct answers fall by about ten. M-c is therefore only as good as the version metadata; the 0% figure is an upper bound that holds when dates are right.

## 7. What the results support

- **M-c** removes stale answers when the dates are right, at the price of about 13% refusals; with 50% missing dates it halves them; with inverted dates it trades them for refusals.
- **M-b** is the only mitigation that works without version metadata: 40 to 23 stale answers pooled (17 fixed, 0 broken) at about 2.1 calls and 2.4 times the tokens. Its remaining 26 stale answers are all retrieval misses it cannot fix.
- **M-a1 and M-a2** show no effect larger than a few points on dev; prompt-only date hints do not fix the problem here.
- All three models behave alike at R1 once the gpt-oss baseline is complete (13 to 19% stale baseline), so the earlier "gpt-oss has no headroom" remark was wrong and is withdrawn.

## 8. Caveats and open items

- Dev split, 28 items from 14 facts; differences of one or two answers are noise, and the SVANidhi facts carry most of the stale answers.
- gemini-3.1 baseline has 5 missing slots, so its matched n is 79.
- The earlier Phase 3 baseline for gpt-oss-20b (conditions R0 to R4) still covers only 24 of 28 items; the R1 baseline used here was completed separately (`configs/experiments/dev-baseline-oss20b-r1.yaml`). The Phase 3 R0/R2/R3/R4 gpt-oss numbers should be completed before they are reported.
- Judge calibration rests on 45 dev answers from a single labeller with only 3 outdated positives; it needs a second labeller and more positives before the judge numbers are relied on. The labelling sheet should be re-sampled to over-represent outdated and "other" answers, and duplicates dropped.
- Latency and cost use uncached calls only, in Phase 5.
- Not run: M-a2 for gpt-oss-20b and the secondary R3 mitigation runs.

## 9. R3 mitigation runs (revision 3; confirmatory condition for H3)

Run after the external review, on dev, for the two Gemini models (gpt-oss-20b R3 mitigation runs were not completed: Groq's free tier was too slow). All tables are regenerated by `uv run policydrift paper` into `paper/dev/`.

**The current value is not always in the R3 context.** R3 retrieves the top-2 chunks of each version, but for three facts (PMUY refills, SVANidhi first and second loan) those chunks never state the current value (0 of 6, 0 of 6 and 1 of 6 answers per model); the context states it for 67 of 84 answers. Those facts are stale in nearly every answer at every condition, so they inflate the R3 rate without saying anything about models overriding a retrieved rule. Pooled over the two Gemini models, R3 baseline outdated rate:

| Answers counted | n | Outdated | 95% CI (bootstrap over facts) | CI lower bound above tau = 2% |
|---|---|---|---|---|
| All R3 answers | 252 (3 models) | 24.2% | [8.7%, 42.5%] | yes |
| Only answers whose context states the current value | 201 (3 models) | 10.0% | [1.1%, 20.4%] | no |

R2 (current version only) is 0.0% in both. So on dev H1 holds in the loose sense (stale answers occur at R3), and fails the tau rule when counting only answers where the current value was in the context. The test split decides; the dev numbers are not a result.

**Mitigations at R3 (Gemini models, matched answers, one-sided exact McNemar, Holm over three):**

| Mitigation | Counting | n | Baseline | With | Fixed / broke | p (Holm) | Calls | Tokens |
|---|---|---|---|---|---|---|---|---|
| M-a1 date stamp | context has current value | 134 | 6.7% | 0.0% | 9 / 0 | 0.006 | 1.0 | 1.0x |
| M-a2 validity statement | same | 134 | 6.7% | 9.0% | 1 / 4 | 0.97 | 1.0 | 1.0x |
| M-b checker | same | 134 | 6.7% | 0.0% | 9 / 0 | 0.006 | 2.1 | 2.2x |
| M-a1 | all answers | 168 | 20.8% | 13.1% | 13 / 0 | 0.0004 | 1.0 | 1.0x |
| M-a2 | all answers | 168 | 20.8% | 22.6% | 2 / 5 | 0.94 | 1.0 | 1.0x |
| M-b | all answers | 168 | 20.8% | 13.7% | 13 / 1 | 0.002 | 2.1 | 2.2x |

- **The earlier "prompt-only hints do not work" was an R1 artefact.** At R3, where the current value is in the context, the date-stamped prompt (M-a1) fixes every stale answer it can reach at no extra cost, and it does as well as the conflict checker at half the cost. M-a2 (validity statement) does nothing useful.
- Refusals do not rise under M-a1 or M-b (6.0% against 6.7% baseline), and correct answers rise (85% to 94%), unlike M-c at R1 where refusals rise to 13%.
- Bootstrap intervals over 14 facts are wide: the upper bound of the change touches 0.0% for M-a1 and M-b. Treat them as descriptive on dev.
- The M-a1 effect is on 9 answers from a handful of facts (PMAY, PMUY subsidy). It needs the test split to say whether it generalises.

**R1, descriptive (all three models):** M-c 17.9% to 0.0% with 13.1% refusals; M-b 17.5% to 10.4% (9.6% refusals, 2.2x tokens); M-a1 17.9% to 18.3%; M-a2 18.5% to 17.3%.

**Calibration:** a second, stratified labelling sheet (60 answers: 24 outdated, 15 current, 12 other, 9 refusal by automatic label, no duplicates, none from the first sheet) is at `data/benchmark/judge_validation/dev-pool-round2.csv`. It needs a human; 56 of the 60 were decided by the matcher, so it mainly checks the rare classes.
