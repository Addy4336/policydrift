"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { ApiError, ask, getExamples } from "@/lib/api";
import { formatDate, todayISO } from "@/lib/format";
import { LANGUAGE_NAMES } from "@/lib/i18n";
import { LANGUAGES, type AskResponse, type Examples, type Language } from "@/lib/types";
import {
  AnswerText,
  ChecksPanel,
  ConflictBanner,
  RuleVersionPanel,
  RunMeta,
  SourceCard,
} from "./answer";
import { AlertIcon, CalendarIcon, SpinnerIcon } from "./icons";
import { useLanguage } from "./language-provider";
import { Card, CardHeading, ErrorNotice, Skeleton } from "./ui";

interface Asked {
  question: string;
  language: Language;
}

export function AskClient() {
  const { language, setLanguage, t } = useLanguage();
  const ids = { q: useId(), date: useId(), dateHelp: useId(), lang: useId() };

  const [today, setToday] = useState("");
  const [asOf, setAsOf] = useState("");
  const [question, setQuestion] = useState("");
  const [examples, setExamples] = useState<Examples | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [asked, setAsked] = useState<Asked | null>(null);
  const [active, setActive] = useState<{ id: number; n: number } | null>(null);
  const [validation, setValidation] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const questionRef = useRef<HTMLTextAreaElement>(null);

  // The date depends on the visitor's clock, so it is set after hydration rather than at prerender.
  useEffect(() => {
    const d = todayISO();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setToday(d);
    setAsOf((prev) => prev || d);
  }, []);

  useEffect(() => {
    let cancelled = false;
    getExamples()
      .then((ex) => {
        if (!cancelled) setExamples(ex);
      })
      .catch(() => {
        if (!cancelled) setExamples(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => () => abortRef.current?.abort(), []);

  const submit = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) {
        setValidation(t.emptyQuestion);
        questionRef.current?.focus();
        return;
      }
      setValidation(null);
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setLoading(true);
      setError(null);
      setActive(null);
      setAsked({ question: trimmed, language });
      try {
        const res = await ask(
          { question: trimmed, language, ...(asOf ? { as_of: asOf } : {}) },
          ctrl.signal,
        );
        if (ctrl.signal.aborted) return;
        setResult(res);
        requestAnimationFrame(() => {
          resultRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
        });
      } catch (e) {
        if (ctrl.signal.aborted || (e instanceof DOMException && e.name === "AbortError")) return;
        setResult(null);
        setError(e instanceof ApiError || e instanceof Error ? e.message : String(e));
      } finally {
        if (abortRef.current === ctrl) setLoading(false);
      }
    },
    [asOf, language, t.emptyQuestion],
  );

  const showCitation = useCallback((id: number) => {
    setActive((prev) => ({ id, n: (prev?.n ?? 0) + 1 }));
    const el = document.getElementById(`source-${id}`);
    if (el) {
      el.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "center" });
      el.focus({ preventScroll: true });
    }
  }, []);

  const citationIds = useMemo(() => new Set(result?.citations.map((c) => c.id) ?? []), [result]);
  const resultLang = result?.language ?? language;
  const ctx = { t, lang: language };
  const exampleList = examples?.[language] ?? [];
  const isPast = asOf !== "" && today !== "" && asOf < today;

  return (
    <div className="mx-auto max-w-6xl px-4 pb-8 pt-8 sm:px-6 sm:pt-12">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{t.askTitle}</h1>
        <p className="mt-2 text-muted">{t.askIntro}</p>
      </div>

      <Card as="div" className="mt-6 p-4 sm:p-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit(question);
          }}
          className="space-y-5"
          aria-busy={loading}
        >
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <fieldset>
              <legend id={ids.lang} className="mb-1.5 text-sm font-medium">
                {t.languageLabel}
              </legend>
              <div role="radiogroup" aria-labelledby={ids.lang} className="inline-flex rounded-lg border border-border bg-surface-2 p-1">
                {LANGUAGES.map((l) => {
                  const selected = l === language;
                  return (
                    <button
                      key={l}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      lang={l}
                      onClick={() => setLanguage(l)}
                      className={`min-w-[5.5rem] rounded-md px-3 py-1.5 text-sm transition-colors ${
                        selected ? "bg-surface font-semibold text-text shadow-sm ring-1 ring-border" : "text-muted hover:text-text"
                      }`}
                    >
                      {LANGUAGE_NAMES[l]}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <div className="md:max-w-xs">
              <label htmlFor={ids.date} className="mb-1.5 flex items-center gap-1.5 text-sm font-medium">
                <CalendarIcon className="h-4 w-4 text-muted" />
                {t.asOfLabel}
              </label>
              <div className="flex items-center gap-2">
                <input
                  id={ids.date}
                  type="date"
                  value={asOf}
                  max={today || undefined}
                  min="2000-01-01"
                  onChange={(e) => setAsOf(e.target.value)}
                  aria-describedby={ids.dateHelp}
                  className="tnum h-10 rounded-lg border border-border bg-surface px-3 text-sm focus:border-accent"
                />
                {isPast ? (
                  <button
                    type="button"
                    onClick={() => setAsOf(today)}
                    className="h-10 rounded-lg px-2.5 text-sm text-accent hover:bg-accent-soft"
                  >
                    {t.today}
                  </button>
                ) : null}
              </div>
              <p id={ids.dateHelp} className="mt-1.5 text-xs text-muted">
                {t.asOfHelp}
              </p>
            </div>
          </div>

          <div>
            <label htmlFor={ids.q} className="mb-1.5 block text-sm font-medium">
              {t.questionLabel}
            </label>
            <textarea
              id={ids.q}
              ref={questionRef}
              lang={language}
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value);
                if (validation) setValidation(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void submit(question);
                }
              }}
              rows={3}
              maxLength={1000}
              placeholder={t.questionPlaceholder}
              aria-invalid={validation ? true : undefined}
              aria-describedby={validation ? `${ids.q}-err` : undefined}
              className="block w-full resize-y rounded-lg border border-border bg-surface px-3.5 py-3 text-base leading-relaxed placeholder:text-muted/70 focus:border-accent"
            />
            {validation ? (
              <p id={`${ids.q}-err`} className="mt-1.5 text-sm text-danger">
                {validation}
              </p>
            ) : null}
          </div>

          {exampleList.length > 0 ? (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">{t.examples}</p>
              <ul className="flex flex-wrap gap-2">
                {exampleList.map((ex) => (
                  <li key={ex}>
                    <button
                      type="button"
                      lang={language}
                      onClick={() => {
                        setQuestion(ex);
                        void submit(ex);
                      }}
                      disabled={loading}
                      className="rounded-full border border-border bg-surface-2 px-3 py-1.5 text-left text-sm text-text transition-colors hover:border-accent hover:bg-accent-soft disabled:opacity-60"
                    >
                      {ex}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <p className="tnum text-xs text-muted">
              {asOf ? (
                <>
                  {t.answerFor} <span className="font-medium text-text">{formatDate(asOf, language)}</span>
                </>
              ) : null}
            </p>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-semibold text-surface transition-colors hover:bg-accent-strong disabled:cursor-progress disabled:opacity-80"
            >
              {loading ? <SpinnerIcon /> : null}
              {loading ? t.submitting : t.submit}
            </button>
          </div>
        </form>
      </Card>

      <div ref={resultRef} className="scroll-mt-20" aria-live="polite">
        {loading ? <ResultSkeleton label={t.submitting} /> : null}
        {!loading && error ? (
          <div className="mt-8">
            <ErrorNotice title={t.errorTitle} message={error} />
          </div>
        ) : null}
        {!loading && result ? (
          <div className="mt-8 space-y-5">
            {result.conflicts.length > 0 ? <ConflictBanner conflicts={result.conflicts} ctx={ctx} /> : null}

            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <div className="min-w-0 space-y-5">
                <Card aria-labelledby="answer-heading">
                  <CardHeading id="answer-heading">{t.answer}</CardHeading>
                  <div className="px-4 py-4 sm:px-5">
                    {asked ? (
                      <p lang={asked.language} className="mb-3 text-sm text-muted">
                        “{asked.question}”
                      </p>
                    ) : null}
                    <AnswerText
                      answer={result.answer}
                      citationIds={citationIds}
                      onCite={showCitation}
                      lang={resultLang}
                      t={t}
                    />
                    {result.warnings.length > 0 ? (
                      <ul className="mt-4 space-y-1.5 rounded-lg bg-surface-2 px-3 py-2.5 text-sm">
                        {result.warnings.map((w) => (
                          <li key={w} className="flex gap-2">
                            <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
                            <span>{w}</span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                </Card>

                <section aria-labelledby="sources-heading" className="space-y-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 id="sources-heading" className="text-xs font-semibold uppercase tracking-wider text-muted">
                      {t.sources} <span className="tnum">({result.citations.length})</span>
                    </h2>
                    <p className="text-xs text-muted">{t.sourcesNote}</p>
                  </div>
                  {result.citations.map((c) => (
                    <SourceCard key={c.id} c={c} active={active?.id === c.id} flashKey={active?.n ?? 0} ctx={ctx} />
                  ))}
                </section>
              </div>

              <aside className="space-y-5 lg:sticky lg:top-20 lg:self-start">
                <RuleVersionPanel versions={result.rule_versions} asOf={result.as_of} ctx={ctx} />
                <ChecksPanel checks={result.checks} onCite={showCitation} ctx={ctx} />
                <RunMeta res={result} ctx={ctx} />
              </aside>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ResultSkeleton({ label }: { label: string }) {
  return (
    <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]" role="status">
      <span className="sr-only">{label}</span>
      <Card as="div" className="space-y-3 p-5">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-3/4" />
      </Card>
      <Card as="div" className="space-y-3 p-5">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
      </Card>
    </div>
  );
}

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
