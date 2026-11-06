import type { Metadata } from "next";
import { ResultsClient } from "@/components/results-client";
import { Card } from "@/components/ui";

export const metadata: Metadata = {
  title: "Research",
  description:
    "Stale by Default: measuring and mitigating outdated-rule answers in multilingual policy RAG agents. Method and results.",
};

const CONDITIONS = [
  ["R0", "No retrieval", "The question alone. Measures what the model remembers from training."],
  ["R1", "Standard RAG", "Top-k passages from the full store, old and current versions mixed, no version filter."],
  ["R2", "Current only", "Top-k passages from the version currently in force."],
  ["R3", "Both versions, with dates", "Matched passages from the old and the current version, each labelled with its effective dates."],
  ["R4", "Both versions, without dates", "As R3 with the date labels removed (exploratory)."],
] as const;

const MITIGATIONS = [
  ["M-a1", "Date-stamped prompt", "States today's date and asks for the rule in force on that date."],
  ["M-a2", "Validity statement", "Each passage carries a sentence saying the period it applies to."],
  ["M-b", "Conflict-checker agent", "Drafts an answer, checks it against the retrieved current rule and re-answers on disagreement."],
  ["M-c", "Version-filtered retrieval", "Keeps only passages whose effective window contains the as-of date."],
] as const;

const HYPOTHESES = [
  ["H1", "Even with the current rule retrieved, models give outdated answers at a measurable rate."],
  ["H2", "The outdated-answer rate is higher for Hindi and Gujarati questions than for English."],
  ["H3", "Mitigations reduce the rate, with different cost and latency tradeoffs."],
] as const;

function DefTable({ caption, rows }: { caption: string; rows: readonly (readonly [string, string, string])[] }) {
  return (
    <Card as="div" className="overflow-hidden">
      <table className="w-full text-sm">
        <caption className="border-b border-border bg-surface-2 px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-muted">
          {caption}
        </caption>
        <tbody className="divide-y divide-border">
          {rows.map(([code, name, desc]) => (
            <tr key={code}>
              <th scope="row" className="w-16 px-4 py-2.5 text-left align-top font-mono text-xs font-semibold text-accent-strong">
                {code}
              </th>
              <td className="py-2.5 pr-4 align-top">
                <span className="font-medium">{name}</span>
                <span className="mt-0.5 block text-muted">{desc}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export default function ResearchPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-8 pt-8 sm:px-6 sm:pt-12">
      <div className="max-w-3xl">
        <p className="text-sm font-medium text-accent">Research</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Stale by Default</h1>
        <p className="mt-1 text-lg text-muted">
          Measuring and mitigating outdated-rule answers in multilingual policy RAG agents
        </p>
        <p className="mt-4 leading-relaxed">
          When a government rule changes, does a retrieval-augmented model answer from the current passage it was
          given, or from the older rule it memorised in training? PolicyDrift measures this on Indian central-government
          schemes whose rules changed, in English, Hindi and Gujarati, and tests which mitigations fix it.
        </p>
      </div>

      <section aria-labelledby="method" className="mt-10">
        <h2 id="method" className="text-lg font-semibold">
          Method
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {HYPOTHESES.map(([code, text]) => (
            <Card as="div" key={code} className="p-4">
              <p className="font-mono text-xs font-semibold text-accent-strong">{code}</p>
              <p className="mt-1 text-sm leading-relaxed">{text}</p>
            </Card>
          ))}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <DefTable caption="Retrieval conditions" rows={CONDITIONS} />
          <DefTable caption="Mitigations" rows={MITIGATIONS} />
        </div>
        <ul className="mt-5 grid gap-x-8 gap-y-2 text-sm text-muted md:grid-cols-2">
          <li className="flex gap-2">
            <span aria-hidden className="text-accent">•</span>
            Benchmark items are version-sensitive question pairs built from curated changed facts, each tied to a
            verbatim quote in an official release, worded in English, Hindi and Gujarati and verified by a human reviewer.
          </li>
          <li className="flex gap-2">
            <span aria-hidden className="text-accent">•</span>
            Passages are English for every question language, so Hindi and Gujarati results measure cross-lingual use
            of the same evidence.
          </li>
          <li className="flex gap-2">
            <span aria-hidden className="text-accent">•</span>
            Hypotheses and analysis were preregistered. The test split is frozen and checksummed and was never used for
            tuning; all development happened on the dev split.
          </li>
          <li className="flex gap-2">
            <span aria-hidden className="text-accent">•</span>
            Answers are scored by a deterministic matcher first and an LLM judge for undecided cases, calibrated against
            human labels. Inference uses paired exact tests with Holm correction and fact-cluster bootstrap intervals.
          </li>
        </ul>
      </section>

      <div className="mt-12">
        <ResultsClient />
      </div>
    </div>
  );
}
