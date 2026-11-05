# PolicyDrift results (dev split)

## label_distribution

| mitigation | cond | model | n | current | outdated | refusal | other | missing | outdated rate |
|---|---|---|---|---|---|---|---|---|---|
| M-a1 | R1 | gemini-35-flash-lite | 84 | 63 | 15 | 4 | 2 | 0 | 17.9% |
| M-a1 | R1 | gemini-flash-lite | 84 | 64 | 15 | 3 | 2 | 0 | 17.9% |
| M-a1 | R1 | groq-gpt-oss-20b | 84 | 64 | 16 | 2 | 2 | 0 | 19.0% |
| M-a1 | R3 | gemini-35-flash-lite | 84 | 65 | 11 | 7 | 1 | 0 | 13.1% |
| M-a1 | R3 | gemini-flash-lite | 84 | 70 | 11 | 3 | 0 | 0 | 13.1% |
| M-a2 | R1 | gemini-35-flash-lite | 84 | 63 | 15 | 4 | 2 | 0 | 17.9% |
| M-a2 | R1 | gemini-flash-lite | 84 | 66 | 14 | 3 | 1 | 0 | 16.7% |
| M-a2 | R3 | gemini-35-flash-lite | 84 | 56 | 24 | 3 | 1 | 0 | 28.6% |
| M-a2 | R3 | gemini-flash-lite | 84 | 65 | 14 | 4 | 1 | 0 | 16.7% |
| M-b | R1 | gemini-35-flash-lite | 84 | 65 | 9 | 9 | 1 | 0 | 10.7% |
| M-b | R1 | gemini-flash-lite | 83 | 67 | 9 | 7 | 0 | 1 | 10.8% |
| M-b | R1 | groq-gpt-oss-20b | 84 | 68 | 8 | 8 | 0 | 0 | 9.5% |
| M-b | R3 | gemini-flash-lite | 84 | 70 | 11 | 3 | 0 | 0 | 13.1% |
| M-c | R1 | gemini-35-flash-lite | 84 | 73 | 0 | 11 | 0 | 0 | 0.0% |
| M-c | R1 | gemini-flash-lite | 84 | 72 | 0 | 11 | 1 | 0 | 0.0% |
| M-c | R1 | groq-gpt-oss-20b | 84 | 72 | 0 | 11 | 1 | 0 | 0.0% |
| none | R0 | gemini-35-flash-lite | 84 | 32 | 40 | 0 | 12 | 0 | 47.6% |
| none | R0 | gemini-flash-lite | 84 | 20 | 56 | 0 | 8 | 0 | 66.7% |
| none | R0 | groq-gpt-oss-20b | 69 | 3 | 43 | 0 | 23 | 2 | 62.3% |
| none | R1 | gemini-35-flash-lite | 84 | 62 | 16 | 4 | 2 | 0 | 19.0% |
| none | R1 | gemini-flash-lite | 84 | 64 | 15 | 3 | 2 | 0 | 17.9% |
| none | R1 | groq-gpt-oss-20b | 84 | 63 | 14 | 2 | 5 | 0 | 16.7% |
| none | R2 | gemini-35-flash-lite | 84 | 78 | 0 | 5 | 1 | 0 | 0.0% |
| none | R2 | gemini-flash-lite | 79 | 74 | 0 | 4 | 1 | 5 | 0.0% |
| none | R2 | groq-gpt-oss-20b | 67 | 66 | 0 | 0 | 1 | 3 | 0.0% |
| none | R3 | gemini-35-flash-lite | 84 | 55 | 21 | 5 | 3 | 0 | 25.0% |
| none | R3 | gemini-flash-lite | 84 | 66 | 14 | 4 | 0 | 0 | 16.7% |
| none | R3 | groq-gpt-oss-20b | 84 | 55 | 26 | 0 | 3 | 0 | 31.0% |
| none | R4 | gemini-35-flash-lite | 84 | 54 | 24 | 3 | 3 | 0 | 28.6% |
| none | R4 | gemini-flash-lite | 84 | 55 | 25 | 4 | 0 | 0 | 29.8% |
| none | R4 | groq-gpt-oss-20b | 70 | 53 | 16 | 0 | 1 | 0 | 22.9% |

## h1

| condition | n | outdated rate | 95% CI (bootstrap over facts) | CI lower > 2% |
|---|---|---|---|---|
| R2 | 230 | 0.0% | [0.0%, 0.0%] | no |
| R3 | 252 | 24.2% | [8.7%, 42.5%] | yes |

Per model:

| condition | model | n | outdated rate |
|---|---|---|---|
| R0 | gemini-35-flash-lite | 84 | 47.6% |
| R0 | gemini-flash-lite | 84 | 66.7% |
| R0 | groq-gpt-oss-20b | 69 | 62.3% |
| R1 | gemini-35-flash-lite | 84 | 19.0% |
| R1 | gemini-flash-lite | 84 | 17.9% |
| R1 | groq-gpt-oss-20b | 84 | 16.7% |
| R2 | gemini-35-flash-lite | 84 | 0.0% |
| R2 | gemini-flash-lite | 79 | 0.0% |
| R2 | groq-gpt-oss-20b | 67 | 0.0% |
| R3 | gemini-35-flash-lite | 84 | 25.0% |
| R3 | gemini-flash-lite | 84 | 16.7% |
| R3 | groq-gpt-oss-20b | 84 | 31.0% |
| R4 | gemini-35-flash-lite | 84 | 28.6% |
| R4 | gemini-flash-lite | 84 | 29.8% |
| R4 | groq-gpt-oss-20b | 70 | 22.9% |

## h2

| language | n | outdated rate |
|---|---|---|
| en | 164 | 14.0% |
| hi | 158 | 14.6% |
| gu | 160 | 9.4% |

| contrast | pairs | other worse / en worse | rate diff | 95% CI (facts) | p (one-sided) | p Holm |
|---|---|---|---|---|---|---|
| hi vs en | 158 | 2 / 2 | 0.0% | [-1.9%, 1.9%] | 0.6875 | 1.0000 |
| gu vs en | 160 | 1 / 9 | -5.0% | [-10.4%, -0.6%] | 0.9990 | 1.0000 |

Mixed-effects logistic regression (preregistration §6) is not fitted here; the prespecified fallback (exact McNemar on paired item x model x condition outcomes, Holm) is reported.

## h3_r3

| mitigation | n | baseline | with | fixed / broke | change [95% CI, facts] | p (one-sided) | p Holm | refusals | current | calls | tokens/answer | latency median / p90 s (uncached) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M-a1 | 168 | 20.8% | 13.1% | 13 / 0 | -7.7% [-16.7%, 0.0%] | 0.0001 | 0.0004 | 6.0% (base 5.4%) | 80.4% (base 72.0%) | 1.00 | 1009 (1.0x) | 1.7 / 8.8 |
| M-a2 | 168 | 20.8% | 22.6% | 2 / 5 | 1.8% [-1.2%, 4.8%] | 0.9375 | 0.9375 | 4.2% (base 5.4%) | 72.0% (base 72.0%) | 1.00 | 987 (1.0x) | 1.2 / 6.5 |
| M-b | 84 | 16.7% | 13.1% | 3 / 0 | -3.6% [-7.1%, 0.0%] | 0.1250 | 0.2500 | 3.6% (base 4.8%) | 83.3% (base 78.6%) | 2.07 | 2083 (2.2x) | 0.9 / 1.2 |

## mitigations_r1_descriptive

| mitigation (R1, descriptive) | n | baseline | with | refusals | tokens/answer |
|---|---|---|---|---|---|
| M-a1 | 252 | 17.9% | 18.3% | 3.6% | 971 |
| M-a2 | 168 | 18.5% | 17.3% | 4.2% | 947 |
| M-b | 251 | 17.5% | 10.4% | 9.6% | 2200 |
| M-c | 252 | 17.9% | 0.0% | 13.1% | 888 |

## per_fact

| fact | R1 outdated | R3 outdated | R1 current chunk retrieved (k=4) |
|---|---|---|---|
| cg-112a-exemption-limit | 0/18 | 0/18 | 18/18 |
| cg-holding-business-trust-months | 0/18 | 0/18 | 18/18 |
| cg-holding-gold-unlisted-months | 0/18 | 0/18 | 18/18 |
| cg-ltcg-112a-rate | 0/18 | 1/18 | 18/18 |
| cg-ltcg-other-rate | 0/18 | 0/18 | 15/18 |
| cg-stcg-111a-rate | 0/18 | 0/18 | 18/18 |
| mudra-max-loan | 0/18 | 0/18 | 18/18 |
| pmay-interest-subsidy-tenure | 0/18 | 5/18 | 18/18 |
| pmay-mig-income-ceiling | 2/18 | 9/18 | 18/18 |
| pmuy-refills-per-year | 7/18 | 8/18 | 0/18 |
| pmuy-subsidy-per-cylinder | 0/18 | 5/18 | 18/18 |
| rural-guaranteed-days | 0/18 | 0/18 | 18/18 |
| svanidhi-first-loan | 18/18 | 18/18 | 0/18 |
| svanidhi-second-loan | 18/18 | 15/18 | 0/18 |
