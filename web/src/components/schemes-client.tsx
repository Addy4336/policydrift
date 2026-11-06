"use client";

import { useEffect, useState } from "react";
import { getSchemes } from "@/lib/api";
import { dateValue, formatDate, todayISO } from "@/lib/format";
import type { Scheme, SchemeVersion } from "@/lib/types";
import { CheckIcon } from "./icons";
import { useLanguage } from "./language-provider";
import { Badge, Card, ErrorNotice, Skeleton } from "./ui";

const DAY = 86_400_000;

interface Range {
  start: number;
  end: number;
}

function schemeRange(s: Scheme, today: number): Range {
  const dates: number[] = [];
  for (const v of s.versions) {
    for (const d of [v.effective_from, v.effective_to, v.announced_on]) if (d) dates.push(dateValue(d));
  }
  const first = dates.length ? Math.min(...dates) : today - 365 * DAY;
  const last = Math.max(today, ...dates);
  const span = Math.max(last - first, 365 * DAY);
  // Pad both sides so open-ended starts and today's marker have room.
  return { start: first - span * 0.06, end: last + span * 0.04 };
}

function pct(t: number, r: Range): number {
  return Math.min(100, Math.max(0, ((t - r.start) / (r.end - r.start)) * 100));
}

function yearTicks(r: Range): number[] {
  const y0 = new Date(r.start).getUTCFullYear() + 1;
  const y1 = new Date(r.end).getUTCFullYear();
  const years: number[] = [];
  const step = Math.max(1, Math.ceil((y1 - y0 + 1) / 6));
  for (let y = y0; y <= y1; y += step) years.push(y);
  return years;
}

function Timeline({ scheme, today }: { scheme: Scheme; today: number }) {
  const r = schemeRange(scheme, today);
  const ticks = yearTicks(r);
  return (
    <div className="relative mt-4 select-none" aria-hidden>
      <div className="relative h-9 rounded-md bg-surface-2">
        {ticks.map((y) => (
          <span
            key={y}
            className="absolute inset-y-0 w-px bg-border"
            style={{ left: `${pct(Date.UTC(y, 0, 1), r)}%` }}
          />
        ))}
        {scheme.versions.map((v, i) => {
          const from = v.effective_from ? dateValue(v.effective_from) : r.start;
          const to = v.effective_to ? dateValue(v.effective_to) + DAY : r.end;
          const left = pct(from, r);
          const width = Math.max(pct(to, r) - left, 1.2);
          const label = width > 7;
          return (
            <div
              key={v.id}
              title={`${v.id}: ${v.effective_from ?? "?"} – ${v.effective_to ?? "now"}`}
              className={`absolute top-1.5 bottom-1.5 flex items-center overflow-hidden rounded px-1.5 text-[11px] font-semibold ${
                v.in_force
                  ? "bg-accent text-surface"
                  : i % 2 === 0
                    ? "bg-border-strong/70 text-text"
                    : "bg-border-strong/45 text-text"
              } ${v.effective_from ? "" : "rounded-l-none [mask-image:linear-gradient(to_right,transparent,black_24px)]"}`}
              style={{ left: `${left}%`, width: `${width}%` }}
            >
              {label ? <span className="truncate">{v.id}</span> : null}
            </div>
          );
        })}
        {scheme.versions
          .filter((v) => v.announced_on && v.announced_on !== v.effective_from)
          .map((v) => (
            <span
              key={`a-${v.id}`}
              className="absolute -bottom-1 h-2.5 w-2.5 -translate-x-1/2 rotate-45 border border-surface bg-warn"
              style={{ left: `${pct(dateValue(v.announced_on as string), r)}%` }}
            />
          ))}
        <span className="absolute -inset-y-1 w-0.5 rounded bg-text/70" style={{ left: `${pct(today, r)}%` }} />
      </div>
      <div className="tnum relative mt-1.5 h-4 text-[11px] text-muted">
        {ticks.map((y) => (
          <span key={y} className="absolute -translate-x-1/2" style={{ left: `${pct(Date.UTC(y, 0, 1), r)}%` }}>
            {y}
          </span>
        ))}
      </div>
    </div>
  );
}

function VersionRow({ v }: { v: SchemeVersion }) {
  const { t, language } = useLanguage();
  return (
    <tr className={v.in_force ? "bg-accent-soft/50" : undefined}>
      <th scope="row" className="whitespace-nowrap py-1.5 pr-3 text-left font-medium">
        {v.id}
      </th>
      <td className="tnum py-1.5 pr-3">{v.effective_from ? formatDate(v.effective_from, language) : t.unknownStart}</td>
      <td className="tnum py-1.5 pr-3">{v.effective_to ? formatDate(v.effective_to, language) : t.noEndDate}</td>
      <td className="tnum hidden py-1.5 pr-3 text-muted sm:table-cell">
        {v.announced_on ? formatDate(v.announced_on, language) : "—"}
      </td>
      <td className="py-1.5 text-right">
        {v.in_force ? (
          <Badge tone="ok">
            <CheckIcon className="h-3.5 w-3.5" />
            {t.inForce}
          </Badge>
        ) : null}
      </td>
    </tr>
  );
}

export function SchemesClient() {
  const { t } = useLanguage();
  const [schemes, setSchemes] = useState<Scheme[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [today, setToday] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setToday(dateValue(todayISO()));
    getSchemes()
      .then((s) => {
        if (!cancelled) setSchemes(s);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-4 pb-8 pt-8 sm:px-6 sm:pt-12">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{t.navSchemes}</h1>
        <p className="mt-2 text-muted">
          Every rule in the store, with the window in which each version applied. Answers use the version whose
          window contains the date you ask about.
        </p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted" aria-hidden>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-5 rounded-sm bg-accent" /> Version in force
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-5 rounded-sm bg-border-strong/70" /> Earlier version
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rotate-45 bg-warn" /> Announced
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3.5 w-0.5 rounded bg-text/70" /> Today
        </span>
      </div>

      {error ? (
        <div className="mt-6">
          <ErrorNotice title={t.errorTitle} message={error} />
        </div>
      ) : null}

      {!schemes && !error ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2" role="status">
          <span className="sr-only">Loading schemes</span>
          {[0, 1, 2, 3].map((i) => (
            <Card as="div" key={i} className="space-y-3 p-5">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-3 w-1/2" />
            </Card>
          ))}
        </div>
      ) : null}

      {schemes && today !== null ? (
        <ul className="mt-6 grid gap-4 md:grid-cols-2">
          {schemes.map((s) => {
            const current = s.versions.find((v) => v.in_force);
            return (
              <li key={s.id}>
                <Card as="article" className="h-full p-4 sm:p-5" aria-labelledby={`scheme-${s.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 id={`scheme-${s.id}`} className="font-semibold leading-snug">
                        {s.name}
                      </h2>
                      <p className="mt-0.5 font-mono text-[11px] text-muted">{s.id}</p>
                    </div>
                    <span className="tnum shrink-0 text-xs text-muted">
                      {s.versions.length} {s.versions.length === 1 ? "version" : "versions"}
                    </span>
                  </div>
                  <Timeline scheme={s} today={today} />
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-sm">
                      <caption className="sr-only">
                        Versions of {s.name}
                        {current ? `; ${current.id} is in force` : ""}
                      </caption>
                      <thead>
                        <tr className="text-left text-xs text-muted">
                          <th scope="col" className="py-1 pr-3 font-medium">
                            {t.version}
                          </th>
                          <th scope="col" className="py-1 pr-3 font-medium">
                            {t.effectiveFrom}
                          </th>
                          <th scope="col" className="py-1 pr-3 font-medium">
                            {t.effectiveTo}
                          </th>
                          <th scope="col" className="hidden py-1 pr-3 font-medium sm:table-cell">
                            Announced
                          </th>
                          <th scope="col" className="py-1">
                            <span className="sr-only">Status</span>
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {s.versions.map((v) => (
                          <VersionRow key={v.id} v={v} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
