# Live demo spot-check (2026-11-06)

`scripts/demo_eval.py` sends 13 questions to the deployed API (https://policydrift-api.vercel.app) and logs the full responses to [demo_eval.json](demo_eval.json). Expected values come from `data/facts.yaml`, where each value is quoted from an official release. Only dev-split facts are used; the frozen test split is not touched.

This is a smoke test of the product, not a research result. Thirteen questions cannot measure accuracy.

## Questions

| ID | Type | Lang | As of | Asked | Expected |
|---|---|---|---|---|---|
| A1 | in scope | en | today | days of guaranteed rural work | 125 (was 100) |
| A2 | in scope | hi | today | STCG rate, section 111A | 20% (was 15%) |
| A3 | in scope | gu | today | PM Ujjwala subsidy per cylinder | ₹300 (was ₹200) |
| A4 | past date | en | 2023-06-01 | PM Mudra maximum loan | ₹10 lakh (v1) |
| A5 | past date | hi | 2023-01-01 | PM SVANidhi second loan | ₹20,000 (v1) |
| A6 | in scope | gu | today | PM SVANidhi second loan | ₹25,000 (v2) |
| A7 | in scope | en | today | LTCG rate on gold and unlisted assets | 12.5% (was 20%) |
| A8 | in scope | en | today | holding period for gold | 24 months (was 36) |
| F1 | false premise | en | today | "why was the Mudra limit cut to ₹5 lakh in 2025?" | correct the premise: raised to ₹20 lakh |
| O1–O4 | out of scope | en, hi, gu, en | today | Gemini-generated questions on the DPDP Order 2026, Census Rules 2026, Merchant Shipping Rules 2026, CBDT G.S.R. 198(E) | decline without inventing details |

The out-of-scope questions were drafted with Gemini. None of these instruments is in the corpus (14 schemes; see the Schemes page). Whether they exist at all was not checked. They test whether the system refuses instead of inventing text, gazette numbers or dates.

## Result (final run)

All 13 behaved as expected.

- **A1–A8:** correct value, in the question's language, cited, with the right rule version. A past as-of date returned the old version and flagged the newer one.
- **F1:** said the premise is not supported and gave ₹20 lakh with citations.
- **O1–O4:** declined in the question's language. No scheme, rule version, sources or change banner was shown, and the answer said what the assistant covers.

Figure checks are deliberately conservative. A8's "(2 years)" and F1's quoted "₹5 lakh" were flagged as not found in the sources, and O4's "198" from the gazette number was too. A false alarm here is preferred to a missed one.

## What the spot-check changed

Three demo-only changes came out of earlier runs of the same script. None affects the research pipeline.

1. A declined answer still showed the scheme the router had fallen back to (KCC, MSP and so on) and its rule-change banner. Declines now return no rule version, sources or flags.
2. A Gujarati decline used wording the keyword detector missed. The prompt now asks the model to mark declines with a fixed `NO_ANSWER:` token, and the keyword list remains as a fallback.
3. The false-premise question was declined instead of corrected. The prompt now separates "the question assumes something the passages contradict" (correct it, with citations) from "the passages say nothing relevant" (decline).

Response times were 1.5–19 s, mostly Groq free-tier latency. Repeated questions come from the cache.
