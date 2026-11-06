"use client";

import { useEffect, useState } from "react";
import { getResults } from "@/lib/api";
import type { Results } from "@/lib/types";
import { HistoryIcon } from "./icons";
import { MarkdownView } from "./markdown-view";
import { Badge, Card, ErrorNotice, Skeleton } from "./ui";

export function ResultsClient() {
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getResults()
      .then((r) => {
        if (!cancelled) setResults(r);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <ErrorNotice title="Results could not be loaded" message={error} />;

  if (!results) {
    return (
      <div className="space-y-3" role="status">
        <span className="sr-only">Loading results</span>
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <section aria-labelledby="test-results">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="test-results" className="text-lg font-semibold">
            Test split
          </h2>
          <Badge tone={results.test ? "ok" : "neutral"}>{results.test ? "Confirmatory" : "Pending"}</Badge>
        </div>
        {results.test ? (
          <div className="mt-4">
            <MarkdownView source={results.test} />
          </div>
        ) : (
          <Card as="div" className="mt-3 flex items-start gap-3 border-dashed p-4 sm:p-5">
            <HistoryIcon className="mt-0.5 h-5 w-5 shrink-0 text-muted" />
            <div className="text-sm">
              <p className="font-medium">Final test run pending</p>
              <p className="mt-1 text-muted">
                The test split is frozen and checksummed. It is run once, with the preregistered configurations, after
                the analysis plan was frozen. Its results will appear here when that run is complete.
              </p>
            </div>
          </Card>
        )}
      </section>

      <section aria-labelledby="dev-results">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="dev-results" className="text-lg font-semibold">
            Development split
          </h2>
          <Badge tone="warn">Development split (not confirmatory)</Badge>
        </div>
        <p className="mt-2 max-w-3xl text-sm text-muted">
          These numbers come from the development split, which was used to build prompts, mitigations and the
          scoring judge. They are useful for direction but are not evidence for or against the hypotheses.
        </p>
        <div className="mt-4">
          <MarkdownView source={results.dev} />
        </div>
      </section>
    </div>
  );
}
