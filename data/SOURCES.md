# Data sources

- **Status:** milestone 1b (2026-10-28). The 65 PIB releases listed below (46 in the first nine schemes, 14 in the three added on 2026-10-31) are captured in `data/raw/`; every rule version of every scheme now has at least one document from its own period. Each file's URL, language, version, retrieval time and SHA-256 are in [`raw/manifest.jsonl`](raw/manifest.jsonl). Check them with `uv run policydrift ingest verify`.
- **Not yet captured:** the VB-G RAM G backgrounder and the primary instruments (see "Remaining gaps" at the end).
- **Rule:** official government publications only (CLAUDE.md, hard rule 3).

## How the captures were made (normalisation `pib-text-v1`)

PIB's HTML pages reject scripted clients (HTTP 401/403), so each release was opened in the desktop app's built-in browser. The capture is the `innerText` of the release body, up to and including its "(Release ID: …)" line, so the changing visitor counter and the language links are left out. The text is then normalised:

1. Unicode NFC.
2. No-break spaces become spaces.
3. Line endings become LF.
4. Runs of spaces collapse to one.
5. Each line is trimmed.
6. Runs of three or more newlines become one blank line.

A SHA-256 of the result was computed in the browser. The file on disk was checked against that hash, so every file is an exact copy of what the page showed.

Characters are otherwise kept as published:
- Hindi zero-width joiners stay.
- Latin ligatures such as "ﬁ" stay.
- Private-use Wingdings bullets stay.

Ligatures and private-use bullets are removed only in the chunk text (`policydrift.ingest.pib.clean_text`), never in the raw files.

**Legacy pages.** Two releases (from 2004 and 2015) exist only in PIB's older layout at `https://www.pib.gov.in/newsite/erelcontent.aspx?relid=<id>`. Their capture is the `innerText` of `#form1` up to the "(Release ID :…)" line, normalised the same way. In the manifest they have `release_id_kind: "relid"`, and their files are named `pib-r<relid>-<lang>.txt`. The header is laid out differently ("18-September, 2004 16:34 IST" instead of "Posted On: …"), and `parse_pib` handles both layouts.

## How the sources are organised

- **Main source: Press Information Bureau (PIB) releases.** PIB is the Government of India's official press agency. Each English release links to official Hindi and Gujarati releases, and PIB Ahmedabad issues the Gujarati ones. That gives parallel official text in all three of our languages.
- **Canonical URL form:** `https://www.pib.gov.in/PressReleasePage.aspx?PRID=<id>`. Each language version has its own PRID.
- **Primary legal instruments** (gazette notifications, Acts, scheme guidelines) are what PIB releases announce. They are usually English or bilingual English/Hindi. Where I already know the reference, it is listed below; the rest get located in milestone 1b. The benchmark's gold answers will cite the release, and the instrument where one exists.
- **Spot check:** I opened one Gujarati release (Ujjwala, PRID 2154137). It states the same figures as the English one, so the translations look faithful. Every Gujarati and Hindi release still gets checked against its English version in 1b.

## Decision table

**Language columns:** ✓ = official text found for that language · – = not found yet.

**Fact types:** amount, limit, age, days, count. All are numeric, so the deterministic scorer can check them.

| # | Scheme | Changed fact(s) | Versions (effective from) | en | hi | gu | Decision |
|---|---|---|---|---|---|---|---|
| 1 | Income tax, new regime (individuals) | slab boundaries, rebate threshold, standard deduction | FY 2023-24 → FY 2024-25 → FY 2025-26 | ✓ | ✓ | ✓ | **Keep.** Many facts, three versions, all three languages. |
| 2 | PM Ujjwala Yojana targeted LPG subsidy | ₹ per cylinder; refills per year | May 2022 → 5 Oct 2023 → FY 2025-26 (→ 2026?) | ✓ | ✓ | ✓ | **Keep.** Two facts changed at different times. |
| 3 | PM SVANidhi (street-vendor loans) | first- and second-tranche loan amounts | 2022 structure → restructured 27 Aug 2025 | ✓ | ✓ | ✓ | **Keep.** The old-amounts release found so far is English-only. |
| 4 | Rural employment guarantee: MGNREGA → VB-G RAM G | guaranteed days per household per year, plus other parameters | MGNREGA 2005 → VB-G RAM G Act in force 1 Jul 2026 | ✓ | ✓ | ✓ | **Keep.** Changed after every candidate model's cutoff. |
| 5 | PMAY-Urban → PMAY-U 2.0 | MIG income ceiling; assistance per unit | PMAY-U (2015) → PMAY-U 2.0 approved 9 Aug 2024 | ✓ | ✓ | ✓ | **Keep, with a caveat** (see the scheme entry). |
| 6 | AB PM-JAY, senior citizens | age-based eligibility (70+ regardless of income) | earlier criteria → approved 11 Sep 2024, launched 29 Oct 2024 | ✓ | ✓ | – | **Keep.** Gujarati only through the cross-lingual condition. |
| 7 | PM Mudra Yojana | maximum loan; new Tarun Plus category | ₹10 lakh → ₹20 lakh from 24 Oct 2024 | ✓ | ✓ | – | **Keep.** Gujarati only through the cross-lingual condition. |
| 8 | Senior Citizens' Savings Scheme (+ Monthly Income Scheme) | maximum deposit limits | ₹15 lakh → ₹30 lakh from 1 Apr 2023 | ✓ | ✓ | – | **Keep.** Gujarati only through the cross-lingual condition. |
| 9 | National Means-cum-Merit Scholarship (NMMSS) | parental income ceiling | ₹1.5 lakh → ₹3.5 lakh (approved 22 Feb 2022) | ✓ | ✓ | – | **Keep as an older change.** The only scholarship found; its change likely predates every model's cutoff. |

**Coverage**
- **Change dates:** 2022 (1), 2023 (2), 2024 (4), 2025 (3), 2026 (1). This leaves room to compare changes before and after each model's knowledge cutoff.
- **Gujarati:** five schemes have official Gujarati text for the current version. The other four give the cross-lingual condition (X) naturally: a Gujarati question against an English or Hindi source.
- **Benchmark size:** these nine schemes yield about 30–35 distinct changed facts. Phase 2 needs 200–400 question pairs, which is feasible across several phrasings and three languages. Statistical power depends on the number of distinct facts, though, so I recommend adding 2–4 schemes (reserve list below) before Phase 2.

## Source register

Values are as stated on the cited pages. The `effective_to` of each version is the day before the next version's `effective_from`.

### 1. Income tax: new regime slabs (individuals)

| Version | effective_from | Facts | Source (PIB PRIDs: en / hi / gu) |
|---|---|---|---|
| FY2023-24 | 2023-04-01 | Slabs: 0–3L nil; 3–6L 5%; 6–9L 10%; 9–12L 15%; 12–15L 20%; >15L 30%. Rebate up to ₹7 lakh. Standard deduction ₹50,000 extended to the new regime. New regime becomes the default. | Budget 2023-24 release, 1 Feb 2023: 1895286 / 1895311 / 1895343 |
| FY2024-25 | 2024-04-01 | Slabs: 0–3L nil; 3–7L 5%; 7–10L 10%; 10–12L 15%; 12–15L 20%; >15L 30%. Standard deduction ₹75,000; family-pension deduction ₹25,000. | Budget 2024-25 release, 23 Jul 2024: 2035605 / 2035659 / 2035916 |
| FY2025-26 | 2025-04-01 | Slabs: 0–4L nil; 4–8L 5%; 8–12L 10%; 12–16L 15%; 16–20L 20%; 20–24L 25%; >24L 30%. No tax up to ₹12 lakh (₹12.75 lakh for salaried). | Budget 2025-26 release, 1 Feb 2025: 2098406 / 2098407 / 2098461 |

- **Primary instruments:** Finance Act 2023, Finance (No. 2) Act 2024 and Finance Act 2025 (Gazette of India, bilingual). The Budget speeches on indiabudget.gov.in are in English and Hindi.
- **Open questions:**
  - Did Budget 2026-27 leave individual slabs unchanged? The Income-tax Act 2025 replaced the 1961 Act from 1 Apr 2026, and a summary says rates were kept. Confirm against the Finance Act 2026 schedule before treating FY2025-26 as current.
  - The FY2024-25 slab table appears to be an **image** on the English PIB page: the text extraction misses it. Take the table from the Budget speech PDF or the Hindi/Gujarati releases instead.

### 2. PM Ujjwala Yojana: targeted LPG subsidy (14.2 kg cylinder)

| Version | effective_from | Facts | Source (en / hi / gu) |
|---|---|---|---|
| V1 | 2022-05 (start of subsidy) | ₹200 per cylinder, up to 12 refills per year | CCEA, 24 Mar 2023 (continuation for FY 2022-23 and 2023-24): 1910516 / 1910524 / 1910534 |
| V2 | 2023-10-05 | ₹300 per cylinder, up to 12 refills per year | Cabinet, 7 Mar 2024 (continuation for FY 2024-25): 2012354 / 2012433 / 2012493 |
| V3 | 2025-04-01 (FY 2025-26; approved 8 Aug 2025) | ₹300 per cylinder, up to **9** refills per year | Cabinet, 8 Aug 2025: 2154117 / 2154218 / 2154137. This release also restates V1 and V2. |
| V4 | 2026-04-01 (**unconfirmed boundary**) | ₹300 per cylinder on the **first 4** refills each year | MoPNG price-comparison release, 7 Jun 2026: 2269944 (en only). It states the first-four-refills rule but also calls the support "unchanged"; it is not a decision document. Press reports put the cut from 9 to 4 at FY 2026-27. Found by the human reviewer. |

- **Primary instrument:** MoPNG orders, to locate. The 5 Oct 2023 effective date is stated in PIB material and should be confirmed against the order.

### 3. PM SVANidhi: loan tranches

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2022 (third loan added with the extension; exact date to confirm) | 1st loan ₹10,000; 2nd ₹20,000; 3rd up to ₹50,000 | MoHUA, Parliament reply, 8 Dec 2022: 1881759 (en only). Related CCEA release, 27 Apr 2022: 1820509 / 1820586 / 1820537 (extension; amounts not stated). |
| V2 | 2025-08-27 (Cabinet approval; confirm the operational date) | 1st up to ₹15,000; 2nd up to ₹25,000; 3rd ₹50,000 unchanged. Lending period to 31 Mar 2030. UPI-linked RuPay credit card after the 2nd loan is repaid. | Cabinet, 27 Aug 2025: 2161157 / 2161190 / 2161168 |

- **Primary instrument:** PM SVANidhi Scheme Guidelines (MoHUA, mohua.gov.in, January 2026 upload). Also look for the earlier guidelines, ideally with Hindi or Gujarati versions of V1.

### 4. Rural employment guarantee: MGNREGA → VB-G RAM G

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2006-02-02 (MGNREGA 2005 in force; to confirm) | At least 100 days of wage employment per rural household per financial year | MoRD, Lok Sabha reply, 3 Dec 2024: 2080090 / 2081833 / –. Primary instrument: MGNREGA 2005, s. 3(1), to locate. |
| V2 | 2026-07-01 | At least **125** days per rural household per financial year (s. 5(1)). MGNREGA repealed the same day. States may notify a pause period of up to 60 days. | Assent release, 21 Dec 2025: 2207187 / 2207188 / 2207195. PIB backgrounder, 11 May 2026: 2259691 / 2259720 / 2259765 (states the 1 Jul 2026 commencement). |

- **Primary instrument:** VB-G RAM G Act 2025 and its commencement notification (Gazette of India), to locate.
- **Note:** between the Dec 2025 assent and the Jul 2026 commencement, the *law* had changed but was not yet in force. That gives a natural "announced but not yet effective" test case.

### 5. PMAY-Urban → PMAY-U 2.0

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2015-06-25 (PMAY-U launch, to confirm; CLSS-MIG added later) | EWS up to ₹3L; LIG ₹3–6L; MIG-I ₹6–12L; MIG-II ₹12–18L (CLSS) | MoHUA, 12 Jun 2018: 1535218 / – / – (states the MIG-I and MIG-II bands as text). The EWS/LIG bands of v1 are not stated in a captured v1 document. |
| V2 | 2024-08-09 (Cabinet approval) | EWS up to ₹3L; LIG ₹3–6L; **MIG ₹6–9L**. Government assistance ₹2.5 lakh per unit (AHP/BLC). | Cabinet, 9 Aug 2024: 2043924 / 2043974 / 2043931 |

- **Caveats:**
  - The CLSS-MIG vertical closed in 2021, so the MIG ceiling "changed" across schemes rather than inside one continuous rule.
  - States may redefine the income criteria.
  - Questions must be scoped carefully (e.g. "under PMAY-Urban"). If that proves too ambiguous in Phase 2, drop this scheme.

### 6. AB PM-JAY: senior citizens aged 70+

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2018-09-23 (PM-JAY launch, to confirm) | Eligibility by deprivation and occupational criteria (SECC), with no age-based entitlement; ₹5 lakh per family per year | MoHFW, Lok Sabha reply, 26 Jul 2024: 2037638 / 2037670 / – ("all members of the eligible families irrespective of age are covered"; "no proposal to open the scheme beyond the existing beneficiary base") |
| V2 | 2024-10-29 (launch; Cabinet approval 11 Sep 2024) | Everyone aged **70+** is eligible regardless of income. ₹5 lakh per year on a family basis, plus a top-up of up to ₹5 lakh for seniors in families already covered. | Cabinet, 11 Sep 2024: 2053883 / 2053919 / – |

### 7. PM Mudra Yojana: loan limit

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2015-04-08 | Loans up to ₹10 lakh (Shishu / Kishore / Tarun) | MoF, 8th-anniversary release, 8 Apr 2023: 1914739 / 1914743 / 1914769 |
| V2 | 2024-10-24 | Up to **₹20 lakh**; new **Tarun Plus** category (₹10–20 lakh) for borrowers who have repaid a Tarun loan | MoF, 29 Oct 2024: 2069170 / 2069230 / – |

### 8. Senior Citizens' Savings Scheme and Monthly Income Scheme: deposit limits

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2004-08-02 (SCSS notified) | SCSS max ₹15 lakh. MIS max ₹4.5 lakh (single), ₹9 lakh (joint). | MoF, 18 Sep 2004 (legacy relid 3906, en only): states the ₹15 lakh SCSS limit. The old MIS limits are not stated in any captured v1 document; they appear only as "raised from" in the v2 release. |
| V2 | 2023-04-01 | SCSS max **₹30 lakh**. MIS max **₹9 lakh** (single), **₹15 lakh** (joint). | MoC/PIB, 1 Apr 2023: 1912742 / 1912834 / –. Gazette: SCSS (Amendment) Scheme 2023, G.S.R. 240(E) dated 31 Mar 2023 (citation from the NSI scheme text; to confirm). |

### 9. National Means-cum-Merit Scholarship (NMMSS): income ceiling

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | before 2021-22 | Parental income ceiling ₹1.5 lakh per year | MHRD, Lok Sabha reply, 4 Mar 2015 (legacy relid 116460, en only) |
| V2 | 2021-22 (approved 22 Feb 2022, for 2021-22 to 2025-26) | Parental income ceiling **₹3.5 lakh** per year; ₹12,000 per year unchanged | MoE, 22 Feb 2022: 1800307 / 1800361 / – |

- **Open question:** the release's text extraction was fragmentary. Confirm the exact ceilings from the full text in 1b.

### 10. GST: rate structure

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2017-07-01 | Four slabs: 5, 12, 18, 28 percent | Roll-out release, 30 Jun 2017: legacy relid 167023 (en only) |
| V2 | 2025-09-22 (56th Council, 3 Sep 2025) | Two main rates, 5 and 18 percent, plus 40 percent for sin/luxury goods. Annexure I lists old and new rates for processed foods | Food-processing release, 8 Sep 2025: 2164586 / 2164646 / 2164687 |

- The 2017 release gives no item rates, so every old item rate in the fact table is restated from the annexure's "From" column.
- The slab count is not a benchmark fact: with a 40 percent rate and Nil items "how many slabs" is ambiguous.
- The full 56th Council release (about 149k characters) was deliberately not captured.

### 11. Capital gains tax

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | 2018-04-01 | Section 112A: 10 percent above ₹1 lakh. Old rates restated in v2 documents | Finance Bill 2018 FAQ, 4 Feb 2018: 1519095 (en only; proposal stage) |
| V2 | 2024-07-23 | STCG (111A) 20 percent; LTCG (112A) 12.5 percent, exemption ₹1.25 lakh; other LTCG 12.5 percent without indexation; holding periods 12/24 months | Budget summary 23 Jul 2024: 2035596 / 2035645 / 2035646; CBDT FAQ 24 Jul 2024: 2036604 / 2036706 (en, hi) |

### 12. Kisan Credit Card and Modified Interest Subvention Scheme

| Version | effective_from | Facts | Source |
|---|---|---|---|
| V1 | not established; in force on 28 May 2025 | Short-term loan limit ₹3 lakh; animal husbandry/fisheries ₹2 lakh | Cabinet release, 28 May 2025: 2131988 / 2132001 / 2132000 |
| V2 | **unknown** (placeholder 2025-05-29) | Limit ₹5 lakh; fisheries/allied ₹5 lakh; collateral-free ₹2 lakh (from ₹1.6 lakh, stated effective 1 Jan 2025) | PIB Backgrounder, 11 Mar 2026: 2238004 (en only) |

- **Open question:** the v1/v2 boundary is a placeholder. Find the primary instrument (RBI/DA&FW circular) before any as-of item uses dates between 28 May 2025 and 11 Mar 2026.
- The Hindi (2238178) and Gujarati (2238058) versions of the backgrounder are not captured.
- Retrieval times for these 14 captures are recorded as midnight UTC of the capture date; the time of day was not kept.

### 13. Minimum Support Prices: kharif and rabi crops

| Version | Announced | Facts | Source |
|---|---|---|---|
| Kharif V1 | 2025-05-28 (season 2025-26) | Paddy (common) ₹2,369; tur ₹8,000; cotton (medium staple) ₹7,710; groundnut ₹7,263 per quintal | CCEA release: 2131983 (en only) |
| Kharif V2 | 2026-05-13 (season 2026-27) | Paddy (common) ₹2,441; tur ₹8,450; cotton ₹8,267; groundnut ₹7,517 | CCEA release: 2260618 (en only) |
| Rabi V1 | 2025-10-01 (season 2026-27) | Wheat ₹2,585; gram ₹5,875; rapeseed and mustard ₹6,200; lentil ₹7,000 | CCEA release: 2173566 (en only) |
| Rabi V2 | 2026-09-30 (season 2027-28) | Wheat ₹2,610; gram ₹5,958; rapeseed and mustard ₹6,613; lentil ₹7,390 | CCEA release: 2316941 (en only) |

- A version runs from the Cabinet decision to the next decision; the price is for the coming marketing season.
- **Season ambiguity:** "current MSP" can mean the season now running or the latest announced. The fact table uses the latest announced; reviewers should check question wording.
- Hindi and Gujarati versions are not captured, so these facts reach hi/gu questions only through the cross-lingual condition.
- **Rejected candidate: Dearness Allowance.** The Jan 2026 and Jul 2026 Cabinet releases (2253245, 2329485) state only the increase over the existing rate ("2% over 58%", "3% over 60%"), never the new total, so the gold value would be derived rather than quoted.

## Reserve and rejected candidates

| Candidate | Status | Reason |
|---|---|---|
| Kisan Credit Card / Modified Interest Subvention Scheme limit ₹3L → ₹5L | Reserve | Announced in Budget 2025-26. A May 2025 Cabinet release still called it "under consideration"; a Mar 2026 backgrounder calls it done. Usable only once an effective-date document is found. |
| Ujjwala V4 (4 refills) | Captured as v4 | Boundary and decision document still unconfirmed (see scheme 2). |
| Gujarat PMJAY-MA cover raised to ₹10 lakh | **Rejected** | No official source found. Gujarat's own page still states ₹5 lakh. It was a recollection of mine that the sources did not support. |
| A Gujarat state scheme (Gujarati-original text) | Open | Not yet found. It would add native Gujarati documents rather than translations. Worth one more search in 1b. |
| Post-Matric Scholarship (SC/OBC) income ceiling | Rejected | Last changes were in 2017 or earlier (₹2.5 lakh); no recent version. |

## Known capture issues

- **Tables published as images.** These are flagged in `notes` in the manifest; the values are missing from the captured text:
  - FY2024-25 slabs in the English and Gujarati releases (2035605, 2035916). The Hindi release (2035659) has them as text.
  - The income-level benefit table in 2098406 and 2098461.
- **Private-use bullets.** In 2069230 (Mudra, Hindi), five list items start with U+F0A7. They are kept in the raw file and dropped from the chunks.
- **Restated history.** Some current-version releases restate the old rule; for example, Ujjwala v3 recounts the ₹200 and 12-refill history. Retrieval and scoring must not count such a mention as the document asserting the old rule.

## Remaining gaps (before Phase 2)

1. **Old-version documents in Hindi and Gujarati.** Every old version now has a document from its own period, so the "both versions retrieved" condition can run in English for all nine schemes. Coverage in the other languages is thinner:
   - **All three languages:** pmuy-subsidy, income-tax, pm-mudra.
   - **English and Hindi only:** rural-employment-guarantee, pmjay-senior.
   - **English only:** pm-svanidhi, pmay-urban, scss-mis and nmmss. These releases link to no Hindi or Gujarati versions.

   For the missing languages, the both-versions condition falls back to the cross-lingual setup (X), pairing an English old-version document with a Hindi or Gujarati question. This must be recorded per item in Phase 2. Two old-version facts have no own-period document at all: the MIS deposit limits, and the PMAY-U EWS/LIG bands (which did not change).
2. **PDFs to download** (static hosts that serve plain requests). None downloaded yet; each needs your approval:
   - VB-G RAM G backgrounder: `static.pib.gov.in/.../2026/may/doc2026511867601.pdf`. It is the source for the 1 Jul 2026 commencement date; its HTML version, at 25.6k characters, is too long to capture through the browser.
   - Primary instruments still to locate: Finance Acts, the SCSS (Amendment) Scheme 2023 gazette, the VB-G RAM G Act, and the scheme guidelines.
3. **Legacy-font PDFs.** Hindi and Gujarati gazette PDFs may extract as garbage. Detect this and flag the file rather than ingest it.
4. **Reuse terms.** Record the reuse terms for PIB and gazette content here before redistributing any text with the benchmark.
