# PolicyDrift: brief for the portfolio site and resume

Everything here is checked against the repository as of 2026-11-06. Dev-split numbers are labelled as such. The confirmatory test-split results are still being produced; update the "Results" line when `paper/test/results.md` exists.

## Links

| What | URL |
|---|---|
| Live demo | https://policydrift-lime.vercel.app |
| API health | https://policydrift-api.vercel.app/api/health |
| Source code | not public yet. Push the repo to GitHub, then add the link here |
| Screenshot | `docs/img/demo-answer.jpg` (1280×900 crop of the answer view) |

## One line

A multilingual (English, Hindi, Gujarati) RAG assistant for Indian government rules that answers from the rule version in force on a chosen date, validates every citation and figure, and flags when a rule has changed. It is backed by a pre-registered study of when LLMs answer from outdated rules.

## Short description (portfolio card, about 50 words)

PolicyDrift asks whether RAG agents answer from the rule they retrieved or the one they memorised. I built a human-verified benchmark of 42 real rule changes across 14 Indian schemes in three languages, ran pre-registered experiments on four mitigations, and shipped the winners as a live assistant with validated citations and rule-change flags.

## Longer description (project page)

Government rules change: loan limits, subsidy amounts, tax rates. A retrieval-augmented model can have the current rule in its context and still answer with an older one. PolicyDrift measures this for Indian government schemes in English, Hindi and Gujarati.

- **Data:** 46 official releases (PIB, ministries), each recorded with URL and SHA-256, chunked into 440 passages tagged with the effective dates of their rule version.
- **Benchmark:** 42 rule changes across 14 schemes; 85 human-verified items × 3 languages = 255 questions; split by scheme; test split frozen and checksummed behind a loader guard.
- **Experiments:** five retrieval conditions and four mitigations (date-stamped prompt, validity statement, conflict-checker agent, version-filtered retrieval); hypotheses and analysis pre-registered and frozen (git tag) before the test run; deterministic number matcher plus an LLM judge (κ = 0.83 against 60 stratified human labels).
- **Findings on the dev split (not confirmatory):**
  - Models know the old rules: 48–67% of closed-book answers give the outdated value.
  - With only the current version retrieved, stale answers drop to 0%. With both versions retrieved, they return (24%).
  - In plain RAG, 38 of 40 stale answers came from retrieval missing the current passage, not from the model overriding it.
  - A one-line date-stamped prompt removed the remaining stale answers where the current rule was in context (6.7% → 0%), matching a conflict-checker agent at half the cost.
  - Hindi and Gujarati questions were not worse than English.
- **Product:** a FastAPI + Next.js app that applies the two mitigations that worked, translates and routes Hindi and Gujarati questions, lets you ask "as of" a past date, validates that every cited number appears in an official source, and declines out-of-scope questions instead of inventing answers (13/13 on a live spot-check).

## Tech tags

Python 3.12 · FastAPI · Next.js 16 · TypeScript · Tailwind CSS · RAG · multilingual embeddings (e5) · BM25 · Gemini & Groq APIs (gpt-oss-120b) · LLM-as-judge · pre-registration · statistics (McNemar, Holm, cluster bootstrap) · pytest (131 tests) · mypy strict · Vercel

## Resume bullets (pick 3–4)

- Built PolicyDrift, a multilingual (en/hi/gu) RAG assistant for Indian government rules with version-aware retrieval, date-scoped answers, citation and figure validation, and rule-change flags; deployed on Vercel (FastAPI + Next.js).
- Designed a human-verified benchmark of 42 real policy changes across 14 schemes (255 questions in 3 languages) from 46 hash-verified official sources, with a frozen, checksummed test split.
- Ran pre-registered experiments on 4 mitigations across 5 retrieval conditions. A date-stamped prompt eliminated stale answers when the current rule was retrieved, matching a conflict-checker agent at half the LLM calls. Found that most staleness in standard RAG came from retrieval misses.
- Engineered a reproducible evaluation stack: cached, rate-limited LLM client; deterministic number matcher plus LLM judge (κ = 0.83 vs human labels); fact-clustered bootstrap and McNemar tests; 131 tests, mypy strict.

## Honest limits to keep in mind when presenting it

- Dev-split results come from 28 items. The pre-registered test results are pending.
- Two of the three models share one provider (Gemini); gpt-oss-20b was dropped from the final run because of free-tier throughput.
- One person verified the benchmark and labelled the judge sample.
- The hosted demo uses BM25 retrieval (free hosting cannot load the embedding model); the research uses e5-base.
