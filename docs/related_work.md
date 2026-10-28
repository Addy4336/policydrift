# Related work and novelty check (Phase 0)

- **Search date:** 2026-10-28
- **Status:** for review
- **Bibliography:** [references.bib](references.bib). 31 entries; 30 verified against arXiv/OpenAlex, 1 flagged as unpublished.

## TL;DR

1. **Our exact angle is not published.** I found no paper or preprint that combines four things: (1) real successive versions of government rules, (2) current-only and both-versions retrieval conditions, (3) Hindi or Gujarati, and (4) a mitigation comparison that includes cost and latency.
2. **The area around it filled up in 2026.** Since May 2026 there have been four legal-temporal RAG preprints: German statutes, French tax law, and two on Chinese law. There is also *Stale-Document Poisoning*, which uses real knowledge reversals, including in law and platform policy. On their own, "LLMs give outdated legal answers" and "version-filtered retrieval fixes it" are no longer new claims.
3. **The open gap is language.** No study of temporal or real-change knowledge conflict covers Hindi or Gujarati. None of the multilingual knowledge-conflict papers is temporal. The closest, CLEAR, uses deliberately false evidence in ten languages, and its only Indic language is Bengali.
4. **A warning for H1.** When only the current version is retrieved, prior work finds that strong models mostly follow it in English: up-to-date evidence was followed in 97–100% of trials in *Stale-Document Poisoning*. The outdated-answer effect is more likely to show up in four places: when both versions are in context, in low-resource languages, under cross-lingual retrieval, and in small open models.
5. **Recommended framing:**
   - Lead with H2 (language) and the both-versions condition.
   - Condition outdated answers on what each model knows closed-book.
   - Present the mitigations as a cost/latency comparison across three families: prompt, agent and retrieval.

   Details are in §7. None of this changes H1–H3.

## 1. Search protocol

- **Window:** 2021 to October 2026, with emphasis on 2025–2026. Preprints from June–October 2026 got a dedicated pass because they fall after the assistant's training data.
- **Sources:**
  - web search (extended mode)
  - arXiv abstract pages, the ACL Anthology and NeurIPS proceedings
  - OpenAlex and arXiv through the `reference-lookup` tool, used for metadata and BibTeX verification
- **Query families:**
  1. context vs parametric-memory conflict in RAG
  2. temporal, outdated or evolving knowledge, and versioned retrieval
  3. multilingual and cross-lingual knowledge conflict and faithfulness
  4. Indic benchmarks and Indian government schemes
  5. legal, regulatory and tax temporal QA and RAG
  6. mitigations: date prompts, verify-and-revise, time filtering
- **Overlap hunt:** each family was searched again combined with "temporal / outdated", "Hindi / Indic / multilingual" and "policy / welfare / tax / statute".
- **Inclusion:** a paper must address at least one family and be either peer-reviewed or a preprint whose abstract page states its method and results. I opened every included paper's canonical page and confirmed title, authors, year and venue. Venues are given only where that page states them.
- **Counts:** about 75 unique records screened by title and snippet, 31 canonical pages opened, 15 core and 16 secondary papers included.
- **Screened but not cited:** I did not open these, or could not verify them in time. They are candidates for follow-up reading.
  - AionRAG (Research Square)
  - WikiContradict
  - MEMERAG
  - Knowledgeable-R1 (ICLR 2026)
  - CK-PLUG (ICLR 2026)
  - UnSeenTimeQA
  - EverGreenQA
  - LLMLagBench
  - Park & Lee 2025 on language preference in multilingual RAG (the metadata check timed out)
  - arXiv:2605.13045 on medical temporal awareness
  - arXiv:2412.08090 on multilingual time-sensitive QA
- **Limitations:**
  - Most papers were read at abstract level, so the quoted numbers come from abstract pages, not full results tables.
  - The search engine is US-centric.
  - Indian-venue and Hindi-language publications may be under-covered.
  - Preprints from the last few weeks may be missing.

## 2. Core papers

Overlap is graded against our research question: High, Medium or Low.

| # | Paper | Venue | What they did | Key finding | Overlap |
|---|---|---|---|---|---|
| 1 | Ahmed, Galke Poech & Röttger, [*Stale-Document Poisoning*](https://arxiv.org/abs/2609.31342) (2026) | arXiv preprint | 317 verified knowledge reversals in medicine, law, software and platform policy, grounded in dated official sources; 12 models. Conditions: outdated evidence alone; outdated evidence plus an instruction to follow it; up-to-date evidence; evaluation date varied; explicit statement of when the old evidence stops applying. | Outdated retrieval flipped 30% (Llama) and 37% (Qwen) of otherwise-correct answers. Up-to-date evidence was followed 97–100% of the time. Stating when the old rule stops applying fixed larger models almost completely. A recency-aware re-ranker cut poisoning by 4.6–10.0 points, but only when the dates were accurate. | **High.** Same real-reversal design, but the opposite direction: a stale document, where we study a stale prior. English only. |
| 2 | Prior, Schultz & Grabmair, [*Asking For An Old Friend*](https://arxiv.org/abs/2605.23497) (2026) | ICAIL 2026 | 312 expert-validated German statutory QA pairs, including post-cutoff-amendment questions; 5 LLMs. Conditions: no retrieval, web search, and two RAG variants with fact-date extraction and version filtering. LLM judge validated against experts. | Without retrieval, answers degrade severely on post-cutoff amendments. Both RAG variants improve substantially. Web search is unstable and shows recency bias. | **High.** Closest to H1 plus mitigation (c). German only, with no multilingual or cost analysis. |
| 3 | Cymbler, Guez & Fabre, [*Temporal Misgrounding in Legal RAG*](https://arxiv.org/abs/2608.09393) (2026) | ICML 2026 AI4Law workshop | 32,436 versions of French tax-code articles (1938–2031); 209 expert-reviewed questions; 11 models. Conditions: closed-book, current-only RAG, multi-version index. Scoring is deterministic and nugget-based. | Closed-book accuracy 3.0%; current-only RAG 2.7% (it retrieves the date-applicable version 0% of the time); multi-version retriever 98.3%. | **High.** A versioned tax corpus with our retrieval conditions, but its questions ask about *historical* dates, so an error means an answer that is too new. One language. Argues against LLM judges because a judge inherits the temporal bias being measured. |
| 4 | Huang et al., [*When Do LLMs Apply the Wrong Law?*](https://arxiv.org/abs/2608.14610) (2026) | arXiv preprint | TALD-Bench: 51,956 Chinese civil judgments spanning the enactment of the Civil Code; 9 LLMs. | Over 70% accuracy on new-law cases but under 25% on old-law cases. Models know the temporal-effect rules but misapply them. Temporal-law hints help. | **Medium.** Shows recency bias *toward* newer law, the mirror image of our failure mode. Relevant to the both-versions condition. |
| 5 | Ouyang et al., [*HoH*](https://aclanthology.org/2025.acl-long.301/) (2025) | ACL 2025 | Large QA benchmark built from token-level diffs of real evolving facts, with outdated and current information side by side in the retrieval pool. | Outdated information lowers RAG accuracy and can cause harmful outputs even when current information is available. | **Medium–High.** A general-domain version of our both-versions condition. The abstract page doesn't state the language; no policy domain. |
| 6 | Marjanović et al., [*DynamicQA*](https://arxiv.org/abs/2407.17023) (2024) | Findings of EMNLP 2024 | Static, temporal and disputable facts; measures intra-memory conflict and whether the model updates when given context. | Dynamic facts carry more intra-memory conflict and are harder to update with context. | **High for H1's rationale.** Predicts that changed rules are exactly what RAG struggles to override. |
| 7 | Hossain et al., [*Right Knowledge, Wrong Answer*](https://arxiv.org/abs/2606.20959) (2026) | arXiv preprint | 8,746 Wikidata position-holder transitions; 4 open-weight models; closed-book. Interventions: a date-prefix prompt, activation patching and steering. | Models store both the old and the new fact but default to the old one. A date-prefix prompt recovers the newer fact in 61–81% of cases. | **Medium.** Closed-book evidence for mitigation (a); no retrieval, no policy domain. |
| 8 | Wu, Wu & Zou, [*ClashEval*](https://arxiv.org/abs/2404.10198) (2024) | NeurIPS 2024 Datasets & Benchmarks | Perturbed retrieved evidence in six domains, including drug dosages and Olympic records. | Models override a correct prior with wrong context more than 60% of the time. Less confident priors adopt the context more often, and subtle deviations are adopted more than blatant ones. | **Medium.** Synthetic perturbations. Method to borrow: stratify results by prior confidence. |
| 9 | Xie et al., [*Adaptive Chameleon or Stubborn Sloth*](https://arxiv.org/abs/2305.13300) (2024) | ICLR 2024 (spotlight) | Systematic study of LLM behaviour when external evidence conflicts with parametric memory. | Models are highly receptive to coherent conflicting evidence, but show strong confirmation bias when evidence consistent with their memory is present too. | **Medium.** Predicts a higher outdated rate in our both-versions condition. |
| 10 | Su et al., [*ConflictBank*](https://arxiv.org/abs/2408.12076) (2024) | NeurIPS 2024 | 7.45M claim–evidence pairs and 553K QA pairs. Conflicts come from misinformation, temporal discrepancy and semantic divergence; 12 LLMs. | Large-scale analysis by conflict cause and model scale. | **Medium.** Has a temporal-conflict category, but the claims are constructed, not real rule versions. |
| 11 | Longpre et al., [*Entity-Based Knowledge Conflicts in QA*](https://aclanthology.org/2021.emnlp-main.565/) (2021) | EMNLP 2021 | Knowledge conflicts in QA, where a passage given at inference time contradicts what the model learned in training. | Over-reliance on memorised information causes hallucination. A mitigation that reduces reliance on parametric knowledge cuts hallucination, improves out-of-distribution generalisation by 4–7%, and helps on time-dependent queries. | **Low–Medium.** Foundational definition of context-vs-memory conflict. |
| 12 | Sharma, Murray & Xiao, [*Faux Polyglot*](https://arxiv.org/abs/2407.05502) (2025) | NAACL 2025 | Cross-language RAG with sources that conflict across languages; covers both retrieval and generation. | Models systematically prefer information in the query's language. When none exists, they prefer documents in high-resource languages. | **Medium for H2.** Predicts behaviour in a cross-lingual condition (Hindi/Gujarati query, English source). |
| 13 | Zhao et al., [*When Abundance Conceals Weakness*](https://arxiv.org/abs/2601.07041) (CLEAR, 2026) | arXiv preprint | Cross- and intra-lingual knowledge conflict in 10 languages (af, bn, de, en, fr, is, ja, sw, tr, zh). Built from ConflictQA with deliberately false counter-evidence. | Resource scale decides conflicts on reasoning tasks; linguistic affinity matters more on entity tasks. | **Medium for H2.** The closest multilingual-conflict study, but it has no Hindi or Gujarati and no temporal or real-world changes. |
| 14 | Vladika, Dhaini & Matthes, [*Facts Fade Fast*](https://arxiv.org/abs/2509.04304) (2025) | Findings of EMNLP 2025 | MedRevQA (16,501 questions) and MedChangeQA (512 questions where medical consensus changed); 8 LLMs. | All models rely on outdated knowledge consistently. | **Medium.** Real-change staleness in memory, in another regulated domain; closed-book. |
| 15 | Verma et al., [*MILU*](https://aclanthology.org/2025.naacl-long.507/) (2025) | NAACL 2025 | 11 Indic languages, including Gujarati; 8 domains, including Law & Governance; more than 42 LLMs. | Models are weaker in low-resource languages and in culturally specific domains such as Law & Governance. | **Low–Medium.** Background for H2. Closed-book multiple choice, no retrieval. |

## 3. Also relevant (secondary)

- **Xu et al.**, [*Knowledge Conflicts for LLMs: A Survey*](https://aclanthology.org/2024.emnlp-main.486/), EMNLP 2024. Taxonomy of context–memory, inter-context and intra-memory conflicts. Our current-only condition is a context–memory conflict; our both-versions condition adds an inter-context one.
- **Fan et al.**, [*Can LLMs Time Travel?*](https://arxiv.org/abs/2605.25920) (LegalSearch-R1), EMNLP NLLP 2026. Legal LLMs show "temporal bias anchored to their training cutoff", and search agents rarely add temporal constraints to their queries. Fix: an RL-trained agent over temporally indexed statutes.
- **Li et al.**, [*LexKairos*](https://arxiv.org/abs/2608.09106), 2026 preprint. Nine Chinese legal-temporal tasks. Even the best model struggles to recall statutory metadata such as effective dates.
- **Cao et al.**, [*Re³*](https://aclanthology.org/2026.acl-long.1180/), ACL 2026. A time-aware encoder plus a conflict-aware recency filter, with average gains of +9.7% (up to +25.2%). A retrieval-side mitigation baseline.
- **An et al.**, [*FRESCO*](https://aclanthology.org/2026.findings-emnlp.54/), Findings of EMNLP 2026. Re-rankers favour older, semantically rich documents even when they are obsolete. This makes staleness a retrieval problem too, not only a generation problem.
- **Huwiler et al.**, [*VersionRAG*](https://arxiv.org/abs/2510.08109), 2025 preprint. Version-aware graph retrieval: 90% vs 58% for naive RAG on version-sensitive technical-document questions.
- **Özer & Yıldız**, [*QA under Temporal Conflict*](https://arxiv.org/abs/2506.07270), 2025 preprint. Models are misled when several versions of a fact appear in context. Fix: a temporally filtered external memory.
- **Tang et al.**, [*EvoWiki*](https://arxiv.org/abs/2412.13582), 2024 preprint. On evolved knowledge, models often give outdated answers. RAG and continual learning work better together than either alone.
- **Vu et al.**, [*FreshLLMs / FreshQA*](https://arxiv.org/abs/2310.03214), 2023 preprint. Benchmark of fast-changing facts. The number and order of retrieved evidence passages affect correctness, a confound to control in our prompts.
- **Augenstein**, [ECIR 2025 keynote](https://arxiv.org/abs/2603.09654), ACM SIGIR Forum 2026. Reviews evidence that LMs often ignore context that conflicts with pre-training, and covers intra-memory conflict.
- **Kang et al.**, [*X-MADAM-RAG*](https://arxiv.org/abs/2606.12903), 2026 preprint. Chinese–English cross-lingual evidence conflict. Its gains collapse on naturalised (non-templated) evidence, a caution against templated benchmark items.
- **Shetty et al.**, [*Tulu Legal Comprehension*](https://arxiv.org/abs/2608.28645), 2026 preprint. Legal comprehension in a low-resource Indic language. RAG gains were mixed, with fact-substitution and confabulation failures, and comprehension depends on script.
- **Bilal & G**, [*AgriGov*](https://arxiv.org/abs/2606.08272), 2026 preprint. A multilingual dataset of 50 farmer schemes in English, Hindi and Marathi. No versioning, effective dates or evaluation, which shows the scheme-data gap we fill.
- **Zhou et al.**, [*Context-faithful Prompting*](https://arxiv.org/abs/2303.11315), Findings of EMNLP 2023. Opinion-based prompts and counterfactual demonstrations. A cheap prompt-level baseline.
- **Dhuliawala et al.**, [*Chain-of-Verification*](https://arxiv.org/abs/2309.11495), 2023 preprint. The draft → verification questions → independent answers → revise pattern. The template for our conflict-checker agent.
- **Kag et al.**, [*Do language models know India's new criminal code?*](https://github.com/hitesh712/bns-statute-grounding), unpublished manuscript (GitHub only, no arXiv or DOI; **weak evidence**). On the IPC→BNS change of 1 July 2024:
  - Closed-book, small models cite repealed IPC sections in up to 67% of queries.
  - With retrieved statute text, they cite correctly 93–98% of the time.

  This is the only evaluation of an Indian rule change that I found.

## 4. Thematic synthesis

**Context vs memory.** The field's view has moved from "models over-rely on memory" (Longpre 2021) to "models readily adopt coherent context" (Xie 2024; ClashEval reports correct priors being overridden by wrong context more than 60% of the time). Two moderators matter for us:

- **Prior confidence:** less confident priors give way to context more easily (ClashEval).
- **Fact dynamics:** time-varying facts carry more intra-memory conflict and are harder to update from context (DynamicQA; Augenstein 2026).

Rule changes are dynamic facts by definition. That is the core argument for why H1 could hold despite the general receptiveness to context.

**Temporal and outdated knowledge.** Closed-book, models encode outdated facts (Facts Fade Fast, EvoWiki, FreshQA). Hossain et al. show models often store *both* versions and default to the old one. With retrieval, outdated material in context misleads models (HoH, Özer & Yıldız), and re-rankers prefer obsolete documents (FRESCO). Retrieval-side fixes (Re³, VersionRAG) work well, but all of this is general-domain and English or unstated.

**Multilingual.** Knowledge-conflict behaviour depends on language. Models prefer evidence in the query's language (Faux Polyglot), resource level and linguistic affinity change which source wins (CLEAR), and cross-lingual evidence conflicts are hard to resolve on natural text (X-MADAM-RAG). None of this work is temporal, and none covers Hindi or Gujarati.

The direction of H2 is genuinely open:

- **Against H2:** if a model's parametric knowledge is weaker in Hindi or Gujarati (MILU), its prior is less confident there, and ClashEval predicts it would adopt the retrieved current rule *more* often. That means a lower outdated rate.
- **For H2:** if the model comprehends the Hindi or Gujarati context less well (MILU, Tulu), it may fall back on a prior learned mostly from English sources. That means a higher outdated rate.

This makes H2 a real empirical question, which strengthens the paper.

**Indic and government schemes.** No peer-reviewed benchmark for Indian scheme or rule QA turned up. What exists:

- multilingual benchmarks with a Law & Governance slice (MILU)
- an unversioned scheme dataset (AgriGov)
- an unpublished IPC→BNS citation study
- many GitHub and Hugging Face scheme chatbots that report metrics on their own small test sets

**Legal and regulatory temporal RAG.** The 2026 cluster splits into two failure directions:

- **Stale:** applying a superseded rule after an amendment. Old Friend's post-cutoff questions and LegalSearch-R1's cutoff-anchored bias fall here.
- **Too new:** applying the in-force rule to historical facts. French tax and TALD fall here.

Our study is in the stale direction, for questions about the *current* rule. The both-versions condition can measure both directions at once, which links our results to this literature.

**Mitigations.**

- **(a) Date prompts.** A date prefix recovers the newer fact closed-book in 61–81% of cases (Hossain). A date alone helps only modestly, but an explicit validity statement ("the old rule stopped applying on D") works well (Stale-Document Poisoning). Hints help in the too-new direction (TALD).
- **(b) Verify-and-revise.** CoVe is the general pattern. I found no paper that evaluates a conflict-checker agent for temporal rule conflicts specifically.
- **(c) Version or time filtering.** Consistently strong across Old Friend, French tax, LegalSearch-R1, Re³ and VersionRAG.

**No paper compares these three families head to head, and none reports token cost or latency.**

## 5. Novelty matrix

Legend: ✓ yes · ◐ partial · ✗ no · ? not stated on the abstract page.

The five design features:
- **(a)** real successive official versions
- **(b)** retrieval conditions: none / current-only / both versions
- **(c)** government policy or legal domain
- **(d)** Hindi or Gujarati
- **(e)** mitigation comparison with cost and latency

| Paper | (a) | (b) | (c) | (d) | (e) |
|---|---|---|---|---|---|
| Stale-Document Poisoning | ✓ dated official sources | ◐ outdated-only, up-to-date-only; both together ? | ◐ law and platform policy among four domains | ✗ English | ◐ one re-ranker plus date and validity statements; no cost |
| Asking For An Old Friend | ✓ German statutes | ◐ none, web, version-filtered RAG | ✓ | ✗ German | ◐ two RAG variants plus web; no cost |
| Temporal Misgrounding (French tax) | ✓ | ✓ none, current-only, multi-version | ✓ tax | ✗ French | ◐ retriever design only |
| When Do LLMs Apply the Wrong Law? | ✓ | ? | ✓ | ✗ Chinese | ◐ hints |
| Can LLMs Time Travel? | ✓ amendment periods | ◐ | ✓ | ✗ | ◐ RL-trained agent |
| HoH | ✓ real evolving facts | ◐ outdated and current side by side | ✗ | ? | ✗ |
| DynamicQA | ◐ Wikidata facts | ◐ context given | ✗ | ✗ | ✗ |
| Right Knowledge, Wrong Answer | ◐ Wikidata transitions | ✗ closed-book only | ✗ | ? | ◐ date prefix, steering |
| CLEAR | ✗ counterfactual | ◐ | ✗ | ✗ (Bengali is the only Indic language) | ✗ |
| Faux Polyglot | ✗ | ◐ cross-lingual | ✗ | ? | ✗ |
| IPC→BNS manuscript (unpublished) | ✓ | ◐ none, statute, statute + knowledge graph | ✓ India | ? | ◐ knowledge graph |
| **PolicyDrift (planned)** | ✓ | ✓ plus cross-lingual | ✓ Indian schemes | ✓ | ✓ prompt vs agent vs retrieval, with tokens and latency |

## 6. Verdict

**Is our exact angle already published? No.** No single paper covers more than three of the five features, and none covers (d), Hindi or Gujarati, at all. The closest work splits into two groups:

- **Same failure mode, different setting:** English or European languages (Stale-Document Poisoning, Old Friend, French tax).
- **Same languages, different problem:** Indic benchmarks with no temporal conflict (MILU, AgriGov).

**How novel is it?** Moderately: the combination is new, but the space around it is not empty. Reviewers will cite Stale-Document Poisoning, Asking For An Old Friend and Temporal Misgrounding as the closest work, so the paper must engage with them directly. Two of our components are not novel on their own:

- **H1 in English with current-only retrieval** is partly answered already: up-to-date evidence is mostly followed, and version filtering mostly works.
- **Mitigation (c)** alone is well established.

**What is still new:**
1. The language effect on real-change staleness (H2), in Hindi and Gujarati.
2. Indian government schemes as a domain, with a versioned, multilingual, human-verified benchmark.
3. The stale-prior direction for current-rule questions when both versions are retrieved.
4. A head-to-head comparison of prompt, agent and retrieval mitigations that includes cost and latency.

## 7. Differentiation: recommended changes

None of these edits H1–H3. Items 1–4 are conditions and analyses to add to the operationalisation in `preregistration.md` before Phase 3. Anything beyond H1–H3 is labelled exploratory there.

1. **Make language the headline contribution (H2).** Add an exploratory cross-lingual condition: a Hindi or Gujarati query against an English-only official source, versus a same-language source where one exists. It is realistic, because many central-scheme documents exist only in English or Hindi. Faux Polyglot and CLEAR predict it matters, and nobody has tested it on temporal conflicts.
2. **Make "both versions retrieved" a primary condition, with effective dates shown vs hidden.** This is where prior work predicts the largest effect (Xie's confirmation bias, HoH, Özer & Yıldız). It also tests whether models actually use date metadata, and lets us count both failure directions (stale and too new).
3. **Condition on what each model knows.** Run a closed-book probe per item: does the model state the old rule, the new rule, or neither? Then report the outdated rate among items where the model memorised the old rule. Without this, "falls back to memorised rules" can't be separated from "misread the context". This follows DynamicQA and ClashEval.
4. **Stratify by when the rule changed relative to each model's knowledge cutoff.** API cutoffs are uncertain, so record the stated cutoff and lean on the closed-book probe.
5. **Focus on numeric rule facts and score them deterministically.** These are income limits, benefit amounts, ages and deadlines. Use an LLM judge only for leftover cases, framed as a *matching* task: "which of these two values does the answer state?". A matching judge needs no rule knowledge, which sidesteps the temporal-bias objection raised in the French-tax paper.
6. **Present the mitigations as a cost/latency trade-off.** Include robustness when dates are missing or wrong: *Stale-Document Poisoning* found its re-ranker only helped with accurate dates. For (a), compare a plain date stamp with an explicit validity statement, since Stale-Document Poisoning found only the latter strong.

On the title: *"Stale by Default"* overclaims if H1 turns out small in English with current-only retrieval. Keep it as the working title and decide after the results. Titles are not part of the pre-registration.

## 8. Implications for later phases

**Phase 1 (data)**
- Prefer rule changes dated close to or after the free-tier models' training cutoffs (2024–2026).
- Prefer numeric facts.
- For every version, record which languages it officially exists in. That decides where the cross-lingual condition arises naturally: central schemes are often in English and Hindi only, while Gujarat state schemes may exist in Gujarati.

**Phase 2 (benchmark)**
- For each item, store the old value, the new value, units, effective dates and a closed-book probe question.
- Vary the time reference across three forms: an explicit date ("as of 2026"), "currently", and none.
- Never put either value in the question.
- Write natural, non-templated phrasing; X-MADAM-RAG's results collapsed once templates were removed.

**Phase 3 (harness)**
- Conditions:
  - none
  - standard RAG
  - current-only
  - both versions, with dates shown and with dates hidden
  - cross-lingual (exploratory)
- Control the number and order of retrieved passages (FreshQA).
- Log prior confidence (logprobs) where the API exposes it (ClashEval).
- Include at least one small open model; small models were more affected in Stale-Document Poisoning and the IPC→BNS manuscript.
- Analyse paired items with McNemar or a mixed-effects logistic model, as in the pre-registration template.

**Phase 4 (mitigations)**
- Expect version filtering to nearly eliminate the effect under current-only retrieval (Old Friend, French tax). The informative comparisons are cost, latency, and robustness to missing or wrong dates.
- Build the conflict-checker in the CoVe pattern and report its extra calls and tokens.
- Context-faithful prompting (Zhou et al.) is an optional cheap extra baseline.
