# PolicyDrift web

Next.js front end for PolicyDrift, a multilingual (English, Hindi, Gujarati) assistant for Indian government
rules. It shows answers with validated citations, the rule version and effective date used, and a notice when a
rule has changed. It also presents the research behind it: *Stale by Default: Measuring and Mitigating
Outdated-Rule Answers in Multilingual Policy RAG Agents*.

The app is a thin client over the FastAPI backend in `../api`. It holds no research logic.

## Stack

- Next.js 16 (App Router, Turbopack), React 19, TypeScript in strict mode
- Tailwind CSS 4, with colour tokens in `src/app/globals.css` (light and dark via `prefers-color-scheme`)
- `react-markdown` + `remark-gfm` for answers and the results tables
- Inter, Noto Sans Devanagari and Noto Sans Gujarati through `next/font/google`

## Setup

```bash
cd web
npm install
cp .env.example .env.local   # then edit if needed
npm run dev                  # http://localhost:3000
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |
| `NEXT_PUBLIC_DEMO_FIXTURES` | unset | Set to `1` to serve every call from `src/lib/fixtures.ts`, with no backend. A banner marks demo mode. |

Both are inlined at build time, so restart `npm run dev` (or rebuild) after changing them.

Run without a backend, for example to take screenshots:

```bash
# bash
NEXT_PUBLIC_DEMO_FIXTURES=1 npm run dev
# PowerShell
$env:NEXT_PUBLIC_DEMO_FIXTURES='1'; npm run dev
```

In demo mode, asking with an "as of" date before 24 Oct 2024 returns the earlier PM Mudra rule (₹10 lakh). Any
later date returns the current rule with a "rule changed" notice.

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint (Next.js config) |
| `npx tsc --noEmit` | Type check |

## Pages

- `/`: Ask. Language switch (also switches the main UI labels), an "as of" date, example questions, and the
  answer with clickable citation markers, the rule version used, a rule-changed notice, citation and number
  checks, and source cards linking to the official release.
- `/schemes`: every scheme with a timeline of its versions, effective windows and announcement dates.
- `/research`: a method summary and the results markdown from `/api/results`. Dev results are labelled as not
  confirmatory; the test section reads "Final test run pending" until the final run exists.

## API contract

Types are in `src/lib/types.ts` and the client is in `src/lib/api.ts`.

| Endpoint | Returns |
|---|---|
| `POST /api/ask` `{question, language, as_of?}` | answer, citations, rule_versions, conflicts, checks, warnings, model, latency_ms, cached |
| `GET /api/schemes` | schemes with versions (`effective_from`, `effective_to`, `announced_on`, `in_force`) |
| `GET /api/examples` | `{en, hi, gu}` example questions |
| `GET /api/results` | `{dev, test}` markdown; `test` is `null` until the final run |
| `GET /api/health` | `{status, chunks, model}` |

Errors are HTTP 4xx/5xx with `{"detail": string}`, and the client shows the detail text. The backend must allow
the front end's origin through CORS.

## Layout

```
src/
├── app/                 # layout, globals.css, / (Ask), /schemes, /research
├── components/          # ask-client, answer panels, schemes timeline, results, header/footer, ui primitives
└── lib/                 # types, api client, fixtures, i18n strings, date formatting
```
