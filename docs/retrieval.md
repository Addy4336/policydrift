# Retrieval (milestone 1c)

## Design

- **Search is local and exact.** Chunk embeddings are cached on disk (`.cache/embeddings/<model>.npz`, gitignored), keyed by model, revision, prefix and text. Search is brute-force cosine similarity over all chunks (276 at the time of the first measurements below; 440 now, see the update at the end). Experiments therefore never need a network, and a rerun re-embeds nothing.
- **Filters** (`policydrift.retrieval.search.Filters`): scheme, document language, explicit versions, `as_of` date (inclusive on both ends; open-ended bounds never exclude), and `current_only`. The `as_of` filter is mitigation (c).
- **Both-versions retrieval** (`Retriever.search_versions`): top-`k` chunks from the current version and the one before it, current first. This is the retrieval step of R3/R4 in the pre-registration.
- **Supabase/pgvector** is for the demo only and comes after review (not built yet).

## Model choice

Chosen on 34 dev probes (`data/probes/retrieval_probes.jsonl`): 15 English, 8 Hindi, 7 Gujarati, and 4 cross-lingual (a Hindi or Gujarati question against English documents). A probe passes when a retrieved chunk has the right scheme, version and document language and contains the probe's fact text. The Hindi and Gujarati wording is mine and awaits native-speaker review. The probes calibrate retrieval only; they are dev data and never touch the frozen test split.

Unfiltered search over all chunks, CPU only (Intel i7-8650U, 8 GB RAM):

| | e5-base | BGE-M3 |
|---|---|---|
| Recall@1 | 0.38 | 0.44 |
| Recall@5 | **0.85** | 0.79 |
| Recall@10 | **0.97** | 0.94 |
| MRR | 0.57 | 0.59 |
| Top-1 right scheme | 0.91 | 0.97 |
| Top-1 wrong version (same scheme and language) | 0.29 | 0.21 |
| Time to embed 276 chunks | 323 s | 610 s |
| Model download | about 1.1 GB | about 2.3 GB |

**Decision: `intfloat/multilingual-e5-base`**, revision `d128750597153bb5987e10b1c3493a34e5a4502a`, with the `query: ` and `passage: ` prefixes. It has higher recall at 5 and 10, half the embedding cost and half the memory. BGE-M3 ranks the right scheme and version first slightly more often, but 34 probes cannot show that gap is real.

## What the probes show for the study

- **In unfiltered search, the top result is often the wrong version of the right scheme** (29% with e5-base). Old and new releases of a scheme share most of their wording, so semantic search alone does not separate them. This is the retrieval-side source of stale answers (cf. FRESCO in `related_work.md`), and it is why version metadata and filtering exist.
- **Cross-lingual search works but is weaker.** Hindi and Gujarati questions against English documents found the gold chunk within the top 10 for 3 of 4 probes with e5-base. With n=4 this is only a smoke test.
- **Do not tune retrieval to the probes.** They are for choosing a model and catching regressions, not for improving scores.

## Update 2026-11-01: store grown to 440 chunks

The store gained 164 chunks (GST, capital gains, KCC, MSP, PMUY v4, Budget 2025 summary). With e5-base re-run on the same 34 probes (no retrieval settings changed):

| | R@1 | R@5 | R@10 | MRR | right scheme @1 | wrong version @1 |
|---|---|---|---|---|---|---|
| all (n=34) | 0.38 | 0.79 | 0.97 | 0.55 | 0.91 | 0.32 |
| en (15) | 0.33 | 0.73 | 1.00 | 0.51 | 1.00 | 0.27 |
| hi (8) | 0.50 | 0.88 | 1.00 | 0.69 | 1.00 | 0.38 |
| gu (7) | 0.43 | 0.86 | 0.86 | 0.56 | 0.86 | 0.43 |
| cross-lingual hi (2) | 0.50 | 1.00 | 1.00 | 0.62 | 1.00 | 0.50 |
| cross-lingual gu (2) | 0.00 | 0.50 | 1.00 | 0.22 | 0.00 | 0.00 |

Reading it for the study: about a third of unfiltered top-1 hits come from the wrong version of the right scheme. That is the situation R1 (standard RAG) is meant to measure, so it is not tuned away. The Supabase store holds the same 440 chunks, and `db check` returns an identical top-5 for 34 of 34 probes. Phase 3 uses `k=4` (R1, R2) and 2 chunks per version (R3, R4, X).
