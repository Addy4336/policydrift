"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { formatDate, formatLatency } from "@/lib/format";
import type { Strings } from "@/lib/i18n";
import type { AskResponse, Checks, Citation, Conflict, Language, RuleVersion } from "@/lib/types";
import { AlertIcon, CalendarIcon, CheckIcon, ExternalIcon, HistoryIcon } from "./icons";
import { Badge, Card, CardHeading } from "./ui";

interface Ctx {
  t: Strings;
  lang: Language;
}

export function effectiveWindow(from: string | null, to: string | null, { t, lang }: Ctx): string {
  const a = from ? formatDate(from, lang) : t.unknownStart;
  const b = to ? formatDate(to, lang) : t.noEndDate;
  return `${a} – ${b}`;
}

/** Turns "[1]" and "[1, 2]" into markdown links the renderer converts to citation buttons. */
export function linkCitationMarkers(text: string): string {
  return text.replace(/\[(\d+(?:\s*[,;]\s*\d+)*)\](?![(:])/g, (_m, ids: string) =>
    ids
      .split(/[,;]/)
      .map((s) => s.trim())
      .map((id) => `[${id}](#cite-${id})`)
      .join(""),
  );
}

export function AnswerText({
  answer,
  citationIds,
  onCite,
  lang,
  t,
}: {
  answer: string;
  citationIds: Set<number>;
  onCite: (id: number) => void;
  lang: Language;
  t: Strings;
}) {
  const components: Components = {
    a({ href, children }) {
      const m = href?.match(/^#cite-(\d+)$/);
      if (m) {
        const id = Number(m[1]);
        const valid = citationIds.has(id);
        return (
          <button
            type="button"
            onClick={() => valid && onCite(id)}
            aria-label={valid ? `${t.showSource} ${id}` : `${id}: ${t.invalidMarker}`}
            title={valid ? `${t.showSource} ${id}` : t.invalidMarker}
            aria-disabled={!valid}
            className={`tnum mx-0.5 inline-flex h-5 min-w-5 -translate-y-1 items-center justify-center rounded px-1 align-baseline text-[11px] font-semibold leading-none transition-colors ${
              valid
                ? "bg-accent-soft text-accent-strong hover:bg-accent hover:text-surface"
                : "cursor-not-allowed border border-warn-border bg-warn-soft text-warn"
            }`}
          >
            {children}
          </button>
        );
      }
      return (
        <a href={href} target="_blank" rel="noreferrer noopener">
          {children}
        </a>
      );
    },
    table({ children }) {
      return (
        <div className="table-wrap">
          <table>{children}</table>
        </div>
      );
    },
  };
  return (
    <div lang={lang} className="md text-[15px] sm:text-base">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {linkCitationMarkers(answer)}
      </ReactMarkdown>
    </div>
  );
}

export function ConflictBanner({ conflicts, ctx }: { conflicts: Conflict[]; ctx: Ctx }) {
  const { t } = ctx;
  return (
    <section
      aria-labelledby="conflict-heading"
      className="rounded-xl border border-warn-border bg-warn-soft px-4 py-4 sm:px-5"
    >
      <div className="flex items-start gap-3">
        <HistoryIcon className="mt-0.5 h-5 w-5 shrink-0 text-warn" />
        <div className="min-w-0 flex-1">
          <h2 id="conflict-heading" className="font-semibold text-text">
            {t.ruleChanged}
          </h2>
          <p className="mt-1 text-sm text-muted">{t.ruleChangedBody}</p>
          <ul className="mt-3 space-y-2.5">
            {conflicts.map((c) => (
              <li
                key={`${c.scheme}:${c.superseded_version}`}
                className="rounded-lg border border-warn-border/70 bg-surface/70 px-3 py-2.5 text-sm"
              >
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="font-medium">{c.scheme_name}</span>
                  <Badge tone="warn">
                    {t.superseded} · {c.superseded_version}
                  </Badge>
                  <span className="tnum text-xs text-muted">{effectiveWindow(c.effective_from, c.effective_to, ctx)}</span>
                </div>
                {c.note ? <p className="mt-1.5 text-text">{c.note}</p> : null}
                {c.excerpt ? (
                  <blockquote className="mt-1.5 border-l-2 border-warn-border pl-3 text-muted">{c.excerpt}</blockquote>
                ) : null}
                <a
                  href={c.source_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                >
                  {t.viewOfficial}: {c.title}
                  <ExternalIcon className="h-3.5 w-3.5 shrink-0" />
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export function RuleVersionPanel({ versions, asOf, ctx }: { versions: RuleVersion[]; asOf: string; ctx: Ctx }) {
  const { t, lang } = ctx;
  return (
    <Card aria-labelledby="rule-version-heading">
      <CardHeading id="rule-version-heading">{t.ruleVersionUsed}</CardHeading>
      <div className="divide-y divide-border">
        {versions.length === 0 ? (
          <p className="px-4 py-3 text-sm text-muted sm:px-5">—</p>
        ) : (
          versions.map((v) => {
            const inForce = (!v.effective_from || v.effective_from <= asOf) && (!v.effective_to || v.effective_to >= asOf);
            return (
              <div key={`${v.scheme}:${v.version}`} className="space-y-2 px-4 py-3 sm:px-5">
                <p className="font-medium leading-snug">{v.scheme_name}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="accent">
                    {t.version} {v.version}
                  </Badge>
                  {inForce ? (
                    <Badge tone="ok">
                      <CheckIcon className="h-3.5 w-3.5" />
                      {t.inForce}
                    </Badge>
                  ) : (
                    <Badge>{t.notInForce}</Badge>
                  )}
                </div>
                <dl className="tnum grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
                  <dt className="text-muted">{t.effectiveFrom}</dt>
                  <dd>{v.effective_from ? formatDate(v.effective_from, lang) : t.unknownStart}</dd>
                  <dt className="text-muted">{t.effectiveTo}</dt>
                  <dd>{v.effective_to ? formatDate(v.effective_to, lang) : t.noEndDate}</dd>
                </dl>
              </div>
            );
          })
        )}
      </div>
      <p className="tnum flex items-center gap-1.5 border-t border-border px-4 py-2.5 text-xs text-muted sm:px-5">
        <CalendarIcon className="h-3.5 w-3.5" />
        {t.answerFor} {formatDate(asOf, lang)}
      </p>
    </Card>
  );
}

function CheckRow({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2.5">
      {ok ? (
        <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-ok" title="OK" />
      ) : (
        <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-warn" title="Warning" />
      )}
      <span className="min-w-0">{children}</span>
    </li>
  );
}

export function ChecksPanel({
  checks,
  onCite,
  ctx,
}: {
  checks: Checks;
  onCite: (id: number) => void;
  ctx: Ctx;
}) {
  const { t } = ctx;
  const citationsOk = checks.citations_valid && checks.invalid_markers.length === 0;
  const allNumbersOk = checks.numbers.every((n) => n.verified);
  return (
    <Card aria-labelledby="checks-heading">
      <CardHeading
        id="checks-heading"
        aside={
          citationsOk && !checks.uncited && allNumbersOk ? (
            <Badge tone="ok">
              <CheckIcon className="h-3.5 w-3.5" /> OK
            </Badge>
          ) : (
            <Badge tone="warn">
              <AlertIcon className="h-3.5 w-3.5" />
              {t.warnings}
            </Badge>
          )
        }
      >
        {t.checks}
      </CardHeading>
      <div className="space-y-4 px-4 py-3 text-sm sm:px-5">
        <ul className="space-y-2">
          <CheckRow ok={citationsOk}>
            {citationsOk ? t.citationsValid : t.citationsInvalid}
            {checks.invalid_markers.length > 0 ? (
              <span className="tnum text-muted"> ({checks.invalid_markers.map((m) => `[${m}]`).join(" ")})</span>
            ) : null}
          </CheckRow>
          {checks.uncited ? <CheckRow ok={false}>{t.uncited}</CheckRow> : null}
        </ul>
        <div>
          <h3 className="mb-2 text-xs font-medium text-muted">{t.numbersHeading}</h3>
          {checks.numbers.length === 0 ? (
            <p className="text-muted">{t.noNumbers}</p>
          ) : (
            <ul className="space-y-2">
              {checks.numbers.map((n, i) => (
                <li
                  key={`${n.value}-${i}`}
                  className={`flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border px-2.5 py-2 ${
                    n.verified ? "border-border" : "border-warn-border bg-warn-soft"
                  }`}
                >
                  {n.verified ? (
                    <CheckIcon className="h-4 w-4 shrink-0 text-ok" />
                  ) : (
                    <AlertIcon className="h-4 w-4 shrink-0 text-warn" />
                  )}
                  <span className="tnum font-semibold">{n.value}</span>
                  <span className={`text-xs ${n.verified ? "text-muted" : "text-warn"}`}>
                    {n.verified ? t.numberVerified : t.numberNotFound}
                  </span>
                  {n.cited_in.length > 0 ? (
                    <span className="ml-auto flex items-center gap-1 text-xs text-muted">
                      {t.citedIn}
                      {n.cited_in.map((id) => (
                        <button
                          key={id}
                          type="button"
                          onClick={() => onCite(id)}
                          className="tnum rounded bg-accent-soft px-1.5 text-[11px] font-semibold text-accent-strong hover:bg-accent hover:text-surface"
                          aria-label={`${t.showSource} ${id}`}
                        >
                          {id}
                        </button>
                      ))}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  );
}

export function SourceCard({ c, active, flashKey, ctx }: { c: Citation; active: boolean; flashKey: number; ctx: Ctx }) {
  const { t, lang } = ctx;
  return (
    <article
      id={`source-${c.id}`}
      tabIndex={-1}
      aria-labelledby={`source-${c.id}-title`}
      className={`relative scroll-mt-24 rounded-xl border bg-surface p-4 transition-colors sm:p-5 ${
        active ? "border-accent ring-1 ring-accent" : "border-border"
      }`}
    >
      {active ? <span key={flashKey} className="flash pointer-events-none absolute inset-0 rounded-xl" aria-hidden /> : null}
      <div className="flex items-start gap-3">
        <span
          className="tnum flex h-6 min-w-6 shrink-0 items-center justify-center rounded-md bg-accent-soft px-1.5 text-xs font-semibold text-accent-strong"
          aria-hidden
        >
          {c.id}
        </span>
        <div className="min-w-0 flex-1">
          <h3 id={`source-${c.id}-title`} lang="en" className="font-medium leading-snug">
            <span className="sr-only">Source {c.id}: </span>
            {c.title}
          </h3>
          <p className="tnum mt-1 text-xs text-muted">
            {c.ministry} · {t.posted} {formatDate(c.posted_on, lang)}
          </p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <Badge tone="accent">
              {c.scheme_name} · {c.version}
            </Badge>
            {c.in_force ? (
              <Badge tone="ok">
                <CheckIcon className="h-3.5 w-3.5" />
                {t.inForce}
              </Badge>
            ) : (
              <Badge tone="warn">
                <HistoryIcon className="h-3.5 w-3.5" />
                {t.superseded}
              </Badge>
            )}
            <span className="tnum text-xs text-muted">{effectiveWindow(c.effective_from, c.effective_to, ctx)}</span>
          </div>
          <blockquote lang="en" className="mt-3 border-l-2 border-border-strong pl-3 text-sm leading-relaxed text-text">
            {c.excerpt}
          </blockquote>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <a
              href={c.source_url}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
            >
              {t.viewOfficial}
              <ExternalIcon className="h-3.5 w-3.5" />
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
            <code className="truncate text-[11px] text-muted">{c.chunk_id}</code>
          </div>
        </div>
      </div>
    </article>
  );
}

export function RunMeta({ res, ctx }: { res: AskResponse; ctx: Ctx }) {
  const { t } = ctx;
  return (
    <Card as="div" className="px-4 py-3 sm:px-5">
      <dl className="tnum grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
        <dt className="text-muted">{t.model}</dt>
        <dd className="truncate font-mono">{res.model}</dd>
        <dt className="text-muted">{t.latency}</dt>
        <dd>{formatLatency(res.latency_ms)}</dd>
        <dt className="text-muted">Cache</dt>
        <dd>{res.cached ? t.cached : t.live}</dd>
      </dl>
    </Card>
  );
}
