# PolicyDrift

**Do RAG agents answer from the rule you retrieved, or the one they remember?**

Government rules change: scholarship income limits, welfare benefit amounts, eligibility ages, subsidy caps, tax slabs. A retrieval-augmented LLM agent can have the current rule right in its context and still answer with the old one it memorised during training. PolicyDrift measures how often that happens for Indian government schemes in English, Hindi and Gujarati, and tests which mitigations fix it. The same codebase powers a multilingual demo agent. It answers with validated citations, shows which rule version and effective date it used, and flags conflicts.

Paper (in progress): *Stale by Default: Measuring and Mitigating Outdated-Rule Answers in Multilingual Policy RAG Agents*.

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Literature review and novelty check ([docs/related_work.md](docs/related_work.md)), pre-registered hypotheses ([docs/preregistration.md](docs/preregistration.md)) | done |
| 1 | Versioned document store built from official sources | in progress: 36 official releases captured and chunked |
| 2 | PolicyDrift-Bench: version-sensitive questions in en/hi/gu, human-verified | – |
| 3 | Experiment harness and scoring | – |
| 4 | Mitigations: date-stamped prompts, conflict-checker agent, version-filtered retrieval | – |
| 5 | Analysis, figures and tables | – |
| 6 | Web demo | – |

## Reproducing the results

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                              # install pinned dependencies
uv run policydrift ingest verify     # check every captured source against its SHA-256
uv run policydrift ingest chunk      # rebuild data/processed/chunks.jsonl
uv run pytest                        # tests, including "the committed chunks are up to date"
```

How the official sources were captured is documented in [data/SOURCES.md](data/SOURCES.md). One-command reproduction of every number in the paper will be added as Phases 2–5 land.
