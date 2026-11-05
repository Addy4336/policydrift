# Phase 4 dev results (draft, 2026-11-05, updated)

Dev split only (28 items x en/hi/gu, R1 = standard top-k over the whole store, English passages for every question language). Nothing here was run on the test split. These are tuning-stage numbers, not confirmatory results.

Outdated-answer rate on **matched answers** (an answer counts only if both the baseline and the mitigation produced one). "Fixed" = outdated in the baseline, not outdated with the mitigation. "Broke" = the reverse.

| Mitigation | Model | n | Baseline | Mitigation | Fixed | Broke | Calls/answer | Tokens/answer |
|---|---|---|---|---|---|---|---|---|
| M-a1 date-stamped prompt | gemini-3.1-flash-lite | 79 | 13% | 13% | 0 | 0 | 1.0 | 893 |
| M-a1 | gemini-3.5-flash-lite | 84 | 19% | 18% | 1 | 0 | 1.0 | 886 |
| M-a1 | gpt-oss-20b | 69 | 3% | 6% | 0 | 2 | 1.0 | 1133 |
| M-c version filter | gemini-3.1-flash-lite | 79 | 13% | 0% | 10 | 0 | 1.0 | 820 |
| M-c | gemini-3.5-flash-lite | 84 | 19% | 0% | 16 | 0 | 1.0 | 814 |
| M-c | gpt-oss-20b | 69 | 3% | 0% | 2 | 0 | 1.0 | 1029 |
| M-a2 validity statement | gemini-3.1-flash-lite | 79 | 13% | 11% | 2 | 1 | 1.0 | 954 |
| M-a2 | gemini-3.5-flash-lite | 84 | 19% | 18% | 1 | 0 | 1.0 | 940 |
| M-b conflict checker | gemini-3.1-flash-lite | 79 | 13% | 8% | 4 | 0 | 2.1 | 1974 |
| M-b | gemini-3.5-flash-lite | 84 | 19% | 11% | 7 | 0 | 2.1 | 1981 |

Baseline mean tokens per answer: 792 (3.1), 839 (3.5), 1040 (gpt-oss-20b).

## What the dev numbers say

- **M-c removes the stale answers, by construction.** The filter drops chunks whose effective window excludes the as-of date, so the old version cannot reach the model. This holds only while the effective dates are correct. The pre-registered robustness test (missing or wrong dates) is exploratory and has not been run.
- **M-b roughly halves the rate** (pooled 16% to 9% over the two Gemini models, 11 fixed and 0 broken) at about 2.1 calls and 2.4x the tokens per answer.
- **M-a1 does nothing measurable.** Stating today's date and asking for the rule in force today changed 1 answer for the better and 2 for the worse.
- **M-a2 barely helps.** Pooled over the two Gemini models 16% to 15% (3 fixed, 1 broken). Prompt-only mitigations (M-a1, M-a2) do not fix the problem on dev.
- **gpt-oss-20b has little room to improve.** Its baseline R1 rate is 3% on the items it answered, so it cannot show a mitigation effect here.

## Caveats

- Dev split, 28 items, one labeller for judge calibration; differences of one or two answers are noise.
- gpt-oss-20b's baseline covers 24 of 28 items, hence the smaller n.
- gemini-3.1-flash-lite M-c now has all 84 answers (gap-filled by a rerun).
- Latency is not reported here: recorded latencies mix cached and uncached calls and free-tier waits. Phase 5 computes it from uncached calls only, as pre-registered.
- Not yet done: gpt-oss-20b M-b (restarted, 21 of 84 answers so far; Groq is slow), M-a2 for gpt-oss-20b, and the secondary R3 runs.
