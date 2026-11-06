// Demo fixtures, used only when NEXT_PUBLIC_DEMO_FIXTURES=1.
// Values are modelled on the real store (PIB releases in data/raw/) so screenshots look like
// genuine output, but they are static and never reflect a live model call.

import type {
  AskRequest,
  AskResponse,
  Citation,
  Examples,
  Health,
  Language,
  Results,
  Scheme,
} from "./types";

export const healthFixture: Health = {
  status: "ok",
  chunks: 440,
  model: "gemini-3.1-flash-lite",
};

export const examplesFixture: Examples = {
  en: [
    "What is the maximum loan I can get under PM Mudra Yojana?",
    "How many LPG refills a year get the PM Ujjwala subsidy?",
    "What is the deposit limit for the Senior Citizens' Savings Scheme?",
    "How many days of work does the rural employment guarantee give?",
  ],
  hi: [
    "प्रधानमंत्री मुद्रा योजना में अधिकतम कितना ऋण मिल सकता है?",
    "उज्ज्वला योजना में साल में कितने एलपीजी रिफिल पर सब्सिडी मिलती है?",
    "वरिष्ठ नागरिक बचत योजना में जमा की अधिकतम सीमा क्या है?",
  ],
  gu: [
    "પ્રધાનમંત્રી મુદ્રા યોજનામાં વધુમાં વધુ કેટલી લોન મળી શકે?",
    "ઉજ્જ્વલા યોજનામાં વર્ષમાં કેટલા એલપીજી રિફિલ પર સબસિડી મળે છે?",
    "વરિષ્ઠ નાગરિક બચત યોજનામાં જમા રકમની મહત્તમ મર્યાદા કેટલી છે?",
  ],
};

export const schemesFixture: Scheme[] = [
  {
    id: "income-tax-new-regime",
    name: "Income tax, new regime (individuals)",
    versions: [
      { id: "fy2023-24", effective_from: "2023-04-01", effective_to: "2024-03-31", announced_on: "2023-02-01", in_force: false },
      { id: "fy2024-25", effective_from: "2024-04-01", effective_to: "2025-03-31", announced_on: "2024-07-23", in_force: false },
      { id: "fy2025-26", effective_from: "2025-04-01", effective_to: null, announced_on: "2025-02-01", in_force: true },
    ],
  },
  {
    id: "pmuy-subsidy",
    name: "PM Ujjwala Yojana targeted LPG subsidy",
    versions: [
      { id: "v1", effective_from: "2022-05-22", effective_to: "2023-10-04", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2023-10-05", effective_to: "2025-03-31", announced_on: null, in_force: false },
      { id: "v3", effective_from: "2025-04-01", effective_to: "2026-03-31", announced_on: "2025-08-08", in_force: false },
      { id: "v4", effective_from: "2026-04-01", effective_to: null, announced_on: null, in_force: true },
    ],
  },
  {
    id: "pm-svanidhi",
    name: "PM SVANidhi street-vendor loans",
    versions: [
      { id: "v1", effective_from: "2022-04-27", effective_to: "2025-08-26", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2025-08-27", effective_to: null, announced_on: null, in_force: true },
    ],
  },
  {
    id: "rural-employment-guarantee",
    name: "Rural employment guarantee (MGNREGA, then VB-G RAM G)",
    versions: [
      { id: "v1", effective_from: "2006-02-02", effective_to: "2026-06-30", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2026-07-01", effective_to: null, announced_on: "2025-12-21", in_force: true },
    ],
  },
  {
    id: "pmay-urban",
    name: "Pradhan Mantri Awas Yojana - Urban",
    versions: [
      { id: "v1", effective_from: "2015-06-25", effective_to: "2024-08-08", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2024-08-09", effective_to: null, announced_on: null, in_force: true },
    ],
  },
  {
    id: "pmjay-senior",
    name: "AB PM-JAY coverage of senior citizens",
    versions: [
      { id: "v1", effective_from: "2018-09-23", effective_to: "2024-10-28", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2024-10-29", effective_to: null, announced_on: "2024-09-11", in_force: true },
    ],
  },
  {
    id: "pm-mudra",
    name: "PM Mudra Yojana loan limit",
    versions: [
      { id: "v1", effective_from: "2015-04-08", effective_to: "2024-10-23", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2024-10-24", effective_to: null, announced_on: "2024-07-23", in_force: true },
    ],
  },
  {
    id: "scss-mis",
    name: "Senior Citizens' Savings Scheme and Monthly Income Scheme deposit limits",
    versions: [
      { id: "v1", effective_from: "2004-08-02", effective_to: "2023-03-31", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2023-04-01", effective_to: null, announced_on: null, in_force: true },
    ],
  },
  {
    id: "nmmss",
    name: "National Means-cum-Merit Scholarship income ceiling",
    versions: [
      { id: "v1", effective_from: null, effective_to: "2021-03-31", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2021-04-01", effective_to: null, announced_on: "2022-02-22", in_force: true },
    ],
  },
  {
    id: "gst",
    name: "Goods and Services Tax rate structure",
    versions: [
      { id: "v1", effective_from: "2017-07-01", effective_to: "2025-09-21", announced_on: "2017-06-30", in_force: false },
      { id: "v2", effective_from: "2025-09-22", effective_to: null, announced_on: "2025-09-03", in_force: true },
    ],
  },
  {
    id: "capital-gains",
    name: "Capital gains tax rates and holding periods (Income-tax Act)",
    versions: [
      { id: "v1", effective_from: "2018-04-01", effective_to: "2024-07-22", announced_on: "2018-02-01", in_force: false },
      { id: "v2", effective_from: "2024-07-23", effective_to: null, announced_on: "2024-07-23", in_force: true },
    ],
  },
  {
    id: "kcc-miss",
    name: "Kisan Credit Card and Modified Interest Subvention Scheme",
    versions: [
      { id: "v1", effective_from: null, effective_to: "2025-05-28", announced_on: null, in_force: false },
      { id: "v2", effective_from: "2025-05-29", effective_to: null, announced_on: "2025-02-01", in_force: true },
    ],
  },
  {
    id: "msp-kharif",
    name: "Minimum Support Prices for kharif crops",
    versions: [
      { id: "v1", effective_from: "2025-05-28", effective_to: "2026-05-12", announced_on: "2025-05-28", in_force: false },
      { id: "v2", effective_from: "2026-05-13", effective_to: null, announced_on: "2026-05-13", in_force: true },
    ],
  },
  {
    id: "msp-rabi",
    name: "Minimum Support Prices for rabi crops",
    versions: [
      { id: "v1", effective_from: "2025-10-01", effective_to: "2026-09-29", announced_on: "2025-10-01", in_force: false },
      { id: "v2", effective_from: "2026-09-30", effective_to: null, announced_on: "2026-09-30", in_force: true },
    ],
  },
];

const MUDRA_V2: Citation = {
  id: 1,
  chunk_id: "pm-mudra:v2:en:2069170:001",
  scheme: "pm-mudra",
  scheme_name: "PM Mudra Yojana loan limit",
  version: "v2",
  effective_from: "2024-10-24",
  effective_to: null,
  in_force: true,
  title: "Pradhan Mantri Mudra Yojana",
  source_url: "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2069170",
  posted_on: "2024-10-29",
  ministry: "Ministry of Finance",
  excerpt:
    "This announcement also introduces a new loan category, Tarun Plus, designed specifically for those who have previously availed and successfully repaid loans under the Tarun category, allowing them to access funding between ₹10 lakh and ₹20 lakh.",
};

const MUDRA_V1: Citation = {
  id: 2,
  chunk_id: "pm-mudra:v1:en:1914739:000",
  scheme: "pm-mudra",
  scheme_name: "PM Mudra Yojana loan limit",
  version: "v1",
  effective_from: "2015-04-08",
  effective_to: "2024-10-23",
  in_force: false,
  title:
    "More than 40.82 crore loans amounting to ₹23.2 lakh crore sanctioned under Pradhan Mantri MUDRA Yojana (PMMY) since inception",
  source_url: "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1914739",
  posted_on: "2023-04-08",
  ministry: "Ministry of Finance",
  excerpt:
    "The Pradhan Mantri MUDRA Yojana (PMMY) was launched on 8th April 2015 by Prime Minister Shri Narendra Modi with the aim to facilitate easy collateral-free micro credit of up to ₹10 lakh to non-corporate, non-farm small and micro entrepreneurs.",
};

const CURRENT_ANSWERS: Record<Language, string> = {
  en:
    "The maximum loan under PM Mudra Yojana is now **₹20 lakh** [1]. The higher limit applies from 24 October 2024, when the new **Tarun Plus** category was introduced for borrowers who have taken and repaid a Tarun loan; it covers loans between ₹10 lakh and ₹20 lakh [1].\n\nBefore that date the ceiling was ₹10 lakh [2], so older guides that quote ₹10 lakh describe the superseded rule.",
  hi:
    "प्रधानमंत्री मुद्रा योजना में अधिकतम ऋण सीमा अब **₹20 लाख** है [1]। यह सीमा 24 अक्टूबर 2024 से लागू है, जब उन उधारकर्ताओं के लिए नई **तरुण प्लस** श्रेणी शुरू की गई जिन्होंने तरुण ऋण लेकर चुका दिया है; इसमें ₹10 लाख से ₹20 लाख तक के ऋण आते हैं [1]।\n\nइससे पहले अधिकतम सीमा ₹10 लाख थी [2], इसलिए ₹10 लाख बताने वाली पुरानी जानकारी अब लागू नहीं है।",
  gu:
    "પ્રધાનમંત્રી મુદ્રા યોજનામાં મહત્તમ લોન મર્યાદા હવે **₹20 લાખ** છે [1]. આ મર્યાદા 24 ઓક્ટોબર 2024થી અમલમાં છે, જ્યારે તરુણ લોન લઈને ચૂકવી દેનાર ઉધાર લેનારાઓ માટે નવી **તરુણ પ્લસ** શ્રેણી શરૂ કરવામાં આવી; તેમાં ₹10 લાખથી ₹20 લાખ સુધીની લોન આવે છે [1].\n\nઆ તારીખ પહેલાં મહત્તમ મર્યાદા ₹10 લાખ હતી [2], તેથી ₹10 લાખ જણાવતી જૂની માહિતી હવે લાગુ પડતી નથી.",
};

const PAST_ANSWERS: Record<Language, string> = {
  en: "On that date the maximum loan under PM Mudra Yojana was **₹10 lakh** [1], covering the Shishu, Kishore and Tarun categories.",
  hi: "उस तारीख को प्रधानमंत्री मुद्रा योजना में अधिकतम ऋण सीमा **₹10 लाख** थी [1], जिसमें शिशु, किशोर और तरुण श्रेणियाँ शामिल थीं।",
  gu: "તે તારીખે પ્રધાનમંત્રી મુદ્રા યોજનામાં મહત્તમ લોન મર્યાદા **₹10 લાખ** હતી [1], જેમાં શિશુ, કિશોર અને તરુણ શ્રેણીઓ સામેલ હતી.",
};

/** Builds a plausible /api/ask response. Dates before the Mudra v2 boundary return the v1 rule. */
export function askFixture(req: AskRequest, today: string): AskResponse {
  const asOf = req.as_of ?? today;
  const past = asOf < "2024-10-24";
  if (past) {
    return {
      answer: PAST_ANSWERS[req.language],
      language: req.language,
      as_of: asOf,
      model: healthFixture.model,
      cached: false,
      latency_ms: 1284,
      citations: [{ ...MUDRA_V1, id: 1, in_force: asOf >= "2015-04-08" }],
      rule_versions: [
        {
          scheme: "pm-mudra",
          scheme_name: MUDRA_V1.scheme_name,
          version: "v1",
          effective_from: "2015-04-08",
          effective_to: "2024-10-23",
        },
      ],
      conflicts: [],
      checks: {
        citations_valid: true,
        uncited: false,
        invalid_markers: [],
        numbers: [{ value: "₹10 lakh", verified: true, cited_in: [1] }],
      },
      warnings: [
        "You asked about a past date. A newer version of this rule (v2, from 2024-10-24) is in force today.",
      ],
    };
  }
  return {
    answer: CURRENT_ANSWERS[req.language],
    language: req.language,
    as_of: asOf,
    model: healthFixture.model,
    cached: true,
    latency_ms: 46,
    citations: [MUDRA_V2, MUDRA_V1],
    rule_versions: [
      {
        scheme: "pm-mudra",
        scheme_name: MUDRA_V2.scheme_name,
        version: "v2",
        effective_from: "2024-10-24",
        effective_to: null,
      },
    ],
    conflicts: [
      {
        scheme: "pm-mudra",
        scheme_name: MUDRA_V1.scheme_name,
        superseded_version: "v1",
        effective_from: "2015-04-08",
        effective_to: "2024-10-23",
        title: MUDRA_V1.title,
        source_url: MUDRA_V1.source_url,
        excerpt: "…collateral-free micro credit of up to ₹10 lakh to non-corporate, non-farm small and micro entrepreneurs.",
        note: "An older version of this rule was also retrieved. It gave a ₹10 lakh ceiling and stopped applying on 2024-10-23.",
      },
    ],
    checks: {
      citations_valid: true,
      uncited: false,
      invalid_markers: [],
      numbers: [
        { value: "₹20 lakh", verified: true, cited_in: [1] },
        { value: "₹10 lakh", verified: true, cited_in: [1, 2] },
        { value: "24 October 2024", verified: false, cited_in: [] },
      ],
    },
    warnings: [
      "One date in the answer (24 October 2024) comes from the version registry, not from the cited passage.",
    ],
  };
}

export const resultsFixture: Results = {
  dev: `# PolicyDrift results (dev split)

## h1

| condition | n | outdated rate | 95% CI (bootstrap over facts) | CI lower > 2% |
|---|---|---|---|---|
| R2 | 206 | 0.0% | [0.0%, 0.0%] | no |
| R3 | 201 | 10.0% | [1.1%, 20.4%] | no |

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

| mitigation | n | baseline | with | fixed / broke | change [95% CI, facts] | p (one-sided) | p Holm |
|---|---|---|---|---|---|---|---|
| M-a1 | 134 | 6.7% | 0.0% | 9 / 0 | -6.7% [-16.7%, 0.0%] | 0.0020 | 0.0059 |
| M-a2 | 134 | 6.7% | 9.0% | 1 / 4 | 2.2% [-1.4%, 6.5%] | 0.9688 | 0.9688 |
| M-b | 134 | 6.7% | 0.0% | 9 / 0 | -6.7% [-16.7%, 0.0%] | 0.0020 | 0.0059 |

## mitigations_r1_descriptive

| mitigation (R1, descriptive) | n | baseline | with | refusals | tokens/answer |
|---|---|---|---|---|---|
| M-a1 | 252 | 17.9% | 18.3% | 3.6% | 971 |
| M-a2 | 168 | 18.5% | 17.3% | 4.2% | 947 |
| M-b | 251 | 17.5% | 10.4% | 9.6% | 2200 |
| M-c | 252 | 17.9% | 0.0% | 13.1% | 888 |
`,
  test: null,
};
