import type { Language } from "./types";

/** Today's date as YYYY-MM-DD in the browser's local time zone. */
export function todayISO(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

const LOCALES: Record<Language, string> = { en: "en-IN", hi: "hi-IN", gu: "gu-IN" };

/** Formats an ISO date (YYYY-MM-DD) for display, e.g. "24 Oct 2024". Uses UTC to avoid off-by-one shifts. */
export function formatDate(iso: string | null | undefined, lang: Language = "en"): string {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return iso;
  const date = new Date(Date.UTC(y, m - 1, d));
  return new Intl.DateTimeFormat(LOCALES[lang], {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
    numberingSystem: "latn",
  }).format(date);
}

/** Milliseconds since the Unix epoch for an ISO date, at UTC midnight. */
export function dateValue(iso: string): number {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1);
}

export function formatLatency(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}
