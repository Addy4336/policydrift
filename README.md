# PolicyDrift

**Do RAG agents answer from the rule you retrieved, or the one they remember?**

Government rules change: scholarship income limits, welfare benefit amounts, eligibility ages, subsidy caps, tax slabs. A retrieval-augmented LLM agent can have the current rule right in its context and still answer with the old one it memorised during training. PolicyDrift measures how often that happens for Indian government schemes in English, Hindi and Gujarati, and tests which mitigations fix it. The same codebase powers a multilingual demo agent. It answers with validated citations, shows which rule version and effective date it used, and flags conflicts.

Paper (in progress): *Stale by Default: Measuring and Mitigating Outdated-Rule Answers in Multilingual Policy RAG Agents*.

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Literature review and novelty check ([docs/related_work.md](docs/related_work.md)), pre-registered hypotheses ([docs/preregistration.md](docs/preregistration.md)) | in progress |
| 1 | Versioned document store built from official sources | – |
| 2 | PolicyDrift-Bench: version-sensitive questions in en/hi/gu, human-verified | – |
| 3 | Experiment harness and scoring | – |
| 4 | Mitigations: date-stamped prompts, conflict-checker agent, version-filtered retrieval | – |
| 5 | Analysis, figures and tables | – |
| 6 | Web demo | – |

## Reproducing the results

Setup and one-command reproduction of every number in the paper will be documented here as Phases 1–5 land.
